#!/usr/bin/env python3
"""Repeat installed language-model speed cohorts until STOP; retain raw evidence."""
import fcntl
import json
import os
import signal
from pathlib import Path
import run_workstation_model_performance as bench
import run_model_endurance as evidence


def report(rows, run):
    groups = {}
    for row in rows:
        if bench.safe(row):
            key = (row['model'], row['config']['backend'])
            groups.setdefault(key, []).extend(row['trials'])
    import statistics
    summary = []
    for (model, backend), trials in groups.items():
        rates = [t['generation_tokens_per_second'] for t in trials]
        summary.append(dict(model=model, backend=backend, samples=len(rates),
                            generation_tps=statistics.median(rates), minimum_tps=min(rates), maximum_tps=max(rates),
                            prompt_tps=statistics.median(t['prompt_tokens_per_second'] for t in trials)))
    summary.sort(key=lambda r: r['generation_tps'], reverse=True)
    evidence.save(run/'summary.json', summary)
    lines = ['# 本機語言模型速度實測', '', '固定 512 輸入 / 128 輸出 token；4K context；每組三次。生成速度不代表回答品質。', '',
             '| 模型 | 後端 | 次數 | 生成 token/s 中位數 | 最低–最高 | 輸入 token/s |',
             '|---|---|---:|---:|---:|---:|']
    for r in summary:
        lines.append(f"| {r['model']} | {r['backend']} | {r['samples']} | {r['generation_tps']:.2f} | {r['minimum_tps']:.2f}–{r['maximum_tps']:.2f} | {r['prompt_tps']:.2f} |")
    lines += ['', '用途與精簡：速度接近（約 10% 內）的同系列量化版本列為比較候選；回答品質尚未驗證，尚不自動刪除。嵌入、語音、影像模型不納入生成速度排名。', '',
              f'已執行 {len(rows)} 組；失敗、資源限制及不支援結果見 results.jsonl。']
    (run/'REPORT.md').write_text('\n'.join(lines)+'\n')


def main():
    evidence.HOME.mkdir(parents=True, exist_ok=True)
    lock = evidence.LOCK.open('a+')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    if evidence.api('health').get('model_loaded'):
        raise RuntimeError('A model is already loaded; do not compete with it')
    run = evidence.ROOT/'output/ALL_MODEL_SPEED'/evidence.datetime.now().astimezone().strftime('%Y%m%dT%H%M%S%z')
    run.mkdir(parents=True)
    evidence.RUN = run
    (evidence.HOME/'STOP').unlink(missing_ok=True)
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda *_: evidence.STOP.set())
    models = [dict(id=p.stem, file=p.name, bytes=p.stat().st_size) for p in (evidence.ROOT/'models').glob('*.gguf')
              if not p.name.startswith(('mmproj', 'sd', 'Qwen3-Embedding'))]
    models.sort(key=lambda m: m['bytes'])
    evidence.save(run/'protocol.json', dict(models=models, prompt_tokens=512, output_tokens=128,
                 context=4096, repetitions=3, backends=['vulkan','cpu'], stop_file=str(evidence.HOME/'STOP'),
                 original_service='unloaded', deletion_policy='No deletion before quality and retention review'))
    rows = []
    cycle = 0
    reason = 'USER_STOP'
    try:
        while not evidence.STOP.is_set() and not (evidence.HOME/'STOP').exists():
            cycle += 1
            for model in models:
                for backend in ['vulkan', 'cpu']:
                    if evidence.STOP.is_set() or (evidence.HOME/'STOP').exists():
                        raise InterruptedError('USER_STOP')
                    profile = bench.base_config(backend)
                    row = bench.run_case(model, profile, run/f'cycle-{cycle:04d}'/model['id']/backend, 'SPEED')
                    rows.append(row)
                    with (run/'results.jsonl').open('a') as stream:
                        stream.write(json.dumps(row, ensure_ascii=False)+'\n')
                    report(rows, run)
                    if bench.severe(row):
                        raise RuntimeError('SEVERE_KERNEL_GATE')
    except InterruptedError:
        pass
    except Exception as exc:
        reason = f'{type(exc).__name__}: {exc}'
    finally:
        bench.shared.stop(bench.CHILD)
        report(rows, run)
        evidence.notify(status='STOPPED', stage='ALL_MODEL_SPEED_FINISHED', reason=reason, recorded_cases=len(rows))


if __name__ == '__main__':
    main()
