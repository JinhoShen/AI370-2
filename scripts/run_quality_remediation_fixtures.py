#!/usr/bin/env python3
"""Run non-model checks required after a quality-harness remediation."""
from __future__ import annotations

import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output" / "LOCAL_MODEL_CONTROLLER" / "remediation-fixtures"


def as_text(value: str | bytes | None) -> str:
    """TimeoutExpired carries bytes on POSIX even when text=True was requested."""
    return value.decode(errors="replace") if isinstance(value, bytes) else (value or "")


def main() -> int:
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    folder = OUT / run_id
    folder.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    commands = [
        ("agent_unit_tests", [sys.executable, "-m", "unittest", "scripts/test_quality_local_agent.py", "scripts/test_quality_pilot.py"], 120),
        ("corpus_fixtures", [sys.executable, "scripts/validate_quality_corpus.py", "--task", "all"], 10800),
    ]
    results = []
    for name, command, timeout in commands:
        try:
            proc = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=timeout)
            result = {"name": name, "command": command, "exit_code": proc.returncode,
                      "stdout": proc.stdout[-8000:], "stderr": proc.stderr[-8000:]}
        except subprocess.TimeoutExpired as exc:
            result = {"name": name, "command": command, "exit_code": None, "error": f"TimeoutExpired after {timeout}s",
                      "stdout": as_text(exc.stdout)[-8000:], "stderr": as_text(exc.stderr)[-8000:]}
        results.append(result)
        (folder / f"{name}.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
        if result.get("exit_code") != 0:
            break
    report = {"stage": "REMEDIATION_FIXTURES", "run_id": run_id,
              "status": "PASS" if len(results) == len(commands) and all(row.get("exit_code") == 0 for row in results) else "FAIL",
              "elapsed_seconds": round(time.monotonic() - started, 3), "results": results}
    (folder / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"status": report["status"], "report": str((folder / "report.json").relative_to(ROOT))}, ensure_ascii=False))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
