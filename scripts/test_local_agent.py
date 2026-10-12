#!/usr/bin/env python3
"""Local Agent policy tests; no model request or system modification."""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import local_agent


class LocalAgentPolicyTests(unittest.TestCase):
    def test_only_loopback_provider_is_accepted(self):
        self.assertTrue(local_agent._loopback_endpoint("http://127.0.0.1:13305/api/v1").startswith("http://127.0.0.1"))
        with self.assertRaises(local_agent.AgentError):
            local_agent._loopback_endpoint("https://api.openai.com/v1")

    def test_path_policy_blocks_traversal_and_resource_roots(self):
        with tempfile.TemporaryDirectory(dir=local_agent.ROOT / "output") as temp:
            root = Path(temp)
            (root / "safe.txt").write_text("safe\n")
            self.assertEqual(local_agent._relative_path(root, "safe.txt"), root / "safe.txt")
            for path in ("../README.md", "resources/model.gguf", ".env"):
                with self.subTest(path=path), self.assertRaises(local_agent.AgentError):
                    local_agent._relative_path(root, path)

    def test_patch_must_target_one_file(self):
        patch = "--- a/rtl/a.v\n+++ b/rtl/a.v\n@@ -1 +1 @@\n-old\n+new\n"
        self.assertEqual(local_agent._patch_paths(patch), ["rtl/a.v"])
        two = patch + "--- a/rtl/b.v\n+++ b/rtl/b.v\n@@ -1 +1 @@\n-x\n+y\n"
        with self.assertRaises(local_agent.AgentError):
            local_agent._patch_paths(two)

    def test_model_authored_exact_replacement_is_applied_without_logic_rewrite(self):
        with tempfile.TemporaryDirectory(dir=local_agent.ROOT / "output") as temp:
            root = Path(temp)
            rtl = root / "rtl/local_model_axi_lite.v"
            rtl.parent.mkdir()
            original = "module m;\n  assign result = input_reg ^ offset_reg;\nendmodule\n"
            rtl.write_text(original)
            (root / "run_validation.sh").write_text("#!/bin/sh\nexit 0\n")
            agent = local_agent.LocalAgent(root, task="test", xsim_enabled=True, editable_paths={"rtl/local_model_axi_lite.v"})
            agent.validation_count = 1
            with self.assertRaises(local_agent.AgentError):
                agent._tool("apply_replacement", {"path": "rtl/local_model_axi_lite.v", "old_text": "input_reg ^ offset_reg", "new_text": "input_reg + offset_reg"})
            agent.last_failed_patch = "malformed model-authored unified diff"
            result = agent._tool("apply_replacement", {
                "path": "rtl/local_model_axi_lite.v",
                "old_text": "input_reg ^ offset_reg",
                "new_text": "input_reg + offset_reg",
            })
            self.assertTrue(result["ok"])
            self.assertEqual(rtl.read_text(), original.replace("input_reg ^ offset_reg", "input_reg + offset_reg"))
            self.assertEqual(agent.patch_count, 1)


if __name__ == "__main__":
    unittest.main()
