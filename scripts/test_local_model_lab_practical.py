#!/usr/bin/env python3
"""Lifecycle tests without loading a model, changing services or using a GPU."""
import json
import signal
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import run_local_model_lab_practical as practical


class PracticalLabLifecycleTests(unittest.TestCase):
    def run_failed_calibration(self, restoration_fails=False):
        model = {"key": "qwen38", "relative_path": "test.gguf", "runtime_model_path": "/unused/test.gguf", "model_id": "Qwen3.8-27B-UD-Q4_K_XL", "bytes": 1, "sha256": "unused"}
        config = {"model_root": "unused", "models": [model], "provider": {"api_base": "http://127.0.0.1:13305/api/v1"}}
        inventory = [{"key": "qwen38", "sha_matches": True, "observed_bytes": 1}]
        previous = {sig: signal.getsignal(sig) for sig in [signal.SIGINT, signal.SIGTERM]}
        try:
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                for relative in ['scripts/local_agent.py', 'scripts/run_local_model_lab_practical.py', 'scripts/run_local_model_lab.py', 'scripts/run_ross_ab_t1.py', 'scripts/run_ross_ab_t2.py', 'scripts/run_ross_ab_hls.py', 'config/local_model_lab.json']:
                    fixture = root / relative
                    fixture.parent.mkdir(parents=True, exist_ok=True)
                    fixture.write_text('isolated lifecycle fixture\n')
                verifies = [(model, [model["model_id"]]), RuntimeError("restore verification failed")] if restoration_fails else [(model, [model["model_id"]])] * 2
                with patch.object(practical, "ROOT", root), patch.object(practical.lab, "load_config", return_value=config), patch.object(practical.lab, "inventory", return_value=inventory), patch.object(practical.lab, "verify_active_model", side_effect=verifies), patch.object(practical.lab, "active_llama_server", side_effect=[["llama-server", "-m", model["runtime_model_path"]], []]), patch.object(practical, "calibration", side_effect=RuntimeError("controlled calibration failure")), patch.object(practical.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, "restored", "")) as commands, patch.object(sys, "argv", ["run_local_model_lab_practical.py"]):
                    self.assertEqual(practical.main(), 1)
                    result = json.loads(next((root / "output/LOCAL_MODEL_LAB_PRACTICAL").glob("*/result.json")).read_text())
                    called = [call.args[0] for call in commands.call_args_list]
                    self.assertEqual(called[0][:2], ["lemonade", "unload"])
                    self.assertEqual(called[-1][:2], ["lemonade", "load"])
                    self.assertNotIn("--save-options", called[-1])
                    self.assertEqual(result["status"], "BLOCKED")
                    return result
        finally:
            for sig, handler in previous.items():
                signal.signal(sig, handler)

    def test_failed_experiment_restores_formal_model(self):
        result = self.run_failed_calibration()
        self.assertEqual(result["formal_model_restoration"], "PASS")

    def test_failed_restoration_never_claims_ready(self):
        result = self.run_failed_calibration(restoration_fails=True)
        self.assertTrue(result["formal_model_restoration"].startswith("FAIL:"))


if __name__ == "__main__":
    unittest.main()
