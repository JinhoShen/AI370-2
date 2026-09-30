import ast
import hashlib
import json
import threading
import time
import urllib.request
import zipfile
import xml.etree.ElementTree as ET
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
            node.value='download-vscode-extensions-results.json'
exec(compile(ast.Module(body=functions,type_ignores=[]),'<download-functions>','exec'))
todo=['ms-python.python','ms-python.vscode-pylance','ms-python.debugpy','ms-vscode.cpptools','ms-vscode.cmake-tools']
seen=set()
while todo:
    name=todo.pop(0)
    if name in seen:
        continue
    seen.add(name)
    publisher,extension=name.split('.',1)
    query={'filters':[{'criteria':[{'filterType':7,'value':name}]}],'flags':403}
    request=urllib.request.Request('https://marketplace.visualstudio.com/_apis/public/gallery/extensionquery',data=json.dumps(query).encode(),headers={'Content-Type':'application/json','Accept':'application/json;api-version=3.0-preview.1','User-Agent':'AI370-2'})
    with urllib.request.urlopen(request,timeout=40) as response:
        metadata=json.load(response)
    versions=[v for v in metadata['results'][0]['extensions'][0]['versions'] if not any(p['key']=='Microsoft.VisualStudio.Code.PreRelease' and p['value']=='true' for p in v.get('properties',[]))]
    version=next((v for v in versions if v.get('targetPlatform')=='linux-x64'),None) or next(v for v in versions if v.get('targetPlatform') in (None,'universal'))
    url=next(f['source'] for f in version['files'] if f['assetType']=='Microsoft.VisualStudio.Services.VSIXPackage')
    result=download(dict(url=url,path='DevTools/VSCode/Extensions/'+name+'-'+version['version']+'.vsix',expected_sha256=None,expected_bytes=None,expected_md5=None,version=version['version']))
    if result['ok']:
        p=ROOT/result['path']
        with zipfile.ZipFile(p) as z:
            if z.testzip():
                raise RuntimeError('VSIX CRC failed: '+name)
            manifest=json.loads(z.read('extension/package.json'))
            result['version']=manifest['version']
            result['extension_id']=name
            for dependency in manifest.get('extensionDependencies',[]):
                if dependency not in seen:
                    todo.append(dependency)
            result['extension_dependencies']=manifest.get('extensionDependencies',[])
(DOCS/'download-vscode-extensions-results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n')
print('VSIX COMPLETE',sum(r['ok'] for r in results),'/',len(results),flush=True)
