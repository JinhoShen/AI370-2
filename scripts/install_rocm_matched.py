"""Install pinned ROCm userspace with exact baseline development headers."""
from pathlib import Path
import hashlib
import json
import os
import re
import subprocess

project = Path(__file__).resolve().parents[1]
os.chdir(project)
paths = json.loads((project/'docs/M3/approved-local-paths.json').read_text())
hashes = {str(Path('resources/Downloads')/line.split('  ',1)[1]): line.split('  ',1)[0]
          for line in (project/'docs/SHA256SUMS.downloads').read_text().splitlines()}
hashes.update({item['path']:item['sha256'] for item in json.loads((project/'docs/M3/matched-header-manifest.json').read_text())})
for path in paths:
    digest = hashlib.sha256()
    with open(path,'rb') as source:
        while block := source.read(1024*1024): digest.update(block)
    assert digest.hexdigest()==hashes[path],path
    print(path,'SHA256 PASS',flush=True)
args=['apt-get','--no-install-recommends','--no-upgrade','--no-remove','install']+['./'+p for p in paths]
result=subprocess.run(args[:1]+['-s']+args[1:],text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
(project/'docs/M3/rocm-final-simulation.txt').write_text(result.stdout)
result.check_returncode()
assert re.search(r'0 upgraded, \d+ newly installed, 0 to remove',result.stdout)
allowed = {subprocess.check_output(['dpkg-deb','-f',p,'Package'],text=True).strip() for p in paths}
for line in result.stdout.splitlines():
    if line.startswith('Inst '):
        name=line.split()[1]
        assert name in allowed,name
        assert not re.search(r'dkms|linux-|amdgpu-dkms|amdxdna|xrt|mesa',name),name
subprocess.run(['sudo','-n','install','-m','0644',*paths,'/var/cache/apt/archives/'],check=True)
env={**os.environ,'DEBIAN_FRONTEND':'noninteractive'}
with (project/'docs/M3/rocm-install.txt').open('w') as log:
    subprocess.run(['sudo','-n','env','DEBIAN_FRONTEND=noninteractive',args[0],'-y','--no-download',*args[1:]],
                   stdout=log,stderr=subprocess.STDOUT,env=env,check=True)
print('ROCm userspace install finished; VERIFY REQUIRED',flush=True)
