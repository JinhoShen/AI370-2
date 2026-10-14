#!/usr/bin/env python3
"""Bounded, sequential Qwen optimization; never saves Lemonade options.

Raw SSE, commands, allocation/DRM samples and kernel audits are retained.
Only temporary owned servers are terminated. Original formal argv is restored.
"""
import argparse
import hashlib
import json
import os
import re
import signal
import statistics
import subprocess
import threading
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import run_local_model_lab_practical as shared
import run_local_model_lab as lab

ROOT = lab.ROOT
PORT = 18082
MODEL = lab.model_for(lab.load_config(), 'qwen38')
PATH = Path(MODEL['runtime_model_path'])
PROMPT = ('Explain the distinction between AXI4-Lite write address and write data handshakes. '
          'Describe how a register block should preserve a pending address until data is accepted, '
          'how it emits the response, and how a self-checking simulation detects lost transactions. '
          'Use concise engineering prose. Do not produce commands.\nAnswer:')


def now():
    return datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')


def vm():
    return {r.split()[0]: int(r.split()[1]) for r in Path('/proc/vmstat').read_text().splitlines()}


def positive_offload_lines(log):
    return [line for line in log.splitlines() if re.search(r'offloaded [1-9]\d*/\d+ layers', line, re.I)]


class Guard:
    def __init__(self, process, directory):
        self.process, self.directory = process, directory
        self.start = now()
        self.base = shared.memory()
        self.swap0 = self.base['SwapTotal'] - self.base['SwapFree']
        self.vm0 = vm()
        self.reason = None
        self.done = threading.Event()
        self.samples = []
        self.thread = threading.Thread(target=self.watch, daemon=True)

    def watch(self):
        last = 0
        while not self.done.is_set() and self.process.poll() is None:
            m = shared.memory()
            swap = m['SwapTotal'] - m['SwapFree']
            v = vm()
            try:
                stat = Path(f'/proc/{self.process.pid}/stat').read_text().rpartition(')')[2].split()
                rss = int(stat[21]) * os.sysconf('SC_PAGE_SIZE')
                ticks = int(stat[11]) + int(stat[12])
            except (OSError, ValueError, IndexError):
                rss, ticks = 0, 0
            gpu = Path('/sys/class/drm/card1/device/gpu_busy_percent')
            try:
                busy = int(gpu.read_text())
            except (OSError, ValueError):
                busy = None
            self.samples.append(dict(monotonic=time.monotonic(), available_kib=m['MemAvailable'],
                                     swap_kib=swap, rss_bytes=rss, cpu_ticks=ticks, gpu_busy_percent=busy,
                                     pswpin=v['pswpin'], pswpout=v['pswpout']))
            if m['MemAvailable'] < max(6 * 1024**2, m['MemTotal'] // 8):
                self.reason = 'MEMORY_SAFETY_FLOOR'
            # 64 MiB tolerates unrelated small background changes, not model spilling.
            if swap - self.swap0 > 64 * 1024 or (v['pswpout'] - self.vm0['pswpout']) * os.sysconf('SC_PAGE_SIZE') > 64 * 1024**2:
                self.reason = 'SWAP_GROWTH_OR_SWAPOUT; configuration excluded'
            if time.monotonic() - last > 10:
                audit = shared.fault_audit(self.start)
                if audit['read_exit'] or audit['faults']:
                    self.reason = 'KERNEL_AUDIT_UNAVAILABLE' if audit['read_exit'] else 'KERNEL_FAULT'
                last = time.monotonic()
            if self.reason:
                shared.stop(self.process)
                break
            self.done.wait(.5)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *_):
        self.done.set()
        self.thread.join(timeout=20)
        shared.write_json(self.directory / 'resource-samples.json', self.samples)

    def summary(self):
        s = self.samples
        return dict(guard=self.reason, peak_process_rss_mib=max((x['rss_bytes'] for x in s), default=0)/1024**2,
                    minimum_available_mib=min((x['available_kib'] for x in s), default=0)/1024,
                    peak_swap_mib=max((x['swap_kib'] for x in s), default=self.swap0)/1024,
                    swap_growth_mib=max(0, max((x['swap_kib'] for x in s), default=self.swap0)-self.swap0)/1024,
                    swapout_mib=max((x['pswpout']-self.vm0['pswpout'] for x in s), default=0)*os.sysconf('SC_PAGE_SIZE')/1024**2,
                    mean_gpu_busy_percent=statistics.mean([x['gpu_busy_percent'] for x in s if x['gpu_busy_percent'] is not None]) if any(x['gpu_busy_percent'] is not None for x in s) else None)


def request(directory, label, tokens=32, port=PORT):
    payload = dict(prompt=PROMPT, n_predict=tokens, temperature=0, seed=42,
                   ignore_eos=True, cache_prompt=False, stream=True)
    shared.write_json(directory / f'{label}-request.json', payload)
    req = urllib.request.Request(f'http://127.0.0.1:{port}/completion', data=json.dumps(payload).encode(), headers={'Content-Type': 'application/json'})
    started = time.monotonic()
    first = None
    final = None
    with urllib.request.urlopen(req, timeout=600) as response, (directory / f'{label}-sse.txt').open('wb') as raw:
        for line in response:
            raw.write(line)
            if not line.startswith(b'data: '):
                continue
            if line.strip() == b'data: [DONE]':
                break
            data = json.loads(line[6:])
            if data.get('content') and first is None:
                first = time.monotonic()-started
            if data.get('stop'):
                final = data
    if not final or final.get('tokens_predicted') != tokens:
        raise RuntimeError('incomplete fixed-output request')
    timings = final['timings']
    row = dict(ttft_seconds=first, elapsed_seconds=time.monotonic()-started,
               prompt_tokens=timings['prompt_n'], output_tokens=timings['predicted_n'],
               prompt_tokens_per_second=timings['prompt_per_second'], generation_tokens_per_second=timings['predicted_per_second'])
    shared.write_json(directory / f'{label}-result.json', row)
    return row


def command(config):
    c = [str(ROOT / f"output/M6/build-{config['backend']}/bin/llama-server"), '-m', str(PATH), '--alias', MODEL['model_id'],
         '--host', '127.0.0.1', '--port', str(PORT), '--ctx-size', str(config['context']),
         '--threads', str(config['threads']), '--threads-batch', str(config['threads_batch']),
         '--n-gpu-layers', str(config['layers']), '--device', {'cpu':'none', 'hip':'ROCm0', 'vulkan':'Vulkan0'}[config['backend']],
         '--parallel', '1', '--jinja', '--reasoning', 'off', '--metrics', '--batch-size', str(config['batch']),
         '--ubatch-size', str(config['ubatch']), '--flash-attn', config['fa'], '--cache-type-k', config['cache_k'], '--cache-type-v', config['cache_v'], '--offline', '-v']
    if config.get('mtp'):
        c += ['--spec-type', 'draft-mtp']
    return c


def measure(config, out):
    d = out / config['name']
    d.mkdir()
    cmd = command(config)
    shared.write_json(d / 'config.json', config)
    shared.write_json(d / 'command.json', cmd)
    row = dict(config=config, status='RUNNING', trials=[])
    stream = (d / 'server.log').open('w')
    p = subprocess.Popen(cmd, stdout=stream, stderr=subprocess.STDOUT, cwd=ROOT, start_new_session=True)
    stream.close()
    start = time.monotonic()
    guard = Guard(p, d)
    try:
        with guard:
            ready = False
            while time.monotonic()-start < 240 and p.poll() is None and not guard.reason:
                try:
                    with urllib.request.urlopen(f'http://127.0.0.1:{PORT}/health', timeout=2) as resp:
                        if resp.status == 200:
                            ready = True
                            break
                except Exception:
                    pass
                time.sleep(.5)
            if not ready:
                raise RuntimeError('server readiness failed; see raw log')
            row['load_seconds'] = time.monotonic()-start
            row['drm_before'] = shared.drm_activity(p.pid)
            row['smoke'] = request(d, 'smoke', 4)
            for i in range(3):
                if guard.reason:
                    raise RuntimeError(guard.reason)
                row['trials'].append(request(d, f'repetition-{i+1}'))
            row['drm_after'] = shared.drm_activity(p.pid)
            row['status'] = 'PASS'
    except Exception as exc:
        row.update(status='FAIL', error=str(exc))
    finally:
        shared.stop(p)
        row['resources'] = guard.summary()
        row['kernel_audit'] = shared.fault_audit(guard.start)
        log = (d / 'server.log').read_text(errors='replace')
        row['effective_configuration_evidence'] = [l for l in log.splitlines() if any(s in l.lower() for s in ['flash_attn', 'flash attention', 'kv self', 'kv cache', 'n_ctx', 'n_batch', 'n_ubatch', 'offloaded', 'buffer size', 'cache type'])][-80:]
        if guard.reason or row['kernel_audit']['faults'] or row['kernel_audit']['read_exit']:
            row['status'] = 'FAIL'
        row['offload_evidence'] = positive_offload_lines(log)
        if config['backend'] != 'cpu' and not row['offload_evidence']:
            row.update(status='FAIL', error='accelerator offload not proven')
        if row['status'] == 'FAIL' and any(s in log.lower() for s in ['not supported', 'unsupported', 'requires flash', 'not implemented']):
            row['status'] = 'UNSUPPORTED'
        if row['status'] == 'PASS':
            for key in ['elapsed_seconds', 'ttft_seconds', 'prompt_tokens_per_second', 'generation_tokens_per_second']:
                row['median_'+key] = statistics.median(t[key] for t in row['trials'])
        shared.write_json(d / 'result.json', row)
        print(json.dumps({'configuration': config['name'], 'status': row['status'], 'latency': row.get('median_elapsed_seconds'), 'generation': row.get('median_generation_tokens_per_second'), 'guard': guard.reason}), flush=True)
    if row['kernel_audit']['faults'] or guard.reason:
        raise RuntimeError('Safety stop: '+str(guard.reason or row['kernel_audit']['faults']))
    if any(s in log.lower() for s in ['device lost', 'illegal memory access', 'gpu reset', 'out of memory']):
        raise RuntimeError('Unsafe configuration: '+config['name'])
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--continue-tuning', type=Path, help='Reuse completed first-stage measurements after the documented offload-log extraction correction')
    parser.add_argument('--tune-backend', choices=['hip','vulkan'], help='Continue one-factor tuning for this measured GPU backend')
    args = parser.parse_args()
    config = lab.load_config()
    # Phase 0: refuse to compete with a live benchmark.
    processes = subprocess.check_output(['ps','-eo','pid,args'], text=True)
    if any('run_local_model_lab_practical.py' in l and 'python' in l for l in processes.splitlines()):
        raise RuntimeError('Prior benchmark still running; wait without interrupting it')
    out = args.continue_tuning or (ROOT / 'output/QWEN_PERFORMANCE_OPTIMIZATION' / datetime.now().astimezone().strftime('%Y%m%dT%H%M%S%z'))
    if args.continue_tuning:
        result = json.loads((out/'result.json').read_text())
        if result.get('status') != 'MEASURED' or result.get('formal_service_restored') != 'PASS':
            raise RuntimeError('Cannot resume incomplete run or failed restoration')
        if not (out/'initial-stage-result.json').exists():
            shared.write_json(out/'initial-stage-result.json',result)
        # This changes only verifier classification, not measured timings/source.
        for r in result['rows']:
            if r.get('error') != 'accelerator offload not proven':
                continue
            log = (out/r['config']['name']/'server.log').read_text()
            lines = positive_offload_lines(log)
            before = sum(int(c.get('drm-engine-compute','0 ns').split()[0]) for c in r.get('drm_before',{}).get('clients',[]))
            after = sum(int(c.get('drm-engine-compute','0 ns').split()[0]) for c in r.get('drm_after',{}).get('clients',[]))
            allocated = any(int(c.get('drm-memory-gtt','0 KiB').split()[0])>0 for c in r.get('drm_after',{}).get('clients',[]) if c.get('drm-driver')=='amdgpu')
            hardware = after>before or (allocated and (r['resources']['mean_gpu_busy_percent'] or 0)>0)
            if lines and hardware and len(r['trials'])==3 and not r['resources']['guard'] and not r['kernel_audit']['faults'] and r['kernel_audit']['read_exit']==0:
                r['initial_verifier_status'] = 'FAIL'
                r['classification_correction'] = 'VERIFICATION_POLICY_FALSE_NEGATIVE: truncated display list omitted full-log offload; actual offload log plus DRM compute delta or GPU allocation/activity prove hardware execution (KFD does not expose a compute counter here)'
                r['offload_evidence'] = lines
                r['status'] = 'PASS'
                for key in ['elapsed_seconds','ttft_seconds','prompt_tokens_per_second','generation_tokens_per_second']:
                    r['median_'+key] = statistics.median(t[key] for t in r['trials'])
        result['continuation_started_local'] = datetime.now().astimezone().isoformat()
        result['status'] = 'RUNNING'
        shared.write_json(out/'result.json',result)
        original = lab.active_llama_server(str(PATH))
        if original != result['original_runtime']:
            raise RuntimeError('Formal configuration differs from saved original')
        lab.verify_active_model(config,'qwen38',config['provider']['api_base'],verify_hash=False)
        integrity = result['integrity']
        if PATH.stat().st_size != integrity['bytes'] or PATH.stat().st_mtime_ns != integrity['mtime_ns']:
            raise RuntimeError('Model changed since checksum')
        # Match the already successful 18-trial engineering configuration exactly.
        known = next(r['config'] for r in result['rows'] if r['config']['name']=='vulkan-99')
        cases = [] if (out/'engineering-vulkan-16384').exists() else [dict(known, name='engineering-vulkan-16384', context=16384)]
        result['requested_tuning_backend'] = args.tune_backend
    else:
        return initial_run(config,out)
    return run_cases(config,out,result,original,cases)


def initial_run(config,out):
    out.mkdir(parents=True)
    original = lab.active_llama_server(str(PATH))
    if not original:
        raise RuntimeError('Original formal service missing; do not guess restoration configuration')
    expected = ['--ctx-size','8192','--n-gpu-layers','0','--threads','24','--threads-batch','24','--spec-type','draft-mtp']
    if any(original[original.index(expected[i])+1] != expected[i+1] for i in range(0,len(expected),2)):
        raise RuntimeError('Formal configuration changed; recorded restore recipe is no longer applicable')
    shared.write_json(out / 'original-runtime.json', original)
    lab.verify_active_model(config, 'qwen38', config['provider']['api_base'], verify_hash=False)
    result = dict(status='RUNNING', started_local=datetime.now().astimezone().isoformat(), output=str(out),
                  original_runtime=original, prompt=PROMPT, output_tokens=32, rows=[])
    shared.write_json(out / 'result.json', result)
    commands = {'cpu':['lscpu'], 'kernel':['uname','-a'], 'packages':['dpkg-query','-W','-f=${Package}\t${Version}\n'],
                'lemonade':['lemonade','--version'], 'llama':['output/M6/build-cpu/bin/llama-server','--version'],
                'hip_devices':['output/M6/build-hip/bin/llama-server','--list-devices'], 'vulkan_devices':['output/M6/build-vulkan/bin/llama-server','--list-devices']}
    for label, cmd in commands.items():
        p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=30)
        (out / f'baseline-{label}.txt').write_text(p.stdout+p.stderr)
    shared.write_json(out / 'baseline-memory.json', shared.memory())
    shared.write_json(out / 'baseline-kernel-audit.json', shared.fault_audit('24 hours ago'))
    before = PATH.stat()
    h = hashlib.sha256()
    with PATH.open('rb') as f:
        for chunk in iter(lambda: f.read(16*1024**2), b''):
            h.update(chunk)
    after = PATH.stat()
    result['integrity'] = dict(path=str(PATH), bytes=after.st_size, mtime_ns=after.st_mtime_ns, sha256=h.hexdigest(),
                               status='PASS' if h.hexdigest()==MODEL['sha256'] and after.st_size==MODEL['bytes'] and before.st_mtime_ns==after.st_mtime_ns else 'FAIL')
    shared.write_json(out / 'result.json', result)
    if result['integrity']['status'] != 'PASS':
        raise RuntimeError('Model integrity mismatch')
    # Preserve current formal timing separately: different speculative mode is explicit.
    result['formal_baseline_request'] = request(out, 'formal-baseline', port=8001)
    base = dict(backend='cpu', threads=len(os.sched_getaffinity(0)), threads_batch=len(os.sched_getaffinity(0)), layers=0,
                context=8192, batch=2048, ubatch=512, fa='auto', cache_k='f16', cache_v='f16', mtp=False)
    cases = []
    for threads in [24,12,18]:
        cases.append(dict(base, name=f'cpu-{threads}-mtp', threads=threads, mtp=True))
    cases.append(dict(base, name='cpu-24-no-mtp'))
    for backend in ['vulkan','hip']:
        for layers in [99,32]:
            cases.append(dict(base, name=f'{backend}-{layers}', backend=backend, layers=layers))
    return run_cases(config,out,result,original,cases)


def run_cases(config,out,result,original,cases):
    unloaded = False
    signal.signal(signal.SIGTERM, lambda *_: (_ for _ in ()).throw(InterruptedError('SIGTERM')))
    signal.signal(signal.SIGINT, lambda *_: (_ for _ in ()).throw(InterruptedError('SIGINT')))
    try:
        subprocess.run(['lemonade','unload',MODEL['model_id']], check=True, timeout=60)
        unloaded = True
        if lab.active_llama_server(str(PATH)):
            raise RuntimeError('formal large model remained resident')
        for c in cases:
            result['rows'].append(measure(c, out))
            shared.write_json(out / 'result.json', result)
        gpu = [r for r in result['rows'] if r['status']=='PASS' and r['config']['backend']!='cpu']
        if result.get('requested_tuning_backend'):
            gpu = [r for r in gpu if r['config']['backend']==result['requested_tuning_backend'] and r['config']['name'] in {'hip-99','hip-32','vulkan-99','vulkan-32'}]
        if gpu:
            anchor = min(gpu, key=lambda r:r['median_elapsed_seconds'])['config']
            result['tuning_anchor'] = anchor
            variants = [('threads-12',{'threads':12}), ('threads-18',{'threads':18}),
                        ('context-4096',{'context':4096}), ('context-16384',{'context':16384}),
                        ('fa-on',{'fa':'on'}), ('fa-off',{'fa':'off'}), ('kv-k-q8',{'cache_k':'q8_0'}),
                        ('kv-v-q8',{'cache_v':'q8_0'}), ('batch-1024',{'batch':1024}), ('ubatch-256',{'ubatch':256})]
            for name, changes in variants:
                c = dict(anchor, **changes)
                c['name'] = anchor['name']+'-'+name
                result['rows'].append(measure(c,out))
                shared.write_json(out / 'result.json',result)
        result['status'] = 'MEASURED'
    except BaseException as exc:
        result.update(status='PARTIAL', error=f'{type(exc).__name__}: {exc}')
        # A safety exception is raised after the per-configuration evidence is saved.
        # Keep that failed row in the overall ledger as well as the raw directory.
        recorded = {r['config']['name'] for r in result['rows']}
        for file in sorted(out.glob('*/result.json')):
            r = json.loads(file.read_text())
            if 'config' in r and r['config']['name'] not in recorded:
                result['rows'].append(r)
                recorded.add(r['config']['name'])
    finally:
        if unloaded:
            # Use exactly the recorded formal configuration, not a winning benchmark profile.
            # Restoration uses manager options proven by preflight configuration.
            p = subprocess.run(['lemonade','load',MODEL['model_id'],'--ctx-size','8192','--llamacpp','cpu','--llamacpp-args',
                                '--n-gpu-layers 0 --parallel 1 --reasoning off --spec-type draft-mtp --threads 24 --threads-batch 24'],capture_output=True,text=True,timeout=600)
            (out/'restore.log').write_text(p.stdout+p.stderr)
            try:
                if p.returncode:
                    raise RuntimeError('manager restore failed')
                lab.verify_active_model(config,'qwen38',config['provider']['api_base'],verify_hash=False)
                restored = lab.active_llama_server(str(PATH))
                shared.write_json(out/'restored-runtime.json',restored)
                if restored != original:
                    raise RuntimeError('Formal argv differs after restoration')
                result['formal_service_restored'] = 'PASS'
            except Exception as exc:
                result['formal_service_restored'] = 'FAIL: '+str(exc)
                result['status'] = 'BLOCKED'
        result['completed_local'] = datetime.now().astimezone().isoformat()
        shared.write_json(out/'result.json',result)
        print(json.dumps({'output':str(out),'status':result['status'],'formal_service_restored':result.get('formal_service_restored')}),flush=True)
    return 0 if result['status']=='MEASURED' else 1


if __name__=='__main__':
    raise SystemExit(main())
