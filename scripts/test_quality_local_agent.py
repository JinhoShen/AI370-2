#!/usr/bin/env python3
from __future__ import annotations

import sys
import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import prepare_quality_workspace as workspace_builder
from quality_local_agent import QualityAgent, validate_t8_delivery_summary
from local_agent import AgentError


class QualityAgentPolicyTests(unittest.TestCase):
    def setUp(self):
        # Materialize the frozen, version-controlled T1/V1 public corpus in the
        # system temp dir so a fresh clone does not depend on ignored output/.
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        with patch.object(workspace_builder, "OUTPUT", Path(temp.name) / "quality"):
            record = workspace_builder.prepare("T1", "V1", "fixture-smoke", "fixture-only")
        self.workspace = Path(record["workspace"])
        self.agent = QualityAgent(
            task="T1", task_id="T1", variant="V1", workspace=self.workspace,
            model="fixture-only", base_url="http://127.0.0.1:18082/v1",
            timeout=3, total_timeout=60, completion_tokens=128, max_calls=4,
            editable_paths={"rtl/axi_regs.sv"}, trace=None,
        )

    def tearDown(self):
        self.agent.close()

    def test_fixture_workspace_comes_from_versioned_corpus_in_system_temp(self):
        self.assertTrue(self.workspace.resolve().is_relative_to(Path(tempfile.gettempdir()).resolve()))
        self.assertFalse(self.workspace.is_relative_to(ROOT))
        corpus = ROOT / "docs/LOCAL_MODEL_LAB/quality-corpus/v2/T1/V1/public"
        for relative in ("TASK_SPEC.md", "rtl/axi_regs.sv"):
            self.assertEqual((self.workspace / relative).read_bytes(), (corpus / relative).read_bytes())

    def test_tool_surface_is_fixed_and_has_no_shell_or_legacy_runner(self):
        offered = {tool["function"]["name"] for tool in self.agent.tool_calls}
        self.assertEqual(offered, {"list_files", "read_file", "apply_patch", "apply_replacement", "run_quality_validation"})

    def test_source_patch_is_blocked_until_unchanged_baseline(self):
        result = self.agent._tool("apply_patch", {"patch": "not a patch"})
        self.assertEqual(result["stage"], "patch-check")
        self.assertIn("baseline", result["error"])

    def test_source_patch_is_allowed_after_failed_baseline(self):
        self.agent.quality_validation_count = 1
        self.agent.patch_count = 0
        result = self.agent._tool("apply_patch", {"patch": "not a patch"})
        self.assertNotIn("Run the fixed validator and inspect its failure", result.get("error", ""))

    def test_validation_tool_accepts_no_model_controlled_arguments(self):
        result = self.agent._tool("run_quality_validation", {"task": "T7", "command": "rm -rf"})
        self.assertFalse(result["ok"])
        self.assertEqual(result["stage"], "xsim")
        self.assertIn("no arguments", result["error"])

    def test_t7_is_blocked_without_real_ross_endpoint(self):
        with self.assertRaisesRegex(AgentError, "Ross Skill reader"):
            QualityAgent(task="T7", task_id="T7", variant="V1", workspace=self.workspace,
                         model="fixture-only", base_url="http://127.0.0.1:18082/v1",
                         timeout=3, total_timeout=60, completion_tokens=128, max_calls=4,
                         editable_paths={"rtl/calc_top.sv"}, trace=None)

    def test_t8_delivery_summary_is_bound_to_runner_marker_report_and_source_hash(self):
        with tempfile.TemporaryDirectory() as temp:
            rtl=Path(temp)/"axi_regs.sv"; rtl.write_text("final RTL\n")
            digest=hashlib.sha256(rtl.read_bytes()).hexdigest()
            payload={"xsim":{"terminal_marker":"QUALITY_T8_PASS checks=32"},
                     "synthesis":{"utilization_report":"/evidence/utilization.rpt"}}
            summary=("STATUS=PASS\nXSim=PASS marker=QUALITY_T8_PASS checks=32\n"
                     "SYNTHESIS=PASS report=/evidence/utilization.rpt\nRTL_SHA256="+digest)
            self.assertTrue(validate_t8_delivery_summary(summary,payload,rtl)["pass"])
            self.assertFalse(validate_t8_delivery_summary(summary.replace("utilization.rpt","invented.rpt"),payload,rtl)["pass"])


if __name__ == "__main__":
    unittest.main()
