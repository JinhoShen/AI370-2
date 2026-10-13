import importlib.util
import unittest
from pathlib import Path

SCRIPT = Path(__file__).with_name("run_local_model_lab.py")
SPEC = importlib.util.spec_from_file_location("run_local_model_lab", SCRIPT)
lab = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(lab)


class LocalModelLabTests(unittest.TestCase):
    def test_config_has_five_roster_entries_and_fixed_sequence(self):
        config = lab.load_config()
        self.assertEqual(len(config["models"]), 5)
        self.assertEqual(config["fixed_sequence"], ["A1", "B1", "B2", "A2", "A3", "B3"])
        self.assertEqual(set(config["tasks"]), {"T1", "T2", "T3"})

    def test_task_timeouts_are_fixed_and_context_is_bounded(self):
        config = lab.load_config()
        self.assertEqual(config["provider"]["context"], 8192)
        self.assertEqual(config["provider"]["threads"], 24)
        self.assertEqual(config["tasks"]["T2"]["request_timeout_seconds"], 900)
        self.assertEqual(config["tasks"]["T2"]["tool_call_cap"], 14)

    def test_missing_candidates_fail_closed_without_provider(self):
        config = lab.load_config()
        for key in ("gpt_oss_20b", "devstral_small_2_24b", "reserved"):
            with self.assertRaises(RuntimeError):
                lab.verify_active_model(config, key, "http://127.0.0.1:8001/v1")

    def test_provider_url_rejects_non_loopback(self):
        with self.assertRaises(ValueError):
            lab.api_models("https://example.com/v1")

    def test_qwen_configuration_uses_only_existing_model_path(self):
        model = lab.model_for(lab.load_config(), "qwen38")
        self.assertTrue((Path("resources/Agent_Tools_Docs/04_Local_AI/GGUF") / model["relative_path"]).is_file())
        self.assertEqual(model["bytes"], 17559178144)

    def test_normalization_preserves_failed_trials(self):
        rows = lab.normalize_run("qwen38", "T2", {"trials": [
            {"trial": "A1", "agent_status": "PASS", "elapsed_seconds": 4},
            {"trial": "B1", "agent_status": "FAIL", "elapsed_seconds": 7, "ross_call_count": 2},
        ]})
        self.assertEqual([row["status"] for row in rows], ["PASS", "FAIL"])
        self.assertEqual([row["arm"] for row in rows], ["non_ross", "ross"])
        summary = lab.summarize_trials(rows)
        self.assertEqual(summary["non_ross"]["success_rate"], 1.0)
        self.assertEqual(summary["ross"]["failures_included"], 1)

    def test_legacy_multifile_completed_status_requires_real_xsim_marker(self):
        rows = lab.normalize_run("qwen38", "T2", [
            {"trial": "A1", "agent_status": "COMPLETED", "model_patch_count": 1, "xsim_pass_markers": 1},
            {"trial": "B1", "agent_status": "COMPLETED", "model_patch_count": 0, "xsim_pass_markers": 0},
        ])
        self.assertEqual([row["status"] for row in rows], ["PASS", "FAIL"])


if __name__ == "__main__":
    unittest.main()
