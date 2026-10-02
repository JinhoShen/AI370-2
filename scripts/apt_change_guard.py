#!/usr/bin/env python3
"""APT simulation guard for AMD GPU/NPU and kernel protected packages.

Never installs anything. Any proposed install, upgrade, downgrade, or removal
matching a protected package family is rejected before a human could run APT.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

PROJECT = Path(__file__).resolve().parent.parent
ACTION_RE = re.compile(r"^(Inst|Remv)\s+([^\s]+)(?:\s|$)", re.MULTILINE)
SUMMARY_RE = re.compile(r"^(\d+) upgraded, (\d+) newly installed, (\d+) to remove", re.MULTILINE)
PROTECTED_RE = re.compile(
    r"^(?:linux-(?:image|headers|modules|generic|firmware).*|"
    r"mesa.*|libdrm.*|rocm.*|libroc.*|hip.*|libamd.*|hsa.*|libhsa.*|libhsakmt.*|"
    r"amdxdna.*|xrt.*|libxrt.*|amdgpu.*|amdvlk.*|firmware-amd.*|amd-gpu.*)$",
    re.IGNORECASE,
)
PACKAGE_RE = re.compile(r"^[A-Za-z0-9.+:~=_-]+$")


def classify_simulation(text: str, *, strict: bool = False) -> dict:
    actions = []
    for kind, raw_name in ACTION_RE.findall(text):
        name = raw_name.split(":", 1)[0]
        actions.append({
            "action": "install_or_change" if kind == "Inst" else "remove",
            "package": raw_name,
            "protected": bool(PROTECTED_RE.fullmatch(name)),
        })
    blocked = [item for item in actions if item["protected"]]
    summary = SUMMARY_RE.search(text)
    expected_actions = None
    if summary:
        upgraded, newly_installed, removed = map(int, summary.groups())
        expected_actions = upgraded + newly_installed + removed
    unknown = strict and (expected_actions is None or expected_actions != len(actions))
    verdict = "BLOCKED_PROTECTED_STACK" if blocked else ("UNKNOWN_SIMULATION_OUTPUT" if unknown else "SAFE_SIMULATION")
    return {
        "actions": actions,
        "protected_changes": blocked,
        "expected_action_count": expected_actions,
        "verdict": verdict,
    }


def main(argv: list[str]) -> int:
    if argv[:1] == ["--parse-only"]:
        report = classify_simulation(sys.stdin.read())
        print(json.dumps(report, indent=2))
        return 3 if report["protected_changes"] else 0
    if not argv or any(not PACKAGE_RE.fullmatch(arg) or arg.startswith("-") for arg in argv):
        print("Usage: apt_change_guard.py PACKAGE[=VERSION] ...", file=sys.stderr)
        return 2

    stamp = datetime.now(ZoneInfo("Asia/Taipei")).strftime("%Y%m%dT%H%M%S%z")
    output_dir = PROJECT / "output" / "M14" / "apt-simulations"
    output_dir.mkdir(parents=True, exist_ok=True)
    log_path = output_dir / f"{stamp}.log"
    command = ["apt-get", "-s", "--no-install-recommends", "install", *argv]
    env = dict(__import__("os").environ, LC_ALL="C")
    run = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False, env=env)
    log_path.write_text(run.stdout, encoding="utf-8")
    report = classify_simulation(run.stdout, strict=True)
    report.update({"requested": argv, "exit_status": run.returncode, "log": str(log_path.relative_to(PROJECT))})
    report_path = output_dir / f"{stamp}.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    if run.returncode:
        return 2
    if report["protected_changes"]:
        return 3
    if report["verdict"] != "SAFE_SIMULATION":
        return 4
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
