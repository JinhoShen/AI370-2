#!/usr/bin/env python3
"""Local Qwen agent with a small, policy-checked local tool executor.

The model can only request the functions declared below. It cannot submit a
shell command. All provider traffic is pinned to loopback; command tools run in
Bubblewrap with the repository read-only except for the selected workspace.
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import ipaddress
import json
import os
import re
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path, PurePosixPath
from typing import Any
from datetime import datetime, timezone


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODEL = "Qwen3.8-27B-UD-Q4_K_XL"
DEFAULT_BASE_URL = "http://127.0.0.1:13305/api/v1"
MAX_FILE_BYTES = 256 * 1024
MAX_REPLACEMENT_BYTES = 24 * 1024
MAX_TOOL_RESULT_CHARS = 12000
MAX_TOOL_CALLS = 24
MAX_XSIM_RUNS = 3
MAX_HLS_RUNS = 3
MAX_PATCHES = 2
MAX_ROSS_CONTEXT_CHARS = 3200
MAX_ROSS_MCP_CHARS = 3000
MAX_CORRECTION_CHARS = 4000
MAX_TRACE_EVENT_BYTES = 64 * 1024
# AI370_TRACE_MODE=hash-only keeps only these fields verbatim; every other field
# (model output, tool arguments/results, patches, errors) becomes bytes + SHA-256.
TRACE_MODES = {"full", "hash-only"}
TRACE_METADATA_KEYS = {"event", "name", "call", "tool_calls", "validation_pass", "model", "provider",
                       "workspace", "offline_tools", "path", "paths", "request_sha256", "request"}
ROSS_SKILLS_ROOT = Path(os.environ.get("AI370_ROSS_SKILLS_ROOT", str(ROOT / "docs/M13/ross-runtime-skills")))
ROSS_SKILLS = {"vivado-simulate-rtl", "vivado-rtl-elaboration-analysis", "hls-run-flow", "hls-synthesizable", "hls-synth-report"}
BLOCKED_ROOT_PARTS = {".git", "resources", "output", ".venv", "venv", "node_modules"}
BLOCKED_NAMES = {".env", ".netrc", "credentials", "Xilinx_shen.lic"}
BLOCKED_EXTENSIONS = {".gguf", ".onnx", ".lic", ".pem", ".key", ".p12", ".pfx", ".bit", ".bin"}
PROTECTED_PATHS = (
    ("docs", "M11", "evidence"),
    ("docs", "M12", "evidence"),
)


class AgentError(RuntimeError):
    pass


def _verification_profile_enabled(*, xsim: bool, multi_file_xsim: bool, hls: bool) -> bool:
    return xsim or multi_file_xsim or hls


def _loopback_endpoint(base_url: str) -> str:
    parsed = urllib.parse.urlparse(base_url)
    if parsed.scheme != "http" or not parsed.hostname or parsed.username or parsed.password:
        raise AgentError("Local provider must be an unauthenticated HTTP loopback URL")
    try:
        addresses = {ipaddress.ip_address(info[4][0]) for info in socket.getaddrinfo(parsed.hostname, parsed.port or 80)}
    except OSError as exc:
        raise AgentError(f"Cannot resolve local provider: {type(exc).__name__}") from exc
    if not addresses or any(not address.is_loopback for address in addresses):
        raise AgentError("Refusing a non-loopback model provider; no cloud endpoint is permitted")
    return base_url.rstrip("/")


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _relative_path(root: Path, value: str) -> Path:
    path = PurePosixPath(value)
    if path.is_absolute() or not path.parts or any(part in {"", ".", ".."} for part in path.parts):
        raise AgentError("Tool path must be a clean workspace-relative path")
    if any(part.startswith(".") for part in path.parts):
        raise AgentError("Hidden paths are outside the agent tool policy")
    if any(part in BLOCKED_ROOT_PARTS for part in path.parts):
        raise AgentError("Resources, build output, caches and Git internals are not agent-readable")
    if path.name in BLOCKED_NAMES or path.suffix.lower() in BLOCKED_EXTENSIONS:
        raise AgentError("Credential, model, firmware and binary files are outside the agent tool policy")
    candidate = root.joinpath(*path.parts)
    cursor = root
    for part in path.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise AgentError("Symlink traversal is forbidden")
    resolved = candidate.resolve(strict=False)
    if root != resolved and root not in resolved.parents:
        raise AgentError("Tool path escaped the selected workspace")
    return candidate


def _editable_allowed(relative: str, explicit: set[str]) -> bool:
    if explicit and relative not in explicit:
        return False
    parts = PurePosixPath(relative).parts
    if any(parts[:len(blocked)] == blocked for blocked in PROTECTED_PATHS):
        return False
    return True


def _canonical_patch_headers(patch: str) -> str:
    """Normalize only existing-file path labels, never model-authored source hunks."""
    lines = patch.splitlines(keepends=True)
    for index in range(len(lines) - 1):
        if lines[index].startswith('--- ') and lines[index + 1].startswith('+++ '):
            old = lines[index][4:].split('\t', 1)[0].strip()
            new = lines[index + 1][4:].split('\t', 1)[0].strip()
            old = old[2:] if old.startswith('a/') else old
            new = new[2:] if new.startswith('b/') else new
            lines[index] = f'--- a/{old}\n'
            lines[index + 1] = f'+++ b/{new}\n'
    return ''.join(lines)


def _patch_paths(patch: str, *, max_files: int = 1) -> list[str]:
    lines = patch.splitlines()
    markers: list[tuple[str, str]] = []
    index = 0
    while index + 1 < len(lines):
        old_line, new_line = lines[index], lines[index + 1]
        if old_line.startswith("--- a/") and new_line.startswith("+++ b/"):
            markers.append((old_line[6:].split("\t", 1)[0].strip(), new_line[6:].split("\t", 1)[0].strip()))
            index += 2
        else:
            index += 1
    if not markers:
        raise AgentError("Patch must contain complete existing-file unified diff sections")
    paths: list[str] = []
    for old, new in markers:
        if old == "/dev/null" or new == "/dev/null" or old != new:
            raise AgentError("New files, deletes and renames are not allowed")
        paths.append(old)
    if len(paths) > max_files or len(set(paths)) != len(paths):
        raise AgentError(f"Patch may modify at most {max_files} distinct existing file(s)")
    return paths


def _normalize_multifile_git_patch(patch: str, paths: list[str], source_files: dict[str, str] | None = None) -> str:
    """Rebase model hunks on the exact allowlisted source and emit a canonical diff."""
    lines = patch.splitlines(keepends=True)
    starts: list[tuple[int, str]] = []
    for index in range(len(lines) - 1):
        if lines[index].startswith("--- a/") and lines[index + 1].startswith("+++ b/"):
            old = lines[index][6:].split("\t", 1)[0].strip()
            new = lines[index + 1][6:].split("\t", 1)[0].strip()
            if old == new and old in paths:
                starts.append((index, old))
    if len(starts) != len(paths) or {path for _, path in starts} != set(paths):
        raise AgentError("Cannot safely identify every path-checked two-file patch section")

    output: list[str] = []
    hunk_re = re.compile(r"^@@(?: -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@(.*?))?(?:\r?\n)?$")
    for slot, (start, relative) in enumerate(starts):
        end = starts[slot + 1][0] if slot + 1 < len(starts) else len(lines)
        section = lines[start:end]
        if relative not in (source_files or {}):
            raise AgentError(f"Exact source text is required to validate model hunks for {relative}")
        original_lines = source_files[relative].splitlines(keepends=True)
        modified_lines = list(original_lines)
        source_cursor = 0
        line_delta = 0
        index = 2
        while index < len(section):
            match = hunk_re.match(section[index])
            if not match:
                if section[index].startswith(("diff --git ", "index ", "new file mode ", "deleted file mode ", "similarity index ", "rename from ", "rename to ")):
                    index += 1
                    continue
                raise AgentError(f"Unsupported text outside a unified-diff hunk for {relative}")
            body_start = index + 1
            body_end = body_start
            while (body_end < len(section)
                   and not hunk_re.match(section[body_end])
                   and not section[body_end].startswith("diff --git ")):
                body_end += 1
            old_body: list[str] = []
            new_body: list[str] = []
            for hunk_line in section[body_start:body_end]:
                if hunk_line.startswith(" "):
                    old_body.append(hunk_line[1:])
                    new_body.append(hunk_line[1:])
                elif hunk_line.startswith("-"):
                    old_body.append(hunk_line[1:])
                elif hunk_line.startswith("+"):
                    new_body.append(hunk_line[1:])
                elif hunk_line.startswith("\\"):
                    raise AgentError(f"No-newline patch markers are not supported for {relative}")
                else:
                    raise AgentError(f"Malformed hunk line for {relative}; no source was changed")
            if not old_body:
                raise AgentError(f"A hunk without original source context cannot be safely placed in {relative}")
            def comparable(items: list[str]) -> list[str]:
                return [item.rstrip("\r\n") for item in items]
            old_key = comparable(old_body)
            source_key = comparable(original_lines)
            matches = [pos for pos in range(source_cursor, len(original_lines) - len(old_body) + 1)
                       if source_key[pos:pos + len(old_body)] == old_key]
            if len(matches) != 1:
                raise AgentError(f"Model hunk for {relative} does not match one unique exact source region")
            source_pos = matches[0]
            modified_pos = source_pos + line_delta
            if comparable(modified_lines[modified_pos:modified_pos + len(old_body)]) != old_key:
                raise AgentError(f"Model hunks overlap or conflict in {relative}")
            modified_lines[modified_pos:modified_pos + len(old_body)] = new_body
            source_cursor = source_pos + len(old_body)
            line_delta += len(new_body) - len(old_body)
            index = body_end
        output.extend(difflib.unified_diff(
            original_lines, modified_lines,
            fromfile=f"a/{relative}", tofile=f"b/{relative}", n=3,
        ))
    return "".join(output)


def _trace_digest(value: Any) -> dict[str, Any]:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str).encode()
    digest: dict[str, Any] = {"bytes": len(encoded), "sha256": hashlib.sha256(encoded).hexdigest()}
    if isinstance(value, dict):
        digest.update({key: value[key] for key in ("ok", "stage", "status")
                       if isinstance(value.get(key), (str, bool, int))})
    return digest


def _request_trace_summary(request_body: dict[str, Any], request_bytes: int) -> dict[str, Any]:
    """Describe a model request by hashes, sizes, roles and tool names; no prompt text."""
    messages = request_body.get("messages", [])
    rows = []
    for message in messages:
        encoded = json.dumps(message, ensure_ascii=False, sort_keys=True).encode()
        rows.append({"role": message.get("role"), "bytes": len(encoded), "sha256": hashlib.sha256(encoded).hexdigest()})
    summary = {key: value for key, value in request_body.items() if key not in {"messages", "tools"}}
    summary.update(request_bytes=request_bytes, message_count=len(messages), messages=rows,
                   tool_names=[tool["function"]["name"] for tool in request_body.get("tools", [])])
    return summary


class LocalAgent:
    def __init__(
        self,
        workspace: Path,
        *,
        task: str,
        model: str = DEFAULT_MODEL,
        base_url: str = DEFAULT_BASE_URL,
        timeout: int = 180,
        total_timeout: int = 1800,
        max_completion_tokens: int = 512,
        max_calls: int = MAX_TOOL_CALLS,
        trace: Path | None = None,
        editable_paths: set[str] | None = None,
        offline_tools: bool = False,
        xsim_enabled: bool = False,
        multi_file_xsim: bool = False,
        hls_enabled: bool = False,
        ross_docsearch_url: str | None = None,
        ross_skills_root: Path = ROSS_SKILLS_ROOT,
        ross_context_chars: int = MAX_ROSS_CONTEXT_CHARS,
        ross_mcp_chars: int = MAX_ROSS_MCP_CHARS,
        fixed_temperature: float | None = None,
        fixed_seed: int | None = None,
    ):
        self.workspace = workspace.resolve(strict=True)
        if not self.workspace.is_dir():
            raise AgentError("Workspace is not a directory")
        self.task = task
        self.model = model
        self.base_url = _loopback_endpoint(base_url)
        self.timeout = timeout
        if not 1 <= max_completion_tokens <= 8192:
            raise AgentError("max_completion_tokens must be between 1 and 8192")
        self.max_completion_tokens = max_completion_tokens
        self.deadline = time.monotonic() + total_timeout
        self.max_calls = min(max_calls, MAX_TOOL_CALLS)
        self.trace = trace
        self.trace_mode = os.environ.get("AI370_TRACE_MODE", "full")
        if self.trace_mode not in TRACE_MODES:
            raise AgentError(f"AI370_TRACE_MODE must be one of {sorted(TRACE_MODES)}")
        self.editable_paths = editable_paths or set()
        self.offline_tools = offline_tools
        self.xsim_enabled = xsim_enabled
        self.multi_file_xsim = multi_file_xsim
        self.hls_enabled = hls_enabled
        if fixed_temperature is not None and not 0.0 <= fixed_temperature <= 2.0:
            raise AgentError("fixed_temperature must be between 0 and 2")
        self.fixed_temperature = fixed_temperature
        self.fixed_seed = fixed_seed
        self.ross_docsearch_url = self._validate_ross_endpoint(ross_docsearch_url) if ross_docsearch_url else None
        self.ross_skills_root = ross_skills_root.resolve(strict=False)
        if not 1200 <= ross_context_chars <= MAX_ROSS_CONTEXT_CHARS:
            raise AgentError(f"ross_context_chars must be between 1200 and {MAX_ROSS_CONTEXT_CHARS}")
        if not 512 <= ross_mcp_chars <= MAX_ROSS_MCP_CHARS:
            raise AgentError(f"ross_mcp_chars must be between 512 and {MAX_ROSS_MCP_CHARS}")
        self.ross_context_chars = ross_context_chars
        self.ross_mcp_chars = ross_mcp_chars
        self._ross_session: str | None = None
        self.ross_server_info: dict[str, Any] | None = None
        self.ross_tool_overhead_s = 0.0
        self.ross_skill_used = False
        self.ross_doc_search_used = False
        self.ross_evidence: dict[str, dict[str, Any]] = {}
        self.model_request_s = 0.0
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.validation_count = 0
        self.patch_count = 0
        self.last_failed_patch: str | None = None
        self.repeated_failed_patch_count = 0
        self.correction_feedback_count = 0
        self.system_prompt_base: str | None = None
        self.xsim_passed = False
        self.messages: list[dict[str, Any]] = [
            {
                "role": "system",
                "content": (
                    "You are the AI370-2 Local Engineering Agent. You run locally on the user's workstation. "
                    "You have no shell tool and must use only the provided local functions. Read the task and source "
                    "before acting. Keep tool calls and final explanations concise. For engineering validation, read the task and design sources, "
                    "run the unchanged baseline before patching, diagnose the actual tool output, apply the smallest design-source-only diff, "
                    "then rerun until the fixed tool reports PASS. If a unified diff is rejected for hunk syntax, use apply_replacement with exact old/new text from your own proposed fix; it will validate and mechanically format that replacement. "
                    "Never edit a testbench or weaken a check. Do not claim success without the fixed runner's PASS marker. "
                    "The tool executor enforces workspace, file, command, timeout, network and retry policy."
                ),
            },
            {"role": "user", "content": task},
        ]
        if self.multi_file_xsim:
            self.messages[0]["content"] += " For this explicitly opted-in T2 profile, one unified diff must modify exactly the two allowlisted RTL files, and no other file; the tool executor independently enforces that boundary."
        if self.ross_docsearch_url and (self.xsim_enabled or self.hls_enabled):
            skill, reference, flow = ("hls-run-flow", "", "Vitis HLS") if self.hls_enabled else ("vivado-simulate-rtl", "xsim.md", "Vivado XSim")
            ref_request = f" with reference {reference}" if reference else " (the installed skill has no local reference file)"
            self.messages[0]["content"] += f" Ross mode is explicitly enabled for this task. Before any {flow} run or source edit, call ross_skill_read for {skill}{ref_request}, and call ross_doc_search for the task-specific 2026.1 guidance. Use the actual returned local Ross material; the executor will block validation and patches until both calls succeed."
        self.tool_calls = self._tool_specs()
        self._trace({"event": "agent_start", "model": model, "provider": self.base_url, "workspace": str(self.workspace), "offline_tools": offline_tools})

    def _tool_specs(self) -> list[dict[str, Any]]:
        tools = [
            {"type": "function", "function": {"name": "list_files", "description": "List safe text files in a workspace directory.", "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"], "additionalProperties": False}}},
            {"type": "function", "function": {"name": "read_file", "description": "Read one safe UTF-8 text file from the selected workspace.", "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"], "additionalProperties": False}}},
            {"type": "function", "function": {"name": "apply_patch", "description": "Apply one unified diff to the explicitly allowed existing workspace source file(s) after checking it with git apply; this task may allow at most two files.", "parameters": {"type": "object", "properties": {"patch": {"type": "string"}}, "required": ["patch"], "additionalProperties": False}}},
        ]
        if self.xsim_enabled:
            if not self.multi_file_xsim:
                tools.append({"type": "function", "function": {"name": "apply_replacement", "description": "After a rejected patch-format attempt, replace exactly one model-selected existing RTL text fragment. The executor validates a unique exact match and mechanically formats that same before/after text into a unified diff; it does not choose or alter replacement logic.", "parameters": {"type": "object", "properties": {"path": {"type": "string"}, "old_text": {"type": "string"}, "new_text": {"type": "string"}}, "required": ["path", "old_text", "new_text"], "additionalProperties": False}}})
            tools.append({"type": "function", "function": {"name": "run_xsim", "description": "Run only the fixed, bounded Vivado XSim smoke script in this isolated M13 workspace and return its real logs.", "parameters": {"type": "object", "properties": {}, "additionalProperties": False}}})
        elif self.hls_enabled:
            tools.append({"type": "function", "function": {"name": "apply_replacement", "description": "After a rejected patch-format attempt, replace exactly one model-selected source fragment. The executor validates a unique exact match and formats the model's exact text into a unified diff.", "parameters": {"type": "object", "properties": {"path": {"type": "string"}, "old_text": {"type": "string"}, "new_text": {"type": "string"}}, "required": ["path", "old_text", "new_text"], "additionalProperties": False}}})
            tools.append({"type": "function", "function": {"name": "run_hls", "description": "Run only the fixed Vitis 2026.1 HLS C-simulation and C-synthesis workflow for the isolated project; return real logs and PASS markers.", "parameters": {"type": "object", "properties": {}, "additionalProperties": False}}})
        else:
            tools.append({"type": "function", "function": {"name": "run_check", "description": "Run one fixed local verification check from the allowlist.", "parameters": {"type": "object", "properties": {"check": {"type": "string", "enum": ["git-diff-check", "telegram-unit-tests"]}}, "required": ["check"], "additionalProperties": False}}})
        if self.ross_docsearch_url:
            tools.append({"type": "function", "function": {"name": "ross_doc_search", "description": "Call the installed AMD local Knowledge Base MCP server (vivado_doc_search), returning cited documentation. This is a real read-only MCP request, not a substitute local search.", "parameters": {"type": "object", "properties": {"query": {"type": "string", "maxLength": 1200}}, "required": ["query"], "additionalProperties": False}}})
            tools.append({"type": "function", "function": {"name": "ross_skill_read", "description": "Read a selected, installed AMD Ross Agent Skill and its one referenced local guide. Returns the actual installed skill text as model context.", "parameters": {"type": "object", "properties": {"skill": {"type": "string", "enum": sorted(ROSS_SKILLS)}, "reference": {"type": "string", "maxLength": 80}}, "required": ["skill"], "additionalProperties": False}}})
        return tools

    @staticmethod
    def _validate_ross_endpoint(url: str) -> str:
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme != "http" or not parsed.hostname or parsed.username or parsed.password or parsed.path != "/mcp/doc-search" or parsed.query or parsed.fragment:
            raise AgentError("Ross Knowledge Base must use its fixed local MCP HTTP path")
        try:
            addresses = {ipaddress.ip_address(info[4][0]) for info in socket.getaddrinfo(parsed.hostname, parsed.port or 80)}
        except OSError as exc:
            raise AgentError(f"Cannot resolve Ross local MCP endpoint: {type(exc).__name__}") from exc
        private_v4 = (ipaddress.ip_network("172.16.0.0/12"), ipaddress.ip_network("10.0.0.0/8"), ipaddress.ip_network("192.168.0.0/16"))
        if not addresses or any(not (address.is_loopback or (address.version == 4 and any(address in network for network in private_v4))) for address in addresses):
            raise AgentError("Ross MCP endpoint must resolve only to loopback or a private RFC1918 address")
        return url.rstrip("/")

    def _ross_post(self, payload: dict[str, Any], *, session: str | None = None) -> tuple[dict[str, Any], str | None]:
        assert self.ross_docsearch_url
        headers = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
        if session:
            headers["Mcp-Session-Id"] = session
        request = urllib.request.Request(self.ross_docsearch_url, data=json.dumps(payload).encode(), headers=headers, method="POST")
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect())
        with opener.open(request, timeout=min(self.timeout, 45)) as response:
            body = response.read(512 * 1024 + 1)
            if len(body) > 512 * 1024:
                raise AgentError("Ross MCP response exceeded 512 KiB")
            content_type = response.headers.get("Content-Type", "")
            new_session = response.headers.get("Mcp-Session-Id") or session
        text = body.decode("utf-8", errors="replace")
        if "text/event-stream" in content_type:
            data_lines = [line[6:].strip() for line in text.splitlines() if line.startswith("data: ")]
            text = data_lines[-1] if data_lines else ""
        result = json.loads(text)
        if result.get("error"):
            raise AgentError(f"Ross MCP error: {result['error']}")
        return result.get("result", {}), new_session

    def _ross_call(self, query: str) -> dict[str, Any]:
        if not isinstance(query, str) or not query.strip() or len(query) > 1200:
            raise AgentError("Ross documentation query must be 1-1200 characters")
        started = time.monotonic()
        try:
            if not self._ross_session:
                init, self._ross_session = self._ross_post({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-03-26", "capabilities": {}, "clientInfo": {"name": "AI370-2 Local Agent", "version": "1.0"}}})
                self.ross_server_info = init.get("serverInfo", {})
                if self.ross_server_info.get("name") != "AMD Doc Search":
                    raise AgentError("Ross MCP identity did not match installed AMD Doc Search server")
                listed, self._ross_session = self._ross_post({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}, session=self._ross_session)
                ross_tool = next((item for item in listed.get("tools", []) if item.get("name") == "vivado_doc_search"), None)
                if not ross_tool or not (ross_tool.get("annotations") or {}).get("readOnlyHint"):
                    raise AgentError("Installed AMD MCP server did not expose vivado_doc_search")
            result, self._ross_session = self._ross_post({"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "vivado_doc_search", "arguments": {"query": query, "limit": 3, "alpha": 0.35, "tool": ["Vivado Design Suite"]}}}, session=self._ross_session)
            texts = [part.get("text", "") for part in result.get("content", []) if part.get("type") == "text"]
            joined = "\n\n".join(texts)
            value = joined[:self.ross_mcp_chars]
            if not value:
                raise AgentError("Ross MCP returned no documentation text")
            return {"ok": True, "server": self.ross_server_info, "mcp_tool": "vivado_doc_search", "elapsed_seconds": round(time.monotonic() - started, 3), "truncated": len(joined) > len(value), "result": value}
        finally:
            self.ross_tool_overhead_s += time.monotonic() - started

    def _ross_skill(self, name: str, reference: str | None = None) -> dict[str, Any]:
        if name not in ROSS_SKILLS:
            raise AgentError("Ross Skill is outside the approved installed-skill allowlist")
        skill_dir = self.ross_skills_root / name
        skill_file = (skill_dir / "SKILL.md").resolve(strict=True)
        if skill_dir.resolve(strict=True) not in skill_file.parents or skill_file.stat().st_size > MAX_FILE_BYTES:
            raise AgentError("Ross Skill path or size is outside policy")
        content = skill_file.read_text(encoding="utf-8")
        skill_excerpt = content[:min(1200, self.ross_context_chars // 2)]
        files = [{"path": str(skill_file), "text": skill_excerpt, "excerpt_truncated": len(content) > len(skill_excerpt)}]
        used_chars = len(skill_excerpt)
        if reference:
            rel = PurePosixPath(reference)
            if rel.is_absolute() or len(rel.parts) != 1 or rel.name.startswith(".") or rel.suffix.lower() not in {".md", ".txt"}:
                raise AgentError("Only a single local markdown/text Ross reference file may be read")
            ref = (skill_dir / "references" / rel.name).resolve(strict=True)
            if skill_dir.resolve(strict=True) not in ref.parents or ref.stat().st_size > MAX_FILE_BYTES:
                raise AgentError("Ross Skill reference path or size is outside policy")
            ref_text = ref.read_text(encoding="utf-8")
            remaining = max(0, self.ross_context_chars - used_chars - 180)
            ref_excerpt = ref_text[:remaining]
            files.append({"path": str(ref), "text": ref_excerpt, "excerpt_truncated": len(ref_text) > len(ref_excerpt)})
            if files[-1]["excerpt_truncated"]:
                files[-1]["text"] += "\n[ROSS SKILL REFERENCE EXCERPT TRUNCATED; complete installed file retained at this path.]"
        return {"ok": True, "source": "installed AMD Ross Agent Skill", "skill": name, "files": files}

    def _trace(self, obj: dict[str, Any]) -> None:
        if self.trace:
            self.trace.parent.mkdir(parents=True, exist_ok=True)
            with self.trace.open("a", encoding="utf-8") as stream:
                event = dict(obj)
                if self.trace_mode == "hash-only":
                    event = {key: value if key in TRACE_METADATA_KEYS else _trace_digest(value)
                             for key, value in event.items()}
                event.setdefault("timestamp_utc", datetime.now(timezone.utc).isoformat(timespec="milliseconds"))
                event.setdefault("monotonic_seconds", round(time.monotonic(), 6))
                line = json.dumps(event, ensure_ascii=False)
                encoded = line.encode()
                if len(encoded) > MAX_TRACE_EVENT_BYTES:
                    # Keep only identity fields the UI reads plus a digest of the dropped event.
                    digest = {key: event[key] for key in ("event", "name", "call") if key in event}
                    digest.update(timestamp_utc=event["timestamp_utc"], monotonic_seconds=event["monotonic_seconds"],
                                  trace_truncated=True, original_bytes=len(encoded),
                                  original_sha256=hashlib.sha256(encoded).hexdigest())
                    line = json.dumps(digest, ensure_ascii=False)
                stream.write(line + "\n")

    def _compact_multifile_context(self, latest_failure: dict[str, Any]) -> None:
        """Retain repair evidence while dropping duplicated model/tool history."""
        if not self.multi_file_xsim:
            return
        pieces = [
            "COMPACTED TOOL CONTEXT: the baseline has already run; do not repeat it. "
            "Continue using these exact task, current source, fixed testbench and latest tool evidence.",
        ]
        spec = self.workspace / "TASK_SPEC.md"
        if spec.is_file():
            pieces.append("TASK_SPEC.md:\n" + spec.read_text(encoding="utf-8")[:MAX_FILE_BYTES])
        for rel in ("rtl/local_model_axi_lite.v", "rtl/axi_result_datapath.v"):
            path = self.workspace / rel
            if path.is_file() and path.stat().st_size <= MAX_FILE_BYTES:
                pieces.append(f"CURRENT {rel}:\n" + path.read_text(encoding="utf-8"))
        tb = self.workspace / "sim/tb_local_model_axi_lite.sv"
        if tb.is_file():
            digest = hashlib.sha256(tb.read_bytes()).hexdigest()
            pieces.append(
                "The fixed sim/tb_local_model_axi_lite.sv testbench was already read in the original turns and is immutable; "
                f"sha256={digest}. Its fixed runner checks baseline, REG_OPERAND_B read/write, "
                "add mode, legacy complement mode, and XOR mode. Do not edit it."
            )
        if self.ross_evidence:
            pieces.append("ACTUAL ROSS MATERIAL ALREADY RETRIEVED; do not repeat calls:\n" + json.dumps(self.ross_evidence, ensure_ascii=False)[:self.ross_context_chars + self.ross_mcp_chars + 300])
        failure_text = str(latest_failure.get("output") or latest_failure.get("error") or latest_failure)
        relevant = [line for line in failure_text.splitlines() if re.search(r"fatal|error|mismatch|fail|slverr|marker", line, re.I)]
        if relevant:
            failure_text = "\n".join(relevant[-12:])
        pieces.append("LATEST ACTUAL TOOL FAILURE:\n" + failure_text[-1000:])
        self.messages = [self.messages[0], self.messages[1], {"role": "user", "content": "\n\n".join(pieces)}]

    def _completion(self) -> dict[str, Any]:
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise AgentError("Local Agent reached its total wall-clock limit")
        temperature = self.fixed_temperature if self.fixed_temperature is not None else (0.25 if self.correction_feedback_count else 0)
        request_body = {"model": self.model, "messages": self.messages, "tools": self.tool_calls,
                        "tool_choice": "auto", "temperature": temperature,
                        "max_tokens": self.max_completion_tokens}
        if self.fixed_seed is not None: request_body["seed"] = self.fixed_seed
        body = json.dumps(request_body, ensure_ascii=False).encode()
        self._trace({"event":"model_request","request_sha256":hashlib.sha256(body).hexdigest(),
                     "request":_request_trace_summary(request_body, len(body))})
        request = urllib.request.Request(self.base_url + "/chat/completions", data=body, headers={"Content-Type": "application/json"})
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect())
        started = time.monotonic()
        try:
            with opener.open(request, timeout=min(self.timeout, max(1, remaining))) as response:
                payload = response.read(8 * 1024 * 1024 + 1)
                if len(payload) > 8 * 1024 * 1024:
                    raise AgentError("Local provider response exceeded the 8 MiB limit")
                data = json.loads(payload)
        except urllib.error.HTTPError as exc:
            detail = exc.read(2000).decode("utf-8", errors="replace")
            raise AgentError(f"Local Qwen provider returned HTTP {exc.code}: {detail[:1000]}") from exc
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise AgentError(f"Local Qwen request failed: {type(exc).__name__}: {exc}") from exc
        finally:
            self.model_request_s += time.monotonic() - started
        if not isinstance(data.get("choices"), list) or not data["choices"]:
            raise AgentError("Local Qwen returned no completion choices")
        usage = data.get("usage") or {}
        data["local_agent_request_seconds"] = round(time.monotonic() - started, 3)
        self.prompt_tokens += int(usage.get("prompt_tokens") or 0)
        self.completion_tokens += int(usage.get("completion_tokens") or 0)
        return data

    def _bwrap_command(self, args: list[str], *, share_net: bool) -> tuple[list[str], tuple[int, ...]]:
        bwrap = "/usr/bin/bwrap"
        if not Path(bwrap).is_file():
            raise AgentError("Bubblewrap is not installed")
        command = [bwrap, "--unshare-all"]
        if share_net:
            # Vivado's existing FlexNet file license is bound to a host NIC MAC.
            # This preserves host identity for license checkout; the command itself is fixed/allowlisted.
            command.append("--share-net")
        command += [
            "--die-with-parent", "--new-session", "--ro-bind", "/", "/",
            "--dev", "/dev", "--proc", "/proc", "--tmpfs", "/tmp",
            # The bind destination must already exist in the read-only root bind.
            # Rebind the existing source directory at its own absolute path.
            "--bind", str(self.workspace), str(self.workspace), "--chdir", str(self.workspace),
            "--setenv", "HOME", str(Path.home()),
            "--setenv", "PATH", "/usr/local/bin:/usr/bin:/bin",
            "--", *args,
        ]
        return command, ()

    def _run_bounded(self, args: list[str], *, share_net: bool, timeout: int = 240) -> subprocess.CompletedProcess[str]:
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise AgentError("Local Agent reached its total wall-clock limit")
        command, pass_fds = self._bwrap_command(args, share_net=share_net)
        return subprocess.run(command, cwd=self.workspace, capture_output=True, text=True, timeout=min(timeout, max(1, remaining)), pass_fds=pass_fds)

    def _tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if name == "list_files":
            relative = arguments.get("path")
            if not isinstance(relative, str):
                raise AgentError("path must be a string")
            directory = self.workspace if relative in {"", "."} else _relative_path(self.workspace, relative)
            if not directory.is_dir():
                raise AgentError("Directory does not exist")
            entries = []
            for entry in sorted(directory.iterdir(), key=lambda p: p.name):
                rel = entry.relative_to(self.workspace).as_posix()
                if entry.is_symlink() or entry.name.startswith(".") or entry.name in BLOCKED_NAMES or entry.suffix.lower() in BLOCKED_EXTENSIONS:
                    continue
                if entry.is_file() and entry.stat().st_size <= MAX_FILE_BYTES:
                    entries.append(rel)
                elif entry.is_dir() and entry.name not in BLOCKED_ROOT_PARTS:
                    entries.append(rel + "/")
            return {"ok": True, "files": entries[:200]}
        if name == "read_file":
            relative = arguments.get("path")
            if not isinstance(relative, str):
                raise AgentError("path must be a string")
            file_path = _relative_path(self.workspace, relative)
            if not file_path.is_file() or file_path.stat().st_size > MAX_FILE_BYTES:
                raise AgentError("File is missing, not regular, or exceeds the 256 KiB text limit")
            try:
                text = file_path.read_text(encoding="utf-8")
            except UnicodeDecodeError as exc:
                raise AgentError("Binary/non-UTF-8 file refused") from exc
            return {"ok": True, "path": relative, "text": text}
        if name == "ross_doc_search" and self.ross_docsearch_url:
            value = self._ross_call(arguments.get("query"))
            self.ross_doc_search_used = bool(value.get("ok"))
            if value.get("ok"):
                self.ross_evidence["AMD local Knowledge Base / vivado_doc_search"] = value
            return value
        if name == "ross_skill_read" and self.ross_docsearch_url:
            value = self._ross_skill(arguments.get("skill"), arguments.get("reference"))
            self.ross_skill_used = bool(value.get("ok"))
            if value.get("ok"):
                self.ross_evidence["installed AMD Ross Skill"] = value
            return value
        if name == "apply_patch":
            patch = arguments.get("patch")
            if not isinstance(patch, str) or len(patch) > 128 * 1024:
                raise AgentError("patch must be text no larger than 128 KiB")
            if self.ross_docsearch_url and not (self.ross_skill_used and self.ross_doc_search_used):
                return {"ok": False, "stage": "ross-prerequisite", "error": "Ross mode requires successful ross_skill_read and ross_doc_search calls before any source modification."}
            if self.last_failed_patch == patch:
                self.repeated_failed_patch_count += 1
                return {"ok": False, "stage": "patch-check", "error": "This exact diff was already rejected. Read the previous patch-check feedback, correct the unified-diff hunk syntax, and submit a different valid patch."}
            headers_normalized = _canonical_patch_headers(patch)
            try:
                paths = _patch_paths(headers_normalized, max_files=2 if self.multi_file_xsim else 1)
            except AgentError as exc:
                self.last_failed_patch = patch
                return {"ok": False, "stage": "patch-check", "error": str(exc)}
            if self.multi_file_xsim and len(paths) != 2:
                raise AgentError("The T2 multi-file task requires one patch that modifies both allowlisted RTL files")
            try:
                if self.multi_file_xsim:
                    allowed = {"rtl/local_model_axi_lite.v", "rtl/axi_result_datapath.v"}
                    if set(paths) != allowed:
                        raise AgentError("The T2 patch must target exactly the two allowlisted RTL files")
                    source_files = {relative: _relative_path(self.workspace, relative).read_text(encoding="utf-8") for relative in paths}
                    applied_patch = _normalize_multifile_git_patch(headers_normalized, paths, source_files)
                else:
                    source_files = {relative: _relative_path(self.workspace, relative).read_text(encoding='utf-8') for relative in paths}
                    applied_patch = _normalize_multifile_git_patch(headers_normalized, paths, source_files)
            except AgentError as exc:
                self.last_failed_patch = patch
                return {"ok": False, "stage": "patch-normalization", "error": str(exc)}
            if self.patch_count >= MAX_PATCHES:
                raise AgentError(f"Maximum {MAX_PATCHES} model-authored RTL corrections reached")
            for relative in paths:
                target = _relative_path(self.workspace, relative)
                if not target.is_file() or not _editable_allowed(relative, self.editable_paths):
                    raise AgentError(f"Patch path is not an allowed existing workspace file: {relative}")
            if self.xsim_enabled:
                permitted = {"rtl/local_model_axi_lite.v", "rtl/axi_result_datapath.v"} if self.multi_file_xsim else {"rtl/local_model_axi_lite.v"}
                if (set(paths) != permitted if self.multi_file_xsim else not set(paths).issubset(permitted)) or self.validation_count == 0:
                    raise AgentError("For this task only explicitly allowed RTL may change, and only after the unchanged baseline XSim run")
            if self.hls_enabled and (paths != ["src/invert32.cpp"] or self.validation_count == 0):
                raise AgentError("For this task only src/invert32.cpp may change, and only after the unchanged baseline HLS C simulation")
            check = subprocess.run(["git", "apply", "--check", "--whitespace=error", "-"], cwd=self.workspace, input=applied_patch, capture_output=True, text=True, timeout=10)
            if check.returncode:
                self.last_failed_patch = patch
                return {"ok": False, "stage": "patch-check", "exit_code": check.returncode, "error": check.stderr[-3000:]}
            applied = subprocess.run(["git", "apply", "--whitespace=error", "-"], cwd=self.workspace, input=applied_patch, capture_output=True, text=True, timeout=10)
            if applied.returncode:
                return {"ok": False, "stage": "patch-apply", "exit_code": applied.returncode, "error": applied.stderr[-3000:]}
            self.patch_count += 1
            self._trace({"event": "patch_applied", "paths": paths, "model_patch": patch, "applied_patch": applied_patch})
            formatting = ("Executor matched each model-authored old-text hunk uniquely against the exact source, applied the model's added/removed lines verbatim, then emitted canonical diff context and counts."
                          if self.multi_file_xsim and applied_patch != patch else "No formatting adjustment was needed.")
            return {"ok": True, "paths": paths, "patch_number": self.patch_count, "formatting": formatting, "message": "Model-authored source hunks applied after independent path and git-apply validation."}
        if name == "apply_replacement" and (self.xsim_enabled or self.hls_enabled):
            if self.multi_file_xsim:
                raise AgentError("The T2 profile accepts only one complete model-authored two-file diff; replacement calls are disabled")
            relative = arguments.get("path")
            old_text = arguments.get("old_text")
            new_text = arguments.get("new_text")
            if not all(isinstance(value, str) for value in (relative, old_text, new_text)):
                raise AgentError("path, old_text and new_text must be strings")
            if self.ross_docsearch_url and not (self.ross_skill_used and self.ross_doc_search_used):
                return {"ok": False, "stage": "ross-prerequisite", "error": "Ross mode requires successful ross_skill_read and ross_doc_search calls before any source modification."}
            if len(old_text) > MAX_REPLACEMENT_BYTES or len(new_text) > MAX_REPLACEMENT_BYTES or not old_text or old_text == new_text:
                raise AgentError(f"Replacement text must be nonempty, different and at most {MAX_REPLACEMENT_BYTES} bytes")
            if self.last_failed_patch is None:
                raise AgentError("Exact replacement is available only after a model-authored unified diff was rejected by patch validation")
            target = _relative_path(self.workspace, relative)
            expected_sources = {"rtl/local_model_axi_lite.v", "rtl/axi_result_datapath.v"} if self.multi_file_xsim else ({"rtl/local_model_axi_lite.v"} if self.xsim_enabled else {"src/invert32.cpp"})
            if relative not in expected_sources or self.validation_count == 0 or not _editable_allowed(relative, self.editable_paths):
                raise AgentError("Exact replacement is limited to the selected design source after its unchanged baseline run")
            if self.patch_count >= MAX_PATCHES or not target.is_file() or target.is_symlink():
                raise AgentError("Correction limit reached or RTL file is unavailable")
            original = target.read_text(encoding="utf-8")
            matches = original.count(old_text)
            if matches != 1:
                return {"ok": False, "stage": "replacement-check", "matches": matches, "error": "old_text must match exactly once; no source change occurred"}
            updated = original.replace(old_text, new_text, 1)
            patch = "".join(difflib.unified_diff(original.splitlines(keepends=True), updated.splitlines(keepends=True), fromfile=f"a/{relative}", tofile=f"b/{relative}"))
            check = subprocess.run(["git", "apply", "--check", "--whitespace=error", "-"], cwd=self.workspace, input=patch, capture_output=True, text=True, timeout=10)
            if check.returncode:
                return {"ok": False, "stage": "replacement-check", "exit_code": check.returncode, "error": check.stderr[-1000:]}
            applied = subprocess.run(["git", "apply", "--whitespace=error", "-"], cwd=self.workspace, input=patch, capture_output=True, text=True, timeout=10)
            if applied.returncode:
                return {"ok": False, "stage": "replacement-apply", "exit_code": applied.returncode, "error": applied.stderr[-1000:]}
            self.patch_count += 1
            self._trace({"event": "model_replacement_applied", "path": relative, "old_text": old_text, "new_text": new_text, "canonical_diff": patch})
            return {"ok": True, "path": relative, "patch_number": self.patch_count, "method": "model-authored exact replacement; executor generated a canonical diff without changing replacement text", "old_text": old_text, "new_text": new_text, "patch": patch}
        if name == "run_xsim" and self.xsim_enabled:
            if self.ross_docsearch_url and not (self.ross_skill_used and self.ross_doc_search_used):
                return {"ok": False, "stage": "ross-prerequisite", "error": "Ross mode requires successful ross_skill_read and ross_doc_search calls before XSim. Call both real Ross tools, then retry the fixed runner."}
            if self.patch_count and self.validation_count == 0:
                raise AgentError("Baseline must run before a patch")
            if self.validation_count > self.patch_count:
                raise AgentError("A model-authored source correction is required after the last failed XSim run before retrying")
            if self.patch_count and self.validation_count >= self.patch_count + 1:
                raise AgentError("A new model patch is required before another XSim run")
            if self.validation_count >= MAX_XSIM_RUNS:
                raise AgentError("Maximum XSim attempts reached")
            runner = "run_validation_multifile.sh" if self.multi_file_xsim else "run_validation.sh"
            required_files = (runner, "TASK_SPEC.md", "rtl/local_model_axi_lite.v", "rtl/axi_result_datapath.v", "sim/tb_local_model_axi_lite.sv") if self.multi_file_xsim else (runner, "TASK_SPEC.md", "rtl/local_model_axi_lite.v", "sim/tb_local_model_axi_lite.sv")
            for required in required_files:
                if not (self.workspace / required).is_file():
                    raise AgentError(f"Required M13 sandbox file missing: {required}")
            if self.validation_count == 0 and self.patch_count != 0:
                raise AgentError("Initial XSim must use unchanged starting RTL")
            self.validation_count += 1
            # The only command executed by the agent tool is this fixed runner.
            try:
                result = self._run_bounded(["/usr/bin/bash", f"./{runner}"], share_net=not self.offline_tools, timeout=300)
                output = (result.stdout + "\n" + result.stderr)[-MAX_TOOL_RESULT_CHARS:]
                pass_marker = "TEST_PASS multi_file_mode=1" if self.multi_file_xsim else "TEST_PASS baseline_and_selected_mode=1"
                passed = result.returncode == 0 and pass_marker in output
                if passed:
                    run_log = self.workspace / f"runs/attempt-{self.validation_count}/xsim.log"
                    passed = run_log.is_file() and pass_marker in run_log.read_text(errors="replace")
                self.xsim_passed = passed
                value = {"ok": passed, "stage": "xsim", "attempt": self.validation_count, "exit_code": result.returncode, "output": output, "terminal_pass_marker": passed}
            except subprocess.TimeoutExpired as exc:
                value = {"ok": False, "stage": "xsim", "attempt": self.validation_count, "error": f"Fixed XSim validation timed out after {exc.timeout}s"}
            self._trace({"event": "tool_result", "name": name, "result": value})
            return value
        if name == "run_hls" and self.hls_enabled:
            if self.ross_docsearch_url and not (self.ross_skill_used and self.ross_doc_search_used):
                return {"ok": False, "stage": "ross-prerequisite", "error": "Ross mode requires successful hls-run-flow Skill and AMD local MCP calls before HLS validation."}
            if self.patch_count and self.validation_count == 0:
                raise AgentError("Baseline HLS C simulation must run before a patch")
            if self.validation_count > self.patch_count:
                raise AgentError("A model-authored source correction is required after the last failed HLS run before retrying")
            if self.patch_count and self.validation_count >= self.patch_count + 1:
                raise AgentError("A new model-authored source correction is required before another HLS validation")
            if self.validation_count >= MAX_HLS_RUNS:
                raise AgentError("Maximum HLS validation runs reached")
            for required in ("hls_config.cfg", "src/invert32.cpp", "src/testbench.cpp"):
                if not (self.workspace / required).is_file():
                    raise AgentError(f"Required isolated HLS sandbox file missing: {required}")
            if self.validation_count == 0 and self.patch_count != 0:
                raise AgentError("Initial HLS C simulation must use unchanged starting source")
            self.validation_count += 1
            try:
                result = self._run_bounded(["/usr/bin/bash", str(ROOT / "scripts/run_m13_hls_validation.sh")], share_net=True, timeout=900)
                output = (result.stdout + "\n" + result.stderr)[-MAX_TOOL_RESULT_CHARS:]
                csim = "M13_HLS_CSIM_PASS" in output
                csynth = "M13_HLS_CSYNTH_PASS" in output
                value = {"ok": result.returncode == 0 and csim and csynth, "stage": "hls", "attempt": self.validation_count, "exit_code": result.returncode, "output": output, "csim_pass": csim, "csynth_pass": csynth}
                self.xsim_passed = bool(value["ok"])
            except subprocess.TimeoutExpired as exc:
                value = {"ok": False, "stage": "hls", "attempt": self.validation_count, "error": f"Fixed HLS validation timed out after {exc.timeout}s"}
            self._trace({"event": "tool_result", "name": name, "result": value})
            return value
        if name == "run_check" and not self.xsim_enabled:
            check = arguments.get("check")
            if check == "git-diff-check":
                result = self._run_bounded(["/usr/bin/git", "diff", "--check"], share_net=False, timeout=30)
                return {"ok": result.returncode == 0, "exit_code": result.returncode, "output": (result.stdout + result.stderr)[-4000:]}
            if check == "telegram-unit-tests":
                result = self._run_bounded(["/usr/bin/python3", str(self.workspace / "scripts/test_telegram_agent.py")], share_net=False, timeout=60)
                return {"ok": result.returncode == 0, "exit_code": result.returncode, "output": (result.stdout + result.stderr)[-6000:]}
            raise AgentError("Verification check is not allowlisted")
        raise AgentError(f"Tool is unavailable in this workspace: {name}")

    def run(self) -> str:
        for call_number in range(self.max_calls):
            response = self._completion()
            message = response["choices"][0]["message"]
            self._trace({"event": "model_response", "call": call_number + 1, "response": response})
            tool_calls = message.get("tool_calls") or []
            if not tool_calls:
                text = message.get("content") or ""
                if self.xsim_enabled and not self.xsim_passed:
                    raise AgentError("Qwen stopped without a verified XSim PASS; task is not complete")
                self._trace({"event": "agent_complete", "tool_calls": call_number})
                return text
            self.messages.append(message)
            feedbacks: list[str] = []
            compact_failure: dict[str, Any] | None = None
            for tool_call in tool_calls:
                name = tool_call.get("function", {}).get("name", "")
                call_id = tool_call.get("id", "")
                args: dict[str, Any] = {}
                try:
                    args = json.loads(tool_call.get("function", {}).get("arguments", "{}"))
                    if not isinstance(args, dict):
                        raise AgentError("Tool arguments must be a JSON object")
                    result: dict[str, Any] = self._tool(name, args)
                except Exception as exc:
                    result = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
                    if name == "apply_patch":
                        result["stage"] = "patch-check"
                        self.last_failed_patch = tool_call.get("function", {}).get("arguments", "")
                self._trace({"event": "tool_call", "name": name, "arguments": args if "args" in locals() else {}, "result": result})
                self.messages.append({"role": "tool", "tool_call_id": call_id, "content": json.dumps(result, ensure_ascii=False)[:MAX_TOOL_RESULT_CHARS]})
                if not result.get("ok"):
                    if result.get("stage") in {"xsim", "patch-check", "patch-normalization", "replacement-check"}:
                        compact_failure = result
                    if result.get("stage") == "patch-check":
                        if self.multi_file_xsim:
                            feedbacks.append(f"The two-file patch was rejected and no source changed: {result.get('error', 'unknown patch error')}. Read the validator feedback, then submit a corrected complete two-file unified diff; do not repeat this patch or switch to one-file replacement calls.")
                        else:
                            feedbacks.append(f"The patch tool rejected your diff and did not modify any source: {result.get('error', 'unknown patch error')}. Do not repeat it. Use apply_replacement with your intended exact old_text and new_text in the RTL; the executor only formats those exact model-selected strings into a valid diff.")
                    elif result.get("stage") == "patch-normalization":
                        if self.multi_file_xsim:
                            feedbacks.append(f"The two-file diff syntax is malformed and no source changed: {result.get('error')}. Re-read the tool feedback, correct the unified-diff hunk line prefixes/counts, and resubmit one complete diff for both files. Do not call a one-file replacement tool.")
                        else:
                            feedbacks.append(f"The source hunk could not be safely matched and no source changed: {result.get('error')}. Read the feedback and use apply_replacement with your own exact old_text and new_text from the allowed source; do not change the testbench.")
                    elif result.get("stage") == "replacement-check":
                        feedbacks.append(f"The exact replacement was rejected and no source changed: {result.get('error', 'replacement did not match uniquely')}. Read the tool result and select an exact source fragment that occurs once.")
                    elif result.get("stage") == "ross-prerequisite":
                        feedbacks.append(f"Ross prerequisite blocked this operation: {result.get('error')}. Use the actual installed Ross Skill and local MCP tools successfully, then continue.")
                    elif result.get("stage") in {"xsim", "hls"}:
                        flow = "HLS C-simulation/C-synthesis" if result.get("stage") == "hls" else "XSim"
                        feedbacks.append(f"The fixed {flow} run completed without PASS. Read its actual failure output in the preceding tool result, diagnose it, and submit a corrected design-source-only patch. Do not claim success before a later validation PASS.")
                if (self.xsim_enabled or self.hls_enabled) and self.xsim_passed:
                    # End on the executor's independently verified marker. A model
                    # response after PASS could otherwise issue more tool calls.
                    self._trace({"event": "agent_complete", "tool_calls": call_number + 1, "validation_pass": True})
                    flow = "HLS C simulation and C synthesis" if self.hls_enabled else "XSim"
                    return f"{flow} PASS verified by the fixed runner; the model-authored patch and full tool trace are retained."
            if feedbacks:
                self.correction_feedback_count += 1
                correction = "Tool feedback requiring correction: " + " ".join(feedbacks)
                # Some GGUF chat templates accept an assistant/tool continuation
                # but reject a new user turn after tool results. The structured
                # tool result already carries the detailed evidence, so retain
                # the correction as system guidance and continue directly with
                # the next assistant turn.
                # Keep only the latest correction so repeated feedback cannot
                # grow the system prompt on every turn.
                if self.system_prompt_base is None:
                    self.system_prompt_base = self.messages[0]["content"]
                self.messages[0]["content"] = self.system_prompt_base + " " + correction[:MAX_CORRECTION_CHARS]
                if compact_failure is not None:
                    self._compact_multifile_context(compact_failure)
        raise AgentError(f"Local Agent reached its bounded limit ({self.max_calls} model/tool turns)")

    def close(self) -> None:
        if not self.ross_docsearch_url or not self._ross_session:
            return
        request = urllib.request.Request(self.ross_docsearch_url, headers={"Mcp-Session-Id": self._ross_session}, method="DELETE")
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect())
        try:
            with opener.open(request, timeout=3):
                pass
        except Exception:
            pass
        self._ross_session = None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--task", required=True)
    parser.add_argument("--model", default=os.environ.get("AI370_LOCAL_MODEL", DEFAULT_MODEL))
    parser.add_argument("--base-url", default=os.environ.get("AI370_LOCAL_BASE_URL", DEFAULT_BASE_URL))
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--total-timeout", type=int, default=1800)
    parser.add_argument("--max-completion-tokens", type=int, default=512, help="Bounded local model response budget (maximum 8192)")
    parser.add_argument("--max-calls", type=int, default=MAX_TOOL_CALLS)
    parser.add_argument("--trace", type=Path)
    parser.add_argument("--editable-path", action="append", default=[])
    parser.add_argument("--offline-tools", action="store_true", help="Run child tools in a network-isolated namespace; Vivado host-NIC license checkout may then be unavailable")
    parser.add_argument("--xsim", action="store_true", help="Expose only the fixed M13 RTL/XSim tool in this workspace")
    parser.add_argument("--multi-file-xsim", action="store_true", help="Enable the bounded M13 two-file RTL/XSim profile; both editable paths must be explicitly allowlisted")
    parser.add_argument("--hls", action="store_true", help="Expose only the fixed M13 Vitis HLS C-simulation/C-synthesis tool in this workspace")
    parser.add_argument("--ross-docsearch-url", default=os.environ.get("AI370_ROSS_DOCSEARCH_URL"), help="Explicitly enable real AMD local doc-search MCP tools at a loopback/private endpoint")
    parser.add_argument("--ross-context-chars", type=int, default=MAX_ROSS_CONTEXT_CHARS, help="Maximum combined installed Ross Skill/reference excerpt characters returned to the local model")
    parser.add_argument("--ross-mcp-chars", type=int, default=MAX_ROSS_MCP_CHARS, help="Maximum AMD local Knowledge Base response characters returned to the local model")
    args = parser.parse_args()
    agent = None
    try:
        if args.multi_file_xsim and args.hls:
            raise AgentError("Multi-file XSim and HLS profiles cannot be enabled together")
        agent = LocalAgent(args.workspace, task=args.task, model=args.model, base_url=args.base_url, timeout=args.timeout, total_timeout=args.total_timeout, max_completion_tokens=args.max_completion_tokens, max_calls=args.max_calls, trace=args.trace, editable_paths=set(args.editable_path), offline_tools=args.offline_tools, xsim_enabled=args.xsim or args.multi_file_xsim, multi_file_xsim=args.multi_file_xsim, hls_enabled=args.hls, ross_docsearch_url=args.ross_docsearch_url, ross_context_chars=args.ross_context_chars, ross_mcp_chars=args.ross_mcp_chars)
        try:
            result = agent.run()
        finally:
            agent.close()
        verify_enabled = _verification_profile_enabled(xsim=args.xsim, multi_file_xsim=args.multi_file_xsim, hls=args.hls)
        status = "PASS" if verify_enabled and agent.xsim_passed and agent.patch_count >= 1 and agent.validation_count >= 2 else "COMPLETED"
        if verify_enabled and status != "PASS":
            raise AgentError("Task ended without a model-authored source patch and independently verified post-patch PASS")
        print(json.dumps({"status": status, "model": args.model, "workspace": str(args.workspace.resolve()), "xsim_runs": agent.validation_count, "patches": agent.patch_count, "metrics": {"model_request_seconds": round(agent.model_request_s, 3), "ross_mcp_seconds": round(agent.ross_tool_overhead_s, 3), "prompt_tokens": agent.prompt_tokens, "completion_tokens": agent.completion_tokens}, "result": result}, ensure_ascii=False))
        return 0
    except Exception as exc:
        failure = {"status": "FAIL", "error": f"{type(exc).__name__}: {exc}"}
        if agent is not None:
            failure.update(model=args.model, patches=agent.patch_count, xsim_runs=agent.validation_count, metrics={"model_request_seconds": round(agent.model_request_s, 3), "ross_mcp_seconds": round(agent.ross_tool_overhead_s, 3), "prompt_tokens": agent.prompt_tokens, "completion_tokens": agent.completion_tokens})
            agent._trace({"event": "agent_failed", **failure})
        print(json.dumps(failure, ensure_ascii=False))
        print(json.dumps(failure, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
