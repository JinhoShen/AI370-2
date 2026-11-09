#!/usr/bin/env python3
"""Create one isolated public workspace from an immutable corpus variant."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "docs/LOCAL_MODEL_LAB/quality-corpus/v1"
OUTPUT = ROOT / "output/QUALITY_MODEL_VALIDATION"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare(task: str, variant: str, session: str, model: str) -> dict:
    if task not in {"T1", "T2", "T3", "T4", "T5", "T6", "T7", "T8"} or variant not in {"V1", "V2", "V3"}:
        raise ValueError("only frozen T1-T8 V1-V3 currently have workspace preparation")
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", session):
        raise ValueError("session must contain only letters, digits, underscore or hyphen")
    source = CORPUS / task / variant
    manifest = json.loads((source / "SHA256SUMS.json").read_text())
    expected = manifest["files"]
    actual = {p.relative_to(source).as_posix(): sha(p) for p in source.rglob("*") if p.is_file() and p.name != "SHA256SUMS.json"}
    if actual != expected:
        raise RuntimeError("frozen corpus hash mismatch")
    workspace = OUTPUT / session / "samples" / model / task / variant / "workspace"
    workspace.parent.mkdir(parents=True, exist_ok=True)
    workspace.mkdir(parents=True, exist_ok=False)
    shutil.copy2(source / "public/TASK_SPEC.md", workspace / "TASK_SPEC.md")
    if task in {"T4", "T5", "T7"}:
        shutil.copytree(source / "public/rtl", workspace / "rtl")
    elif task == "T6":
        shutil.copytree(source / "public/src", workspace / "src")
        shutil.copy2(source / "public/hls_config.cfg", workspace / "hls_config.cfg")
    else:
        (workspace / "rtl").mkdir()
        shutil.copy2(source / "public/rtl/axi_regs.sv", workspace / "rtl/axi_regs.sv")
    if task == "T3":
        (workspace / "sim").mkdir()
        shutil.copy2(source / "public/sim/tb_axi_regs.sv", workspace / "sim/tb_axi_regs.sv")
    subprocess.run(["git", "init", "--quiet"], cwd=workspace, check=True)
    subprocess.run(["git", "config", "user.name", "AI370-2 isolated quality fixture"], cwd=workspace, check=True)
    subprocess.run(["git", "config", "user.email", "local@invalid"], cwd=workspace, check=True)
    initial_files = ["TASK_SPEC.md"] + [p.relative_to(workspace).as_posix() for p in sorted((workspace / "rtl").rglob("*.sv"))]
    if task == "T6":
        initial_files += ["src/invert32.cpp", "hls_config.cfg"]
    if task == "T3":
        initial_files.append("sim/tb_axi_regs.sv")
    editable = {
        "T1": ["rtl/axi_regs.sv"], "T2": ["rtl/axi_regs.sv"],
        "T3": ["sim/tb_axi_regs.sv"],
        "T4": ["rtl/alu_pkg.sv", "rtl/alu.sv", "rtl/calc_top.sv"],
        "T5": ["rtl/mux_math.sv"], "T6": ["src/invert32.cpp"],
        "T7": ["rtl/alu_pkg.sv", "rtl/alu.sv", "rtl/calc_top.sv"],
        "T8": ["rtl/axi_regs.sv"],
    }[task]
    subprocess.run(["git", "add", *initial_files], cwd=workspace, check=True)
    subprocess.run(["git", "commit", "--quiet", "-m", f"Frozen {task} baseline"], cwd=workspace, check=True)
    record = {
        "task": task, "variant": variant, "model": model,
        "workspace": str(workspace),
        "editable_paths": editable,
        "public_inputs_sha256": {"TASK_SPEC.md": sha(workspace / "TASK_SPEC.md"),
                                 **{p.relative_to(workspace).as_posix(): sha(p) for p in sorted((workspace / "rtl").rglob("*.sv"))},
                                 **({"src/invert32.cpp":sha(workspace/"src/invert32.cpp"),"hls_config.cfg":sha(workspace/"hls_config.cfg")} if task=="T6" else {}),
                                 **({"sim/tb_axi_regs.sv": sha(workspace / "sim/tb_axi_regs.sv")} if task == "T3" else {})},
        "corpus_manifest": str((source / "SHA256SUMS.json").relative_to(ROOT)),
        "corpus_manifest_sha256": sha(source / "SHA256SUMS.json"),
        "runner_sha256": {
            path: sha(ROOT / path) for path in (
                "scripts/quality_task_executor.py", "scripts/quality_local_agent.py",
                "scripts/local_agent.py", "scripts/run_quality_guarded_trial.py", "scripts/run_quality_pilot.py",
            )
        },
        "workspace_git_head": subprocess.run(["git", "rev-parse", "HEAD"], cwd=workspace, capture_output=True, text=True, check=True).stdout.strip(),
    }
    record_path = workspace.parent / "protocol.json"
    record_path.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n")
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task", required=True)
    parser.add_argument("--variant", required=True)
    parser.add_argument("--session", required=True)
    parser.add_argument("--model", required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args.task, args.variant, args.session, args.model), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
