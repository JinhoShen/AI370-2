#!/usr/bin/env python3
"""Run independent non-Ross/Ross Qwen HLS repair trials with hard bounds."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

from run_ross_ab_t1 import proc_snapshot

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "projects/FPGA/Ross_HLS_Skill_Smoke"
OUT = Path(os.environ.get("AI370_ROSS_AB_OUT", str(ROOT / "output/M13/ross-ab-benchmark-2026-10-12/T3-HLS-timeout600")))
ROSS_URL = os.environ.get("AI370_ROSS_DOCSEARCH_URL", "")
SEQUENCE = [tuple((part[0], int(part[1:]))) for part in os.environ.get("AI370_ROSS_AB_SEQUENCE", "A1,B1,B2,A2,A3,B3").split(",")]
MODEL = os.environ.get("AI370_LOCAL_MODEL", "Qwen3.8-27B-UD-Q4_K_XL")
REQUEST_TIMEOUT = int(os.environ.get("AI370_MODEL_LAB_REQUEST_TIMEOUT", "600"))
TOTAL_TIMEOUT = int(os.environ.get("AI370_MODEL_LAB_TOTAL_TIMEOUT", "1800"))
COMPLETION_CAP = int(os.environ.get("AI370_MODEL_LAB_COMPLETION_CAP", "512"))
TOOL_CALL_CAP = int(os.environ.get("AI370_MODEL_LAB_TOOL_CALL_CAP", "12"))
TRIAL_HARD_TIMEOUT = TOTAL_TIMEOUT


def seed(label: str, rep: int) -> Path:
    work = OUT / f"{label}{rep}/workspace"
    (work / "src").mkdir(parents=True)
    (work / "sim").mkdir()
    (work / "runs").mkdir()
    shutil.copy2(SOURCE / "hls_config.cfg", work / "hls_config.cfg")
    shutil.copy2(SOURCE / "src/testbench.cpp", work / "src/testbench.cpp")
    good = (SOURCE / "src/invert32.cpp").read_text()
    bug = good.replace("return ~input;", "return ~input ^ 1u;")
    if bug == good:
        raise RuntimeError("Could not seed the known deterministic HLS C-sim fault")
    (work / "src/invert32.cpp").write_text(bug)
    (work / "TASK_SPEC.md").write_text(
        """# T3 isolated Vitis HLS engineering task\n\n"
        "The top function is `invert32(uint32_t input)`. Required behavior is the bitwise complement of all 32 input bits. "
        "The fixed testbench has four vectors and must remain unchanged. The source has a seeded defect.\n\n"
        "Read this specification, source, testbench and HLS config. Run `run_hls` unchanged, diagnose its actual C-simulation failure, "
        "make the smallest source-only correction using `apply_patch` or an exact model-authored `apply_replacement`, then rerun `run_hls`. "
        "The fixed tool performs C simulation and, only after all four vectors pass, C synthesis for xc7s100fgga676-2. "
        "Do not edit the testbench/config/runner, invoke shell, or access hardware. Require both fixed PASS markers.\n"""
    )
    instructions = "Read TASK_SPEC.md, then read hls_config.cfg, src/invert32.cpp and src/testbench.cpp. Run the unchanged HLS baseline before patching. Diagnose actual C simulation output; fix only src/invert32.cpp and rerun until fixed C simulation and C synthesis both pass. Do not edit testbench/config."
    if label == "B":
        instructions += " Before HLS execution or source edits, use ross_skill_read for the installed hls-run-flow skill (reference empty string because it has no reference file) and ross_doc_search for Vitis HLS 2026.1 C simulation/C synthesis guidance. Use both actual Ross results."
    else:
        instructions += " This is the non-Ross control. Do not call or consult any Ross tool."
    (work / "TASK_INSTRUCTIONS.md").write_text(instructions)
    return work


def run_trial(label: str, rep: int) -> dict:
    work = seed(label, rep)
    root = OUT / f"{label}{rep}"
    trace, stdout, stderr = root / "local-agent-trace.jsonl", root / "stdout.json", root / "stderr.log"
    task = (work / "TASK_INSTRUCTIONS.md").read_text() + "\nEngineering specification:\n" + (work / "TASK_SPEC.md").read_text()
    command = [sys.executable, str(ROOT / "scripts/local_agent.py"), "--workspace", str(work), "--task", task,
               "--timeout", str(REQUEST_TIMEOUT), "--total-timeout", str(TOTAL_TIMEOUT), "--max-completion-tokens", str(COMPLETION_CAP), "--max-calls", str(TOOL_CALL_CAP), "--hls",
               "--editable-path", "src/invert32.cpp", "--trace", str(trace)]
    if label == "B":
        if not ROSS_URL:
            raise RuntimeError("AI370_ROSS_DOCSEARCH_URL is required for treatment group B")
        command += ["--ross-docsearch-url", ROSS_URL]
        if "AI370_ROSS_CONTEXT_CHARS" in os.environ:
            command += ["--ross-context-chars", os.environ["AI370_ROSS_CONTEXT_CHARS"], "--ross-mcp-chars", os.environ["AI370_ROSS_MCP_CHARS"]]
    before_hash = hashlib.sha256((work / "src/invert32.cpp").read_bytes()).hexdigest()
    start_local = datetime.now().astimezone().isoformat(timespec="seconds")
    started = time.monotonic()
    agent_pid = 0
    peak_rss = first_ticks = last_ticks = 0
    min_available = None
    max_swap = base_swap = mem_total = 0
    resource_stop = hard_timeout = None
    env = os.environ.copy()
    if label == "A":
        env.pop("AI370_ROSS_DOCSEARCH_URL", None)
    with stdout.open("wb") as out, stderr.open("wb") as err:
        proc = subprocess.Popen(command, cwd=ROOT, stdout=out, stderr=err, env=env, start_new_session=True)
        agent_pid = proc.pid
        while proc.poll() is None:
            now_elapsed = time.monotonic() - started
            rss, ticks, available, swap = proc_snapshot(proc.pid)
            peak_rss = max(peak_rss, rss)
            first_ticks = ticks if first_ticks == 0 else first_ticks
            last_ticks = ticks
            min_available = available if min_available is None else min(min_available, available)
            max_swap = max(max_swap, swap)
            base_swap = swap if base_swap == 0 else base_swap
            if not mem_total:
                for line in Path("/proc/meminfo").read_text().splitlines():
                    if line.startswith("MemTotal:"):
                        mem_total = int(line.split()[1])
                        break
            if available < max(6 * 1024 * 1024, int(mem_total * 0.125)):
                resource_stop = "MemAvailable crossed the documented resource guard"
            elif swap > base_swap + 2 * 1024 * 1024:
                resource_stop = "Swap grew by more than 2 GiB during this trial"
            elif now_elapsed > TRIAL_HARD_TIMEOUT:
                hard_timeout = f"Trial exceeded hard wall-clock limit {TRIAL_HARD_TIMEOUT}s"
            if resource_stop or hard_timeout:
                try:
                    os.killpg(proc.pid, 2)
                    proc.wait(timeout=10)
                except Exception:
                    os.killpg(proc.pid, 9)
                    proc.wait()
                break
            time.sleep(0.5)
        code = proc.wait()
    elapsed = time.monotonic() - started
    raw = stdout.read_text(errors="replace").strip()
    try:
        result = json.loads(raw.splitlines()[-1])
    except (json.JSONDecodeError, IndexError):
        result = {"status": "FAIL", "error": "missing agent JSON result"}
    events = [json.loads(line) for line in trace.read_text().splitlines()] if trace.exists() else []
    usages = [x.get("response", {}).get("usage", {}) for x in events if x.get("event") == "model_response"]
    ross_calls = [x for x in events if x.get("event") == "tool_call" and x.get("name") in {"ross_doc_search", "ross_skill_read"}]
    validations = [x.get("result", {}) for x in events if x.get("event") == "tool_call" and x.get("name") == "run_hls"]
    after_hash = hashlib.sha256((work / "src/invert32.cpp").read_bytes()).hexdigest()
    return {
        "trial": f"{label}{rep}", "condition": "ross" if label == "B" else "non_ross",
        "sequence_position": SEQUENCE.index((label, rep)) + 1, "started_local": start_local,
        "elapsed_seconds": round(elapsed, 3), "exit_code": code,
        "agent_status": "RESOURCE_GUARD_STOP" if resource_stop else "HARD_TIMEOUT" if hard_timeout else result.get("status", "FAIL"),
        "resource_guard_stop": resource_stop, "hard_timeout": hard_timeout,
        "model_patch_count": result.get("patches", 0), "ross_call_count": len(ross_calls),
        "ross_call_names": [x.get("name") for x in ross_calls], "hls_attempts": len(validations),
        "hls_csim_pass_markers": sum(bool(x.get("csim_pass")) for x in validations),
        "hls_csynth_pass_markers": sum(bool(x.get("csynth_pass")) for x in validations),
        "observed_prompt_tokens": sum(int(x.get("prompt_tokens") or 0) for x in usages),
        "observed_completion_tokens": sum(int(x.get("completion_tokens") or 0) for x in usages),
        "process_peak_rss_mib": round(peak_rss / 1024, 1),
        "host_min_memavailable_mib": round((min_available or 0) / 1024, 1),
        "host_max_swap_used_mib": round(max_swap / 1024, 1),
        "seed_source_sha256": before_hash, "final_source_sha256": after_hash, "result": result,
        "trial_wall_timeout_seconds": TRIAL_HARD_TIMEOUT,
    }


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for label, rep in SEQUENCE:
        print(f"START {label}{rep}", flush=True)
        row = run_trial(label, rep)
        rows.append(row)
        print(json.dumps({k: row[k] for k in ("trial", "elapsed_seconds", "agent_status", "hls_attempts", "ross_call_count", "process_peak_rss_mib", "host_min_memavailable_mib", "host_max_swap_used_mib")}, ensure_ascii=False), flush=True)
        (OUT / "trials.json").write_text(json.dumps(rows, indent=2, ensure_ascii=False) + "\n")
    return 0 if len(rows) == 6 else 1


if __name__ == "__main__":
    raise SystemExit(main())
