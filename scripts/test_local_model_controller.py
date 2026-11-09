#!/usr/bin/env python3
"""Offline tests for the local model controller.

Every writable controller path is redirected to the system temp dir, and
subprocesses, signals, process-group kills, sleeps and /proc health readings
are mocked.  No runner, model, systemd unit or network endpoint is touched.
"""
from __future__ import annotations

import copy
import fcntl
import io
import json
import os
import signal
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import local_model_controller as controller

GIB_KIB = 1024 * 1024
PLAN_ID = "20261103T065105Z"
READ_ONLY_PATHS = {"RUNNER", "FIXTURE_RUNNER", "PLAN_RUNNER"}
# Captured before any Sandbox patches them, so nested sandboxes wrap the real writers.
REAL_ATOMIC_JSON, REAL_APPEND_JSONL = controller.atomic_json, controller.append_jsonl


def healthy() -> dict:
    return {"timestamp_utc": "fixture", "memavailable_kib": 40 * GIB_KIB, "memtotal_kib": 48 * GIB_KIB,
            "swaptotal_kib": 8 * GIB_KIB, "swapfree_kib": 8 * GIB_KIB, "swapused_kib": 0,
            "vmstat_pages": {"pswpin": 0, "pswpout": 0, "pgmajfault": 0},
            "memory_psi": {"full": {"avg10": 0.0}}, "top_vmswap_processes": []}


class FakeProcess:
    def __init__(self, pid: int, command: list[str], kwargs: dict):
        self.pid, self.command, self.kwargs, self.returncode = pid, command, kwargs, None

    def poll(self):
        return self.returncode


class Sandbox:
    """Run controller code against a temp tree with all side effects mocked."""

    def __init__(self, case: unittest.TestCase, ticks: int = 1):
        self.case, self.ticks, self.tick = case, ticks, 0
        temp = tempfile.TemporaryDirectory()
        case.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()
        base = self.root / "output/LOCAL_MODEL_CONTROLLER"
        self.paths = dict(
            ROOT=self.root, QUALITY_BASE=self.root / "output/QUALITY_MODEL_VALIDATION", BASE=base,
            STATE_PATH=base / "status.json", COMMAND_PATH=base / "command.json", EVENTS_PATH=base / "events.jsonl",
            TELEMETRY_PATH=base / "telemetry.jsonl", LOCK_PATH=base / "controller.lock",
            CONTROLLER_DIAGNOSTICS=base / "diagnostics",
            REMEDIATION_REPORT=self.root / "docs/LOCAL_MODEL_LAB/PILOT_V1_REMEDIATION.md")
        for name, value in self.paths.items():
            self._start(patch.object(controller, name, value))
        self.health = healthy()
        self.processes: list[FakeProcess] = []
        self.kills: list[tuple[int, int]] = []
        self.handlers: dict[int, object] = {}
        self.hooks: dict[int, object] = {}
        self.states: list[dict | None] = []
        self.run_calls: list[list[str]] = []
        self.run_result = subprocess.CompletedProcess([], 0, "plan frozen", "")
        self._start(patch.object(controller, "atomic_json", side_effect=lambda p, v: REAL_ATOMIC_JSON(self.inside(p), v)))
        self._start(patch.object(controller, "append_jsonl", side_effect=lambda p, v: REAL_APPEND_JSONL(self.inside(p), v)))
        self._start(patch.object(controller, "health_snapshot", side_effect=self._health))
        self._start(patch.object(controller.subprocess, "Popen", side_effect=self._popen))
        self._start(patch.object(controller.subprocess, "run", side_effect=self._run))
        self._start(patch.object(controller.os, "killpg", side_effect=lambda pid, sig: self.kills.append((pid, sig))))
        self._start(patch.object(controller.signal, "signal", side_effect=lambda sig, handler: self.handlers.__setitem__(sig, handler)))
        self._start(patch.object(controller.time, "sleep", side_effect=self._sleep))

    def _start(self, patcher) -> None:
        patcher.start()
        self.case.addCleanup(patcher.stop)

    def inside(self, path: Path) -> Path:
        if not Path(path).resolve().is_relative_to(self.root):
            raise AssertionError(f"controller write escaped the sandbox: {path}")
        return path

    def _health(self):
        # Assigning an exception to box.health simulates an unreadable /proc source.
        if isinstance(self.health, Exception):
            raise self.health
        return copy.deepcopy(self.health)

    def _popen(self, command, **kwargs):
        self.inside(Path(kwargs["cwd"]))
        proc = FakeProcess(5000 + len(self.processes), command, kwargs)
        self.processes.append(proc)
        return proc

    def _run(self, command, **kwargs):
        self.run_calls.append(command)
        return self.run_result

    def _sleep(self, seconds):
        self.case.assertEqual(seconds, controller.POLL_SECONDS)
        self.states.append(controller.read_json(controller.STATE_PATH))
        hook = self.hooks.get(self.tick)
        if hook:
            hook()
        self.tick += 1
        if self.tick >= self.ticks:
            self.handlers[signal.SIGTERM](signal.SIGTERM, None)

    # Fixture helpers -----------------------------------------------------
    def command(self, action: str, request_id: str = "req-1", **fields) -> None:
        value = {"schema_version": 1, "request_id": request_id, "action": action, "approved": True, **fields}
        controller.atomic_json(controller.COMMAND_PATH, value)

    def quality(self, status: str) -> None:
        controller.atomic_json(controller.QUALITY_BASE / "status.json", {"status": status})

    def plan(self) -> Path:
        path = controller.BASE / "plans" / PLAN_ID / "v2-v3-plan.json"
        controller.atomic_json(path, {"schema_version": 1})
        return path

    def report(self) -> None:
        controller.REMEDIATION_REPORT.parent.mkdir(parents=True, exist_ok=True)
        controller.REMEDIATION_REPORT.write_text("# remediation fixture\n")

    def serve(self) -> int:
        result = controller.serve()
        self.case.assertEqual(self.tick, self.ticks)
        return result

    def events(self) -> list[dict]:
        if not controller.EVENTS_PATH.exists():
            return []
        return [json.loads(line) for line in controller.EVENTS_PATH.read_text().splitlines()]

    def event_names(self) -> list[str]:
        return [event["event"] for event in self.events()]

    def final_state(self) -> dict:
        return controller.read_json(controller.STATE_PATH)


class SandboxIsolationTests(unittest.TestCase):
    def test_every_writable_module_path_is_redirected_to_system_temp(self):
        box = Sandbox(self)
        temp_root = Path(tempfile.gettempdir()).resolve()
        for name, value in vars(controller).items():
            if isinstance(value, Path) and name not in READ_ONLY_PATHS:
                self.assertTrue(value.resolve().is_relative_to(box.root), name)
                self.assertTrue(value.resolve().is_relative_to(temp_root), name)

    def test_escaping_write_is_rejected(self):
        box = Sandbox(self)
        with self.assertRaisesRegex(AssertionError, "escaped the sandbox"):
            controller.atomic_json(Path(tempfile.gettempdir()) / "outside-controller-sandbox.json", {})


class StateTests(unittest.TestCase):
    def test_atomic_json_round_trip_leaves_no_temp_file(self):
        box = Sandbox(self)
        path = box.root / "nested/state.json"
        controller.atomic_json(path, {"status": "MONITORING", "text": "記憶體"})
        self.assertEqual(controller.read_json(path), {"status": "MONITORING", "text": "記憶體"})
        self.assertFalse(path.with_suffix(".json.tmp").exists())

    def test_read_json_returns_none_for_missing_or_corrupt_state(self):
        box = Sandbox(self)
        self.assertIsNone(controller.read_json(box.root / "missing.json"))
        corrupt = box.root / "corrupt.json"
        corrupt.write_text("{not json")
        self.assertIsNone(controller.read_json(corrupt))

    def test_fresh_controller_monitors_records_health_and_stops_cleanly(self):
        box = Sandbox(self, ticks=2)
        self.assertEqual(box.serve(), 0)
        self.assertEqual([s["status"] for s in box.states], ["MONITORING", "MONITORING"])
        self.assertEqual(box.states[0]["last_health"]["memavailable_kib"], 40 * GIB_KIB)
        self.assertEqual(len(controller.TELEMETRY_PATH.read_text().splitlines()), 2)
        self.assertEqual(box.event_names(), ["CONTROLLER_STARTED", "CONTROLLER_STOPPED"])
        self.assertEqual(box.final_state()["status"], "CONTROLLER_STOPPED")
        self.assertEqual(box.processes, [])

    def test_stopped_controller_returns_to_monitoring_on_restart(self):
        box = Sandbox(self)
        controller.atomic_json(controller.STATE_PATH, {**controller.state_template(), "status": "CONTROLLER_STOPPED"})
        box.serve()
        self.assertEqual(box.states[0]["status"], "MONITORING")

    def test_restart_preserves_controller_safety_review_and_never_relaunches(self):
        box = Sandbox(self)
        box.plan()
        box.quality("STOPPED_BY_USER")
        controller.atomic_json(controller.STATE_PATH, {**controller.state_template(), "status": "V2_V3_STOPPED",
                                                       "runner": {"kind": "V2_V3", "pid": 4242}})
        controller.append_jsonl(controller.EVENTS_PATH, {"event": "CHILD_SAFETY_STOP", "pid": 4242, "reason": "MEMAVAILABLE_GUARD"})
        box.serve()
        self.assertEqual(box.states[0]["status"], "V2_V3_SAFETY_REVIEW_REQUIRED")
        self.assertEqual(box.states[0]["runner"]["controller_guard_reason"], "MEMAVAILABLE_GUARD")
        self.assertEqual(box.processes, [])

    def test_recorded_controller_guard_matches_only_the_same_pid(self):
        box = Sandbox(self)
        self.assertIsNone(controller.recorded_controller_guard(7))
        controller.append_jsonl(controller.EVENTS_PATH, {"event": "CHILD_SAFETY_STOP", "pid": 7, "reason": "MEMORY_PSI_GUARD"})
        self.assertEqual(controller.recorded_controller_guard(7), "MEMORY_PSI_GUARD")
        self.assertIsNone(controller.recorded_controller_guard(8))
        self.assertIsNone(controller.recorded_controller_guard(None))
        with controller.EVENTS_PATH.open("a") as stream:
            stream.write("{corrupt\n")
        self.assertIsNone(controller.recorded_controller_guard(7))

    def test_second_controller_instance_is_refused_by_lock(self):
        box = Sandbox(self)
        controller.BASE.mkdir(parents=True)
        with controller.LOCK_PATH.open("w") as held:
            fcntl.flock(held, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with redirect_stdout(io.StringIO()) as out:
                self.assertEqual(controller.serve(), 2)
        self.assertEqual(json.loads(out.getvalue())["status"], "CONTROLLER_ALREADY_RUNNING")
        self.assertFalse(controller.STATE_PATH.exists())
        self.assertEqual(box.tick, 0)


class RunnerTests(unittest.TestCase):
    def test_pilot_success_launches_once_without_shell_and_waits_for_review(self):
        box = Sandbox(self, ticks=3)
        box.command("ARM_PILOT")
        def finish():
            box.processes[0].returncode = 0
            box.quality("PILOT_COMPLETE")
        box.hooks[0] = finish
        box.serve()
        self.assertEqual(len(box.processes), 1)
        proc = box.processes[0]
        self.assertEqual(proc.command, [sys.executable, str(controller.RUNNER), "--pilot-only"])
        self.assertEqual(proc.kwargs["cwd"], box.root)
        self.assertTrue(proc.kwargs["start_new_session"])
        self.assertNotIn("shell", proc.kwargs)
        self.assertEqual([s["status"] for s in box.states], ["RUNNER_ACTIVE", "WAITING_FOR_REVIEW", "WAITING_FOR_REVIEW"])
        self.assertEqual(box.states[1]["runner"]["exit_code"], 0)
        self.assertIn("RUNNER_STARTED", box.event_names())
        exited = [e for e in box.events() if e["event"] == "RUNNER_EXITED"]
        self.assertEqual(exited[0]["exit_code"], 0)
        self.assertEqual(exited[0]["quality_status"], "PILOT_COMPLETE")

    def test_pilot_failure_records_exit_code_and_returns_to_monitoring(self):
        box = Sandbox(self, ticks=2)
        box.command("ARM_PILOT")
        box.hooks[0] = lambda: setattr(box.processes[0], "returncode", 1)
        box.serve()
        self.assertEqual(box.states[1]["status"], "MONITORING")
        self.assertEqual(box.states[1]["runner"]["exit_code"], 1)
        self.assertEqual(len(box.processes), 1)

    def test_pilot_is_not_started_when_quality_state_needs_review(self):
        for quality, reason in (("PILOT_COMPLETE", "PILOT_ALREADY_COMPLETE_REVIEW_REQUIRED"),
                                ("RUNNING", "QUALITY_STATE_RUNNING"), ("SAFETY_STOP", "QUALITY_STATE_SAFETY_STOP"),
                                ("SOMETHING_ELSE", "UNRECOGNIZED_QUALITY_STATE")):
            with self.subTest(quality=quality):
                box = Sandbox(self)
                box.quality(quality)
                box.command("ARM_PILOT")
                box.serve()
                self.assertEqual(box.processes, [])
                rejected = [e for e in box.events() if e["event"] == "RUNNER_NOT_STARTED"]
                self.assertEqual(rejected[0]["reason"], reason)

    def test_remediation_fixture_success_freezes_plan_without_model_execution(self):
        box = Sandbox(self, ticks=2)
        box.quality("PILOT_COMPLETE")
        box.report()
        box.command("RUN_REMEDIATION_FIXTURES")
        box.hooks[0] = lambda: setattr(box.processes[0], "returncode", 0)
        box.serve()
        self.assertEqual(box.processes[0].command, [sys.executable, str(controller.FIXTURE_RUNNER)])
        self.assertEqual(box.states[0]["status"], "REMEDIATION_FIXTURES_ACTIVE")
        self.assertEqual(box.run_calls, [[sys.executable, str(controller.PLAN_RUNNER)]])
        self.assertEqual(box.states[1]["status"], "V2_V3_PLAN_READY")
        self.assertIn("V2_V3_PLAN_FROZEN", box.event_names())
        self.assertEqual(len(box.processes), 1)

    def test_remediation_fixture_failure_does_not_freeze_plan(self):
        box = Sandbox(self, ticks=2)
        box.quality("PILOT_COMPLETE")
        box.report()
        box.command("RUN_REMEDIATION_FIXTURES")
        box.hooks[0] = lambda: setattr(box.processes[0], "returncode", 1)
        box.serve()
        self.assertEqual(box.states[1]["status"], "REMEDIATION_FIXTURES_FAILED")
        self.assertEqual(box.run_calls, [])

    def test_plan_freeze_failure_is_recorded(self):
        box = Sandbox(self, ticks=2)
        box.quality("PILOT_COMPLETE")
        box.report()
        box.run_result = subprocess.CompletedProcess([], 3, "", "freeze failed")
        box.command("RUN_REMEDIATION_FIXTURES")
        box.hooks[0] = lambda: setattr(box.processes[0], "returncode", 0)
        box.serve()
        self.assertEqual(box.states[1]["status"], "V2_V3_PLAN_FAILED")
        self.assertEqual(box.states[1]["v2_v3_plan"]["exit_code"], 3)
        self.assertIn("V2_V3_PLAN_FAILED", box.event_names())

    def test_remediation_fixtures_need_completed_pilot_and_report(self):
        for quality, with_report in (("PILOT_COMPLETE", False), ("RUNNING", True), (None, True)):
            with self.subTest(quality=quality, report=with_report):
                box = Sandbox(self)
                if quality:
                    box.quality(quality)
                if with_report:
                    box.report()
                box.command("RUN_REMEDIATION_FIXTURES")
                box.serve()
                self.assertEqual(box.processes, [])
                self.assertIn("FIXTURES_NOT_STARTED", box.event_names())


class SafetyStopTests(unittest.TestCase):
    def run_v2_v3(self, mutate) -> Sandbox:
        """Auto-start a frozen V2/V3 plan, then apply one health change."""
        box = Sandbox(self, ticks=2)
        box.quality("PILOT_COMPLETE")
        box.plan()
        box.hooks[0] = lambda: mutate(box.health)
        box.serve()
        return box

    def test_v2_v3_auto_start_passes_controller_stop_file(self):
        box = self.run_v2_v3(lambda health: None)
        proc = box.processes[0]
        self.assertEqual(proc.command, [sys.executable, str(controller.RUNNER), "--variants", "V2", "V3", "--max-cycles", "1"])
        stop_file = controller.BASE / f"controller-stop-auto-v2-v3-{PLAN_ID}.json"
        self.assertEqual(proc.kwargs["env"]["AI370_CONTROLLER_STOP_FILE"], str(stop_file))
        self.assertEqual(box.states[0]["status"], "V2_V3_ACTIVE")

    def test_healthy_runner_is_not_interrupted(self):
        box = self.run_v2_v3(lambda health: None)
        # The only interruption is the orderly stop when the controller exits.
        self.assertEqual(box.kills, [(box.processes[0].pid, signal.SIGINT)])
        self.assertIn("CONTROLLER_SHUTDOWN", (controller.QUALITY_BASE / "STOP").read_text())
        self.assertEqual(box.states[1]["status"], "V2_V3_ACTIVE")
        self.assertNotIn("CHILD_SAFETY_STOP", box.event_names())

    def test_resource_guards_interrupt_the_runner_and_write_stop_reason(self):
        page = os.sysconf("SC_PAGE_SIZE")
        cases = {
            "MEMAVAILABLE_GUARD": lambda h: h.update(memavailable_kib=GIB_KIB),
            "CORROBORATED_SWAP_PRESSURE_GUARD": lambda h: h.update(
                swapused_kib=128 * 1024, vmstat_pages={"pswpin": (1024**2 + page - 1) // page, "pswpout": 0}),
            "MEMORY_PSI_GUARD": lambda h: h.update(memory_psi={"full": {"avg10": 25.0}}),
        }
        for reason, mutate in cases.items():
            with self.subTest(reason=reason):
                box = self.run_v2_v3(mutate)
                pid = box.processes[0].pid
                self.assertEqual(box.kills, [(pid, signal.SIGINT), (pid, signal.SIGINT)])
                self.assertEqual(box.states[1]["status"], "SAFETY_STOP")
                self.assertEqual(box.states[1]["runner"]["controller_guard_reason"], reason)
                stop = controller.read_json(controller.BASE / f"controller-stop-auto-v2-v3-{PLAN_ID}.json")
                self.assertEqual((stop["reason"], stop["owner"]), (reason, "LOCAL_MODEL_CONTROLLER"))
                events = [e for e in box.events() if e["event"] == "CHILD_SAFETY_STOP"]
                self.assertEqual((events[0]["reason"], events[0]["pid"]), (reason, pid))

    def test_guarded_runner_exit_requires_safety_review(self):
        box = Sandbox(self, ticks=3)
        box.quality("PILOT_COMPLETE")
        box.plan()
        box.hooks[0] = lambda: box.health.update(memavailable_kib=GIB_KIB)
        def child_exits():
            box.processes[0].returncode = 130
            box.quality("STOPPED_BY_USER")
        box.hooks[1] = child_exits
        box.serve()
        self.assertEqual(box.states[2]["status"], "V2_V3_SAFETY_REVIEW_REQUIRED")
        self.assertIn("CONTROLLER_SAFETY_STOP_CONFIRMED", box.event_names())
        self.assertEqual(len(box.processes), 1)
        self.assertEqual(len(box.kills), 1)

    def write_guarded_result(self, box: Sandbox, samples: list[dict]) -> Path:
        path = controller.QUALITY_BASE / "20261106T105511/cycle-0001/samples/m/T1/V1/guarded/guarded-result.json"
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps({"guard_reason": "SUSTAINED_SWAPOUT_GUARD", "resource_samples": samples}))
        return path

    def test_diagnosis_is_read_only_and_classifies_evidence(self):
        quiet = {"pswpin_pages_delta": 0, "pswpout_pages_delta": 9, "psi_full_avg10": 1.0, "memavailable_kib": 10 * GIB_KIB}
        cases = {"INSUFFICIENT_EVIDENCE_OF_MEMORY_PRESSURE": quiet,
                 "SAFETY_STOP_EVIDENCE_REQUIRES_REVIEW": {**quiet, "pswpin_pages_delta": 5}}
        for assessment, sample in cases.items():
            with self.subTest(assessment=assessment):
                box = Sandbox(self)
                result = self.write_guarded_result(box, [sample])
                before = result.read_bytes()
                state: dict = {}
                path = controller.diagnose_safety_stop(state)
                self.assertTrue(path.is_relative_to(controller.CONTROLLER_DIAGNOSTICS))
                diagnosis = controller.read_json(path)
                self.assertEqual(diagnosis["assessment"], assessment)
                self.assertEqual(diagnosis["trigger"], "SUSTAINED_SWAPOUT_GUARD")
                self.assertEqual(state["last_safety_diagnosis"], str(path.relative_to(box.root)))
                self.assertEqual(result.read_bytes(), before)

    def test_healthy_snapshot_has_no_unreadable_fields(self):
        self.assertEqual(controller.unreadable_health_fields(healthy(), healthy()), [])

    def test_unreadable_proc_stops_runner_fail_closed_and_controller_keeps_running(self):
        box = Sandbox(self, ticks=4)
        box.quality("PILOT_COMPLETE")
        box.plan()
        def proc_unreadable():
            box.health = FileNotFoundError(2, "No such file or directory", "/proc/pressure/memory")
        def child_exits():
            box.processes[0].returncode = 130
            box.quality("STOPPED_BY_USER")
        box.hooks[0] = proc_unreadable
        box.hooks[1] = child_exits
        self.assertEqual(box.serve(), 0)
        pid = box.processes[0].pid
        guard = [e for e in box.events() if e["event"] == "HEALTH_UNREADABLE_GUARD"]
        self.assertEqual(len(guard), 1)
        self.assertEqual(guard[0]["pid"], pid)
        self.assertIn("current.health_error", guard[0]["fields"])
        self.assertIn("/proc/pressure/memory", guard[0]["health_error"])
        stops = [e for e in box.events() if e["event"] == "CHILD_SAFETY_STOP"]
        self.assertEqual(stops[0]["reason"], "HEALTH_UNREADABLE_GUARD")
        self.assertEqual(box.kills, [(pid, signal.SIGINT)])
        stop = controller.read_json(controller.BASE / f"controller-stop-auto-v2-v3-{PLAN_ID}.json")
        self.assertEqual(stop["reason"], "HEALTH_UNREADABLE_GUARD")
        # The controller keeps polling after the stop: review state, telemetry and no relaunch.
        self.assertEqual([s["status"] for s in box.states[1:]],
                         ["SAFETY_STOP", "V2_V3_SAFETY_REVIEW_REQUIRED", "V2_V3_SAFETY_REVIEW_REQUIRED"])
        telemetry = [json.loads(line) for line in controller.TELEMETRY_PATH.read_text().splitlines()]
        self.assertEqual(len(telemetry), 4)
        self.assertEqual(sum("health_error" in row for row in telemetry), 3)
        self.assertEqual(len(box.processes), 1)
        self.assertEqual(box.final_state()["status"], "CONTROLLER_STOPPED")

    def test_missing_or_malformed_health_fields_fail_closed(self):
        cases = {
            "current.memavailable_kib": lambda h: h.update(memavailable_kib=None),
            "current.memtotal_kib": lambda h: h.pop("memtotal_kib"),
            "current.swapused_kib": lambda h: h.update(swapused_kib="unknown"),
            "current.memory_psi.full.avg10": lambda h: h.update(memory_psi={}),
            "current.vmstat_pages.pswpin": lambda h: h.update(vmstat_pages={"pswpout": 0}),
        }
        for field, mutate in cases.items():
            with self.subTest(field=field):
                box = self.run_v2_v3(mutate)
                guard = [e for e in box.events() if e["event"] == "HEALTH_UNREADABLE_GUARD"]
                self.assertEqual(guard[0]["fields"], [field])
                self.assertEqual(box.states[1]["runner"]["controller_guard_reason"], "HEALTH_UNREADABLE_GUARD")
                self.assertEqual(box.kills[0], (box.processes[0].pid, signal.SIGINT))

    def test_unreadable_health_without_runner_is_recorded_and_ignored(self):
        box = Sandbox(self, ticks=2)
        box.health = OSError("meminfo unavailable")
        self.assertEqual(box.serve(), 0)
        self.assertEqual(box.kills, [])
        self.assertNotIn("HEALTH_UNREADABLE_GUARD", box.event_names())
        self.assertIn("meminfo unavailable", box.states[1]["last_health"]["health_error"])
        self.assertEqual([s["status"] for s in box.states], ["MONITORING", "MONITORING"])

    def test_diagnosis_without_guarded_result_writes_nothing(self):
        box = Sandbox(self)
        self.assertIsNone(controller.diagnose_safety_stop({}))
        self.assertFalse(controller.CONTROLLER_DIAGNOSTICS.exists())


class StopTests(unittest.TestCase):
    def test_stop_command_interrupts_active_runner_and_writes_stop_file(self):
        box = Sandbox(self, ticks=2)
        box.command("ARM_PILOT", "arm-1")
        box.hooks[0] = lambda: box.command("STOP", "stop-1", approved=None)
        seen: list[str] = []
        box.hooks[1] = lambda: seen.append((controller.QUALITY_BASE / "STOP").read_text())
        box.serve()
        pid = box.processes[0].pid
        self.assertEqual(box.states[1]["status"], "STOP_REQUESTED")
        self.assertEqual(box.kills[0], (pid, signal.SIGINT))
        self.assertIn("Controller stop request stop-1", seen[0])
        self.assertIn("STOP_REQUESTED", box.event_names())

    def test_stop_without_active_runner_only_writes_stop_file(self):
        box = Sandbox(self)
        box.command("STOP", "stop-1", approved=None)
        box.serve()
        self.assertEqual(box.kills, [])
        self.assertTrue((controller.QUALITY_BASE / "STOP").is_file())
        self.assertEqual(box.states[0]["status"], "STOP_REQUESTED")

    def test_controller_shutdown_stops_active_runner(self):
        box = Sandbox(self)
        box.command("ARM_PILOT")
        box.serve()
        pid = box.processes[0].pid
        self.assertEqual(box.kills, [(pid, signal.SIGINT)])
        self.assertIn("CONTROLLER_SHUTDOWN", (controller.QUALITY_BASE / "STOP").read_text())
        self.assertEqual(box.final_state()["status"], "CONTROLLER_STOPPED")


class InvalidInputTests(unittest.TestCase):
    def test_command_validation(self):
        good = {"schema_version": 1, "request_id": "r", "action": "ARM_PILOT", "approved": True}
        cases = [
            ([], "COMMAND_NOT_AN_OBJECT"),
            ({**good, "schema_version": 2}, "UNSUPPORTED_COMMAND_SCHEMA"),
            ({**good, "request_id": "  "}, "REQUEST_ID_REQUIRED"),
            ({**good, "request_id": 5}, "REQUEST_ID_REQUIRED"),
            ({**good, "action": "DELETE_EVERYTHING"}, "UNSUPPORTED_ACTION"),
            ({**good, "approved": "yes"}, "EXPLICIT_APPROVAL_REQUIRED"),
            ({**good, "action": "RESUME_V2_V3", "approved": False}, "EXPLICIT_APPROVAL_REQUIRED"),
            (good, None),
            ({"schema_version": 1, "request_id": "r", "action": "STOP"}, None),
        ]
        for command, expected in cases:
            with self.subTest(command=command):
                self.assertEqual(controller.command_error(command), expected)

    def test_unapproved_command_is_rejected_without_launch(self):
        box = Sandbox(self)
        box.command("ARM_PILOT", approved=None)
        box.serve()
        self.assertEqual(box.processes, [])
        self.assertIsNone(box.states[0]["last_command_id"])
        rejected = [e for e in box.events() if e["event"] == "COMMAND_REJECTED"]
        self.assertEqual(rejected[0]["reason"], "EXPLICIT_APPROVAL_REQUIRED")

    def test_corrupt_command_file_is_ignored(self):
        box = Sandbox(self)
        controller.BASE.mkdir(parents=True)
        controller.COMMAND_PATH.write_text("{truncated")
        self.assertEqual(box.serve(), 0)
        self.assertEqual(box.processes, [])
        self.assertNotIn("COMMAND_REJECTED", box.event_names())

    def rejected(self, box: Sandbox) -> list[dict]:
        return [e for e in box.events() if e["event"] == "COMMAND_REJECTED"]

    def test_identical_invalid_command_is_logged_once_per_process(self):
        box = Sandbox(self, ticks=4)
        box.command("ARM_PILOT", approved=None)
        box.serve()
        self.assertEqual(len(self.rejected(box)), 1)
        self.assertEqual(len(self.rejected(box)[0]["command_sha256"]), 64)

    def test_changed_invalid_command_is_logged_again(self):
        box = Sandbox(self, ticks=3)
        box.command("ARM_PILOT", approved=None)
        box.hooks[0] = lambda: box.command("NOT_AN_ACTION", approved=None)
        box.serve()
        self.assertEqual([e["reason"] for e in self.rejected(box)], ["EXPLICIT_APPROVAL_REQUIRED", "UNSUPPORTED_ACTION"])

    def test_valid_command_resets_invalid_command_dedupe(self):
        box = Sandbox(self, ticks=4)
        box.command("ARM_PILOT", "bad-1", approved=None)
        box.hooks[0] = lambda: box.command("STOP", "stop-1", approved=None)
        box.hooks[1] = lambda: box.command("ARM_PILOT", "bad-1", approved=None)
        box.serve()
        self.assertEqual(len(self.rejected(box)), 2)
        self.assertIn("STOP_REQUESTED", box.event_names())
        self.assertEqual(box.processes, [])

    def test_new_controller_process_logs_the_same_invalid_command_again(self):
        box = Sandbox(self, ticks=1)
        box.command("ARM_PILOT", approved=None)
        box.serve()
        box.ticks = 2
        box.serve()
        self.assertEqual(len(self.rejected(box)), 2)

    def test_resume_and_t7_preconditions_are_enforced(self):
        cases = [("RESUME_V2_V3", None, "V2_V3_PLAN_MISSING"),
                 ("RUN_T7_SUPPLEMENT", "RUNNING", "V2_V3_RESULT_NOT_COMPLETE"),
                 ("RUN_T7_SUPPLEMENT", "COMPLETED_REQUESTED_CYCLES", "ROSS_DOCSEARCH_URL_NOT_CONFIGURED")]
        for action, quality, reason in cases:
            with self.subTest(action=action, quality=quality):
                box = Sandbox(self)
                if quality:
                    box.quality(quality)
                box.command(action)
                with patch.dict(os.environ, {}, clear=False):
                    os.environ.pop("AI370_ROSS_DOCSEARCH_URL", None)
                    box.serve()
                self.assertEqual(box.processes, [])
                rejected = [e for e in box.events() if e["event"] == "COMMAND_REJECTED"]
                self.assertEqual(rejected[0]["reason"], reason)


class CliTests(unittest.TestCase):
    def run_cli(self, *argv: str) -> tuple[int, str]:
        with patch.object(sys, "argv", ["local_model_controller.py", *argv]), redirect_stdout(io.StringIO()) as out:
            code = controller.main()
        return code, out.getvalue()

    def test_status_without_state_reports_not_running(self):
        Sandbox(self)
        code, out = self.run_cli("status")
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["status"], "NOT_RUNNING")

    def test_action_commands_write_durable_requests(self):
        Sandbox(self)
        self.assertEqual(self.run_cli("arm-pilot", "--request-id", "arm-1")[0], 0)
        self.assertEqual(controller.read_json(controller.COMMAND_PATH),
                         {"schema_version": 1, "request_id": "arm-1", "action": "ARM_PILOT", "approved": True})
        self.run_cli("stop", "--request-id", "stop-1")
        self.assertEqual(controller.read_json(controller.COMMAND_PATH),
                         {"schema_version": 1, "request_id": "stop-1", "action": "STOP"})

    def test_action_without_request_id_is_a_usage_error(self):
        Sandbox(self)
        with patch("sys.stderr", io.StringIO()), self.assertRaises(SystemExit) as caught:
            self.run_cli("arm-pilot")
        self.assertEqual(caught.exception.code, 2)
        self.assertFalse(controller.COMMAND_PATH.exists())


if __name__ == "__main__":
    unittest.main()
