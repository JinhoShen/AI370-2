import hashlib
import json
import shutil
import subprocess
import time
from pathlib import Path

SOURCE = Path('/media/shen/T7/Agent_Tools_Docs')
DEST = Path('/home/shen/AI370-2/resources/Agent_Tools_Docs')
DOCS = Path('/home/shen/AI370-2/docs')
selections = ['00_Docs', '01_OS', '05_SER9_Project', '99_Checksums',
              '03_RyzenAI/XRT_NPU', '04_Local_AI/Lemonade',
              '03_RyzenAI/RyzenAI_1.7.1/ryzen_ai-1.7.1.tgz',
              '02_FPGA/Vivado_Vitis_2026.1/FPGAs_AdaptiveSoCs_Unified_SDI_2026.1_0616_1700.tar']
selections += [str(p.relative_to(SOURCE)) for p in sorted((SOURCE/'04_Local_AI/GGUF').glob('*.gguf')) if p.stat().st_size]
known = {}
for line in (SOURCE/'99_Checksums/SHA256SUMS').read_text().splitlines():
    digest, name = line.split(maxsplit=1)
    known[name] = digest
bundle = '05_SER9_Project/Git/SER9-AI-FPGA-Workstation.bundle'
known[bundle] = (SOURCE/(bundle+'.sha256')).read_text().split()[0]
files = []
for name in selections:
    p = SOURCE/name
    files.extend(sorted(f for f in p.rglob('*') if f.is_file()) if p.is_dir() else [p])
total = sum(p.stat().st_size for p in files)
if shutil.disk_usage(DEST.parent).free < total + 20*2**30:
    raise RuntimeError('Insufficient space with 20 GiB reserve')
manifest = []
for p in files:
    rel = str(p.relative_to(SOURCE))
    digest = known.get(rel)
    if digest is None:
        with p.open('rb') as stream:
            digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    manifest.append({'path': rel, 'bytes': p.stat().st_size, 'sha256': digest})
(DOCS/'resource-manifest.json').write_text(json.dumps({'source': str(SOURCE), 'destination': str(DEST), 'bytes': total, 'files': manifest, 'checksum_note': 'Bundle uses matching standalone checksum; original aggregate checksum is inconsistent.'}, ensure_ascii=False, indent=2)+'\n')
print(f'PLAN {len(files)} files, {total/2**30:.3f} GiB', flush=True)
DEST.mkdir(parents=True, exist_ok=True)
for name in selections:
    src = SOURCE/name
    target = DEST/name
    target.parent.mkdir(parents=True, exist_ok=True)
    if src.is_dir():
        target.mkdir(parents=True, exist_ok=True)
        args = [str(src)+'/', str(target)+'/']
    else:
        args = [str(src), str(target)]
    print('COPY '+name, flush=True)
    subprocess.run(['rsync', '-rt', '--human-readable', '--info=progress2', '--', *args], check=True)
print('COPY COMPLETE; VERIFYING SHA256', flush=True)
results = []
for item in manifest:
    p = DEST/item['path']
    with p.open('rb') as stream:
        actual = hashlib.file_digest(stream, 'sha256').hexdigest()
    ok = p.stat().st_size == item['bytes'] and actual == item['sha256']
    results.append({**item, 'actual_sha256': actual, 'ok': ok})
    print(('OK ' if ok else 'FAILED ')+item['path'], flush=True)
    if not ok:
        (DOCS/'copy-verification.json').write_text(json.dumps(results, ensure_ascii=False, indent=2)+'\n')
        raise RuntimeError('Verification failed: '+item['path'])
(DOCS/'copy-verification.json').write_text(json.dumps(results, ensure_ascii=False, indent=2)+'\n')
(DOCS/'SHA256SUMS.local').write_text(''.join(f"{item['sha256']}  {item['path']}\n" for item in manifest))
print(f'COMPLETE {len(results)} files verified, {total/2**30:.3f} GiB', flush=True)
