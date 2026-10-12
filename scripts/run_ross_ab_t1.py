#!/usr/bin/env python3
"""Run the isolated T1 Local Qwen with/without AMD Ross A/B sequence."""

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

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs/M13/evidence/2026-10-12/local-qwen-standalone-agent-rtl/source"
OUT = Path(os.environ.get("AI370_ROSS_AB_OUT", str(ROOT / "output/M13/ross-ab-benchmark-2026-10-12/T1-timeout600")))
MODEL = "Qwen3.8-27B-UD-Q4_K_XL"
ROSS_URL = os.environ.get("AI370_ROSS_DOCSEARCH_URL", "")
FULL_SEQUENCE = [("A", 1), ("B", 1), ("B", 2), ("A", 2), ("A", 3), ("B", 3)]
SEQUENCE = [tuple((part[0], int(part[1:]))) for part in os.environ.get("AI370_ROSS_AB_SEQUENCE", "A1,B1,B2,A2,A3,B3").split(",")]


def proc_snapshot(agent_pid: int) -> tuple[int, int, int, int]:
    """Return agent+Qwen RSS, CPU ticks, host available KiB, swap-used KiB."""
    table: dict[int, tuple[int, int, int]] = {}
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        pid = int(entry.name)
        try:
            raw = (entry / "stat").read_text()
            tail = raw[raw.rfind(")") + 2:].split()
            ppid = int(tail[1])
            ticks = int(tail[11]) + int(tail[12])
            rss = int(tail[21]) * os.sysconf("SC_PAGE_SIZE") // 1024
            cmd = (entry / "cmdline").read_bytes().replace(b"\0", b" ").decode(errors="ignore")
            table[pid] = (ppid, ticks, rss)
            if "Qwen3.8-27B-UD-Q4_K_XL.gguf" in cmd:
                table[pid] = (-1, ticks, rss)
        except (OSError, ValueError, IndexError):
            continue
    descendants = {agent_pid}
    changed = True
    while changed:
        changed = False
        for pid, (ppid, _, _) in table.items():
            if ppid in descendants and pid not in descendants:
                descendants.add(pid)
                changed = True
    rss = ticks = 0
    for pid in descendants:
        if pid in table:
            _, cpu_ticks, mem = table[pid]
            ticks += cpu_ticks
            rss += mem
    for pid, (ppid, cpu_ticks, mem) in table.items():
        if ppid == -1:
            ticks += cpu_ticks
            rss += mem
    meminfo = {}
    for line in Path("/proc/meminfo").read_text().splitlines():
        key, _, value = line.partition(":")
        if value.strip().endswith("kB"):
            meminfo[key] = int(value.split()[0])
    return rss, ticks, meminfo.get("MemAvailable", 0), meminfo.get("SwapTotal", 0) - meminfo.get("SwapFree", 0)


def seed(label: str, rep: int) -> Path:
    work = OUT / f"{label}{rep}/workspace"
    work.mkdir(parents=True)
    (work / "rtl").mkdir()
    (work / "sim").mkdir()
    (work / "runs").mkdir()
    shutil.copy2(SOURCE / "seeded_rtl.v", work / "rtl/local_model_axi_lite.v")
    shutil.copy2(SOURCE / "testbench.sv", work / "sim/tb_local_model_axi_lite.sv")
    shutil.copy2(SOURCE / "run_validation.sh", work / "run_validation.sh")
    shutil.copy2(SOURCE / "task_spec.md", work / "TASK_SPEC.md")
    task = ("""Read TASK_SPEC.md and the RTL. This is one independent T1 trial. First read task/spec and DUT, then call run_xsim on unchanged baseline, diagnose its real output, submit the smallest RTL-only repair using apply_patch (or after a rejected diff, your exact apply_replacement), and rerun XSim. Do not change testbench or runner. Require the actual terminal PASS marker. Do not claim success otherwise.\n""")
    if label == "B":
        task += "Use both AMD Ross tools before changing source: read vivado-simulate-rtl Skill and its xsim.md reference with ross_skill_read, then query ross_doc_search for the applicable Vivado 2026.1 XSim batch simulation guidance. Use the returned Ross material to inform your repair. Ross calls and results will be recorded.\n"
    else:
        task += "This is the non-Ross control: use only the provided source, task specification and fixed tools. Do not use or consult AMD Ross Skills or Knowledge Base.\n"
    (work / "TASK_INSTRUCTIONS.md").write_text(task)
    return work


def run_trial(label: str, rep: int) -> dict:
    work = seed(label, rep)
    root = OUT / f"{label}{rep}"
    trace = root / "local-agent-trace.jsonl"
    stdout = root / "stdout.json"
    stderr = root / "stderr.log"
    result_path = root / "result.json"
    task = (work / "TASK_INSTRUCTIONS.md").read_text() + "\nUser engineering request: " + (work / "TASK_SPEC.md").read_text()
    command = [sys.executable, str(ROOT / "scripts/local_agent.py"), "--workspace", str(work), "--task", task,
               "--timeout", "600", "--total-timeout", "1800", "--max-calls", "12", "--xsim",
               "--editable-path", "rtl/local_model_axi_lite.v", "--trace", str(trace)]
    if label == "B":
        if not ROSS_URL:
            raise RuntimeError("AI370_ROSS_DOCSEARCH_URL is required for Ross condition B")
        command += ["--ross-docsearch-url", ROSS_URL]
    before_hash = hashlib.sha256((work / "rtl/local_model_axi_lite.v").read_bytes()).hexdigest()
    start_local = datetime.now().astimezone().isoformat(timespec="seconds")
    start = time.monotonic()
    rss_peak = first_ticks = last_ticks = 0
    min_available = None
    max_swap = 0
    base_swap: int | None = None
    mem_total = 0
    resource_stop = None
    run_env = os.environ.copy()
    if label == "A":
        run_env.pop("AI370_ROSS_DOCSEARCH_URL", None)
    with stdout.open("wb") as out_stream, stderr.open("wb") as err_stream:
        proc = subprocess.Popen(command, cwd=ROOT, stdout=out_stream, stderr=err_stream, env=run_env, start_new_session=True)
        try:
            while proc.poll() is None:
                rss, ticks, available, swap = proc_snapshot(proc.pid)
                rss_peak = max(rss_peak, rss)
                first_ticks = ticks if first_ticks == 0 else first_ticks
                last_ticks = ticks
                min_available = available if min_available is None else min(min_available, available)
                max_swap = max(max_swap, swap)
                if base_swap is None:
                    base_swap = swap
                if not mem_total:
                    for line in Path("/proc/meminfo").read_text().splitlines():
                        if line.startswith("MemTotal:"):
                            mem_total = int(line.split()[1])
                            break
                floor_kib = max(6 * 1024 * 1024, int(mem_total * 0.125))
                if available < floor_kib:
                    resource_stop = f"MemAvailable below guard floor ({available} KiB < {floor_kib} KiB)"
                elif swap > (base_swap or 0) + 2 * 1024 * 1024:
                    resource_stop = f"Swap use increased by more than 2 GiB ({swap - base_swap} KiB)"
                if resource_stop:
                    os.killpg(proc.pid, 2)
                    break
                time.sleep(0.5)
        finally:
            code = proc.wait()
    elapsed = time.monotonic() - start
    raw = stdout.read_bytes().decode(errors="replace").strip()
    try:
        agent_result = json.loads(raw.splitlines()[-1])
    except (json.JSONDecodeError, IndexError):
        agent_result = {"status": "FAIL", "error": "missing agent JSON result", "stdout_tail": raw[-2000:]}
    after_hash = hashlib.sha256((work / "rtl/local_model_axi_lite.v").read_bytes()).hexdigest()
    events = [json.loads(line) for line in trace.read_text().splitlines()] if trace.exists() else []
    usage_events = [x.get("response", {}).get("usage", {}) for x in events if x.get("event") == "model_response"]
    prompt_tokens = sum(int(x.get("prompt_tokens") or 0) for x in usage_events)
    completion_tokens = sum(int(x.get("completion_tokens") or 0) for x in usage_events)
    ross_calls = [x for x in events if x.get("event") == "tool_call" and x.get("name") in {"ross_doc_search", "ross_skill_read"}]
    validations = [x.get("result", {}) for x in events if x.get("event") == "tool_call" and x.get("name") == "run_xsim"]
    summary = {
        "trial": f"{label}{rep}", "condition": "ross" if label == "B" else "non_ross", "sequence_position": SEQUENCE.index((label, rep)) + 1,
        "started_local": start_local,
        "elapsed_seconds": round(elapsed, 3), "exit_code": code,
        "agent_status": "RESOURCE_GUARD_STOP" if resource_stop else agent_result.get("status", "FAIL"),
        "resource_guard_stop": resource_stop, "resource_guard": {"min_memavailable_mib": max(6144, round(mem_total * 0.125 / 1024, 1)), "max_swap_increase_mib": 2048},
        "xsim_attempts": len(validations), "xsim_pass_markers": sum(bool(v.get("terminal_pass_marker")) for v in validations),
        "model_patch_count": agent_result.get("patches", 0), "ross_call_count": len(ross_calls),
        "observed_prompt_tokens": prompt_tokens, "observed_completion_tokens": completion_tokens,
        "ross_call_names": [x.get("name") for x in ross_calls], "metrics": agent_result.get("metrics", {}),
        "process_peak_rss_mib": round(rss_peak / 1024, 1), "host_min_memavailable_mib": round((min_available or 0) / 1024, 1),
        "host_max_swap_used_mib": round(max_swap / 1024, 1),
        "process_cpu_core_equivalent_percent": round(max(0, last_ticks - first_ticks) / os.sysconf("SC_CLK_TCK") / max(elapsed, 0.001) * 100, 1),
        "process_cpu_machine_percent": round(max(0, last_ticks - first_ticks) / os.sysconf("SC_CLK_TCK") / max(elapsed, 0.001) / max(os.cpu_count() or 1, 1) * 100, 1),
        "seed_rtl_sha256": before_hash, "final_rtl_sha256": after_hash, "result": agent_result,
    }
    result_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n")
    return summary


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    summaries = []
    for label, rep in SEQUENCE:
        print(f"START {label}{rep}", flush=True)
        summary = run_trial(label, rep)
        summaries.append(summary)
        print(json.dumps({k: summary[k] for k in ("trial", "elapsed_seconds", "agent_status", "xsim_attempts", "ross_call_count", "metrics", "process_peak_rss_mib", "host_min_memavailable_mib", "host_max_swap_used_mib")}, ensure_ascii=False), flush=True)
        (OUT / "trials.json").write_text(json.dumps(summaries, indent=2, ensure_ascii=False) + "\n")
    return 0 if len(summaries) == 6 else 1


if __name__ == "__main__":
    raise SystemExit(main())
