#!/usr/bin/env python3
"""Run one legacy LocalAgent trial under the quality-validation resource gates.

This adapter never owns or stops the model server. It supervises only the trial
controller and the LocalAgent process whose workspace is the requested output.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import signal
import shutil
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# A few pages being written to swap during model-server startup is not, by
# itself, proof of memory pressure. Swap activity is recorded at every level,
# but it must have independent pressure evidence before it can stop a formal
# sample.
PAGE_SIZE = os.sysconf("SC_PAGE_SIZE")
MEM_GUARD_KIB = 6 * 1024**2
LOW_MEMORY_GRACE_SECONDS = 20
PSI_HARD_LIMIT = 20.0
PSI_GRACE_SECONDS = 10
SWAP_GROWTH_WARNING_KIB = 64 * 1024
SWAPOUT_CORROBORATION_BYTES = 16 * 1024**2
SWAPIN_CORROBORATION_BYTES = 1 * 1024**2


def verify_quality_protocol(workspace: Path, config: dict, model: str) -> None:
    protocol_path = workspace.parent / "protocol.json"
    protocol = json.loads(protocol_path.read_text())
    if (protocol.get("task"), protocol.get("variant"), protocol.get("model")) != (config.get("task"), config.get("variant"), model):
        raise SystemExit("controller config/model does not match the frozen workspace protocol")
    for relative, expected in protocol.get("public_inputs_sha256", {}).items():
        path = workspace / relative
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise SystemExit(f"frozen public input changed before model start: {relative}")
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=workspace, capture_output=True, text=True, check=True).stdout.strip()
    if head != protocol.get("workspace_git_head"):
        raise SystemExit("workspace Git baseline does not match the frozen protocol")
    dirty = subprocess.run(["git", "status", "--porcelain"], cwd=workspace, capture_output=True, text=True, check=True).stdout
    if dirty.strip():
        raise SystemExit("workspace is dirty before the model sample starts")
    manifest_path = ROOT / protocol["corpus_manifest"]
    if hashlib.sha256(manifest_path.read_bytes()).hexdigest() != protocol.get("corpus_manifest_sha256"):
        raise SystemExit("frozen corpus manifest changed after workspace preparation")
    for relative, expected in protocol.get("runner_sha256", {}).items():
        if hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() != expected:
            raise SystemExit(f"frozen harness changed after workspace preparation: {relative}")
    verify_live_quality_protocol(workspace, protocol)


def verify_live_quality_protocol(workspace: Path, protocol: dict) -> None:
    """Detect immutable input/harness drift while a model owns the sample."""
    for relative, expected in protocol.get("runner_sha256", {}).items():
        if hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() != expected:
            raise RuntimeError(f"HARNESS_INTEGRITY_GUARD: runner changed: {relative}")
    manifest_path=ROOT/protocol["corpus_manifest"]
    if hashlib.sha256(manifest_path.read_bytes()).hexdigest()!=protocol.get("corpus_manifest_sha256"):
        raise RuntimeError("HARNESS_INTEGRITY_GUARD: corpus manifest changed")
    manifest=json.loads(manifest_path.read_text())
    corpus_root=manifest_path.parent
    for relative,expected in manifest.get("files",{}).items():
        path=corpus_root/relative
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=expected:
            raise RuntimeError(f"HARNESS_INTEGRITY_GUARD: corpus asset changed: {relative}")
    editable=set(protocol.get("editable_paths",[]))
    for relative,expected in protocol.get("public_inputs_sha256",{}).items():
        if relative in editable: continue
        path=workspace/relative
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=expected:
            raise RuntimeError(f"HARNESS_INTEGRITY_GUARD: protected workspace input changed: {relative}")
    status=subprocess.run(["git","status","--porcelain","--untracked-files=all"],cwd=workspace,capture_output=True,text=True,check=True).stdout
    for line in status.splitlines():
        relative=line[3:].strip()
        if relative.startswith(("runs/",".quality-hidden/")): continue
        if relative not in editable:
            raise RuntimeError(f"HARNESS_INTEGRITY_GUARD: workspace write outside allowlist: {relative}")


def meminfo() -> dict[str, int]:
    return {line.split(":")[0]: int(line.split()[1]) for line in Path("/proc/meminfo").read_text().splitlines() if line.endswith(" kB")}


def vmstat() -> dict[str, int]:
    wanted = {"pswpin", "pswpout"}
    return {line.split()[0]: int(line.split()[1]) for line in Path("/proc/vmstat").read_text().splitlines() if line.split()[0] in wanted}


def psi_full_avg10() -> float:
    for line in Path("/proc/pressure/memory").read_text().splitlines():
        if line.startswith("full "):
            return float(next(item.split("=")[1] for item in line.split() if item.startswith("avg10=")))
    raise RuntimeError("memory PSI full line unavailable")


def terminate_trial(controller: subprocess.Popen, workspace: str) -> None:
    # LocalAgent deliberately runs validation in its own process group. Match
    # only the process that names this exact disposable workspace.
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        try:
            cmd = (entry / "cmdline").read_bytes().replace(b"\0", b" ").decode(errors="ignore")
            if ("local_agent.py --workspace" in cmd or "quality_local_agent.py --workspace" in cmd) and workspace in cmd:
                pid = int(entry.name)
                try:
                    os.killpg(pid, signal.SIGINT)
                except ProcessLookupError:
                    pass
        except OSError:
            continue
    if controller.poll() is None:
        try:
            os.killpg(controller.pid, signal.SIGINT)
        except ProcessLookupError:
            pass
        try:
            controller.wait(timeout=15)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(controller.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            controller.wait()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True, help="Immutable controller JSON for the selected task sample")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--model-path", type=Path, required=True)
    parser.add_argument("--server-pid", type=int, required=True)
    parser.add_argument("--base-url", default="http://127.0.0.1:18082/v1")
    parser.add_argument("--ross-docsearch-url")
    parser.add_argument("--stop-file", type=Path)
    parser.add_argument("--timeout", type=int, default=2700)
    parser.add_argument("--quality-agent", action="store_true", help="Run the frozen quality-corpus LocalAgent rather than the legacy M13 calibration wrapper")
    args = parser.parse_args()
    config = args.config.resolve(strict=True)
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    run_config = json.loads(config.read_text())
    workspace = str(Path(run_config["workspace"]).resolve()) if args.quality_agent else str((output / ("A" + str(run_config["rep"]) ) / "workspace").resolve())
    model_path = args.model_path.resolve(strict=True)
    try:
        server_cmd = Path(f"/proc/{args.server_pid}/cmdline").read_bytes().replace(b"\0", b" ").decode(errors="ignore")
    except OSError as exc:
        raise SystemExit(f"model server PID is not live: {exc}")
    if model_path.name not in server_cmd:
        raise SystemExit("model server PID does not name the requested model path")
    with urllib.request.urlopen(args.base_url.rsplit("/v1", 1)[0] + "/health", timeout=5) as response:
        if response.status != 200:
            raise SystemExit("model server health check failed")

    baseline = meminfo()
    base_swap = baseline["SwapTotal"] - baseline["SwapFree"]
    base_vm = vmstat()
    start_wall = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    started = time.monotonic()
    out_window: list[tuple[float, int]] = []
    samples: list[dict] = []
    resource_warnings: list[dict[str, object]] = []
    psi_high_since: float | None = None
    low_memory_since: float | None = None
    last_server_audit=0.0
    server_health_failures=0
    integrity_detail: str | None = None
    reason: str | None = None
    env = os.environ.copy()
    env.update({
        "AI370_LOCAL_MODEL": args.model,
        "AI370_LOCAL_BASE_URL": args.base_url,
        "AI370_MODEL_LAB_SERVER_PID": str(args.server_pid),
        "AI370_MODEL_LAB_MODEL_PATH": str(model_path),
        "AI370_ROSS_AB_OUT": str(output),
        "AI370_MODEL_LAB_REQUEST_TIMEOUT": "600",
        "AI370_MODEL_LAB_TOTAL_TIMEOUT": "2400",
        "AI370_MODEL_LAB_COMPLETION_CAP": "8192",
        "AI370_MODEL_LAB_TOOL_CALL_CAP": "14",
    })
    if args.quality_agent:
        if run_config.get("task") not in {f"T{i}" for i in range(1,9)} or run_config.get("variant") not in {"V1", "V2", "V3"}:
            raise SystemExit("controller config is not a supported frozen quality task")
        verify_quality_protocol(Path(workspace), run_config, args.model)
        editable = run_config.get("editable_paths") or []
        if not editable:
            editable = ["sim/tb_axi_regs.sv"] if run_config["task"] == "T3" else ["rtl/axi_regs.sv"]
        command = [
            sys.executable, str(ROOT / "scripts/quality_local_agent.py"),
            "--workspace", workspace, "--task", run_config["task"], "--variant", run_config["variant"],
            "--model", args.model, "--base-url", args.base_url,
            *[part for path in editable for part in ("--editable-path", path)],
            "--trace", str(output / "quality-agent-trace.jsonl"),
            "--timeout", "600", "--total-timeout", "2400",
            "--max-completion-tokens", "8192", "--max-calls", "14",
        ]
        if args.ross_docsearch_url:
            command += ["--ross-docsearch-url", args.ross_docsearch_url]
    else:
        command = [sys.executable, str(ROOT / "scripts/run_model_endurance.py"), "--trial", str(config)]
    with (output / "guarded.stdout.log").open("w") as stdout, (output / "guarded.stderr.log").open("w") as stderr:
        child = subprocess.Popen(command, cwd=ROOT, env=env, stdout=stdout, stderr=stderr, start_new_session=True)
        try:
            while child.poll() is None:
                now = time.monotonic()
                current = meminfo()
                vm = vmstat()
                swap_used = current["SwapTotal"] - current["SwapFree"]
                psi = psi_full_avg10()
                samples.append({
                    "elapsed_seconds": round(now - started, 2),
                    "memavailable_kib": current["MemAvailable"],
                    "swap_used_kib": swap_used,
                    "pswpin_pages_delta": vm["pswpin"] - base_vm["pswpin"],
                    "pswpout_pages_delta": vm["pswpout"] - base_vm["pswpout"],
                    "psi_full_avg10": psi,
                })
                mem_guard = max(MEM_GUARD_KIB, current["MemTotal"] // 8)
                swap_growth_kib = swap_used - base_swap
                swapin_bytes = (vm["pswpin"] - base_vm["pswpin"]) * PAGE_SIZE
                if current["MemAvailable"] < mem_guard:
                    low_memory_since = low_memory_since or now
                    if now - low_memory_since >= LOW_MEMORY_GRACE_SECONDS:
                        reason = "SUSTAINED_MEMAVAILABLE_GUARD"
                else:
                    low_memory_since = None
                out_window.append((now, vm["pswpout"]))
                out_window = [item for item in out_window if now - item[0] <= 60]
                window_swapout_bytes = (out_window[-1][1] - out_window[0][1]) * PAGE_SIZE if len(out_window) > 1 else 0
                # Preserve evidence for small swap-out activity, but only
                # stop if it is corroborated by swap-in, PSI, or low memory.
                if window_swapout_bytes >= 1024**2:
                    warning = {
                        "kind": "SWAPOUT_ACTIVITY",
                        "elapsed_seconds": round(now - started, 2),
                        "window_swapout_bytes": window_swapout_bytes,
                        "swapin_bytes": swapin_bytes,
                        "memavailable_kib": current["MemAvailable"],
                        "psi_full_avg10": psi,
                    }
                    if not resource_warnings or resource_warnings[-1] != warning:
                        resource_warnings.append(warning)
                if (swap_growth_kib > SWAP_GROWTH_WARNING_KIB and
                        not any(item.get("kind") == "LARGE_SWAP_GROWTH_UNCORROBORATED" for item in resource_warnings)):
                    resource_warnings.append({
                        "kind": "LARGE_SWAP_GROWTH_UNCORROBORATED",
                        "elapsed_seconds": round(now - started, 2),
                        "swap_growth_kib": swap_growth_kib,
                        "swapin_bytes": swapin_bytes,
                        "memavailable_kib": current["MemAvailable"],
                        "psi_full_avg10": psi,
                    })
                if (window_swapout_bytes >= SWAPOUT_CORROBORATION_BYTES and
                        (swapin_bytes >= SWAPIN_CORROBORATION_BYTES or psi >= PSI_HARD_LIMIT or
                         current["MemAvailable"] < mem_guard)):
                    reason = "CORROBORATED_SWAP_PRESSURE_GUARD"
                if psi >= PSI_HARD_LIMIT:
                    psi_high_since = psi_high_since or now
                    if now - psi_high_since >= PSI_GRACE_SECONDS:
                        reason = "MEMORY_PSI_GUARD"
                else:
                    psi_high_since = None
                if shutil.disk_usage(ROOT).free < 20 * 1024**3:
                    reason = "DISK_GUARD"
                if now - started > args.timeout:
                    reason = "SAMPLE_TIMEOUT"
                if args.stop_file and args.stop_file.exists():
                    reason = "USER_STOP"
                if now-last_server_audit>=5:
                    last_server_audit=now
                    try:
                        live_cmd=Path(f"/proc/{args.server_pid}/cmdline").read_bytes().replace(b"\0",b" ").decode(errors="ignore")
                        if model_path.name not in live_cmd:
                            reason="MODEL_SERVER_CRASH"
                        else:
                            with urllib.request.urlopen(args.base_url.rsplit("/v1",1)[0]+"/health",timeout=3) as response:
                                if response.status!=200: server_health_failures+=1
                                else: server_health_failures=0
                            if server_health_failures>=2: reason="MODEL_SERVER_HEALTH_LOST"
                    except (OSError,urllib.error.URLError,TimeoutError):
                        server_health_failures+=1
                        if server_health_failures>=2: reason="MODEL_SERVER_HEALTH_LOST"
                if args.quality_agent and now - getattr(main,"last_integrity_check",0) >= 5:
                    try:
                        protocol=json.loads((Path(workspace).parent/"protocol.json").read_text())
                        verify_live_quality_protocol(Path(workspace),protocol)
                    except Exception as exc:
                        integrity_detail=f"{type(exc).__name__}: {exc}"
                        reason="HARNESS_INTEGRITY_GUARD"
                    main.last_integrity_check=now
                if len(samples) == 1 or now - getattr(main, "last_audit", 0) >= 15:
                    audit = subprocess.run(
                        ["journalctl", "-k", "--since", start_wall, "--no-pager", "-o", "short-iso"],
                        capture_output=True, text=True, timeout=12,
                    )
                    main.last_audit = now
                    if audit.returncode != 0:
                        reason = "KERNEL_AUDIT_UNREADABLE"
                    elif any(token in audit.stdout.lower() for token in (
                        "gpu reset", "amdgpu: page fault", "device lost", "out of memory: killed process", "oom-kill", "ring timeout",
                    )):
                        reason = "GPU_KERNEL_OOM_FAULT"
                if reason:
                    terminate_trial(child, workspace)
                    break
                time.sleep(1)
        except BaseException:
            terminate_trial(child, workspace)
            raise
        returncode = child.wait()
    result = {
        "model": args.model,
        "config": str(config),
        "returncode": returncode,
        "guard_reason": reason,
        "guard_detail": integrity_detail,
        "baseline": {"memavailable_kib": baseline["MemAvailable"], "swap_used_kib": base_swap},
        "resource_samples": samples,
        "resource_warnings": resource_warnings,
        "resource_guard_policy": {
            "low_memory_grace_seconds": LOW_MEMORY_GRACE_SECONDS,
            "psi_hard_limit": PSI_HARD_LIMIT,
            "psi_grace_seconds": PSI_GRACE_SECONDS,
            "swap_growth_warning_kib": SWAP_GROWTH_WARNING_KIB,
            "swapout_requires_corroboration_bytes": SWAPOUT_CORROBORATION_BYTES,
            "swapin_corroboration_bytes": SWAPIN_CORROBORATION_BYTES,
        },
        "formal_quality_sample": bool(args.quality_agent),
        "classification": "FORMAL_QUALITY_SAMPLE" if args.quality_agent else "LEGACY_CALIBRATION_ONLY",
    }
    if args.quality_agent:
        try:
            lines=(output/"guarded.stdout.log").read_text(errors="replace").splitlines()
            result["agent_result"]=json.loads(lines[-1]) if lines else None
        except (json.JSONDecodeError,OSError):
            result["agent_result"]=None
        result["sample_status"]=("BLOCKED" if reason and reason not in {"SAMPLE_TIMEOUT"} else
                                 "PARTIAL" if reason=="SAMPLE_TIMEOUT" else
                                 "PASS" if returncode==0 else "FAIL")
    (output / "guarded-result.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"returncode": returncode, "guard_reason": reason, "sample_count": len(samples)}))
    return 0 if returncode == 0 and reason is None else 1


if __name__ == "__main__":
    raise SystemExit(main())
