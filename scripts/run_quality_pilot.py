#!/usr/bin/env python3
"""Run frozen, guarded FPGA model-quality cycles until the stop marker exists."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import re
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/"output/QUALITY_MODEL_VALIDATION"
SESSION="20261022T182952+0800"
MODEL_INTEGRITY=BASE/SESSION/"model-integrity.json"
CORPUS=ROOT/"docs/LOCAL_MODEL_LAB/quality-corpus/v1"
PORT=18082
STOP_FILE=BASE/"STOP"
TASKS=[f"T{i}" for i in range(1,9)]
VARIANTS=["V1","V2","V3"]
FAULT_RE=re.compile(r"amdgpu.*(?:page fault|GPU reset|ring.*timeout|device lost)|TTM.*(?:corrupt|error)|soft lockup|Out of memory: Killed process|oom-kill",re.I)


def controller_stop_reason() -> str | None:
    """Read an explicit supervisor stop cause, if the parent owns this stop.

    SIGINT alone is ambiguous (it can be Ctrl+C or a supervisor interrupt), so
    the controller supplies a small immutable sidecar before signalling us.
    """
    raw = os.environ.get("AI370_CONTROLLER_STOP_FILE")
    if not raw:
        return None
    try:
        value = json.loads(Path(raw).read_text())
        reason = value.get("reason")
        return str(reason) if reason else "CONTROLLER_SAFETY_STOP"
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None


def sha(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda:f.read(4*1024*1024),b""): h.update(block)
    return h.hexdigest()

def meminfo()->dict[str,int]:
    return {l.split(":")[0]:int(l.split()[1]) for l in Path("/proc/meminfo").read_text().splitlines() if l.endswith(" kB")}

def vmstat()->dict[str,int]:
    wanted={"pswpin","pswpout"}
    return {l.split()[0]:int(l.split()[1]) for l in Path("/proc/vmstat").read_text().splitlines() if l.split()[0] in wanted}

def psi_full()->float:
    for line in Path("/proc/pressure/memory").read_text().splitlines():
        if line.startswith("full "): return float(next(x.split("=")[1] for x in line.split() if x.startswith("avg10=")))
    raise RuntimeError("memory PSI full line unavailable")

def kernel_audit(since:str)->dict:
    p=subprocess.run(["journalctl","-k","--since",since,"--no-pager","-o","short-iso"],capture_output=True,text=True,timeout=20)
    return {"read_exit":p.returncode,"faults":[line for line in p.stdout.splitlines() if FAULT_RE.search(line)],"stderr":p.stderr[-1000:]}

def http_json(url:str, payload:dict|None=None, timeout:float=5)->dict:
    data=None if payload is None else json.dumps(payload).encode()
    req=urllib.request.Request(url,data=data,headers={"Content-Type":"application/json"} if data else {})
    with urllib.request.urlopen(req,timeout=timeout) as response: return json.loads(response.read().decode())

def preflight(seconds:int, record_path:Path, ross_url:str|None)->dict:
    start=datetime.now(timezone.utc); start_iso=start.strftime("%Y-%m-%d %H:%M:%S UTC")
    baseline=meminfo(); base_vm=vmstat(); disk=__import__("shutil").disk_usage(ROOT).free
    p={"started_utc":start_iso,"duration_requested_seconds":seconds,"swapfree_2gib_waived_by_user":True,
       "baseline":{"meminfo_kib":baseline,"vmstat_pages":base_vm,"disk_free_bytes":disk},
       "samples":[],"blockers":[],"ross_docsearch_endpoint_configured":bool(ross_url)}
    try:
        info=subprocess.run(["vulkaninfo","--summary"],capture_output=True,text=True,timeout=45)
        combined=info.stdout+info.stderr
        p["vulkaninfo"]={"exit_code":info.returncode,"summary":combined[-8000:]}
        if info.returncode or "deviceName" not in combined: p["blockers"].append("VULKAN_DEVICE_UNVERIFIED")
    except Exception as e: p["vulkaninfo"]={"error":f"{type(e).__name__}: {e}"};p["blockers"].append("VULKAN_DEVICE_UNVERIFIED")
    try:
        a=kernel_audit(start_iso);p["initial_kernel_audit"]=a
        if a["read_exit"]:p["blockers"].append("KERNEL_AUDIT_UNREADABLE")
        if a["faults"]:p["blockers"].append("GPU_KERNEL_FAULT")
    except Exception as e:p["initial_kernel_audit"]={"error":f"{type(e).__name__}: {e}"};p["blockers"].append("KERNEL_AUDIT_UNREADABLE")
    try:
        p["lemonade_health"]=http_json("http://127.0.0.1:13305/api/v1/health")
        with urllib.request.urlopen("http://127.0.0.1:13305/health",timeout=5) as response:
            p["local_ui"]={"url":"http://127.0.0.1:13305/health","status":response.status}
            if response.status!=200:p["blockers"].append("LOCAL_UI_HEALTH_UNAVAILABLE")
    except Exception as e:
        p["lemonade_health"]={"error":f"{type(e).__name__}: {e}"};p["blockers"].append("LEMONADE_HEALTH_UNAVAILABLE")
    processes=[]
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():continue
        try:
            command=(entry/"cmdline").read_bytes().replace(b"\0",b" ").decode(errors="ignore")
            if "llama-server" in command or "lemonade" in command:
                processes.append({"pid":int(entry.name),"command_summary":command[:400]})
        except OSError:continue
    p["existing_model_services"]=processes
    if disk<20*1024**3:p["blockers"].append("DISK_BELOW_20_GIB")
    if baseline["MemAvailable"]<max(8*1024**2,baseline["MemTotal"]//5):p["blockers"].append("MEMAVAILABLE_BELOW_START_THRESHOLD")
    # SwapFree <2 GiB alone is explicitly waived; live swap activity remains gated.
    p["swapfree_kib"]=baseline["SwapFree"]
    previous_psi=psi_full(); psi_high=False;psi_high_samples=0
    deadline=time.monotonic()+seconds
    while time.monotonic()<deadline:
        if controller_stop_reason():p["blockers"].append("CONTROLLER_SAFETY_STOP_DURING_PREFLIGHT");break
        if STOP_FILE.exists():p["blockers"].append("USER_STOP_DURING_PREFLIGHT");break
        time.sleep(min(10,max(0,deadline-time.monotonic())))
        current=meminfo();vm=vmstat();psi=psi_full()
        sample={"elapsed_seconds":round(seconds-(deadline-time.monotonic()),1),"memavailable_kib":current["MemAvailable"],
                "swapfree_kib":current["SwapFree"],"pswpin_delta_pages":vm["pswpin"]-base_vm["pswpin"],
                "pswpout_delta_pages":vm["pswpout"]-base_vm["pswpout"],"psi_full_avg10":psi,
                "disk_free_bytes":__import__("shutil").disk_usage(ROOT).free}
        p["samples"].append(sample)
        if current["MemAvailable"]<max(8*1024**2,current["MemTotal"]//5):p["blockers"].append("MEMAVAILABLE_BELOW_START_THRESHOLD")
        page_size=os.sysconf("SC_PAGE_SIZE")
        swapin_bytes=(vm["pswpin"]-base_vm["pswpin"])*page_size
        swapout_bytes=(vm["pswpout"]-base_vm["pswpout"])*page_size
        if swapin_bytes>=1024**2:p["blockers"].append("SWAPIN_DURING_PREFLIGHT")
        # A small global swap-out can occur during normal desktop activity.
        # Block only substantial, corroborated pressure; all raw samples stay
        # in preflight.json for later review.
        if swapout_bytes>=16*1024**2 and (swapin_bytes>=1024**2 or psi>=20.0):
            p["blockers"].append("CORROBORATED_SWAP_PRESSURE_PREFLIGHT")
        psi_high_samples=psi_high_samples+1 if psi>=20.0 else 0
        if psi_high_samples>=2:psi_high=True
        previous_psi=psi
        if sample["disk_free_bytes"]<20*1024**3:p["blockers"].append("DISK_BELOW_20_GIB")
    if psi_high:p["blockers"].append("MEMORY_PSI_PREFLIGHT")
    try:
        a=kernel_audit(start_iso);p["final_kernel_audit"]=a
        if a["read_exit"]:p["blockers"].append("KERNEL_AUDIT_UNREADABLE")
        if a["faults"]:p["blockers"].append("GPU_KERNEL_FAULT")
    except Exception as e:p["final_kernel_audit"]={"error":f"{type(e).__name__}: {e}"};p["blockers"].append("KERNEL_AUDIT_UNREADABLE")
    sock=socket.socket()
    try:
        sock.bind(("127.0.0.1",PORT))
    except OSError:p["blockers"].append("QUALITY_MODEL_PORT_BUSY")
    finally:sock.close()
    p["blockers"]=sorted(set(p["blockers"]))
    p["status"]="PASS" if not p["blockers"] else "PREFLIGHT_BLOCKED"
    p["finished_utc"]=datetime.now(timezone.utc).isoformat()
    record_path.parent.mkdir(parents=True,exist_ok=True);record_path.write_text(json.dumps(p,indent=2,ensure_ascii=False)+"\n")
    return p

def model_server_command(model:dict,threads:int)->list[str]:
    return [str(ROOT/"output/M6/build-vulkan/bin/llama-server"),"-m",model["path"],"--alias",model["model"],
            "--host","127.0.0.1","--port",str(PORT),"--offline","--log-verbosity","5","--ctx-size","16384",
            "--threads",str(threads),"--threads-batch",str(threads),"--n-gpu-layers","99","--device","Vulkan0",
            "--parallel","1","--reasoning","off","--jinja","--metrics","--batch-size","2048","--ubatch-size","512"]

def server_binary_details()->dict:
    binary=ROOT/"output/M6/build-vulkan/bin/llama-server"
    proc=subprocess.run([str(binary),"--version"],capture_output=True,text=True,timeout=20)
    return {"path":str(binary),"sha256":sha(binary),"version_exit_code":proc.returncode,
            "version":(proc.stdout+proc.stderr).strip()[:1000]}

def stop_owned_server(server:subprocess.Popen|None)->None:
    if server is None or server.poll() is not None:return
    try:os.killpg(server.pid,signal.SIGINT)
    except ProcessLookupError:return
    try:server.wait(timeout=25)
    except subprocess.TimeoutExpired:
        try:os.killpg(server.pid,signal.SIGKILL)
        except ProcessLookupError:pass
        server.wait()

def launch_server(model:dict,model_dir:Path,threads:int,stop_event)->tuple[subprocess.Popen|None,dict]:
    if sha(Path(model["path"]))!=model["sha256"]:return None,{"status":"BLOCKED","reason":"MODEL_SHA256_MISMATCH"}
    mem=meminfo();base_swap=mem["SwapTotal"]-mem["SwapFree"];base_vm=vmstat();started=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    command=model_server_command(model,threads);(model_dir/"server-command.json").write_text(json.dumps(command,indent=2)+"\n")
    log=(model_dir/"server.log").open("w")
    server=subprocess.Popen(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,start_new_session=True);log.close()
    deadline=time.monotonic()+240;reason=None;last_audit=0;pressure_since=None;load_samples=[]
    while time.monotonic()<deadline:
        if stop_event or STOP_FILE.exists():reason="USER_STOP";break
        if server.poll() is not None:reason="MODEL_SERVER_EXIT";break
        now=time.monotonic();cur=meminfo();swap=cur["SwapTotal"]-cur["SwapFree"];vm=vmstat();psi=psi_full()
        swapin_bytes=(vm["pswpin"]-base_vm["pswpin"])*os.sysconf("SC_PAGE_SIZE")
        swapout_bytes=(vm["pswpout"]-base_vm["pswpout"])*os.sysconf("SC_PAGE_SIZE")
        load_samples.append({"elapsed_seconds":round(now-(deadline-240),2),"memavailable_kib":cur["MemAvailable"],
                             "swap_growth_kib":swap-base_swap,"swapin_bytes":swapin_bytes,
                             "swapout_bytes":swapout_bytes,"psi_full_avg10":psi})
        if cur["MemAvailable"]<max(6*1024**2,cur["MemTotal"]//8):reason="MEMAVAILABLE_GUARD_LOAD";break
        # Swap growth alone is global and may come from normal desktop cache
        # reclamation. Require sustained active pressure before stopping model
        # load, because these counters cannot attribute activity to this model.
        pressure=(swap-base_swap>64*1024 and (swapin_bytes>=1024**2 or psi>=20.0))
        pressure_since=pressure_since or now if pressure else None
        if pressure_since is not None and now-pressure_since>=10:
            reason="SUSTAINED_CORROBORATED_SWAP_PRESSURE_GUARD_LOAD";break
        if now-last_audit>10:
            audit=kernel_audit(started);last_audit=now
            if audit["read_exit"]:reason="KERNEL_AUDIT_UNREADABLE";break
            if audit["faults"]:reason="GPU_KERNEL_FAULT";break
        try:
            health=http_json(f"http://127.0.0.1:{PORT}/health")
            if health.get("status")=="ok":
                text=(model_dir/"server.log").read_text(errors="replace")
                layers=re.findall(r"offloaded\s+(\d+)/(\d+)\s+layers to GPU",text)
                if layers and int(layers[-1][0])>0 and int(layers[-1][0])==int(layers[-1][1]):
                    patterns={"architecture":r"general\.architecture\s+str\s+=\s+(.+)","name":r"general\.name\s+str\s+=\s+(.+)",
                              "file_type":r"file type\s*=\s*(.+)","model_type":r"model type\s*=\s*(.+)","model_params":r"model params\s*=\s*(.+)"}
                    metadata={k:re.findall(pattern,text)[-1].strip() for k,pattern in patterns.items() if re.findall(pattern,text)}
                    return server,{"status":"LOADED","health":health,"gpu_offload_layers":layers[-1],"model_metadata_from_load_log":metadata,"resource_samples":load_samples,
                                   "server_log_sha256":sha(model_dir/"server.log"),"command":command}
        except (OSError,ValueError,urllib.error.URLError):pass
        time.sleep(1)
    stop_owned_server(server)
    return None,{"status":"BLOCKED","reason":reason or "MODEL_LOAD_TIMEOUT","resource_samples":load_samples}

def write_sample_blocked(path:Path,model:str,task:str,variant:str,reason:str)->dict:
    path.mkdir(parents=True,exist_ok=True)
    value={"model":model,"task":task,"variant":variant,"status":"BLOCKED","reason":reason,"formal_sample":True}
    (path/"sample-result.json").write_text(json.dumps(value,indent=2,ensure_ascii=False)+"\n");return value

def write_sample_not_tested(path:Path,model:str,task:str,variant:str,reason:str)->dict:
    path.mkdir(parents=True,exist_ok=True)
    value={"model":model,"task":task,"variant":variant,"status":"NOT_TESTED","reason":reason,"formal_sample":False}
    (path/"sample-result.json").write_text(json.dumps(value,indent=2,ensure_ascii=False)+"\n");return value

def build_execution_plan(models:list[dict],tasks:list[str],variants:list[str],seed:int)->dict:
    """Build a deterministic variant-major matrix so every model sees each common variant."""
    model_ids=[m["model"] for m in models]
    if not model_ids or len(model_ids)!=len(set(model_ids)):
        raise ValueError("model roster must be non-empty and have unique model IDs")
    if not tasks or len(tasks)!=len(set(tasks)):
        raise ValueError("task list must be non-empty and unique")
    if not variants or len(variants)!=len(set(variants)):
        raise ValueError("variant list must be non-empty and unique")
    model_order=model_ids.copy();random.Random(seed).shuffle(model_order)
    task_order=tasks.copy();random.Random(seed+7919).shuffle(task_order)
    by_variant={};entries=[]
    for variant_index,variant in enumerate(variants):
        model_shift=variant_index % len(model_order)
        task_shift=variant_index % len(task_order)
        variant_models=model_order[model_shift:]+model_order[:model_shift]
        variant_tasks=task_order[task_shift:]+task_order[:task_shift]
        by_variant[variant]={"model_order":variant_models,"task_order":variant_tasks}
        entries.extend({"variant":variant,"model":model,"task":task}
                       for model in variant_models for task in variant_tasks)
    return {"variant_order":variants.copy(),"model_order":model_order,"task_order":task_order,
            "by_variant":by_variant,"entries":entries,"expected_sample_count":len(model_ids)*len(tasks)*len(variants)}

def write_cycle_report(cycle_dir:Path,cycle:dict)->Path:
    rows=cycle.get("samples",[]); models=cycle.get("model_order",[]); tasks=cycle.get("task_order",TASKS)
    counts={name:sum(r.get("status")==name for r in rows) for name in ("PASS","FAIL","BLOCKED","PARTIAL","HARNESS_INVALID","NOT_TESTED")}
    lines=[f"# {cycle.get('cycle')} FPGA model-quality report","",f"Stage: **{cycle.get('stage','FULL_CYCLE')}**",f"Status: **{cycle.get('status','RUNNING')}**",
           f"Samples recorded: **{len(rows)} / {cycle.get('expected_sample_count','unknown')}**",f"Seed: `{cycle.get('seed')}`","",
           "Each cell is `PASS / FAIL / BLOCKED / PARTIAL / HARNESS_INVALID / NOT_TESTED` across the scheduled shared variants.","",
           "| Result | Count |","|---|---:|",*[f"| {name} | {counts[name]} |" for name in counts],"",
           "| Model | "+" | ".join(tasks)+" | Pass | Fail | Blocked | Partial | Harness invalid | Not tested |",
           "|---|"+"|".join(["---"]*(len(tasks)+6))+"|"]
    for model in models:
        cells=[]; counts={"PASS":0,"FAIL":0,"BLOCKED":0,"PARTIAL":0,"NOT_TESTED":0}
        mr=[r for r in rows if r.get("model")==model]
        for row in mr: counts[row.get("status","NOT_TESTED")]=counts.get(row.get("status","NOT_TESTED"),0)+1
        for task in tasks:
            tr=[r for r in mr if r.get("task")==task]
            cells.append("/".join(str(sum(r.get("status")==s for r in tr)) for s in ("PASS","FAIL","BLOCKED","PARTIAL","HARNESS_INVALID","NOT_TESTED")))
        lines.append("| `"+model+"` | "+" | ".join(cells)+f" | {counts['PASS']} | {counts['FAIL']} | {counts['BLOCKED']} | {counts['PARTIAL']} | {counts.get('HARNESS_INVALID',0)} | {counts['NOT_TESTED']} |")
    lines += ["","## Notes","",f"T7 Ross endpoint available: **{bool(cycle.get('ross_endpoint_available'))}**.","","Detailed trace, validator logs, resource samples, and source hashes are stored beside each sample's `sample-result.json`.",""]
    path=cycle_dir/"REPORT.md";path.write_text("\n".join(lines));return path

def run_one_sample(model:dict,task:str,variant:str,cycle_dir:Path,server:subprocess.Popen,ross_url:str|None,session_name:str)->dict:
    model_key=model["model"].replace("/","_")
    sample_dir=cycle_dir/"samples"/model_key/task/variant
    sample_dir.mkdir(parents=True,exist_ok=True)
    if task=="T7" and not ross_url:
        return write_sample_blocked(sample_dir,model["model"],task,variant,"ROSS_MCP_ENDPOINT_UNAVAILABLE")
    prepared=subprocess.run([sys.executable,str(ROOT/"scripts/prepare_quality_workspace.py"),"--task",task,"--variant",variant,
                             "--session",session_name,"--model",model_key],cwd=ROOT,capture_output=True,text=True,timeout=120)
    if prepared.returncode:
        value={"model":model["model"],"task":task,"variant":variant,"status":"HARNESS_INVALID",
               "reason":"WORKSPACE_PREPARATION_FAILED: "+prepared.stderr[-1000:],"formal_sample":True}
        (sample_dir/"sample-result.json").write_text(json.dumps(value,indent=2,ensure_ascii=False)+"\n")
        return value
    protocol=json.loads(prepared.stdout.splitlines()[-1]);workspace=Path(protocol["workspace"])
    config={"task":task,"variant":variant,"model":model["model"],"workspace":str(workspace),"editable_paths":protocol["editable_paths"],"cycle":cycle_dir.name}
    config_path=sample_dir/"controller.json";config_path.write_text(json.dumps(config,indent=2)+"\n")
    artifacts=sample_dir/"guarded";cmd=[sys.executable,str(ROOT/"scripts/run_quality_guarded_trial.py"),"--quality-agent","--config",str(config_path),
          "--output",str(artifacts),"--model",model["model"],"--model-path",model["path"],"--server-pid",str(server.pid),
          "--stop-file",str(STOP_FILE),"--timeout","2700"]
    if ross_url:cmd += ["--ross-docsearch-url",ross_url]
    begin=time.monotonic();proc=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True,timeout=2800)
    summary={"model":model["model"],"task":task,"variant":variant,"elapsed_seconds":round(time.monotonic()-begin,2),
             "guarded_returncode":proc.returncode,"stdout":proc.stdout[-3000:],"stderr":proc.stderr[-3000:]}
    guarded=artifacts/"guarded-result.json"
    if guarded.is_file():
        summary["guarded_result"]=json.loads(guarded.read_text())
        summary["status"]=summary["guarded_result"].get("sample_status","HARNESS_INVALID")
        if summary["status"] not in {"PASS","FAIL","BLOCKED","PARTIAL","HARNESS_INVALID"}:
            summary["status"]="HARNESS_INVALID"
    else:
        summary["status"]="BLOCKED" if STOP_FILE.exists() else "HARNESS_INVALID"
        summary["reason"]="GUARDED_CONTROLLER_DID_NOT_WRITE_RESULT"
    summary["formal_sample"]=True
    (sample_dir/"sample-result.json").write_text(json.dumps(summary,indent=2,ensure_ascii=False)+"\n")
    return summary

def roster()->list[dict]:
    result=[]
    for row in json.loads(MODEL_INTEGRITY.read_text()):
        result.append({"model":row["model"],"path":row["path"],"sha256":row["sha256"],"bytes":row["bytes"],"backend":row.get("backend","vulkan")})
    return result

def main()->int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preflight-seconds",type=int,default=300,help="read-only preflight duration; must be at least 300 seconds")
    parser.add_argument("--pilot-only",action="store_true",help="run one shared V1 pilot matrix: 9 models × T1–T8 (72 samples), then stop")
    parser.add_argument("--variants", nargs="+", choices=VARIANTS, help="shared frozen variants to run; use only after a reviewed post-Pilot plan")
    parser.add_argument("--tasks", nargs="+", choices=TASKS, help="frozen task subset for an explicitly identified follow-up session")
    parser.add_argument("--max-cycles",type=int,default=0,help="0 repeats until the stop marker exists")
    args=parser.parse_args()
    if args.preflight_seconds<300:parser.error("preflight must be at least 300 seconds")
    if args.max_cycles<0:parser.error("--max-cycles must be zero or a positive integer")
    if args.pilot_only and args.max_cycles not in {0,1}:parser.error("--pilot-only always runs exactly one V1 matrix")
    if args.pilot_only and args.variants:parser.error("--pilot-only fixes the matrix to V1; do not pass --variants")
    if args.pilot_only and args.tasks:parser.error("--pilot-only fixes the matrix to T1-T8; do not pass --tasks")
    if STOP_FILE.exists():print(json.dumps({"status":"USER_STOP_PRESENT","stop_file":str(STOP_FILE)}));return 0
    run_id=datetime.now().strftime("%Y%m%dT%H%M%S%z");root=BASE/run_id;root.mkdir(parents=True,exist_ok=False)
    models=roster();threads=len(os.sched_getaffinity(0))
    server_details=server_binary_details()
    ross_url=os.environ.get("AI370_ROSS_DOCSEARCH_URL")
    preflight_path=root/"preflight.json"
    pre=preflight(args.preflight_seconds,preflight_path,ross_url)
    if pre["status"]!="PASS":
        blocked={"stage":"QUALITY_MODEL_VALIDATION","status":"PREFLIGHT_BLOCKED","formal_tests":"NOT_STARTED","formal_sample_count":0,
                 "session":str(root.relative_to(ROOT)),"preflight_report":str(preflight_path.relative_to(ROOT)),"blocking_gaps":pre.get("blockers",[]),
                 "ross_endpoint_available":bool(ross_url)}
        (BASE/"status.json").write_text(json.dumps(blocked,indent=2,ensure_ascii=False)+"\n")
        print(json.dumps({"status":"PREFLIGHT_BLOCKED","report":str(preflight_path),"blockers":pre.get("blockers")},ensure_ascii=False),flush=True);return 2
    index={m["model"]:m for m in models}
    status={"stage":"QUALITY_MODEL_VALIDATION","status":"RUNNING","formal_tests":"RUNNING","formal_sample_count":0,"scored_sample_count":0,
            "session":str(root.relative_to(ROOT)),"threads":threads,"ross_endpoint_available":bool(ross_url),"cycles":[]}
    (BASE/"status.json").write_text(json.dumps(status,indent=2,ensure_ascii=False)+"\n")
    cycle_num=1
    cycle_limit=1 if args.pilot_only else args.max_cycles
    variants=["V1"] if args.pilot_only else (args.variants or VARIANTS)
    selected_tasks=TASKS if args.pilot_only else (args.tasks or TASKS)
    try:
        while not STOP_FILE.exists() and (cycle_limit==0 or cycle_num<=cycle_limit):
            cycle_name=f"cycle-{cycle_num:04d}";cycle_dir=root/cycle_name;cycle_dir.mkdir()
            seed=20261022+cycle_num;plan=build_execution_plan(models,selected_tasks,variants,seed)
            order=plan["model_order"];tasks=plan["task_order"];entries=plan["entries"]
            cycle={"cycle":cycle_name,"stage":"P1_PILOT" if args.pilot_only else ("T7_SUPPLEMENT" if selected_tasks==["T7"] else "FULL_CYCLE"),"seed":seed,
                   "variant_order":variants,"model_order":order,"task_order":tasks,
                   "model_order_by_variant":{k:v["model_order"] for k,v in plan["by_variant"].items()},
                   "task_order_by_variant":{k:v["task_order"] for k,v in plan["by_variant"].items()},
                   "expected_sample_count":plan["expected_sample_count"],"status":"RUNNING",
                   "ross_endpoint_available":bool(ross_url),"samples":[]}
            status["current_cycle"]={"cycle":cycle_name,"stage":cycle["stage"],"variant_order":variants,
                                     "model_order_by_variant":cycle["model_order_by_variant"],
                                     "task_order_by_variant":cycle["task_order_by_variant"],
                                     "expected_sample_count":cycle["expected_sample_count"]}
            (cycle_dir/"protocol.json").write_text(json.dumps({"schema_version":1,"cycle":cycle_name,"stage":cycle["stage"],"seed":seed,"variant_order":variants,
                "models":[{k:m[k] for k in ("model","path","sha256","bytes","backend")} for m in models],"model_order":order,
                "model_order_by_variant":cycle["model_order_by_variant"],"task_order_by_variant":cycle["task_order_by_variant"],
                "execution_order":entries,"expected_sample_count":cycle["expected_sample_count"],"context":16384,"threads":threads,"parallel":1,"batch":2048,"ubatch":512,
                "temperature":0.0,"request_seed":20261022,"reasoning":"off",
                "max_completion_tokens":8192,"tool_call_cap":14,"request_timeout_seconds":600,"sample_timeout_seconds":2700,
                "llama_server":server_details,"gguf_identity_source":"model-integrity.json full-byte SHA256; architecture, quantization and parameter count captured from the actual load log",
                "pilot_t7_endpoint":bool(ross_url),"stop_file":str(STOP_FILE)},indent=2,ensure_ascii=False)+"\n")
            stop_cycle=False;blocked_models={};server=None;current_key=None;next_index=0
            def record(row:dict, formal:bool=True)->None:
                nonlocal status
                row.setdefault("formal_sample",formal)
                cycle["samples"].append(row)
                if row.get("formal_sample"):
                    status["formal_sample_count"]+=1
                    if row.get("status") in {"PASS","FAIL","PARTIAL"}:status["scored_sample_count"]+=1
                with (cycle_dir/"samples.jsonl").open("a") as stream:
                    stream.write(json.dumps({k:row.get(k) for k in ("model","task","variant","status","reason","elapsed_seconds","formal_sample")},ensure_ascii=False)+"\n")
                (cycle_dir/"cycle-status.json").write_text(json.dumps(cycle,indent=2,ensure_ascii=False)+"\n")
                (BASE/"status.json").write_text(json.dumps(status,indent=2,ensure_ascii=False)+"\n")
                print(json.dumps({"cycle":cycle_name,"model":row.get("model"),"task":row.get("task"),"variant":row.get("variant"),"status":row.get("status")},ensure_ascii=False),flush=True)
            try:
                for entry_index,entry in enumerate(entries):
                    next_index=entry_index
                    variant,model_id,task=entry["variant"],entry["model"],entry["task"]
                    model=next(m for m in models if m["model"]==model_id)
                    model_key=model_id.replace("/","_")
                    sample_dir=cycle_dir/"samples"/model_key/task/variant
                    supervisor_reason = controller_stop_reason()
                    if supervisor_reason:
                        stop_cycle=True;status["status"]="SAFETY_STOP";status["formal_tests"]="STOPPED_BY_CONTROLLER_SAFETY_GATE";break
                    if STOP_FILE.exists():
                        stop_cycle=True;status["status"]="STOPPED_BY_USER";status["formal_tests"]="STOPPED";break
                    key=(variant,model_id)
                    if key!=current_key:
                        stop_owned_server(server);server=None;current_key=key
                        if model_id not in blocked_models:
                            model_dir=cycle_dir/"models"/model_key/variant
                            model_dir.mkdir(parents=True,exist_ok=True)
                            server,load=launch_server(model,model_dir,threads,STOP_FILE.exists())
                            (model_dir/"load-result.json").write_text(json.dumps(load,indent=2,ensure_ascii=False)+"\n")
                            if server is None:
                                reason=load.get("reason","MODEL_LOAD_FAILED")
                                if reason=="USER_STOP":
                                    stop_cycle=True;status["status"]="STOPPED_BY_USER";status["formal_tests"]="STOPPED";break
                                if reason in {"GPU_KERNEL_FAULT","KERNEL_AUDIT_UNREADABLE","MEMAVAILABLE_GUARD_LOAD","SWAP_GROWTH_GUARD_LOAD","CORROBORATED_SWAP_PRESSURE_GUARD_LOAD","SUSTAINED_CORROBORATED_SWAP_PRESSURE_GUARD_LOAD"}:
                                    record(write_sample_blocked(sample_dir,model_id,task,variant,reason))
                                    next_index=entry_index+1
                                    status["status"]="SAFETY_STOP";status["formal_tests"]="STOPPED_BY_SAFETY_GATE";stop_cycle=True;break
                                blocked_models[model_id]=reason
                    if model_id in blocked_models:
                        row=write_sample_blocked(sample_dir,model_id,task,variant,blocked_models[model_id])
                    else:
                        row=run_one_sample(model,task,variant,cycle_dir,server,ross_url,f"{root.name}-{cycle_name}")
                    record(row);next_index=entry_index+1
                    if row.get("status")=="HARNESS_INVALID":
                        status["status"]="HARNESS_INVALID";status["formal_tests"]="STOPPED_BY_HARNESS_INVALID";stop_cycle=True;break
                    guard_reason=(row.get("guarded_result") or {}).get("guard_reason")
                    if guard_reason and guard_reason!="SAMPLE_TIMEOUT":
                        if guard_reason=="USER_STOP" or STOP_FILE.exists():
                            status["status"]="STOPPED_BY_USER";status["formal_tests"]="STOPPED"
                        else:
                            status["status"]="SAFETY_STOP";status["formal_tests"]="STOPPED_BY_SAFETY_GATE"
                        stop_cycle=True;break
            except KeyboardInterrupt:
                if controller_stop_reason():
                    status["status"]="SAFETY_STOP";status["formal_tests"]="STOPPED_BY_CONTROLLER_SAFETY_GATE"
                else:
                    status["status"]="STOPPED_BY_USER";status["formal_tests"]="STOPPED"
                stop_cycle=True
                if next_index<len(entries) and (not cycle["samples"] or cycle["samples"][-1].get("model")!=entries[next_index]["model"] or cycle["samples"][-1].get("task")!=entries[next_index]["task"] or cycle["samples"][-1].get("variant")!=entries[next_index]["variant"]):
                    active=entries[next_index]
                    record(write_sample_blocked(cycle_dir/"samples"/active["model"].replace("/","_")/active["task"]/active["variant"],active["model"],active["task"],active["variant"],"USER_INTERRUPT"))
                    next_index+=1
            finally:
                stop_owned_server(server)
            if stop_cycle:
                reason=status.get("status","STOPPED")
                for entry in entries[next_index:]:
                    path=cycle_dir/"samples"/entry["model"].replace("/","_")/entry["task"]/entry["variant"]
                    row=write_sample_not_tested(path,entry["model"],entry["task"],entry["variant"],reason)
                    record(row,formal=False)
            if args.pilot_only and not stop_cycle:
                cycle["status"]="PILOT_COMPLETE"
            elif STOP_FILE.exists() or status.get("status")=="STOPPED_BY_USER":cycle["status"]="STOPPED"
            elif status.get("status")=="SAFETY_STOP":cycle["status"]="SAFETY_STOP"
            elif status.get("status")=="HARNESS_INVALID":cycle["status"]="HARNESS_INVALID"
            else:cycle["status"]="COMPLETE"
            cycle["sample_count"]=len(cycle["samples"]);cycle["finished_utc"]=datetime.now(timezone.utc).isoformat()
            cycle_path=cycle_dir/"cycle-status.json";cycle_path.write_text(json.dumps(cycle,indent=2,ensure_ascii=False)+"\n")
            report_path=write_cycle_report(cycle_dir,cycle)
            status["cycles"].append({"cycle":cycle_name,"status":cycle["status"],"samples":len(cycle["samples"]),"path":str(cycle_path.relative_to(ROOT))})
            status["cycles"][-1]["report"]=str(report_path.relative_to(ROOT))
            (BASE/"status.json").write_text(json.dumps(status,indent=2,ensure_ascii=False)+"\n")
            if stop_cycle or args.pilot_only:break
            cycle_num+=1
        if controller_stop_reason():
            status["status"]="SAFETY_STOP";status["formal_tests"]="STOPPED_BY_CONTROLLER_SAFETY_GATE"
        elif STOP_FILE.exists():
            status["status"]="STOPPED_BY_USER";status["formal_tests"]="STOPPED"
        elif status.get("status")=="SAFETY_STOP":
            status["formal_tests"]="STOPPED_BY_SAFETY_GATE"
        elif args.pilot_only and status.get("cycles") and status["cycles"][-1].get("status")=="PILOT_COMPLETE":
            status["status"]="PILOT_COMPLETE";status["formal_tests"]="PILOT_COMPLETE_REVIEW_REQUIRED"
        elif args.max_cycles and cycle_num>args.max_cycles:
            status["status"]="COMPLETED_REQUESTED_CYCLES";status["formal_tests"]="STOPPED_AFTER_REQUESTED_CYCLES"
    except KeyboardInterrupt:
        status["status"]="STOPPED_BY_USER";status["formal_tests"]="STOPPED"
    finally:
        (BASE/"status.json").write_text(json.dumps(status,indent=2,ensure_ascii=False)+"\n")
    print(json.dumps({"status":status["status"],"formal_sample_count":status["formal_sample_count"],"session":str(root.relative_to(ROOT))},ensure_ascii=False),flush=True)
    return 0

if __name__=="__main__":raise SystemExit(main())
