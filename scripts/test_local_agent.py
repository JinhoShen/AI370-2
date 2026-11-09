#!/usr/bin/env python3
"""Local Agent policy tests; no model request or system modification."""

import sys
import subprocess
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import local_agent


class LocalAgentPolicyTests(unittest.TestCase):
    def test_plain_unified_diff_headers_are_normalized_without_rewriting_source(self):
        raw = '--- rtl/a.v\n+++ rtl/a.v\n@@ -90,99 +90,99 @@\n before\n-old\n+MODEL_SELECTED_NEW\n after\n'
        canonical = local_agent._canonical_patch_headers(raw)
        self.assertEqual(canonical.splitlines()[2:], raw.splitlines()[2:])
        with tempfile.TemporaryDirectory(dir=local_agent.ROOT / 'output') as temp:
            root = Path(temp)
            target = root / 'rtl/a.v'
            target.parent.mkdir()
            target.write_text('before\nold\nafter\n')
            subprocess.run(['git', 'init', '--quiet'], cwd=root, check=True)
            agent = local_agent.LocalAgent(root, task='test', editable_paths={'rtl/a.v'})
            result = agent._tool('apply_patch', {'patch': raw})
            self.assertTrue(result['ok'], result)
            self.assertEqual(target.read_text(), 'before\nMODEL_SELECTED_NEW\nafter\n')

    def test_header_normalization_still_rejects_new_files(self):
        raw = '--- /dev/null\n+++ rtl/new.v\n@@ -0,0 +1 @@\n+module new; endmodule\n'
        with self.assertRaisesRegex(local_agent.AgentError, 'not allowed'):
            local_agent._patch_paths(local_agent._canonical_patch_headers(raw))

    def test_invalid_patch_headers_return_feedback_and_enable_exact_replacement(self):
        with tempfile.TemporaryDirectory(dir=local_agent.ROOT / "output") as temp:
            root = Path(temp)
            rtl = root / "rtl/local_model_axi_lite.v"
            rtl.parent.mkdir()
            rtl.write_text("module m;\n  assign result = input_reg ^ offset_reg;\nendmodule\n")
            (root / "run_validation.sh").write_text("#!/bin/sh\nexit 0\n")
            agent = local_agent.LocalAgent(root, task="test", xsim_enabled=True, editable_paths={"rtl/local_model_axi_lite.v"})
            agent.validation_count = 1
            result = agent._tool("apply_patch", {"patch": "@@\n-old\n+new\n"})
            self.assertFalse(result["ok"])
            self.assertEqual(result["stage"], "patch-check")
            self.assertIn("input_reg ^ offset_reg", rtl.read_text())
            fixed = agent._tool("apply_replacement", {"path": "rtl/local_model_axi_lite.v", "old_text": "input_reg ^ offset_reg", "new_text": "input_reg + offset_reg"})
            self.assertTrue(fixed["ok"])

    def test_multi_file_xsim_requires_final_verification_pass(self):
        self.assertTrue(local_agent._verification_profile_enabled(xsim=False, multi_file_xsim=True, hls=False))
        self.assertTrue(local_agent._verification_profile_enabled(xsim=True, multi_file_xsim=False, hls=False))
        self.assertTrue(local_agent._verification_profile_enabled(xsim=False, multi_file_xsim=False, hls=True))
        self.assertFalse(local_agent._verification_profile_enabled(xsim=False, multi_file_xsim=False, hls=False))

    def test_completion_token_budget_is_bounded(self):
        agent = local_agent.LocalAgent(local_agent.ROOT, task="test", max_completion_tokens=8192)
        self.assertEqual(agent.max_completion_tokens, 8192)
        with self.assertRaisesRegex(local_agent.AgentError, "between 1 and 8192"):
            local_agent.LocalAgent(local_agent.ROOT, task="test", max_completion_tokens=8193)

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

    def test_opt_in_multifile_patch_is_limited_to_two_existing_allowlisted_sources(self):
        patch = ("--- a/rtl/a.v\n+++ b/rtl/a.v\n@@ -1 +1 @@\n-old\n+new\n"
                 "--- a/rtl/b.v\n+++ b/rtl/b.v\n@@ -1 +1 @@\n-x\n+y\n")
        self.assertEqual(local_agent._patch_paths(patch, max_files=2), ["rtl/a.v", "rtl/b.v"])
        with self.assertRaisesRegex(local_agent.AgentError, "at most 1"):
            local_agent._patch_paths(patch)
        three = patch + "--- a/rtl/c.v\n+++ b/rtl/c.v\n@@ -1 +1 @@\n-p\n+q\n"
        with self.assertRaisesRegex(local_agent.AgentError, "at most 2"):
            local_agent._patch_paths(three, max_files=2)

    def test_git_style_multifile_diff_normalizes_each_file_section(self):
        patch = (
            "diff --git a/rtl/a.v b/rtl/a.v\nindex 1111111..2222222 100644\n"
            "--- a/rtl/a.v\n+++ b/rtl/a.v\n@@\n-old\n+new\n"
            "diff --git a/rtl/b.v b/rtl/b.v\nindex 3333333..4444444 100644\n"
            "--- a/rtl/b.v\n+++ b/rtl/b.v\n@@\n-before\n+after\n"
        )
        paths = local_agent._patch_paths(patch, max_files=2)
        normalized = local_agent._normalize_multifile_git_patch(
            patch, paths, {"rtl/a.v": "old\n", "rtl/b.v": "before\n"}
        )
        self.assertEqual(local_agent._patch_paths(normalized, max_files=2), paths)
        self.assertEqual(normalized.count("--- a/"), 2)
        self.assertIn("@@ -1 +1 @@", normalized)

    def test_git_style_bare_hunks_apply_only_at_exact_source_context(self):
        sources = {
            "rtl/a.v": "head\nfirst\nmid\nsecond\ntail\n",
            "rtl/b.v": "begin\nleft\ncenter\nright\nend\n",
        }
        patch = (
            "diff --git a/rtl/a.v b/rtl/a.v\n--- a/rtl/a.v\n+++ b/rtl/a.v\n"
            "@@\n head\n-first\n+FIRST\n@@\n mid\n-second\n+SECOND\n tail\n"
            "diff --git a/rtl/b.v b/rtl/b.v\n--- a/rtl/b.v\n+++ b/rtl/b.v\n"
            "@@\n begin\n-left\n+LEFT\n@@\n center\n-right\n+RIGHT\n end\n"
        )
        with tempfile.TemporaryDirectory(dir=local_agent.ROOT / "output") as temp:
            root = Path(temp)
            for relative, text in sources.items():
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(text)
            subprocess.run(["git", "init", "--quiet"], cwd=root, check=True)
            subprocess.run(["git", "-c", "user.name=AI370-2 test", "-c", "user.email=local@invalid", "add", "rtl"], cwd=root, check=True)
            subprocess.run(["git", "-c", "user.name=AI370-2 test", "-c", "user.email=local@invalid", "commit", "--quiet", "-m", "seed"], cwd=root, check=True)
            paths = local_agent._patch_paths(patch, max_files=2)
            normalized = local_agent._normalize_multifile_git_patch(patch, paths, sources)
            checked = subprocess.run(["git", "apply", "--check", "--whitespace=error", "-"], cwd=root, input=normalized, capture_output=True, text=True)
            self.assertEqual(checked.returncode, 0, checked.stderr)

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

    def test_ross_endpoint_must_be_private_and_fixed_mcp_path(self):
        self.assertTrue(local_agent.LocalAgent._validate_ross_endpoint("http://172.18.0.4:8080/mcp/doc-search").startswith("http://172.18.0.4"))
        for endpoint in ("https://example.com/mcp/doc-search", "http://8.8.8.8/mcp/doc-search", "http://[2001:4860:4860::8888]/mcp/doc-search", "http://127.0.0.1/admin"):
            with self.subTest(endpoint=endpoint), self.assertRaises(local_agent.AgentError):
                local_agent.LocalAgent._validate_ross_endpoint(endpoint)

    def test_ross_skill_reader_is_allowlisted_and_reads_installed_skill(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            skill = root / "vivado-simulate-rtl"
            skill.mkdir()
            (skill / "SKILL.md").write_text("Official Skill text\n")
            agent = local_agent.LocalAgent(local_agent.ROOT, task="test", ross_docsearch_url="http://127.0.0.1:8080/mcp/doc-search", ross_skills_root=root)
            value = agent._tool("ross_skill_read", {"skill": "vivado-simulate-rtl"})
            self.assertIn("Official Skill text", value["files"][0]["text"])
            with self.assertRaises(local_agent.AgentError):
                agent._tool("ross_skill_read", {"skill": "unknown-skill"})

    def test_ross_mode_gates_simulation_until_both_real_ross_tools_succeed(self):
        with tempfile.TemporaryDirectory(dir=local_agent.ROOT / "output") as temp:
            agent = local_agent.LocalAgent(Path(temp), task="test", ross_docsearch_url="http://127.0.0.1:8080/mcp/doc-search", xsim_enabled=True)
            offered = {tool["function"]["name"] for tool in agent.tool_calls}
            self.assertTrue({"ross_skill_read", "ross_doc_search", "run_xsim"}.issubset(offered))
            denied = agent._tool("run_xsim", {})
            self.assertEqual(denied["stage"], "ross-prerequisite")
            agent.ross_skill_used = True
            agent.ross_doc_search_used = True
            with self.assertRaisesRegex(local_agent.AgentError, "Required M13 sandbox file missing"):
                agent._tool("run_xsim", {})

    def test_ross_skill_context_is_bounded(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            skill = root / "vivado-simulate-rtl"
            (skill / "references").mkdir(parents=True)
            (skill / "SKILL.md").write_text("S" * 10000)
            (skill / "references/xsim.md").write_text("R" * 10000)
            agent = local_agent.LocalAgent(local_agent.ROOT, task="test", ross_docsearch_url="http://127.0.0.1:8080/mcp/doc-search", ross_skills_root=root)
            result = agent._tool("ross_skill_read", {"skill": "vivado-simulate-rtl", "reference": "xsim.md"})
            self.assertTrue(result["ok"])
            self.assertTrue(result["files"][0]["excerpt_truncated"])
            self.assertTrue(result["files"][1]["excerpt_truncated"])
            self.assertLessEqual(sum(len(x["text"]) for x in result["files"]), local_agent.MAX_ROSS_CONTEXT_CHARS + 200)

    def test_ross_context_budgets_are_configurable_but_stay_within_policy(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            skill = root / "vivado-simulate-rtl"
            (skill / "references").mkdir(parents=True)
            (skill / "SKILL.md").write_text("S" * 10000)
            (skill / "references/xsim.md").write_text("R" * 10000)
            agent = local_agent.LocalAgent(
                local_agent.ROOT, task="test",
                ross_docsearch_url="http://127.0.0.1:8080/mcp/doc-search",
                ross_skills_root=root, ross_context_chars=1800, ross_mcp_chars=1200,
            )
            result = agent._tool("ross_skill_read", {"skill": "vivado-simulate-rtl", "reference": "xsim.md"})
            self.assertLessEqual(sum(len(item["text"]) for item in result["files"]), 1800 + 200)
            self.assertEqual(agent.ross_context_chars, 1800)
            self.assertEqual(agent.ross_mcp_chars, 1200)
            with self.assertRaisesRegex(local_agent.AgentError, "ross_context_chars"):
                local_agent.LocalAgent(local_agent.ROOT, task="test", ross_context_chars=500)

    def test_multifile_repair_compaction_keeps_sources_tool_failure_and_ross_evidence(self):
        with tempfile.TemporaryDirectory(dir=local_agent.ROOT / "output") as temp:
            root = Path(temp)
            (root / "rtl").mkdir()
            (root / "sim").mkdir()
            (root / "TASK_SPEC.md").write_text("sum operand B when control bit 2 is set\n")
            (root / "rtl/local_model_axi_lite.v").write_text("module top; endmodule\n")
            (root / "rtl/axi_result_datapath.v").write_text("module datapath; endmodule\n")
            (root / "sim/tb_local_model_axi_lite.sv").write_text("module tb; endmodule\n")
            agent = local_agent.LocalAgent(root, task="follow TASK_SPEC.md", multi_file_xsim=True)
            agent.ross_evidence["AMD local Knowledge Base"] = {"result": "UG900 XSim flow"}
            agent.messages += [{"role": "assistant", "tool_calls": [{"id": "old", "function": {"name": "run_xsim"}}]}, {"role": "tool", "tool_call_id": "old", "content": "large transcript"}]
            agent._compact_multifile_context({"stage": "xsim", "output": "baseline compare failure"})
            self.assertEqual(len(agent.messages), 3)
            context = agent.messages[2]["content"]
            for expected in ("TASK_SPEC.md", "rtl/local_model_axi_lite.v", "rtl/axi_result_datapath.v", "sim/tb_local_model_axi_lite.sv", "baseline compare failure", "UG900 XSim flow"):
                self.assertIn(expected, context)
            self.assertNotIn("large transcript", context)

    def test_hls_mode_exposes_only_fixed_hls_validation_and_gates_source_edits(self):
        with tempfile.TemporaryDirectory(dir=local_agent.ROOT / "output") as temp:
            root = Path(temp)
            (root / "src").mkdir()
            (root / "sim").mkdir()
            (root / "runs").mkdir()
            (root / "hls_config.cfg").write_text("[hls]\n")
            (root / "src/invert32.cpp").write_text("int invert32(int x) { return x; }\n")
            (root / "sim/testbench.cpp").write_text("int main() { return 0; }\n")
            agent = local_agent.LocalAgent(root, task="test", hls_enabled=True, editable_paths={"src/invert32.cpp"}, ross_docsearch_url="http://127.0.0.1:8080/mcp/doc-search")
            offered = {tool["function"]["name"] for tool in agent.tool_calls}
            self.assertIn("run_hls", offered)
            self.assertNotIn("run_xsim", offered)
            self.assertEqual(agent._tool("run_hls", {})["stage"], "ross-prerequisite")
            no_ross = local_agent.LocalAgent(root, task="test", hls_enabled=True, editable_paths={"src/invert32.cpp"})
            with self.assertRaisesRegex(local_agent.AgentError, "baseline HLS"):
                no_ross._tool("apply_patch", {"patch": "--- a/src/invert32.cpp\n+++ b/src/invert32.cpp\n@@ -1 +1 @@\n-int invert32(int x) { return x; }\n+int invert32(int x) { return ~x; }\n"})

    def test_multifile_xsim_policy_requires_baseline_and_allows_only_two_named_rtl_files(self):
        with tempfile.TemporaryDirectory(dir=local_agent.ROOT / "output") as temp:
            root = Path(temp)
            (root / "rtl").mkdir()
            (root / "sim").mkdir()
            (root / "runs").mkdir()
            for path in ("rtl/local_model_axi_lite.v", "rtl/axi_result_datapath.v"):
                (root / path).write_text("old\nkeep1\nkeep2\nend\n")
            (root / "sim/tb_local_model_axi_lite.sv").write_text("fixed\n")
            (root / "TASK_SPEC.md").write_text("spec\n")
            (root / "run_validation_multifile.sh").write_text("#!/bin/sh\nexit 0\n")
            subprocess.run(["git", "init", "--quiet"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.name", "AI370-2 isolated test"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.email", "local@invalid"], cwd=root, check=True)
            subprocess.run(["git", "add", "rtl", "sim", "TASK_SPEC.md", "run_validation_multifile.sh"], cwd=root, check=True)
            subprocess.run(["git", "commit", "--quiet", "-m", "Seed policy test"], cwd=root, check=True)
            editable = {"rtl/local_model_axi_lite.v", "rtl/axi_result_datapath.v"}
            agent = local_agent.LocalAgent(root, task="test", xsim_enabled=True, multi_file_xsim=True, editable_paths=editable)
            offered = {tool["function"]["name"] for tool in agent.tool_calls}
            self.assertIn("run_xsim", offered)
            patch = ("--- a/rtl/local_model_axi_lite.v\n+++ b/rtl/local_model_axi_lite.v\n@@ -1,3 +1,3 @@\n-old\n+new\n keep1\n keep2\n-end\n+finish\n"
                     "--- a/rtl/axi_result_datapath.v\n+++ b/rtl/axi_result_datapath.v\n@@ -1,3 +1,3 @@\n-old\n+new\n keep1\n keep2\n-end\n+finish\n")
            with self.assertRaisesRegex(local_agent.AgentError, "after the unchanged baseline"):
                agent._tool("apply_patch", {"patch": patch})
            agent.validation_count = 1
            one_file = patch.split("--- a/rtl/axi_result_datapath.v")[0]
            with self.assertRaisesRegex(local_agent.AgentError, "both allowlisted"):
                agent._tool("apply_patch", {"patch": one_file})
            malformed = patch.replace(" keep1\n", "keep1\n")
            rejected = agent._tool("apply_patch", {"patch": malformed})
            self.assertFalse(rejected["ok"])
            self.assertEqual(rejected["stage"], "patch-normalization")
            self.assertEqual((root / "rtl/local_model_axi_lite.v").read_text(), "old\nkeep1\nkeep2\nend\n")
            result = agent._tool("apply_patch", {"patch": patch})
            self.assertTrue(result["ok"])
            self.assertIn("canonical diff", result["formatting"])
            self.assertEqual((root / "rtl/local_model_axi_lite.v").read_text(), "new\nkeep1\nkeep2\nfinish\n")
            self.assertEqual((root / "rtl/axi_result_datapath.v").read_text(), "new\nkeep1\nkeep2\nfinish\n")


if __name__ == "__main__":
    unittest.main()
