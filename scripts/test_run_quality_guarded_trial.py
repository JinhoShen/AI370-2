#!/usr/bin/env python3
"""Offline tests for the guarded quality-trial supervisor.

Workspaces are materialised from a temp copy of the frozen corpus with fake
runner files, and every module path that points into the repo is redirected to
the system temp dir.  Popen, journalctl, health checks, /proc readings, disk
usage, process-group kills, the clock and sleeps are mocked.  No model, model
server, LocalAgent child, EDA tool, systemd unit or network endpoint is used.
"""
from __future__ import annotations

import io
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import unittest
import urllib.error
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import prepare_quality_workspace as builder
import run_quality_guarded_trial as trial

REPO_CORPUS = Path(__file__).resolve().parents[1] / "docs/LOCAL_MODEL_LAB/quality-corpus/v1"
RUNNERS = ("scripts/quality_task_executor.py", "scripts/quality_local_agent.py", "scripts/local_agent.py",
           "scripts/run_quality_guarded_trial.py", "scripts/run_quality_pilot.py")
GIB_KIB = 1024 * 1024
MIB = 1024 * 1024
SERVER_PID = 424242
MODEL = "fixture-model"
# Captured before any patching so wrappers can delegate to the real behaviour.
REAL_RUN = subprocess.run
REAL_POPEN = subprocess.Popen
REAL_READ_BYTES = Path.read_bytes
REAL_READ_TEXT = Path.read_text
REAL_ITERDIR = Path.iterdir
# Hermetic git: ignore user/system config (hooks, signing, templates).
GIT_ENV = {"GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_COUNT": "1",
           "GIT_CONFIG_KEY_0": "init.defaultBranch", "GIT_CONFIG_VALUE_0": "main"}


def pages(nbytes: int) -> int:
    return nbytes // trial.PAGE_SIZE


def start(case: unittest.TestCase, patcher):
    value = patcher.start()
    case.addCleanup(patcher.stop)
    return value


def clear_main_state() -> None:
    # main() keeps audit timestamps on the function object; isolate each test.
    for name in ("last_integrity_check", "last_audit"):
        if hasattr(trial.main, name):
            delattr(trial.main, name)


class PreparedWorkspace:
    """A real prepared workspace under a fake ROOT in the system temp dir."""

    def __init__(self, case: unittest.TestCase, task: str = "T1", variant: str = "V1"):
        temp = tempfile.TemporaryDirectory(prefix="guarded-trial-test-")
        case.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()
        for relative in RUNNERS:
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(f"# fake runner fixture: {relative}\n")
        corpus = self.root / "docs/LOCAL_MODEL_LAB/quality-corpus/v1"
        shutil.copytree(REPO_CORPUS / task / variant, corpus / task / variant)
        start(case, patch.dict(os.environ, GIT_ENV))
        with patch.object(builder, "ROOT", self.root), patch.object(builder, "CORPUS", corpus), \
                patch.object(builder, "OUTPUT", self.root / "output/QUALITY_MODEL_VALIDATION"):
            self.protocol = builder.prepare(task, variant, "unit", MODEL)
        start(case, patch.object(trial, "ROOT", self.root))
        self.workspace = Path(self.protocol["workspace"])
        self.protocol_path = self.workspace.parent / "protocol.json"
        self.corpus_dir = corpus / task / variant
        case.assertTrue(self.workspace.is_relative_to(self.root))
        case.assertTrue(self.root.is_relative_to(Path(tempfile.gettempdir()).resolve()))

    def config(self, **overrides) -> dict:
        value = {"task": self.protocol["task"], "variant": self.protocol["variant"], "model": MODEL,
                 "workspace": str(self.workspace), "editable_paths": self.protocol["editable_paths"], "cycle": "unit"}
        value.update(overrides)
        return value


class FakeChild:
    def __init__(self, harness: "MainHarness", command, kwargs):
        self.harness, self.command, self.kwargs = harness, command, kwargs
        self.pid, self.returncode, self.wait_calls = 7000, None, 0
        kwargs["stdout"].write("".join(line + "\n" for line in harness.child_stdout))

    def poll(self):
        if self.returncode is None and self.harness.child_exit_tick is not None \
                and self.harness.tick >= self.harness.child_exit_tick:
            self.returncode = self.harness.child_returncode
        return self.returncode

    def wait(self, timeout=None):
        self.wait_calls += 1
        if self.returncode is None:
            raise AssertionError("main() waited on a child that was neither finished nor terminated")
        return self.returncode


class FakeResponse:
    def __init__(self, status: int):
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class MainHarness:
    """Drive main() with a fake clock; each time.sleep(1) is one tick."""

    def __init__(self, case: unittest.TestCase, prepared: PreparedWorkspace | None = None, legacy: bool = False):
        self.case, self.prepared = case, prepared
        if prepared is None:
            temp = tempfile.TemporaryDirectory(prefix="guarded-trial-legacy-")
            case.addCleanup(temp.cleanup)
            self.root = Path(temp.name).resolve()
            start(case, patch.object(trial, "ROOT", self.root))
        else:
            self.root = prepared.root
        self.legacy = legacy
        self.output = self.root / "guarded-output"
        self.model_path = self.root / f"{MODEL}.gguf"
        self.model_path.write_bytes(b"not a model")
        self.config_path = self.root / "controller.json"
        self.config = {"rep": 1} if legacy else prepared.config()
        self.extra_args: list[str] = []
        self.tick, self.clock, self.hooks = 0, 1000.0, {}
        self.mem = lambda t: {"MemTotal": 48 * GIB_KIB, "MemAvailable": 40 * GIB_KIB,
                              "SwapTotal": 8 * GIB_KIB, "SwapFree": 8 * GIB_KIB}
        self.vm = lambda t: {"pswpin": 0, "pswpout": 0}
        self.psi = lambda t: 0.0
        self.health = lambda t: 200
        self.disk_free = 500 * 1024**3
        self.journal = lambda t: subprocess.CompletedProcess([], 0, "kernel: nothing to see\n", "")
        self.proc_cmdlines = {SERVER_PID: b"llama-server\0-m\0/models/" + self.model_path.name.encode() + b"\0"}
        self.child_stdout = ["agent progress", json.dumps({"status": "DONE", "calls": 3})]
        self.child_exit_tick: int | None = 2
        self.child_returncode = 0
        self.children: list[FakeChild] = []
        self.terminated: list[tuple[FakeChild, str]] = []
        self.journal_calls: list[tuple[list[str], dict]] = []
        self.health_calls: list[tuple[str, int]] = []
        self.sleeps = 0
        clear_main_state()
        case.addCleanup(clear_main_state)
        start(case, patch.object(Path, "read_bytes", lambda path: self._read_bytes(path)))
        start(case, patch.object(trial, "meminfo", side_effect=lambda: dict(self.mem(self.tick))))
        start(case, patch.object(trial, "vmstat", side_effect=lambda: dict(self.vm(self.tick))))
        start(case, patch.object(trial, "psi_full_avg10", side_effect=lambda: self.psi(self.tick)))
        start(case, patch.object(trial.time, "monotonic", side_effect=lambda: self.clock))
        start(case, patch.object(trial.time, "sleep", side_effect=self._sleep))
        start(case, patch.object(trial.urllib.request, "urlopen", side_effect=self._urlopen))
        start(case, patch.object(trial.subprocess, "Popen", side_effect=self._popen))
        start(case, patch.object(trial.subprocess, "run", side_effect=self._run))
        start(case, patch.object(trial.shutil, "disk_usage", side_effect=lambda p: SimpleNamespace(free=self.disk_free)))
        start(case, patch.object(trial, "terminate_trial", side_effect=self._terminate))
        self.killpg = start(case, patch.object(trial.os, "killpg"))
        self.kill = start(case, patch.object(trial.os, "kill"))

    # Mocks ----------------------------------------------------------------
    def _read_bytes(self, path: Path) -> bytes:
        text = str(path)
        if text.startswith("/proc/"):
            parts = text.split("/")
            if len(parts) == 4 and parts[3] == "cmdline" and parts[2].isdigit() and int(parts[2]) in self.proc_cmdlines:
                return self.proc_cmdlines[int(parts[2])]
            raise FileNotFoundError(text)
        return REAL_READ_BYTES(path)

    def _sleep(self, seconds) -> None:
        self.case.assertEqual(seconds, 1)
        self.sleeps += 1
        self.tick += 1
        self.clock += seconds
        hook = self.hooks.get(self.tick)
        if hook:
            hook()

    def _urlopen(self, url, timeout=None):
        self.health_calls.append((url, timeout))
        status = self.health(self.tick)
        if isinstance(status, BaseException):
            raise status
        return FakeResponse(status)

    def _popen(self, command, *args, **kwargs):
        if command[0] == "git":  # subprocess.run() for the real git checks goes through Popen.
            return REAL_POPEN(command, *args, **kwargs)
        child = FakeChild(self, command, kwargs)
        self.children.append(child)
        return child

    def _run(self, command, **kwargs):
        if command[0] == "journalctl":
            self.journal_calls.append((command, kwargs))
            value = self.journal(self.tick)
            if isinstance(value, BaseException):
                raise value
            return value
        if command[0] == "git":
            self.case.assertTrue(Path(kwargs["cwd"]).resolve().is_relative_to(Path(tempfile.gettempdir()).resolve()))
            return REAL_RUN(command, **kwargs)
        raise AssertionError(f"unexpected subprocess.run: {command}")

    def _terminate(self, child, workspace) -> None:
        self.terminated.append((child, workspace))
        if child.returncode is None:
            child.returncode = -signal.SIGINT

    # Driver ---------------------------------------------------------------
    def argv(self) -> list[str]:
        args = ["run_quality_guarded_trial.py", "--config", str(self.config_path), "--output", str(self.output),
                "--model", MODEL, "--model-path", str(self.model_path), "--server-pid", str(SERVER_PID)]
        if not self.legacy:
            args.append("--quality-agent")
        return args + self.extra_args

    def run(self) -> int:
        self.config_path.write_text(json.dumps(self.config))
        buffer = io.StringIO()
        with patch.object(sys, "argv", self.argv()), redirect_stdout(buffer):
            code = trial.main()
        self.printed = json.loads(buffer.getvalue().splitlines()[-1])
        return code

    def result(self) -> dict:
        return json.loads((self.output / "guarded-result.json").read_text())

    @property
    def workspace(self) -> str:
        return str(self.prepared.workspace)


# ---------------------------------------------------------------------------
# Harness integrity guards
# ---------------------------------------------------------------------------
class LiveIntegrityGuardTests(unittest.TestCase):
    def setUp(self) -> None:
        self.ws = PreparedWorkspace(self)
        start(self, patch.object(trial.subprocess, "run", side_effect=REAL_RUN))

    def verify(self) -> None:
        trial.verify_live_quality_protocol(self.ws.workspace, json.loads(self.ws.protocol_path.read_text()))

    def test_prepared_protocol_records_every_guarded_input(self) -> None:
        protocol = self.ws.protocol
        self.assertEqual(set(protocol["runner_sha256"]), set(RUNNERS))
        self.assertEqual(protocol["editable_paths"], ["rtl/axi_regs.sv"])
        self.assertEqual(set(protocol["public_inputs_sha256"]), {"TASK_SPEC.md", "rtl/axi_regs.sv"})
        self.assertTrue((self.ws.root / protocol["corpus_manifest"]).is_file())

    def test_clean_workspace_passes(self) -> None:
        self.verify()

    def test_editable_and_run_artifact_writes_are_allowed(self) -> None:
        (self.ws.workspace / "rtl/axi_regs.sv").write_text("// model edit\n")
        (self.ws.workspace / "runs/r1").mkdir(parents=True)
        (self.ws.workspace / "runs/r1/xsim.log").write_text("log\n")
        (self.ws.workspace / ".quality-hidden").mkdir()
        (self.ws.workspace / ".quality-hidden/private_tb.sv").write_text("tb\n")
        self.verify()

    def test_runner_hash_change_is_detected(self) -> None:
        (self.ws.root / "scripts/quality_local_agent.py").write_text("# tampered\n")
        with self.assertRaisesRegex(RuntimeError, "HARNESS_INTEGRITY_GUARD: runner changed: scripts/quality_local_agent.py"):
            self.verify()

    def test_missing_runner_fails_closed(self) -> None:
        (self.ws.root / "scripts/run_quality_pilot.py").unlink()
        with self.assertRaises(OSError):
            self.verify()

    def test_corpus_manifest_change_is_detected(self) -> None:
        manifest = self.ws.root / self.ws.protocol["corpus_manifest"]
        manifest.write_text(manifest.read_text() + "\n")
        with self.assertRaisesRegex(RuntimeError, "HARNESS_INTEGRITY_GUARD: corpus manifest changed"):
            self.verify()

    def test_corpus_asset_change_is_detected(self) -> None:
        (self.ws.corpus_dir / "private/tb_axi_regs.sv").write_text("// weakened hidden testbench\n")
        with self.assertRaisesRegex(RuntimeError, "HARNESS_INTEGRITY_GUARD: corpus asset changed: private/tb_axi_regs.sv"):
            self.verify()

    def test_deleted_corpus_asset_is_detected(self) -> None:
        (self.ws.corpus_dir / "private/reference_axi_regs.sv").unlink()
        with self.assertRaisesRegex(RuntimeError, "corpus asset changed: private/reference_axi_regs.sv"):
            self.verify()

    def test_protected_workspace_input_change_is_detected(self) -> None:
        (self.ws.workspace / "TASK_SPEC.md").write_text("# easier task\n")
        with self.assertRaisesRegex(RuntimeError, "HARNESS_INTEGRITY_GUARD: protected workspace input changed: TASK_SPEC.md"):
            self.verify()

    def test_deleted_protected_workspace_input_is_detected(self) -> None:
        (self.ws.workspace / "TASK_SPEC.md").unlink()
        with self.assertRaisesRegex(RuntimeError, "protected workspace input changed: TASK_SPEC.md"):
            self.verify()

    def test_new_file_outside_allowlist_is_detected(self) -> None:
        (self.ws.workspace / "rtl/helper.sv").write_text("module helper; endmodule\n")
        with self.assertRaisesRegex(RuntimeError, "HARNESS_INTEGRITY_GUARD: workspace write outside allowlist: rtl/helper.sv"):
            self.verify()

    def test_nested_untracked_file_outside_allowlist_is_reported_by_path(self) -> None:
        (self.ws.workspace / "notes/deep").mkdir(parents=True)
        (self.ws.workspace / "notes/deep/scratch.txt").write_text("x\n")
        with self.assertRaisesRegex(RuntimeError, "workspace write outside allowlist: notes/deep/scratch.txt"):
            self.verify()

    def test_lookalike_of_exempt_prefix_is_not_exempt(self) -> None:
        (self.ws.workspace / "runs.txt").write_text("x\n")
        with self.assertRaisesRegex(RuntimeError, "outside allowlist: runs.txt"):
            self.verify()


class LiveIntegrityT3Tests(unittest.TestCase):
    def test_t3_protects_rtl_but_allows_testbench_edit(self) -> None:
        ws = PreparedWorkspace(self, task="T3")
        start(self, patch.object(trial.subprocess, "run", side_effect=REAL_RUN))
        protocol = json.loads(ws.protocol_path.read_text())
        self.assertEqual(protocol["editable_paths"], ["sim/tb_axi_regs.sv"])
        (ws.workspace / "sim/tb_axi_regs.sv").write_text("// stronger tb\n")
        trial.verify_live_quality_protocol(ws.workspace, protocol)
        (ws.workspace / "rtl/axi_regs.sv").write_text("// sneaky dut edit\n")
        with self.assertRaisesRegex(RuntimeError, "protected workspace input changed: rtl/axi_regs.sv"):
            trial.verify_live_quality_protocol(ws.workspace, protocol)


class PreStartProtocolTests(unittest.TestCase):
    def setUp(self) -> None:
        self.ws = PreparedWorkspace(self)
        start(self, patch.object(trial.subprocess, "run", side_effect=REAL_RUN))

    def verify(self, config: dict | None = None, model: str = MODEL) -> None:
        trial.verify_quality_protocol(self.ws.workspace, config or self.ws.config(), model)

    def test_clean_frozen_workspace_passes(self) -> None:
        self.verify()

    def test_config_or_model_mismatch_is_rejected(self) -> None:
        for config, model in ((self.ws.config(task="T2"), MODEL), (self.ws.config(variant="V2"), MODEL),
                              (self.ws.config(), "other-model")):
            with self.subTest(config=config, model=model):
                with self.assertRaisesRegex(SystemExit, "does not match the frozen workspace protocol"):
                    self.verify(config, model)

    def test_public_input_edit_before_start_is_rejected(self) -> None:
        (self.ws.workspace / "rtl/axi_regs.sv").write_text("// pre-solved\n")
        with self.assertRaisesRegex(SystemExit, "frozen public input changed before model start: rtl/axi_regs.sv"):
            self.verify()

    def test_untracked_file_before_start_is_rejected(self) -> None:
        (self.ws.workspace / "hint.txt").write_text("answer\n")
        with self.assertRaisesRegex(SystemExit, "workspace is dirty"):
            self.verify()

    def test_moved_git_baseline_is_rejected(self) -> None:
        REAL_RUN(["git", "commit", "--quiet", "--allow-empty", "-m", "extra"], cwd=self.ws.workspace, check=True)
        with self.assertRaisesRegex(SystemExit, "Git baseline does not match"):
            self.verify()

    def test_corpus_manifest_drift_is_rejected(self) -> None:
        manifest = self.ws.root / self.ws.protocol["corpus_manifest"]
        manifest.write_text(manifest.read_text() + " ")
        with self.assertRaisesRegex(SystemExit, "frozen corpus manifest changed"):
            self.verify()

    def test_runner_drift_is_rejected(self) -> None:
        (self.ws.root / "scripts/run_quality_guarded_trial.py").write_text("# patched\n")
        with self.assertRaisesRegex(SystemExit, "frozen harness changed after workspace preparation: scripts/run_quality_guarded_trial.py"):
            self.verify()

    def test_corpus_asset_drift_is_caught_by_live_check_before_start(self) -> None:
        (self.ws.corpus_dir / "public/TASK_SPEC.md").write_text("changed\n")
        with self.assertRaisesRegex(RuntimeError, "corpus asset changed: public/TASK_SPEC.md"):
            self.verify()


# ---------------------------------------------------------------------------
# /proc readers and process termination
# ---------------------------------------------------------------------------
class ProcReaderTests(unittest.TestCase):
    def fake_proc(self, files: dict[str, str]) -> None:
        def read_text(path, *args, **kwargs):
            if str(path).startswith("/proc/"):
                if str(path) not in files:
                    raise FileNotFoundError(str(path))
                return files[str(path)]
            return REAL_READ_TEXT(path, *args, **kwargs)
        start(self, patch.object(Path, "read_text", read_text))

    def test_meminfo_parses_only_kib_lines(self) -> None:
        self.fake_proc({"/proc/meminfo": "MemTotal:       49152000 kB\nMemAvailable:   1234 kB\n"
                                         "HugePages_Total:       0\nSwapFree:  8 kB\n"})
        self.assertEqual(trial.meminfo(), {"MemTotal": 49152000, "MemAvailable": 1234, "SwapFree": 8})

    def test_vmstat_keeps_only_swap_counters(self) -> None:
        self.fake_proc({"/proc/vmstat": "nr_free_pages 10\npswpin 7\npswpout 9\npgmajfault 3\n"})
        self.assertEqual(trial.vmstat(), {"pswpin": 7, "pswpout": 9})

    def test_psi_reads_full_avg10(self) -> None:
        self.fake_proc({"/proc/pressure/memory": "some avg10=55.00 avg60=1.00 avg300=0.00 total=1\n"
                                                 "full avg10=12.50 avg60=0.40 avg300=0.00 total=2\n"})
        self.assertEqual(trial.psi_full_avg10(), 12.5)

    def test_psi_without_full_line_fails_closed(self) -> None:
        self.fake_proc({"/proc/pressure/memory": "some avg10=1.00 avg60=0.00 avg300=0.00 total=1\n"})
        with self.assertRaisesRegex(RuntimeError, "memory PSI full line unavailable"):
            trial.psi_full_avg10()


class FakeController:
    def __init__(self, running: bool = True, hang: bool = False):
        self.pid, self.running, self.hang, self.waits = 9100, running, hang, []

    def poll(self):
        return None if self.running else 0

    def wait(self, timeout=None):
        self.waits.append(timeout)
        if self.hang and timeout is not None:
            raise subprocess.TimeoutExpired("controller", timeout)
        return -signal.SIGINT


class TerminateTrialTests(unittest.TestCase):
    WS = "/tmp/fixture-session/samples/m/T1/V1/workspace"

    def setUp(self) -> None:
        self.table: dict[str, object] = {
            "1": b"/sbin/init\0splash",
            "200": b"python3\0scripts/quality_local_agent.py\0--workspace\0" + self.WS.encode() + b"\0--task\0T1",
            "201": b"python3\0scripts/quality_local_agent.py\0--workspace\0/tmp/other/workspace",
            "202": PermissionError("denied"),
            "203": b"python3\0local_agent.py\0--workspace\0" + self.WS.encode(),
            "204": b"vim\0" + self.WS.encode() + b"/rtl/axi_regs.sv",
            "205": b"python3\0quality_local_agent.py\0--workspace\0" + self.WS.encode(),
        }

        def iterdir(path):
            if str(path) == "/proc":
                return iter([Path("/proc/self"), *[Path("/proc") / pid for pid in self.table]])
            return REAL_ITERDIR(path)

        def read_bytes(path):
            text = str(path)
            if text.startswith("/proc/"):
                value = self.table.get(text.split("/")[2])
                if value is None or isinstance(value, BaseException):
                    raise value or FileNotFoundError(text)
                return value
            return REAL_READ_BYTES(path)

        def killpg(pid, sig):
            self.kills.append((pid, sig))
            if pid == 205:
                raise ProcessLookupError(pid)

        self.kills: list[tuple[int, int]] = []
        start(self, patch.object(Path, "iterdir", iterdir))
        start(self, patch.object(Path, "read_bytes", read_bytes))
        start(self, patch.object(trial.os, "killpg", side_effect=killpg))
        start(self, patch.object(trial.os, "kill", side_effect=AssertionError("os.kill must not be used")))

    def test_interrupts_only_agents_for_this_workspace_then_controller(self) -> None:
        controller = FakeController()
        trial.terminate_trial(controller, self.WS)
        self.assertEqual(self.kills, [(200, signal.SIGINT), (203, signal.SIGINT), (205, signal.SIGINT),
                                      (controller.pid, signal.SIGINT)])
        self.assertEqual(controller.waits, [15])

    def test_hung_controller_is_escalated_to_sigkill(self) -> None:
        controller = FakeController(hang=True)
        trial.terminate_trial(controller, self.WS)
        self.assertEqual(self.kills[-2:], [(controller.pid, signal.SIGINT), (controller.pid, signal.SIGKILL)])
        self.assertEqual(controller.waits, [15, None])

    def test_exited_controller_is_not_signalled(self) -> None:
        controller = FakeController(running=False)
        trial.terminate_trial(controller, "/tmp/no-such-workspace")
        self.assertEqual(self.kills, [])
        self.assertEqual(controller.waits, [])


# ---------------------------------------------------------------------------
# main(): child command, classification, and guard decisions
# ---------------------------------------------------------------------------
class ChildLaunchTests(unittest.TestCase):
    def test_quality_child_command_is_fixed_argv_without_shell(self) -> None:
        h = MainHarness(self, PreparedWorkspace(self))
        self.assertEqual(h.run(), 0)
        self.assertEqual(len(h.children), 1)
        child = h.children[0]
        self.assertEqual(child.command, [
            sys.executable, str(h.root / "scripts/quality_local_agent.py"),
            "--workspace", h.workspace, "--task", "T1", "--variant", "V1",
            "--model", MODEL, "--base-url", "http://127.0.0.1:18082/v1",
            "--editable-path", "rtl/axi_regs.sv",
            "--trace", str(h.output / "quality-agent-trace.jsonl"),
            "--timeout", "600", "--total-timeout", "2400",
            "--max-completion-tokens", "8192", "--max-calls", "14",
        ])
        self.assertTrue(all(isinstance(part, str) for part in child.command))
        self.assertFalse(child.kwargs.get("shell", False))
        self.assertEqual(child.kwargs["cwd"], h.root)
        self.assertTrue(child.kwargs["start_new_session"])
        env = child.kwargs["env"]
        self.assertEqual(env["AI370_LOCAL_MODEL"], MODEL)
        self.assertEqual(env["AI370_MODEL_LAB_SERVER_PID"], str(SERVER_PID))
        self.assertEqual(env["AI370_MODEL_LAB_MODEL_PATH"], str(h.model_path))
        self.assertEqual(env["AI370_ROSS_AB_OUT"], str(h.output))
        self.assertEqual((env["AI370_MODEL_LAB_TOOL_CALL_CAP"], env["AI370_MODEL_LAB_COMPLETION_CAP"]), ("14", "8192"))
        self.assertEqual(h.health_calls[0], ("http://127.0.0.1:18082/health", 5))

    def test_multi_file_editable_paths_and_ross_url_are_passed_as_separate_args(self) -> None:
        h = MainHarness(self, PreparedWorkspace(self, task="T4"))
        h.extra_args = ["--ross-docsearch-url", "http://127.0.0.1:9/mcp; rm -rf /"]
        self.assertEqual(h.run(), 0)
        command = h.children[0].command
        editable = [command[i + 1] for i, part in enumerate(command) if part == "--editable-path"]
        self.assertEqual(editable, ["rtl/alu_pkg.sv", "rtl/alu.sv", "rtl/calc_top.sv"])
        self.assertEqual(command[-2:], ["--ross-docsearch-url", "http://127.0.0.1:9/mcp; rm -rf /"])

    def test_legacy_mode_runs_endurance_wrapper_and_is_not_formal(self) -> None:
        h = MainHarness(self, legacy=True)
        self.assertEqual(h.run(), 0)
        self.assertEqual(h.children[0].command,
                         [sys.executable, str(h.root / "scripts/run_model_endurance.py"), "--trial", str(h.config_path)])
        result = h.result()
        self.assertFalse(result["formal_quality_sample"])
        self.assertEqual(result["classification"], "LEGACY_CALIBRATION_ONLY")
        self.assertNotIn("sample_status", result)
        self.assertNotIn("agent_result", result)


class PreLaunchRefusalTests(unittest.TestCase):
    def assert_refused(self, h: MainHarness, message: str) -> None:
        with self.assertRaisesRegex(SystemExit, message):
            h.run()
        self.assertEqual(h.children, [])
        self.assertFalse((h.output / "guarded-result.json").exists())

    def test_unsupported_task_or_variant_is_refused(self) -> None:
        ws = PreparedWorkspace(self)
        for overrides in ({"task": "T9"}, {"variant": "V4"}):
            with self.subTest(overrides=overrides):
                h = MainHarness(self, ws)
                h.config = ws.config(**overrides)
                self.assert_refused(h, "not a supported frozen quality task")

    def test_harness_drift_before_launch_is_refused(self) -> None:
        ws = PreparedWorkspace(self)
        (ws.root / "scripts/local_agent.py").write_text("# drift\n")
        self.assert_refused(MainHarness(self, ws), "frozen harness changed")

    def test_dead_server_pid_is_refused(self) -> None:
        h = MainHarness(self, PreparedWorkspace(self))
        h.proc_cmdlines.clear()
        self.assert_refused(h, "model server PID is not live")

    def test_server_running_another_model_is_refused(self) -> None:
        h = MainHarness(self, PreparedWorkspace(self))
        h.proc_cmdlines[SERVER_PID] = b"llama-server\0-m\0/models/other.gguf"
        self.assert_refused(h, "does not name the requested model path")

    def test_unhealthy_server_is_refused(self) -> None:
        h = MainHarness(self, PreparedWorkspace(self))
        h.health = lambda t: 503
        self.assert_refused(h, "health check failed")


class ResultClassificationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.h = MainHarness(self, PreparedWorkspace(self))

    def test_clean_exit_zero_is_pass_with_agent_result(self) -> None:
        h = self.h
        self.assertEqual(h.run(), 0)
        result = h.result()
        self.assertEqual(result["sample_status"], "PASS")
        self.assertIsNone(result["guard_reason"])
        self.assertIsNone(result["guard_detail"])
        self.assertEqual(result["returncode"], 0)
        self.assertEqual(result["agent_result"], {"status": "DONE", "calls": 3})
        self.assertTrue(result["formal_quality_sample"])
        self.assertEqual(result["classification"], "FORMAL_QUALITY_SAMPLE")
        self.assertEqual(len(result["resource_samples"]), 2)
        self.assertEqual(result["resource_warnings"], [])
        self.assertEqual(h.printed, {"returncode": 0, "guard_reason": None, "sample_count": 2})
        self.assertEqual(h.terminated, [])
        h.killpg.assert_not_called()

    def test_nonzero_child_exit_is_fail(self) -> None:
        h = self.h
        h.child_returncode = 3
        self.assertEqual(h.run(), 1)
        result = h.result()
        self.assertEqual((result["sample_status"], result["returncode"], result["guard_reason"]), ("FAIL", 3, None))
        self.assertEqual(h.terminated, [])

    def test_unparseable_or_empty_agent_output_gives_null_agent_result(self) -> None:
        for lines in (["Traceback (most recent call last):", "boom"], []):
            with self.subTest(lines=lines):
                h = MainHarness(self, PreparedWorkspace(self))
                h.child_stdout = lines
                self.assertEqual(h.run(), 0)
                self.assertIsNone(h.result()["agent_result"])

    def test_timeout_stops_child_and_is_partial(self) -> None:
        h = self.h
        h.extra_args = ["--timeout", "3"]
        h.child_exit_tick = None
        self.assertEqual(h.run(), 1)
        result = h.result()
        self.assertEqual((result["guard_reason"], result["sample_status"]), ("SAMPLE_TIMEOUT", "PARTIAL"))
        self.assertEqual(result["returncode"], -signal.SIGINT)
        self.assertEqual(len(result["resource_samples"]), 5)  # stops at elapsed 4 > 3
        self.assertEqual(h.terminated, [(h.children[0], h.workspace)])
        self.assertEqual(h.sleeps, 4)

    def test_user_stop_file_blocks_sample(self) -> None:
        h = self.h
        stop = h.root / "STOP"
        h.extra_args = ["--stop-file", str(stop)]
        h.child_exit_tick = None
        h.hooks[2] = stop.touch
        self.assertEqual(h.run(), 1)
        result = h.result()
        self.assertEqual((result["guard_reason"], result["sample_status"]), ("USER_STOP", "BLOCKED"))
        self.assertEqual(len(result["resource_samples"]), 3)
        self.assertEqual(len(h.terminated), 1)

    def test_interrupt_inside_loop_terminates_child_and_propagates(self) -> None:
        h = self.h
        h.child_exit_tick = None

        def interrupt():
            raise KeyboardInterrupt
        h.hooks[2] = interrupt
        with self.assertRaises(KeyboardInterrupt):
            h.run()
        self.assertEqual(h.terminated, [(h.children[0], h.workspace)])
        self.assertFalse((h.output / "guarded-result.json").exists())

    def test_journal_timeout_terminates_child_and_propagates(self) -> None:
        h = self.h
        h.child_exit_tick = None
        h.journal = lambda t: subprocess.TimeoutExpired("journalctl", 12)
        with self.assertRaises(subprocess.TimeoutExpired):
            h.run()
        self.assertEqual(len(h.terminated), 1)


class LiveIntegrityInMainTests(unittest.TestCase):
    def setUp(self) -> None:
        self.ws = PreparedWorkspace(self)
        self.h = MainHarness(self, self.ws)
        self.h.child_exit_tick = None

    def assert_blocked_at(self, tick: int, detail: str) -> None:
        h = self.h
        self.assertEqual(h.run(), 1)
        result = h.result()
        self.assertEqual(result["guard_reason"], "HARNESS_INTEGRITY_GUARD")
        self.assertIn(detail, result["guard_detail"])
        self.assertEqual(result["sample_status"], "BLOCKED")
        self.assertEqual(len(result["resource_samples"]), tick + 1)
        self.assertEqual(result["resource_samples"][-1]["elapsed_seconds"], float(tick))
        self.assertEqual(h.terminated, [(h.children[0], h.workspace)])
        self.assertEqual(h.sleeps, tick)

    def test_runner_change_mid_sample_stops_child_at_next_integrity_check(self) -> None:
        self.h.hooks[2] = lambda: (self.ws.root / "scripts/quality_task_executor.py").write_text("# swapped\n")
        self.assert_blocked_at(5, "RuntimeError: HARNESS_INTEGRITY_GUARD: runner changed: scripts/quality_task_executor.py")

    def test_write_outside_allowlist_mid_sample_stops_child(self) -> None:
        self.h.hooks[6] = lambda: (self.ws.workspace / "rtl/extra.sv").write_text("// x\n")
        self.assert_blocked_at(10, "workspace write outside allowlist: rtl/extra.sv")

    def test_unreadable_protocol_mid_sample_fails_closed(self) -> None:
        self.h.hooks[1] = lambda: self.ws.protocol_path.write_text("{corrupt")
        self.assert_blocked_at(5, "JSONDecodeError")

    def test_editable_write_mid_sample_is_not_a_guard(self) -> None:
        h = self.h
        h.child_exit_tick = 12
        h.hooks[3] = lambda: (self.ws.workspace / "rtl/axi_regs.sv").write_text("// candidate fix\n")
        self.assertEqual(h.run(), 0)
        self.assertEqual(h.result()["sample_status"], "PASS")
        self.assertEqual(h.terminated, [])


class ResourceGuardTests(unittest.TestCase):
    def setUp(self) -> None:
        self.h = MainHarness(self, PreparedWorkspace(self))

    def mem(self, available_kib, total_kib=48 * GIB_KIB, swap_free_kib=8 * GIB_KIB):
        return {"MemTotal": total_kib, "MemAvailable": available_kib, "SwapTotal": 8 * GIB_KIB, "SwapFree": swap_free_kib}

    def assert_guard(self, reason: str, tick: int) -> dict:
        h = self.h
        self.assertEqual(h.run(), 1)
        result = h.result()
        self.assertEqual(result["guard_reason"], reason)
        self.assertEqual(result["sample_status"], "BLOCKED")
        self.assertEqual(len(result["resource_samples"]), tick + 1)
        self.assertEqual(h.terminated, [(h.children[0], h.workspace)])
        self.assertEqual(h.sleeps, tick)
        return result

    def assert_no_guard(self) -> dict:
        h = self.h
        self.assertEqual(h.run(), 0)
        result = h.result()
        self.assertIsNone(result["guard_reason"])
        self.assertEqual(result["sample_status"], "PASS")
        self.assertEqual(h.terminated, [])
        return result

    def test_sustained_low_memavailable_stops_after_grace(self) -> None:
        self.h.child_exit_tick = None
        self.h.mem = lambda t: self.mem(4 * GIB_KIB)
        self.assert_guard("SUSTAINED_MEMAVAILABLE_GUARD", trial.LOW_MEMORY_GRACE_SECONDS)

    def test_memory_floor_scales_with_memtotal(self) -> None:
        self.h.child_exit_tick = None
        # 10 GiB is above the 6 GiB floor but below 128 GiB / 8.
        self.h.mem = lambda t: self.mem(10 * GIB_KIB, total_kib=128 * GIB_KIB)
        self.assert_guard("SUSTAINED_MEMAVAILABLE_GUARD", trial.LOW_MEMORY_GRACE_SECONDS)

    def test_transient_low_memory_resets_grace(self) -> None:
        self.h.child_exit_tick = 35
        self.h.mem = lambda t: self.mem(40 * GIB_KIB if t == 16 else 4 * GIB_KIB)
        self.assert_no_guard()

    def test_sustained_psi_stops_after_grace(self) -> None:
        self.h.child_exit_tick = None
        self.h.psi = lambda t: trial.PSI_HARD_LIMIT
        self.assert_guard("MEMORY_PSI_GUARD", trial.PSI_GRACE_SECONDS)

    def test_psi_spikes_shorter_than_grace_are_tolerated(self) -> None:
        self.h.child_exit_tick = 19
        self.h.psi = lambda t: 0.0 if t == 9 else 50.0
        self.assert_no_guard()

    def test_uncorroborated_swapout_is_recorded_but_does_not_stop(self) -> None:
        self.h.child_exit_tick = 3
        self.h.vm = lambda t: {"pswpin": 0, "pswpout": t * pages(20 * MIB)}
        result = self.assert_no_guard()
        kinds = [w["kind"] for w in result["resource_warnings"]]
        self.assertEqual(kinds, ["SWAPOUT_ACTIVITY"] * 2)
        self.assertEqual(result["resource_warnings"][0]["window_swapout_bytes"], pages(20 * MIB) * trial.PAGE_SIZE)
        self.assertEqual(result["resource_samples"][-1]["pswpout_pages_delta"], 2 * pages(20 * MIB))

    def test_swapout_corroborated_by_swapin_stops_immediately(self) -> None:
        self.h.child_exit_tick = None
        self.h.vm = lambda t: {"pswpin": t * pages(2 * MIB), "pswpout": t * pages(20 * MIB)}
        self.assert_guard("CORROBORATED_SWAP_PRESSURE_GUARD", 1)

    def test_swapout_corroborated_by_low_memory_bypasses_grace(self) -> None:
        self.h.child_exit_tick = None
        self.h.mem = lambda t: self.mem(4 * GIB_KIB)
        self.h.vm = lambda t: {"pswpin": 0, "pswpout": t * pages(20 * MIB)}
        self.assert_guard("CORROBORATED_SWAP_PRESSURE_GUARD", 1)

    def test_small_swapout_with_swapin_is_not_enough(self) -> None:
        self.h.child_exit_tick = 4
        self.h.vm = lambda t: {"pswpin": t * pages(2 * MIB), "pswpout": t * pages(2 * MIB)}
        result = self.assert_no_guard()
        self.assertTrue(all(w["kind"] == "SWAPOUT_ACTIVITY" for w in result["resource_warnings"]))

    def test_large_swap_growth_is_warned_once_without_stopping(self) -> None:
        self.h.child_exit_tick = 4
        self.h.mem = lambda t: self.mem(40 * GIB_KIB, swap_free_kib=8 * GIB_KIB - t * 100 * 1024)
        result = self.assert_no_guard()
        warnings = [w for w in result["resource_warnings"] if w["kind"] == "LARGE_SWAP_GROWTH_UNCORROBORATED"]
        self.assertEqual(len(warnings), 1)
        self.assertEqual(warnings[0]["swap_growth_kib"], 100 * 1024)

    def test_low_disk_stops_sample(self) -> None:
        self.h.child_exit_tick = None
        self.h.disk_free = 19 * 1024**3
        self.assert_guard("DISK_GUARD", 0)


class ServerAndKernelGuardTests(unittest.TestCase):
    def setUp(self) -> None:
        self.h = MainHarness(self, PreparedWorkspace(self))
        self.h.child_exit_tick = None

    def assert_guard(self, reason: str, tick: int) -> None:
        h = self.h
        self.assertEqual(h.run(), 1)
        result = h.result()
        self.assertEqual((result["guard_reason"], result["sample_status"]), (reason, "BLOCKED"))
        self.assertEqual(len(result["resource_samples"]), tick + 1)
        self.assertEqual(h.terminated, [(h.children[0], h.workspace)])

    def test_server_process_replaced_is_crash(self) -> None:
        h = self.h
        h.hooks[3] = lambda: h.proc_cmdlines.__setitem__(SERVER_PID, b"bash\0")
        self.assert_guard("MODEL_SERVER_CRASH", 5)

    def test_two_consecutive_health_failures_stop_sample(self) -> None:
        h = self.h
        h.health = lambda t: urllib.error.URLError("refused") if t >= 1 else 200
        # Startup check (tick 0) passes; live audits at t=0 pass, t=5 and t=10 fail.
        self.assert_guard("MODEL_SERVER_HEALTH_LOST", 10)
        self.assertEqual([timeout for _, timeout in h.health_calls], [5, 3, 3, 3])

    def test_two_consecutive_non_200_health_statuses_stop_sample(self) -> None:
        h = self.h
        h.health = lambda t: 503 if t >= 1 else 200
        self.assert_guard("MODEL_SERVER_HEALTH_LOST", 10)

    def test_vanished_server_pid_counts_as_health_loss(self) -> None:
        h = self.h
        h.hooks[1] = h.proc_cmdlines.clear
        self.assert_guard("MODEL_SERVER_HEALTH_LOST", 10)

    def test_single_health_failure_recovers(self) -> None:
        h = self.h
        h.child_exit_tick = 12
        # Call 1 is the startup check; live audits at elapsed 0 (HTTP 503) and
        # 10 (timeout) fail, the audit at 5 recovers and resets the counter.
        calls = {"n": 0}

        def health(t):
            calls["n"] += 1
            return {2: 503, 4: TimeoutError("slow")}.get(calls["n"], 200)
        h.health = health
        self.assertEqual(h.run(), 0)
        self.assertIsNone(h.result()["guard_reason"])
        self.assertEqual(calls["n"], 4)

    def test_kernel_audit_unreadable_stops_sample(self) -> None:
        self.h.journal = lambda t: subprocess.CompletedProcess([], 1, "", "permission denied")
        self.assert_guard("KERNEL_AUDIT_UNREADABLE", 0)

    def test_kernel_fault_tokens_stop_sample(self) -> None:
        for line in ("amdgpu: page fault (src_id:0 ring:24)", "Out of memory: Killed process 1234 (llama-server)",
                     "amdgpu 0000:c5:00.0: GPU reset begin!", "ring timeout, signaled seq=1"):
            with self.subTest(line=line):
                h = MainHarness(self, PreparedWorkspace(self))
                h.child_exit_tick = None
                h.journal = lambda t, line=line: subprocess.CompletedProcess([], 0, line + "\n", "")
                self.assertEqual(h.run(), 1)
                self.assertEqual(h.result()["guard_reason"], "GPU_KERNEL_OOM_FAULT")
                self.assertEqual(len(h.terminated), 1)

    def test_kernel_audit_cadence_and_arguments(self) -> None:
        h = self.h
        h.child_exit_tick = 31
        self.assertEqual(h.run(), 0)
        self.assertEqual(len(h.journal_calls), 3)  # elapsed 0, 15, 30
        command, kwargs = h.journal_calls[0]
        self.assertEqual(command[:3], ["journalctl", "-k", "--since"])
        self.assertRegex(command[3], r"^\d{4}-\d\d-\d\d \d\d:\d\d:\d\d UTC$")
        self.assertEqual(command[4:], ["--no-pager", "-o", "short-iso"])
        self.assertEqual(kwargs["timeout"], 12)
        self.assertFalse(kwargs.get("shell", False))


if __name__ == "__main__":
    unittest.main()
