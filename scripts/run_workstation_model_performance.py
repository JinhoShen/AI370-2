#!/usr/bin/env python3
"""Hardware-aware four-model performance/engineering evaluation until user stop.

No package/driver/model changes. Uses the existing benchmark, agent and tools.
"""
import argparse
import fcntl
import json
import os
import re
import shutil
import signal
import socket
import statistics
import subprocess
import sys
import time
from pathlib import Path
import optimize_qwen_performance as perf
import run_local_model_lab_practical as shared
import run_model_endurance as evidence

ROOT=evidence.ROOT
HOME=evidence.HOME
STOP=evidence.STOP
PROMPT_SOURCE=perf.PROMPT
PROFILE=None
CHILD=None
BLOCKED_PROFILES={}


def risk(available_kib,total_kib,low_seconds,swapout_rate_mib,thrash_seconds,psi_full):
    if available_kib<1024**2:return 'EMERGENCY_LOW_MEMORY'
    if available_kib<max(2*1024**2,total_kib//20) and low_seconds>=5:return 'SUSTAINED_LOW_MEMORY'
    if swapout_rate_mib>=32 and thrash_seconds>=10:return 'SUSTAINED_SWAPOUT'
    if psi_full>=20 and low_seconds>=10:return 'SUSTAINED_MEMORY_PRESSURE'
    return None


class HardwareGuard(perf.Guard):
    def watch(self):
        previous=perf.vm();previous_time=time.monotonic();low_since=thrash_since=None;last=0
        while not self.done.is_set() and self.process.poll() is None:
            now=time.monotonic();m=shared.memory();v=perf.vm();swap=m['SwapTotal']-m['SwapFree']
            rate=max(0,v['pswpout']-previous['pswpout'])*os.sysconf('SC_PAGE_SIZE')/1024**2/max(.01,now-previous_time)
            previous,previous_time=v,now
            low=m['MemAvailable']<max(2*1024**2,m['MemTotal']//20)
            low_since=(low_since or now) if low else None
            thrash_since=(thrash_since or now) if rate>=32 else None
            try:
                pressure=Path('/proc/pressure/memory').read_text()
                psi=float(re.search(r'^full avg10=([\d.]+)',pressure,re.M).group(1))
            except (OSError,AttributeError):psi=0
            try:
                stat=Path(f'/proc/{self.process.pid}/stat').read_text().rpartition(')')[2].split()
                rss=int(stat[21])*os.sysconf('SC_PAGE_SIZE');ticks=int(stat[11])+int(stat[12])
            except (OSError,ValueError,IndexError):rss=ticks=0
            gpu=evidence.gpu_sample()
            sample=dict(monotonic=now,available_kib=m['MemAvailable'],swap_kib=swap,rss_bytes=rss,cpu_ticks=ticks,
                        gpu_busy_percent=gpu['gpu_busy_percent'],gpu_whole_device=gpu,pswpin=v['pswpin'],pswpout=v['pswpout'],swapout_rate_mib_s=rate,memory_psi_full_avg10=psi)
            self.samples.append(sample)
            self.reason=risk(m['MemAvailable'],m['MemTotal'],now-low_since if low_since else 0,rate,now-thrash_since if thrash_since else 0,psi)
            if (HOME/'STOP').exists():self.reason='USER_STOP'
            if now-last>5:
                audit=shared.fault_audit(self.start)
                if audit['read_exit'] or audit['faults']:self.reason='KERNEL_AUDIT_UNAVAILABLE' if audit['read_exit'] else 'KERNEL_FAULT'
                if shutil.disk_usage(ROOT).free<20*1024**3:self.reason='DISK_GUARD'
                evidence.save(self.directory/'live-resource.json',sample);last=now
            if self.reason:
                shared.stop(self.process);break
            self.done.wait(.5)

    def summary(self):
        result=super().summary()
        result['policy']='No fixed swap-growth cap. Emergency <1 GiB; sustained <max(2 GiB,5% OS RAM) 5s; swapout >=32 MiB/s 10s; full memory PSI >=20% with pressure 10s.'
        result['gpu_whole_device_peak']={name:max([s['gpu_whole_device'][name] for s in self.samples if s['gpu_whole_device'][name] is not None],default=None) for name in ['gpu_busy_percent','mem_info_vram_used','mem_info_gtt_used']}
        result['peak_swapout_rate_mib_s']=max([s['swapout_rate_mib_s'] for s in self.samples],default=0)
        return result


ORIGINAL_REQUEST=perf.request
TOKEN_CACHE=None

def measured_request(directory,label,tokens=128,port=perf.PORT):
    global TOKEN_CACHE
    if TOKEN_CACHE is None:
        count=PROFILE['prompt_tokens']
        text=PROMPT_SOURCE*max(8,count//60+2)
        response=evidence.api('tokenize',dict(content=text,add_special=False),base=f'http://127.0.0.1:{port}/')
        TOKEN_CACHE=response['tokens'][:count]
        if len(TOKEN_CACHE)<count:raise ValueError('tokenized prompt shorter than required')
    perf.PROMPT=TOKEN_CACHE
    return ORIGINAL_REQUEST(directory,label,4 if label=='smoke' else PROFILE['output_tokens'],port)


def base_config(backend,context=4096,prompt_tokens=512,output_tokens=128,layers=None):
    return dict(name=f'{backend}-ctx{context}-pp{prompt_tokens}-tg{output_tokens}'+(f'-layers{layers}' if layers is not None else ''),
                backend=backend,context=context,prompt_tokens=prompt_tokens,output_tokens=output_tokens,
                threads=len(os.sched_getaffinity(0)),threads_batch=len(os.sched_getaffinity(0)),
                layers=0 if backend=='cpu' else (99 if layers is None else layers),batch=2048,ubatch=512,fa='auto',cache_k='f16',cache_v='f16',mtp=False)


def worker(config_file):
    global PROFILE
    cfg=json.loads(config_file.read_text());PROFILE=cfg['profile'];model=cfg['model']
    perf.MODEL=dict(model_id=model['id']);perf.PATH=ROOT/'models/GGUF'/model['file']
    perf.Guard=HardwareGuard;perf.request=measured_request
    if cfg.get('task'):
        directory=config_file.parent/'engineering';directory.mkdir()
        command=perf.command(PROFILE);evidence.save(directory/'server-command.json',command)
        stream=(directory/'server.log').open('w');server=subprocess.Popen(command,cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True);stream.close()
        guard=HardwareGuard(server,directory)
        try:
            with guard:
                deadline=time.monotonic()+240
                while time.monotonic()<deadline and server.poll() is None and not guard.reason:
                    try:
                        if evidence.api('health',base=f'http://127.0.0.1:{perf.PORT}/').get('status')=='ok':break
                    except OSError:pass
                    time.sleep(.5)
                else:raise RuntimeError('engineering model not ready')
                if PROFILE['backend']!='cpu' and not perf.positive_offload_lines((directory/'server.log').read_text()):raise RuntimeError('GPU execution unproven')
                env=dict(AI370_LOCAL_MODEL=model['id'],AI370_LOCAL_BASE_URL=f'http://127.0.0.1:{perf.PORT}/v1',AI370_ROSS_DOCSEARCH_URL='http://172.18.0.4:8080/mcp/doc-search',AI370_ROSS_AB_OUT=str(directory/cfg['task']),AI370_MODEL_LAB_SERVER_PID=str(server.pid),AI370_MODEL_LAB_MODEL_PATH=str(perf.PATH),AI370_MODEL_LAB_REQUEST_TIMEOUT='600',AI370_MODEL_LAB_TOTAL_TIMEOUT='2400',AI370_MODEL_LAB_COMPLETION_CAP='2048',AI370_MODEL_LAB_TOOL_CALL_CAP='14',AI370_ROSS_CONTEXT_CHARS='1800',AI370_ROSS_MCP_CHARS='1200')
                os.environ.update(env)
                trial_config=directory/'config.json';evidence.save(trial_config,dict(task=cfg['task'],arm='B',rep=cfg['rep']))
                started=time.monotonic();evidence.trial(trial_config)
                row=json.loads((directory/'trial-result.json').read_text());row['elapsed_seconds_including_synthesis']=time.monotonic()-started
        finally:
            shared.stop(server)
            result=dict(status=locals().get('row',{}).get('status','FAIL'),detail=locals().get('row'),resources=guard.summary(),kernel_audit=shared.fault_audit(guard.start),model=model['id'],profile=PROFILE)
            if guard.reason:result['status']='CANCELLED' if guard.reason=='USER_STOP' else 'RESOURCE_OR_KERNEL_GUARD'
            evidence.save(config_file.parent/'result.json',result)
    else:
        try:
            row=perf.measure(PROFILE,config_file.parent)
        finally:
            file=config_file.parent/PROFILE['name']/'result.json'
            if file.exists():
                row=json.loads(file.read_text());row.update(model=model['id'],phase=cfg['phase'])
                evidence.save(config_file.parent/'result.json',row)


def run_case(model,profile,directory,phase,task=None,rep=None):
    global CHILD
    directory.mkdir(parents=True)
    signature=(model['id'],profile['backend'],profile['context'],profile['layers'])
    if signature in BLOCKED_PROFILES:
        row=dict(status='BLOCKED_PRIOR_RESOURCE_GATE',model=model['id'],config=profile,phase=phase,reason=BLOCKED_PROFILES[signature],actual_executed=False,directory=str(directory))
        evidence.save(directory/'controller-result.json',row)
        return row
    config=dict(model=model,profile=profile,phase=phase,task=task,rep=rep)
    evidence.save(directory/'config.json',config)
    evidence.notify(status='RUNNING',stage='PERFORMANCE_'+phase,model=model['id'],backend=profile['backend'],task=task or profile['name'],rep=rep,context=profile['context'])
    with (directory/'worker-stdout.log').open('w') as out,(directory/'worker-stderr.log').open('w') as err:
        CHILD=subprocess.Popen([sys.executable,str(Path(__file__).resolve()),'--worker',str(directory/'config.json')],cwd=ROOT,stdout=out,stderr=err,start_new_session=True)
        started=time.monotonic()
        try:
            while CHILD.poll() is None:
                if STOP.is_set() or (HOME/'STOP').exists():raise InterruptedError('USER_STOP')
                if time.monotonic()-started>3000:raise TimeoutError('PROFILE_WALL_TIMEOUT')
                time.sleep(.5)
            result_file=directory/'result.json'
            result=json.loads(result_file.read_text()) if result_file.exists() else dict(status='HARNESS_INVALID',error='worker produced no result')
        finally:shared.stop(CHILD);CHILD=None
    result.update(directory=str(directory),profile_wall_seconds=time.monotonic()-started,actual_executed=True)
    reason=result.get('resources',{}).get('guard')
    error=str(result.get('error','')).lower()
    if reason or any(x in error for x in ['out of memory','device lost','illegal memory access']):
        BLOCKED_PROFILES[signature]=reason or error
    evidence.save(directory/'controller-result.json',result);evidence.manifest(directory)
    return result


def severe(row):
    audit=row.get('kernel_audit',{})
    return bool(audit.get('faults')) or audit.get('read_exit',0)!=0 or row.get('resources',{}).get('guard') in {'KERNEL_FAULT','KERNEL_AUDIT_UNAVAILABLE'}


def safe(row):return row.get('status')=='PASS' and not row.get('resources',{}).get('guard') and not severe(row)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--worker',type=Path);parser.add_argument('--continuous',action='store_true');args=parser.parse_args()
    if args.worker:return worker(args.worker)
    if not args.continuous:parser.error('Requires --continuous')
    global CHILD
    os.umask(0o077);HOME.mkdir(parents=True,exist_ok=True);lock=evidence.LOCK.open('a+');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    from verify_local_agent_runtime import verify
    from local_agent_ui import load_command
    verify(smoke=False)
    if any(m.get('is_busy') for m in evidence.api('health').get('all_models_loaded',[])):raise RuntimeError('MODEL_BUSY')
    with socket.socket() as s:s.bind(('127.0.0.1',perf.PORT))
    evidence.RUN=ROOT/'output/HARDWARE_MODEL_PERFORMANCE'/evidence.datetime.now().astimezone().strftime('%Y%m%dT%H%M%S%z');evidence.RUN.mkdir(parents=True)
    (HOME/'STOP').unlink(missing_ok=True)
    for sig in [signal.SIGTERM,signal.SIGINT]:signal.signal(sig,lambda *_:STOP.set())
    original=verify(smoke=False);packages=evidence.package_state();evidence.save(evidence.RUN/'original-runtime.json',original);evidence.save(evidence.RUN/'original-packages.json',packages)
    protocol=dict(started=evidence.stamp(),scope='practical workstation performance, not utilization for its own sake',models=evidence.roster(),speed='512 input tokens / 128 output, three repetitions, 4K context',capacity='8K/16K/32K allocation with 2K/4K/8K prompt and 256 output; tested allocation and tested input separately',engineering='best observed safe 16K profile, Ross T1/T2/T3 three each',guard='hardware-aware sustained pressure, no 64 MiB swap-growth cap',stop='user STOP or genuine safety gate',formal_recipe_changes=False)
    evidence.save(evidence.RUN/'protocol.json',protocol)
    for name in ['run_workstation_model_performance.py','run_model_endurance.py','optimize_qwen_performance.py','local_agent.py']:
        target=evidence.RUN/'harness'/name;target.parent.mkdir(exist_ok=True);shutil.copy2(ROOT/'scripts'/name,target)
    reason='USER_STOP';rows=[];cycle=1;unloaded=False;unsafe=False;integrity={}
    def retain(row):
        rows.append(row)
        with (evidence.RUN/'results.jsonl').open('a') as f:f.write(json.dumps(row,ensure_ascii=False)+'\n');f.flush();os.fsync(f.fileno())
        evidence.save(evidence.RUN/'summary.json',[dict(model=r.get('model'),phase=r.get('phase'),status=r['status'],backend=r.get('config',r.get('profile',{})).get('backend'),context=r.get('config',r.get('profile',{})).get('context'),prompt_tps=r.get('median_prompt_tokens_per_second'),generation_tps=r.get('median_generation_tokens_per_second'),latency=r.get('median_elapsed_seconds'),guard=r.get('resources',{}).get('guard'),directory=r.get('directory')) for r in rows])
        if severe(row):raise RuntimeError('SEVERE_KERNEL_GATE')
    try:
        unloaded=True;subprocess.run(['/usr/bin/lemonade','unload',evidence.FORMAL],capture_output=True,check=True,timeout=45)
        if evidence.api('health').get('model_loaded'):raise RuntimeError('FORMAL_STILL_LOADED')
        while not STOP.is_set() and not (HOME/'STOP').exists():
            winners={};good16={}
            # All four models receive basic speed data before long engineering tasks.
            for model in evidence.roster():
                if evidence.package_state()!=packages:raise RuntimeError('PROTECTED_STACK_CHANGED')
                evidence.notify(status='RUNNING',stage='PERFORMANCE_INTEGRITY',model=model['id'],cycle=cycle)
                if model['id'] not in integrity:integrity[model['id']]=evidence.hash_model(model);evidence.save(evidence.RUN/'model-integrity.json',integrity)
                stat=Path(integrity[model['id']]['path']).stat()
                if stat.st_size!=integrity[model['id']]['bytes'] or stat.st_mtime_ns!=integrity[model['id']]['mtime_ns']:raise RuntimeError('MODEL_CHANGED')
                candidates=[]
                for backend in ['vulkan','cpu','hip']:
                    profile=base_config(backend)
                    if backend=='hip':
                        probe=base_config('hip',prompt_tokens=64,output_tokens=8,layers=16)
                        test=run_case(model,probe,evidence.RUN/f'cycle-{cycle:03d}'/model['id']/'hip-probe','PROBE');retain(test)
                        if not safe(test):continue
                    row=run_case(model,profile,evidence.RUN/f'cycle-{cycle:03d}'/model['id']/profile['name'],'SPEED');retain(row)
                    if safe(row):candidates.append(row)
                if candidates:winners[model['id']]=min(candidates,key=lambda r:r['median_elapsed_seconds'])['config']
            for model in evidence.roster():
                best=winners.get(model['id'])
                if not best:continue
                for context,prompt in [(8192,2048),(16384,4096),(32768,8192)]:
                    profile=dict(best,name=f'capacity-{best["backend"]}-{context}',context=context,prompt_tokens=prompt,output_tokens=256)
                    row=run_case(model,profile,evidence.RUN/f'cycle-{cycle:03d}'/model['id']/profile['name'],'CAPACITY');retain(row)
                    if not safe(row):break
                    if context==16384:good16[model['id']]=profile
                profile=good16.get(model['id'])
                if profile:
                    for rep in [1,2,3]:
                        for task in ['T1','T2','T3']:
                            row=run_case(model,profile,evidence.RUN/f'cycle-{cycle:03d}'/model['id']/f'engineering-{task}-{rep}','ENGINEERING',task=task,rep=rep);row['phase']='ENGINEERING';retain(row)
                            if row.get('resources',{}).get('guard'):break
                        else:continue
                        break
            if not winners:reason='NO_SAFE_SPEED_CONFIGURATION';break
            cycle+=1
    except InterruptedError:reason='USER_STOP'
    except BaseException as exc:
        reason=f'{type(exc).__name__}: {exc}';unsafe='SEVERE_KERNEL_GATE' in reason or 'PROTECTED_STACK_CHANGED' in reason
    finally:
        shared.stop(CHILD)
        evidence.notify(status='RESTORING',stage='PERFORMANCE_RESTORE',reason=reason)
        restoration='NOT_NEEDED'
        if unloaded and unsafe:restoration='DEFERRED_SAFETY'
        elif unloaded:
            try:
                r=subprocess.run(load_command(evidence.FORMAL),capture_output=True,text=True,timeout=180);(evidence.RUN/'restore.log').write_text(r.stdout+r.stderr)
                if r.returncode:raise RuntimeError('formal load failed')
                evidence.save(evidence.RUN/'restored-runtime.json',verify(smoke=False));restoration='PASS'
            except Exception as exc:restoration='FAIL: '+str(exc)
        evidence.notify(status='STOPPED' if reason=='USER_STOP' and restoration=='PASS' else 'BLOCKED',stage='PERFORMANCE_FINISHED',reason=reason,formal_restoration=restoration,recorded_cases=len(rows))
        evidence.manifest(evidence.RUN);fcntl.flock(lock,fcntl.LOCK_UN);lock.close()


if __name__=='__main__':main()
