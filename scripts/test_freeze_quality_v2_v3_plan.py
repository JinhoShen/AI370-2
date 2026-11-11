#!/usr/bin/env python3
"""Offline tests for freeze_quality_v2_v3_plan.

ROOT, QUALITY and OUT are redirected to a system temp tree that holds copies of
the declared harness files and corpus manifests (the real repo is only read).
Nothing is written under the repo's output/, and no subprocess or model starts.
"""
from __future__ import annotations

import ast
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import freeze_quality_v2_v3_plan as freeze

REPO = Path(__file__).resolve().parents[1]
REAL_PLANS = REPO / "output" / "LOCAL_MODEL_CONTROLLER" / "plans"
CORPUS = Path("docs") / "LOCAL_MODEL_LAB" / "quality-corpus" / "v2"
INTEGRITY = Path("20261022T182952+0800") / "model-integrity.json"
FIXED = datetime(2026, 11, 9, 1, 2, 3, tzinfo=timezone.utc)
RUN_ID = "20261109T010203Z"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def plans_snapshot() -> list[str]:
    if not REAL_PLANS.exists():
        return []
    return sorted(str(p) for p in REAL_PLANS.rglob("*"))


class FixedDatetime(datetime):
    @classmethod
    def now(cls, tz=None):
        return FIXED if tz is None else FIXED.astimezone(tz)


def forbid(*_args, **_kwargs):
    raise AssertionError("freeze plan must not start any process")


class FreezePlanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.real_plans_before = plans_snapshot()

    @classmethod
    def tearDownClass(cls):
        assert plans_snapshot() == cls.real_plans_before, "real controller plans directory changed"

    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()
        self.quality = self.root / "output" / "QUALITY_MODEL_VALIDATION"
        self.out = self.root / "output" / "LOCAL_MODEL_CONTROLLER" / "plans"
        for name in freeze.FILES:
            (self.root / name).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(REPO / name, self.root / name)
        for task in (f"T{i}" for i in range(1, 9)):
            for variant in ("V2", "V3"):
                target = self.root / CORPUS / task / variant / "SHA256SUMS.json"
                target.parent.mkdir(parents=True)
                target.write_text(json.dumps({"task": task, "variant": variant}) + "\n")
        (self.quality / INTEGRITY).parent.mkdir(parents=True)
        (self.quality / INTEGRITY).write_text('{"models": 9}\n')
        self.write_status({"status": "PILOT_COMPLETE", "session": "S1", "formal_sample_count": 72})
        for name, value in (("ROOT", self.root), ("QUALITY", self.quality), ("OUT", self.out)):
            patcher = patch.object(freeze, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.assertFalse(str(freeze.OUT).startswith(str(REPO)))
        for target in ("Popen", "run", "call", "check_call", "check_output"):
            patcher = patch.object(subprocess, target, side_effect=forbid)
            patcher.start()
            self.addCleanup(patcher.stop)
        for target in ("system", "execv", "execvp", "fork", "spawnv"):
            patcher = patch.object(os, target, side_effect=forbid)
            patcher.start()
            self.addCleanup(patcher.stop)
        patcher = patch.object(freeze, "datetime", FixedDatetime)
        patcher.start()
        self.addCleanup(patcher.stop)

    def write_status(self, data: dict) -> None:
        self.quality.mkdir(parents=True, exist_ok=True)
        (self.quality / "status.json").write_text(json.dumps(data))

    def run_main(self) -> tuple[int, dict]:
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            code = freeze.main()
        return code, json.loads(stdout.getvalue())

    def test_writes_single_plan_at_timestamped_path_with_expected_shape(self):
        code, printed = self.run_main()
        self.assertEqual(code, 0)
        path = self.out / RUN_ID / "v2-v3-plan.json"
        self.assertEqual(printed, {"status": "PLAN_FROZEN_NOT_STARTED",
                                   "plan": f"output/LOCAL_MODEL_CONTROLLER/plans/{RUN_ID}/v2-v3-plan.json"})
        self.assertEqual([p.name for p in self.out.iterdir()], [RUN_ID])
        self.assertEqual([p.name for p in (self.out / RUN_ID).iterdir()], ["v2-v3-plan.json"])
        plan = json.loads(path.read_text())
        self.assertEqual(set(plan), {"schema_version", "stage", "created_utc", "v1_evidence", "execution",
                                     "harness_sha256", "corpus_manifests_sha256", "model_integrity_sha256",
                                     "t7_policy", "approval"})
        self.assertEqual(plan["schema_version"], 1)
        self.assertEqual(plan["stage"], "V2_V3_POST_PILOT_PLAN")
        self.assertEqual(plan["approval"], "PLAN_FROZEN_NOT_STARTED")
        self.assertEqual(plan["created_utc"], FIXED.isoformat())
        self.assertEqual(plan["v1_evidence"], {"session": "S1", "status": "PILOT_COMPLETE", "samples": 72})
        self.assertEqual(plan["execution"], {
            "variants": ["V2", "V3"], "models": 9, "tasks_per_model": 8, "expected_samples": 144,
            "command": ["python3", "scripts/run_quality_pilot.py", "--variants", "V2", "V3", "--max-cycles", "1"]})
        self.assertEqual(plan["execution"]["models"] * plan["execution"]["tasks_per_model"] * 2,
                         plan["execution"]["expected_samples"])
        self.assertIn("BLOCKED", plan["t7_policy"])
        self.assertTrue(path.read_text().endswith("\n"))

    def test_harness_hashes_cover_exactly_declared_files_and_match_real_repo(self):
        self.run_main()
        plan = json.loads((self.out / RUN_ID / "v2-v3-plan.json").read_text())
        self.assertEqual(list(plan["harness_sha256"]), list(freeze.FILES))
        self.assertEqual(len(set(freeze.FILES)), len(freeze.FILES))
        for name, value in plan["harness_sha256"].items():
            self.assertEqual(value, digest(REPO / name), name)
            self.assertRegex(value, r"^[0-9a-f]{64}$")

    def test_harness_hash_changes_when_a_declared_file_changes(self):
        target = self.root / freeze.FILES[0]
        target.write_text(target.read_text() + "\n# drift\n")
        self.run_main()
        plan = json.loads((self.out / RUN_ID / "v2-v3-plan.json").read_text())
        self.assertEqual(plan["harness_sha256"][freeze.FILES[0]], digest(target))
        self.assertNotEqual(plan["harness_sha256"][freeze.FILES[0]], digest(REPO / freeze.FILES[0]))

    def test_corpus_manifests_and_model_integrity_hashes(self):
        self.run_main()
        plan = json.loads((self.out / RUN_ID / "v2-v3-plan.json").read_text())
        expected = {f"T{i}/{v}": digest(self.root / CORPUS / f"T{i}" / v / "SHA256SUMS.json")
                    for i in range(1, 9) for v in ("V2", "V3")}
        self.assertEqual(plan["corpus_manifests_sha256"], expected)
        self.assertEqual(len(expected), 16)
        self.assertNotIn("T1/V1", plan["corpus_manifests_sha256"])
        self.assertEqual(plan["model_integrity_sha256"], digest(self.quality / INTEGRITY))

    def test_real_repo_ships_every_declared_hash_input(self):
        for name in freeze.FILES:
            self.assertTrue((REPO / name).is_file(), name)
        for i in range(1, 9):
            for variant in ("V2", "V3"):
                self.assertTrue((REPO / CORPUS / f"T{i}" / variant / "SHA256SUMS.json").is_file())

    def test_sha_streams_large_file_correctly(self):
        blob = self.root / "big.bin"
        blob.write_bytes(os.urandom(9 * 1024 * 1024 + 7))
        self.assertEqual(freeze.sha(blob), digest(blob))

    def test_never_overwrites_an_existing_plan(self):
        existing = self.out / RUN_ID / "v2-v3-plan.json"
        existing.parent.mkdir(parents=True)
        existing.write_text("ORIGINAL\n")
        with self.assertRaises(FileExistsError):
            self.run_main()
        self.assertEqual(existing.read_text(), "ORIGINAL\n")
        self.assertEqual(list(existing.parent.iterdir()), [existing])

    def test_second_freeze_in_same_second_is_refused(self):
        self.run_main()
        first = (self.out / RUN_ID / "v2-v3-plan.json").read_text()
        with self.assertRaises(FileExistsError):
            self.run_main()
        self.assertEqual((self.out / RUN_ID / "v2-v3-plan.json").read_text(), first)

    def test_requires_pilot_complete_and_writes_nothing_otherwise(self):
        for status in ({"status": "PILOT_RUNNING"}, {"status": "FAILED"}, {}):
            with self.subTest(status=status):
                self.write_status(status)
                with self.assertRaises(SystemExit) as raised:
                    freeze.main()
                self.assertIn("PILOT_COMPLETE", str(raised.exception.code))
                self.assertFalse(self.out.exists())

    def test_missing_status_writes_nothing(self):
        (self.quality / "status.json").unlink()
        with self.assertRaises(FileNotFoundError):
            freeze.main()
        self.assertFalse(self.out.exists())

    def test_missing_hash_inputs_never_produce_a_plan_file(self):
        missing = (self.quality / INTEGRITY, self.root / CORPUS / "T8" / "V3" / "SHA256SUMS.json",
                   self.root / freeze.FILES[-1])
        for victim in missing:
            with self.subTest(missing=victim.name):
                saved = victim.read_bytes()
                victim.unlink()
                try:
                    with self.assertRaises(FileNotFoundError):
                        freeze.main()
                    # Regression: no empty timestamped folder may be left in the plans tree.
                    self.assertFalse(self.out.exists())
                finally:
                    victim.write_bytes(saved)
                    shutil.rmtree(self.out, ignore_errors=True)

    def test_module_imports_no_process_or_network_machinery(self):
        tree = ast.parse(Path(freeze.__file__).read_text())
        names = {alias.name.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names}
        names |= {node.module.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module}
        self.assertEqual(names - {"__future__"}, {"hashlib", "json", "datetime", "pathlib"})


if __name__ == "__main__":
    unittest.main()
