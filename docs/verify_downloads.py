import hashlib
import json
import tarfile
import zipfile
from pathlib import Path

ROOT=Path('/home/shen/AI370-2/resources/Downloads')
DOCS=Path('/home/shen/AI370-2/docs')
all_results={}
failed=[]
for name in ['download-results.json','download-supplement-results.json','download-fpga-results.json','download-vscode-extensions-results.json','download-vscode-prerelease-results.json']:
    for result in json.loads((DOCS/name).read_text()):
        if result.get('ok'):
            all_results[result['path']]=result
        else:
            failed.append(result)
ubuntu_sha=json.loads((DOCS/'ubuntu-published-sha256.json').read_text())
verified=[]
for name,result in sorted(all_results.items()):
    p=ROOT/name
    with p.open('rb') as f:
        digest=hashlib.file_digest(f,'sha256').hexdigest()
    if digest!=result['sha256'] or p.stat().st_size!=result['bytes']:
        raise RuntimeError('Local file changed: '+name)
    published=result.get('expected_sha256') or ubuntu_sha.get(name)
    if published and digest!=published:
        raise RuntimeError('Published SHA256 mismatch: '+name)
    if p.suffix=='.deb':
        with p.open('rb') as f:
            if f.read(8)!=b'!<arch>\n':
                raise RuntimeError('Invalid DEB header: '+name)
    if p.suffix in ('.whl','.vsix'):
        with zipfile.ZipFile(p) as z:
            if z.testzip() is not None:
                raise RuntimeError('Wheel CRC failure: '+name)
    if name.endswith('.tar.gz'):
        with tarfile.open(p,'r:gz') as t:
            for member in t:
                if member.isfile():
                    f=t.extractfile(member)
                    while f.read(2**20):
                        pass
    verified.append({**result,'expected_sha256':published,'verification':'published SHA256 + local reread' if published else 'local SHA256 reread; no published SHA256 available', 'format_check':'DEB header' if p.suffix=='.deb' else 'ZIP CRC' if p.suffix in ('.whl','.vsix') else 'gzip/tar stream' if name.endswith('.tar.gz') else None})
    print('VERIFIED',name,flush=True)
summary={'files':len(verified),'bytes':sum(r['bytes'] for r in verified),'published_sha256_files':sum(bool(r['expected_sha256']) for r in verified),'failed_downloads':failed,'partial_files':[str(p.relative_to(ROOT)) for p in ROOT.rglob('*.part')],'results':verified}
(DOCS/'download-verification.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
(DOCS/'SHA256SUMS.downloads').write_text(''.join(f"{r['sha256']}  {r['path']}\n" for r in verified))
print('FINAL',summary['files'],'files',round(summary['bytes']/2**30,3),'GiB; failures',len(failed),'partials',len(summary['partial_files']),flush=True)
