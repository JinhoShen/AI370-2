#!/usr/bin/env python3
"""Fixed validators for the isolated FPGA model-quality tasks.

Only this controller-facing program may choose a task and variant. Model tools
invoke a read-only wrapper with those values already fixed in the trial record.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "docs/LOCAL_MODEL_LAB/quality-corpus/v1"
OUTPUT = ROOT / "output/QUALITY_MODEL_VALIDATION"
VIVADO = Path("/home/shen/tools/Xilinx/2026.1/2026.1/Vivado")
VALID_TASKS = {f"T{i}": {"V1", "V2", "V3"} for i in range(1, 9)}


class FixtureError(RuntimeError):
    pass


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _verify_variant(task: str, variant: str) -> dict[str, str]:
    folder = CORPUS / task / variant
    manifest_path = folder / "SHA256SUMS.json"
    manifest = json.loads(manifest_path.read_text())
    actual = {}
    for path in sorted(folder.rglob("*")):
        if path.is_file() and path != manifest_path:
            actual[path.relative_to(folder).as_posix()] = _sha(path)
    if actual != manifest.get("files"):
        raise FixtureError(f"frozen corpus integrity mismatch for {task}/{variant}")
    return actual


def _vivado_env() -> dict[str, str]:
    proc = subprocess.run(
        ["/usr/bin/bash", "-c", f"source {shlex.quote(str(VIVADO / 'settings64.sh'))} >/dev/null && /usr/bin/env -0"],
        capture_output=True, timeout=30, check=True,
    )
    env = os.environ.copy()
    for item in proc.stdout.split(b"\0"):
        if b"=" in item:
            key, value = item.split(b"=", 1)
            env[key.decode()] = value.decode(errors="replace")
    return env


def _safe_workspace(path: Path) -> Path:
    workspace = path.resolve(strict=True)
    if OUTPUT.resolve() not in workspace.parents:
        raise FixtureError("workspace must be an isolated child of output/QUALITY_MODEL_VALIDATION")
    if workspace.is_symlink():
        raise FixtureError("workspace symlinks are forbidden")
    return workspace


def _run(command: list[str], cwd: Path, env: dict[str, str], timeout: int, log: Path) -> dict:
    proc = subprocess.run(command, cwd=cwd, env=env, capture_output=True, text=True, timeout=timeout)
    output = proc.stdout + "\n" + proc.stderr
    log.write_text(output)
    return {"exit_code": proc.returncode, "log": str(log), "log_sha256": hashlib.sha256(output.encode()).hexdigest(), "tail": output[-6000:]}


def _synthesize_t1(source: Path, work: Path, env: dict[str, str]) -> dict:
    work.mkdir(parents=True, exist_ok=True)
    report = work / "utilization.rpt"
    tcl = work / "fixed_synth.tcl"
    tcl.write_text(
        f"read_verilog -sv {{{source}}}\n"
        "synth_design -top axi_regs -part xc7s100fgga676-2\n"
        f"report_utilization -file {{{report}}}\n"
        "puts QUALITY_T1_SYNTH_PASS\nexit\n"
    )
    proc = subprocess.run(
        [str(VIVADO / "bin/vivado"), "-mode", "batch", "-notrace", "-source", str(tcl), "-log", str(work / "vivado.log"), "-journal", str(work / "vivado.jou")],
        cwd=work, env=env, capture_output=True, text=True, timeout=600,
    )
    output = proc.stdout + "\n" + proc.stderr
    (work / "stdout.log").write_text(proc.stdout)
    (work / "stderr.log").write_text(proc.stderr)
    log = (work / "vivado.log").read_text(errors="replace") if (work / "vivado.log").is_file() else output
    latch_lines = [line for line in log.splitlines() if re.search(r"infer(?:ring|red)? latch|latch inferred", line, re.I)]
    passed = proc.returncode == 0 and "QUALITY_T1_SYNTH_PASS" in output and report.is_file() and not latch_lines
    return {"pass": passed, "exit_code": proc.returncode, "pass_marker": "QUALITY_T1_SYNTH_PASS" in output,
            "utilization_report": str(report), "latch_diagnostics": latch_lines,
            "log_sha256": hashlib.sha256(log.encode()).hexdigest(), "tail": output[-4000:]}


def _simulate_t3(dut: Path, testbench: Path, run: Path, marker: str) -> dict:
    run.mkdir(parents=True, exist_ok=False)
    env = _vivado_env()
    rows = {}
    commands = [
        ("xvlog", [str(VIVADO / "bin/xvlog"), "--sv", "-work", "xil_defaultlib", str(dut), str(testbench)], 180),
        ("xelab", [str(VIVADO / "bin/xelab"), "xil_defaultlib.tb_axi_regs", "-s", "quality_t3_mutation"], 180),
        ("xsim", [str(VIVADO / "bin/xsim"), "quality_t3_mutation", "-runall"], 180),
    ]
    for name, command, timeout in commands:
        proc = subprocess.run(command, cwd=run, env=env, capture_output=True, text=True, timeout=timeout)
        output = proc.stdout + "\n" + proc.stderr
        log = run / f"{name}.log"
        log.write_text(output)
        rows[name] = {"exit_code": proc.returncode, "log_sha256": hashlib.sha256(output.encode()).hexdigest()}
        if proc.returncode:
            break
    sim = run / "xsim.log"
    text = sim.read_text(errors="replace") if sim.is_file() else ""
    rows["terminal_marker"] = next((line for line in text.splitlines() if line.startswith(marker)), None)
    rows["pass"] = all(rows.get(k, {}).get("exit_code") == 0 for k in ("xvlog", "xelab", "xsim")) and rows["terminal_marker"] is not None
    rows["failure_kind"] = "NONE" if rows["pass"] else ("WATCHDOG" if "watchdog" in text.lower() else "SIMULATION_OR_ASSERTION")
    rows["log_tail"] = text[-4000:]
    return rows


def _validate_t3(variant: str, workspace: Path, attempt: int, corpus_files: dict[str, str]) -> dict:
    public = workspace / "sim/tb_axi_regs.sv"
    dut = workspace / "rtl/axi_regs.sv"
    spec = workspace / "TASK_SPEC.md"
    if not public.is_file() or public.is_symlink() or not dut.is_file() or dut.is_symlink():
        raise FixtureError("T3 public testbench or fixed DUT is missing")
    expected = CORPUS / "T3" / variant / "public"
    if _sha(dut) != _sha(expected / "rtl/axi_regs.sv") or _sha(spec) != _sha(expected / "TASK_SPEC.md"):
        raise FixtureError("T3 fixed DUT or task specification changed")
    before = _sha(public)
    run = workspace / "runs" / f"attempt-{attempt}"
    run.mkdir(parents=True, exist_ok=False)
    correct_run = _simulate_t3(dut, public, run / "correct", "QUALITY_T3_PASS")
    required = {
        "QUALITY_T3_SCENARIO_reset_PASS", "QUALITY_T3_SCENARIO_aw_before_w_PASS",
        "QUALITY_T3_SCENARIO_w_before_aw_PASS", "QUALITY_T3_SCENARIO_simultaneous_PASS",
        "QUALITY_T3_SCENARIO_wstrb_PASS", "QUALITY_T3_SCENARIO_unmapped_PASS",
        "QUALITY_T3_SCENARIO_b_backpressure_PASS", "QUALITY_T3_SCENARIO_r_backpressure_PASS",
        "QUALITY_T3_SCENARIO_consecutive_PASS",
    }
    sim_text = (run / "correct/xsim.log").read_text(errors="replace") if (run / "correct/xsim.log").is_file() else ""
    observed = {line for line in sim_text.splitlines() if line in required}
    # Mutation runs and their diagnostic logs are stored in a dot-directory.
    # Workspace file tools reject hidden paths, so the model cannot inspect them.
    hidden = workspace / ".quality-hidden" / f"attempt-{attempt}"
    hidden.mkdir(parents=True, exist_ok=False)
    mutations = []
    for index, path in enumerate(sorted((CORPUS / "T3" / variant / "private/mutants").glob("*.sv")), start=1):
        mutated = _simulate_t3(path, public, hidden / f"mutation-{index}", "QUALITY_T3_PASS")
        # A compile/elaboration failure is a harness problem, not a successful
        # functional mutation catch. A proper catch is a simulation assertion
        # or finite watchdog after successful compile and elaboration.
        tools_ready = all(mutated.get(k, {}).get("exit_code") == 0 for k in ("xvlog", "xelab"))
        detected = tools_ready and not mutated.get("pass", False) and mutated.get("failure_kind") in {"WATCHDOG", "SIMULATION_OR_ASSERTION"}
        mutations.append({"id": f"M{index}", "detected": detected, "failure_kind": mutated.get("failure_kind"),
                          "compile_exit": mutated.get("xvlog", {}).get("exit_code"), "elab_exit": mutated.get("xelab", {}).get("exit_code")})
    after = _sha(public)
    mutations_pass = bool(mutations) and all(item["detected"] for item in mutations)
    passed = correct_run.get("pass", False) and observed == required and mutations_pass and before == after
    result = {
        "task": "T3", "variant": variant, "attempt": attempt,
        "status": "PASS" if passed else "FAIL",
        "xsim": {"pass": correct_run.get("pass"), "terminal_marker": correct_run.get("terminal_marker"),
                 "scenario_markers_expected": sorted(required), "scenario_markers_observed": sorted(observed),
                 "log_tail": correct_run.get("log_tail")},
        "mutation_detection": {"detected": sum(item["detected"] for item in mutations), "total": len(mutations),
                               "mutants": mutations},
        "synthesis": {"pass": True, "status": "NOT_REQUIRED_FOR_T3"},
        "source_sha256_before": before, "source_sha256_after": after,
        "source_unchanged_during_validation": before == after,
        "corpus_files_sha256": corpus_files,
    }
    (hidden / "result.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    public_result = {
        "task": "T3", "variant": variant, "attempt": attempt, "status": result["status"],
        "xsim": {"pass": correct_run.get("pass"), "terminal_marker": correct_run.get("terminal_marker"),
                 "scenario_marker_count": len(observed), "scenario_marker_total": len(required),
                 "log_tail": correct_run.get("log_tail")},
        "mutation_detection": {"detected": result["mutation_detection"]["detected"],
                               "total": result["mutation_detection"]["total"]},
        "synthesis": result["synthesis"],
        "source_unchanged_during_validation": before == after,
    }
    (run / "result.json").write_text(json.dumps(public_result, indent=2, ensure_ascii=False) + "\n")
    return result


def _validate_t4(task: str, variant: str, workspace: Path, attempt: int, corpus_files: dict[str, str]) -> dict:
    rtl = workspace / "rtl"
    files = [rtl / name for name in ("alu_pkg.sv", "alu.sv", "calc_top.sv")]
    if any(not f.is_file() or f.is_symlink() for f in files):
        raise FixtureError("T4 allowlisted multi-file RTL is missing or symlinked")
    private = CORPUS / task / variant / "private/tb_calc_top.sv"
    run = workspace / "runs" / f"attempt-{attempt}"
    run.mkdir(parents=True, exist_ok=False)
    before = {f.name: _sha(f) for f in files}
    env = _vivado_env()
    rows = {}
    commands = [
        ("xvlog", [str(VIVADO / "bin/xvlog"), "--sv", "-work", "xil_defaultlib", *(str(f) for f in files), str(private)], 180),
        ("xelab", [str(VIVADO / "bin/xelab"), "xil_defaultlib.tb_calc_top", "-s", f"quality_t4_attempt_{attempt}"], 180),
        ("xsim", [str(VIVADO / "bin/xsim"), f"quality_t4_attempt_{attempt}", "-runall"], 180),
    ]
    for name, command, timeout in commands:
        rows[name] = _run(command, run, env, timeout, run / f"{name}.log")
        if rows[name]["exit_code"]:
            break
    sim_log = (run / "xsim.log").read_text(errors="replace") if (run / "xsim.log").is_file() else ""
    marker = "QUALITY_T7_PASS" if task == "T7" else "QUALITY_T4_PASS"
    rows["terminal_marker"] = next((line for line in sim_log.splitlines() if line.startswith(marker)), None)
    rows["pass"] = all(rows.get(n, {}).get("exit_code") == 0 for n in ("xvlog", "xelab", "xsim")) and rows["terminal_marker"] is not None
    after = {f.name: _sha(f) for f in files}
    passed = rows["pass"] and before == after
    result = {"task": task, "variant": variant, "attempt": attempt, "status": "PASS" if passed else "FAIL",
              "xsim": rows, "synthesis": {"pass": True, "status": "NOT_REQUIRED_FOR_T4"},
              "source_sha256_before": before, "source_sha256_after": after,
              "source_unchanged_during_validation": before == after, "corpus_files_sha256": corpus_files,
              "hidden_assets_sha256": {"testbench": _sha(private)}}
    (run / "result.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    return result


def _validate_t5(variant: str, workspace: Path, attempt: int, corpus_files: dict[str, str]) -> dict:
    source = workspace / "rtl/mux_math.sv"
    if not source.is_file() or source.is_symlink(): raise FixtureError("T5 allowlisted RTL is missing or symlinked")
    private = CORPUS / "T5" / variant / "private/tb_mux_math.sv"
    run = workspace / "runs" / f"attempt-{attempt}"
    run.mkdir(parents=True, exist_ok=False)
    env = _vivado_env(); before = _sha(source); xsim = {}
    for name, command in [
        ("xvlog", [str(VIVADO / "bin/xvlog"), "--sv", "-work", "xil_defaultlib", str(source), str(private)]),
        ("xelab", [str(VIVADO / "bin/xelab"), "xil_defaultlib.tb_mux_math", "-s", f"quality_t5_{attempt}"]),
        ("xsim", [str(VIVADO / "bin/xsim"), f"quality_t5_{attempt}", "-runall"]),
    ]:
        xsim[name] = _run(command, run, env, 180, run / f"{name}.log")
        if xsim[name]["exit_code"]: break
    sim_log=(run / "xsim.log").read_text(errors="replace") if (run / "xsim.log").is_file() else ""
    xsim["terminal_marker"]=next((line for line in sim_log.splitlines() if line.startswith("QUALITY_T5_PASS")),None)
    xsim["pass"]=all(xsim.get(n,{}).get("exit_code")==0 for n in ("xvlog","xelab","xsim")) and bool(xsim["terminal_marker"])
    work=run/"synthesis"; work.mkdir(); report=work/"utilization.rpt"
    tcl=work/"fixed_synth.tcl"
    tcl.write_text(f"read_verilog -sv {{{source}}}\nsynth_design -top mux_math -part xc7s100fgga676-2\nreport_utilization -file {{{report}}}\nputs QUALITY_T5_SYNTH_PASS\nexit\n")
    proc=subprocess.run([str(VIVADO/"bin/vivado"),"-mode","batch","-notrace","-source",str(tcl),"-log",str(work/"vivado.log"),"-journal",str(work/"vivado.jou")],cwd=work,env=env,capture_output=True,text=True,timeout=600)
    output=proc.stdout+"\n"+proc.stderr; (work/"stdout.log").write_text(proc.stdout); (work/"stderr.log").write_text(proc.stderr)
    log=(work/"vivado.log").read_text(errors="replace") if (work/"vivado.log").is_file() else output
    latches=[line for line in log.splitlines() if re.search(r"infer(?:ring|red)? latch|latch inferred",line,re.I)]
    synthesis={"pass":proc.returncode==0 and "QUALITY_T5_SYNTH_PASS" in output and report.is_file() and not latches,
               "exit_code":proc.returncode,"pass_marker":"QUALITY_T5_SYNTH_PASS" in output,
               "utilization_report":str(report),"latch_diagnostics":latches,"log_sha256":hashlib.sha256(log.encode()).hexdigest()}
    after=_sha(source); passed=xsim["pass"] and synthesis.get("pass") is True and before==after
    result={"task":"T5","variant":variant,"attempt":attempt,"status":"PASS" if passed else "FAIL","xsim":xsim,"synthesis":synthesis,
            "source_sha256_before":before,"source_sha256_after":after,"source_unchanged_during_validation":before==after,
            "corpus_files_sha256":corpus_files,"hidden_assets_sha256":{"testbench":_sha(private)}}
    (run/"result.json").write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n")
    return result


def _vitis_env() -> dict[str, str]:
    settings=Path("/home/shen/tools/Xilinx/2026.1/2026.1/Vitis/settings64.sh")
    proc=subprocess.run(["/usr/bin/bash","-c",f"source {shlex.quote(str(settings))} >/dev/null && /usr/bin/env -0"],capture_output=True,timeout=45,check=True)
    env=os.environ.copy()
    for item in proc.stdout.split(b"\0"):
        if b"=" in item:
            k,v=item.split(b"=",1); env[k.decode()]=v.decode(errors="replace")
    return env


def _validate_t6(variant: str, workspace: Path, attempt: int, corpus_files: dict[str, str]) -> dict:
    source=workspace/"src/invert32.cpp"; config=workspace/"hls_config.cfg"
    private=CORPUS/"T6"/variant/"private/testbench.cpp"
    if any(not p.is_file() or p.is_symlink() for p in (source,config)): raise FixtureError("T6 public source/config missing or symlinked")
    hidden=workspace/".quality-hidden"/f"attempt-{attempt}"; hidden.mkdir(parents=True,exist_ok=False)
    project=hidden/"project"; (project/"src").mkdir(parents=True)
    shutil.copy2(source,project/"src/invert32.cpp"); shutil.copy2(private,project/"src/testbench.cpp")
    base=json.loads(json.dumps(corpus_files))
    (project/"hls_config.cfg").write_text(config.read_text()+"tb.file=src/testbench.cpp\n")
    public_before={"source":_sha(source),"config":_sha(config)}
    env=_vitis_env(); csim_dir=hidden/"csim"; synth_dir=hidden/"csynth"
    csim=subprocess.run(["vitis-run","--mode","hls","--csim","--config",str(project/"hls_config.cfg"),"--work_dir",str(csim_dir)],cwd=project,env=env,capture_output=True,text=True,timeout=900)
    csim_text=csim.stdout+"\n"+csim.stderr
    (hidden/"csim.log").write_text(csim_text)
    marker=next((line for line in csim_text.splitlines() if line.startswith("QUALITY_T6_CSIM_PASS")),None)
    csim_pass=csim.returncode==0 and marker is not None
    synth=subprocess.run(["v++","-c","--mode","hls","--part","xc7s100fgga676-2","--config",str(project/"hls_config.cfg"),"--work_dir",str(synth_dir)],cwd=project,env=env,capture_output=True,text=True,timeout=1200)
    synth_text=synth.stdout+"\n"+synth.stderr; (hidden/"csynth.log").write_text(synth_text)
    reports=list(synth_dir.rglob("invert32_csynth.rpt"))+list(synth_dir.rglob("csynth.rpt"))
    synth_pass=synth.returncode==0 and bool(reports)
    public_after={"source":_sha(source),"config":_sha(config)}
    passed=csim_pass and synth_pass and public_before==public_after
    result={"task":"T6","variant":variant,"attempt":attempt,"status":"PASS" if passed else "FAIL",
            "csim":{"pass":csim_pass,"exit_code":csim.returncode,"terminal_marker":marker,"log_sha256":hashlib.sha256(csim_text.encode()).hexdigest()},
            "csim_diagnostic":None if csim_pass else "Fixed C simulation completed with a vector mismatch against the frozen bitwise-complement specification.",
            "csynth":{"pass":synth_pass,"exit_code":synth.returncode,"reports":[str(p.relative_to(hidden)) for p in reports],"log_sha256":hashlib.sha256(synth_text.encode()).hexdigest()},
            "public_source_sha256_before":public_before,"public_source_sha256_after":public_after,"source_unchanged_during_validation":public_before==public_after,
            "corpus_files_sha256":base}
    (hidden/"result.json").write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n")
    safe={"task":"T6","variant":variant,"attempt":attempt,"status":result["status"],"csim":{"pass":csim_pass,"terminal_marker":marker},"csim_diagnostic":result["csim_diagnostic"],"csynth":{"pass":synth_pass,"report_count":len(reports)},"source_unchanged_during_validation":public_before==public_after}
    public_run=workspace/"runs"/f"attempt-{attempt}"; public_run.mkdir(parents=True,exist_ok=False)
    (public_run/"result.json").write_text(json.dumps(safe,indent=2,ensure_ascii=False)+"\n")
    return result


def validate(task: str, variant: str, workspace_arg: Path, attempt: int) -> dict:
    if task not in VALID_TASKS or variant not in VALID_TASKS[task]:
        raise FixtureError("task/variant pair is not in the frozen corpus allowlist")
    asset_hashes = _verify_variant(task, variant)
    if not 1 <= attempt <= 3:
        raise FixtureError("attempt must be 1..3")
    workspace = _safe_workspace(workspace_arg)
    if task == "T3":
        return _validate_t3(variant, workspace, attempt, asset_hashes)
    if task in {"T4", "T7"}:
        return _validate_t4(task, variant, workspace, attempt, asset_hashes)
    if task == "T5":
        return _validate_t5(variant, workspace, attempt, asset_hashes)
    if task == "T6":
        return _validate_t6(variant, workspace, attempt, asset_hashes)
    source = workspace / "rtl/axi_regs.sv"
    if not source.is_file() or source.is_symlink():
        raise FixtureError("allowlisted T1 source is missing or a symlink")
    private = CORPUS / task / variant / "private"
    tb = private / "tb_axi_regs.sv"
    if not tb.is_file():
        raise FixtureError("frozen hidden testbench is missing")
    run = workspace / "runs" / f"attempt-{attempt}"
    run.mkdir(parents=True, exist_ok=False)
    env = _vivado_env()
    before = _sha(source)
    xsim_result = {}
    commands = [
        ("xvlog", [str(VIVADO / "bin/xvlog"), "--sv", "-work", "xil_defaultlib", str(source), str(tb)], 180),
        ("xelab", [str(VIVADO / "bin/xelab"), "xil_defaultlib.tb_axi_regs", "-s", f"quality_attempt_{attempt}"], 180),
        ("xsim", [str(VIVADO / "bin/xsim"), f"quality_attempt_{attempt}", "-runall"], 180),
    ]
    for name, command, timeout in commands:
        xsim_result[name] = _run(command, run, env, timeout, run / f"{name}.log")
        if xsim_result[name]["exit_code"]:
            break
    sim_log = (run / "xsim.log").read_text(errors="replace") if (run / "xsim.log").is_file() else ""
    expected_marker = "QUALITY_T8_PASS" if task == "T8" else "QUALITY_T1_PASS"
    terminal = next((line for line in sim_log.splitlines() if line.startswith(expected_marker)), None)
    xsim_result["terminal_marker"] = terminal
    xsim_result["pass"] = all(xsim_result.get(name, {}).get("exit_code") == 0 for name in ("xvlog", "xelab", "xsim")) and terminal is not None
    synth_result = _synthesize_t1(source, run / "synthesis", env) if xsim_result["pass"] else {"pass": False, "status": "SKIPPED_UNTIL_XSIM_PASS"}
    after = _sha(source)
    # As for T3-T6, a source edited while the fixed validators ran cannot PASS.
    result = {"task": task, "variant": variant, "attempt": attempt,
              "status": "PASS" if xsim_result["pass"] and synth_result.get("pass") and before == after else "FAIL",
              "xsim": xsim_result, "synthesis": synth_result,
              "source_sha256_before": before, "source_sha256_after": after,
              "source_unchanged_during_validation": before == after,
              "corpus_files_sha256": asset_hashes,
              "hidden_assets_sha256": {"testbench": _sha(tb), "reference": _sha(private / "reference_axi_regs.sv")}}
    (run / "result.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task", choices=sorted(VALID_TASKS), required=True)
    parser.add_argument("--variant", required=True)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--attempt", type=int, required=True)
    args = parser.parse_args()
    try:
        result = validate(args.task, args.variant, args.workspace, args.attempt)
    except Exception as exc:
        print(json.dumps({"status": "HARNESS_INVALID", "error": f"{type(exc).__name__}: {exc}"}, ensure_ascii=False))
        return 2
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
