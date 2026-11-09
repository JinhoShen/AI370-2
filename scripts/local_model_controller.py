#!/usr/bin/env python3
"""Long-running supervisor for guarded local-model quality evaluation.

The controller is intentionally conservative: it records machine health by
default and launches a quality runner only after an explicit, durable arm
request.  It never changes model settings, corpus files, scoring rules, or
the production Agent configuration.
"""
from __future__ import annotations

import argparse
import fcntl
import json
import os
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
QUALITY_BASE = ROOT / "output" / "QUALITY_MODEL_VALIDATION"
BASE = ROOT / "output" / "LOCAL_MODEL_CONTROLLER"
STATE_PATH = BASE / "status.json"
COMMAND_PATH = BASE / "command.json"
EVENTS_PATH = BASE / "events.jsonl"
TELEMETRY_PATH = BASE / "telemetry.jsonl"
LOCK_PATH = BASE / "controller.lock"
RUNNER = ROOT / "scripts" / "run_quality_pilot.py"
FIXTURE_RUNNER = ROOT / "scripts" / "run_quality_remediation_fixtures.py"
PLAN_RUNNER = ROOT / "scripts" / "freeze_quality_v2_v3_plan.py"
REMEDIATION_REPORT = ROOT / "docs" / "LOCAL_MODEL_LAB" / "PILOT_V1_REMEDIATION.md"
POLL_SECONDS = 30
AUTO_CONTINUE_V2_V3 = True
CONTROLLER_DIAGNOSTICS = BASE / "diagnostics"


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")
    temp.replace(path)


def append_jsonl(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as stream:
        stream.write(json.dumps(value, ensure_ascii=False) + "\n")


def read_json(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def meminfo() -> dict[str, int]:
    result: dict[str, int] = {}
    for line in Path("/proc/meminfo").read_text().splitlines():
        key, rest = line.split(":", 1)
        fields = rest.split()
        if fields and fields[-1] == "kB":
            result[key] = int(fields[0])
    return result


def vmstat() -> dict[str, int]:
    wanted = {"pswpin", "pswpout", "pgmajfault"}
    return {
        fields[0]: int(fields[1])
        for fields in (line.split() for line in Path("/proc/vmstat").read_text().splitlines())
        if len(fields) == 2 and fields[0] in wanted
    }


def memory_psi() -> dict[str, dict[str, float]]:
    result: dict[str, dict[str, float]] = {}
    for line in Path("/proc/pressure/memory").read_text().splitlines():
        fields = line.split()
        result[fields[0]] = {key: float(value) for key, value in (part.split("=") for part in fields[1:])}
    return result


def swapped_processes() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for proc in Path("/proc").iterdir():
        if not proc.name.isdigit():
            continue
        try:
            fields = {}
            for line in (proc / "status").read_text().splitlines():
                if line.startswith(("Name:", "VmSwap:")):
                    key, value = line.split(":", 1)
                    fields[key] = value.split()[0]
            swap = int(fields.get("VmSwap", "0"))
            if swap:
                rows.append({"pid": int(proc.name), "name": fields.get("Name", "?"), "vmswap_kib": swap})
        except (FileNotFoundError, ProcessLookupError, PermissionError, ValueError):
            continue
    return sorted(rows, key=lambda row: row["vmswap_kib"], reverse=True)[:10]


def health_snapshot() -> dict[str, Any]:
    memory = meminfo()
    return {
        "timestamp_utc": now(),
        "memavailable_kib": memory.get("MemAvailable"),
        "memtotal_kib": memory.get("MemTotal"),
        "swaptotal_kib": memory.get("SwapTotal"),
        "swapfree_kib": memory.get("SwapFree"),
        "swapused_kib": memory.get("SwapTotal", 0) - memory.get("SwapFree", 0),
        "vmstat_pages": vmstat(),
        "memory_psi": memory_psi(),
        "top_vmswap_processes": swapped_processes(),
    }


def runner_status() -> dict[str, Any] | None:
    return read_json(QUALITY_BASE / "status.json")


def latest_v2_v3_plan() -> Path | None:
    plans = sorted((BASE / "plans").glob("*/v2-v3-plan.json"))
    return plans[-1] if plans else None


def latest_guarded_result() -> Path | None:
    """Return the newest formal guarded result without altering its evidence."""
    results = list(QUALITY_BASE.glob("*/cycle-*/samples/**/guarded/guarded-result.json"))
    return max(results, key=lambda path: path.stat().st_mtime) if results else None


def recorded_controller_guard(pid: int | None) -> str | None:
    """Recover a controller-originated stop after a service restart."""
    if pid is None:
        return None
    try:
        for line in reversed(EVENTS_PATH.read_text().splitlines()):
            event = json.loads(line)
            if event.get("event") == "CHILD_SAFETY_STOP" and event.get("pid") == pid:
                return str(event.get("reason") or "CONTROLLER_SAFETY_STOP")
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None
    return None


def diagnose_safety_stop(state: dict[str, Any]) -> Path | None:
    """Create a read-only, evidence-bounded diagnosis for a stopped sample."""
    result_path = latest_guarded_result()
    if result_path is None:
        return None
    result = read_json(result_path)
    if result is None:
        return None
    samples = result.get("resource_samples", [])
    if not isinstance(samples, list):
        samples = []
    page_size = os.sysconf("SC_PAGE_SIZE")
    swapin_pages = max((int(row.get("pswpin_pages_delta", 0)) for row in samples), default=0)
    swapout_pages = max((int(row.get("pswpout_pages_delta", 0)) for row in samples), default=0)
    max_psi = max((float(row.get("psi_full_avg10", 0.0)) for row in samples), default=0.0)
    min_available = min((int(row.get("memavailable_kib", 0)) for row in samples), default=None)
    diagnosis = {
        "schema_version": 1,
        "created_utc": now(),
        "kind": "READ_ONLY_SAFETY_STOP_DIAGNOSIS",
        "guarded_result": str(result_path.relative_to(ROOT)),
        "trigger": result.get("guard_reason"),
        "confirmed": {
            "swapin_bytes_observed": swapin_pages * page_size,
            "swapout_bytes_observed": swapout_pages * page_size,
            "max_psi_full_avg10": max_psi,
            "min_memavailable_kib": min_available,
            "resource_sample_count": len(samples),
        },
        "assessment": (
            "INSUFFICIENT_EVIDENCE_OF_MEMORY_PRESSURE"
            if swapin_pages == 0 and max_psi < 20.0 and (min_available or 0) >= 6 * 1024**2
            else "SAFETY_STOP_EVIDENCE_REQUIRES_REVIEW"
        ),
        "not_confirmed": [
            "The source process of global swap-in or swap-out activity is not identified by memory.swap.current or /proc/vmstat alone.",
            "A global swap counter does not by itself establish an OOM, GPU fault, or sustained memory-pressure event.",
        ],
        "administrator_diagnostics_if_needed": [
            "Inspect privileged kernel and cgroup memory-event records for the exact model-server cgroup.",
            "Correlate system-wide swap tracepoints with process/cgroup attribution during a controlled future run.",
        ],
        "next_action": "Do not retry automatically. Review this diagnosis and the frozen policy before starting a new run.",
    }
    directory = CONTROLLER_DIAGNOSTICS / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = directory / "safety-stop-diagnosis.json"
    atomic_json(path, diagnosis)
    state["last_safety_diagnosis"] = str(path.relative_to(ROOT))
    emit(state, "SAFETY_DIAGNOSIS_WRITTEN", path=str(path.relative_to(ROOT)), trigger=result.get("guard_reason"))
    return path


def state_template() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "controller": "LOCAL_MODEL_CONTROLLER",
        "status": "MONITORING",
        "started_utc": now(),
        "last_command_id": None,
        "runner": None,
        "last_health": None,
        "notes": "Monitoring only. A durable arm request is required before a runner can start.",
    }


def emit(state: dict[str, Any], event: str, **fields: Any) -> None:
    payload = {"timestamp_utc": now(), "event": event, **fields}
    append_jsonl(EVENTS_PATH, payload)
    state["last_event"] = payload


def command_error(command: Any) -> str | None:
    if not isinstance(command, dict):
        return "COMMAND_NOT_AN_OBJECT"
    if command.get("schema_version") != 1:
        return "UNSUPPORTED_COMMAND_SCHEMA"
    if not isinstance(command.get("request_id"), str) or not command["request_id"].strip():
        return "REQUEST_ID_REQUIRED"
    if command.get("action") not in {"ARM_PILOT", "RUN_REMEDIATION_FIXTURES", "RESUME_V2_V3", "RUN_T7_SUPPLEMENT", "STOP"}:
        return "UNSUPPORTED_ACTION"
    if command.get("action") in {"ARM_PILOT", "RUN_REMEDIATION_FIXTURES", "RESUME_V2_V3", "RUN_T7_SUPPLEMENT"} and command.get("approved") is not True:
        return "EXPLICIT_APPROVAL_REQUIRED"
    return None


def may_start_pilot() -> tuple[bool, str]:
    status = runner_status()
    if status is None:
        return True, "NO_PREVIOUS_QUALITY_STATE"
    if status.get("status") == "PILOT_COMPLETE":
        return False, "PILOT_ALREADY_COMPLETE_REVIEW_REQUIRED"
    if status.get("status") in {"RUNNING", "SAFETY_STOP", "PREFLIGHT_BLOCKED"}:
        return False, f"QUALITY_STATE_{status.get('status')}"
    return False, "UNRECOGNIZED_QUALITY_STATE"


def launch_pilot(state: dict[str, Any], request_id: str) -> subprocess.Popen[str] | None:
    allowed, reason = may_start_pilot()
    if not allowed:
        state["status"] = "WAITING_FOR_REVIEW"
        emit(state, "RUNNER_NOT_STARTED", request_id=request_id, reason=reason)
        return None
    command = [sys.executable, str(RUNNER), "--pilot-only"]
    log_path = BASE / f"runner-{request_id}.log"
    with log_path.open("w") as log:
        proc = subprocess.Popen(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, start_new_session=True, text=True)
    state["status"] = "RUNNER_ACTIVE"
    state["runner"] = {"request_id": request_id, "pid": proc.pid, "command": command, "log": str(log_path.relative_to(ROOT)), "started_utc": now()}
    emit(state, "RUNNER_STARTED", request_id=request_id, pid=proc.pid, command=command)
    return proc


def launch_remediation_fixtures(state: dict[str, Any], request_id: str) -> subprocess.Popen[str] | None:
    quality = runner_status()
    if not REMEDIATION_REPORT.is_file() or not quality or quality.get("status") != "PILOT_COMPLETE":
        emit(state, "FIXTURES_NOT_STARTED", request_id=request_id, reason="PILOT_REMEDIATION_NOT_READY")
        return None
    command = [sys.executable, str(FIXTURE_RUNNER)]
    log_path = BASE / f"remediation-fixtures-{request_id}.log"
    with log_path.open("w") as log:
        proc = subprocess.Popen(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, start_new_session=True, text=True)
    state["status"] = "REMEDIATION_FIXTURES_ACTIVE"
    state["runner"] = {"kind": "REMEDIATION_FIXTURES", "request_id": request_id, "pid": proc.pid,
                       "command": command, "log": str(log_path.relative_to(ROOT)), "started_utc": now()}
    emit(state, "FIXTURES_STARTED", request_id=request_id, pid=proc.pid, command=command)
    return proc


def launch_v2_v3(state: dict[str, Any], plan: Path, request_id: str | None = None) -> subprocess.Popen[str]:
    command = [sys.executable, str(RUNNER), "--variants", "V2", "V3", "--max-cycles", "1"]
    request_id = request_id or f"auto-v2-v3-{plan.parent.name}"
    log_path = BASE / f"runner-{request_id}.log"
    controller_stop_path = BASE / f"controller-stop-{request_id}.json"
    controller_stop_path.unlink(missing_ok=True)
    env = os.environ.copy()
    env["AI370_CONTROLLER_STOP_FILE"] = str(controller_stop_path)
    with log_path.open("w") as log:
        proc = subprocess.Popen(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, start_new_session=True, text=True, env=env)
    state["status"] = "V2_V3_ACTIVE"
    state["runner"] = {"kind": "V2_V3", "request_id": request_id, "pid": proc.pid,
                       "command": command, "plan": str(plan.relative_to(ROOT)), "log": str(log_path.relative_to(ROOT)),
                       "controller_stop_path": str(controller_stop_path.relative_to(ROOT)), "started_utc": now()}
    emit(state, "V2_V3_STARTED", request_id=request_id, pid=proc.pid, command=command)
    return proc


def launch_t7_supplement(state: dict[str, Any], request_id: str) -> subprocess.Popen[str]:
    command = [sys.executable, str(RUNNER), "--variants", "V2", "V3", "--tasks", "T7", "--max-cycles", "1"]
    log_path = BASE / f"runner-{request_id}.log"
    controller_stop_path = BASE / f"controller-stop-{request_id}.json"
    controller_stop_path.unlink(missing_ok=True)
    env = os.environ.copy()
    env["AI370_CONTROLLER_STOP_FILE"] = str(controller_stop_path)
    with log_path.open("w") as log:
        proc = subprocess.Popen(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, start_new_session=True, text=True, env=env)
    state["status"] = "T7_SUPPLEMENT_ACTIVE"
    state["runner"] = {"kind": "T7_SUPPLEMENT", "request_id": request_id, "pid": proc.pid,
                       "command": command, "log": str(log_path.relative_to(ROOT)),
                       "controller_stop_path": str(controller_stop_path.relative_to(ROOT)), "started_utc": now()}
    emit(state, "T7_SUPPLEMENT_STARTED", request_id=request_id, pid=proc.pid, command=command)
    return proc


def request_stop(state: dict[str, Any], active: subprocess.Popen[str] | None, request_id: str) -> None:
    stop_path = QUALITY_BASE / "STOP"
    stop_path.parent.mkdir(parents=True, exist_ok=True)
    stop_path.write_text(f"Controller stop request {request_id} at {now()}\n")
    if active is not None and active.poll() is None:
        os.killpg(active.pid, signal.SIGINT)
    state["status"] = "STOP_REQUESTED"
    emit(state, "STOP_REQUESTED", request_id=request_id)


def freeze_v2_v3_plan(state: dict[str, Any]) -> bool:
    result = subprocess.run([sys.executable, str(PLAN_RUNNER)], cwd=ROOT, capture_output=True, text=True, timeout=60)
    details = {"exit_code": result.returncode, "stdout": result.stdout[-2000:], "stderr": result.stderr[-2000:]}
    state["v2_v3_plan"] = details
    if result.returncode == 0:
        state["status"] = "V2_V3_PLAN_READY"
        emit(state, "V2_V3_PLAN_FROZEN", **details)
        return True
    state["status"] = "V2_V3_PLAN_FAILED"
    emit(state, "V2_V3_PLAN_FAILED", **details)
    return False


def serve() -> int:
    BASE.mkdir(parents=True, exist_ok=True)
    with LOCK_PATH.open("w") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print(json.dumps({"status": "CONTROLLER_ALREADY_RUNNING", "lock": str(LOCK_PATH)}))
            return 2
        state = read_json(STATE_PATH) or state_template()
        # A service restart must not erase a terminal/review state.  Only a
        # newly created state, or a deliberately stopped controller, returns
        # to passive monitoring.
        if state.get("status") in {None, "CONTROLLER_STOPPED"}:
            state["status"] = "MONITORING"
        active: subprocess.Popen[str] | None = None
        active_baseline: dict[str, Any] | None = None
        terminate = False

        def handle_signal(_signum: int, _frame: Any) -> None:
            nonlocal terminate
            terminate = True

        signal.signal(signal.SIGINT, handle_signal)
        signal.signal(signal.SIGTERM, handle_signal)
        emit(state, "CONTROLLER_STARTED", pid=os.getpid())
        while not terminate:
            health = health_snapshot()
            append_jsonl(TELEMETRY_PATH, health)
            state["last_health"] = health
            quality = runner_status()
            state["quality_runner_status"] = quality.get("status") if quality else None
            historical_guard = recorded_controller_guard((state.get("runner") or {}).get("pid"))
            if (active is None and historical_guard and (state.get("runner") or {}).get("kind") == "V2_V3"
                    and state["quality_runner_status"] in {"STOPPED_BY_USER", "SAFETY_STOP"}):
                state["status"] = "V2_V3_SAFETY_REVIEW_REQUIRED"
                state["notes"] = f"V2/V3 was stopped by the controller safety gate ({historical_guard}); no retry is scheduled."
                state["runner"]["controller_guard_reason"] = historical_guard
            # Recover the explanatory state after a controller/service restart.
            # This is read-only with respect to the frozen quality session and
            # never relaunches a stopped run.
            if (active is None and state["quality_runner_status"] == "SAFETY_STOP"
                    and (state.get("runner") or {}).get("kind") == "V2_V3"
                    and state.get("status") != "V2_V3_SAFETY_REVIEW_REQUIRED"):
                state["status"] = "V2_V3_SAFETY_REVIEW_REQUIRED"
                state["notes"] = "V2/V3 stopped after a formal sample. Evidence was preserved and a read-only safety diagnosis was written; no retry is scheduled."
                diagnose_safety_stop(state)
            if (active is None and state["quality_runner_status"] == "PILOT_COMPLETE"
                    and state.get("status") not in {"REMEDIATION_FIXTURES_COMPLETE", "REMEDIATION_FIXTURES_FAILED", "V2_V3_PLAN_READY", "V2_V3_PLAN_FAILED"}):
                plan = latest_v2_v3_plan()
                if plan:
                    state["status"] = "V2_V3_PLAN_READY"
                    state["notes"] = "V1 evidence and remediation fixtures are retained. A frozen 144-sample V2/V3 plan is ready; model execution has not started."
                    state["v2_v3_plan_path"] = str(plan.relative_to(ROOT))
                elif REMEDIATION_REPORT.is_file():
                    state["status"] = "PILOT_REMEDIATION_READY"
                    state["notes"] = "V1 evidence is retained. Harness remediation is ready; freeze and validate a new V2/V3 execution plan before model work."
                else:
                    state["status"] = "WAITING_FOR_REVIEW"

            if active is not None and active.poll() is None and active_baseline is not None:
                mem_guard = max(6 * 1024 * 1024, int(health["memtotal_kib"] or 0) // 8)
                psi = (health.get("memory_psi", {}).get("full", {}) or {}).get("avg10", 0.0)
                base_vm = active_baseline.get("vmstat_pages", {})
                current_vm = health.get("vmstat_pages", {})
                swapin_bytes = (int(current_vm.get("pswpin", 0)) - int(base_vm.get("pswpin", 0))) * os.sysconf("SC_PAGE_SIZE")
                if health["memavailable_kib"] < mem_guard:
                    guard_reason = "MEMAVAILABLE_GUARD"
                elif (health["swapused_kib"] - active_baseline["swapused_kib"] > 64 * 1024
                      and (swapin_bytes >= 1024**2 or psi >= 20.0)):
                    guard_reason = "CORROBORATED_SWAP_PRESSURE_GUARD"
                elif psi >= 20.0:
                    guard_reason = "MEMORY_PSI_GUARD"
                else:
                    guard_reason = None
                if guard_reason:
                    stop_path = ROOT / state["runner"].get("controller_stop_path", "")
                    if str(stop_path) != str(ROOT):
                        atomic_json(stop_path, {"schema_version": 1, "reason": guard_reason, "timestamp_utc": now(),
                                                "owner": "LOCAL_MODEL_CONTROLLER"})
                    state["runner"]["controller_guard_reason"] = guard_reason
                    os.killpg(active.pid, signal.SIGINT)
                    state["status"] = "SAFETY_STOP"
                    emit(state, "CHILD_SAFETY_STOP", reason=guard_reason, pid=active.pid)

            plan = latest_v2_v3_plan()
            if (AUTO_CONTINUE_V2_V3 and active is None and plan is not None
                    and state.get("status") == "V2_V3_PLAN_READY"):
                active = launch_v2_v3(state, plan)
                active_baseline = health

            command = read_json(COMMAND_PATH)
            if command:
                error = command_error(command)
                request_id = command.get("request_id") if isinstance(command, dict) else None
                if error:
                    emit(state, "COMMAND_REJECTED", reason=error)
                elif request_id != state.get("last_command_id"):
                    state["last_command_id"] = request_id
                    if command["action"] == "ARM_PILOT":
                        if active is None or active.poll() is not None:
                            active = launch_pilot(state, request_id)
                            active_baseline = health if active else None
                        else:
                            emit(state, "COMMAND_REJECTED", request_id=request_id, reason="RUNNER_ALREADY_ACTIVE")
                    elif command["action"] == "RUN_REMEDIATION_FIXTURES":
                        if active is None or active.poll() is not None:
                            active = launch_remediation_fixtures(state, request_id)
                            active_baseline = health if active else None
                        else:
                            emit(state, "COMMAND_REJECTED", request_id=request_id, reason="RUNNER_ALREADY_ACTIVE")
                    elif command["action"] == "RESUME_V2_V3":
                        plan = latest_v2_v3_plan()
                        diagnosis = read_json(ROOT / state["last_safety_diagnosis"]) if state.get("last_safety_diagnosis") else None
                        assessment = (diagnosis or {}).get("assessment")
                        if active is not None and active.poll() is None:
                            emit(state, "COMMAND_REJECTED", request_id=request_id, reason="RUNNER_ALREADY_ACTIVE")
                        elif plan is None:
                            emit(state, "COMMAND_REJECTED", request_id=request_id, reason="V2_V3_PLAN_MISSING")
                        elif (state.get("quality_runner_status") not in {"SAFETY_STOP", "STOPPED_BY_USER"}
                              or (state.get("quality_runner_status") == "STOPPED_BY_USER"
                                  and not (state.get("runner") or {}).get("controller_guard_reason"))):
                            emit(state, "COMMAND_REJECTED", request_id=request_id, reason="QUALITY_STATE_NOT_RESUMABLE")
                        elif assessment != "INSUFFICIENT_EVIDENCE_OF_MEMORY_PRESSURE":
                            emit(state, "COMMAND_REJECTED", request_id=request_id, reason="SAFETY_DIAGNOSIS_REQUIRES_MANUAL_REVIEW")
                        else:
                            state["resumed_from_safety_diagnosis"] = state["last_safety_diagnosis"]
                            state["notes"] = "User-approved V2/V3 continuation starts a new session after a fresh five-minute preflight; prior evidence remains immutable."
                            active = launch_v2_v3(state, plan, request_id)
                            active_baseline = health
                    elif command["action"] == "RUN_T7_SUPPLEMENT":
                        ross_url = os.environ.get("AI370_ROSS_DOCSEARCH_URL")
                        quality_state = state.get("quality_runner_status")
                        if active is not None and active.poll() is None:
                            emit(state, "COMMAND_REJECTED", request_id=request_id, reason="RUNNER_ALREADY_ACTIVE")
                        elif quality_state not in {"COMPLETED_REQUESTED_CYCLES", "SAFETY_STOP"}:
                            emit(state, "COMMAND_REJECTED", request_id=request_id, reason="V2_V3_RESULT_NOT_COMPLETE")
                        elif not ross_url:
                            emit(state, "COMMAND_REJECTED", request_id=request_id, reason="ROSS_DOCSEARCH_URL_NOT_CONFIGURED")
                        else:
                            state["notes"] = "User-approved T7-only Ross MCP supplement starts a new 18-sample session; the completed V2/V3 session remains immutable."
                            active = launch_t7_supplement(state, request_id)
                            active_baseline = health
                    else:
                        request_stop(state, active, request_id)

            if active is not None and active.poll() is not None:
                exit_code = active.returncode
                state["runner"]["finished_utc"] = now()
                state["runner"]["exit_code"] = exit_code
                runner_kind = state["runner"].get("kind", "PILOT")
                active = None
                active_baseline = None
                quality = runner_status()
                state["quality_runner_status"] = quality.get("status") if quality else None
                if runner_kind == "REMEDIATION_FIXTURES":
                    if exit_code == 0:
                        freeze_v2_v3_plan(state)
                    else:
                        state["status"] = "REMEDIATION_FIXTURES_FAILED"
                elif runner_kind == "V2_V3":
                    controller_guard = state["runner"].get("controller_guard_reason")
                    if controller_guard:
                        state["status"] = "V2_V3_SAFETY_REVIEW_REQUIRED"
                        state["notes"] = f"V2/V3 was stopped by the controller safety gate ({controller_guard}); no retry is scheduled."
                        emit(state, "CONTROLLER_SAFETY_STOP_CONFIRMED", reason=controller_guard)
                    elif quality and quality.get("status") == "COMPLETED_REQUESTED_CYCLES":
                        state["status"] = "V2_V3_COMPLETE"
                    elif quality and quality.get("status") == "PREFLIGHT_BLOCKED":
                        state["status"] = "V2_V3_PREFLIGHT_BLOCKED"
                    elif quality and quality.get("status") == "SAFETY_STOP":
                        state["status"] = "V2_V3_SAFETY_REVIEW_REQUIRED"
                        state["notes"] = "V2/V3 stopped after a formal sample. Evidence was preserved and a read-only safety diagnosis was written; no retry is scheduled."
                        diagnose_safety_stop(state)
                    else:
                        state["status"] = "V2_V3_STOPPED"
                elif runner_kind == "T7_SUPPLEMENT":
                    if quality and quality.get("status") == "COMPLETED_REQUESTED_CYCLES":
                        state["status"] = "T7_SUPPLEMENT_COMPLETE"
                    elif quality and quality.get("status") == "PREFLIGHT_BLOCKED":
                        state["status"] = "T7_SUPPLEMENT_PREFLIGHT_BLOCKED"
                    else:
                        state["status"] = "T7_SUPPLEMENT_STOPPED"
                else:
                    state["status"] = "WAITING_FOR_REVIEW" if quality and quality.get("status") == "PILOT_COMPLETE" else "MONITORING"
                emit(state, "RUNNER_EXITED", kind=runner_kind, exit_code=exit_code, quality_status=state["quality_runner_status"])
            atomic_json(STATE_PATH, state)
            time.sleep(POLL_SECONDS)

        if active is not None and active.poll() is None:
            request_stop(state, active, "CONTROLLER_SHUTDOWN")
        state["status"] = "CONTROLLER_STOPPED"
        emit(state, "CONTROLLER_STOPPED")
        atomic_json(STATE_PATH, state)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("serve", "status", "arm-pilot", "run-remediation-fixtures", "resume-v2-v3", "run-t7-supplement", "stop"))
    parser.add_argument("--request-id", help="Unique durable command ID for an action")
    args = parser.parse_args()
    if args.command == "serve":
        return serve()
    if args.command == "status":
        state = read_json(STATE_PATH) or {"status": "NOT_RUNNING"}
        print(json.dumps(state, ensure_ascii=False, indent=2))
        return 0
    if not args.request_id:
        parser.error("--request-id is required for arm-pilot and stop")
    action = {"arm-pilot": "ARM_PILOT", "run-remediation-fixtures": "RUN_REMEDIATION_FIXTURES", "resume-v2-v3": "RESUME_V2_V3", "run-t7-supplement": "RUN_T7_SUPPLEMENT", "stop": "STOP"}[args.command]
    command: dict[str, Any] = {"schema_version": 1, "request_id": args.request_id, "action": action}
    if action in {"ARM_PILOT", "RUN_REMEDIATION_FIXTURES", "RESUME_V2_V3", "RUN_T7_SUPPLEMENT"}:
        command["approved"] = True
    atomic_json(COMMAND_PATH, command)
    print(json.dumps({"status": "COMMAND_WRITTEN", "command": command, "path": str(COMMAND_PATH)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
