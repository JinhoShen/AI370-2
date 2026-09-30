"""Read-only host inventory; writes evidence only under docs/M0."""
import datetime
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
from pathlib import Path

PROJECT=Path('/home/shen/AI370-2')
OUT=PROJECT/'docs/M0'
OUT.mkdir(parents=True,exist_ok=True)
records=[]
def capture(name,args,timeout=20):
    start=datetime.datetime.now().astimezone().isoformat()
    try:
        p=subprocess.run(args,capture_output=True,text=True,timeout=timeout,env={**os.environ,'LC_ALL':'C'},cwd=PROJECT)
        result={'started_at':start,'command':args,'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr}
    except (OSError,subprocess.TimeoutExpired) as e:
        result={'started_at':start,'command':args,'returncode':None,'error':str(e)}
    records.append({'file':name+'.txt',**result})
    text='$ '+' '.join(args)+'\n'+result.get('stdout','')
    if result.get('stderr'): text+='\n[stderr]\n'+result['stderr']
    if result.get('error'): text+='\n[error]\n'+result['error']+'\n'
    text+='\n[returncode] '+str(result['returncode'])+'\n'
    (OUT/(name+'.txt')).write_text(text)
    print(name,result['returncode'],flush=True)
    return result

capture('system',['bash','-c','date --iso-8601=seconds; uname -a; cat /etc/os-release; uptime; timedatectl show -p Timezone -p NTPSynchronized; cat /proc/cmdline'])
capture('cpu',['lscpu'])
capture('ram',['bash','-c','free -h; cat /proc/meminfo; lsmem; lshw -class memory -short'],timeout=30)
capture('bios',['bash','-c','for n in sys_vendor product_name product_version board_vendor board_name board_version bios_vendor bios_version bios_date; do printf "%s: " "$n"; cat "/sys/class/dmi/id/$n"; done; mokutil --sb-state'])
capture('disks',['bash','-c','lsblk -b -o NAME,SIZE,TYPE,FSTYPE,MOUNTPOINTS,MODEL,TRAN; df -B1 -T; findmnt -no SOURCE,TARGET,FSTYPE,OPTIONS /; swapon --show --bytes'])
capture('pci',['lspci','-nnk'])
capture('usb',['lsusb'])
capture('modules',['lsmod'])
capture('driver_metadata',['bash','-c','for m in amdgpu amdxdna amd64_edac mt7925e r8169; do printf "\nMODULE %s\n" "$m"; modinfo "$m" 2>&1 | sed -n "/^filename:/p; /^version:/p; /^srcversion:/p; /^vermagic:/p; /^signer:/p"; done; printf "\nNPU firmware declarations\n"; modinfo -F firmware amdxdna; printf "\nFirmware files\n"; find /lib/firmware/amdnpu -maxdepth 3 -type f -printf "%P %s bytes\n"'])
capture('device_permissions',['bash','-c','id; ls -l /dev/kfd /dev/dri /dev/accel; getfacl -cp /dev/kfd /dev/dri/renderD128 /dev/accel/accel0; for p in /dev/kfd /dev/dri/renderD128 /dev/accel/accel0; do if test -r "$p" && test -w "$p"; then printf "%s: readable+writable\n" "$p"; else printf "%s: access restricted\n" "$p"; fi; done'])
capture('packages',['dpkg-query','-W','-f=${db:Status-Abbrev}\t${binary:Package}\t${Version}\n'])
capture('graphics_packages',['bash','-c',"dpkg-query -W -f='${db:Status-Abbrev}\\t${binary:Package}\\t${Version}\\n' | awk '$1 == \"ii\"' | rg '\\t(linux-(image|headers|firmware)|amd64-microcode|libdrm|mesa|libegl-mesa|libgl1-mesa|libglx-mesa|libvulkan|xserver-xorg-video-amdgpu|rocm|hip|hsa|xrt|amdxdna|ocl-icd|opencl)'" ])
capture('kernel_gpu_npu',['bash','-c',"journalctl -b -k --no-pager | rg -i 'amdgpu|amdxdna|kfd|firmware.*(error|fail)'" ])
capture('kernel_warnings',['journalctl','-b','-k','-p','warning','--no-pager'])
capture('git_state',['bash','-c','git rev-parse --show-toplevel; git status --short --branch; git log -1 --format="%H %s"; git remote -v'])
capture('historical_bundle',['git','bundle','list-heads',str(PROJECT/'resources/Agent_Tools_Docs/05_SER9_Project/Git/SER9-AI-FPGA-Workstation.bundle')])

device={}
for label,bdf in [('gpu','0000:c5:00.0'),('npu','0000:c6:00.1')]:
    p=Path('/sys/bus/pci/devices')/bdf
    d={'bdf':bdf}
    for attr in ['vendor','device','revision','class','power/runtime_status']:
        try: d[attr]=(p/attr).read_text().strip()
        except OSError as e: d[attr]={'error':str(e)}
    d['driver']=(p/'driver').resolve().name if (p/'driver').exists() else None
    if label=='gpu':
        for attr in ['mem_info_vram_total','mem_info_gtt_total']:
            try: d[attr]=int((p/attr).read_text())
            except OSError as e: d[attr]={'error':str(e)}
    device[label]=d

tools={}
safe_versions={'gcc':['--version'],'g++':['--version'],'make':['--version'],'git':['--version'],'python3':['--version'],'node':['--version'],'npm':['--version'],'cmake':['--version'],'ninja':['--version'],'clang':['--version'],'uv':['--version'],'rustc':['--version'],'cargo':['--version'],'go':['version'],'docker':['--version'],'podman':['--version'],'code':['--version'],'git-lfs':['--version'],'pip':['--version'],'pip3':['--version']}
for name in [*safe_versions,'conda','rocminfo','hipcc','rocm-smi','amd-smi','xrt-smi','xbutil','vulkaninfo','glxinfo','clinfo','lemonade','vivado','vitis','dkms','codex']:
    path=shutil.which(name)
    d={'path':path}
    if path and name in safe_versions:
        try:
            r=subprocess.run([path,*safe_versions[name]],capture_output=True,text=True,timeout=10,env={**os.environ,'LC_ALL':'C'})
            d.update(version_output=(r.stdout+r.stderr).strip(),returncode=r.returncode)
        except (OSError,subprocess.TimeoutExpired) as e: d['error']=str(e)
    tools[name]=d
capture('python_packages',['python3','-B','-c','import importlib.metadata as m, json, importlib.util as u; names={"numpy","torch","torchvision","torchaudio","tensorflow","onnx","onnxruntime","onnxruntime-gpu","transformers","openvino","pip","uv"}; print(json.dumps({"packages":{d.metadata.get("Name", ""):d.version for d in m.distributions() if d.metadata.get("Name", "").lower() in names}, "modules":{n:u.find_spec(n) is not None for n in ("pip","venv")}},indent=2))'])
capture('optional_install_locations',['bash','-c','ls -la /opt /usr/local/bin; printf "\nVirtual environment indicators\n"; printenv | rg "^(VIRTUAL_ENV|CONDA_PREFIX|ROCM_PATH|HIP_PATH|XILINX_XRT|XDG_SESSION_TYPE|DISPLAY|WAYLAND_DISPLAY)="; printf "\nUser tool locations\n"; for p in /home/shen/.cargo /home/shen/.rustup /home/shen/.nvm /home/shen/.local/bin; do test ! -e "$p" || ls -ld "$p"; done'])
snapshot={'captured_at':datetime.datetime.now().astimezone().isoformat(),'project':str(PROJECT),'os_kernel':platform.uname()._asdict(),'devices':device,'tools':tools,'scope':'Read-only host inventory; evidence files only. No install, update, GPU/NPU workload, or Git mutation.','commands':records}
(OUT/'inventory.json').write_text(json.dumps(snapshot,ensure_ascii=False,indent=2)+'\n')
evidence=sorted(p for p in OUT.iterdir() if p.is_file() and p.name!='SHA256SUMS')
(OUT/'SHA256SUMS').write_text(''.join(f"{hashlib.file_digest(p.open('rb'),'sha256').hexdigest()}  {p.name}\n" for p in evidence))
print('M0 evidence collection complete',snapshot['captured_at'],flush=True)
