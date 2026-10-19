#!/usr/bin/env python3
"""Continuous bounded model engineering cohorts; user stops, finally restores Qwen.

Reuses unchanged M13 trial functions, tasks, sandbox and independent validators.
No downloads, profile saving, driver changes or hardware programming.
"""
import argparse
import fcntl
import hashlib
import importlib
import json
import os
import shutil
import signal
import statistics
import subprocess
import sys
import threading
import time
import urllib.request
from datetime import datetime
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
HOME=ROOT/'output/model-endurance'
LOCK=ROOT/'output/local-agent-operation.lock'
PORT=18082
FORMAL='Qwen3.8-27B-UD-Q4_K_XL'
STOP=threading.Event()
CHILD=None
SERVER=None
RUN=None
BLOCKED={}


class SafetyFault(RuntimeError):pass


def stamp():return datetime.now().astimezone().isoformat()


def save(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix('.tmp');temp.write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n');temp.replace(path)


def notify(**data):
    data.update(timestamp=stamp(),run=str(RUN),controller_pid=os.getpid())
    save(HOME/'status.json',data)
    with (RUN/'events.jsonl').open('a') as f:f.write(json.dumps(data,ensure_ascii=False)+'\n')
    print(json.dumps(data,ensure_ascii=False),flush=True)


def api(path,body=None,base='http://127.0.0.1:13305/api/v1/'):
    req=urllib.request.Request(base+path,data=json.dumps(body).encode() if body else None,
                               headers={'Content-Type':'application/json'})
    op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with op.open(req,timeout=120 if body else 5) as r:return json.load(r)


def restoration_allowed(reason):
    # Reinitializing a GPU after a severe device/kernel fault is not safe recovery.
    return 'KERNEL_FAULT_OR_UNREADABLE' not in reason and 'PROTECTED_STACK_CHANGED' not in reason


def roster():
    c=json.loads((ROOT/'config/local_model_lab.json').read_text())
    known={m['key']:m for m in c['models']}
    variants=c['additional_local_variants_not_in_five_model_roster']
    rows=[]
    for i in [0,1]:
        v=variants[i];rows.append(dict(id=v['artifact'][:-5],file=v['artifact'],bytes=v['bytes'],sha256=v['sha256'],backend='vulkan'))
    for key,backend in [('gemma4_31b','cpu'),('qwen38','vulkan')]:
        m=known[key];rows.append(dict(id=m['model_id'],file=m['relative_path'],bytes=m['bytes'],sha256=m['sha256'],backend=backend))
    return rows


def schedule():
    # A1 B1 B2 A2 A3 B3 for each model/task, spread models across repetitions.
    for rep,arms in [(1,'AB'),(2,'BA'),(3,'AB')]:
        for model in roster():
            for task in ['T1','T2','T3']:
                for arm in arms:yield rep,model,task,arm


def package_state():
    names=['mesa-vulkan-drivers','libdrm-amdgpu1','rocm-core','hip-runtime-amd','xrt-base','xrt-npu','xrt_plugin-amdxdna']
    r=subprocess.run(['dpkg-query','-W','-f=${Package}=${Version}\n',*names],capture_output=True,text=True,check=True)
    return dict(kernel=os.uname().release,packages=r.stdout.splitlines(),module=Path('/sys/module/amdxdna/version').read_text().strip())


def manifest(directory):
    with (directory/'SHA256SUMS').open('w') as f:
        for p in sorted(directory.rglob('*')):
            if p.is_file() and p.name!='SHA256SUMS' and '.git' not in p.parts and 'xsim.dir' not in p.parts and p.suffix in {'.json','.jsonl','.log','.rpt','.md','.v','.sv','.cpp','.cfg','.tcl','.py','.sh'}:
                f.write(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+str(p.relative_to(directory))+'\n')


def resources():
    from run_local_model_lab_practical import memory
    m=memory();return dict(available=m['MemAvailable'],floor=max(6*1024**2,m['MemTotal']//8),swap=m['SwapTotal']-m['SwapFree'])


def synthesize(workspace):
    from local_agent import LocalAgent
    directory=workspace/'post-agent-synthesis';directory.mkdir()
    files=sorted((workspace/'rtl').glob('*.v'))
    before={str(p.relative_to(workspace)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    tcl=directory/'fixed.tcl'
    tcl.write_text('set_param general.maxThreads '+str(min(32,len(os.sched_getaffinity(0))))+'\n'+
                   'read_verilog -sv {'+' '.join(str(p) for p in files)+'}\n'+
                   'synth_design -top local_model_axi_lite -part xc7s100fgga676-2\n'+
                   'create_clock -period 10.000 [get_ports aclk]\n'+
                   'report_utilization -file {'+str(directory/'utilization.rpt')+'}\n'+
                   'report_timing_summary -file {'+str(directory/'timing.rpt')+'}\n'+
                   'puts ENDURANCE_SYNTHESIS_PASS\nexit\n')
    agent=LocalAgent(workspace,task='Fixed post-model synthesis',total_timeout=240)
    try:
        r=agent._run_bounded(['/home/shen/tools/Xilinx/2026.1/2026.1/Vivado/bin/vivado','-mode','batch','-notrace','-source',str(tcl),'-log',str(directory/'vivado.log'),'-journal',str(directory/'vivado.jou')],share_net=True,timeout=180)
    finally:agent.close()
    (directory/'stdout.log').write_text(r.stdout);(directory/'stderr.log').write_text(r.stderr)
    after={str(p.relative_to(workspace)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    good=r.returncode==0 and 'ENDURANCE_SYNTHESIS_PASS' in r.stdout and before==after and all((directory/n).is_file() for n in ['utilization.rpt','timing.rpt'])
    result=dict(status='PASS' if good else 'FAIL',exit_code=r.returncode,source_before=before,source_after=after,timing='REPORT_ONLY, no IO timing closure')
    save(directory/'result.json',result);return result


def trial(cfgpath):
    cfg=json.loads(cfgpath.read_text())
    module=importlib.import_module({'T1':'run_ross_ab_t1','T2':'run_ross_ab_t2','T3':'run_ross_ab_hls'}[cfg['task']])
    row=module.run_trial(cfg['arm'],cfg['rep'])
    status=row['agent_status']
    if status=='PASS':
        import audit_local_engineering_evidence as audit
        case=Path(os.environ['AI370_ROSS_AB_OUT'])/(cfg['arm']+str(cfg['rep']))
        events=[json.loads(s) for s in (case/'local-agent-trace.jsonl').read_text().splitlines()]
        try:
            row['proof']=audit.trace_checks(events,cfg['task'],cfg['arm']=='B')
            if cfg['task']!='T3':
                row['synthesis']=synthesize(case/'workspace')
                if row['synthesis']['status']!='PASS':status='FAIL_SYNTHESIS'
        except Exception as exc:status='HARNESS_INVALID';row['audit_error']=str(exc)
    row['status']=status
    save(cfgpath.parent/'trial-result.json',row)
    print(json.dumps(dict(status=status,trial=row['trial']),ensure_ascii=False))


def gpu_sample():
    sample={}
    for name in ['gpu_busy_percent','mem_info_vram_used','mem_info_gtt_used']:
        values=[]
        for path in Path('/sys/class/drm').glob('card*/device/'+name):
            try:values.append(int(path.read_text()))
            except (OSError,ValueError):pass
        sample[name]=max(values) if values else None
    return sample


def guarded_process(command,directory,timeout,env=None):
    global CHILD
    from run_local_model_lab_practical import stop,fault_audit
    baseline=resources();start=time.monotonic();started=stamp();last=0;peak_swap=baseline['swap'];min_avail=baseline['available'];reason=None;gpu_peak={}
    with (directory/'stdout.log').open('w') as out,(directory/'stderr.log').open('w') as err:
        CHILD=subprocess.Popen(command,cwd=ROOT,env=env,stdout=out,stderr=err,start_new_session=True)
        try:
            while CHILD.poll() is None:
                if STOP.is_set() or (HOME/'STOP').exists():raise InterruptedError('USER_STOP')
                if shutil.disk_usage(ROOT).free<20*1024**3:raise RuntimeError('DISK_GUARD')
                m=resources();peak_swap=max(peak_swap,m['swap']);min_avail=min(min_avail,m['available'])
                gpu=gpu_sample()
                for name,value in gpu.items():
                    if value is not None:gpu_peak[name]=max(gpu_peak.get(name,0),value)
                if m['available']<m['floor'] or m['swap']-baseline['swap']>64*1024:
                    save(directory/'resource-guard.json',dict(baseline=baseline,current=m,elapsed_seconds=time.monotonic()-start))
                    raise RuntimeError('RESOURCE_GUARD')
                if time.monotonic()-start>timeout:reason='TIMEOUT';break
                if time.monotonic()-last>10:
                    a=fault_audit(started)
                    if a['read_exit'] or a['faults']:raise SafetyFault('KERNEL_FAULT_OR_UNREADABLE: '+str(a))
                    with (directory/'resource-samples.jsonl').open('a') as f:f.write(json.dumps(dict(timestamp=stamp(),memory=m,gpu_whole_device=gpu))+'\n')
                    last=time.monotonic()
                time.sleep(.5)
            if reason:stop(CHILD)
            code=CHILD.wait()
            return dict(exit_code=code,reason=reason,elapsed_seconds=round(time.monotonic()-start,3),peak_swap_kib=peak_swap,swap_growth_kib=peak_swap-baseline['swap'],min_available_kib=min_avail,gpu_whole_device_peak=gpu_peak)
        finally:
            stop(CHILD);CHILD=None


def hash_model(model):
    path=ROOT/'resources/Agent_Tools_Docs/04_Local_AI/GGUF'/model['file']
    if not path.is_file() or path.stat().st_size!=model['bytes']:raise ValueError('MODEL_MISSING_OR_SIZE_MISMATCH')
    h=hashlib.sha256()
    with path.open('rb') as f:
        while chunk:=f.read(8*1024**2):
            if STOP.is_set() or (HOME/'STOP').exists():raise InterruptedError('USER_STOP')
            h.update(chunk)
    result=dict(path=str(path),bytes=path.stat().st_size,sha256=h.hexdigest(),mtime_ns=path.stat().st_mtime_ns)
    if result['sha256']!=model['sha256']:raise ValueError('MODEL_SHA256_MISMATCH')
    return result


def server_command(model):
    backend=model['backend'];threads=len(os.sched_getaffinity(0))
    path=ROOT/'resources/Agent_Tools_Docs/04_Local_AI/GGUF'/model['file']
    return [str(ROOT/f'output/M6/build-{backend}/bin/llama-server'),'-m',str(path),'--alias',model['id'],'--host','127.0.0.1','--port',str(PORT),'--offline','--log-verbosity','5','--ctx-size','16384','--threads',str(threads),'--threads-batch',str(threads),'--n-gpu-layers','99' if backend=='vulkan' else '0','--device','Vulkan0' if backend=='vulkan' else 'none','--parallel','1','--reasoning','off','--jinja','--metrics','--batch-size','2048','--ubatch-size','512']


def load(model,directory):
    global SERVER
    if api('health').get('model_loaded'):raise SafetyFault('EXTERNAL_MODEL_LOAD_CONFLICT')
    command=server_command(model);save(directory/'server-command.json',command)
    stream=(directory/'server.log').open('w');SERVER=subprocess.Popen(command,cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True);stream.close()
    begin=time.monotonic();baseline=resources();started=stamp();last_audit=0
    while time.monotonic()-begin<180:
        if STOP.is_set() or (HOME/'STOP').exists():raise InterruptedError('USER_STOP')
        m=resources()
        if m['available']<m['floor'] or m['swap']-baseline['swap']>64*1024:
            save(directory/'load-resource-guard.json',dict(baseline=baseline,current=m,elapsed_seconds=time.monotonic()-begin))
            raise RuntimeError('RESOURCE_GUARD_LOAD')
        if time.monotonic()-last_audit>3:
            from run_local_model_lab_practical import fault_audit
            a=fault_audit(started)
            if a['read_exit'] or a['faults']:raise SafetyFault('KERNEL_FAULT_OR_UNREADABLE: '+str(a))
            last_audit=time.monotonic()
        if SERVER.poll() is not None:raise RuntimeError('MODEL_SERVER_EXIT')
        try:
            health=api('health',base=f'http://127.0.0.1:{PORT}/')
            if health.get('status')=='ok':break
        except OSError:pass
        time.sleep(.5)
    else:raise TimeoutError('MODEL_LOAD_TIMEOUT')
    text=(directory/'server.log').read_text(errors='replace')
    import re
    if model['backend']=='vulkan' and not re.search(r'offloaded [1-9]\d*/\d+ layers',text):raise RuntimeError('GPU_OFFLOAD_NOT_PROVEN')
    r=dict(model=model['id'],backend=model['backend'],command=command,load_seconds=round(time.monotonic()-begin,3),pid=SERVER.pid,actual_offload_lines=[s for s in text.splitlines() if 'offload' in s.lower()])
    save(directory/'runtime.json',r)
    smoke=api('chat/completions',dict(model=model['id'],messages=[dict(role='user',content='Reply READY.')],temperature=0,max_tokens=4),base=f'http://127.0.0.1:{PORT}/v1/')
    save(directory/'smoke.json',smoke)
    if not smoke.get('choices'):raise RuntimeError('SMOKE_NO_RESPONSE')
    return r


def summarize(rows):
    groups={}
    for row in rows:
        key=(row['model'],row['task'],row['arm'])
        groups.setdefault(key,[]).append(row)
    result=[]
    for key,items in groups.items():
        times=[r['elapsed_seconds'] for r in items if isinstance(r.get('elapsed_seconds'),(int,float))]
        result.append(dict(model=key[0],task=key[1],arm=key[2],attempts=len(items),passes=sum(r['status']=='PASS' for r in items),success_rate=sum(r['status']=='PASS' for r in items)/len(items),timing_observations=len(times),mean_all_attempt_seconds=statistics.mean(times) if times else None,median_all_attempt_seconds=statistics.median(times) if times else None,statuses=[r['status'] for r in items]))
    return result


def verified_resume(source):
    import audit_local_engineering_evidence as audit
    source=source.resolve()
    if HOME.resolve() not in source.parents:raise ValueError('Resume must be an existing local evaluation session')
    audit.manifest(source)
    rows=[]
    for path in source.glob('cycle-*/rep-*/*/T*/*-controller/trial-result.json'):
        detail=json.loads(path.read_text())
        if detail.get('status')!='PASS':continue
        cfg=json.loads((path.parent/'config.json').read_text())
        model=detail.get('result',{}).get('model')
        known=next((m for m in roster() if m['id']==model),None)
        if not known:continue
        case=path.parent.parent/(cfg['arm']+str(cfg['rep']))
        events=[json.loads(s) for s in (case/'local-agent-trace.jsonl').read_text().splitlines()]
        audit.trace_checks(events,cfg['task'],cfg['arm']=='B')
        if cfg['task']!='T3':
            proof=json.loads((case/'workspace/post-agent-synthesis/result.json').read_text())
            if proof['status']!='PASS' or proof['source_before']!=proof['source_after']:continue
            for name,digest in proof['source_after'].items():
                if hashlib.sha256((case/'workspace'/name).read_bytes()).hexdigest()!=digest:raise ValueError('Resumed source hash mismatch')
        cycle=int(path.relative_to(source).parts[0].split('-')[1])
        rows.append(dict(cycle=cycle,model=model,backend=known['backend'],task=cfg['task'],arm=cfg['arm'],rep=cfg['rep'],status='PASS',detail=detail,
                         imported_evidence=str(path),elapsed_seconds=None,timing_scope='Outer end-to-end duration UNKNOWN after controller crash; model/XSim time retained in detail, excluded from end-to-end timing averages'))
    return rows


def main():
    global RUN,SERVER
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--continuous',action='store_true');parser.add_argument('--trial',type=Path);parser.add_argument('--resume',type=Path);args=parser.parse_args()
    if args.trial:return trial(args.trial)
    if not args.continuous:parser.error('Explicit --continuous required')
    os.umask(0o077);HOME.mkdir(parents=True,exist_ok=True);LOCK.parent.mkdir(exist_ok=True)
    lock=LOCK.open('a+');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    from local_agent_ui import api as ui_api,load_command
    from verify_local_agent_runtime import verify
    from run_local_model_lab_practical import stop,fault_audit
    verify(smoke=False)
    if any(x.get('is_busy') for x in ui_api('health').get('all_models_loaded',[])):raise RuntimeError('EXTERNAL_MODEL_BUSY')
    with __import__('socket').socket() as s:s.bind(('127.0.0.1',PORT))
    RUN=HOME/datetime.now().astimezone().strftime('%Y%m%dT%H%M%S%z');RUN.mkdir()
    (HOME/'STOP').unlink(missing_ok=True)
    for sig in [signal.SIGTERM,signal.SIGINT]:signal.signal(sig,lambda *_:STOP.set())
    save(RUN/'original-runtime.json',verify(smoke=False))
    original_packages=package_state();save(RUN/'original-packages.json',original_packages)
    snapshots={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [ROOT/'scripts'/n for n in ['run_model_endurance.py','local_agent.py','run_ross_ab_t1.py','run_ross_ab_t2.py','run_ross_ab_hls.py']]}
    save(RUN/'harness-sha256.json',snapshots)
    for name in snapshots:
        p=ROOT/name;target=RUN/'harness'/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target)
    save(RUN/'protocol.json',dict(models=roster(),context=16384,threads=len(os.sched_getaffinity(0)),request_timeout=600,max_tokens=2048,max_calls=14,cycles='until user stop or safety gate',limits=dict(min_memavailable='max(6 GiB, 12.5% OS RAM)',max_swap_growth_mib=64),actual_user_project='NOT_TESTED: no project supplied',physical_airgap='NOT_TESTED: no host network changes',long_job_cancel='validated only when actually requested and observed',gemma_cpu='explicit distinct profile; previous Vulkan guard remains blocked',comparison='practical configured system, not pure backend-controlled model ranking'))
    rows=verified_resume(args.resume) if args.resume else [];save(RUN/'imported-verified-trials.json',rows)
    resumed={(r['cycle'],r['rep'],r['model'],r['task'],r['arm']) for r in rows}
    verified={};current=None;cycle=1;reason='USER_STOP';unloaded=False;pending=None
    try:
        unloaded=True
        subprocess.run(['/usr/bin/lemonade','unload',FORMAL],check=True,capture_output=True,timeout=45)
        if ui_api('health').get('model_loaded'):raise RuntimeError('FORMAL_MODEL_STILL_LOADED')
        while not STOP.is_set() and not (HOME/'STOP').exists():
            eligible=False
            for rep,model,task,arm in schedule():
                if STOP.is_set() or (HOME/'STOP').exists():raise InterruptedError('USER_STOP')
                if (cycle,rep,model['id'],task,arm) in resumed:continue
                if model['id'] in BLOCKED:continue
                eligible=True
                base=RUN/f'cycle-{cycle:03d}'/f'rep-{rep}'/model['id'];base.mkdir(parents=True,exist_ok=True)
                if current!=model['id']:
                    stop(SERVER);SERVER=None;current=None
                    notify(status='RUNNING',stage='MODEL_INTEGRITY_AND_LOAD',model=model['id'],backend=model['backend'],cycle=cycle,rep=rep,blocked=BLOCKED)
                    try:
                        if package_state()!=original_packages:raise SafetyFault('PROTECTED_STACK_CHANGED')
                        if model['id'] not in verified:verified[model['id']]=hash_model(model);save(RUN/'model-integrity.json',verified)
                        actual=Path(verified[model['id']]['path']).stat()
                        if actual.st_size!=verified[model['id']]['bytes'] or actual.st_mtime_ns!=verified[model['id']]['mtime_ns']:raise SafetyFault('MODEL_CHANGED_AFTER_HASH')
                        load(model,base);current=model['id']
                    except (InterruptedError,SafetyFault):raise
                    except Exception as exc:
                        stop(SERVER);SERVER=None;BLOCKED[model['id']]=str(exc);save(base/'load-failure.json',dict(status='BLOCKED',reason=str(exc)));continue
                notify(status='RUNNING',stage='ENGINEERING',model=model['id'],backend=model['backend'],cycle=cycle,rep=rep,task=task,arm=arm,blocked=BLOCKED)
                if any(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=value for p,value in snapshots.items()):raise SafetyFault('HARNESS_CHANGED')
                directory=base/task/(arm+str(rep)+'-controller');directory.mkdir(parents=True)
                cfg=dict(task=task,arm=arm,rep=rep);save(directory/'config.json',cfg)
                env=os.environ.copy();env.update(AI370_LOCAL_MODEL=model['id'],AI370_LOCAL_BASE_URL=f'http://127.0.0.1:{PORT}/v1',AI370_ROSS_DOCSEARCH_URL='http://172.18.0.4:8080/mcp/doc-search',AI370_ROSS_AB_OUT=str(base/task),AI370_MODEL_LAB_SERVER_PID=str(SERVER.pid),AI370_MODEL_LAB_MODEL_PATH=str(ROOT/'resources/Agent_Tools_Docs/04_Local_AI/GGUF'/model['file']),AI370_MODEL_LAB_REQUEST_TIMEOUT='600',AI370_MODEL_LAB_TOTAL_TIMEOUT='2400',AI370_MODEL_LAB_COMPLETION_CAP='2048',AI370_MODEL_LAB_TOOL_CALL_CAP='14',AI370_ROSS_CONTEXT_CHARS='1800',AI370_ROSS_MCP_CHARS='1200')
                pending=dict(cycle=cycle,model=model['id'],backend=model['backend'],task=task,arm=arm,rep=rep,started=stamp())
                try:
                    stats=guarded_process([sys.executable,str(Path(__file__).resolve()),'--trial',str(directory/'config.json')],directory,timeout=2700,env=env)
                    file=directory/'trial-result.json';detail=json.loads(file.read_text()) if file.exists() else {}
                    row=dict(cycle=cycle,model=model['id'],backend=model['backend'],context=16384,threads=len(os.sched_getaffinity(0)),task=task,arm=arm,rep=rep,detail=detail,**stats)
                    row['status']='TIMEOUT' if stats['reason'] else detail.get('status','HARNESS_INVALID')
                except (InterruptedError,SafetyFault):raise
                except RuntimeError as exc:
                    if 'KERNEL_' in str(exc):raise
                    BLOCKED[model['id']]=str(exc);current=None;stop(SERVER);SERVER=None
                    row=dict(cycle=cycle,model=model['id'],task=task,arm=arm,rep=rep,status='RESOURCE_GUARD_STOP',reason=str(exc))
                manifest(directory)
                case=base/task/(arm+str(rep))
                if case.is_dir():manifest(case)
                rows.append(row);pending=None
                with (RUN/'trials.jsonl').open('a') as f:f.write(json.dumps(row,ensure_ascii=False)+'\n');f.flush();os.fsync(f.fileno())
                save(RUN/'scoreboard.json',summarize(rows))
                notify(status='RUNNING',stage='TRIAL_COMPLETED',model=model['id'],backend=model['backend'],cycle=cycle,task=task,arm=arm,rep=rep,last_result=row['status'],completed_trials=len(rows),blocked=BLOCKED)
            stop(SERVER);SERVER=None;current=None
            if not eligible:reason='ALL_CONFIGURATIONS_BLOCKED';break
            cycle+=1
    except InterruptedError:reason='USER_STOP'
    except BaseException as exc:reason=f'SAFETY_OR_CONTROLLER_BLOCK: {type(exc).__name__}: {exc}'
    finally:
        if pending is not None:
            pending.update(status='CANCELLED' if reason=='USER_STOP' else 'CONTROLLER_STOP',reason=reason)
            rows.append(pending)
            with (RUN/'trials.jsonl').open('a') as f:f.write(json.dumps(pending,ensure_ascii=False)+'\n');f.flush();os.fsync(f.fileno())
        stop(SERVER);SERVER=None
        notify(status='RESTORING',stage='RESTORE_FORMAL_QWEN',reason=reason,blocked=BLOCKED)
        restoration='NOT_NEEDED'
        if unloaded and not restoration_allowed(reason):
            restoration='DEFERRED_SAFETY: GPU profile not reloaded after kernel/stack gate'
        elif unloaded:
            try:
                r=subprocess.run(load_command(FORMAL),capture_output=True,text=True,timeout=180);(RUN/'restore.log').write_text(r.stdout+r.stderr)
                if r.returncode:raise RuntimeError('formal load failed')
                save(RUN/'restored-runtime.json',verify(smoke=False));restoration='PASS'
            except Exception as exc:restoration='FAIL: '+str(exc)
        notify(status='STOPPED' if reason=='USER_STOP' and restoration=='PASS' else 'BLOCKED',stage='FINISHED',reason=reason,formal_restoration=restoration,completed_trials=len(rows),blocked=BLOCKED)
        save(RUN/'scoreboard.json',summarize(rows))
        save(RUN/'final-packages.json',package_state())
        # Hash source/config/text evidence; leave large generated caches untracked.
        with (RUN/'SHA256SUMS').open('w') as checksum_stream:
            for p in sorted(RUN.rglob('*')):
                if p.is_file() and p.suffix in {'.json','.jsonl','.log','.rpt','.md','.v','.sv','.cpp','.cfg','.tcl','.py','.sh'} and 'xsim.dir' not in p.parts:
                    checksum_stream.write(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+str(p.relative_to(RUN))+'\n')
        fcntl.flock(lock,fcntl.LOCK_UN);lock.close()


if __name__=='__main__':main()
