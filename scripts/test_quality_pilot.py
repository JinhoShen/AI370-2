#!/usr/bin/env python3
from __future__ import annotations

import json
import io
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import patch
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import run_quality_pilot as pilot
import prepare_quality_workspace as workspace_builder
from run_quality_pilot import TASKS, VARIANTS, build_execution_plan, write_sample_not_tested


class QualityPilotScheduleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.models = [{"model": f"model-{i}"} for i in range(9)]

    def test_pilot_is_exactly_one_complete_shared_v1_matrix(self) -> None:
        plan = build_execution_plan(self.models, TASKS, ["V1"], seed=17)
        self.assertEqual(plan["expected_sample_count"], 72)
        self.assertEqual(len(plan["entries"]), 72)
        self.assertEqual({row["variant"] for row in plan["entries"]}, {"V1"})
        self.assertEqual(
            {(row["model"], row["task"]) for row in plan["entries"]},
            {(model["model"], task) for model in self.models for task in TASKS},
        )

    def test_full_cycle_finishes_each_common_variant_before_next(self) -> None:
        plan = build_execution_plan(self.models, TASKS, VARIANTS, seed=17)
        self.assertEqual(plan["expected_sample_count"], 216)
        self.assertEqual(len(plan["entries"]), 216)
        for i, variant in enumerate(VARIANTS):
            rows = plan["entries"][i * 72:(i + 1) * 72]
            self.assertEqual({row["variant"] for row in rows}, {variant})
            self.assertEqual(len({(row["model"], row["task"]) for row in rows}), 72)
        self.assertNotEqual(plan["by_variant"]["V1"]["model_order"], plan["by_variant"]["V2"]["model_order"])

    def test_plan_is_reproducible_and_rejects_duplicate_roster_entries(self) -> None:
        first = build_execution_plan(self.models, TASKS, VARIANTS, seed=20261023)
        second = build_execution_plan(self.models, TASKS, VARIANTS, seed=20261023)
        self.assertEqual(first, second)
        with self.assertRaisesRegex(ValueError, "unique model IDs"):
            build_execution_plan([self.models[0], self.models[0]], TASKS, VARIANTS, seed=1)

    def test_not_tested_is_saved_as_non_formal_without_overwriting_other_rows(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "samples" / "m1" / "T1" / "V1"
            row = write_sample_not_tested(path, "m1", "T1", "V1", "SAFETY_STOP")
            saved = json.loads((path / "sample-result.json").read_text())
        self.assertEqual(row["status"], "NOT_TESTED")
        self.assertFalse(row["formal_sample"])
        self.assertEqual(saved, row)

    def test_all_frozen_variants_materialize_clean_public_workspaces(self) -> None:
        with tempfile.TemporaryDirectory() as temp, patch.object(workspace_builder, "OUTPUT", Path(temp) / "quality"):
            for task in TASKS:
                for variant in VARIANTS:
                    record = workspace_builder.prepare(task, variant, "fixture-smoke", f"{task}-{variant}")
                    workspace = Path(record["workspace"])
                    self.assertTrue((workspace / "TASK_SPEC.md").is_file())
                    self.assertFalse(any("private" in p.parts or ".quality-hidden" in p.parts for p in workspace.rglob("*")))
                    self.assertTrue(all((workspace / path).is_file() for path in record["editable_paths"]))
                    state = pilot.subprocess.run(["git", "status", "--porcelain"], cwd=workspace,
                                                 capture_output=True, text=True, check=True).stdout
                    self.assertEqual(state.strip(), "")


class QualityPilotOrchestratorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.models = [{"model": f"model-{i}", "path": f"/models/model-{i}.gguf",
                        "sha256": f"sha-{i}", "bytes": i + 1, "backend": "vulkan"}
                       for i in range(9)]

    def run_isolated(self, args: list[str], sample_side_effect=None, preflight_status="PASS"):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            base = root / "output" / "QUALITY_MODEL_VALIDATION"
            stop_file = base / "STOP"
            launch = unittest.mock.Mock(return_value=(object(), {"status": "LOADED"}))
            stop_server = unittest.mock.Mock()
            run_sample = unittest.mock.Mock(side_effect=sample_side_effect or
                (lambda model, task, variant, *_: {"model": model["model"], "task": task,
                    "variant": variant, "status": "PASS", "formal_sample": True}))
            with (
                patch.object(pilot, "ROOT", root),
                patch.object(pilot, "BASE", base),
                patch.object(pilot, "STOP_FILE", stop_file),
                patch.object(pilot, "roster", return_value=self.models),
                patch.object(pilot, "server_binary_details", return_value={"sha256": "fixture"}),
                patch.object(pilot, "preflight", return_value={"status": preflight_status, "blockers": [] if preflight_status == "PASS" else ["FIXTURE_BLOCK"]}),
                patch.object(pilot, "launch_server", launch),
                patch.object(pilot, "stop_owned_server", stop_server),
                patch.object(pilot, "run_one_sample", run_sample),
                patch.dict(os.environ, {"AI370_ROSS_DOCSEARCH_URL": "http://fixture.invalid/mcp"}),
                patch.object(sys, "argv", ["run_quality_pilot.py", *args]),
            ):
                with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                    rc = pilot.main()
            status = json.loads((base / "status.json").read_text())
            session = root / status["session"]
            cycle = None
            reports = list(session.glob("cycle-*/cycle-status.json"))
            if reports:
                cycle = json.loads(reports[0].read_text())
            report_files = list(session.glob("cycle-*/REPORT.md"))
            report_text = report_files[0].read_text() if report_files else None
            return rc, status, cycle, run_sample, launch, report_text

    def test_pilot_cli_runs_only_one_72_sample_v1_matrix(self) -> None:
        rc, status, cycle, run_sample, launch, report_text = self.run_isolated(["--pilot-only"])
        self.assertEqual(rc, 0)
        self.assertEqual(status["status"], "PILOT_COMPLETE")
        self.assertEqual(cycle["status"], "PILOT_COMPLETE")
        self.assertEqual(cycle["expected_sample_count"], 72)
        self.assertEqual(len(cycle["samples"]), 72)
        self.assertEqual({row["variant"] for row in cycle["samples"]}, {"V1"})
        self.assertEqual(run_sample.call_count, 72)
        self.assertEqual(launch.call_count, 9)
        report = report_text.splitlines()
        header_index = next(i for i, line in enumerate(report) if line.startswith("| Model |"))
        self.assertEqual(report[header_index].count("|"), report[header_index + 1].count("|"))

    def test_full_cycle_is_variant_major_and_records_216_samples(self) -> None:
        rc, status, cycle, run_sample, launch, _ = self.run_isolated(["--max-cycles", "1"])
        self.assertEqual(rc, 0)
        self.assertEqual(status["status"], "COMPLETED_REQUESTED_CYCLES")
        self.assertEqual(cycle["status"], "COMPLETE")
        self.assertEqual(cycle["expected_sample_count"], 216)
        self.assertEqual(len(cycle["samples"]), 216)
        self.assertEqual([cycle["samples"][i * 72]["variant"] for i in range(3)], VARIANTS)
        self.assertEqual(run_sample.call_count, 216)
        self.assertEqual(launch.call_count, 27)

    def test_t7_supplement_runs_only_the_18_requested_rows(self) -> None:
        rc, status, cycle, run_sample, launch, _ = self.run_isolated(["--variants", "V2", "V3", "--tasks", "T7", "--max-cycles", "1"])
        self.assertEqual(rc, 0)
        self.assertEqual(status["status"], "COMPLETED_REQUESTED_CYCLES")
        self.assertEqual(cycle["stage"], "T7_SUPPLEMENT")
        self.assertEqual(cycle["expected_sample_count"], 18)
        self.assertEqual(len(cycle["samples"]), 18)
        self.assertEqual({row["task"] for row in cycle["samples"]}, {"T7"})
        self.assertEqual(run_sample.call_count, 18)
        self.assertEqual(launch.call_count, 18)

    def test_safety_stop_materializes_remaining_rows_as_not_tested(self) -> None:
        calls = 0
        def stop_after_second(model, task, variant, *_):
            nonlocal calls
            calls += 1
            if calls == 2:
                return {"model": model["model"], "task": task, "variant": variant,
                        "status": "BLOCKED", "formal_sample": True,
                        "guarded_result": {"guard_reason": "SUSTAINED_SWAPOUT_GUARD"}}
            return {"model": model["model"], "task": task, "variant": variant,
                    "status": "PASS", "formal_sample": True}
        rc, status, cycle, _, _, _ = self.run_isolated(["--pilot-only"], sample_side_effect=stop_after_second)
        self.assertEqual(rc, 0)
        self.assertEqual(status["status"], "SAFETY_STOP")
        self.assertEqual(cycle["status"], "SAFETY_STOP")
        self.assertEqual(sum(row["status"] == "BLOCKED" for row in cycle["samples"]), 1)
        self.assertEqual(sum(row["status"] == "NOT_TESTED" for row in cycle["samples"]), 70)
        self.assertEqual(status["formal_sample_count"], 2)

    def test_preflight_failure_never_launches_model(self) -> None:
        rc, status, cycle, _, launch, _ = self.run_isolated([], preflight_status="PREFLIGHT_BLOCKED")
        self.assertEqual(rc, 2)
        self.assertEqual(status["status"], "PREFLIGHT_BLOCKED")
        self.assertIsNone(cycle)
        launch.assert_not_called()

    def test_preflight_cannot_be_shortened_below_five_minutes(self) -> None:
        with patch.object(sys, "argv", ["run_quality_pilot.py", "--preflight-seconds", "299"]):
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as caught:
                    pilot.main()
        self.assertEqual(caught.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
