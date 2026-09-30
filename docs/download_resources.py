import concurrent.futures
import gzip
import hashlib
import json
import shlex
import subprocess
import threading
import time
import urllib.parse
import urllib.request
from pathlib import Path
import apt_pkg

apt_pkg.init_system()
ROOT = Path('/home/shen/AI370-2/resources/Downloads')
DOCS = Path('/home/shen/AI370-2/docs')
ROOT.mkdir(parents=True, exist_ok=True)
lock = threading.Lock()
jobs = []
notes = []

def fetch(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'AI370-2-resource-preparation'}), timeout=40) as r:
        return r.read()

def js(url):
    return json.loads(fetch(url))

def add(url, path, sha=None, size=None, version=None, md5=None):
    jobs.append(dict(url=url, path=path, expected_sha256=sha, expected_bytes=size, version=version, expected_md5=md5))

def fields(text):
    result = {}
    key = None
    for line in text.splitlines():
        if line.startswith((' ', '\t')) and key:
            result[key] += '\n'+line
        elif ': ' in line:
            key, value = line.split(': ', 1)
            result[key] = value
    return result

def repo(base, folder):
    url = base+'/dists/noble/main/binary-amd64/Packages.gz'
    raw = fetch(url)
    p = ROOT/folder/'metadata/Packages.gz'
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(raw)
    return {d['Package']: d for block in gzip.decompress(raw).decode().split('\n\n') if (d := fields(block)).get('Architecture') in ('amd64', 'all')}

v = js('https://update.code.visualstudio.com/api/update/linux-deb-x64/stable/latest')
add(v['url'], 'DevTools/VSCode/'+v['url'].split('/')[-1], v['sha256hash'], version=v['productVersion'])
for repository, folder in [('ggml-org/llama.cpp', 'LocalAI/llama.cpp'), ('astral-sh/uv', 'DevTools/uv')]:
    d = js('https://api.github.com/repos/'+repository+'/releases/latest')
    if repository.endswith('llama.cpp'):
        tag = d['tag_name']
        ref = js('https://api.github.com/repos/'+repository+'/git/ref/tags/'+tag)['object']
        if ref['type'] == 'tag':
            ref = js(ref['url'])['object']
        commit = ref['sha']
        add('https://codeload.github.com/'+repository+'/tar.gz/'+commit, folder+'/llama.cpp-'+tag+'-'+commit[:12]+'.tar.gz', version=tag+' '+commit)
    else:
        for a in d['assets']:
            if a['name'] in ('uv-x86_64-unknown-linux-gnu.tar.gz', 'uv-x86_64-unknown-linux-gnu.tar.gz.sha256'):
                add(a['browser_download_url'], folder+'/'+d['tag_name']+'/'+a['name'], (a.get('digest') or '').removeprefix('sha256:') or None, a['size'], d['tag_name'])

amd_base = 'https://repo.radeon.com/rocm/apt/7.2.1'
amd = repo(amd_base, 'AMD/ROCm-7.2.1')
todo = ['rocm']
selected = {}
ubuntu_dependencies = set()
while todo:
    name = todo.pop()
    if name in selected:
        continue
    d = amd[name]
    selected[name] = d
    for group in apt_pkg.parse_depends(d.get('Depends', '')+(',' if d.get('Depends') and d.get('Pre-Depends') else '')+d.get('Pre-Depends', '')):
        choices = [a[0].split(':')[0] for a in group]
        candidate = next((n for n in choices if n in amd), None)
        if candidate:
            todo.append(candidate)
        else:
            ubuntu_dependencies.add(choices[0])
for name, d in selected.items():
    add(amd_base+'/'+d['Filename'], 'AMD/ROCm-7.2.1/debs/'+Path(d['Filename']).name, d['SHA256'], int(d['Size']), d['Version'])
add('https://repo.radeon.com/amdgpu-install/7.2.1/ubuntu/noble/amdgpu-install_7.2.1.70201-1_all.deb', 'AMD/ROCm-7.2.1/amdgpu-install_7.2.1.70201-1_all.deb', version='7.2.1')
wheel_base = 'https://repo.radeon.com/rocm/manylinux/rocm-rel-7.2.1/'
for name in ['torch-2.9.1+rocm7.2.1.lw.gitff65f5bc-cp312-cp312-linux_x86_64.whl', 'torchvision-0.24.0+rocm7.2.1.gitb919bd0c-cp312-cp312-linux_x86_64.whl', 'triton-3.5.1+rocm7.2.1.gita272dfa8-cp312-cp312-linux_x86_64.whl', 'torchaudio-2.9.0+rocm7.2.1.gite3c6ee2b-cp312-cp312-linux_x86_64.whl']:
    add(wheel_base+urllib.parse.quote(name), 'AMD/PyTorch-ROCm-7.2.1/'+name, version='ROCm 7.2.1 Python 3.12')

ppa_base = 'https://ppa.launchpadcontent.net/lemonade-team/stable/ubuntu'
ppa = repo(ppa_base, 'LocalAI/Lemonade-Ubuntu24.04')
for name, d in ppa.items():
    add(ppa_base+'/'+d['Filename'], 'LocalAI/Lemonade-Ubuntu24.04/debs/'+Path(d['Filename']).name, d['SHA256'], int(d['Size']), d['Version'])
    for group in apt_pkg.parse_depends(d.get('Depends', '')):
        if not any(a[0].split(':')[0] in ppa for a in group):
            ubuntu_dependencies.add(group[0][0].split(':')[0])

basic = ['cmake', 'ninja-build', 'python3.12-venv', 'python3-pip', 'git-lfs', 'libvulkan-dev', 'glslc', 'vulkan-tools', 'mesa-utils', 'clinfo', 'libcurl4-openssl-dev', 'libssl-dev', 'pkg-config', 'zip', 'unzip', 'libboost-filesystem1.83.0', 'libboost-program-options1.83.0', 'ocl-icd-opencl-dev', 'uuid-dev']
available = []
for name in sorted(ubuntu_dependencies):
    out = subprocess.run(['apt-cache', 'policy', name], capture_output=True, text=True).stdout
    if 'Candidate:' in out and 'Candidate: (none)' not in out:
        available.append(name)
    else:
        notes.append('Ubuntu dependency requires later review: '+name)
args = ['apt-get', '--print-uris', '--download-only', '-y', '-o', 'Debug::NoLocking=1', 'install', *sorted(set(basic+available))]
out = subprocess.run(args, capture_output=True, text=True)
(DOCS/'ubuntu-download-resolution.txt').write_text(out.stdout+'\n'+out.stderr)
if out.returncode:
    raise RuntimeError('Ubuntu download resolution failed; no installation performed')
for line in out.stdout.splitlines():
    if line.startswith("'"):
        url, name, size, digest = shlex.split(line)
        url = url.replace('http://', 'https://', 1)
        add(url, 'Ubuntu24.04/debs/'+name, size=int(size), md5=digest.removeprefix('MD5Sum:'))

# Save pinned NPU model metadata if accessible. No token/login or license bypass.
model = 'amd/Phi-3.5-mini-instruct_rai_1.7.1_npu_4K'
try:
    d = js('https://huggingface.co/api/models/'+model+'?blobs=true')
    (ROOT/'AMD/NPU-model-metadata.json').write_text(json.dumps(d, indent=2)+'\n')
    for item in d['siblings']:
        name = item['rfilename']
        if name.startswith('.git'):
            continue
        add('https://huggingface.co/'+model+'/resolve/'+d['sha']+'/'+urllib.parse.quote(name), 'AMD/NPU-models/Phi-3.5-mini-instruct_rai_1.7.1_npu_4K/'+name, item.get('lfs', {}).get('sha256'), item.get('size'), d['sha'])
except Exception as e:
    notes.append('NPU model metadata unavailable: '+str(e))

plan = {'jobs': jobs, 'notes': notes, 'ubuntu_dependencies': sorted(ubuntu_dependencies), 'rocm_packages': len(selected), 'known_bytes': sum(j['expected_bytes'] or 0 for j in jobs)}
(DOCS/'download-plan.json').write_text(json.dumps(plan, ensure_ascii=False, indent=2)+'\n')
print('PLAN', len(jobs), 'downloads;', len(selected), 'ROCm packages; known GiB', round(plan['known_bytes']/2**30, 2), flush=True)
results = []

def download(j):
    p = ROOT/j['path']
    p.parent.mkdir(parents=True, exist_ok=True)
    partial = p.with_name(p.name+'.part')
    for attempt in range(3):
        try:
            if not p.exists():
                sha = hashlib.sha256()
                md5 = hashlib.md5()
                count = 0
                with urllib.request.urlopen(urllib.request.Request(j['url'], headers={'User-Agent': 'AI370-2-resource-preparation'}), timeout=60) as r, partial.open('wb') as f:
                    expected = r.headers.get('Content-Length')
                    final_url = r.url
                    while chunk := r.read(2**20):
                        f.write(chunk)
                        sha.update(chunk)
                        md5.update(chunk)
                        count += len(chunk)
                if expected is not None and count != int(expected):
                    raise RuntimeError('HTTP length mismatch')
                actual = sha.hexdigest()
                actual_md5 = md5.hexdigest()
            else:
                with p.open('rb') as f:
                    actual = hashlib.file_digest(f, 'sha256').hexdigest()
                with p.open('rb') as f:
                    actual_md5 = hashlib.file_digest(f, 'md5').hexdigest()
                count = p.stat().st_size
                final_url = j['url']
            if j['expected_bytes'] is not None and count != j['expected_bytes']:
                raise RuntimeError('Metadata length mismatch')
            if j['expected_sha256'] and actual != j['expected_sha256']:
                raise RuntimeError('Published SHA256 mismatch')
            if j['expected_md5'] and actual_md5 != j['expected_md5']:
                raise RuntimeError('APT metadata MD5 mismatch')
            if not p.exists():
                partial.rename(p)
            result = {**j, 'sha256': actual, 'bytes': count, 'final_url': final_url, 'ok': True, 'verification': 'published SHA256' if j['expected_sha256'] else 'APT MD5 + local SHA256' if j['expected_md5'] else 'HTTP length + local SHA256'}
            with lock:
                results.append(result)
                (DOCS/'download-results.json').write_text(json.dumps(results, ensure_ascii=False, indent=2)+'\n')
                print('OK', j['path'], count, flush=True)
            return result
        except Exception as e:
            if attempt < 2:
                time.sleep(2)
            else:
                result = {**j, 'ok': False, 'error': str(e)}
                with lock:
                    results.append(result)
                    (DOCS/'download-results.json').write_text(json.dumps(results, ensure_ascii=False, indent=2)+'\n')
                    print('FAILED', j['path'], str(e), flush=True)
                return result

with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
    list(pool.map(download, jobs))
(DOCS/'SHA256SUMS.downloads').write_text(''.join(f"{j['sha256']}  {j['path']}\n" for j in sorted(results, key=lambda j:j['path']) if j['ok']))
print('COMPLETE', sum(j['ok'] for j in results), '/', len(results), 'downloads;', sum(j.get('bytes',0) for j in results)/2**30, 'GiB', 'NOTES', notes, flush=True)
