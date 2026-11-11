#!/usr/bin/env python3
"""Offline tests for the quality-corpus fixture validator.

A copy of the committed corpus is placed in a system temp dir and every
writable path (ROOT, CORPUS, FIXTURE_ROOT) is redirected there.  Vivado
(xvlog/xelab/xsim/vivado), ``settings64.sh`` and quality_task_executor.py are
replaced by an in-process fake ``subprocess.run`` that returns canned results;
any other command fails the test.  No EDA tool, model or network is touched.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import validate_quality_corpus as validate

REPO = Path(__file__).resolve().parents[1]
COMMITTED = REPO / "docs/LOCAL_MODEL_LAB/quality-corpus/v2"
VARIANTS = ["V1", "V2", "V3"]
FAKE_VIVADO = Path("/nonexistent/fixture/Vivado")
MARKER_RE = re.compile(r'\$display\("(QUALITY_[A-Za-z0-9_]+_PASS)')
T4_FIXED = "alu u_alu(.a(a), .b(b), .op(op), .y(result), .valid(valid));"


def tree(root: Path) -> dict[str, bytes]:
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in sorted(root.rglob("*")) if p.is_file()}


def completed(command, returncode=0, stdout="", stderr=""):
    return subprocess.CompletedProcess(command, returncode, stdout, stderr)


class FakeTools:
    """Stand-in for subprocess.run covering Vivado tools and the task executor.

    The fake simulator is an oracle: a hidden testbench "passes" only when it
    is compiled together with the exact reference RTL frozen for it, in which
    case every ``QUALITY_*_PASS`` marker the testbench displays is printed.
    """

    def __init__(self, corpus: Path, sim_mode: str = "oracle", latch_line: str | None = None,
                 synth_report: bool = True, synth_rc: int = 0, xvlog_rc=0, drop_markers=(),
                 executor=None):
        self.corpus, self.sim_mode, self.latch_line = corpus, sim_mode, latch_line
        self.synth_report, self.synth_rc, self.xvlog_rc = synth_report, synth_rc, xvlog_rc
        self.drop_markers, self.executor = set(drop_markers), executor or self.oracle_executor
        self.calls: list[tuple[list[str], dict]] = []
        self.compiled: dict[str, tuple[str, str]] = {}
        self.synthesized: list[str] = []
        self.executor_calls: list[dict] = []
        self.golden: dict[str, str] = {}
        for task in ("T1", "T2", "T8"):
            for v in VARIANTS:
                private = corpus / task / v / "private"
                self.golden[(private / "tb_axi_regs.sv").read_text()] = (private / "reference_axi_regs.sv").read_text()
        for v in VARIANTS:
            folder = corpus / "T3" / v
            self.golden[(folder / "private/reference_tb_axi_regs.sv").read_text()] = (folder / "public/rtl/axi_regs.sv").read_text()

    def __call__(self, command, **kwargs):
        self.calls.append((list(command), kwargs))
        if command[0] == sys.executable and command[1].endswith("quality_task_executor.py"):
            return self.run_executor(command, kwargs)
        if Path(command[0]).parent.parent == FAKE_VIVADO:
            return getattr(self, "tool_" + Path(command[0]).name)(command, kwargs)
        raise AssertionError(f"unexpected subprocess in offline test: {command!r}")

    def tool_xvlog(self, command, kwargs):
        rtl, tb = Path(command[-2]).read_text(), Path(command[-1]).read_text()
        self.compiled[str(kwargs["cwd"])] = (rtl, tb)
        rc = self.xvlog_rc(rtl, tb) if callable(self.xvlog_rc) else self.xvlog_rc
        return completed(command, rc, "INFO: [VRFC 10-2263] Analyzing SystemVerilog file\n",
                         "ERROR: [VRFC 10-4982] fixture compile error\n" if rc else "")

    def tool_xelab(self, command, kwargs):
        return completed(command, 0, "INFO: built simulation snapshot quality_fixture\n")

    def tool_xsim(self, command, kwargs):
        rtl, tb = self.compiled[str(kwargs["cwd"])]
        if self.sim_mode == "always_pass" or self.golden.get(tb) == rtl:
            lines = []
            for marker in MARKER_RE.findall(tb):
                if marker in self.drop_markers:
                    continue
                lines.append(marker if "SCENARIO" in marker else f"{marker} checks=32")
            return completed(command, 0, "\n".join(lines) + "\n")
        return completed(command, 0, "Fatal: R response changed or mismatch addr=00\n")

    def tool_vivado(self, command, kwargs):
        tcl = Path(command[command.index("-source") + 1]).read_text()
        self.synthesized.append(Path(re.search(r"read_verilog -sv \{(.+)\}", tcl).group(1)).read_text())
        report = Path(re.search(r"report_utilization -file \{(.+)\}", tcl).group(1))
        if self.synth_report:
            report.write_text("| Slice LUTs | 42 |\n")
        log = "INFO: [Synth 8-7075] Helper process launched\n"
        if self.latch_line:
            log += self.latch_line + "\n"
        Path(command[command.index("-log") + 1]).write_text(log)
        return completed(command, self.synth_rc, "QUALITY_T1_SYNTH_PASS\n" if self.synth_rc == 0 else "")

    def run_executor(self, command, kwargs):
        args = dict(zip(command[2::2], command[3::2]))
        workspace = Path(args["--workspace"])
        record = {"task": args["--task"], "variant": args["--variant"], "workspace": workspace,
                  "attempt": int(args["--attempt"]), "files": sorted(tree(workspace)), "kwargs": kwargs}
        self.executor_calls.append(record)
        rc, stdout, stderr = self.executor(record["task"], record["variant"], workspace, record["attempt"])
        return completed(command, rc, stdout, stderr)

    def oracle_executor(self, task, variant, workspace, attempt):
        if task in {"T4", "T7"}:
            ok = T4_FIXED in (workspace / "rtl/calc_top.sv").read_text()
            payload = {"xsim": {"pass": ok, "terminal_marker": f"QUALITY_{task}_PASS checks=5" if ok else None},
                       "synthesis": {"pass": True, "status": "NOT_REQUIRED_FOR_T4"}}
        elif task == "T5":
            ok = "default" in (workspace / "rtl/mux_math.sv").read_text()
            payload = {"xsim": {"pass": ok, "terminal_marker": "QUALITY_T5_PASS checks=8" if ok else None},
                       "synthesis": {"pass": ok, "latch_diagnostics": [] if ok else
                                     ["WARNING: [Synth 8-327] inferring latch for variable 'y_reg'"]}}
        elif task == "T6":
            ok = "return ~input;" in (workspace / "src/invert32.cpp").read_text()
            payload = {"csim": {"pass": ok, "terminal_marker": "QUALITY_T6_CSIM_PASS checks=4" if ok else None},
                       "csynth": {"pass": True, "report_count": 1}}
        elif task == "T8":
            reference = (self.corpus / "T8" / variant / "private/reference_axi_regs.sv").read_text()
            ok = (workspace / "rtl/axi_regs.sv").read_text() == reference
            payload = {"xsim": {"pass": ok, "terminal_marker": "QUALITY_T8_PASS checks=32" if ok else None},
                       "synthesis": {"pass": True} if ok else {"pass": False, "status": "SKIPPED_UNTIL_XSIM_PASS"}}
        else:
            raise AssertionError(task)
        payload = {"task": task, "variant": variant, "attempt": attempt, "status": "PASS" if ok else "FAIL", **payload}
        return (0 if ok else 1), "fixture executor banner\n" + json.dumps(payload) + "\n", ""


class Sandbox:
    """Temp ROOT holding a copy of the committed corpus, with tools faked."""

    def __init__(self, case: unittest.TestCase, chdir: bool = True, **tool_options):
        temp = tempfile.TemporaryDirectory(prefix="validate-quality-corpus-")
        case.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()
        case.assertFalse(str(self.root).startswith(str(REPO)))
        self.corpus = self.root / "docs/LOCAL_MODEL_LAB/quality-corpus/v2"
        shutil.copytree(COMMITTED, self.corpus, ignore=shutil.ignore_patterns("CORPUS_PROGRESS.json"))
        self.fixture_root = self.root / "output/QUALITY_MODEL_VALIDATION/fixture-test/fixtures"
        self.result_root = self.fixture_root / "runs" / "fixture-run"
        self.result_root.mkdir(parents=True)
        self.tools = FakeTools(self.corpus, **tool_options)
        self.vivado_env = Mock(return_value={"PATH": "/fixture/bin"})
        for name, value in (("ROOT", self.root), ("CORPUS", self.corpus), ("VIVADO", FAKE_VIVADO),
                            ("FIXTURE_ROOT", self.fixture_root), ("vivado_env", self.vivado_env)):
            patcher = patch.object(validate, name, value)
            patcher.start()
            case.addCleanup(patcher.stop)
        patcher = patch.object(validate.subprocess, "run", self.tools)
        patcher.start()
        case.addCleanup(patcher.stop)
        self.corpus_snapshot = tree(self.corpus)
        if chdir:
            # run_xsim records logs relative to ROOT and validate_t3 reopens them
            # relative to the cwd, so the real CLI is run from the repo root.
            previous = os.getcwd()
            os.chdir(self.root)
            case.addCleanup(os.chdir, previous)

    def assert_corpus_untouched(self, case: unittest.TestCase) -> None:
        case.assertEqual(tree(self.corpus), self.corpus_snapshot)


class ToolWrapperTests(unittest.TestCase):
    def test_vivado_env_sources_settings_and_merges_null_separated_env(self) -> None:
        vivado = Path("/opt/Xilinx dir/Vivado")
        proc = completed([], 0, b"FOO=bar\0XILINX_VIVADO=/x\0garbage\0MULTI=a=b\0BAD=\xff\0")
        with patch.object(validate, "VIVADO", vivado), \
             patch.object(validate.subprocess, "run", return_value=proc) as run, \
             patch.dict(os.environ, {"KEEP_ME": "1"}, clear=False):
            env = validate.vivado_env()
        command = run.call_args.args[0]
        self.assertEqual(command[:2], ["/usr/bin/bash", "-c"])
        self.assertEqual(command[2], "source '/opt/Xilinx dir/Vivado/settings64.sh' >/dev/null && /usr/bin/env -0")
        self.assertEqual(run.call_args.kwargs, {"capture_output": True, "timeout": 30, "check": True})
        self.assertEqual((env["FOO"], env["XILINX_VIVADO"], env["MULTI"], env["KEEP_ME"]), ("bar", "/x", "a=b", "1"))
        self.assertEqual(env["BAD"], "\ufffd")
        self.assertNotIn("garbage", env)

    def test_run_xsim_runs_three_tools_and_requires_terminal_marker(self) -> None:
        box = Sandbox(self)
        private = box.corpus / "T1/V1/private"
        work = box.root / "output/work"
        result = validate.run_xsim(private / "reference_axi_regs.sv", private / "tb_axi_regs.sv", work)
        self.assertEqual([Path(c[0]).name for c, _ in box.tools.calls], ["xvlog", "xelab", "xsim"])
        self.assertEqual(box.tools.calls[0][0][1:4], ["--sv", "-work", "xil_defaultlib"])
        self.assertEqual(box.tools.calls[1][0][1], "xil_defaultlib.tb_axi_regs")
        for _, kwargs in box.tools.calls:
            self.assertEqual((kwargs["cwd"], kwargs["env"], kwargs["timeout"]), (work, {"PATH": "/fixture/bin"}, 180))
        self.assertTrue(result["pass"])
        self.assertEqual(result["terminal_marker"], "QUALITY_T1_PASS checks=32")
        for tool in ("xvlog", "xelab", "xsim"):
            self.assertEqual(result[tool]["exit_code"], 0)
            log = box.root / result[tool]["log"]
            self.assertEqual(result[tool]["log"], f"output/work/{tool}.log")
            self.assertEqual(result[tool]["log_sha256"], hashlib.sha256(log.read_bytes()).hexdigest())
        wrong_marker = validate.run_xsim(private / "reference_axi_regs.sv", private / "tb_axi_regs.sv",
                                         box.root / "output/work2", "QUALITY_T3_PASS")
        self.assertFalse(wrong_marker["pass"])
        self.assertIsNone(wrong_marker["terminal_marker"])

    def test_run_xsim_stops_after_first_failing_tool(self) -> None:
        box = Sandbox(self, xvlog_rc=1)
        private = box.corpus / "T1/V1/private"
        result = validate.run_xsim(private / "reference_axi_regs.sv", private / "tb_axi_regs.sv", box.root / "output/w")
        self.assertEqual(len(box.tools.calls), 1)
        self.assertEqual(set(result), {"xvlog", "terminal_marker"})
        self.assertIsNone(result["terminal_marker"])
        self.assertFalse(result.get("pass", False))
        self.assertIn("fixture compile error", (box.root / "output/w/xvlog.log").read_text())

    def run_synth(self, **options) -> tuple[dict, Sandbox]:
        box = Sandbox(self, **options)
        rtl = box.corpus / "T1/V2/private/reference_axi_regs.sv"
        result = validate.run_synthesis(rtl, box.root / "output/synth")
        tcl = (box.root / "output/synth/fixed_synth.tcl").read_text()
        self.assertIn(f"read_verilog -sv {{{rtl}}}", tcl)
        self.assertIn("synth_design -top axi_regs -part xc7s100fgga676-2", tcl)
        self.assertEqual(box.tools.calls[0][1]["timeout"], 600)
        return result, box

    def test_run_synthesis_pass_requires_marker_report_exit_zero_and_no_latch(self) -> None:
        result, _ = self.run_synth()
        self.assertTrue(result["pass"])
        self.assertEqual(result["utilization_report"], "output/synth/utilization.rpt")
        self.assertEqual(result["latch_diagnostics"], [])
        result, _ = self.run_synth(latch_line="WARNING: [Synth 8-327] inferred latch for variable 'x_reg'")
        self.assertFalse(result["pass"])
        self.assertEqual(len(result["latch_diagnostics"]), 1)
        result, _ = self.run_synth(synth_report=False)
        self.assertFalse(result["pass"])
        self.assertIsNone(result["utilization_report"])
        result, _ = self.run_synth(synth_rc=1)
        self.assertFalse(result["pass"])
        self.assertFalse(result["pass_marker"])

    def test_run_synthesis_rejects_vivado_inferring_latch_wording(self) -> None:
        # Regression: the latch check used to match only "inferred latch" /
        # "latch inferred"; Vivado's Synth 8-327 says "inferring latch", which
        # quality_task_executor.py's T5 regex already caught.
        result, _ = self.run_synth(latch_line="WARNING: [Synth 8-327] inferring latch for variable 'regs_reg'")
        self.assertFalse(result["pass"])

    def test_run_mutation_matches_frozen_t3_mutants_and_reports_detection(self) -> None:
        box = Sandbox(self)
        t3_names = {"reset-value": "wrong-reset-value", "ignore-wstrb": "ignore-wstrb",
                    "same-cycle-aw-w": "same-cycle-aw-w", "unstable-read-response": "unstable-read-response"}
        for variant in VARIANTS:
            reference = box.corpus / "T1" / variant / "private/reference_axi_regs.sv"
            tb = box.corpus / "T1" / variant / "private/tb_axi_regs.sv"
            for mutation, t3_name in t3_names.items():
                with self.subTest(variant=variant, mutation=mutation):
                    work = box.root / "output/mut" / variant / mutation
                    row = validate.run_mutation(reference, tb, work, mutation)
                    mutant = (work / "axi_regs.sv").read_text()
                    self.assertEqual(mutant, (box.corpus / "T3" / variant / "private/mutants" / f"{t3_name}.sv").read_text())
                    self.assertEqual(row["mutation"], mutation)
                    self.assertTrue(row["detected"])
                    self.assertFalse(row["result"]["pass"])
        with patch.object(validate, "run_xsim", return_value={"pass": True}):
            row = validate.run_mutation(reference, tb, box.root / "output/mut/x", "ignore-wstrb")
        self.assertFalse(row["detected"])
        with self.assertRaises(ValueError):
            validate.run_mutation(reference, tb, box.root / "output/mut/y", "no-such-mutation")
        inert = box.root / "inert.sv"
        inert.write_text("module axi_regs; endmodule\n")
        for mutation in t3_names:
            with self.assertRaisesRegex(RuntimeError, "mutation did not alter source"):
                validate.run_mutation(inert, tb, box.root / "output/mut/z", mutation)
        box.assert_corpus_untouched(self)

    def test_verify_frozen_variant_detects_any_drift(self) -> None:
        box = Sandbox(self)
        folder = box.corpus / "T4/V2"
        validate.verify_frozen_variant(folder)
        target = folder / "public/rtl/calc_top.sv"
        original = target.read_bytes()
        target.write_bytes(original + b" ")
        with self.assertRaisesRegex(RuntimeError, "frozen corpus integrity mismatch"):
            validate.verify_frozen_variant(folder)
        target.write_bytes(original)
        (folder / "private/extra.sv").write_text("")
        with self.assertRaisesRegex(RuntimeError, "integrity mismatch"):
            validate.verify_frozen_variant(folder)
        (folder / "private/extra.sv").unlink()
        target.unlink()
        with self.assertRaisesRegex(RuntimeError, "integrity mismatch"):
            validate.verify_frozen_variant(folder)
        target.write_bytes(original)
        validate.verify_frozen_variant(folder)
        (folder / "SHA256SUMS.json").unlink()
        with self.assertRaises(FileNotFoundError):
            validate.verify_frozen_variant(folder)


class AxiFixtureFlowTests(unittest.TestCase):
    def test_t1_oracle_baseline_fails_reference_passes_and_all_mutations_detected(self) -> None:
        box = Sandbox(self)
        outcomes = validate.validate_t1(VARIANTS, box.result_root)
        self.assertEqual([(o["task"], o["variant"]) for o in outcomes], [("T1", v) for v in VARIANTS])
        for outcome in outcomes:
            variant = outcome["variant"]
            with self.subTest(variant=variant):
                self.assertTrue(outcome["fixture_pass"])
                self.assertTrue(outcome["baseline_expected_fail"])
                self.assertTrue(outcome["reference_xsim"]["pass"])
                self.assertTrue(outcome["reference_synthesis"]["pass"])
                self.assertEqual([m["mutation"] for m in outcome["mutations"]],
                                 ["reset-value", "ignore-wstrb", "same-cycle-aw-w", "unstable-read-response"])
                self.assertTrue(all(m["detected"] for m in outcome["mutations"]))
                self.assertEqual(outcome["artifacts"], f"output/QUALITY_MODEL_VALIDATION/fixture-test/fixtures/runs/fixture-run/T1/{variant}")
                result_dir = box.root / outcome["artifacts"]
                source = box.corpus / "T1" / variant
                self.assertEqual((result_dir / "baseline/axi_regs.sv").read_bytes(), (source / "public/rtl/axi_regs.sv").read_bytes())
                self.assertEqual((result_dir / "reference/axi_regs.sv").read_bytes(), (source / "private/reference_axi_regs.sv").read_bytes())
        # Synthesis runs once per variant, on the reference only.
        self.assertEqual(box.tools.synthesized, [(box.corpus / "T1" / v / "private/reference_axi_regs.sv").read_text() for v in VARIANTS])
        # 3 variants x (baseline + reference + 4 mutants) x 3 tools + 3 synth runs.
        self.assertEqual(len(box.tools.calls), 3 * 6 * 3 + 3)
        box.assert_corpus_untouched(self)

    def test_t1_rerun_replaces_previous_result_dir(self) -> None:
        box = Sandbox(self)
        validate.validate_t1(["V1"], box.result_root)
        stale = box.result_root / "T1/V1/stale.txt"
        stale.write_text("old")
        self.assertTrue(validate.validate_t1(["V1"], box.result_root)[0]["fixture_pass"])
        self.assertFalse(stale.exists())

    def test_t1_insensitive_simulator_or_latch_fails_fixture(self) -> None:
        box = Sandbox(self, sim_mode="always_pass")
        outcome = validate.validate_t1(["V2"], box.result_root)[0]
        self.assertFalse(outcome["baseline_expected_fail"])
        self.assertFalse(any(m["detected"] for m in outcome["mutations"]))
        self.assertFalse(outcome["fixture_pass"])
        box = Sandbox(self, latch_line="WARNING: latch inferred for regs")
        outcome = validate.validate_t1(["V3"], box.result_root)[0]
        self.assertTrue(outcome["baseline_expected_fail"] and outcome["reference_xsim"]["pass"])
        self.assertFalse(outcome["fixture_pass"])

    def test_t2_oracle_and_refusal_to_reuse_result_dir(self) -> None:
        box = Sandbox(self)
        outcomes = validate.validate_t2(VARIANTS, box.result_root)
        for outcome in outcomes:
            self.assertTrue(outcome["fixture_pass"], outcome["variant"])
            self.assertTrue(outcome["baseline_expected_fail"])
            self.assertNotIn("mutations", outcome)
        self.assertEqual(len(box.tools.synthesized), 3)
        with self.assertRaises(FileExistsError):
            validate.validate_t2(["V1"], box.result_root)
        box.assert_corpus_untouched(self)

    def test_t2_reference_synthesis_failure_fails_fixture(self) -> None:
        box = Sandbox(self, synth_rc=1)
        outcome = validate.validate_t2(["V1"], box.result_root)[0]
        self.assertTrue(outcome["reference_xsim"]["pass"])
        self.assertFalse(outcome["fixture_pass"])

    def test_t3_oracle_requires_markers_and_detects_all_five_mutants(self) -> None:
        box = Sandbox(self)
        outcomes = validate.validate_t3(VARIANTS, box.result_root)
        for outcome in outcomes:
            with self.subTest(variant=outcome["variant"]):
                self.assertTrue(outcome["fixture_pass"])
                self.assertTrue(outcome["baseline_expected_fail"])
                self.assertEqual(outcome["scenario_markers_observed"], outcome["scenario_markers_expected"])
                self.assertEqual(len(outcome["scenario_markers_expected"]), 9)
                self.assertEqual([m["mutation"] for m in outcome["mutants"]],
                                 ["ignore-wstrb", "same-cycle-aw-w", "unstable-read-response",
                                  "unstable-write-response", "wrong-reset-value"])
                self.assertTrue(all(m["detected"] for m in outcome["mutants"]))
        self.assertEqual(box.tools.synthesized, [])
        box.assert_corpus_untouched(self)

    def test_t3_missing_scenario_marker_or_undetected_mutant_fails_fixture(self) -> None:
        box = Sandbox(self, drop_markers={"QUALITY_T3_SCENARIO_consecutive_PASS"})
        outcome = validate.validate_t3(["V1"], box.result_root)[0]
        self.assertTrue(outcome["reference_xsim"]["pass"])
        self.assertNotIn("QUALITY_T3_SCENARIO_consecutive_PASS", outcome["scenario_markers_observed"])
        self.assertFalse(outcome["fixture_pass"])
        box = Sandbox(self, sim_mode="always_pass")
        outcome = validate.validate_t3(["V2"], box.result_root)[0]
        self.assertFalse(outcome["fixture_pass"])
        self.assertFalse(any(m["detected"] for m in outcome["mutants"]))

    def test_t3_reads_reference_log_independently_of_cwd(self) -> None:
        # Regression: the reference XSim log path is stored relative to ROOT and
        # used to be opened against the process cwd.
        box = Sandbox(self, chdir=False)
        elsewhere = tempfile.TemporaryDirectory()
        self.addCleanup(elsewhere.cleanup)
        previous = os.getcwd()
        os.chdir(elsewhere.name)
        self.addCleanup(os.chdir, previous)
        self.assertTrue(validate.validate_t3(["V1"], box.result_root)[0]["fixture_pass"])

    def test_t3_reference_compile_failure_is_reported_not_raised(self) -> None:
        # Regression: run_xsim omits "xsim" when xvlog/xelab fail, and indexing it
        # used to abort the whole run with KeyError instead of failing the fixture.
        box = Sandbox(self, xvlog_rc=lambda rtl, tb: int("QUALITY_T3_SCENARIO" in tb))
        outcome = validate.validate_t3(["V1"], box.result_root)[0]
        self.assertFalse(outcome["fixture_pass"])


class ExecutorFixtureFlowTests(unittest.TestCase):
    def check_executor_calls(self, box: Sandbox, task: str, timeout: int) -> None:
        calls = [c for c in box.tools.executor_calls if c["task"] == task]
        self.assertEqual([(c["variant"], c["attempt"]) for c in calls],
                         [(v, a) for v in VARIANTS for a in (1, 2)])
        for call in calls:
            label = "baseline" if call["attempt"] == 1 else "reference"
            self.assertEqual(call["workspace"], box.result_root / task / call["variant"] / label)
            self.assertEqual(call["kwargs"]["cwd"], box.root)
            self.assertEqual(call["kwargs"]["timeout"], timeout)
            public = sorted(tree(box.corpus / task / call["variant"] / "public"))
            self.assertEqual(call["files"], public, "workspace must hold exactly the public files")
        executor_argv = [c for c, _ in box.tools.calls
                         if c[1].endswith("quality_task_executor.py") and c[c.index("--task") + 1] == task]
        self.assertEqual(executor_argv[0], [sys.executable, str(box.root / "scripts/quality_task_executor.py"),
                                            "--task", task, "--variant", "V1", "--workspace",
                                            str(box.result_root / task / "V1/baseline"), "--attempt", "1"])

    def assert_all_pass(self, outcomes: list[dict], task: str) -> None:
        self.assertEqual([(o["task"], o["variant"]) for o in outcomes], [(task, v) for v in VARIANTS])
        for outcome in outcomes:
            with self.subTest(task=task, variant=outcome["variant"]):
                self.assertTrue(outcome["baseline_expected_fail"])
                self.assertTrue(outcome["reference_expected_pass"])
                self.assertTrue(outcome["fixture_pass"])
                self.assertEqual(outcome["baseline"]["exit_code"], 1)
                self.assertEqual(outcome["reference"]["exit_code"], 0)
                self.assertEqual(outcome["reference"]["result"]["status"], "PASS")

    def test_t4_and_t7_apply_known_repair_only_to_reference_workspace(self) -> None:
        box = Sandbox(self)
        broken = {"V1": ".operation(op)", "V2": "alu_core u_alu", "V3": ".valid_o(valid)"}
        for task in ("T4", "T7"):
            outcomes = validate.validate_t4(VARIANTS, box.result_root, task=task)
            self.assert_all_pass(outcomes, task)
            self.check_executor_calls(box, task, 900)
            for variant in VARIANTS:
                base = (box.result_root / task / variant / "baseline/rtl/calc_top.sv").read_text()
                ref = (box.result_root / task / variant / "reference/rtl/calc_top.sv").read_text()
                self.assertIn(broken[variant], base)
                self.assertNotIn(broken[variant], ref)
                self.assertIn(T4_FIXED, ref)
        box.assert_corpus_untouched(self)

    def test_t7_requires_t7_marker(self) -> None:
        def wrong_marker(task, variant, workspace, attempt):
            ok = attempt == 2
            return (0, json.dumps({"status": "PASS" if ok else "FAIL",
                                   "xsim": {"terminal_marker": "QUALITY_T4_PASS checks=5" if ok else None}}), "")
        box = Sandbox(self, executor=wrong_marker)
        outcome = validate.validate_t4(["V1"], box.result_root, task="T7")[0]
        self.assertTrue(outcome["baseline_expected_fail"])
        self.assertFalse(outcome["reference_expected_pass"])
        self.assertFalse(outcome["fixture_pass"])

    def test_t5_t6_t8_oracles_pass_with_task_specific_timeouts(self) -> None:
        box = Sandbox(self)
        for task, func, timeout, reference_rel, private_rel in (
            ("T5", validate.validate_t5, 900, "rtl/mux_math.sv", "private/reference_mux_math.sv"),
            ("T6", validate.validate_t6, 2400, "src/invert32.cpp", "private/reference_invert32.cpp"),
            ("T8", validate.validate_t8, 1200, "rtl/axi_regs.sv", "private/reference_axi_regs.sv"),
        ):
            outcomes = func(VARIANTS, box.result_root)
            self.assert_all_pass(outcomes, task)
            self.check_executor_calls(box, task, timeout)
            for variant in VARIANTS:
                source = box.corpus / task / variant
                self.assertEqual((box.result_root / task / variant / "reference" / reference_rel).read_bytes(),
                                 (source / private_rel).read_bytes())
                self.assertEqual((box.result_root / task / variant / "baseline" / reference_rel).read_bytes(),
                                 (source / "public" / reference_rel).read_bytes())
        box.assert_corpus_untouched(self)

    def test_baseline_must_fail_for_the_intended_reason(self) -> None:
        def canned(payloads):
            return lambda task, variant, workspace, attempt: (0, json.dumps(payloads[attempt]), "")
        good_t5 = {"status": "PASS", "xsim": {"terminal_marker": "QUALITY_T5_PASS checks=8"}, "synthesis": {"pass": True}}
        # T5 baseline failing without latch diagnostics is not the seeded defect.
        box = Sandbox(self, executor=canned({1: {"status": "FAIL", "xsim": {"terminal_marker": None},
                                                  "synthesis": {"pass": False, "latch_diagnostics": []}}, 2: good_t5}))
        outcome = validate.validate_t5(["V1"], box.result_root)[0]
        self.assertFalse(outcome["baseline_expected_fail"])
        self.assertTrue(outcome["reference_expected_pass"])
        self.assertFalse(outcome["fixture_pass"])
        # T6 baseline must fail C simulation, not merely report FAIL.
        box = Sandbox(self, executor=canned({1: {"status": "FAIL", "csim": {"pass": True}, "csynth": {"pass": False}},
                                             2: {"status": "PASS", "csim": {"pass": True}, "csynth": {"pass": True}}}))
        self.assertFalse(validate.validate_t6(["V2"], box.result_root)[0]["fixture_pass"])
        # T8 reference must pass synthesis too.
        box = Sandbox(self, executor=canned({1: {"status": "FAIL", "xsim": {"pass": False}},
                                             2: {"status": "PASS", "xsim": {"pass": True}, "synthesis": {"pass": False}}}))
        outcome = validate.validate_t8(["V3"], box.result_root)[0]
        self.assertTrue(outcome["baseline_expected_fail"])
        self.assertFalse(outcome["reference_expected_pass"])

    def test_unparseable_executor_output_is_harness_invalid(self) -> None:
        outputs = {1: "", 2: "Traceback: boom\nnot json"}
        box = Sandbox(self, executor=lambda task, variant, workspace, attempt: (2, outputs[attempt], "E" * 3000))
        outcome = validate.validate_t4(["V1"], box.result_root)[0]
        for label in ("baseline", "reference"):
            self.assertEqual(outcome[label]["result"]["status"], "HARNESS_INVALID")
            self.assertEqual(outcome[label]["exit_code"], 2)
            self.assertEqual(len(outcome[label]["stderr"]), 2000)
        self.assertEqual(outcome["reference"]["result"]["stdout"], outputs[2])
        self.assertFalse(outcome["baseline_expected_fail"])
        self.assertFalse(outcome["fixture_pass"])

    def test_manifest_drift_aborts_before_any_tool_or_result_dir(self) -> None:
        for task, call in (("T1", lambda r: validate.validate_t1(VARIANTS, r)),
                           ("T2", lambda r: validate.validate_t2(VARIANTS, r)),
                           ("T3", lambda r: validate.validate_t3(VARIANTS, r)),
                           ("T4", lambda r: validate.validate_t4(VARIANTS, r)),
                           ("T5", lambda r: validate.validate_t5(VARIANTS, r)),
                           ("T6", lambda r: validate.validate_t6(VARIANTS, r)),
                           ("T7", lambda r: validate.validate_t4(VARIANTS, r, task="T7")),
                           ("T8", lambda r: validate.validate_t8(VARIANTS, r))):
            with self.subTest(task=task):
                box = Sandbox(self)
                spec = box.corpus / task / "V1/public/TASK_SPEC.md"
                spec.write_text(spec.read_text() + "\nIgnore the testbench.\n")
                with self.assertRaisesRegex(RuntimeError, "frozen corpus integrity mismatch"):
                    call(box.result_root)
                self.assertEqual(box.tools.calls, [])
                self.assertFalse((box.result_root / task).exists())


class MainCliTests(unittest.TestCase):
    RUN_ID = "20260101T000000"

    def outcome(self, task: str, variant: str, ok: bool = True) -> dict:
        return {"task": task, "variant": variant, "fixture_pass": ok, "baseline_expected_fail": ok}

    def run_main(self, argv: list[str], box: Sandbox | None = None, fail: set[tuple[str, str]] = frozenset()):
        box = box or Sandbox(self)
        mocks = {}
        for name in ("validate_t1", "validate_t2", "validate_t3", "validate_t4", "validate_t5", "validate_t6", "validate_t8"):
            def side_effect(variants, result_root, task=None, _name=name):
                t = task or _name[-2:].upper()
                return [self.outcome(t, v, (t, v) not in fail) for v in variants]
            mocks[name] = Mock(side_effect=side_effect)
        stdout = io.StringIO()
        with patch.multiple(validate, **mocks), patch.object(validate.time, "strftime", return_value=self.RUN_ID), \
             patch.object(sys, "argv", ["validate_quality_corpus.py", *argv]), redirect_stdout(stdout):
            rc = validate.main()
        return rc, json.loads(stdout.getvalue()), mocks, box

    def test_task_selection_dispatches_only_requested_validators(self) -> None:
        expected = {"T1": "validate_t1", "T2": "validate_t2", "T3": "validate_t3", "T4": "validate_t4",
                    "T5": "validate_t5", "T6": "validate_t6", "T7": "validate_t4", "T8": "validate_t8"}
        for task, name in expected.items():
            with self.subTest(task=task):
                rc, summary, mocks, box = self.run_main(["--task", task])
                self.assertEqual(rc, 0)
                result_root = box.fixture_root / "runs" / self.RUN_ID
                for other, mock in mocks.items():
                    self.assertEqual(mock.call_count, int(other == name), other)
                kwargs = {"task": "T7"} if task == "T7" else {}
                mocks[name].assert_called_once_with(VARIANTS, result_root, **kwargs)
                self.assertEqual([(v["task"], v["variant"]) for v in summary["variants"]], [(task, v) for v in VARIANTS])

    def test_all_runs_every_task_in_order_and_writes_report(self) -> None:
        rc, summary, mocks, box = self.run_main(["--task", "all"])
        self.assertEqual(rc, 0)
        self.assertEqual(mocks["validate_t4"].call_count, 2)
        self.assertEqual([v["task"] for v in summary["variants"][::3]], [f"T{i}" for i in range(1, 9)])
        report_path = box.fixture_root / "runs" / self.RUN_ID / "fixture-results.json"
        self.assertEqual(summary["report"], str(report_path.relative_to(box.root)))
        report = json.loads(report_path.read_text())
        self.assertEqual((report["task"], report["run_id"], report["status"]), ("all", self.RUN_ID, "PASS"))
        self.assertEqual(len(report["variants"]), 24)
        self.assertIsInstance(report["elapsed_seconds"], float)

    def test_any_failed_fixture_makes_status_fail_and_exit_one(self) -> None:
        rc, summary, _, box = self.run_main(["--task", "all"], fail={("T6", "V2")})
        self.assertEqual(rc, 1)
        self.assertEqual(summary["status"], "FAIL")
        report = json.loads((box.root / summary["report"]).read_text())
        self.assertEqual([(v["task"], v["variant"]) for v in report["variants"] if not v["fixture_pass"]], [("T6", "V2")])

    def test_invalid_or_missing_task_is_usage_error_without_side_effects(self) -> None:
        for argv in ([], ["--task", "T9"], ["--task", "t1"]):
            with self.subTest(argv=argv):
                box = Sandbox(self)
                with patch.object(sys, "argv", ["validate_quality_corpus.py", *argv]), \
                     redirect_stdout(io.StringIO()), patch("sys.stderr", io.StringIO()):
                    with self.assertRaises(SystemExit) as caught:
                        validate.main()
                self.assertEqual(caught.exception.code, 2)
                self.assertEqual([p.name for p in (box.fixture_root / "runs").iterdir()], ["fixture-run"])
                self.assertEqual(box.tools.calls, [])

    def test_same_run_id_never_overwrites_previous_evidence(self) -> None:
        box = Sandbox(self)
        self.run_main(["--task", "T1"], box=box)
        report = box.fixture_root / "runs" / self.RUN_ID / "fixture-results.json"
        before = report.read_bytes()
        with self.assertRaises(FileExistsError):
            self.run_main(["--task", "T2"], box=box)
        self.assertEqual(report.read_bytes(), before)

    def test_end_to_end_all_with_fake_tools_summarizes_every_fixture(self) -> None:
        box = Sandbox(self)
        stdout = io.StringIO()
        with patch.object(validate.time, "strftime", return_value=self.RUN_ID), \
             patch.object(sys, "argv", ["validate_quality_corpus.py", "--task", "all"]), redirect_stdout(stdout):
            rc = validate.main()
        summary = json.loads(stdout.getvalue())
        self.assertEqual(rc, 0)
        self.assertEqual(summary["status"], "PASS")
        rows = {(v["task"], v["variant"]): v for v in summary["variants"]}
        self.assertEqual(len(rows), 24)
        for (task, variant), row in rows.items():
            with self.subTest(task=task, variant=variant):
                self.assertTrue(row["baseline_failed"])
                self.assertTrue(row["reference_xsim"])
                expected_synth = {"T3": None, "T4": None, "T7": None}.get(task, True)
                self.assertEqual(row["reference_synthesis"], expected_synth)
                total = {"T1": 4, "T3": 5}.get(task, 0)
                self.assertEqual((row["mutations_detected"], row["mutations_total"]), (total, total))
        report = json.loads((box.root / summary["report"]).read_text())
        self.assertTrue(all(v["fixture_pass"] for v in report["variants"]))
        box.assert_corpus_untouched(self)
        written = [p for p in box.root.rglob("*") if p.is_file() and not p.is_relative_to(box.corpus)]
        self.assertTrue(all(p.is_relative_to(box.fixture_root) for p in written))

    def test_end_to_end_drift_aborts_without_report(self) -> None:
        box = Sandbox(self)
        target = box.corpus / "T5/V3/private/tb_mux_math.sv"
        target.write_text(target.read_text().replace("expected=8'h0a", "expected=8'h0b"))
        with patch.object(validate.time, "strftime", return_value=self.RUN_ID), \
             patch.object(sys, "argv", ["validate_quality_corpus.py", "--task", "T5"]), redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(RuntimeError, "T5/V3"):
                validate.main()
        self.assertFalse((box.fixture_root / "runs" / self.RUN_ID / "fixture-results.json").exists())


class ExecutorPayloadTests(unittest.TestCase):
    @staticmethod
    def proc(stdout: str) -> subprocess.CompletedProcess:
        return subprocess.CompletedProcess([], 0, stdout, "err" * 1000)

    def test_object_on_last_line_is_returned(self) -> None:
        self.assertEqual(validate.executor_payload(self.proc('noise\n{"status": "PASS"}')), {"status": "PASS"})

    def test_anything_but_a_json_object_is_harness_invalid(self) -> None:
        # Regression: a valid non-object line such as `1` used to raise AttributeError on .get.
        for stdout in ("", "not json", "1", "[]", '"PASS"', "null"):
            with self.subTest(stdout=stdout):
                payload = validate.executor_payload(self.proc(stdout))
                self.assertEqual(payload["status"], "HARNESS_INVALID")
                self.assertEqual(len(payload["stderr"]), 2000)


if __name__ == "__main__":
    unittest.main()
