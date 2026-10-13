#!/usr/bin/env python3
"""Inventory and run bounded M13 A/B cohorts against an already-active local model.

This tool never loads, unloads, or switches a model. `run` fails closed unless
the requested model is already visible from the selected loopback API endpoint.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import statistics
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config/local_model_lab.json"
TASK_KEYS = ("T1", "T2", "T3")


def load_config() -> dict[str, Any]:
    data = json.loads(CONFIG_PATH.read_text())
    if data.get("schema_version") != 1:
        raise ValueError("unsupported Model Lab config schema")
    return data


def model_for(config: dict[str, Any], key: str) -> dict[str, Any]:
    for model in config["models"]:
        if model["key"] == key:
            return model
    raise KeyError(f"unknown model key: {key}")


def inventory(config: dict[str, Any], full_hash: bool = False) -> list[dict[str, Any]]:
    root = ROOT / config["model_root"]
    rows = []
    for model in config["models"]:
        row = {k: model.get(k) for k in ("key", "name", "selected_artifact", "status", "sha256")}
        relative = model.get("relative_path")
        if not relative:
            row.update(path=None, exists=False, observed_bytes=None, observed_sha256=None, sha_matches=None)
        else:
            path = root / relative
            row.update(path=str(path), exists=path.is_file(), observed_bytes=path.stat().st_size if path.is_file() else None)
            row["observed_sha256"] = None
            if full_hash and path.is_file():
                digest = hashlib.sha256()
                with path.open("rb") as f:
                    while block := f.read(8 * 1024 * 1024):
                        digest.update(block)
                row["observed_sha256"] = digest.hexdigest()
            row["sha_matches"] = row["observed_sha256"] == model["sha256"] if row["observed_sha256"] else None
        rows.append(row)
    for variant in config.get("additional_local_variants_not_in_five_model_roster", []):
        path = root / variant["artifact"]
        row = {"key": "qwen38_variant", "name": variant["artifact"], "selected_artifact": variant["artifact"], "status": variant["status"], "sha256": variant["sha256"], "path": str(path), "exists": path.is_file(), "observed_bytes": path.stat().st_size if path.is_file() else None, "observed_sha256": None}
        if full_hash and path.is_file():
            digest = hashlib.sha256()
            with path.open("rb") as f:
                while block := f.read(8 * 1024 * 1024):
                    digest.update(block)
            row["observed_sha256"] = digest.hexdigest()
        row["sha_matches"] = row["observed_sha256"] == variant["sha256"] if row["observed_sha256"] else None
        rows.append(row)
    return rows


def api_models(api_base: str, timeout: float = 3.0) -> list[str]:
    parsed = urllib.parse.urlparse(api_base)
    if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError("provider must be an unauthenticated loopback HTTP URL")
    prefix = api_base.rstrip("/")
    try:
        with urllib.request.urlopen(prefix + "/health", timeout=timeout) as response:
            health = json.load(response)
        loaded = health.get("all_models_loaded", [])
        active = []
        for row in loaded:
            if not row.get("loaded") or row.get("status") != "ready":
                continue
            for field in ("model_name", "checkpoint"):
                value = row.get(field)
                if isinstance(value, str) and value not in active:
                    active.append(value)
        if active:
            return active
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        pass
    with urllib.request.urlopen(prefix + "/models", timeout=timeout) as response:
        body = json.load(response)
    rows = body.get("data", body.get("models", []))
    result = []
    for row in rows:
        if isinstance(row, dict):
            for field in ("id", "model", "name"):
                value = row.get(field)
                if isinstance(value, str) and value not in result:
                    result.append(value)
    return result


def active_llama_server(model_id: str) -> list[str]:
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        try:
            argv = [x.decode(errors="replace") for x in (entry / "cmdline").read_bytes().split(b"\0") if x]
        except OSError:
            continue
        if argv and Path(argv[0]).name == "llama-server" and model_id in argv:
            return argv
    return []


def verify_active_model(config: dict[str, Any], key: str, api_base: str, verify_hash: bool = True) -> tuple[dict[str, Any], list[str]]:
    model = model_for(config, key)
    if model.get("status") in {"NOT_INSTALLED", "WAITING_FOR_MODEL_SELECTION"}:
        raise RuntimeError(f"{model['status']}: no model artifact is configured")
    artifact = ROOT / config["model_root"] / str(model.get("relative_path"))
    if not artifact.is_file() or artifact.stat().st_size != model.get("bytes"):
        raise RuntimeError("configured model file is missing or its size differs from the inventory")
    if verify_hash:
        digest = hashlib.sha256()
        with artifact.open("rb") as f:
            while block := f.read(8 * 1024 * 1024):
                digest.update(block)
        if digest.hexdigest() != model.get("sha256"):
            raise RuntimeError("configured model SHA256 differs from the verified inventory")
    active_ids = api_models(api_base)
    expected = model.get("model_id")
    if not expected or expected not in active_ids:
        raise RuntimeError(f"requested model is not the active loopback model; observed={active_ids}")
    runtime_path = model.get("runtime_model_path", expected)
    argv = active_llama_server(runtime_path)
    if not argv:
        raise RuntimeError("the expected model is visible via API but its active llama-server process cannot be verified")
    expected_flags = {"--ctx-size": str(config["provider"]["context"]), "--threads": str(config["provider"]["threads"]), "--threads-batch": str(config["provider"]["threads"]), "--n-gpu-layers": "0"}
    for flag, value in expected_flags.items():
        if flag not in argv or argv[argv.index(flag) + 1] != value:
            raise RuntimeError(f"active llama-server does not match fixed benchmark setting {flag}={value}")
    return model, active_ids


def normalize_run(model_key: str, task: str, ledger: dict[str, Any], trial_root: Path | None = None) -> list[dict[str, Any]]:
    rows = []
    trials = ledger if isinstance(ledger, list) else ledger.get("trials", [])
    for trial in trials:
        trial_id = str(trial.get("trial", ""))
        trace_path = trial_root / trial_id / "local-agent-trace.jsonl" if trial_root else None
        tool_calls: list[dict[str, Any]] = []
        trace_text = ""
        if trace_path and trace_path.is_file():
            trace_text = trace_path.read_text()
            for line in trace_text.splitlines():
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if event.get("event") == "tool_call":
                    tool_calls.append(event)
        stderr_path = trial_root / trial_id / "stderr.log" if trial_root else None
        if stderr_path and stderr_path.is_file():
            trace_text += stderr_path.read_text(errors="replace")
        tool_results = [event.get("result") or {} for event in tool_calls]
        result = trial.get("result") or {}
        metrics = trial.get("metrics") or result.get("metrics") or {}
        error_text = (json.dumps(result, ensure_ascii=False) + trace_text).lower()
        status = trial.get("agent_status", result.get("status", "UNKNOWN"))
        xsim_pass = int(trial.get("xsim_pass_markers", 0) or 0)
        hls_csim_pass = int(trial.get("hls_csim_pass_markers", 0) or 0)
        hls_csynth_pass = int(trial.get("hls_csynth_pass_markers", 0) or 0)
        if status == "COMPLETED":
            if (task in {"T1", "T2"} and xsim_pass >= 1 and int(trial.get("model_patch_count", 0) or 0) >= 1) or (task == "T3" and hls_csim_pass >= 1 and hls_csynth_pass >= 1 and int(trial.get("model_patch_count", 0) or 0) >= 1):
                status = "PASS"
            else:
                status = "FAIL"
        rows.append({
            "model_key": model_key,
            "task": task,
            "arm": "ross" if trial_id.startswith("B") else "non_ross",
            "trial": trial_id,
            "status": status,
            "elapsed_seconds": trial.get("elapsed_seconds"),
            "model_load_time_seconds": None,
            "model_load_time_status": "NOT_INSTRUMENTED; server must be already active",
            "prompt_tokens": trial.get("observed_prompt_tokens", trial.get("prompt_tokens")),
            "completion_tokens": trial.get("observed_completion_tokens", trial.get("completion_tokens")),
            "model_request_seconds": metrics.get("model_request_seconds"),
            "ross_calls": trial.get("ross_call_count"),
            "ross_call_seconds": trial.get("ross_call_seconds"),
            "tool_call_count": len(tool_calls),
            "tool_call_successes": sum(item.get("ok") is True for item in tool_results),
            "tool_call_success_rate": (sum(item.get("ok") is True for item in tool_results) / len(tool_calls)) if tool_calls else None,
            "context_overflow": "context_length_exceeded" in error_text or "context length" in error_text,
            "tool_attempts": trial.get("xsim_attempts", trial.get("hls_attempts")),
            "xsim_pass_markers": xsim_pass,
            "hls_csim_pass_markers": trial.get("hls_csim_pass_markers"),
            "hls_csynth_pass_markers": trial.get("hls_csynth_pass_markers"),
            "peak_rss_mib": trial.get("process_peak_rss_mib"),
            "minimum_memavailable_mib": trial.get("host_min_memavailable_mib"),
            "maximum_swap_mib": trial.get("host_max_swap_used_mib"),
            "cpu_machine_percent": trial.get("process_cpu_machine_percent"),
            "source_sha256_before": trial.get("seed_source_sha256"),
            "source_sha256_after": trial.get("final_source_sha256"),
            "resource_guard_stop": trial.get("resource_guard_stop"),
            "raw": trial,
        })
    return rows


def summarize_trials(rows: list[dict[str, Any]]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    for arm in ("non_ross", "ross"):
        selected = [r for r in rows if r["arm"] == arm]
        passed = [r for r in selected if r["status"] == "PASS"]
        elapsed = [r["elapsed_seconds"] for r in passed if isinstance(r.get("elapsed_seconds"), (int, float))]
        prompt = [r["prompt_tokens"] for r in selected if isinstance(r.get("prompt_tokens"), (int, float))]
        completion = [r["completion_tokens"] for r in selected if isinstance(r.get("completion_tokens"), (int, float))]
        tool_calls = [r for r in selected if r.get("tool_call_count") is not None]
        total_tools = sum(int(r["tool_call_count"]) for r in tool_calls)
        successful_tools = sum(int(r["tool_call_successes"]) for r in tool_calls)
        rss_values = [r["peak_rss_mib"] for r in selected if isinstance(r.get("peak_rss_mib"), (int, float))]
        available_values = [r["minimum_memavailable_mib"] for r in selected if isinstance(r.get("minimum_memavailable_mib"), (int, float))]
        swap_values = [r["maximum_swap_mib"] for r in selected if isinstance(r.get("maximum_swap_mib"), (int, float))]
        cpu_values = [r["cpu_machine_percent"] for r in selected if isinstance(r.get("cpu_machine_percent"), (int, float))]
        summary[arm] = {
            "trials": len(selected), "passes": len(passed),
            "success_rate": len(passed) / len(selected) if selected else None,
            "successful_time_mean_seconds": statistics.mean(elapsed) if elapsed else None,
            "successful_time_median_seconds": statistics.median(elapsed) if elapsed else None,
            "successful_time_p90_seconds": max(elapsed) if len(elapsed) >= 3 else None,
            "successful_time_sample_count": len(elapsed),
            "mean_prompt_tokens": statistics.mean(prompt) if prompt else None,
            "mean_completion_tokens": statistics.mean(completion) if completion else None,
            "tool_calls": total_tools,
            "tool_call_success_rate": successful_tools / total_tools if total_tools else None,
            "context_overflow_trials": sum(bool(r.get("context_overflow")) for r in selected),
            "mean_peak_rss_mib": statistics.mean(rss_values) if rss_values else None,
            "minimum_memavailable_mib": min(available_values) if available_values else None,
            "maximum_swap_mib": max(swap_values) if swap_values else None,
            "mean_cpu_machine_percent": statistics.mean(cpu_values) if cpu_values else None,
            "failures_included": len(selected) - len(passed),
        }
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    inv = sub.add_parser("inventory", help="show candidate presence and saved hashes")
    inv.add_argument("--full-hash", action="store_true", help="read and hash each configured model file sequentially")
    pre = sub.add_parser("preflight", help="verify that a model is already active at a loopback server")
    pre.add_argument("model_key")
    pre.add_argument("--api-base", default=None)
    run = sub.add_parser("run", help="run all three M13 A/B cohorts against the already-active model")
    run.add_argument("model_key")
    run.add_argument("--api-base", default=None)
    run.add_argument("--ross-url", default=os.environ.get("AI370_ROSS_DOCSEARCH_URL"))
    args = parser.parse_args()
    config = load_config()
    api_base = getattr(args, "api_base", None) or config["provider"]["api_base"]

    if args.command == "inventory":
        print(json.dumps({"generated_local": datetime.now().astimezone().isoformat(timespec="seconds"), "rows": inventory(config, args.full_hash)}, indent=2, ensure_ascii=False))
        return 0

    try:
        model, active = verify_active_model(config, args.model_key, api_base)
    except Exception as exc:
        print(json.dumps({"status": "BLOCKED", "model_key": args.model_key, "reason": str(exc)}, ensure_ascii=False))
        return 3
    preflight = {"status": "PASS", "model_key": model["key"], "model_id": model["model_id"], "runtime_model_path": model.get("runtime_model_path"), "active_models": active, "api_base": api_base, "model_switching": "not performed"}
    if args.command == "preflight":
        print(json.dumps(preflight, ensure_ascii=False))
        return 0
    if not args.ross_url:
        print(json.dumps({"status": "BLOCKED", "reason": "Ross A/B requires explicit local AMD Knowledge Base endpoint", "preflight": preflight}, ensure_ascii=False))
        return 3

    run_id = datetime.now().astimezone().strftime("%Y%m%dT%H%M%S%z")
    out = ROOT / "output/LOCAL_MODEL_LAB" / run_id / model["key"]
    out.mkdir(parents=True, exist_ok=False)
    summary: dict[str, Any] = {"status": "RUNNING", "run_id": run_id, "preflight": preflight, "model": model, "out": str(out), "tasks": {}}
    for task in TASK_KEYS:
        # Recheck identity before each cohort; never start or switch a model server.
        verify_active_model(config, args.model_key, api_base, verify_hash=False)
        task_cfg = config["tasks"][task]
        env = os.environ.copy()
        env.update({"AI370_LOCAL_MODEL": model["model_id"], "AI370_LOCAL_BASE_URL": api_base, "AI370_ROSS_DOCSEARCH_URL": args.ross_url, "AI370_ROSS_AB_OUT": str(out / task), "AI370_ROSS_AB_SEQUENCE": ",".join(config["fixed_sequence"]), "AI370_MODEL_LAB_REQUEST_TIMEOUT": str(task_cfg["request_timeout_seconds"]), "AI370_MODEL_LAB_TOTAL_TIMEOUT": str(task_cfg["total_timeout_seconds"]), "AI370_MODEL_LAB_COMPLETION_CAP": str(task_cfg["max_completion_tokens"]), "AI370_MODEL_LAB_TOOL_CALL_CAP": str(task_cfg["tool_call_cap"])})
        start = time.monotonic()
        proc = subprocess.run([sys.executable, str(ROOT / task_cfg["runner"])], cwd=ROOT, env=env, check=False)
        elapsed = time.monotonic() - start
        ledger_path = out / task / "trials.json"
        ledger = json.loads(ledger_path.read_text()) if ledger_path.is_file() else {"trials": []}
        rows = normalize_run(model["key"], task, ledger, out / task)
        summary["tasks"][task] = {"runner_exit_code": proc.returncode, "elapsed_seconds": round(elapsed, 3), "trials": rows, "scoreboard": summarize_trials(rows)}
        summary["status"] = "PARTIAL" if proc.returncode else summary["status"]
        (out / "result.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n")
        if proc.returncode:
            break
    if all(len(summary["tasks"].get(task, {}).get("trials", [])) == 6 for task in TASK_KEYS):
        summary["status"] = "COMPLETE"
    (out / "result.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"status": summary["status"], "out": str(out), "completed_tasks": list(summary["tasks"])}, ensure_ascii=False))
    return 0 if summary["status"] == "COMPLETE" else 1


if __name__ == "__main__":
    raise SystemExit(main())
