#!/usr/bin/env python3
"""Read-only semantic audit of retained model/FPGA evidence, never a workload.

This verifies historical results and their scope. It cannot establish current
inference, physical hardware availability, air-gap or clean-host rebuild PASS.
"""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'docs/LOCAL_MODEL_LAB/evidence'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def manifest(base):
    count = 0
    for line in (base/'SHA256SUMS').read_text().splitlines():
        expected, name = line.split('  ', 1)
        path = base/name
        require(not Path(name).is_absolute() and '..' not in Path(name).parts, 'unsafe manifest path')
        require(path.resolve().is_relative_to(base.resolve()) and not path.is_symlink(), 'manifest escapes evidence root')
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        require(digest == expected, 'checksum mismatch: '+name)
        count += 1
    require(count > 0, 'empty checksum manifest')
    return count


def trace_checks(events, task, ross):
    calls = [e for e in events if e['event']=='tool_call']
    tools = {e.get('name') for e in calls if e.get('result',{}).get('ok')}
    if ross:
        require({'ross_skill_read','ross_doc_search'} <= tools, 'missing real Ross prerequisite calls')
        docs = [e['result'] for e in calls if e.get('name')=='ross_doc_search' and e.get('result',{}).get('ok')]
        require(any(r.get('mcp_tool')=='vivado_doc_search' and r.get('server',{}).get('name')=='AMD Doc Search' for r in docs), 'local KB MCP identity missing')
    else:
        require(not any(e.get('name','').startswith('ross_') for e in calls), 'Non-Ross arm contaminated')
    name = 'run_hls' if task=='T3' else 'run_xsim'
    runs = [e['result'] for e in events if e['event']=='tool_result' and e.get('name')==name]
    require(len(runs)>=2 and not runs[0]['ok'] and runs[0]['exit_code']!=0, 'missing actual baseline failure')
    last = runs[-1]
    require(last['ok'] and last['exit_code']==0, 'missing final validation success')
    require(last.get('csim_pass') and last.get('csynth_pass') if task=='T3' else last.get('terminal_pass_marker'), 'missing terminal markers')
    patches = [e for e in calls if e.get('name') in {'apply_patch','apply_replacement'} and e.get('result',{}).get('ok')]
    require(patches, 'no applied model patch')
    # Match each accepted request against the actual Qwen/Gemma response arguments.
    authored = []
    for e in events:
        if e['event']=='model_response':
            for choice in e.get('response',{}).get('choices',[]):
                for c in choice.get('message',{}).get('tool_calls',[]):
                    function = c.get('function',{})
                    try:
                        authored.append((function.get('name'),json.loads(function.get('arguments','{}'))))
                    except (ValueError,TypeError):
                        pass
    require(all((p['name'],p['arguments']) in authored for p in patches), 'accepted patch not present in model response')
    return {'validation_runs':len(runs),'model_authored_accepted_patches':len(patches),'ross':ross}


def cohort(base):
    d=json.loads((base/'result.json').read_text())
    require(d['formal_model_restoration']=='PASS','prior service restoration failed')
    audited=[]
    for key in ['qwen38','gemma4_31b']:
        require(d['models'][key]['runtime']['status']=='READY','missing recorded runtime readiness')
        for task in ['T1','T2','T3']:
            rows=d['models'][key]['tasks'][task]['trials']
            require(len(rows)==6 and {r['trial'] for r in rows}=={'A1','A2','A3','B1','B2','B3'}, 'incomplete cohort')
            for row in rows:
                require(row['status']=='PASS','retained successful cohort status changed')
                trial=base/key/task/row['trial']
                events=[json.loads(l) for l in (trial/'local-agent-trace.jsonl').read_text().splitlines()]
                audit=trace_checks(events,task,row['arm']=='ross')
                if task!='T3':
                    require(row['vivado_synthesis']['status']=='PASS' and row['vivado_synthesis']['exit_code']==0,'synthesis not successful')
                    require((trial/'workspace/post-agent-synthesis/utilization.rpt').stat().st_size>0,'utilization missing')
                    hashes=row['source_sha256_after']
                    if isinstance(hashes,str):
                        hashes={'rtl/local_model_axi_lite.v':hashes}
                    for name,expected in hashes.items():
                        require(hashlib.sha256((trial/'workspace'/name).read_bytes()).hexdigest()==expected,'retained RTL final hash mismatch')
                audited.append(dict(model=key,task=task,trial=row['trial'],**audit))
    return {'retained_trials_verified':len(audited),'trials':audited,'scope':'historical bounded XSim/HLS/model provenance; not a fresh workload'}


def optimization(base):
    d=json.loads((base/'result.json').read_text())
    passed=[r for r in d['rows'] if r['status']=='PASS']
    failed=[r for r in d['rows'] if r['status']!='PASS']
    require(len(passed)==20 and len(failed)==1,'unexpected measurement inventory')
    for r in passed:
        require(len(r['trials'])==3 and all(t['prompt_tokens']==64 and t['output_tokens']==32 for t in r['trials']), 'measurement repetitions/token counts invalid')
        require(not r['resources']['guard'] and not r['kernel_audit']['faults'] and r['kernel_audit']['read_exit']==0,'unsafe trial passed')
    require(failed[0]['config']['name']=='hip-99-threads-18' and failed[0]['resources']['guard'].startswith('SWAP_GROWTH_OR_SWAPOUT'),'resource stop hidden/misclassified')
    require(not failed[0]['trials'],'aborted load given throughput measurements')
    require(d['formal_service_restored']=='PASS' and d['formal_argv_identical'] and d['all_package_versions_unchanged'],'restoration/protected-package assertion failed')
    require(json.loads((base/'original-runtime.json').read_text())==json.loads((base/'restored-runtime.json').read_text()),'actual argv differ')
    events=[json.loads(l) for l in (base/'formal-agent-readiness/trace.jsonl').read_text().splitlines()]
    require(any(e['event']=='tool_call' and e.get('name')=='read_file' and e.get('result',{}).get('ok') for e in events),'agent read tool missing')
    require(json.loads((base/'formal-agent-readiness/stdout.json').read_text())['result']=='AI370_QWEN_RESTORE_OK','agent result mismatch')
    require(d['final_status']=='PARTIAL_SAFE_PROFILES_READY','optimization limits lost')
    require(all(v['status']=='RECOMMENDED_NOT_APPLIED' for v in d['profiles'].values()),'profile promotion not authorized by evidence')
    return {'successful_configurations':len(passed),'excluded_configurations':len(failed),'service_restore':'historical PASS','scope':'historical optimization; ROCm safety-deferred; no current inference assertion'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    result={'scope':'read-only saved evidence audit; no model/tool/hardware execution','checks':[]}
    for name,path,check in [('practical-cohort',BASE/'practical-2026-10-13',cohort),('qwen-optimization',BASE/'qwen-performance-2026-10-14',optimization)]:
        try:
            count=manifest(path)
            detail=check(path)
            result['checks'].append(dict(name=name,status='PASS',checksum_entries=count,detail=detail))
        except (OSError,ValueError,KeyError,TypeError) as exc:
            result['checks'].append(dict(name=name,status='FAIL',error=str(exc)))
    result['status']='FAIL' if any(c['status']=='FAIL' for c in result['checks']) else 'PASS'
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))
    return int(result['status']=='FAIL')


if __name__=='__main__':
    raise SystemExit(main())
