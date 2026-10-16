#!/usr/bin/env python3
"""Bounded on-host WAN-isolated engineering test with an independent NM restore.

Requires an externally armed systemd restore timer named in the local plan.
Only active device never-default properties change; saved profiles/NICs do not.
Never treat this route isolation as physical air-gap certification.
"""
import argparse
import errno
import hashlib
import json
import os
import signal
import socket
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def write(path,data):
    path.write_text(json.dumps(data,indent=2)+'\n')


def command(args,timeout=25):
    return subprocess.run(args,capture_output=True,text=True,timeout=timeout)


def routes():
    return {family:json.loads(subprocess.check_output(['ip','-j',family,'route','show','default'],text=True)) for family in ['-4','-6']}


def nic_hash(device):
    return hashlib.sha256((Path('/sys/class/net')/device/'address').read_bytes()).hexdigest()


def restore(plan):
    r=command(['nmcli','--wait','20','device','modify',plan['device'],'ipv4.never-default',plan['ipv4'],'ipv6.never-default',plan['ipv6']])
    saved=command(['nmcli','-g','ipv4.never-default,ipv6.never-default','connection','show',plan['connection_uuid']])
    result={'timestamp':datetime.now().astimezone().isoformat(),'exit_code':r.returncode,'stdout':r.stdout,'stderr':r.stderr,'default_routes':routes(),
            'persistent_never_default':saved.stdout.splitlines(),'persistent_profile_unchanged':saved.returncode==0 and saved.stdout.splitlines()==[plan['ipv4'],plan['ipv6']]}
    write(Path(plan['output'])/'restore-result.json',result)
    return result


def public_probe():
    result=[]
    for family,address in [(socket.AF_INET,'1.1.1.1'),(socket.AF_INET6,'2606:4700:4700::1111')]:
        with socket.socket(family,socket.SOCK_STREAM) as s:
            s.settimeout(2)
            try:s.connect((address,443));value=0
            except OSError as e:value=e.errno
        result.append({'family':int(family),'destination':address,'errno':value})
    return result


def run(plan):
    out=Path(plan['output']);started=datetime.now().astimezone().isoformat(timespec='seconds')
    result=dict(status='RUNNING',started=started,scope='WAN route isolation; NOT physical air gap')
    write(out/'result.json',result)
    proc=None
    changed=False
    def interrupted(*_):
        raise InterruptedError('offline acceptance interrupted')
    signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted)
    try:
        timer=command(['systemctl','--user','is-active',plan['restore_unit']+'.timer'])
        if timer.returncode or timer.stdout.strip()!='active':
            raise RuntimeError('Independent restore timer not active; refusing network changes')
        if routes()!=plan['routes'] or nic_hash(plan['device'])!=plan['nic_hash']:
            raise RuntimeError('Network changed since preflight')
        # Give the launching remote tool time to return before removing the WAN route.
        time.sleep(5)
        changed=True  # restore even if nmcli partially applies then returns an error
        r=command(['nmcli','--wait','20','device','modify',plan['device'],'ipv4.never-default','yes','ipv6.never-default','yes'])
        (out/'temporary-network-change.log').write_text(r.stdout+r.stderr)
        if r.returncode:raise RuntimeError('Temporary device modification rejected')
        # NetworkManager's accepted D-Bus reapply can precede kernel route updates.
        settled=time.monotonic()+5
        while any(routes().values()) and time.monotonic()<settled:
            time.sleep(.25)
        write(out/'routes-after-reapply.json',routes())
        if any(routes().values()):raise RuntimeError('Public default route remains after settling; no offline claim')
        if nic_hash(plan['device'])!=plan['nic_hash']:raise RuntimeError('NIC identity changed')
        probes=public_probe();write(out/'offline-network-proof.json',dict(default_routes=routes(),nic_hash_unchanged=True,link_state=(Path('/sys/class/net')/plan['device']/'operstate').read_text().strip(),public_tcp_probes=probes))
        if not all(p['errno']==errno.ENETUNREACH for p in probes):raise RuntimeError('External TCP did not fail with ENETUNREACH')
        # Reuse the unchanged T1 corpus; invoke Local Agent directly, not six-trial main().
        os.environ['AI370_ROSS_AB_OUT']=str(out/'T1')
        import run_ross_ab_t1 as t1
        work=t1.seed('B',1)
        task=(work/'TASK_INSTRUCTIONS.md').read_text()+'\nUser engineering request: '+(work/'TASK_SPEC.md').read_text()
        cmd=[sys.executable,str(ROOT/'scripts/local_agent.py'),'--workspace',str(work),'--task',task,
             '--model','Qwen3.8-27B-UD-Q4_K_XL','--base-url','http://127.0.0.1:13305/api/v1',
             '--timeout','180','--total-timeout','400','--max-completion-tokens','2048','--max-calls','12',
             '--xsim','--editable-path','rtl/local_model_axi_lite.v','--trace',str(out/'local-agent-trace.jsonl'),
             '--ross-docsearch-url','http://172.18.0.4:8080/mcp/doc-search','--ross-context-chars','1800','--ross-mcp-chars','1200']
        write(out/'agent-command.json',cmd)
        import run_local_model_lab_practical as guard
        mem=guard.memory();swap0=mem['SwapTotal']-mem['SwapFree'];begin=time.monotonic();last_audit=0
        with (out/'agent-stdout.json').open('w') as stdout,(out/'agent-stderr.log').open('w') as stderr:
            proc=subprocess.Popen(cmd,cwd=ROOT,stdout=stdout,stderr=stderr,start_new_session=True)
            while proc.poll() is None:
                m=guard.memory()
                if m['MemAvailable']<max(6*1024**2,m['MemTotal']//8) or m['SwapTotal']-m['SwapFree']-swap0>64*1024:
                    raise RuntimeError('Memory/swap guard')
                if time.monotonic()-begin>420:raise TimeoutError('Bounded offline task timeout')
                if time.monotonic()-last_audit>5:
                    audit=guard.fault_audit(started)
                    if audit['read_exit'] or audit['faults']:raise RuntimeError('Kernel audit failed')
                    if any(routes().values()):raise RuntimeError('WAN route reappeared during task')
                    last_audit=time.monotonic()
                time.sleep(.5)
        data=json.loads((out/'agent-stdout.json').read_text().splitlines()[-1])
        if proc.returncode or data.get('status')!='PASS':raise RuntimeError('Local Agent did not PASS')
        import audit_local_engineering_evidence as evidence
        events=[json.loads(l) for l in (out/'local-agent-trace.jsonl').read_text().splitlines()]
        result['engineering_proof']=evidence.trace_checks(events,'T1',True)
        result['agent_result']=data
        result['elapsed_seconds']=round(time.monotonic()-begin,3)
        result['final_offline_routes']=routes()
        if any(result['final_offline_routes'].values()) or nic_hash(plan['device'])!=plan['nic_hash']:
            raise RuntimeError('Offline/NIC invariants not held')
        result['status']='WAN_OFFLINE_ENGINEERING_PASS'
    except BaseException as exc:
        result.update(status='FAIL',error=f'{type(exc).__name__}: {exc}')
    finally:
        if proc is not None:
            import run_local_model_lab_practical as guard
            guard.stop(proc)
        if changed:
            try:
                restored=restore(plan)
                result['network_restoration']='PASS' if restored['exit_code']==0 and restored['persistent_profile_unchanged'] and restored['default_routes']['-4'] and nic_hash(plan['device'])==plan['nic_hash'] else 'FAIL'
            except Exception as exc:result['network_restoration']='FAIL: '+str(exc)
            if result['network_restoration']!='PASS':result['status']='FAIL'
        else:result['network_restoration']='NOT_NEEDED'
        result['completed']=datetime.now().astimezone().isoformat()
        write(out/'result.json',result)
        if result['network_restoration'] in ['PASS','NOT_NEEDED']:
            command(['systemctl','--user','stop',plan['restore_unit']+'.timer'])
    return int(result['status']!='WAN_OFFLINE_ENGINEERING_PASS')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--restore-plan',type=Path)
    group.add_argument('--run-plan',type=Path)
    args=parser.parse_args();plan=json.loads((args.restore_plan or args.run_plan).read_text())
    return int(restore(plan)['exit_code']!=0) if args.restore_plan else run(plan)


if __name__=='__main__':raise SystemExit(main())
