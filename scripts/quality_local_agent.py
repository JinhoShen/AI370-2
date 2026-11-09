#!/usr/bin/env python3
"""Bounded function-call agent for frozen quality-corpus workspaces."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from local_agent import AgentError, LocalAgent, ROOT, _relative_path


def validate_t8_delivery_summary(summary: str, payload: dict, rtl_path: Path) -> dict:
    xsim=payload.get("xsim",{}); synth=payload.get("synthesis",{})
    digest=hashlib.sha256(rtl_path.read_bytes()).hexdigest()
    expected=["STATUS=PASS",f"XSim=PASS marker={xsim.get('terminal_marker')}",
              f"SYNTHESIS=PASS report={synth.get('utilization_report')}",f"RTL_SHA256={digest}"]
    lines=summary.splitlines()
    missing=[line for line in expected if line not in lines]
    return {"pass":not missing,"expected_lines":expected,"missing_lines":missing,"actual_rtl_sha256":digest}


class QualityAgent(LocalAgent):
    def __init__(self, *, task: str, task_id: str, variant: str, workspace: Path, model: str, base_url: str,
                 timeout: int, total_timeout: int, completion_tokens: int, max_calls: int,
                 editable_paths: set[str], trace: Path | None, ross_docsearch_url: str | None = None):
        self.quality_task = task_id
        self.quality_variant = variant
        self.quality_workspace = workspace.resolve(strict=True)
        if task_id == "T7" and not ross_docsearch_url:
            raise AgentError("T7 requires the installed Ross Skill reader and AMD documentation MCP endpoint; no model request was started.")
        super().__init__(
            self.quality_workspace, task=task, model=model, base_url=base_url,
            timeout=timeout, total_timeout=total_timeout,
            max_completion_tokens=completion_tokens, max_calls=max_calls,
            trace=trace, editable_paths=editable_paths, xsim_enabled=False,
            ross_docsearch_url=ross_docsearch_url, fixed_temperature=0.0, fixed_seed=20261022,
        )
        self.xsim_enabled = True
        self.tool_calls = [tool for tool in self.tool_calls if tool["function"]["name"] != "run_check"]
        self.tool_calls.append({"type": "function", "function": {
            "name": "apply_replacement",
            "description": "After a rejected unified diff, replace one exact model-selected source fragment. The executor requires one unique old_text match and creates the diff mechanically without changing the proposed source text.",
            "parameters": {"type": "object", "properties": {"path": {"type": "string"}, "old_text": {"type": "string"}, "new_text": {"type": "string"}}, "required": ["path", "old_text", "new_text"], "additionalProperties": False},
        }})
        self.tool_calls.append({"type": "function", "function": {
            "name": "run_quality_validation",
            "description": "Run the fixed hidden task validator for this frozen variant. No command or paths are accepted.",
            "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
        }})
        self.messages[0]["content"] = (
            "You are a local FPGA engineering agent. You have no shell tool. Read the frozen task and public RTL, "
            "run the unchanged baseline exactly once, diagnose actual fixed-validator output, submit the smallest "
            "allowed source-only patch, and rerun. Never edit task specifications, tests, hidden assets, validators, "
            "or runner files. Do not repeat a baseline after it fails. Do not claim success without the fixed task PASS marker."
        )
        self.quality_validation_count = 0
        self.quality_pass = False
        self.last_quality_payload = None

    def _tool(self, name: str, arguments: dict):
        if self.quality_task == "T8" and self.quality_pass and name in {"apply_patch", "apply_replacement", "run_quality_validation"}:
            return {"ok": False, "stage": "delivery-summary", "error": "Validation already passed; no further source edits or reruns are allowed. Provide the required evidence-backed delivery summary."}
        if name == "apply_patch":
            if self.quality_validation_count == 0:
                return {"ok": False, "stage": "patch-check", "error": "Run the unchanged baseline before modifying source."}
            if self.quality_validation_count <= self.patch_count:
                return {"ok": False, "stage": "patch-check", "error": "Run the fixed validator and inspect its failure before another source patch."}
            self.xsim_enabled = False
            try:
                return super()._tool(name, arguments)
            finally:
                self.xsim_enabled = True
        if name == "run_quality_validation":
            if arguments:
                return {"ok": False, "stage": "xsim", "error": "This fixed validation tool accepts no arguments."}
            if self.quality_validation_count == 0 and self.patch_count:
                return {"ok": False, "stage": "xsim", "error": "The baseline must run before any source patch."}
            if self.quality_validation_count > self.patch_count:
                return {"ok": False, "stage": "xsim", "error": "A source patch is required after the last failed validator run."}
            if self.quality_validation_count >= 3:
                return {"ok": False, "stage": "xsim", "error": "The frozen three-attempt cap was reached."}
            if self.quality_task == "T7" and not (self.ross_skill_used and self.ross_doc_search_used):
                return {"ok": False, "stage": "ross-prerequisite", "error": "T7 requires successful Ross Skill and AMD documentation calls before simulation."}
            self.quality_validation_count += 1
            command = [
                sys.executable, str(ROOT / "scripts/quality_task_executor.py"),
                "--task", self.quality_task, "--variant", self.quality_variant,
                "--workspace", str(self.quality_workspace), "--attempt", str(self.quality_validation_count),
            ]
            try:
                result = self._run_bounded(command, share_net=True, timeout=900)
            except Exception as exc:
                return {"ok": False, "stage": "xsim", "attempt": self.quality_validation_count,
                        "error": f"Fixed quality validation failed to execute: {type(exc).__name__}: {exc}"}
            try:
                payload = json.loads(result.stdout.splitlines()[-1])
            except (json.JSONDecodeError, IndexError):
                payload = {"status": "HARNESS_INVALID", "error": result.stdout[-2000:] + result.stderr[-2000:]}
            xsim = payload.get("xsim", payload.get("csim", {}))
            synth = payload.get("synthesis", payload.get("csynth", {}))
            terminal = xsim.get("terminal_marker")
            self.xsim_passed = result.returncode == 0 and payload.get("status") == "PASS" and bool(terminal) and synth.get("pass") is True
            self.quality_pass = self.xsim_passed and self.quality_validation_count > 1 and self.patch_count > 0
            self.last_quality_payload = payload
            if self.quality_task == "T8" and self.quality_pass:
                # Let the model produce its required final delivery summary after
                # the fixed runner passes; subsequent write/run calls are blocked.
                self.xsim_enabled = False
            summary = {
                "status": payload.get("status"), "task": self.quality_task,
                "variant": self.quality_variant, "attempt": self.quality_validation_count,
                "xsim": {"pass": xsim.get("pass"), "terminal_marker": terminal,
                         "last_log": (xsim.get("log_tail") or (xsim.get("xsim") or {}).get("tail", ""))[-3000:]},
                "csim_diagnostic": payload.get("csim_diagnostic"),
                "mutation_detection": payload.get("mutation_detection"),
                "synthesis": {"pass": synth.get("pass"), "latch_diagnostics": synth.get("latch_diagnostics"),
                              "utilization_report": synth.get("utilization_report")},
                "rtl_sha256": payload.get("source_sha256_after"),
                "source_unchanged_during_validation": payload.get("source_unchanged_during_validation"),
                "error": payload.get("error"),
            }
            return {"ok": self.xsim_passed, "stage": "xsim", "attempt": self.quality_validation_count,
                    "exit_code": result.returncode, "terminal_pass_marker": bool(terminal),
                    "output": json.dumps(summary, ensure_ascii=False)}
        return super()._tool(name, arguments)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--task", choices=["T1", "T2", "T3", "T4", "T5", "T6", "T7", "T8"], required=True)
    parser.add_argument("--variant", choices=["V1", "V2", "V3"], required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--editable-path", action="append", default=[])
    parser.add_argument("--timeout", type=int, default=600)
    parser.add_argument("--total-timeout", type=int, default=2400)
    parser.add_argument("--max-completion-tokens", type=int, default=8192)
    parser.add_argument("--max-calls", type=int, default=14)
    parser.add_argument("--trace", type=Path)
    parser.add_argument("--ross-docsearch-url")
    args = parser.parse_args()
    agent = None
    try:
        task_path = args.workspace / "TASK_SPEC.md"
        task = task_path.read_text(encoding="utf-8")
        task += "\nExecution instruction: call run_quality_validation once on unchanged source; read the actual failure; patch only "
        task += ", ".join(args.editable_path) + "; then rerun the fixed validator. No more than three validator calls."
        agent = QualityAgent(task=task, task_id=args.task, variant=args.variant, workspace=args.workspace, model=args.model,
                             base_url=args.base_url, timeout=args.timeout, total_timeout=args.total_timeout,
                             completion_tokens=args.max_completion_tokens, max_calls=args.max_calls,
                             editable_paths=set(args.editable_path), trace=args.trace,
                             ross_docsearch_url=args.ross_docsearch_url)
        result = agent.run()
        if not agent.quality_pass or agent.patch_count < 1 or agent.quality_validation_count < 2:
            raise AgentError("Task ended without a model-authored patch and XSim+synthesis PASS")
        if args.task == "T8":
            payload = agent.last_quality_payload or {}
            rtl = args.workspace / "rtl/axi_regs.sv"
            audit=validate_t8_delivery_summary(result,payload,rtl)
            if not audit["pass"]:
                raise AgentError("T8 delivery summary did not reproduce every required PASS marker, report path and final RTL SHA-256 exactly")
            agent._trace({"event":"delivery_summary_audit","result":audit})
        print(json.dumps({"status": "PASS", "model": args.model, "task": args.task, "variant": args.variant,
                          "patches": agent.patch_count, "validation_attempts": agent.quality_validation_count,
                          "metrics": {"model_request_seconds": round(agent.model_request_s, 3),
                                      "prompt_tokens": agent.prompt_tokens, "completion_tokens": agent.completion_tokens},
                          "result": result}, ensure_ascii=False))
        return 0
    except Exception as exc:
        failure = {"status": "FAIL", "error": f"{type(exc).__name__}: {exc}"}
        if agent:
            failure.update(model=args.model, task=args.task, variant=args.variant,
                           patches=agent.patch_count, validation_attempts=agent.quality_validation_count,
                           metrics={"model_request_seconds": round(agent.model_request_s, 3),
                                    "prompt_tokens": agent.prompt_tokens, "completion_tokens": agent.completion_tokens})
            agent._trace({"event": "quality_agent_failed", **failure})
        print(json.dumps(failure, ensure_ascii=False))
        return 1
    finally:
        if agent:
            agent.close()


if __name__ == "__main__":
    raise SystemExit(main())
