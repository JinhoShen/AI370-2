import ast
import hashlib
import json
import threading
import time
import urllib.request
from pathlib import Path

ROOT=Path('/home/shen/AI370-2/resources/Downloads')
DOCS=Path('/home/shen/AI370-2/docs')
lock=threading.Lock()
results=[]
tree=ast.parse((DOCS/'download_resources.py').read_text())
functions=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('fetch','js','download')]
for function in functions:
    for node in ast.walk(function):
        if isinstance(node,ast.Constant) and node.value=='download-results.json':
            node.value='download-fpga-results.json'
exec(compile(ast.Module(body=functions,type_ignores=[]),'<download-functions>','exec'))
for repository in ['Xilinx/XilinxBoardStore','Digilent/vivado-boards','Xilinx/Vitis_Embedded_Platform_Source']:
    try:
        metadata=js('https://api.github.com/repos/'+repository)
        ref=js('https://api.github.com/repos/'+repository+'/commits/'+metadata['default_branch'])
        sha=ref['sha']
        job=dict(url='https://codeload.github.com/'+repository+'/tar.gz/'+sha,path='FPGA/Board-and-Platform-Sources/'+repository.replace('/','-')+'-'+sha[:12]+'.tar.gz',expected_sha256=None,expected_bytes=None,expected_md5=None,version=sha)
        download(job)
    except Exception as e:
        results.append(dict(repository=repository,ok=False,error=str(e)))
(DOCS/'download-fpga-results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n')
print('FPGA SOURCES COMPLETE',sum(j['ok'] for j in results),'/',len(results),flush=True)
