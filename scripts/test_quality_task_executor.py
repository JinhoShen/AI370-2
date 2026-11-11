#!/usr/bin/env python3
"""Offline tests for the fixed FPGA quality-task validators.

OUTPUT and the Vivado install path are redirected to the system temp dir and
``subprocess.run`` is replaced by a fake tool table that writes canned logs and
reports.  No Vivado, XSim, Vitis HLS, model, systemd unit or network endpoint
is launched; the version-controlled frozen corpus is only read.
"""
from __future__ import annotations

import hashlib
import io
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import quality_task_executor as executor

REAL_CORPUS = executor.CORPUS
T3_SCENARIOS = [f"QUALITY_T3_SCENARIO_{name}_PASS" for name in (
    "reset", "aw_before_w", "w_before_aw", "simultaneous", "wstrb", "unmapped",
    "b_backpressure", "r_backpressure", "consecutive")]
T3_MUTANTS = sorted(p.name for p in (REAL_CORPUS / "T3/V1/private/mutants").glob("*.sv"))
SIM_MARKER = {"T1": "QUALITY_T1_PASS", "T2": "QUALITY_T1_PASS", "T4": "QUALITY_T4_PASS",
              "T5": "QUALITY_T5_PASS", "T7": "QUALITY_T7_PASS", "T8": "QUALITY_T8_PASS"}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class FakeTools:
    """Stand-in for subprocess.run; refuses anything it does not recognise."""

    def __init__(self, vivado: Path):
        self.vivado = vivado
        self.calls: list[dict] = []
        self.env_sources: list[str] = []
        self.xsim_stdout = "QUALITY_T1_PASS\n"
        self.handlers = {
            "xvlog": lambda cmd, cwd: (0, "INFO: [VRFC] analyzing\n", ""),
            "xelab": lambda cmd, cwd: (0, "INFO: built snapshot\n", ""),
            "xsim": lambda cmd, cwd: (0, self.xsim_stdout, ""),
            "vivado": self.vivado_ok,
            "vitis-run": lambda cmd, cwd: (0, "INFO: csim start\nQUALITY_T6_CSIM_PASS 32 vectors\n", ""),
            "v++": self.vpp_ok,
        }

    def __call__(self, command, **kwargs):
        assert isinstance(command, list) and not kwargs.get("shell"), command
        name = Path(command[0]).name
        if name == "bash":
            assert command[:2] == ["/usr/bin/bash", "-c"] and "settings64.sh" in command[2], command
            self.env_sources.append(command[2])
            return subprocess.CompletedProcess(command, 0, b"FAKE_XILINX=1\0PATH=/fake/bin\0no-equals\0", b"")
        if name in {"xvlog", "xelab", "xsim", "vivado"}:
            assert command[0] == str(self.vivado / "bin" / name), command
        if name not in self.handlers:
            raise AssertionError(f"unexpected command {command}")
        self.calls.append({"tool": name, "command": list(command), **kwargs})
        rc, out, err = self.handlers[name](command, Path(kwargs["cwd"]))
        return subprocess.CompletedProcess(command, rc, out, err)

    def tools(self) -> list[str]:
        return [call["tool"] for call in self.calls]

    @staticmethod
    def vivado_run(command, rc=0, marker=True, report=True, log_lines=(), write_log=True, stdout_extra=""):
        tcl = Path(command[command.index("-source") + 1]).read_text()
        report_path = Path(re.search(r"report_utilization -file \{(.+)\}", tcl).group(1))
        puts = re.search(r"puts (\S+)", tcl).group(1)
        if report:
            report_path.write_text("| Slice LUTs | 12 |\n")
        if write_log:
            Path(command[command.index("-log") + 1]).write_text("synth_design\n" + "".join(f"{l}\n" for l in log_lines))
        return rc, (f"{puts}\n" if marker else "") + stdout_extra, ""

    def vivado_ok(self, command, cwd):
        return self.vivado_run(command)

    @staticmethod
    def vpp_ok(command, cwd):
        report = Path(command[command.index("--work_dir") + 1]) / "hls/syn/report/invert32_csynth.rpt"
        report.parent.mkdir(parents=True)
        report.write_text("== Performance Estimates\n")
        return 0, "INFO: csynth done\n", ""


class ExecutorCase(unittest.TestCase):
    def setUp(self) -> None:
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()
        self.output = self.root / "output/QUALITY_MODEL_VALIDATION"
        self.output.mkdir(parents=True)
        self.vivado = self.root / "fake-xilinx/Vivado"
        self.fake = FakeTools(self.vivado)
        for patcher in (patch.object(executor, "OUTPUT", self.output),
                        patch.object(executor, "VIVADO", self.vivado),
                        patch.object(executor.subprocess, "run", self.fake)):
            patcher.start()
            self.addCleanup(patcher.stop)

    def workspace(self, task: str, variant: str = "V1", model: str = "fixture") -> Path:
        public = REAL_CORPUS / task / variant / "public"
        ws = self.output / "session" / "samples" / model / task / variant / "workspace"
        ws.mkdir(parents=True)
        shutil.copy2(public / "TASK_SPEC.md", ws / "TASK_SPEC.md")
        if task in {"T4", "T5", "T7"}:
            shutil.copytree(public / "rtl", ws / "rtl")
        elif task == "T6":
            shutil.copytree(public / "src", ws / "src")
            shutil.copy2(public / "hls_config.cfg", ws / "hls_config.cfg")
        else:
            (ws / "rtl").mkdir()
            shutil.copy2(public / "rtl/axi_regs.sv", ws / "rtl/axi_regs.sv")
        if task == "T3":
            (ws / "sim").mkdir()
            shutil.copy2(public / "sim/tb_axi_regs.sv", ws / "sim/tb_axi_regs.sv")
        return ws

    def corpus_copy(self, task: str, variant: str = "V1") -> Path:
        corpus = self.root / "corpus"
        shutil.copytree(REAL_CORPUS / task / variant, corpus / task / variant)
        patcher = patch.object(executor, "CORPUS", corpus)
        patcher.start()
        self.addCleanup(patcher.stop)
        return corpus / task / variant

    def run_main(self, *args: str) -> tuple[int, dict]:
        stdout = io.StringIO()
        with patch.object(sys, "argv", ["quality_task_executor.py", *args]), redirect_stdout(stdout):
            rc = executor.main()
        return rc, json.loads(stdout.getvalue().splitlines()[-1])


class ArgumentAndCorpusTests(ExecutorCase):
    def test_task_variant_allowlist_rejected_before_corpus_or_tools(self) -> None:
        ws = self.workspace("T1")
        with patch.object(executor, "_verify_variant") as verify:
            for task, variant in [("T9", "V1"), ("T0", "V1"), ("t1", "V1"), ("T1", "V4"), ("T1", "v1"), ("T1", "")]:
                with self.subTest(task=task, variant=variant), \
                        self.assertRaisesRegex(executor.FixtureError, "allowlist"):
                    executor.validate(task, variant, ws, 1)
        verify.assert_not_called()
        self.assertEqual(self.fake.calls, [])

    def test_attempt_must_be_one_to_three_and_creates_nothing(self) -> None:
        ws = self.workspace("T1")
        for attempt in (0, 4, -1):
            with self.subTest(attempt=attempt), self.assertRaisesRegex(executor.FixtureError, "attempt must be 1..3"):
                executor.validate("T1", "V1", ws, attempt)
        self.assertFalse((ws / "runs").exists())
        self.assertEqual(self.fake.calls, [])
        self.assertEqual(self.fake.env_sources, [])

    def test_every_frozen_variant_passes_integrity_check(self) -> None:
        for task in sorted(executor.VALID_TASKS):
            for variant in sorted(executor.VALID_TASKS[task]):
                with self.subTest(task=task, variant=variant):
                    folder = REAL_CORPUS / task / variant
                    files = executor._verify_variant(task, variant)
                    self.assertEqual(files, json.loads((folder / "SHA256SUMS.json").read_text())["files"])
                    self.assertNotIn("SHA256SUMS.json", files)
                    self.assertTrue(any(name.startswith("private/") for name in files))

    def test_tampered_extra_or_missing_corpus_file_is_rejected(self) -> None:
        folder = self.corpus_copy("T1")
        tb = folder / "private/tb_axi_regs.sv"
        original = tb.read_bytes()
        cases = [
            ("modified", lambda: tb.write_bytes(original + b"// tamper\n"), lambda: tb.write_bytes(original)),
            ("extra", lambda: (folder / "private/extra.sv").write_text("x"), lambda: (folder / "private/extra.sv").unlink()),
            ("missing", lambda: tb.unlink(), lambda: tb.write_bytes(original)),
        ]
        executor._verify_variant("T1", "V1")
        for label, damage, repair in cases:
            with self.subTest(label):
                damage()
                with self.assertRaisesRegex(executor.FixtureError, "integrity mismatch for T1/V1"):
                    executor.validate("T1", "V1", self.workspace("T1", model=label), 1)
                repair()
        executor._verify_variant("T1", "V1")
        self.assertEqual(self.fake.calls, [])

    def test_workspace_must_be_real_child_of_output(self) -> None:
        ws = self.workspace("T1")
        self.assertEqual(executor._safe_workspace(ws), ws)
        self.assertEqual(executor._safe_workspace(ws / ".." / "workspace"), ws)
        outside = self.root / "elsewhere"
        outside.mkdir()
        link = self.output / "session" / "escape"
        link.symlink_to(outside, target_is_directory=True)
        sibling = self.output.parent / "QUALITY_MODEL_VALIDATION-evil"
        sibling.mkdir()
        for bad in (outside, self.output, self.output / ".." / ".." / "elsewhere", link, sibling):
            with self.subTest(str(bad)), self.assertRaisesRegex(executor.FixtureError, "isolated child"):
                executor._safe_workspace(bad)
        with self.assertRaises(FileNotFoundError):
            executor._safe_workspace(self.output / "missing")
        with self.assertRaisesRegex(executor.FixtureError, "isolated child"):
            executor.validate("T1", "V1", outside, 1)
        self.assertEqual(self.fake.calls, [])

    def test_vivado_env_merges_sourced_settings_into_environment(self) -> None:
        with patch.dict(executor.os.environ, {"KEEP_ME": "1"}):
            env = executor._vivado_env()
        self.assertEqual(env["FAKE_XILINX"], "1")
        self.assertEqual(env["PATH"], "/fake/bin")
        self.assertEqual(env["KEEP_ME"], "1")
        self.assertIn(str(self.vivado / "settings64.sh"), self.fake.env_sources[0])

    def test_main_exit_codes_and_json_shapes(self) -> None:
        ws = self.workspace("T1")
        with self.assertRaises(SystemExit) as raised, redirect_stdout(io.StringIO()), \
                patch.object(sys, "stderr", io.StringIO()), \
                patch.object(sys, "argv", ["x", "--task", "T9", "--variant", "V1", "--workspace", str(ws), "--attempt", "1"]):
            executor.main()
        self.assertEqual(raised.exception.code, 2)

        rc, payload = self.run_main("--task", "T1", "--variant", "V9", "--workspace", str(ws), "--attempt", "1")
        self.assertEqual((rc, payload["status"]), (2, "HARNESS_INVALID"))
        self.assertTrue(payload["error"].startswith("FixtureError: "))

        rc, payload = self.run_main("--task", "T1", "--variant", "V1", "--workspace", str(ws), "--attempt", "1")
        self.assertEqual((rc, payload["status"]), (0, "PASS"))
        self.fake.xsim_stdout = "ERROR: mismatch\n"
        rc, payload = self.run_main("--task", "T1", "--variant", "V1", "--workspace", str(ws), "--attempt", "2")
        self.assertEqual((rc, payload["status"]), (1, "FAIL"))
        rc, payload = self.run_main("--task", "T1", "--variant", "V1", "--workspace", str(ws), "--attempt", "2")
        self.assertEqual(rc, 2)
        self.assertIn("FileExistsError", payload["error"])


class AxiRegsValidatorTests(ExecutorCase):
    """T1, T2 and T8 share the hidden-testbench plus synthesis path."""

    def test_t1_pass_builds_fixed_commands_and_writes_result(self) -> None:
        ws = self.workspace("T1")
        source = ws / "rtl/axi_regs.sv"
        private = REAL_CORPUS / "T1/V1/private"
        result = executor.validate("T1", "V1", ws, 2)
        run = ws / "runs/attempt-2"
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(self.fake.tools(), ["xvlog", "xelab", "xsim", "vivado"])
        xvlog, xelab, xsim, vivado = (call["command"] for call in self.fake.calls)
        self.assertEqual(xvlog[1:], ["--sv", "-work", "xil_defaultlib", str(source), str(private / "tb_axi_regs.sv")])
        self.assertEqual(xelab[1:], ["xil_defaultlib.tb_axi_regs", "-s", "quality_attempt_2"])
        self.assertEqual(xsim[1:], ["quality_attempt_2", "-runall"])
        self.assertEqual([c["timeout"] for c in self.fake.calls], [180, 180, 180, 600])
        self.assertEqual([c["cwd"] for c in self.fake.calls], [run, run, run, run / "synthesis"])
        self.assertTrue(all(c["env"]["FAKE_XILINX"] == "1" for c in self.fake.calls))
        self.assertEqual(vivado[1:5], ["-mode", "batch", "-notrace", "-source"])
        tcl = (run / "synthesis/fixed_synth.tcl").read_text()
        self.assertIn(f"read_verilog -sv {{{source}}}", tcl)
        self.assertIn("synth_design -top axi_regs -part xc7s100fgga676-2", tcl)
        self.assertIn(f"report_utilization -file {{{run / 'synthesis/utilization.rpt'}}}", tcl)

        self.assertEqual(json.loads((run / "result.json").read_text()), result)
        self.assertEqual(result["xsim"]["terminal_marker"], "QUALITY_T1_PASS")
        self.assertEqual(result["xsim"]["xsim"]["exit_code"], 0)
        log = run / "xsim.log"
        self.assertEqual(result["xsim"]["xsim"]["log"], str(log))
        self.assertEqual(result["xsim"]["xsim"]["log_sha256"], sha(log))
        self.assertEqual(result["synthesis"]["latch_diagnostics"], [])
        self.assertTrue(result["synthesis"]["pass_marker"])
        self.assertEqual(result["source_sha256_before"], sha(source))
        self.assertTrue(result["source_unchanged_during_validation"])
        self.assertEqual(result["hidden_assets_sha256"], {"testbench": sha(private / "tb_axi_regs.sv"),
                                                          "reference": sha(private / "reference_axi_regs.sv")})
        self.assertEqual(set(result["corpus_files_sha256"]),
                         {"private/reference_axi_regs.sv", "private/tb_axi_regs.sv", "public/TASK_SPEC.md", "public/rtl/axi_regs.sv"})

    def test_task_specific_terminal_markers(self) -> None:
        cases = [("T1", "QUALITY_T1_PASS", "PASS"), ("T2", "QUALITY_T1_PASS", "PASS"),
                 ("T8", "QUALITY_T8_PASS", "PASS"), ("T8", "QUALITY_T1_PASS", "FAIL"),
                 ("T1", "QUALITY_T8_PASS", "FAIL"), ("T1", "  QUALITY_T1_PASS", "FAIL"),
                 ("T1", "ERROR: QUALITY_T1_PASS not reached", "FAIL"),
                 ("T1", "QUALITY_T1_PASS checks=42", "PASS")]
        for i, (task, line, status) in enumerate(cases):
            with self.subTest(task=task, line=line):
                self.fake.calls.clear()
                self.fake.xsim_stdout = f"INFO: start\n{line}\n$finish called\n"
                result = executor.validate(task, "V1", self.workspace(task, model=f"m{i}"), 1)
                self.assertEqual(result["status"], status)
                self.assertEqual(result["xsim"]["pass"], status == "PASS")
                if status == "FAIL":
                    self.assertIsNone(result["xsim"]["terminal_marker"])
                    self.assertEqual(result["synthesis"], {"pass": False, "status": "SKIPPED_UNTIL_XSIM_PASS"})
                    self.assertNotIn("vivado", self.fake.tools())

    def test_tool_failure_stops_chain_and_skips_synthesis(self) -> None:
        for i, failing in enumerate(("xvlog", "xelab", "xsim")):
            with self.subTest(failing=failing):
                self.fake.calls.clear()
                self.fake.handlers[failing] = lambda cmd, cwd: (1, "QUALITY_T1_PASS\n", "ERROR: [VRFC 10-1] syntax")
                ws = self.workspace("T1", model=f"m{i}")
                result = executor.validate("T1", "V1", ws, 1)
                self.fake.handlers = FakeTools(self.vivado).handlers
                order = ["xvlog", "xelab", "xsim"]
                self.assertEqual(self.fake.tools(), order[:order.index(failing) + 1])
                self.assertEqual(result["status"], "FAIL")
                self.assertFalse(result["xsim"]["pass"])
                self.assertEqual(result["xsim"][failing]["exit_code"], 1)
                self.assertIn("syntax", (ws / f"runs/attempt-1/{failing}.log").read_text())
                self.assertEqual(result["synthesis"]["status"], "SKIPPED_UNTIL_XSIM_PASS")

    def test_synthesis_failures_and_latch_detection(self) -> None:
        run = FakeTools.vivado_run
        cases = {
            "latch_infer": (lambda c, w: run(c, log_lines=["WARNING: [Synth 8-327] inferring latch for variable 'q_reg'"]), 1),
            "latch_inferred": (lambda c, w: run(c, log_lines=["WARNING: Latch inferred for signal data"]), 1),
            "no_report": (lambda c, w: run(c, report=False), 0),
            "no_marker": (lambda c, w: run(c, marker=False), 0),
            "nonzero": (lambda c, w: run(c, rc=1), 0),
            "stdout_latch_without_log": (lambda c, w: run(c, write_log=False, stdout_extra="inferred latch q\n"), 1),
        }
        for i, (label, (handler, latch_count)) in enumerate(cases.items()):
            with self.subTest(label):
                self.fake.handlers["vivado"] = handler
                result = executor.validate("T1", "V1", self.workspace("T1", model=f"m{i}"), 1)
                self.assertTrue(result["xsim"]["pass"])
                self.assertEqual(result["status"], "FAIL")
                self.assertFalse(result["synthesis"]["pass"])
                self.assertEqual(len(result["synthesis"]["latch_diagnostics"]), latch_count)
        self.fake.handlers["vivado"] = lambda c, w: run(c, log_lines=["INFO: no latches found; latch count 0"])
        self.assertEqual(executor.validate("T1", "V1", self.workspace("T1", model="clean"), 1)["status"], "PASS")

    def test_missing_symlinked_source_and_rerun_of_attempt(self) -> None:
        ws = self.workspace("T1")
        source = ws / "rtl/axi_regs.sv"
        real = ws / "real.sv"
        source.rename(real)
        with self.assertRaisesRegex(executor.FixtureError, "missing or a symlink"):
            executor.validate("T1", "V1", ws, 1)
        source.symlink_to(real)
        with self.assertRaisesRegex(executor.FixtureError, "missing or a symlink"):
            executor.validate("T1", "V1", ws, 1)
        source.unlink()
        real.rename(source)
        (ws / "runs/attempt-1").mkdir(parents=True)
        with self.assertRaises(FileExistsError):
            executor.validate("T1", "V1", ws, 1)
        self.assertEqual(self.fake.calls, [])
        self.assertEqual(self.fake.env_sources, [])

    def test_environment_failure_is_harness_invalid(self) -> None:
        ws = self.workspace("T1")

        def broken_settings(command, **kwargs):
            raise subprocess.CalledProcessError(1, command)
        with patch.object(executor.subprocess, "run", broken_settings):
            rc, payload = self.run_main("--task", "T1", "--variant", "V1", "--workspace", str(ws), "--attempt", "3")
        self.assertEqual((rc, payload["status"]), (2, "HARNESS_INVALID"))
        self.assertIn("CalledProcessError", payload["error"])

    def test_source_change_during_validation_is_recorded_and_fails(self) -> None:
        # Regression: T1/T2/T8 used to PASS a source edited while validators ran.
        default_xelab = self.fake.handlers["xelab"]
        for task in ("T1", "T2", "T8"):
            with self.subTest(task=task):
                self.fake.handlers["xelab"] = default_xelab
                self.fake.xsim_stdout = ("QUALITY_T8_PASS" if task == "T8" else "QUALITY_T1_PASS") + "\n"
                ws = self.workspace(task)
                self.assertEqual(executor.validate(task, "V1", ws, 1)["status"], "PASS")
                source = ws / "rtl/axi_regs.sv"

                def edit_source(cmd, cwd):
                    source.write_text(source.read_text() + "// concurrent edit\n")
                    return 0, "", ""
                self.fake.handlers["xelab"] = edit_source
                result = executor.validate(task, "V1", ws, 2)
                self.assertFalse(result["source_unchanged_during_validation"])
                self.assertNotEqual(result["source_sha256_before"], result["source_sha256_after"])
                self.assertTrue(result["xsim"]["pass"])
                self.assertEqual(result["status"], "FAIL")


class ToolTimeoutTests(ExecutorCase):
    """Regression: a tool timeout used to raise and become HARNESS_INVALID, stopping the pilot."""

    @staticmethod
    def hang(cmd, cwd):
        raise subprocess.TimeoutExpired(cmd, 180)

    def test_simulation_timeout_is_a_failed_step_with_a_written_result(self) -> None:
        self.fake.handlers["xsim"] = self.hang
        ws = self.workspace("T1")
        rc, payload = self.run_main("--task", "T1", "--variant", "V1", "--workspace", str(ws), "--attempt", "1")
        self.assertEqual((rc, payload["status"]), (1, "FAIL"))
        self.assertEqual((payload["xsim"]["xsim"]["exit_code"], payload["xsim"]["xsim"]["timed_out"]), (None, True))
        self.assertEqual(payload["synthesis"]["status"], "SKIPPED_UNTIL_XSIM_PASS")
        self.assertIn("QUALITY_TOOL_TIMEOUT: xsim exceeded 180s", (ws / "runs/attempt-1/xsim.log").read_text())
        self.assertTrue((ws / "runs/attempt-1/result.json").is_file())

    def test_compile_timeout_stops_later_tools(self) -> None:
        # returncode None must not be mistaken for success by the step loop.
        self.fake.handlers["xvlog"] = self.hang
        result = executor.validate("T1", "V1", self.workspace("T1"), 1)
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(self.fake.tools(), ["xvlog"])

    def test_hls_csim_timeout_fails_with_a_timeout_diagnostic(self) -> None:
        self.fake.handlers["vitis-run"] = self.hang
        result = executor.validate("T6", "V1", self.workspace("T6"), 1)
        self.assertEqual(result["status"], "FAIL")
        self.assertIsNone(result["csim"]["exit_code"])
        self.assertEqual(result["csim_diagnostic"], "Fixed C simulation exceeded its time limit.")


class T3MutationTests(ExecutorCase):
    def setUp(self) -> None:
        super().setUp()
        self.correct_stdout = "\n".join(T3_SCENARIOS + ["QUALITY_T3_PASS"]) + "\n"
        self.mutant_outcome = {name: (0, "Error: assertion failed\n$finish\n") for name in T3_MUTANTS}
        self.mutant_compile_rc = {}
        self.fake.handlers["xsim"] = self.xsim
        self.fake.handlers["xvlog"] = self.xvlog

    def xvlog(self, cmd, cwd):
        return self.mutant_compile_rc.get(Path(cmd[4]).name, 0), "", ""

    def xsim(self, cmd, cwd):
        if cwd.name == "correct":
            if self.correct_stdout == "HANG":
                raise subprocess.TimeoutExpired(cmd, 180)
            return 0, self.correct_stdout, ""
        dut = Path(next(c for c in self.fake.calls if c["tool"] == "xvlog" and c["cwd"] == cwd)["command"][4])
        if self.mutant_outcome[dut.name] == "HANG":
            raise subprocess.TimeoutExpired(cmd, 180)
        return self.mutant_outcome[dut.name][0], self.mutant_outcome[dut.name][1], ""

    def test_mutant_that_hangs_is_not_a_catch(self) -> None:
        # The spec requires a finite watchdog; a testbench that hangs on a mutant has not caught it.
        self.mutant_outcome[T3_MUTANTS[0]] = "HANG"
        result = executor.validate("T3", "V1", self.workspace("T3"), 1)
        self.assertEqual(result["status"], "FAIL")
        first = result["mutation_detection"]["mutants"][0]
        self.assertEqual((first["detected"], first["failure_kind"]), (False, "TOOL_TIMEOUT"))
        self.assertEqual(result["mutation_detection"]["detected"], 4)

    def test_correct_run_that_hangs_fails_instead_of_aborting(self) -> None:
        self.correct_stdout = "HANG"
        ws = self.workspace("T3")
        rc, payload = self.run_main("--task", "T3", "--variant", "V1", "--workspace", str(ws), "--attempt", "1")
        self.assertEqual((rc, payload["status"]), (1, "FAIL"))
        self.assertFalse(payload["xsim"]["pass"])
        self.assertIn("QUALITY_TOOL_TIMEOUT", (ws / "runs/attempt-1/correct/xsim.log").read_text())

    def test_pass_requires_scenarios_and_catches_every_mutant(self) -> None:
        ws = self.workspace("T3")
        tb = ws / "sim/tb_axi_regs.sv"
        result = executor.validate("T3", "V1", ws, 1)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(len(T3_MUTANTS), 5)
        self.assertEqual(self.fake.tools(), ["xvlog", "xelab", "xsim"] * 6)
        correct = ws / "runs/attempt-1/correct"
        hidden = ws / ".quality-hidden/attempt-1"
        self.assertEqual([c["cwd"] for c in self.fake.calls[::3]],
                         [correct] + [hidden / f"mutation-{i}" for i in range(1, 6)])
        compiled = [Path(c["command"][4]).name for c in self.fake.calls[::3]]
        self.assertEqual(compiled, ["axi_regs.sv"] + T3_MUTANTS)
        self.assertTrue(all(c["command"][5] == str(tb) for c in self.fake.calls[::3]))
        self.assertEqual(self.fake.calls[1]["command"][1:], ["xil_defaultlib.tb_axi_regs", "-s", "quality_t3_mutation"])
        self.assertEqual(result["mutation_detection"]["detected"], 5)
        self.assertEqual([m["id"] for m in result["mutation_detection"]["mutants"]], ["M1", "M2", "M3", "M4", "M5"])
        self.assertEqual(result["xsim"]["scenario_markers_observed"], sorted(T3_SCENARIOS))
        self.assertEqual(result["synthesis"], {"pass": True, "status": "NOT_REQUIRED_FOR_T3"})
        self.assertEqual(json.loads((hidden / "result.json").read_text()), result)

        public = json.loads((ws / "runs/attempt-1/result.json").read_text())
        self.assertEqual(public["mutation_detection"], {"detected": 5, "total": 5})
        self.assertEqual(public["xsim"]["scenario_marker_count"], 9)
        self.assertNotIn("corpus_files_sha256", public)
        public_text = (ws / "runs/attempt-1/result.json").read_text()
        for secret in [*T3_MUTANTS, "private/", "mutants"]:
            self.assertNotIn(secret, public_text)

    def test_missing_scenario_marker_fails_even_with_terminal_pass(self) -> None:
        self.correct_stdout = "\n".join(T3_SCENARIOS[:-1] + ["QUALITY_T3_PASS"]) + "\n"
        result = executor.validate("T3", "V1", self.workspace("T3"), 1)
        self.assertTrue(result["xsim"]["pass"])
        self.assertEqual(result["status"], "FAIL")
        self.assertNotIn(T3_SCENARIOS[-1], result["xsim"]["scenario_markers_observed"])

    def test_scenario_markers_must_be_exact_lines(self) -> None:
        self.correct_stdout = "\n".join([f"{m} " for m in T3_SCENARIOS] + ["QUALITY_T3_PASS"]) + "\n"
        result = executor.validate("T3", "V1", self.workspace("T3"), 1)
        self.assertEqual((result["status"], result["xsim"]["scenario_markers_observed"]), ("FAIL", []))

    def test_surviving_mutant_or_compile_failure_is_not_detection(self) -> None:
        cases = {
            "survivor": lambda: self.mutant_outcome.__setitem__(T3_MUTANTS[0], (0, "QUALITY_T3_PASS\n")),
            "compile_error": lambda: self.mutant_compile_rc.__setitem__(T3_MUTANTS[1], 1),
        }
        for i, (label, arrange) in enumerate(cases.items()):
            with self.subTest(label):
                self.reset_outcomes()
                arrange()
                result = executor.validate("T3", "V1", self.workspace("T3", model=f"m{i}"), 1)
                self.assertTrue(result["xsim"]["pass"])
                self.assertEqual(result["status"], "FAIL")
                self.assertEqual(result["mutation_detection"]["detected"], 4)
                missed = [m for m in result["mutation_detection"]["mutants"] if not m["detected"]]
                self.assertEqual(len(missed), 1)
                if label == "compile_error":
                    self.assertEqual((missed[0]["compile_exit"], missed[0]["elab_exit"]), (1, None))

    def reset_outcomes(self) -> None:
        self.mutant_outcome = {name: (0, "Error: assertion failed\n") for name in T3_MUTANTS}
        self.mutant_compile_rc = {}

    def test_failure_kinds_watchdog_nonzero_and_silent_exit(self) -> None:
        self.mutant_outcome[T3_MUTANTS[0]] = (0, "ERROR: Watchdog timeout at 10000 ns\n")
        self.mutant_outcome[T3_MUTANTS[1]] = (1, "FATAL: $fatal called\n")
        self.mutant_outcome[T3_MUTANTS[2]] = (0, "")
        result = executor.validate("T3", "V1", self.workspace("T3"), 1)
        kinds = [m["failure_kind"] for m in result["mutation_detection"]["mutants"]]
        self.assertEqual(kinds, ["WATCHDOG"] + ["SIMULATION_OR_ASSERTION"] * 4)
        self.assertEqual(result["status"], "PASS")

    def test_changed_dut_spec_or_missing_testbench_rejected_before_tools(self) -> None:
        for i, (relative, action) in enumerate([("rtl/axi_regs.sv", "edit"), ("TASK_SPEC.md", "edit"),
                                                ("sim/tb_axi_regs.sv", "delete"), ("rtl/axi_regs.sv", "delete")]):
            with self.subTest(relative=relative, action=action):
                ws = self.workspace("T3", model=f"m{i}")
                target = ws / relative
                target.unlink() if action == "delete" else target.write_text(target.read_text() + "\n// edit\n")
                with self.assertRaises(executor.FixtureError):
                    executor.validate("T3", "V1", ws, 1)
                self.assertFalse((ws / "runs").exists())
        self.assertEqual(self.fake.calls, [])

    def test_empty_mutant_set_cannot_pass(self) -> None:
        folder = self.corpus_copy("T3")
        shutil.rmtree(folder / "private/mutants")
        result = executor._validate_t3("V1", self.workspace("T3"), 1, {})
        self.assertEqual(result["mutation_detection"], {"detected": 0, "total": 0, "mutants": []})
        self.assertEqual(result["status"], "FAIL")

    def test_testbench_changed_during_validation_fails(self) -> None:
        ws = self.workspace("T3")
        original = self.xsim

        def editing_xsim(cmd, cwd):
            if cwd.name == "mutation-5":
                (ws / "sim/tb_axi_regs.sv").write_text("// replaced\n")
            return original(cmd, cwd)
        self.fake.handlers["xsim"] = editing_xsim
        result = executor.validate("T3", "V1", ws, 1)
        self.assertEqual(result["mutation_detection"]["detected"], 5)
        self.assertFalse(result["source_unchanged_during_validation"])
        self.assertEqual(result["status"], "FAIL")


class MultiFileAndSynthesisTaskTests(ExecutorCase):
    def test_t4_and_t7_compile_allowlisted_files_with_hidden_testbench(self) -> None:
        for task in ("T4", "T7"):
            with self.subTest(task=task):
                self.fake.calls.clear()
                self.fake.xsim_stdout = f"{SIM_MARKER[task]} all vectors\n"
                ws = self.workspace(task)
                result = executor.validate(task, "V1", ws, 3)
                private = REAL_CORPUS / task / "V1/private/tb_calc_top.sv"
                self.assertEqual(result["status"], "PASS")
                self.assertEqual(self.fake.tools(), ["xvlog", "xelab", "xsim"])
                self.assertEqual(self.fake.calls[0]["command"][4:],
                                 [str(ws / "rtl" / n) for n in ("alu_pkg.sv", "alu.sv", "calc_top.sv")] + [str(private)])
                self.assertEqual(self.fake.calls[1]["command"][1:], ["xil_defaultlib.tb_calc_top", "-s", "quality_t4_attempt_3"])
                self.assertEqual(self.fake.calls[2]["command"][1:], ["quality_t4_attempt_3", "-runall"])
                self.assertEqual(result["synthesis"]["status"], "NOT_REQUIRED_FOR_T4")
                self.assertEqual(result["hidden_assets_sha256"], {"testbench": sha(private)})
                self.assertEqual(set(result["source_sha256_before"]), {"alu_pkg.sv", "alu.sv", "calc_top.sv"})
                self.assertEqual(json.loads((ws / "runs/attempt-3/result.json").read_text()), result)

    def test_t7_rejects_t4_marker_and_t4_rejects_t7_marker(self) -> None:
        for task, wrong in (("T7", "QUALITY_T4_PASS"), ("T4", "QUALITY_T7_PASS")):
            with self.subTest(task=task):
                self.fake.xsim_stdout = f"{wrong}\n"
                result = executor.validate(task, "V1", self.workspace(task), 1)
                self.assertEqual(result["status"], "FAIL")
                self.assertIsNone(result["xsim"]["terminal_marker"])

    def test_t4_missing_file_and_edit_during_validation(self) -> None:
        ws = self.workspace("T4", model="missing")
        (ws / "rtl/alu.sv").unlink()
        with self.assertRaisesRegex(executor.FixtureError, "T4 allowlisted"):
            executor.validate("T4", "V1", ws, 1)
        self.assertEqual(self.fake.calls, [])

        ws = self.workspace("T4", model="edited")
        self.fake.xsim_stdout = "QUALITY_T4_PASS\n"
        self.fake.handlers["xelab"] = lambda c, w: ((ws / "rtl/alu.sv").write_text("// edit\n"), (0, "", ""))[1]
        result = executor.validate("T4", "V1", ws, 1)
        self.assertTrue(result["xsim"]["pass"])
        self.assertFalse(result["source_unchanged_during_validation"])
        self.assertEqual(result["status"], "FAIL")

    def test_t5_requires_simulation_and_latch_free_synthesis(self) -> None:
        self.fake.xsim_stdout = "QUALITY_T5_PASS\n"
        ws = self.workspace("T5")
        result = executor.validate("T5", "V1", ws, 1)
        run = ws / "runs/attempt-1"
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(self.fake.tools(), ["xvlog", "xelab", "xsim", "vivado"])
        self.assertEqual(self.fake.calls[1]["command"][1:], ["xil_defaultlib.tb_mux_math", "-s", "quality_t5_1"])
        self.assertEqual(self.fake.calls[3]["cwd"], run / "synthesis")
        self.assertEqual(self.fake.calls[3]["timeout"], 600)
        tcl = (run / "synthesis/fixed_synth.tcl").read_text()
        self.assertIn("synth_design -top mux_math -part xc7s100fgga676-2", tcl)
        self.assertIn("puts QUALITY_T5_SYNTH_PASS", tcl)
        self.assertTrue(result["synthesis"]["pass_marker"])
        self.assertEqual(json.loads((run / "result.json").read_text()), result)

        self.fake.handlers["vivado"] = lambda c, w: FakeTools.vivado_run(
            c, log_lines=["WARNING: [Synth 8-327] inferring latch for variable 'y_reg' [mux_math.sv:9]"])
        result = executor.validate("T5", "V1", ws, 2)
        self.assertTrue(result["xsim"]["pass"])
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(len(result["synthesis"]["latch_diagnostics"]), 1)

    def test_t5_simulation_failure_still_fails_even_when_synthesis_is_clean(self) -> None:
        self.fake.xsim_stdout = "ERROR: y mismatch sel=5\n"
        result = executor.validate("T5", "V1", self.workspace("T5"), 1)
        self.assertEqual(result["status"], "FAIL")
        self.assertFalse(result["xsim"]["pass"])
        self.assertTrue(result["synthesis"]["pass"])
        self.assertIn("vivado", self.fake.tools())


class T6HlsTests(ExecutorCase):
    def test_t6_pass_isolates_private_testbench_and_publishes_safe_result(self) -> None:
        ws = self.workspace("T6")
        result = executor.validate("T6", "V1", ws, 1)
        hidden = ws / ".quality-hidden/attempt-1"
        project = hidden / "project"
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(self.fake.tools(), ["vitis-run", "v++"])
        self.assertIn("Vitis/settings64.sh", self.fake.env_sources[0])
        csim, synth = (c["command"] for c in self.fake.calls)
        cfg = str(project / "hls_config.cfg")
        self.assertEqual(csim, ["vitis-run", "--mode", "hls", "--csim", "--config", cfg, "--work_dir", str(hidden / "csim")])
        self.assertEqual(synth, ["v++", "-c", "--mode", "hls", "--part", "xc7s100fgga676-2", "--config", cfg,
                                 "--work_dir", str(hidden / "csynth")])
        self.assertEqual([c["timeout"] for c in self.fake.calls], [900, 1200])
        self.assertEqual({c["cwd"] for c in self.fake.calls}, {project})
        self.assertEqual((project / "hls_config.cfg").read_text(),
                         (ws / "hls_config.cfg").read_text() + "tb.file=src/testbench.cpp\n")
        self.assertEqual(sha(project / "src/testbench.cpp"), sha(REAL_CORPUS / "T6/V1/private/testbench.cpp"))
        self.assertEqual(result["csynth"]["reports"], ["csynth/hls/syn/report/invert32_csynth.rpt"])
        self.assertTrue(result["csim"]["terminal_marker"].startswith("QUALITY_T6_CSIM_PASS"))
        self.assertIsNone(result["csim_diagnostic"])
        self.assertEqual(json.loads((hidden / "result.json").read_text()), result)
        public = json.loads((ws / "runs/attempt-1/result.json").read_text())
        self.assertEqual(public, {"task": "T6", "variant": "V1", "attempt": 1, "status": "PASS",
                                  "csim": {"pass": True, "terminal_marker": result["csim"]["terminal_marker"]},
                                  "csim_diagnostic": None, "csynth": {"pass": True, "report_count": 1},
                                  "source_unchanged_during_validation": True})
        self.assertFalse(any("testbench" in p.name for p in ws.rglob("*") if ".quality-hidden" not in p.parts))

    def test_t6_csim_or_csynth_failures(self) -> None:
        cases = {
            "csim_no_marker": ("vitis-run", lambda c, w: (0, "Mismatch at vector 3\n", ""), "csim"),
            "csim_nonzero": ("vitis-run", lambda c, w: (1, "QUALITY_T6_CSIM_PASS\n", "error"), "csim"),
            "csynth_no_report": ("v++", lambda c, w: (0, "done\n", ""), "csynth"),
            "csynth_nonzero": ("v++", lambda c, w: (1, "", "ERROR"), "csynth"),
        }
        for i, (label, (tool, handler, stage)) in enumerate(cases.items()):
            with self.subTest(label):
                self.fake.handlers = FakeTools(self.vivado).handlers
                self.fake.handlers[tool] = handler
                result = executor.validate("T6", "V1", self.workspace("T6", model=f"m{i}"), 1)
                self.assertEqual(result["status"], "FAIL")
                self.assertFalse(result[stage]["pass"])
                other = "csynth" if stage == "csim" else "csim"
                self.assertTrue(result[other]["pass"])
                self.assertEqual(result["csim_diagnostic"] is None, stage != "csim")

    def test_t6_missing_or_symlinked_inputs_rejected_before_tools(self) -> None:
        ws = self.workspace("T6", model="missing")
        (ws / "hls_config.cfg").unlink()
        with self.assertRaisesRegex(executor.FixtureError, "T6 public source/config"):
            executor.validate("T6", "V1", ws, 1)
        ws = self.workspace("T6", model="symlink")
        src = ws / "src/invert32.cpp"
        src.rename(ws / "real.cpp")
        src.symlink_to(ws / "real.cpp")
        with self.assertRaisesRegex(executor.FixtureError, "T6 public source/config"):
            executor.validate("T6", "V1", ws, 1)
        self.assertEqual(self.fake.calls, [])
        self.assertFalse((ws / ".quality-hidden").exists())


if __name__ == "__main__":
    unittest.main()
