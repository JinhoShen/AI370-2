#!/usr/bin/env python3
"""Run deterministic non-model fixtures for the frozen quality corpus."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import time
import shlex
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "docs/LOCAL_MODEL_LAB/quality-corpus/v2"
VIVADO = Path("/home/shen/tools/Xilinx/2026.1/2026.1/Vivado")
FIXTURE_ROOT = ROOT / "output/QUALITY_MODEL_VALIDATION/20261022T182952+0800/fixtures"


def vivado_env() -> dict[str, str]:
    proc = subprocess.run(
        ["/usr/bin/bash", "-c", f"source {shlex.quote(str(VIVADO / 'settings64.sh'))} >/dev/null && /usr/bin/env -0"],
        capture_output=True, timeout=30, check=True,
    )
    result = os.environ.copy()
    for item in proc.stdout.split(b"\0"):
        if b"=" in item:
            key, value = item.split(b"=", 1)
            result[key.decode()] = value.decode(errors="replace")
    return result


def run_xsim(rtl: Path, tb: Path, work: Path, marker: str = "QUALITY_T1_PASS") -> dict:
    work.mkdir(parents=True, exist_ok=True)
    result = {}
    env = vivado_env()
    for name, command in [
        ("xvlog", [str(VIVADO / "bin/xvlog"), "--sv", "-work", "xil_defaultlib", str(rtl), str(tb)]),
        ("xelab", [str(VIVADO / "bin/xelab"), "xil_defaultlib.tb_axi_regs", "-s", "quality_fixture"]),
        ("xsim", [str(VIVADO / "bin/xsim"), "quality_fixture", "-runall"]),
    ]:
        proc = subprocess.run(command, cwd=work, env=env, capture_output=True, text=True, timeout=180)
        output = proc.stdout + "\n" + proc.stderr
        (work / f"{name}.log").write_text(output)
        result[name] = {"exit_code": proc.returncode, "log": str((work / f"{name}.log").relative_to(ROOT)), "log_sha256": hashlib.sha256(output.encode()).hexdigest()}
        if proc.returncode:
            result["terminal_marker"] = None
            return result
    sim_log = (work / "xsim.log").read_text(errors="replace")
    result["terminal_marker"] = next((line for line in sim_log.splitlines() if line.startswith(marker)), None)
    result["pass"] = result["terminal_marker"] is not None
    return result


def run_synthesis(rtl: Path, work: Path) -> dict:
    work.mkdir(parents=True, exist_ok=True)
    tcl = work / "fixed_synth.tcl"
    report = work / "utilization.rpt"
    tcl.write_text(
        f"read_verilog -sv {{{rtl}}}\n"
        "synth_design -top axi_regs -part xc7s100fgga676-2\n"
        f"report_utilization -file {{{report}}}\n"
        "puts QUALITY_T1_SYNTH_PASS\nexit\n"
    )
    command = [str(VIVADO / "bin/vivado"), "-mode", "batch", "-notrace", "-source", str(tcl), "-log", str(work / "vivado.log"), "-journal", str(work / "vivado.jou")]
    proc = subprocess.run(command, cwd=work, env=vivado_env(), capture_output=True, text=True, timeout=600)
    output = proc.stdout + "\n" + proc.stderr
    (work / "stdout.log").write_text(proc.stdout)
    (work / "stderr.log").write_text(proc.stderr)
    log_path = work / "vivado.log"
    log = log_path.read_text(errors="replace") if log_path.exists() else output
    latch_lines = [line for line in log.splitlines() if re.search(r"infer(?:ring|red)? latch|latch inferred", line, re.I)]
    result = {
        "exit_code": proc.returncode,
        "pass_marker": "QUALITY_T1_SYNTH_PASS" in output,
        "utilization_report": str(report.relative_to(ROOT)) if report.exists() else None,
        "latch_diagnostics": latch_lines,
        "log_sha256": hashlib.sha256(log.encode()).hexdigest(),
    }
    result["pass"] = proc.returncode == 0 and result["pass_marker"] and report.is_file() and not latch_lines
    return result


def run_mutation(reference: Path, tb: Path, work: Path, mutation: str) -> dict:
    source = reference.read_text()
    if mutation == "reset-value":
        source = re.sub(r"regs\[0\] <= 32'h[0-9A-Fa-f]+;", "regs[0] <= 32'h00000000;", source, count=1)
    elif mutation == "ignore-wstrb":
        source = source.replace("if (selected_ws[b])", "if (1'b1)")
    elif mutation == "same-cycle-aw-w":
        source = source.replace(
            "assign s_axi_awready = aresetn && !aw_pending && !s_axi_bvalid;",
            "assign s_axi_awready = aresetn && !aw_pending && !s_axi_bvalid && s_axi_wvalid;",
        )
    elif mutation == "unstable-read-response":
        source = source.replace(
            "if (s_axi_rvalid && s_axi_rready) s_axi_rvalid <= 0;",
            "if (s_axi_rvalid && !s_axi_rready) s_axi_rdata <= ~s_axi_rdata;\n      if (s_axi_rvalid && s_axi_rready) s_axi_rvalid <= 0;",
        )
    else:
        raise ValueError(mutation)
    if source == reference.read_text():
        raise RuntimeError(f"mutation did not alter source: {mutation}")
    work.mkdir(parents=True, exist_ok=True)
    mutant = work / "axi_regs.sv"
    mutant.write_text(source)
    result = run_xsim(mutant, tb, work / "runs")
    return {"mutation": mutation, "detected": not result.get("pass", False), "result": result}


def verify_frozen_variant(folder: Path) -> None:
    manifest_path = folder / "SHA256SUMS.json"
    manifest = json.loads(manifest_path.read_text())
    actual = {}
    for path in sorted(folder.rglob("*")):
        if path.is_file() and path != manifest_path:
            actual[path.relative_to(folder).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual != manifest.get("files"):
        raise RuntimeError(f"frozen corpus integrity mismatch: {folder}")


def validate_t1(variants: list[str], result_root: Path) -> list[dict]:
    outcomes = []
    for variant in variants:
        source = CORPUS / "T1" / variant
        verify_frozen_variant(source)
        public_rtl = source / "public/rtl/axi_regs.sv"
        hidden_tb = source / "private/tb_axi_regs.sv"
        reference = source / "private/reference_axi_regs.sv"
        result_dir = result_root / "T1" / variant
        shutil.rmtree(result_dir, ignore_errors=True)
        baseline_dir = result_dir / "baseline"
        reference_dir = result_dir / "reference"
        baseline_dir.mkdir(parents=True)
        reference_dir.mkdir(parents=True)
        baseline_rtl = baseline_dir / "axi_regs.sv"
        baseline_rtl.write_bytes(public_rtl.read_bytes())
        tb_copy = baseline_dir / "tb_axi_regs.sv"
        tb_copy.write_bytes(hidden_tb.read_bytes())
        baseline_xsim = run_xsim(baseline_rtl, tb_copy, baseline_dir / "runs")
        reference_rtl = reference_dir / "axi_regs.sv"
        reference_rtl.write_bytes(reference.read_bytes())
        ref_tb = reference_dir / "tb_axi_regs.sv"
        ref_tb.write_bytes(hidden_tb.read_bytes())
        ref_xsim = run_xsim(reference_rtl, ref_tb, reference_dir / "runs")
        synth = run_synthesis(reference_rtl, reference_dir / "synthesis")
        mutations = [
            run_mutation(reference, hidden_tb, result_dir / "mutations" / name, name)
            for name in ("reset-value", "ignore-wstrb", "same-cycle-aw-w", "unstable-read-response")
        ]
        outcomes.append({
            "task": "T1", "variant": variant,
            "baseline_expected_fail": not baseline_xsim.get("pass", False),
            "baseline": baseline_xsim,
            "reference_xsim": ref_xsim,
            "reference_synthesis": synth,
            "mutations": mutations,
            "fixture_pass": not baseline_xsim.get("pass", False) and ref_xsim.get("pass", False) and synth.get("pass", False) and all(row["detected"] for row in mutations),
            "artifacts": str(result_dir.relative_to(ROOT)),
        })
    return outcomes


def validate_t2(variants: list[str], result_root: Path) -> list[dict]:
    outcomes = []
    for variant in variants:
        source = CORPUS / "T2" / variant
        verify_frozen_variant(source)
        public_rtl = source / "public/rtl/axi_regs.sv"
        hidden_tb = source / "private/tb_axi_regs.sv"
        reference = source / "private/reference_axi_regs.sv"
        result_dir = result_root / "T2" / variant
        baseline_dir = result_dir / "baseline"
        reference_dir = result_dir / "reference"
        baseline_dir.mkdir(parents=True, exist_ok=False)
        reference_dir.mkdir(parents=True, exist_ok=False)
        baseline_rtl = baseline_dir / "axi_regs.sv"
        baseline_rtl.write_bytes(public_rtl.read_bytes())
        baseline_tb = baseline_dir / "tb_axi_regs.sv"
        baseline_tb.write_bytes(hidden_tb.read_bytes())
        baseline = run_xsim(baseline_rtl, baseline_tb, baseline_dir / "runs")
        ref_rtl = reference_dir / "axi_regs.sv"
        ref_rtl.write_bytes(reference.read_bytes())
        ref_tb = reference_dir / "tb_axi_regs.sv"
        ref_tb.write_bytes(hidden_tb.read_bytes())
        ref_xsim = run_xsim(ref_rtl, ref_tb, reference_dir / "runs")
        synth = run_synthesis(ref_rtl, reference_dir / "synthesis")
        outcomes.append({
            "task": "T2", "variant": variant,
            "baseline_expected_fail": not baseline.get("pass", False),
            "baseline": baseline, "reference_xsim": ref_xsim,
            "reference_synthesis": synth,
            "fixture_pass": not baseline.get("pass", False) and ref_xsim.get("pass", False) and synth.get("pass", False),
            "artifacts": str(result_dir.relative_to(ROOT)),
        })
    return outcomes


def validate_t3(variants: list[str], result_root: Path) -> list[dict]:
    outcomes = []
    required = {f"QUALITY_T3_SCENARIO_{name}_PASS" for name in (
        "reset", "aw_before_w", "w_before_aw", "simultaneous", "wstrb", "unmapped",
        "b_backpressure", "r_backpressure", "consecutive",
    )}
    for variant in variants:
        source = CORPUS / "T3" / variant
        verify_frozen_variant(source)
        public = source / "public"
        private = source / "private"
        result_dir = result_root / "T3" / variant
        baseline_dir = result_dir / "baseline"
        reference_dir = result_dir / "reference"
        baseline_dir.mkdir(parents=True, exist_ok=False)
        reference_dir.mkdir(parents=True, exist_ok=False)
        dut = public / "rtl/axi_regs.sv"
        baseline_tb = baseline_dir / "tb_axi_regs.sv"
        reference_tb = private / "reference_tb_axi_regs.sv"
        shutil.copy2(public / "sim/tb_axi_regs.sv", baseline_tb)
        baseline_xsim = run_xsim(dut, baseline_tb, baseline_dir / "runs", "QUALITY_T3_PASS")
        ref_tb_copy = reference_dir / "tb_axi_regs.sv"
        shutil.copy2(reference_tb, ref_tb_copy)
        reference_xsim = run_xsim(dut, ref_tb_copy, reference_dir / "runs", "QUALITY_T3_PASS")
        # A reference that fails xvlog/xelab has no xsim log; its missing markers then fail the fixture.
        ref_log = reference_xsim.get("xsim", {}).get("log")
        ref_text = (ROOT / ref_log).read_text(errors="replace") if ref_log else ""
        observed = {line for line in ref_text.splitlines() if line in required}
        mutants = []
        for mutation_path in sorted((private / "mutants").glob("*.sv")):
            name = mutation_path.stem
            mutation_dir = result_dir / "mutants" / name
            mutation_dir.mkdir(parents=True, exist_ok=False)
            tb_copy = mutation_dir / "tb_axi_regs.sv"
            shutil.copy2(reference_tb, tb_copy)
            result = run_xsim(mutation_path, tb_copy, mutation_dir / "runs", "QUALITY_T3_PASS")
            mutants.append({"mutation": name, "detected": not result.get("pass", False), "result": result})
        outcomes.append({
            "task": "T3", "variant": variant,
            "baseline_expected_fail": not baseline_xsim.get("pass", False), "baseline": baseline_xsim,
            "reference_xsim": reference_xsim,
            "scenario_markers_expected": sorted(required), "scenario_markers_observed": sorted(observed),
            "mutants": mutants,
            "fixture_pass": not baseline_xsim.get("pass", False) and reference_xsim.get("pass", False)
                and observed == required and all(row["detected"] for row in mutants),
            "artifacts": str(result_dir.relative_to(ROOT)),
        })
    return outcomes


def executor_payload(proc: subprocess.CompletedProcess) -> dict:
    """Parse the executor's final JSON line; anything but an object is a harness fault."""
    try:
        payload = json.loads(proc.stdout.splitlines()[-1])
    except (IndexError, json.JSONDecodeError):
        payload = None
    if not isinstance(payload, dict):
        payload = {"status": "HARNESS_INVALID", "stdout": proc.stdout[-2000:], "stderr": proc.stderr[-2000:]}
    return payload


def validate_t4(variants: list[str], result_root: Path, task: str = "T4") -> list[dict]:
    outcomes = []
    for variant in variants:
        source = CORPUS / task / variant
        verify_frozen_variant(source)
        result_dir = result_root / task / variant
        result_dir.mkdir(parents=True, exist_ok=False)
        pair = {}
        for label, attempt in (("baseline", 1), ("reference", 2)):
            workspace = result_dir / label
            shutil.copytree(source / "public", workspace)
            if label == "reference":
                design = workspace / "rtl/calc_top.sv"
                text = design.read_text()
                if variant == "V1": text = text.replace(".operation(op)", ".op(op)")
                elif variant == "V2": text = text.replace("alu_core u_alu", "alu u_alu")
                elif variant == "V3": text = text.replace(".valid_o(valid)", ".valid(valid)")
                design.write_text(text)
            proc = subprocess.run([sys.executable, str(ROOT / "scripts/quality_task_executor.py"),
                                   "--task", task, "--variant", variant, "--workspace", str(workspace),
                                   "--attempt", str(attempt)], cwd=ROOT, capture_output=True, text=True, timeout=900)
            payload = executor_payload(proc)
            pair[label] = {"exit_code": proc.returncode, "result": payload, "stderr": proc.stderr[-2000:]}
        baseline = pair["baseline"]["result"]
        reference = pair["reference"]["result"]
        expected_fail = baseline.get("status") == "FAIL" and not baseline.get("xsim", {}).get("terminal_marker")
        marker = "QUALITY_T7_PASS" if task == "T7" else "QUALITY_T4_PASS"
        expected_pass = reference.get("status") == "PASS" and str(reference.get("xsim", {}).get("terminal_marker", "")).startswith(marker)
        outcomes.append({"task": task, "variant": variant, **pair,
                         "baseline_expected_fail": expected_fail, "reference_expected_pass": expected_pass,
                         "fixture_pass": expected_fail and expected_pass, "artifacts": str(result_dir.relative_to(ROOT))})
    return outcomes


def validate_t5(variants: list[str], result_root: Path) -> list[dict]:
    outcomes=[]
    for variant in variants:
        source=CORPUS/"T5"/variant; verify_frozen_variant(source)
        result_dir=result_root/"T5"/variant; result_dir.mkdir(parents=True,exist_ok=False)
        pair={}
        for label,attempt in (("baseline",1),("reference",2)):
            workspace=result_dir/label; shutil.copytree(source/"public",workspace)
            if label=="reference": shutil.copy2(source/"private/reference_mux_math.sv",workspace/"rtl/mux_math.sv")
            proc=subprocess.run([sys.executable,str(ROOT/"scripts/quality_task_executor.py"),"--task","T5","--variant",variant,"--workspace",str(workspace),"--attempt",str(attempt)],cwd=ROOT,capture_output=True,text=True,timeout=900)
            payload=executor_payload(proc)
            pair[label]={"exit_code":proc.returncode,"result":payload,"stderr":proc.stderr[-2000:]}
        baseline=pair["baseline"]["result"]; reference=pair["reference"]["result"]
        expected_fail=baseline.get("status")=="FAIL" and not baseline.get("xsim",{}).get("terminal_marker") and baseline.get("synthesis",{}).get("pass") is False and bool(baseline.get("synthesis",{}).get("latch_diagnostics"))
        expected_pass=reference.get("status")=="PASS" and str(reference.get("xsim",{}).get("terminal_marker","")).startswith("QUALITY_T5_PASS") and reference.get("synthesis",{}).get("pass") is True
        outcomes.append({"task":"T5","variant":variant,**pair,"baseline_expected_fail":expected_fail,"reference_expected_pass":expected_pass,
                         "fixture_pass":expected_fail and expected_pass,"artifacts":str(result_dir.relative_to(ROOT))})
    return outcomes


def validate_t6(variants: list[str], result_root: Path) -> list[dict]:
    outcomes=[]
    for variant in variants:
        source=CORPUS/"T6"/variant; verify_frozen_variant(source)
        result_dir=result_root/"T6"/variant; result_dir.mkdir(parents=True,exist_ok=False); pair={}
        for label,attempt in (("baseline",1),("reference",2)):
            workspace=result_dir/label; shutil.copytree(source/"public",workspace)
            if label=="reference": shutil.copy2(source/"private/reference_invert32.cpp",workspace/"src/invert32.cpp")
            proc=subprocess.run([sys.executable,str(ROOT/"scripts/quality_task_executor.py"),"--task","T6","--variant",variant,"--workspace",str(workspace),"--attempt",str(attempt)],cwd=ROOT,capture_output=True,text=True,timeout=2400)
            payload=executor_payload(proc)
            pair[label]={"exit_code":proc.returncode,"result":payload,"stderr":proc.stderr[-2000:]}
        baseline=pair["baseline"]["result"]; reference=pair["reference"]["result"]
        expected_fail=baseline.get("status")=="FAIL" and baseline.get("csim",{}).get("pass") is False
        expected_pass=reference.get("status")=="PASS" and reference.get("csim",{}).get("pass") is True and reference.get("csynth",{}).get("pass") is True
        outcomes.append({"task":"T6","variant":variant,**pair,"baseline_expected_fail":expected_fail,"reference_expected_pass":expected_pass,
                         "fixture_pass":expected_fail and expected_pass,"artifacts":str(result_dir.relative_to(ROOT))})
    return outcomes


def validate_t8(variants: list[str], result_root: Path) -> list[dict]:
    outcomes=[]
    for variant in variants:
        source=CORPUS/"T8"/variant; verify_frozen_variant(source)
        result_dir=result_root/"T8"/variant; result_dir.mkdir(parents=True,exist_ok=False); pair={}
        for label,attempt in (("baseline",1),("reference",2)):
            workspace=result_dir/label; shutil.copytree(source/"public",workspace)
            if label=="reference": shutil.copy2(source/"private/reference_axi_regs.sv",workspace/"rtl/axi_regs.sv")
            proc=subprocess.run([sys.executable,str(ROOT/"scripts/quality_task_executor.py"),"--task","T8","--variant",variant,"--workspace",str(workspace),"--attempt",str(attempt)],cwd=ROOT,capture_output=True,text=True,timeout=1200)
            payload=executor_payload(proc)
            pair[label]={"exit_code":proc.returncode,"result":payload,"stderr":proc.stderr[-2000:]}
        baseline=pair["baseline"]["result"]; reference=pair["reference"]["result"]
        expected_fail=baseline.get("status")=="FAIL" and baseline.get("xsim",{}).get("pass") is False
        expected_pass=reference.get("status")=="PASS" and reference.get("xsim",{}).get("pass") is True and reference.get("synthesis",{}).get("pass") is True
        outcomes.append({"task":"T8","variant":variant,**pair,"baseline_expected_fail":expected_fail,"reference_expected_pass":expected_pass,
                         "fixture_pass":expected_fail and expected_pass,"artifacts":str(result_dir.relative_to(ROOT))})
    return outcomes


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task", choices=["T1", "T2", "T3", "T4", "T5", "T6", "T7", "T8", "all"], required=True)
    args = parser.parse_args()
    start = time.monotonic()
    run_id = time.strftime("%Y%m%dT%H%M%S")
    result_root = FIXTURE_ROOT / "runs" / run_id
    result_root.mkdir(parents=True, exist_ok=False)
    outcomes = []
    if args.task in {"T1", "all"}:
        outcomes += validate_t1(["V1", "V2", "V3"], result_root)
    if args.task in {"T2", "all"}:
        outcomes += validate_t2(["V1", "V2", "V3"], result_root)
    if args.task in {"T3", "all"}:
        outcomes += validate_t3(["V1", "V2", "V3"], result_root)
    if args.task in {"T4", "all"}:
        outcomes += validate_t4(["V1", "V2", "V3"], result_root)
    if args.task in {"T5", "all"}:
        outcomes += validate_t5(["V1", "V2", "V3"], result_root)
    if args.task in {"T6", "all"}:
        outcomes += validate_t6(["V1", "V2", "V3"], result_root)
    if args.task in {"T7", "all"}:
        outcomes += validate_t4(["V1", "V2", "V3"], result_root, task="T7")
    if args.task in {"T8", "all"}:
        outcomes += validate_t8(["V1", "V2", "V3"], result_root)
    report = {"task": args.task, "run_id": run_id, "status": "PASS" if all(row["fixture_pass"] for row in outcomes) else "FAIL", "elapsed_seconds": round(time.monotonic() - start, 3), "variants": outcomes}
    destination = result_root / "fixture-results.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"status": report["status"], "report": str(destination.relative_to(ROOT)), "variants": [{"task": x["task"], "variant": x["variant"], "baseline_failed": x.get("baseline_expected_fail"), "reference_xsim": x.get("reference_xsim", {}).get("pass", x.get("reference", {}).get("result", {}).get("xsim", x.get("reference", {}).get("result", {}).get("csim", {})).get("pass")), "reference_synthesis": None if x["task"] in {"T4","T7"} else x.get("reference_synthesis", {}).get("pass", x.get("reference", {}).get("result", {}).get("synthesis", x.get("reference", {}).get("result", {}).get("csynth", {})).get("pass")), "mutations_detected": sum(row["detected"] for row in x.get("mutations", x.get("mutants", []))), "mutations_total": len(x.get("mutations", x.get("mutants", [])))} for x in outcomes]}, ensure_ascii=False))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
