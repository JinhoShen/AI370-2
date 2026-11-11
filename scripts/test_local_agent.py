#!/usr/bin/env python3
"""Local Agent policy tests; no model request or system modification."""

import hashlib
import json
import sys
import subprocess
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import local_agent


class LocalAgentPolicyTests(unittest.TestCase):
    def test_plain_unified_diff_headers_are_normalized_without_rewriting_source(self):
        raw = '--- rtl/a.v\n+++ rtl/a.v\n@@ -90,99 +90,99 @@\n before\n-old\n+MODEL_SELECTED_NEW\n after\n'
        canonical = local_agent._canonical_patch_headers(raw)
        self.assertEqual(canonical.splitlines()[2:], raw.splitlines()[2:])
        with tempfile.TemporaryDirectory() as temp:
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
        with tempfile.TemporaryDirectory() as temp:
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
        with tempfile.TemporaryDirectory() as temp:
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
        with tempfile.TemporaryDirectory() as temp:
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
        with tempfile.TemporaryDirectory() as temp:
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
        with tempfile.TemporaryDirectory() as temp:
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
        with tempfile.TemporaryDirectory() as temp:
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
        with tempfile.TemporaryDirectory() as temp:
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
        with tempfile.TemporaryDirectory() as temp:
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


class LocalAgentBoundedStateTests(unittest.TestCase):
    """Regression guards for prompt and trace growth; the provider is mocked."""

    @staticmethod
    def tool_turn(call: int) -> dict:
        arguments = json.dumps({"path": "rtl/top.v", "old_text": "a", "new_text": "b"})
        return {"choices": [{"message": {"role": "assistant", "content": None, "tool_calls": [
            {"id": f"call-{call}", "type": "function", "function": {"name": "apply_replacement", "arguments": arguments}}]}}]}

    def run_corrections(self, count: int, error: str) -> tuple[local_agent.LocalAgent, list[str]]:
        prompts: list[str] = []
        with tempfile.TemporaryDirectory() as temp:
            agent = local_agent.LocalAgent(Path(temp), task="test", max_calls=count + 1)
            responses = [self.tool_turn(i) for i in range(count)]
            responses.append({"choices": [{"message": {"role": "assistant", "content": "done"}}]})
            def completion():
                prompts.append(agent.messages[0]["content"])
                return responses.pop(0)
            failure = {"ok": False, "stage": "replacement-check", "error": error}
            with patch.object(agent, "_completion", side_effect=completion), \
                 patch.object(agent, "_tool", return_value=failure), \
                 patch.object(agent, "_compact_multifile_context"):
                self.assertEqual(agent.run(), "done")
        return agent, prompts

    def test_repeated_corrections_keep_only_latest_bounded_feedback(self):
        agent, prompts = self.run_corrections(5, "replacement did not match uniquely")
        base = prompts[0]
        self.assertEqual(agent.correction_feedback_count, 5)
        for prompt in prompts[1:]:
            self.assertTrue(prompt.startswith(base + " Tool feedback requiring correction: "))
            self.assertEqual(prompt.count("Tool feedback requiring correction:"), 1)
        self.assertEqual(len(set(prompts[1:])), 1)
        self.assertEqual(agent.system_prompt_base, base)

    def test_oversized_correction_is_truncated(self):
        agent, prompts = self.run_corrections(3, "E" * 50000)
        base = prompts[0]
        self.assertLessEqual(len(prompts[-1]), len(base) + 1 + local_agent.MAX_CORRECTION_CHARS)
        self.assertLessEqual(len(agent.messages[0]["content"]), len(base) + 1 + local_agent.MAX_CORRECTION_CHARS)

    def test_model_request_trace_records_only_hashes_sizes_roles_and_tool_names(self):
        sent: list[bytes] = []
        class Opener:
            def open(self, request, timeout):
                sent.append(request.data)
                raise urllib.error.URLError("offline test provider")
        secret = "SECRET-PROMPT-TEXT-7f3a"
        with tempfile.TemporaryDirectory() as temp:
            trace = Path(temp) / "trace.jsonl"
            agent = local_agent.LocalAgent(Path(temp), task="test " + secret, trace=trace)
            agent.messages[0]["content"] += " " + secret
            agent.messages.append({"role": "user", "content": secret * 20000})
            with patch.object(local_agent.urllib.request, "build_opener", return_value=Opener()):
                with self.assertRaisesRegex(local_agent.AgentError, "request failed"):
                    agent._completion()
            lines = [line for line in trace.read_text().splitlines() if json.loads(line)["event"] == "model_request"]
        self.assertEqual(len(lines), 1)
        self.assertNotIn(secret, lines[0])
        self.assertLessEqual(len(lines[0].encode()), local_agent.MAX_TRACE_EVENT_BYTES)
        event = json.loads(lines[0])
        request = event["request"]
        self.assertEqual(event["request_sha256"], hashlib.sha256(sent[0]).hexdigest())
        self.assertEqual(request["request_bytes"], len(sent[0]))
        self.assertEqual(request["message_count"], len(agent.messages))
        self.assertNotIn("tools", request)
        self.assertIn("read_file", request["tool_names"])
        self.assertEqual(set(request) - {"messages", "tool_names", "message_count", "request_bytes"},
                         {"model", "tool_choice", "temperature", "max_tokens"})
        for row, message in zip(request["messages"], agent.messages, strict=True):
            encoded = json.dumps(message, ensure_ascii=False, sort_keys=True).encode()
            self.assertEqual(row, {"role": message["role"], "bytes": len(encoded),
                                   "sha256": hashlib.sha256(encoded).hexdigest()})

    def test_any_oversized_trace_event_is_replaced_by_bounded_digest_without_content(self):
        with tempfile.TemporaryDirectory() as temp:
            trace = Path(temp) / "trace.jsonl"
            agent = local_agent.LocalAgent(Path(temp), task="test", trace=trace)
            agent._trace({"event": "tool_call", "name": "read_file", "call": 3, "result": "SECRET-RESULT " * 30000})
            agent._trace({"event": "small", "value": 1})
            lines = trace.read_text().splitlines()[-2:]
        big, small = (json.loads(line) for line in lines)
        self.assertLessEqual(len(lines[0].encode()), local_agent.MAX_TRACE_EVENT_BYTES)
        self.assertNotIn("SECRET-RESULT", lines[0])
        self.assertEqual(set(big), {"event", "name", "call", "timestamp_utc", "monotonic_seconds",
                                    "trace_truncated", "original_bytes", "original_sha256"})
        self.assertEqual((big["event"], big["name"], big["call"]), ("tool_call", "read_file", 3))
        self.assertTrue(big["trace_truncated"])
        self.assertGreater(big["original_bytes"], local_agent.MAX_TRACE_EVENT_BYTES)
        self.assertEqual(len(big["original_sha256"]), 64)
        self.assertEqual(small["value"], 1)
        self.assertNotIn("trace_truncated", small)

class LocalAgentTraceModeTests(unittest.TestCase):
    """AI370_TRACE_MODE controls whether model output and tool data are kept verbatim."""

    SECRET = "SECRET-CONTENT-91c2"

    def run_traced(self, mode: str | None) -> list[dict]:
        env = {} if mode is None else {"AI370_TRACE_MODE": mode}
        arguments = {"path": "rtl/top.v", "old_text": self.SECRET, "new_text": "b"}
        responses = [
            {"choices": [{"message": {"role": "assistant", "content": self.SECRET, "tool_calls": [
                {"id": "c1", "type": "function", "function": {"name": "apply_replacement", "arguments": json.dumps(arguments)}}]}}]},
            {"choices": [{"message": {"role": "assistant", "content": "done " + self.SECRET}}]},
        ]
        failure = {"ok": False, "stage": "replacement-check", "error": "no match for " + self.SECRET}
        with tempfile.TemporaryDirectory() as temp, patch.dict("os.environ", env):
            trace = Path(temp) / "trace.jsonl"
            agent = local_agent.LocalAgent(Path(temp), task="test", trace=trace, max_calls=3)
            with patch.object(agent, "_completion", side_effect=responses), \
                 patch.object(agent, "_tool", return_value=failure), \
                 patch.object(agent, "_compact_multifile_context"):
                agent.run()
            self.raw = trace.read_text()
        return [json.loads(line) for line in self.raw.splitlines()]

    def test_default_full_mode_keeps_model_output_and_tool_evidence(self):
        events = self.run_traced(None)
        self.assertIn(self.SECRET, self.raw)
        call = next(e for e in events if e["event"] == "tool_call")
        self.assertEqual(call["arguments"]["old_text"], self.SECRET)
        self.assertEqual(call["result"]["error"], "no match for " + self.SECRET)

    def test_hash_only_mode_keeps_metadata_and_replaces_content_with_digests(self):
        events = self.run_traced("hash-only")
        self.assertNotIn(self.SECRET, self.raw)
        self.assertEqual([e["event"] for e in events],
                         ["agent_start", "model_response", "tool_call", "model_response", "agent_complete"])
        start = events[0]
        self.assertEqual(start["model"], local_agent.DEFAULT_MODEL)
        response = events[1]
        self.assertEqual(response["call"], 1)
        self.assertEqual(set(response["response"]), {"bytes", "sha256"})
        call = events[2]
        self.assertEqual(call["name"], "apply_replacement")
        arguments = {"path": "rtl/top.v", "old_text": self.SECRET, "new_text": "b"}
        encoded = json.dumps(arguments, ensure_ascii=False, sort_keys=True).encode()
        self.assertEqual(call["arguments"], {"bytes": len(encoded), "sha256": hashlib.sha256(encoded).hexdigest()})
        self.assertEqual({k: call["result"][k] for k in ("ok", "stage")}, {"ok": False, "stage": "replacement-check"})
        self.assertNotIn("error", call["result"])
        self.assertEqual(events[4]["tool_calls"], 1)

    def test_unknown_trace_mode_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict("os.environ", {"AI370_TRACE_MODE": "verbose"}):
            with self.assertRaisesRegex(local_agent.AgentError, "AI370_TRACE_MODE"):
                local_agent.LocalAgent(Path(temp), task="test")

if __name__ == "__main__":
    unittest.main()
