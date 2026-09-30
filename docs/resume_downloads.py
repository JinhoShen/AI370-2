import ast
import concurrent.futures
import hashlib
import json
import os
import threading
import time
import urllib.request
from pathlib import Path

ROOT=Path('/home/shen/AI370-2/resources/Downloads')
DOCS=Path('/home/shen/AI370-2/docs')
lock=threading.Lock()
results=json.loads((DOCS/'download-results.json').read_text())
tree=ast.parse((DOCS/'download_resources.py').read_text())
functions=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('fetch','js','download')]
exec(compile(ast.Module(body=functions,type_ignores=[]),'<download-functions>','exec'))
plan=json.loads((DOCS/'download-plan.json').read_text())
done={r['path'] for r in results if r.get('ok')}
jobs=[j for j in plan['jobs'] if j['path'] not in done]
results[:]=[r for r in results if r.get('ok')]

def segmented(j):
    if not j['url'].startswith('https://repo.radeon.com/'):
        return download(j)
    size=j.get('expected_bytes')
    if size is None:
        with urllib.request.urlopen(urllib.request.Request(j['url'],method='HEAD'),timeout=40) as r:
            size=int(r.headers.get('Content-Length','0'))
    if size<100*2**20:
        return download(j)
    target=ROOT/j['path']
    target.parent.mkdir(parents=True,exist_ok=True)
    partial=target.with_name(target.name+'.part')
    prefix=partial.stat().st_size if partial.exists() else 0
    if prefix>size:
        raise RuntimeError('Partial file exceeds expected size')
    # Preserve the existing sequential prefix. Each range has an independent
    # temporary file and is assembled only after its complete response passes.
    chunk_size=64*2**20
    ranges=[(offset,min(size-1,offset+chunk_size-1)) for offset in range(prefix,size,chunk_size)]
    def part(bounds):
        start,end=bounds
        p=target.with_name(target.name+f'.range-{start}-{end}')
        for attempt in range(3):
            try:
                request=urllib.request.Request(j['url'],headers={'Range':f'bytes={start}-{end}','User-Agent':'AI370-2-resource-preparation'})
                count=0
                with urllib.request.urlopen(request,timeout=60) as r,p.open('wb') as f:
                    if r.status!=206 or r.headers.get('Content-Range')!=f'bytes {start}-{end}/{size}':
                        raise RuntimeError('Unexpected range response')
                    while data:=r.read(2**20):
                        f.write(data); count+=len(data)
                if count!=end-start+1:
                    raise RuntimeError('Incomplete range')
                return start,p
            except Exception:
                if attempt==2:
                    raise
                time.sleep(2)
    print('RESUME RANGES',j['path'],'prefix',prefix,'total',size,flush=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        parts=list(pool.map(part,ranges))
    with partial.open('r+b' if partial.exists() else 'wb') as f:
        for start,p in sorted(parts):
            f.seek(start)
            with p.open('rb') as src:
                while data:=src.read(2**20):
                    f.write(data)
        f.truncate(size)
    with partial.open('rb') as f:
        digest=hashlib.file_digest(f,'sha256').hexdigest()
    if j['expected_sha256'] and digest!=j['expected_sha256']:
        raise RuntimeError('Published SHA256 mismatch')
    partial.rename(target)
    # These range files were created exclusively by this downloader.
    for start,p in parts:
        p.unlink()
    result={**j,'sha256':digest,'bytes':size,'final_url':j['url'],'ok':True,'verification':'published SHA256' if j['expected_sha256'] else 'HTTP range lengths + local SHA256'}
    with lock:
        results.append(result)
        (DOCS/'download-results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n')
        print('OK',j['path'],size,flush=True)
    return result

print('RESUME',len(done),'completed;',len(jobs),'remaining',flush=True)
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
    futures={pool.submit(segmented,j):j for j in jobs}
    for future in concurrent.futures.as_completed(futures):
        j=futures[future]
        try:
            future.result()
        except Exception as e:
            with lock:
                results.append({**j,'ok':False,'error':str(e)})
                (DOCS/'download-results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n')
                print('FAILED',j['path'],str(e),flush=True)
print('COMPLETE',sum(r['ok'] for r in results),'/',len(results),'downloads',flush=True)
