#!/usr/bin/env python3
"""Freeze the post-Pilot V2/V3 execution identity without starting a model."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
QUALITY = ROOT / "output" / "QUALITY_MODEL_VALIDATION"
OUT = ROOT / "output" / "LOCAL_MODEL_CONTROLLER" / "plans"
FILES = (
    "scripts/run_quality_pilot.py", "scripts/run_quality_guarded_trial.py",
    "scripts/quality_local_agent.py", "scripts/local_agent.py",
    "scripts/quality_task_executor.py", "scripts/prepare_quality_workspace.py",
)


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    current = json.loads((QUALITY / "status.json").read_text())
    if current.get("status") != "PILOT_COMPLETE":
        raise SystemExit("V2/V3 plan requires retained V1 PILOT_COMPLETE evidence")
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    folder = OUT / run_id
    corpus = ROOT / "docs" / "LOCAL_MODEL_LAB" / "quality-corpus" / "v1"
    manifests = {f"{task}/{variant}": sha(corpus / task / variant / "SHA256SUMS.json")
                 for task in (f"T{i}" for i in range(1, 9)) for variant in ("V2", "V3")}
    model_integrity = QUALITY / "20261022T182952+0800" / "model-integrity.json"
    plan = {
        "schema_version": 1,
        "stage": "V2_V3_POST_PILOT_PLAN",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "v1_evidence": {"session": current.get("session"), "status": current.get("status"), "samples": current.get("formal_sample_count")},
        "execution": {"variants": ["V2", "V3"], "models": 9, "tasks_per_model": 8, "expected_samples": 144,
                      "command": ["python3", "scripts/run_quality_pilot.py", "--variants", "V2", "V3", "--max-cycles", "1"]},
        "harness_sha256": {name: sha(ROOT / name) for name in FILES},
        "corpus_manifests_sha256": manifests,
        "model_integrity_sha256": sha(model_integrity),
        "t7_policy": "BLOCKED for every model unless the configured local Ross MCP endpoint is available; no substitute source is permitted.",
        "approval": "PLAN_FROZEN_NOT_STARTED",
    }
    # Hash every input before creating the folder so a missing input leaves no
    # empty plan directory behind in the live plans tree.
    folder.mkdir(parents=True, exist_ok=False)
    path = folder / "v2-v3-plan.json"
    path.write_text(json.dumps(plan, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"status": "PLAN_FROZEN_NOT_STARTED", "plan": str(path.relative_to(ROOT))}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
