"""XRT 2.21 only. Never install the driver plugin DEB or run its scripts."""
from pathlib import Path
import hashlib, io, json, os, re, subprocess, tarfile

project=Path(__file__).resolve().parents[1]
os.chdir(project)
original=project/'resources/Agent_Tools_Docs'
download=project/'resources/Downloads'
hashes={str(original/line.split('  ',1)[1]):line.split('  ',1)[0]
        for line in (project/'docs/SHA256SUMS.local').read_text().splitlines()}
hashes.update({str(download/line.split('  ',1)[1]):line.split('  ',1)[0]
               for line in (project/'docs/SHA256SUMS.downloads').read_text().splitlines()})
installed=subprocess.check_output(['dpkg-query','-W','-f','${db:Status-Abbrev} ${binary:Package} ${Version}\n'],text=True)
for line in installed.splitlines():
    fields=line.split(maxsplit=2)
    if fields[0]=='ii':
        name=fields[1].split(':')[0]
        assert not name.startswith(('libxrt','xrt_plugin')), ('Other XRT provider/driver package',line)
        if name in ['xrt-base','xrt-npu','xrt-base-dev']: assert fields[2]=='2.21.75',line
xrt=original/'03_RyzenAI/XRT_NPU'
paths=[xrt/'xrt_202610.2.21.75_24.04-amd64-base.deb',xrt/'xrt_202610.2.21.75_24.04-amd64-npu.deb']
paths += [download/'Ubuntu24.04/debs'/name for name in [
    'libboost-filesystem1.83.0_1.83.0-2.1ubuntu3.2_amd64.deb',
    'libboost-program-options1.83.0_1.83.0-2.1ubuntu3.2_amd64.deb',
    'ocl-icd-libopencl1_2.3.2-1build1_amd64.deb']]
plugin=xrt/'xrt_plugin.2.21.260102.53.release_24.04-amd64-amdxdna.deb'
for path in [*paths,plugin]:
    assert hashlib.sha256(path.read_bytes()).hexdigest()==hashes[str(path)],path
args=['apt-get','--no-install-recommends','--no-upgrade','--no-remove','install',*map(str,paths)]
r=subprocess.run(args[:1]+['-s']+args[1:],text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
(project/'docs/M5/xrt-final-simulation.txt').write_text(r.stdout);r.check_returncode()
assert re.search(r'0 upgraded, \d+ newly installed, 0 to remove',r.stdout)
allowed={subprocess.check_output(['dpkg-deb','-f',str(p),'Package'],text=True).strip() for p in paths}
for line in r.stdout.splitlines():
    if line.startswith('Inst '): assert line.split()[1] in allowed,line
for path in paths:
    fields=[subprocess.check_output(['dpkg-deb','-f',str(path),field],text=True).strip() for field in ['Package','Version','Architecture']]
    canonical='_'.join(fields)+'.deb'
    subprocess.run(['sudo','-n','install','-m','0644',str(path),'/var/cache/apt/archives/'+canonical],check=True)
with (project/'docs/M5/xrt-install.txt').open('w') as log:
    subprocess.run(['sudo','-n','env','DEBIAN_FRONTEND=noninteractive',args[0],'-y','--no-download',*args[1:]],
                   stdout=log,stderr=subprocess.STDOUT,check=True)
# Copy only the userspace SHIM payload to an isolated, root-owned prefix.
# No DEB installation, maintainer script, firmware, source or DKMS copying.
prefix=Path('/opt/ai370/npu/xrt21-shim/lib')
subprocess.run(['sudo','-n','mkdir','-p',str(prefix)],check=True)
payload=subprocess.check_output(['dpkg-deb','--fsys-tarfile',str(plugin)])
with tarfile.open(fileobj=io.BytesIO(payload)) as archive:
    files=[m for m in archive if m.isfile() and m.name.startswith('./opt/xilinx/xrt/lib/libxrt_driver_xdna.so.')]
    assert len(files)==1
    member=files[0];data=archive.extractfile(member).read()
    staged=project/'output/M5'/Path(member.name).name;staged.write_bytes(data)
    subprocess.run(['sudo','-n','install','-m','0644',str(staged),str(prefix/staged.name)],check=True)
    subprocess.run(['sudo','-n','ln','-sfn',staged.name,str(prefix/'libxrt_driver_xdna.so.2')],check=True)
    (project/'docs/M5/shim-payload.json').write_text(json.dumps({'source_deb':str(plugin.relative_to(project)),
        'member':member.name,'sha256':hashlib.sha256(data).hexdigest(),'destination':str(prefix/staged.name),
        'method':'userspace-only payload copy; plugin DEB NOT installed; official whole-package procedure NOT used'},indent=2)+'\n')
print('XRT2.21 userspace installed; isolated SHIM copied; NO DKMS/driver/firmware operation.')

# XRT scans the directory of libxrt_core for driver SHIM plugins.
subprocess.run(['sudo','-n','ln','-sfn',str(prefix/'libxrt_driver_xdna.so.2'),'/opt/xilinx/xrt/lib/libxrt_driver_xdna.so.2'],check=True)
