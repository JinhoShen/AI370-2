#!/usr/bin/env python3
"""Run isolated T2 two-file Local Qwen RTL A/B trials with and without AMD Ross."""
from __future__ import annotations
import hashlib, json, os, shutil, subprocess, sys, time
from datetime import datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SEED=ROOT/'docs/M13/evidence/2026-10-12/ross-ab-benchmark/T2/seed'
OUT=Path(os.environ.get('AI370_ROSS_AB_OUT',str(ROOT/'output/M13/ross-ab-benchmark-2026-10-12/T2-multifile')))
MODEL='Qwen3.8-27B-UD-Q4_K_XL'
ROSS_URL=os.environ.get('AI370_ROSS_DOCSEARCH_URL','')
ROSS_CONTEXT_CHARS=int(os.environ.get('AI370_ROSS_CONTEXT_CHARS','1800'))
ROSS_MCP_CHARS=int(os.environ.get('AI370_ROSS_MCP_CHARS','1200'))
REQUEST_TIMEOUT=900
TOTAL_TIMEOUT=2400
TRIAL_WALL_TIMEOUT=2500
SEQUENCE=[tuple((p[0],int(p[1:]))) for p in os.environ.get('AI370_ROSS_AB_SEQUENCE','A1,B1,B2,A2,A3,B3').split(',')]


def snapshot(root_pid:int):
    table={}
    for entry in Path('/proc').iterdir():
        if not entry.name.isdigit(): continue
        try:
            pid=int(entry.name); raw=(entry/'stat').read_text(); tail=raw[raw.rfind(')')+2:].split()
            ppid=int(tail[1]); ticks=int(tail[11])+int(tail[12]); rss=int(tail[21])*os.sysconf('SC_PAGE_SIZE')//1024
            cmd=(entry/'cmdline').read_bytes().replace(b'\0',b' ').decode(errors='ignore')
            table[pid]=(ppid,ticks,rss)
            if 'Qwen3.8-27B-UD-Q4_K_XL.gguf' in cmd: table[pid]=(-1,ticks,rss)
        except (OSError,ValueError,IndexError): pass
    descendants={root_pid}; changed=True
    while changed:
        changed=False
        for pid,(ppid,_,_) in table.items():
            if ppid in descendants and pid not in descendants: descendants.add(pid); changed=True
    rss=ticks=0
    for pid in descendants:
        if pid in table: _,t,r=table[pid]; ticks+=t; rss+=r
    for ppid,t,r in table.values():
        if ppid==-1: ticks+=t; rss+=r
    mem={}
    for line in Path('/proc/meminfo').read_text().splitlines():
        k,_,v=line.partition(':')
        if v.strip().endswith('kB'): mem[k]=int(v.split()[0])
    return rss,ticks,mem.get('MemAvailable',0),mem.get('SwapTotal',0)-mem.get('SwapFree',0),mem.get('MemTotal',0)


def seed(label,rep):
    work=OUT/f'{label}{rep}/workspace'; work.mkdir(parents=True)
    shutil.copytree(SEED/'rtl',work/'rtl'); shutil.copytree(SEED/'sim',work/'sim')
    shutil.copy2(SEED/'TASK_SPEC.md',work/'TASK_SPEC.md')
    shutil.copy2(ROOT/'scripts/run_m13_t2_validation.sh',work/'run_validation_multifile.sh')
    # An isolated tracked baseline lets git apply validate/apply complete multi-file diffs.
    # This .git lives only inside the disposable trial workspace and has no remote.
    subprocess.run(['git','init','--quiet'],cwd=work,check=True)
    subprocess.run(['git','config','user.name','AI370-2 isolated trial'],cwd=work,check=True)
    subprocess.run(['git','config','user.email','local@invalid'],cwd=work,check=True)
    subprocess.run(['git','add','rtl','sim','TASK_SPEC.md','run_validation_multifile.sh'],cwd=work,check=True)
    subprocess.run(['git','commit','--quiet','-m','Seed isolated T2 baseline'],cwd=work,check=True)
    task=("Read these exact workspace files with read_file: TASK_SPEC.md, rtl/local_model_axi_lite.v, "
          "rtl/axi_result_datapath.v, and sim/tb_local_model_axi_lite.sv. Do not call list_files or reread them unless the agent supplies a concrete reason; "
          "do not read the fixed validation runner. First run the unchanged baseline with run_xsim and diagnose its real failure. "
          "Then make the smallest single model-authored unified diff that modifies BOTH explicitly allowed RTL sources: "
          "rtl/local_model_axi_lite.v and rtl/axi_result_datapath.v. Do not edit the fixed testbench, task, runner or any other path. "
          "Rerun run_xsim and use actual feedback for at most 3 total validation attempts. The final fixed self-checking XSim marker is required.\n")
    if label=='B':
        task+=("Before any simulation or patch, use the actual installed AMD Ross vivado-simulate-rtl skill and its xsim.md reference via ross_skill_read, "
               "then ross_doc_search for Vivado 2026.1 XSim RTL and multi-file source compilation guidance. Incorporate the returned evidence.\n")
    else: task+="Non-Ross control: do not consult or call any Ross Skill or Knowledge Base; use only task/spec/source and fixed tools.\n"
    (work/'TASK_INSTRUCTIONS.md').write_text(task)
    return work


def run_trial(label,rep):
    work=seed(label,rep); base=OUT/f'{label}{rep}'; trace=base/'local-agent-trace.jsonl'; stdout=base/'stdout.json'; stderr=base/'stderr.log'
    # The model must read the exact specification through the workspace tool; avoid duplicating
    # its full text in the system prompt, which consumes scarce local-model context.
    task=(work/'TASK_INSTRUCTIONS.md').read_text()+"\nUse TASK_SPEC.md as the complete engineering request; do not infer requirements beyond it.\n"
    command=[sys.executable,str(ROOT/'scripts/local_agent.py'),'--workspace',str(work),'--task',task,'--timeout',str(REQUEST_TIMEOUT),'--total-timeout',str(TOTAL_TIMEOUT),'--max-completion-tokens','2048','--max-calls','14','--multi-file-xsim','--editable-path','rtl/local_model_axi_lite.v','--editable-path','rtl/axi_result_datapath.v','--trace',str(trace)]
    if label=='B':
        if not ROSS_URL: raise RuntimeError('AI370_ROSS_DOCSEARCH_URL required for condition B')
        command += ['--ross-docsearch-url',ROSS_URL,'--ross-context-chars',str(ROSS_CONTEXT_CHARS),'--ross-mcp-chars',str(ROSS_MCP_CHARS)]
    before={p:hashlib.sha256((work/p).read_bytes()).hexdigest() for p in ('rtl/local_model_axi_lite.v','rtl/axi_result_datapath.v')}
    started=datetime.now().astimezone().isoformat(timespec='seconds'); begin=time.monotonic()
    rss_peak=min_avail=max_swap=None; base_swap=None; min_avail=None; max_swap=0; cpu_first=cpu_last=0; mem_total=0; guard=None
    env=os.environ.copy()
    if label=='A': env.pop('AI370_ROSS_DOCSEARCH_URL',None)
    with stdout.open('wb') as out,stderr.open('wb') as err:
        proc=subprocess.Popen(command,cwd=ROOT,stdout=out,stderr=err,env=env,start_new_session=True)
        while proc.poll() is None:
            rss,ticks,avail,swap,total=snapshot(proc.pid)
            rss_peak=max(rss_peak or 0,rss); cpu_first=ticks if cpu_first==0 else cpu_first; cpu_last=ticks
            min_avail=avail if min_avail is None else min(min_avail,avail); max_swap=max(max_swap,swap); base_swap=swap if base_swap is None else base_swap; mem_total=total
            floor=max(6*1024*1024,int(total*.125))
            if avail<floor: guard=f'MemAvailable below guard floor: {avail} KiB < {floor} KiB'
            elif swap>base_swap+2*1024*1024: guard=f'Swap increased >2 GiB: {swap-base_swap} KiB'
            if guard:
                subprocess.run(['kill','-INT','--',str(-proc.pid)],capture_output=True); break
            if time.monotonic()-begin>TRIAL_WALL_TIMEOUT:
                guard=f'hard trial wall limit exceeded: {TRIAL_WALL_TIMEOUT} seconds'
                subprocess.run(['kill','-INT','--',str(-proc.pid)],capture_output=True)
                break
            time.sleep(.5)
        try: code=proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            subprocess.run(['kill','-TERM','--',str(-proc.pid)],capture_output=True)
            try: code=proc.wait(timeout=5)
            except subprocess.TimeoutExpired: subprocess.run(['kill','-KILL','--',str(-proc.pid)],capture_output=True); code=proc.wait()
    elapsed=time.monotonic()-begin; raw=stdout.read_text(errors='replace').strip()
    cpu_core_percent=max(0.0,(cpu_last-cpu_first)/os.sysconf('SC_CLK_TCK')/max(elapsed,0.001)*100.0)
    cpu_machine_percent=cpu_core_percent/max(os.cpu_count() or 1,1)
    try: result=json.loads(raw.splitlines()[-1])
    except (json.JSONDecodeError,IndexError): result={'status':'FAIL','error':'missing Agent result JSON','stdout_tail':raw[-2000:]}
    after={p:hashlib.sha256((work/p).read_bytes()).hexdigest() for p in before}
    events=[json.loads(x) for x in trace.read_text().splitlines()] if trace.exists() else []
    usage=[e.get('response',{}).get('usage',{}) for e in events if e.get('event')=='model_response']
    ross=[e for e in events if e.get('event')=='tool_call' and e.get('name') in {'ross_doc_search','ross_skill_read'}]
    val=[e.get('result',{}) for e in events if e.get('event')=='tool_call' and e.get('name')=='run_xsim']
    patches=[e for e in events if e.get('event') in {'patch_applied','model_replacement_applied'}]
    status='RESOURCE_GUARD_STOP' if guard and not guard.startswith('hard trial') else ('HARD_TIMEOUT' if guard else result.get('status','FAIL'))
    summary={'trial':f'{label}{rep}','condition':'ross' if label=='B' else 'non_ross','sequence_position':SEQUENCE.index((label,rep))+1,'started_local':started,'elapsed_seconds':round(elapsed,3),'exit_code':code,'agent_status':status,'resource_guard_stop':guard if status=='RESOURCE_GUARD_STOP' else None,'hard_timeout':guard if status and status.startswith('HARD_TIMEOUT') else None,'model_patch_count':result.get('patches',0),'applied_patch_paths':[e.get('paths',[e.get('path')]) for e in patches],'ross_call_count':len(ross),'ross_call_names':[e.get('name') for e in ross],'ross_call_seconds':sum((e.get('result') or {}).get('elapsed_seconds',0) for e in ross),'ross_context_chars':ROSS_CONTEXT_CHARS if label=='B' else None,'ross_mcp_chars':ROSS_MCP_CHARS if label=='B' else None,'xsim_attempts':len(val),'xsim_pass_markers':sum(bool(x.get('terminal_pass_marker')) for x in val),'observed_prompt_tokens':sum(int(u.get('prompt_tokens') or 0) for u in usage),'observed_completion_tokens':sum(int(u.get('completion_tokens') or 0) for u in usage),'process_peak_rss_mib':round((rss_peak or 0)/1024,1),'host_min_memavailable_mib':round((min_avail or 0)/1024,1),'host_max_swap_used_mib':round(max_swap/1024,1),'process_cpu_machine_percent':round(cpu_machine_percent,1),'process_cpu_core_equivalent_percent':round(cpu_core_percent,1),'seed_source_sha256':before,'final_source_sha256':after,'result':result,'agent_policy':{'request_timeout_seconds':REQUEST_TIMEOUT,'total_timeout_seconds':TOTAL_TIMEOUT,'max_completion_tokens':2048,'max_tool_calls':14,'validation_attempt_cap':3},'trial_wall_timeout_seconds':TRIAL_WALL_TIMEOUT}
    (base/'result.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False)+'\n')
    return summary


def main():
    OUT.mkdir(parents=True,exist_ok=True); all_trials=[]
    for label,rep in SEQUENCE:
        print(f'START {label}{rep}',flush=True); item=run_trial(label,rep); all_trials.append(item)
        (OUT/'trials.json').write_text(json.dumps(all_trials,indent=2,ensure_ascii=False)+'\n')
        print(json.dumps({k:item[k] for k in ('trial','elapsed_seconds','agent_status','xsim_attempts','ross_call_count','model_patch_count','host_min_memavailable_mib','host_max_swap_used_mib')},ensure_ascii=False),flush=True)
    return 0 if len(all_trials)==6 else 1
if __name__=='__main__': raise SystemExit(main())
