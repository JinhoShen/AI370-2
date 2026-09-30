import datetime
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

PROJECT=Path('/home/shen/AI370-2')
SOURCE=PROJECT/'resources/Downloads'
DOCS=PROJECT/'docs'
DEST=Path('/media/shen/T7/Agent_Tools_Docs/06_AI370_2_Downloads')
if not Path('/media/shen/T7').is_mount():
    raise RuntimeError('T7 is not mounted')
files=sorted(p for p in SOURCE.rglob('*') if p.is_file())
total=sum(p.stat().st_size for p in files)
if shutil.disk_usage(DEST.parent).free<total+2**30:
    raise RuntimeError('Insufficient T7 free space')
if DEST.exists():
    raise RuntimeError('Backup destination already exists; review before replacing')
known={r['path']:r for r in json.loads((DOCS/'download-verification.json').read_text())['results']}
manifest=[]
for p in files:
    rel=str(p.relative_to(SOURCE))
    if rel in known:
        digest=known[rel]['sha256']
        if p.stat().st_size!=known[rel]['bytes']:
            raise RuntimeError('Source size changed: '+rel)
    else:
        with p.open('rb') as f:
            digest=hashlib.file_digest(f,'sha256').hexdigest()
    manifest.append({'path':rel,'bytes':p.stat().st_size,'sha256':digest})
DEST.mkdir()
print('COPY',len(files),'files',total,'bytes',flush=True)
subprocess.run(['rsync','-rt','--info=stats2','--',str(SOURCE)+'/',str(DEST)+'/'],check=True)
print('VERIFY T7 SHA256',flush=True)
checks=[]
for item in manifest:
    p=DEST/item['path']
    with p.open('rb') as f:
        digest=hashlib.file_digest(f,'sha256').hexdigest()
    ok=p.stat().st_size==item['bytes'] and digest==item['sha256']
    checks.append({**item,'actual_sha256':digest,'ok':ok})
    if not ok:
        raise RuntimeError('T7 verification failed: '+item['path'])
records=DEST/'99_Records'
records.mkdir()
names=['DOWNLOAD_PREPARATION.md','download-verification.json','SHA256SUMS.downloads','download-plan.json','rocm-dependency-review.json','ubuntu-published-sha256.json','ubuntu-iso-published-checksum.json']
names+=[p.name for p in DOCS.glob('download*-results.json')]
record_checks=[]
for name in sorted(set(names)):
    src=DOCS/name
    target=records/name
    shutil.copyfile(src,target)
    with src.open('rb') as f:
        expected=hashlib.file_digest(f,'sha256').hexdigest()
    with target.open('rb') as f:
        actual=hashlib.file_digest(f,'sha256').hexdigest()
    if expected!=actual:
        raise RuntimeError('Record verification failed: '+name)
    record_checks.append({'path':'99_Records/'+name,'sha256':expected,'bytes':src.stat().st_size,'ok':True})
result={'completed_at':datetime.datetime.now().astimezone().isoformat(),'source':str(SOURCE),'destination':str(DEST),'resource_files':len(files),'resource_bytes':total,'all_passed':all(i['ok'] for i in checks),'records':record_checks,'files':checks,'operation':'Copy only; no deletions or installation. T7 remains mounted.'}
(DOCS/'t7-sync-verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
shutil.copyfile(DOCS/'t7-sync-verification.json',records/'t7-sync-verification.json')
checksums=''.join(f"{i['sha256']}  {i['path']}\n" for i in manifest+record_checks)
(records/'SHA256SUMS.backup').write_text(checksums)
(DOCS/'SHA256SUMS.t7-backup').write_text(checksums)
# Flush only this filesystem; do not repair or unmount it.
subprocess.run(['sync','-f',str(DEST)],check=True)
print('COMPLETE',len(files),'resources;',len(record_checks),'records; all SHA256 matched; filesystem flushed',flush=True)
