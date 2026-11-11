#!/usr/bin/env python3
"""Offline tests for run_quality_remediation_fixtures.

ROOT and OUT are redirected to a system temp dir and subprocess.run is mocked,
so neither the unit-test suites nor the corpus validator actually execute.
"""
from __future__ import annotations

import io
import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_quality_remediation_fixtures as fixtures

REPO = Path(__file__).resolve().parents[1]
FIXED = datetime(2026, 11, 9, 1, 2, 3, tzinfo=timezone.utc)
RUN_ID = "20261109T010203Z"


class FixedDatetime(datetime):
    @classmethod
    def now(cls, tz=None):
        return FIXED if tz is None else FIXED.astimezone(tz)


class RemediationFixtureTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()
        self.out = self.root / "output" / "LOCAL_MODEL_CONTROLLER" / "remediation-fixtures"
        self.calls: list[tuple[list[str], dict]] = []
        self.outcomes: list[object] = []
        for target, value in (("ROOT", self.root), ("OUT", self.out), ("datetime", FixedDatetime)):
            self._start(patch.object(fixtures, target, value))
        self.assertFalse(str(fixtures.OUT).startswith(str(REPO)))
        self._start(patch.object(fixtures.subprocess, "run", side_effect=self._run))
        self._start(patch.object(fixtures.subprocess, "Popen", side_effect=AssertionError("Popen not allowed")))
        clock = [100.0, 112.3456]
        self._start(patch.object(fixtures.time, "monotonic", side_effect=lambda: clock.pop(0) if len(clock) > 1 else clock[0]))

    def _start(self, patcher):
        patcher.start()
        self.addCleanup(patcher.stop)

    def _run(self, command, **kwargs):
        self.calls.append((command, kwargs))
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome

    def ok(self, code=0, stdout="ok", stderr=""):
        return subprocess.CompletedProcess([], code, stdout, stderr)

    def run_main(self) -> tuple[int, dict]:
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            code = fixtures.main()
        return code, json.loads(stdout.getvalue())

    def report(self) -> dict:
        return json.loads((self.out / RUN_ID / "report.json").read_text())

    def test_runs_exact_commands_without_shell_in_order(self):
        self.outcomes = [self.ok(), self.ok()]
        code, printed = self.run_main()
        self.assertEqual(code, 0)
        self.assertEqual([c for c, _ in self.calls], [
            [sys.executable, "-m", "unittest", "scripts/test_quality_local_agent.py", "scripts/test_quality_pilot.py"],
            [sys.executable, "scripts/validate_quality_corpus.py", "--task", "all"],
        ])
        for (command, kwargs), timeout in zip(self.calls, (120, 10800)):
            self.assertIsInstance(command, list)
            self.assertFalse(kwargs.get("shell", False))
            self.assertEqual(kwargs, {"cwd": self.root, "capture_output": True, "text": True, "timeout": timeout})
        self.assertEqual(printed, {"status": "PASS",
                                   "report": f"output/LOCAL_MODEL_CONTROLLER/remediation-fixtures/{RUN_ID}/report.json"})

    def test_referenced_fixture_scripts_exist_in_repo(self):
        for name in ("scripts/test_quality_local_agent.py", "scripts/test_quality_pilot.py",
                     "scripts/validate_quality_corpus.py"):
            self.assertTrue((REPO / name).is_file(), name)

    def test_all_pass_writes_per_step_and_report_evidence(self):
        self.outcomes = [self.ok(stdout="unit ok"), self.ok(stdout="corpus ok", stderr="warn")]
        self.run_main()
        folder = self.out / RUN_ID
        self.assertEqual(sorted(p.name for p in folder.iterdir()),
                         ["agent_unit_tests.json", "corpus_fixtures.json", "report.json"])
        report = self.report()
        self.assertEqual(report["stage"], "REMEDIATION_FIXTURES")
        self.assertEqual(report["run_id"], RUN_ID)
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["elapsed_seconds"], 12.346)
        self.assertEqual([r["name"] for r in report["results"]], ["agent_unit_tests", "corpus_fixtures"])
        self.assertEqual(report["results"][1]["stderr"], "warn")
        step = json.loads((folder / "corpus_fixtures.json").read_text())
        self.assertEqual(step, report["results"][1])
        self.assertEqual(step["exit_code"], 0)
        self.assertEqual(step["stdout"], "corpus ok")

    def test_first_failure_stops_and_propagates(self):
        self.outcomes = [self.ok(code=1, stdout="FAILED (failures=1)")]
        code, printed = self.run_main()
        self.assertEqual(code, 1)
        self.assertEqual(printed["status"], "FAIL")
        self.assertEqual(len(self.calls), 1)
        report = self.report()
        self.assertEqual(report["status"], "FAIL")
        self.assertEqual([r["exit_code"] for r in report["results"]], [1])
        self.assertFalse((self.out / RUN_ID / "corpus_fixtures.json").exists())

    def test_second_failure_is_fail(self):
        self.outcomes = [self.ok(), self.ok(code=2)]
        code, _ = self.run_main()
        self.assertEqual(code, 1)
        self.assertEqual([r["exit_code"] for r in self.report()["results"]], [0, 2])
        self.assertEqual(self.report()["status"], "FAIL")

    def test_negative_signal_exit_is_fail(self):
        self.outcomes = [self.ok(), self.ok(code=-9)]
        self.assertEqual(self.run_main()[0], 1)

    def test_timeout_records_error_and_stops(self):
        self.outcomes = [subprocess.TimeoutExpired(["x"], 120, output="partial", stderr=None)]
        code, _ = self.run_main()
        self.assertEqual(code, 1)
        self.assertEqual(len(self.calls), 1)
        result = self.report()["results"][0]
        self.assertIsNone(result["exit_code"])
        self.assertEqual(result["error"], "TimeoutExpired after 120s")
        self.assertEqual((result["stdout"], result["stderr"]), ("partial", ""))

    def test_timeout_with_captured_bytes_still_writes_report(self):
        # Regression: on POSIX, subprocess.run(text=True) raises TimeoutExpired with
        # *bytes* stdout/stderr, which json.dumps used to reject with TypeError.
        self.outcomes = [subprocess.TimeoutExpired(["x"], 120, output=b"partial", stderr=b"")]
        code, _ = self.run_main()
        self.assertEqual(code, 1)
        self.assertEqual(self.report()["results"][0]["stdout"], "partial")

    def test_output_is_truncated_to_last_8000_chars(self):
        self.outcomes = [self.ok(stdout="a" * 100 + "b" * 8000, stderr="c" * 9000), self.ok()]
        self.run_main()
        result = self.report()["results"][0]
        self.assertEqual(result["stdout"], "b" * 8000)
        self.assertEqual(len(result["stderr"]), 8000)

    def test_existing_run_folder_is_never_overwritten(self):
        folder = self.out / RUN_ID
        folder.mkdir(parents=True)
        (folder / "report.json").write_text("ORIGINAL")
        with self.assertRaises(FileExistsError):
            fixtures.main()
        self.assertEqual(self.calls, [])
        self.assertEqual((folder / "report.json").read_text(), "ORIGINAL")


if __name__ == "__main__":
    unittest.main()
