#!/usr/bin/env python3
"""Offline tests for run_all_model_speed.

evidence.ROOT/HOME/LOCK/RUN/STOP are redirected to a system temp tree with fake
.gguf files. The performance runner (bench.run_case), process stop, health API,
signal installation, subprocess and sleep are mocked: no server or model starts.
"""
from __future__ import annotations

import fcntl
import io
import json
import signal
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import warnings
from contextlib import redirect_stdout
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_all_model_speed as speed

bench, evidence = speed.bench, speed.evidence
REPO = Path(__file__).resolve().parents[1]
SIZES = {"big.gguf": 300, "small.gguf": 100, "mid.gguf": 200, "mmproj-big.gguf": 50,
         "sd-turbo.gguf": 60, "Qwen3-Embedding-0.6B.gguf": 70, "notes.txt": 10}


class FixedDatetime(datetime):
    @classmethod
    def now(cls, tz=None):
        value = datetime(2026, 11, 9, 1, 2, 3, tzinfo=timezone.utc)
        return value if tz is None else value.astimezone(tz)


RUN_NAME = FixedDatetime.now().astimezone().strftime("%Y%m%dT%H%M%S%z")


def forbid(*_args, **_kwargs):
    raise AssertionError("no real process, server or sleep may be used")


def row(model: str, backend: str, rates=(10.0, 12.0, 11.0), status="PASS", **extra) -> dict:
    trials = [dict(generation_tokens_per_second=r, prompt_tokens_per_second=r * 10) for r in rates]
    return dict(status=status, model=model, config=dict(backend=backend), trials=trials,
                resources={}, kernel_audit=dict(read_exit=0, faults=[]), **extra)


class Sandbox:
    def __init__(self, case: unittest.TestCase):
        temp = tempfile.TemporaryDirectory()
        case.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()
        self.home = self.root / "output/model-endurance"
        self.lock = self.root / "output/local-agent-operation.lock"
        (self.root / "models").mkdir()
        for name, size in SIZES.items():
            (self.root / "models" / name).write_bytes(b"\0" * size)
        self.stop = threading.Event()
        self.calls: list[tuple[dict, dict, Path, str]] = []
        self.handlers: dict[int, object] = {}
        self.health = {"model_loaded": False}
        self.on_case = lambda n, model, backend: row(model["id"], backend)

        def start(patcher):
            patcher.start()
            case.addCleanup(patcher.stop)

        for name, value in (("ROOT", self.root), ("HOME", self.home), ("LOCK", self.lock),
                            ("RUN", None), ("STOP", self.stop), ("datetime", FixedDatetime)):
            start(patch.object(evidence, name, value))
        case.assertFalse(str(evidence.HOME).startswith(str(REPO)))
        start(patch.object(evidence, "api", side_effect=lambda path, *a, **k: dict(self.health)))
        start(patch.object(bench, "run_case", side_effect=self._run_case))
        start(patch.object(bench, "CHILD", "CHILD-SENTINEL"))
        self.stopped = []
        start(patch.object(bench.shared, "stop", side_effect=self.stopped.append))
        start(patch.object(signal, "signal", side_effect=lambda sig, handler: self.handlers.__setitem__(sig, handler)))
        for target in ("Popen", "run", "call", "check_call", "check_output"):
            start(patch.object(subprocess, target, side_effect=forbid))
        start(patch.object(time, "sleep", side_effect=forbid))
        self.run = self.root / "output/ALL_MODEL_SPEED" / RUN_NAME

    def _run_case(self, model, profile, directory, phase):
        self.calls.append((model, profile, directory, phase))
        return self.on_case(len(self.calls), model, profile["backend"])

    def main(self):
        out = io.StringIO()
        with redirect_stdout(out), warnings.catch_warnings():
            warnings.simplefilter("ignore", ResourceWarning)  # main() holds the lock file for its lifetime
            try:
                speed.main()
            except Exception as exc:
                raise exc.with_traceback(None)  # release main()'s frame (and lock file) inside this filter
        return [json.loads(line) for line in out.getvalue().splitlines() if line.strip()]

    def touch_stop(self):
        (self.home / "STOP").touch()


class AllModelSpeedTests(unittest.TestCase):
    def test_selects_installed_generation_models_smallest_first_and_stops_on_file(self):
        box = Sandbox(self)

        def on_case(n, model, backend):
            if n == 6:
                box.touch_stop()
            return row(model["id"], backend)
        box.on_case = on_case
        events = box.main()
        order = [(m["id"], p["backend"]) for m, p, _, _ in box.calls]
        self.assertEqual(order, [("small", "vulkan"), ("small", "cpu"), ("mid", "vulkan"), ("mid", "cpu"),
                                 ("big", "vulkan"), ("big", "cpu")])
        protocol = json.loads((box.run / "protocol.json").read_text())
        self.assertEqual(protocol["models"], [dict(id="small", file="small.gguf", bytes=100),
                                              dict(id="mid", file="mid.gguf", bytes=200),
                                              dict(id="big", file="big.gguf", bytes=300)])
        self.assertEqual((protocol["prompt_tokens"], protocol["output_tokens"], protocol["context"],
                          protocol["repetitions"], protocol["backends"]), (512, 128, 4096, 3, ["vulkan", "cpu"]))
        self.assertEqual(protocol["stop_file"], str(box.home / "STOP"))
        self.assertEqual(events[-1]["status"], "STOPPED")
        self.assertEqual(events[-1]["stage"], "ALL_MODEL_SPEED_FINISHED")
        self.assertEqual(events[-1]["reason"], "USER_STOP")
        self.assertEqual(events[-1]["recorded_cases"], 6)

    def test_delegates_speed_profile_and_evidence_directory_to_runner(self):
        box = Sandbox(self)
        box.on_case = lambda n, model, backend: (box.stop.set(), row(model["id"], backend))[1]
        box.main()
        (model, profile, directory, phase), = box.calls
        self.assertEqual(model, dict(id="small", file="small.gguf", bytes=100))
        self.assertEqual(profile, bench.base_config("vulkan"))
        self.assertEqual((profile["context"], profile["prompt_tokens"], profile["output_tokens"]), (4096, 512, 128))
        self.assertEqual(directory, box.run / "cycle-0001" / "small" / "vulkan")
        self.assertEqual(phase, "SPEED")
        self.assertEqual(box.stopped, ["CHILD-SENTINEL"])

    def test_repeats_cycles_until_stop_and_retains_raw_rows(self):
        box = Sandbox(self)

        def on_case(n, model, backend):
            if n == 8:
                box.stop.set()
            return row(model["id"], backend, status="PASS" if n % 2 else "FAIL")
        box.on_case = on_case
        box.main()
        dirs = [d.relative_to(box.run).parts[0] for _, _, d, _ in box.calls]
        self.assertEqual(dirs, ["cycle-0001"] * 6 + ["cycle-0002"] * 2)
        lines = (box.run / "results.jsonl").read_text().splitlines()
        self.assertEqual(len(lines), 8)
        self.assertEqual([json.loads(x)["status"] for x in lines], ["PASS", "FAIL"] * 4)
        self.assertIn("已執行 8 組", (box.run / "REPORT.md").read_text())
        status = json.loads((box.home / "status.json").read_text())
        self.assertEqual((status["reason"], status["recorded_cases"], status["run"]), ("USER_STOP", 8, str(box.run)))
        self.assertTrue((box.run / "events.jsonl").exists())

    def test_stale_stop_file_is_cleared_at_start(self):
        box = Sandbox(self)
        box.home.mkdir(parents=True)
        box.touch_stop()
        box.on_case = lambda n, model, backend: (box.touch_stop(), row(model["id"], backend))[1]
        box.main()
        self.assertEqual(len(box.calls), 1)

    def test_signal_handlers_request_stop(self):
        box = Sandbox(self)

        def on_case(n, model, backend):
            box.handlers[signal.SIGTERM](signal.SIGTERM, None)
            return row(model["id"], backend)
        box.on_case = on_case
        events = box.main()
        self.assertEqual(set(box.handlers), {signal.SIGINT, signal.SIGTERM})
        self.assertTrue(box.stop.is_set())
        self.assertEqual(len(box.calls), 1)
        self.assertEqual(events[-1]["reason"], "USER_STOP")

    def test_severe_kernel_row_ends_run_with_reason(self):
        box = Sandbox(self)
        box.on_case = lambda n, model, backend: row(model["id"], backend) | dict(
            kernel_audit=dict(read_exit=0, faults=["amdgpu page fault"]))
        events = box.main()
        self.assertEqual(len(box.calls), 1)
        self.assertEqual(events[-1]["reason"], "RuntimeError: SEVERE_KERNEL_GATE")
        self.assertEqual(len((box.run / "results.jsonl").read_text().splitlines()), 1)
        self.assertEqual(json.loads((box.run / "summary.json").read_text()), [])
        self.assertEqual(box.stopped, ["CHILD-SENTINEL"])

    def test_runner_exception_is_recorded_and_cleanup_runs(self):
        box = Sandbox(self)

        def on_case(n, model, backend):
            if n == 3:
                raise TimeoutError("PROFILE_WALL_TIMEOUT")
            return row(model["id"], backend)
        box.on_case = on_case
        events = box.main()
        self.assertEqual(events[-1]["reason"], "TimeoutError: PROFILE_WALL_TIMEOUT")
        self.assertEqual(events[-1]["recorded_cases"], 2)
        self.assertEqual(box.stopped, ["CHILD-SENTINEL"])

    def test_refuses_when_a_model_is_already_loaded(self):
        box = Sandbox(self)
        box.health = {"model_loaded": True}
        with self.assertRaisesRegex(RuntimeError, "already loaded"):
            box.main()
        self.assertEqual(box.calls, [])
        self.assertFalse(box.run.exists())

    def test_refuses_when_operation_lock_is_held(self):
        box = Sandbox(self)
        box.lock.parent.mkdir(parents=True, exist_ok=True)
        with box.lock.open("a+") as held:
            fcntl.flock(held, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.assertRaises(BlockingIOError):
                box.main()
        self.assertEqual(box.calls, [])
        self.assertFalse(box.run.exists())

    def test_existing_run_directory_is_not_reused(self):
        box = Sandbox(self)
        box.run.mkdir(parents=True)
        with self.assertRaises(FileExistsError):
            box.main()
        self.assertEqual(box.calls, [])

    def test_no_eligible_models_returns_without_busy_looping(self):
        # Regression: with zero eligible .gguf files the while-loop used to spin (no
        # sleep) until STOP. A bounded fake STOP turns true after 10000 polls.
        box = Sandbox(self)
        for path in (box.root / "models").glob("*.gguf"):
            if not path.name.startswith(("mmproj", "sd", "Qwen3-Embedding")):
                path.unlink()

        class CountingStop:
            polls = 0

            def is_set(self):
                self.polls += 1
                return self.polls > 10000

            def set(self):
                self.polls = 10**9
        counter = CountingStop()
        with patch.object(evidence, "STOP", counter):
            box.main()
        self.assertLess(counter.polls, 100)

    def test_report_ranks_only_safe_rows_and_keeps_all_counts(self):
        box = Sandbox(self)
        run = box.root / "report"
        run.mkdir()
        rows = [row("a", "cpu", rates=(5.0, 7.0, 6.0)),
                row("b", "vulkan", rates=(20.0, 30.0, 25.0)),
                row("a", "cpu", rates=(8.0,)),
                row("c", "vulkan", status="FAIL"),
                row("d", "vulkan") | dict(resources=dict(guard="DISK_GUARD")),
                row("e", "vulkan") | dict(kernel_audit=dict(read_exit=1, faults=[]))]
        speed.report(rows, run)
        summary = json.loads((run / "summary.json").read_text())
        self.assertEqual([(s["model"], s["backend"]) for s in summary], [("b", "vulkan"), ("a", "cpu")])
        self.assertEqual(summary[0], dict(model="b", backend="vulkan", samples=3, generation_tps=25.0,
                                          minimum_tps=20.0, maximum_tps=30.0, prompt_tps=250.0))
        self.assertEqual((summary[1]["samples"], summary[1]["generation_tps"]), (4, 6.5))
        text = (run / "REPORT.md").read_text()
        self.assertIn("| b | vulkan | 3 | 25.00 | 20.00–30.00 | 250.00 |", text)
        self.assertIn("已執行 6 組", text)
        self.assertNotIn("| c |", text)


if __name__ == "__main__":
    unittest.main()
