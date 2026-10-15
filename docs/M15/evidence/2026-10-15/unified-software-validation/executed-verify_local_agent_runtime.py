#!/usr/bin/env python3
"""Check the already resident formal Qwen; never load/switch a model."""
import argparse
import json
import os
import urllib.request
from datetime import datetime
from pathlib import Path
import run_local_model_lab as lab


def verify(profile='ENGINEERING',smoke=True):
    model=lab.model_for(lab.load_config(),'qwen38')
    argv=lab.active_llama_server(model['runtime_model_path'])
    if not argv:
        raise RuntimeError('Formal model absent; refusing auto-load or a second large model')
    backend,context,layers=('vulkan','16384','99') if profile=='ENGINEERING' else ('cpu','8192','0')
    if f'build-{backend}/' not in argv[0]:
        raise RuntimeError('Backend mismatch; implicit fallback is forbidden')
    for flag,value in [('--ctx-size',context),('--n-gpu-layers',layers),('--threads',str(len(os.sched_getaffinity(0)))),('--threads-batch',str(len(os.sched_getaffinity(0))))]:
        if flag not in argv or argv[argv.index(flag)+1]!=value:
            raise RuntimeError('Formal argument mismatch: '+flag)
    reference=json.loads((lab.ROOT/'docs/LOCAL_MODEL_LAB/evidence/qwen-performance-2026-10-14/result.json').read_text())['integrity']
    stat=Path(model['runtime_model_path']).stat()
    if stat.st_size!=reference['bytes'] or stat.st_mtime_ns!=reference['mtime_ns'] or reference['sha256']!=model['sha256']:
        raise RuntimeError('Model changed since full SHA256; requires fresh integrity verification')
    cfg=json.loads((Path.home()/'.config/lemonade/config.json').read_text())
    settings={k:cfg.get(k) for k in ['offline','no_fetch_executables','auto_check_model_updates','auto_update_models']}
    settings['telemetry_enabled']=cfg.get('telemetry',{}).get('enabled')
    if settings!={'offline':True,'no_fetch_executables':True,'auto_check_model_updates':False,'auto_update_models':False,'telemetry_enabled':False}:
        raise RuntimeError('Offline/telemetry settings mismatch')
    result=dict(status='PASS',profile=profile,backend=backend,argv=argv,model=model['model_id'],offline_settings=settings,
                integrity='Prior full SHA256 record + unchanged size/mtime; not a fresh full rehash',
                physical_airgap='NOT_TESTED',fresh_inference='NOT_TESTED')
    if smoke:
        body=dict(model=model['model_id'],messages=[dict(role='user',content='Say READY.')],max_tokens=4,temperature=0)
        req=urllib.request.Request('http://127.0.0.1:13305/api/v1/chat/completions',data=json.dumps(body).encode(),headers={'Content-Type':'application/json'})
        with urllib.request.urlopen(req,timeout=90) as r:reply=json.load(r)
        if not reply.get('choices'):
            raise RuntimeError('No completion')
        result.update(fresh_inference='PASS',reply=reply)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile',choices=['ENGINEERING','SAFE'],default='ENGINEERING')
    parser.add_argument('--no-inference',action='store_true')
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    try:
        result=verify(args.profile,not args.no_inference)
    except (OSError,ValueError,RuntimeError) as exc:
        result=dict(status='FAIL',error=str(exc),profile=args.profile)
    result['captured_at']=datetime.now().astimezone().isoformat()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ['status','profile']}))
    return int(result['status']!='PASS')


if __name__=='__main__':
    raise SystemExit(main())
