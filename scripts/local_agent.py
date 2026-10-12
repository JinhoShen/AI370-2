#!/usr/bin/env python3
"""Local Qwen agent with a small, policy-checked local tool executor.

The model can only request the functions declared below. It cannot submit a
shell command. All provider traffic is pinned to loopback; command tools run in
Bubblewrap with the repository read-only except for the selected workspace.
"""

from __future__ import annotations

import argparse
import difflib
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


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODEL = "Qwen3.8-27B-UD-Q4_K_XL"
DEFAULT_BASE_URL = "http://127.0.0.1:13305/api/v1"
MAX_FILE_BYTES = 256 * 1024
MAX_TOOL_RESULT_CHARS = 12000
MAX_TOOL_CALLS = 24
MAX_XSIM_RUNS = 3
MAX_PATCHES = 2
BLOCKED_ROOT_PARTS = {".git", "resources", "output", ".venv", "venv", "node_modules"}
BLOCKED_NAMES = {".env", ".netrc", "credentials", "Xilinx_shen.lic"}
BLOCKED_EXTENSIONS = {".gguf", ".onnx", ".lic", ".pem", ".key", ".p12", ".pfx", ".bit", ".bin"}
PROTECTED_PATHS = (
    ("docs", "M11", "evidence"),
    ("docs", "M12", "evidence"),
)


class AgentError(RuntimeError):
    pass


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


def _patch_paths(patch: str) -> list[str]:
    paths: list[str] = []
    for line in patch.splitlines():
        if line.startswith("--- ") or line.startswith("+++ "):
            raw = line[4:].split("\t", 1)[0].strip()
            if raw == "/dev/null":
                paths.append(raw)
                continue
            if raw.startswith(("a/", "b/")):
                raw = raw[2:]
            paths.append(raw)
    if len(paths) != 2 or paths[0] != paths[1]:
        raise AgentError("Patch must modify exactly one existing file; renames/deletes are not allowed")
    return [paths[0]]


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
        max_calls: int = MAX_TOOL_CALLS,
        trace: Path | None = None,
        editable_paths: set[str] | None = None,
        offline_tools: bool = False,
        xsim_enabled: bool = False,
    ):
        self.workspace = workspace.resolve(strict=True)
        if not self.workspace.is_dir():
            raise AgentError("Workspace is not a directory")
        self.task = task
        self.model = model
        self.base_url = _loopback_endpoint(base_url)
        self.timeout = timeout
        self.deadline = time.monotonic() + total_timeout
        self.max_calls = min(max_calls, MAX_TOOL_CALLS)
        self.trace = trace
        self.editable_paths = editable_paths or set()
        self.offline_tools = offline_tools
        self.xsim_enabled = xsim_enabled
        self.validation_count = 0
        self.patch_count = 0
        self.last_failed_patch: str | None = None
        self.repeated_failed_patch_count = 0
        self.correction_feedback_count = 0
        self.xsim_passed = False
        self.messages: list[dict[str, Any]] = [
            {
                "role": "system",
                "content": (
                    "You are the AI370-2 Local Engineering Agent. You run locally on the user's workstation. "
                    "You have no shell tool and must use only the provided local functions. Read the task and source "
                    "before acting. Keep tool calls and final explanations concise. For RTL repair, read the task and DUT, "
                    "then immediately run the unchanged baseline before patching; diagnose "
                    "actual XSim output, apply the smallest RTL-only diff, then rerun until the test reports PASS. "
                    "If a unified diff is rejected for hunk syntax, use apply_replacement with the exact old and new RTL line from your own proposed fix; it will validate and format that exact replacement. "
                    "Never edit a testbench or weaken a check. Do not claim success without a terminal PASS marker. "
                    "The tool executor enforces workspace, file, command, timeout, network and retry policy."
                ),
            },
            {"role": "user", "content": task},
        ]
        self.tool_calls = self._tool_specs()
        self._trace({"event": "agent_start", "model": model, "provider": self.base_url, "workspace": str(self.workspace), "offline_tools": offline_tools})

    def _tool_specs(self) -> list[dict[str, Any]]:
        tools = [
            {"type": "function", "function": {"name": "list_files", "description": "List safe text files in a workspace directory.", "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"], "additionalProperties": False}}},
            {"type": "function", "function": {"name": "read_file", "description": "Read one safe UTF-8 text file from the selected workspace.", "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"], "additionalProperties": False}}},
            {"type": "function", "function": {"name": "apply_patch", "description": "Apply one unified diff to one allowed workspace file after checking it with git apply.", "parameters": {"type": "object", "properties": {"patch": {"type": "string"}}, "required": ["patch"], "additionalProperties": False}}},
        ]
        if self.xsim_enabled:
            tools.append({"type": "function", "function": {"name": "apply_replacement", "description": "After a rejected patch-format attempt, replace exactly one model-selected existing RTL text fragment. The executor validates a unique exact match and mechanically formats that same before/after text into a unified diff; it does not choose or alter replacement logic.", "parameters": {"type": "object", "properties": {"path": {"type": "string"}, "old_text": {"type": "string"}, "new_text": {"type": "string"}}, "required": ["path", "old_text", "new_text"], "additionalProperties": False}}})
            tools.append({"type": "function", "function": {"name": "run_xsim", "description": "Run only the fixed, bounded Vivado XSim smoke script in this isolated M13 workspace and return its real logs.", "parameters": {"type": "object", "properties": {}, "additionalProperties": False}}})
        else:
            tools.append({"type": "function", "function": {"name": "run_check", "description": "Run one fixed local verification check from the allowlist.", "parameters": {"type": "object", "properties": {"check": {"type": "string", "enum": ["git-diff-check", "telegram-unit-tests"]}}, "required": ["check"], "additionalProperties": False}}})
        return tools

    def _trace(self, obj: dict[str, Any]) -> None:
        if self.trace:
            self.trace.parent.mkdir(parents=True, exist_ok=True)
            with self.trace.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(obj, ensure_ascii=False) + "\n")

    def _completion(self) -> dict[str, Any]:
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise AgentError("Local Agent reached its total wall-clock limit")
        temperature = 0.25 if self.correction_feedback_count else 0
        body = json.dumps({"model": self.model, "messages": self.messages, "tools": self.tool_calls, "tool_choice": "auto", "temperature": temperature, "max_tokens": 512}, ensure_ascii=False).encode()
        request = urllib.request.Request(self.base_url + "/chat/completions", data=body, headers={"Content-Type": "application/json"})
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect())
        try:
            with opener.open(request, timeout=min(self.timeout, max(1, remaining))) as response:
                payload = response.read(8 * 1024 * 1024 + 1)
                if len(payload) > 8 * 1024 * 1024:
                    raise AgentError("Local provider response exceeded the 8 MiB limit")
                data = json.loads(payload)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise AgentError(f"Local Qwen request failed: {type(exc).__name__}: {exc}") from exc
        if not isinstance(data.get("choices"), list) or not data["choices"]:
            raise AgentError("Local Qwen returned no completion choices")
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
        if name == "apply_patch":
            patch = arguments.get("patch")
            if not isinstance(patch, str) or len(patch) > 128 * 1024:
                raise AgentError("patch must be text no larger than 128 KiB")
            if self.last_failed_patch == patch:
                self.repeated_failed_patch_count += 1
                return {"ok": False, "stage": "patch-check", "error": "This exact diff was already rejected. Read the previous patch-check feedback, correct the unified-diff hunk syntax, and submit a different valid patch."}
            paths = _patch_paths(patch)
            if paths == ["/dev/null"]:
                raise AgentError("New files are not accepted by the bounded patch tool")
            relative = paths[0]
            target = _relative_path(self.workspace, relative)
            if self.patch_count >= MAX_PATCHES:
                raise AgentError(f"Maximum {MAX_PATCHES} model-authored RTL corrections reached")
            if not target.is_file() or not _editable_allowed(relative, self.editable_paths):
                raise AgentError(f"Patch path is not an allowed existing workspace file: {relative}")
            if self.xsim_enabled and (relative != "rtl/local_model_axi_lite.v" or self.validation_count == 0):
                raise AgentError("For this task only the RTL may change, and only after the unchanged baseline XSim run")
            check = subprocess.run(["git", "apply", "--check", "--whitespace=error", "-"], cwd=self.workspace, input=patch, capture_output=True, text=True, timeout=10)
            if check.returncode:
                self.last_failed_patch = patch
                value = {"ok": False, "stage": "patch-check", "exit_code": check.returncode, "error": check.stderr[-3000:]}
                return value
            applied = subprocess.run(["git", "apply", "--whitespace=error", "-"], cwd=self.workspace, input=patch, capture_output=True, text=True, timeout=10)
            if applied.returncode:
                return {"ok": False, "stage": "patch-apply", "exit_code": applied.returncode, "error": applied.stderr[-3000:]}
            self.patch_count += 1
            self._trace({"event": "patch_applied", "path": relative, "patch": patch})
            return {"ok": True, "path": relative, "patch_number": self.patch_count, "message": "Exact submitted patch applied; no agent-side edits were added."}
        if name == "apply_replacement" and self.xsim_enabled:
            relative = arguments.get("path")
            old_text = arguments.get("old_text")
            new_text = arguments.get("new_text")
            if not all(isinstance(value, str) for value in (relative, old_text, new_text)):
                raise AgentError("path, old_text and new_text must be strings")
            if len(old_text) > 4096 or len(new_text) > 4096 or not old_text or old_text == new_text:
                raise AgentError("Replacement text must be nonempty, different and at most 4096 bytes")
            if self.last_failed_patch is None:
                raise AgentError("Exact replacement is available only after a model-authored unified diff was rejected by patch validation")
            target = _relative_path(self.workspace, relative)
            if relative != "rtl/local_model_axi_lite.v" or self.validation_count == 0 or not _editable_allowed(relative, self.editable_paths):
                raise AgentError("This XSim task only allows exact replacement in the RTL after the unchanged baseline run")
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
            if self.patch_count and self.validation_count == 0:
                raise AgentError("Baseline must run before a patch")
            if self.patch_count and self.validation_count >= self.patch_count + 1:
                raise AgentError("A new model patch is required before another XSim run")
            if self.validation_count >= MAX_XSIM_RUNS:
                raise AgentError("Maximum XSim attempts reached")
            for required in ("run_validation.sh", "TASK_SPEC.md", "rtl/local_model_axi_lite.v", "sim/tb_local_model_axi_lite.sv"):
                if not (self.workspace / required).is_file():
                    raise AgentError(f"Required M13 sandbox file missing: {required}")
            if self.validation_count == 0 and self.patch_count != 0:
                raise AgentError("Initial XSim must use unchanged starting RTL")
            self.validation_count += 1
            # The only command executed by the agent tool is this fixed runner.
            try:
                result = self._run_bounded(["/usr/bin/bash", "./run_validation.sh"], share_net=not self.offline_tools, timeout=300)
                output = (result.stdout + "\n" + result.stderr)[-MAX_TOOL_RESULT_CHARS:]
                passed = result.returncode == 0 and "TEST_PASS baseline_and_selected_mode=1" in output
                if passed:
                    run_log = self.workspace / f"runs/attempt-{self.validation_count}/xsim.log"
                    passed = run_log.is_file() and "TEST_PASS baseline_and_selected_mode=1" in run_log.read_text(errors="replace")
                self.xsim_passed = passed
                value = {"ok": passed, "stage": "xsim", "attempt": self.validation_count, "exit_code": result.returncode, "output": output, "terminal_pass_marker": passed}
            except subprocess.TimeoutExpired as exc:
                value = {"ok": False, "stage": "xsim", "attempt": self.validation_count, "error": f"Fixed XSim validation timed out after {exc.timeout}s"}
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
            for tool_call in tool_calls:
                name = tool_call.get("function", {}).get("name", "")
                call_id = tool_call.get("id", "")
                try:
                    args = json.loads(tool_call.get("function", {}).get("arguments", "{}"))
                    if not isinstance(args, dict):
                        raise AgentError("Tool arguments must be a JSON object")
                    result: dict[str, Any] = self._tool(name, args)
                except Exception as exc:
                    args = {}
                    result = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
                self._trace({"event": "tool_call", "name": name, "arguments": args if "args" in locals() else {}, "result": result})
                self.messages.append({"role": "tool", "tool_call_id": call_id, "content": json.dumps(result, ensure_ascii=False)[:MAX_TOOL_RESULT_CHARS]})
                if not result.get("ok"):
                    if result.get("stage") == "patch-check":
                        feedbacks.append(f"The patch tool rejected your diff and did not modify any source: {result.get('error', 'unknown patch error')}. Do not repeat it. Use apply_replacement with your intended exact old_text and new_text in the RTL; the executor only formats those exact model-selected strings into a valid diff.")
                    elif result.get("stage") == "replacement-check":
                        feedbacks.append(f"The exact replacement was rejected and no source changed: {result.get('error', 'replacement did not match uniquely')}. Read the tool result and select an exact source fragment that occurs once.")
                    elif result.get("stage") == "xsim":
                        feedbacks.append("The fixed XSim run completed without PASS. Read its actual failure output in the preceding tool result, diagnose it, and submit a corrected RTL-only patch. Do not claim success before a later XSim PASS.")
                if self.xsim_enabled and self.xsim_passed:
                    # End on the executor's independently verified marker. A model
                    # response after PASS could otherwise issue more tool calls.
                    self._trace({"event": "agent_complete", "tool_calls": call_number + 1, "xsim_pass": True})
                    return "XSim PASS verified by the fixed runner; the model-authored patch and full tool trace are retained."
            if feedbacks:
                self.correction_feedback_count += 1
                correction = "Tool feedback requiring correction: " + " ".join(feedbacks)
                self.messages[0]["content"] += " A previous tool operation was rejected; never repeat that failed action unchanged. Read tool feedback and produce a corrected action."
                self.messages.append({"role": "user", "content": correction})
        raise AgentError(f"Local Agent reached its bounded limit ({self.max_calls} model/tool turns)")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--task", required=True)
    parser.add_argument("--model", default=os.environ.get("AI370_LOCAL_MODEL", DEFAULT_MODEL))
    parser.add_argument("--base-url", default=os.environ.get("AI370_LOCAL_BASE_URL", DEFAULT_BASE_URL))
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--total-timeout", type=int, default=1800)
    parser.add_argument("--max-calls", type=int, default=MAX_TOOL_CALLS)
    parser.add_argument("--trace", type=Path)
    parser.add_argument("--editable-path", action="append", default=[])
    parser.add_argument("--offline-tools", action="store_true", help="Run child tools in a network-isolated namespace; Vivado host-NIC license checkout may then be unavailable")
    parser.add_argument("--xsim", action="store_true", help="Expose only the fixed M13 RTL/XSim tool in this workspace")
    args = parser.parse_args()
    try:
        agent = LocalAgent(args.workspace, task=args.task, model=args.model, base_url=args.base_url, timeout=args.timeout, total_timeout=args.total_timeout, max_calls=args.max_calls, trace=args.trace, editable_paths=set(args.editable_path), offline_tools=args.offline_tools, xsim_enabled=args.xsim)
        result = agent.run()
        status = "PASS" if args.xsim and agent.xsim_passed and agent.patch_count >= 1 and agent.validation_count >= 2 else "COMPLETED"
        if args.xsim and status != "PASS":
            raise AgentError("XSim task ended without a model-authored patch and independently verified post-patch PASS")
        print(json.dumps({"status": status, "model": args.model, "workspace": str(args.workspace.resolve()), "xsim_runs": agent.validation_count, "patches": agent.patch_count, "result": result}, ensure_ascii=False))
        return 0
    except Exception as exc:
        print(json.dumps({"status": "FAIL", "error": f"{type(exc).__name__}: {exc}"}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
