#!/usr/bin/env python3
"""Compare available roster models using measured CPU/GPU configurations.

Reuses the M13 tasks, Local Agent, sandbox and Ross tools. Runtime model loads
are temporary; the original Lemonade Qwen configuration is restored in finally.
No downloads, persistent model settings, hardware programming or stack changes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import signal
import subprocess
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import run_local_model_lab as lab

ROOT = lab.ROOT
PORT = 18081
FAULT = re.compile(r"amdgpu.*(?:page fault|GPU reset|ring.*timeout|device lost)|TTM.*(?:corrupt|error)|soft lockup|Out of memory: Killed process|oom-kill", re.I)


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def memory() -> dict[str, int]:
    rows = {line.split(":")[0]: int(line.split()[1]) for line in Path("/proc/meminfo").read_text().splitlines() if line.endswith(" kB")}
    return rows


def stop(proc: subprocess.Popen | None) -> None:
    if proc is None or proc.poll() is not None:
        return
    table = {}
    for entry in Path('/proc').iterdir():
        if entry.name.isdigit():
            try:
                stat = (entry / 'stat').read_text()
                table[int(entry.name)] = int(stat[stat.rfind(')') + 2:].split()[1])
            except (OSError, ValueError, IndexError):
                pass
    descendants = {proc.pid}
    while True:
        expanded = descendants | {pid for pid, ppid in table.items() if ppid in descendants}
        if expanded == descendants:
            break
        descendants = expanded
    for pid in descendants:
        try:
            if os.getpgid(pid) == pid:
                os.killpg(pid, signal.SIGTERM)
            else:
                os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
    try:
        proc.wait(timeout=15)
    except subprocess.TimeoutExpired:
        for pid in descendants:
            try:
                if os.getpgid(pid) == pid:
                    os.killpg(pid, signal.SIGKILL)
                else:
                    os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        proc.wait()


def fault_audit(since: str) -> dict:
    p = subprocess.run(["journalctl", "-k", "--since", since, "--no-pager", "-o", "short-iso"], capture_output=True, text=True, timeout=15)
    return {"read_exit": p.returncode, "faults": [line for line in p.stdout.splitlines() if FAULT.search(line)], "error": p.stderr[:500]}


def guarded(command: list[str], stdout: Path, stderr: Path, *, timeout: float, env: dict | None = None, cwd: Path = ROOT) -> dict:
    started = time.monotonic()
    baseline = memory()
    min_available = baseline["MemAvailable"]
    max_swap = baseline["SwapTotal"] - baseline["SwapFree"]
    reason = None
    started_utc = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
    last_audit = time.monotonic()
    with stdout.open("w") as out, stderr.open("w") as err:
        proc = subprocess.Popen(command, cwd=cwd, env=env, stdout=out, stderr=err, start_new_session=True)
        try:
            while proc.poll() is None:
                current = memory()
                min_available = min(min_available, current["MemAvailable"])
                max_swap = max(max_swap, current["SwapTotal"] - current["SwapFree"])
                if current["MemAvailable"] < max(6 * 1024**2, current["MemTotal"] // 8):
                    reason = "RESOURCE_GUARD: insufficient host available memory"
                elif max_swap - (baseline["SwapTotal"] - baseline["SwapFree"]) > 2 * 1024**2:
                    reason = "RESOURCE_GUARD: swap growth exceeded 2 GiB"
                elif time.monotonic() - started > timeout:
                    reason = "TIMEOUT"
                if time.monotonic() - last_audit > 10:
                    audit = fault_audit(started_utc)
                    last_audit = time.monotonic()
                    if audit['faults']:
                        reason = "KERNEL_FAULT: " + audit['faults'][0]
                if reason:
                    stop(proc)
                    break
                time.sleep(0.5)
            code = proc.wait()
        finally:
            stop(proc)
    return {"command": command, "exit_code": code, "elapsed_seconds": round(time.monotonic() - started, 3), "guard": reason, "minimum_memavailable_mib": min_available / 1024, "maximum_swap_used_mib": max_swap / 1024}


def calibration(model: dict, base: Path, threads: int, inherited: Path | None = None) -> dict:
    path = ROOT / lab.load_config()["model_root"] / model["relative_path"]
    if inherited is not None and inherited.is_file():
        previous = json.loads(inherited.read_text())
        valid = [x for x in previous if x.get('status') == 'PASS' and not x.get('probe_only') and not x.get('kernel_audit', {}).get('faults')]
        if valid:
            for row in previous:
                row['inherited_calibration_file'] = str(inherited)
            write_json(base / 'calibration.json', previous)
            print(json.dumps({'stage': 'reuse_verified_calibration', 'model': model['key'], 'source': str(inherited)}), flush=True)
            return min(valid, key=lambda x: x['representative_request_seconds'])
    results = []
    failed_backends = set()
    for backend, layers, probe in [("cpu", 0, False), ("hip", 16, True), ("hip", 99, False), ("vulkan", 16, True), ("vulkan", 99, False)]:
        if backend in failed_backends:
            continue
        directory = base / f"{backend}-{layers}"
        directory.mkdir(parents=True)
        started_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        device = {"cpu": "none", "hip": "ROCm0", "vulkan": "Vulkan0"}[backend]
        command = [str(ROOT / f"output/M6/build-{backend}/bin/llama-bench"), "-m", str(path), "--offline", "-t", str(threads), "-ngl", str(layers), "-dev", device, "-p", "32" if probe else "128", "-n", "4" if probe else "32", "-r", "1" if probe else "3", "-o", "json", "-v"]
        result = guarded(command, directory / "bench.json", directory / "bench.log", timeout=900)
        audit = fault_audit(started_utc)
        result.update(backend=backend, gpu_layers=layers, device=device, probe_only=probe, kernel_audit=audit)
        try:
            metrics = json.loads((directory / "bench.json").read_text())
            pp = next(x["avg_ts"] for x in metrics if x.get("n_prompt") == (32 if probe else 128))
            tg = next(x["avg_ts"] for x in metrics if x.get("n_gen") == (4 if probe else 32))
            result.update(prompt_tokens_per_second=pp, generation_tokens_per_second=tg, representative_request_seconds=512 / pp + 128 / tg)
        except (ValueError, KeyError, StopIteration, TypeError):
            result["parse_error"] = "benchmark did not produce complete throughput JSON"
        log = (directory / "bench.log").read_text(errors="replace")
        result["offload_evidence"] = [line for line in log.splitlines() if "offload" in line.lower() or "buffer size" in line.lower()]
        if backend != 'cpu' and not re.search(r'offloaded [1-9]\d*/\d+ layers', log):
            result['parse_error'] = 'actual accelerator offload was not established in the log'
        result["status"] = "PASS" if result["exit_code"] == 0 and not result["guard"] and "parse_error" not in result and not audit["faults"] and audit["read_exit"] == 0 else "FAIL"
        results.append(result)
        write_json(base / "calibration.json", results)
        print(json.dumps({"stage": "backend_calibration", "model": model["key"], **{k: result.get(k) for k in ["backend", "gpu_layers", "status", "prompt_tokens_per_second", "generation_tokens_per_second"]}}), flush=True)
        if audit["faults"] or re.search(r"device lost|GPU reset|illegal memory access", log, re.I):
            raise RuntimeError("GPU/kernel fault detected; stopped GPU/engineering test expansion")
        if probe and result["status"] != "PASS":
            # Do not increase offload after a failed partial-offload probe.
            failed_backends.add(backend)
    measured = [x for x in results if not x["probe_only"] and x["status"] == "PASS"]
    if not measured:
        raise RuntimeError("no usable measured backend")
    return min(measured, key=lambda x: x["representative_request_seconds"])


def launch(model: dict, selected: dict, base: Path, threads: int, context: int) -> tuple[subprocess.Popen, dict]:
    path = ROOT / lab.load_config()["model_root"] / model["relative_path"]
    command = [str(ROOT / f"output/M6/build-{selected['backend']}/bin/llama-server"), "-m", str(path), "--alias", model["model_id"], "--host", "127.0.0.1", "--port", str(PORT), "--ctx-size", str(context), "--threads", str(threads), "--threads-batch", str(threads), "--n-gpu-layers", str(selected["gpu_layers"]), "--device", selected["device"], "--parallel", "1", "--jinja", "--reasoning", "off", "--metrics"]
    started = time.monotonic()
    stream = (base / "server.log").open("w")
    proc = subprocess.Popen(command, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT, start_new_session=True)
    stream.close()
    try:
        while time.monotonic() - started < 600:
            if proc.poll() is not None:
                raise RuntimeError(f"model server exited {proc.returncode}; see server.log")
            mem = memory()
            if mem['MemAvailable'] < max(6 * 1024**2, mem['MemTotal'] // 8):
                raise RuntimeError('model load crossed host available-memory safety floor')
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/health", timeout=2) as response:
                    if response.status == 200:
                        state = {"status": "READY", "pid": proc.pid, "command": command, "load_seconds": round(time.monotonic() - started, 3), "model_sha256": model["sha256"], "memory": memory()}
                        write_json(base / "runtime.json", state)
                        return proc, state
            except Exception:
                pass
            time.sleep(1)
        raise RuntimeError("model server load timed out")
    except BaseException:
        stop(proc)
        raise


def drm_activity(pid: int) -> dict:
    clients = {}
    for entry in Path(f'/proc/{pid}/fdinfo').glob('*'):
        try:
            data = entry.read_text()
            if 'drm-driver:' not in data:
                continue
            fields = {line.partition(':')[0]: line.partition(':')[2].strip() for line in data.splitlines() if line.startswith(('drm-', 'amd-'))}
            clients[fields.get('drm-client-id', entry.name)] = fields
        except OSError:
            continue
    return {'timestamp_utc': datetime.now(timezone.utc).isoformat(), 'clients': list(clients.values())}


def post_synthesis(workspace: Path) -> dict:
    directory = workspace / "post-agent-synthesis"
    directory.mkdir(exist_ok=True)
    rtl = sorted((workspace / "rtl").glob("*.v"))
    tcl = directory / "validate.tcl"
    tcl.write_text("read_verilog -sv {" + " ".join(str(p) for p in rtl) + "}\nsynth_design -top local_model_axi_lite -part xc7s100fgga676-2\ncreate_clock -period 10.000 [get_ports aclk]\nreport_utilization -file utilization.rpt\nreport_timing_summary -file timing.rpt\nputs PRACTICAL_SYNTHESIS_PASS\nexit\n")
    command = ["/home/shen/tools/Xilinx/2026.1/2026.1/Vivado/bin/vivado", "-mode", "batch", "-notrace", "-source", str(tcl), "-log", "vivado.log", "-journal", "vivado.jou"]
    result = guarded(command, directory / "stdout.log", directory / "stderr.log", timeout=600, cwd=directory)
    result["status"] = "PASS" if result["exit_code"] == 0 and "PRACTICAL_SYNTHESIS_PASS" in (directory / "stdout.log").read_text() else "FAIL"
    result["scope"] = "post-agent synthesis of model-authored final RTL; no implementation/timing-closure claim"
    write_json(directory / "result.json", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ross-url", default="http://172.18.0.4:8080/mcp/doc-search")
    parser.add_argument("--calibration-only", action="store_true")
    parser.add_argument('--reuse-calibration', type=Path, help='Reuse matching artifact/thread calibration after a harness-only correction')
    args = parser.parse_args()
    config = lab.load_config()
    run_id = datetime.now().astimezone().strftime("%Y%m%dT%H%M%S%z")
    out = ROOT / "output/LOCAL_MODEL_LAB_PRACTICAL" / run_id
    out.mkdir(parents=True)
    threads, context = len(os.sched_getaffinity(0)), 16384
    result = {"status": "RUNNING", "run_id": run_id, "scope": "practical model suitability with measured backend selection", "threads": threads, "context": context, "inventory": lab.inventory(config, full_hash=True), "models": {}}
    result['harness_sha256'] = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in [ROOT / 'scripts/local_agent.py', ROOT / 'scripts/run_local_model_lab_practical.py', ROOT / 'scripts/run_local_model_lab.py', ROOT / 'scripts/run_ross_ab_t1.py', ROOT / 'scripts/run_ross_ab_t2.py', ROOT / 'scripts/run_ross_ab_hls.py', ROOT / 'config/local_model_lab.json']}
    write_json(out / "result.json", result)
    inherited_result = json.loads((args.reuse_calibration / 'result.json').read_text()) if args.reuse_calibration else None
    if inherited_result and inherited_result.get('threads') != threads:
        raise RuntimeError('cannot reuse calibration with a different CPU thread count')
    _, _ = lab.verify_active_model(config, "qwen38", config["provider"]["api_base"], verify_hash=False)
    original = lab.active_llama_server(lab.model_for(config, "qwen38")["runtime_model_path"])
    write_json(out / "original-runtime.json", original)
    server = None
    formal_unloaded = False
    def interrupted(signum, frame):
        raise InterruptedError(f"interrupted by signal {signum}")
    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    try:
        subprocess.run(["lemonade", "unload", "Qwen3.8-27B-UD-Q4_K_XL"], check=True, timeout=60)
        formal_unloaded = True
        if lab.active_llama_server(lab.model_for(config, "qwen38")["runtime_model_path"]):
            raise RuntimeError("formal model is still resident; refusing concurrent large models")
        # Start the previously untested model family first; keep missing roster slots.
        for model in sorted(config["models"], key=lambda m: m['key'] != 'gemma4_31b'):
            if not model.get("relative_path"):
                result["models"][model["key"]] = {"status": model["status"], "reason": "no configured local artifact; no download attempted"}
                continue
            inventory = next(x for x in result["inventory"] if x["key"] == model["key"])
            if not inventory.get("sha_matches") or inventory["observed_bytes"] != model["bytes"]:
                result["models"][model["key"]] = {"status": "BLOCKED", "reason": "artifact integrity mismatch"}
                continue
            base = out / model["key"]
            base.mkdir()
            inherited_file = None
            if inherited_result:
                earlier = next((r for r in inherited_result.get('inventory', []) if r.get('key') == model['key']), {})
                if earlier.get('observed_sha256') == model['sha256'] and earlier.get('observed_bytes') == model['bytes']:
                    inherited_file = args.reuse_calibration / model['key'] / 'backend-calibration/calibration.json'
            selected = calibration(model, base / "backend-calibration", threads, inherited_file)
            item = {"status": "CALIBRATED", "selected_backend": selected, "tasks": {}}
            result["models"][model["key"]] = item
            write_json(out / "result.json", result)
            if args.calibration_only:
                continue
            candidates = json.loads((base / 'backend-calibration/calibration.json').read_text())
            candidates = sorted([x for x in candidates if x['status'] == 'PASS' and not x['probe_only']], key=lambda x: x['representative_request_seconds'])
            item['runtime_load_attempts'] = []
            for candidate in candidates:
                runtime_dir = base / f"runtime-{candidate['backend']}-{candidate['gpu_layers']}"
                runtime_dir.mkdir()
                started_utc = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
                try:
                    server, runtime = launch(model, candidate, runtime_dir, threads, context)
                    selected = candidate
                    item['selected_backend'] = candidate
                    item['runtime_load_attempts'].append({'backend': candidate['backend'], 'status': 'READY', 'log': str(runtime_dir / 'server.log')})
                    break
                except RuntimeError as exc:
                    item['runtime_load_attempts'].append({'backend': candidate['backend'], 'status': 'FAIL', 'error': str(exc), 'log': str(runtime_dir / 'server.log')})
                    if fault_audit(started_utc)['faults']:
                        raise RuntimeError('GPU/kernel fault during runtime load; stopping tests')
                    write_json(out / 'result.json', result)
            if server is None:
                raise RuntimeError('no measured configuration could load the engineering context safely')
            item["runtime"] = runtime
            item['drm_activity_before'] = drm_activity(server.pid)
            for task in lab.TASK_KEYS:
                task_cfg = config["tasks"][task]
                env = os.environ.copy()
                env.update({"AI370_LOCAL_MODEL": model["model_id"], "AI370_LOCAL_BASE_URL": f"http://127.0.0.1:{PORT}/v1", "AI370_MODEL_LAB_SERVER_PID": str(server.pid), "AI370_MODEL_LAB_MODEL_PATH": model["runtime_model_path"], "AI370_ROSS_DOCSEARCH_URL": args.ross_url, "AI370_ROSS_AB_OUT": str(base / task), "AI370_ROSS_AB_SEQUENCE": ",".join(config["fixed_sequence"]), "AI370_MODEL_LAB_REQUEST_TIMEOUT": str(task_cfg["request_timeout_seconds"]), "AI370_MODEL_LAB_TOTAL_TIMEOUT": str(task_cfg["total_timeout_seconds"]), "AI370_MODEL_LAB_COMPLETION_CAP": "2048", "AI370_MODEL_LAB_TOOL_CALL_CAP": str(task_cfg["tool_call_cap"]), "AI370_ROSS_CONTEXT_CHARS": "1800", "AI370_ROSS_MCP_CHARS": "1200"})
                print(json.dumps({"stage": "engineering", "model": model["key"], "task": task, "backend": selected["backend"]}), flush=True)
                task_run = guarded(["python3", str(ROOT / task_cfg["runner"])], base / f'{task}-stdout.log', base / f'{task}-stderr.log', timeout=6 * task_cfg['total_timeout_seconds'] + 180, env=env)
                code = task_run['exit_code']
                if task_run.get('guard'):
                    raise RuntimeError(task_run['guard'])
                ledger_file = base / task / "trials.json"
                ledger = json.loads(ledger_file.read_text()) if ledger_file.exists() else []
                rows = lab.normalize_run(model["key"], task, ledger, base / task)
                if task in {"T1", "T2"}:
                    for row in rows:
                        if row["status"] == "PASS":
                            row["vivado_synthesis"] = post_synthesis(base / task / row["trial"] / "workspace")
                            if row["vivado_synthesis"]["status"] != "PASS":
                                row["status"] = "FAIL_SYNTHESIS"
                item["tasks"][task] = {"runner_exit_code": code, "trials": rows, "scoreboard": lab.summarize_trials(rows)}
                item['tasks'][task]['drm_activity_after'] = drm_activity(server.pid)
                write_json(out / "result.json", result)
            stop(server)
            server = None
            item["status"] = "EXECUTED" if all(len(x['trials']) == 6 and x['runner_exit_code'] == 0 for x in item['tasks'].values()) else "PARTIAL"
        result["status"] = "PARTIAL" if any(x["status"] in {"NOT_INSTALLED", "WAITING_FOR_MODEL_SELECTION", "BLOCKED", "PARTIAL"} for x in result["models"].values()) else "EXECUTED"
    except BaseException as exc:
        result.update(status="BLOCKED", error=f"{type(exc).__name__}: {exc}")
        print(result["error"], flush=True)
    finally:
        stop(server)
        if formal_unloaded:
            print("RESTORING_FORMAL_QWEN", flush=True)
            try:
                restored = subprocess.run(["lemonade", "load", "Qwen3.8-27B-UD-Q4_K_XL", "--ctx-size", "8192", "--llamacpp", "cpu", "--llamacpp-args", "--n-gpu-layers 0 --parallel 1 --reasoning off --spec-type draft-mtp --threads 24 --threads-batch 24"], capture_output=True, text=True, timeout=600)
                (out / "restore.log").write_text(restored.stdout + restored.stderr)
                if restored.returncode:
                    raise RuntimeError(f'Lemonade restore command exited {restored.returncode}')
                lab.verify_active_model(config, "qwen38", config["provider"]["api_base"], verify_hash=False)
                result["formal_model_restoration"] = "PASS"
            except Exception as exc:
                result["formal_model_restoration"] = f"FAIL: {exc}"
                result["status"] = "BLOCKED"
        result['completed_local'] = datetime.now().astimezone().isoformat(timespec='seconds')
        write_json(out / "result.json", result)
        print(json.dumps({"status": result["status"], "evidence": str(out), "formal_model_restoration": result.get("formal_model_restoration")}), flush=True)
    return 0 if result["status"] in {"PARTIAL", "EXECUTED"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
