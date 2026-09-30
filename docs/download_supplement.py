import ast
import hashlib
import json
import shlex
import subprocess
import threading
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path('/home/shen/AI370-2/resources/Downloads')
DOCS = Path('/home/shen/AI370-2/docs')
results = []
lock = threading.Lock()
# Reuse only download functions; do not execute the main planner a second time.
tree = ast.parse((DOCS/'download_resources.py').read_text())
functions = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in ('fetch', 'js', 'download')]
for function in functions:
    for node in ast.walk(function):
        if isinstance(node, ast.Constant) and node.value == 'download-results.json':
            node.value = 'download-supplement-results.json'
exec(compile(ast.Module(body=functions, type_ignores=[]), '<download-functions>', 'exec'))
jobs = []
args = ['apt-get', '--print-uris', '--download-only', '-y', '-o', 'Debug::NoLocking=1', 'install', 'libncurses-dev', 'libdrm-dev', 'libelf1t64', 'libgcc-13-dev', 'libstdc++-13-dev']
r = subprocess.run(args, capture_output=True, text=True, check=True)
(DOCS/'ubuntu-supplement-resolution.txt').write_text(r.stdout+r.stderr)
for line in r.stdout.splitlines():
    if line.startswith("'"):
        url, name, size, digest = shlex.split(line)
        jobs.append(dict(url=url.replace('http://','https://',1), path='Ubuntu24.04/debs/'+name, expected_sha256=None, expected_bytes=int(size), expected_md5=digest.removeprefix('MD5Sum:'), version=None))
pages = {
    'rocm-7.2.1-ryzen-install.html': 'https://rocm.docs.amd.com/projects/radeon-ryzen/en/docs-7.2.1/docs/install/installryz/native_linux/install-ryzen.html',
    'rocm-7.2.1-pytorch.html': 'https://rocm.docs.amd.com/projects/radeon-ryzen/en/docs-7.2.1/docs/install/installryz/native_linux/install-pytorch.html',
    'ryzenai-1.7.1-linux.html': 'https://ryzenai.docs.amd.com/en/1.7.1/linux.html',
    'ryzenai-1.7.1-npu-llm.html': 'https://ryzenai.docs.amd.com/en/1.7.1/llm_linux.html',
    'lemonade-ubuntu.html': 'https://lemonade-server.ai/docs/guide/install/ubuntu/',
    'vscode-linux.html': 'https://code.visualstudio.com/docs/setup/linux',
    'llama-build.md': 'https://raw.githubusercontent.com/ggml-org/llama.cpp/7fe450e19305f7c3a29bcd5f2ced3b873a7bbdfa/docs/build.md',
}
# Resolve the exact source commit already selected by the main planner.
plan=json.loads((DOCS/'download-plan.json').read_text())
for job in plan['jobs']:
    if job['path'].startswith('LocalAI/llama.cpp/'):
        commit=job['version'].split()[-1]
        pages['llama-build.md']='https://raw.githubusercontent.com/ggml-org/llama.cpp/'+commit+'/docs/build.md'
for name,url in pages.items():
    jobs.append(dict(url=url,path='Documentation/'+name,expected_sha256=None,expected_bytes=None,expected_md5=None,version=None))
for job in jobs:
    download(job)
(DOCS/'download-supplement-results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n')
print('SUPPLEMENT COMPLETE',sum(j['ok'] for j in results),'/',len(results),flush=True)
