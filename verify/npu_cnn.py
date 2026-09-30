"""Verify the supplied CNN on XDNA2, disallowing ORT CPU fallback."""
from pathlib import Path
import hashlib, json, os, time, sys
import numpy as np
import onnxruntime as ort

project=Path(__file__).resolve().parents[1]
out=project/'output/M5/cnn'
out.mkdir(parents=True,exist_ok=True)
model=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else project/'output/M5/quicktest/quicktest/test_model.onnx'
assert 'XCL_EMULATION_MODE' not in os.environ, 'Emulation forbidden'
assert 'VitisAIExecutionProvider' in ort.get_available_providers(),ort.get_available_providers()

def accel_fds(label):
    entries={}
    for fd in Path('/proc/self/fd').iterdir():
        try:
            target=os.readlink(fd)
            if target.startswith('/dev/accel/'):
                entries[fd.name]={'device':target,'fdinfo':Path('/proc/self/fdinfo',fd.name).read_text()}
        except FileNotFoundError:
            pass
    (out/f'{label}-accel-fds.json').write_text(json.dumps(entries,indent=2)+'\n')
    return entries

reference=ort.InferenceSession(str(model),providers=['CPUExecutionProvider'])
shape=[d if isinstance(d,int) and d>0 else 1 for d in reference.get_inputs()[0].shape]
data=np.random.default_rng(370).random(shape,dtype=np.float32)
expected=reference.run(None,{'input':data})
del reference
print('CPU reference calculated explicitly; candidate run forbids fallback',flush=True)
options=ort.SessionOptions()
options.log_severity_level=0
options.enable_profiling=True
options.profile_file_prefix=str(out/'ort-profile')
options.add_session_config_entry('session.disable_cpu_ep_fallback','1')
session=ort.InferenceSession(str(model),sess_options=options,providers=['VitisAIExecutionProvider'],provider_options=[{}])
session.disable_fallback()
providers=session.get_providers()
# ORT may register CPU EP even when fallback is disabled; placement/profile
# and live accelerator descriptors determine actual execution.
assert 'VitisAIExecutionProvider' in providers,providers
before=accel_fds('before')
assert before, 'No live accelerator device descriptor; NPU execution not proven'
started=time.monotonic()
for _ in range(10):
    actual=session.run(None,{'input':data})
elapsed=time.monotonic()-started
after=accel_fds('after')
profile=Path(session.end_profiling())
events=json.loads(profile.read_text())
executed=[e for e in events if e.get('cat')=='Node' and e.get('args',{}).get('provider')]
assert executed,'No node execution provider evidence'
assert {e['args']['provider'] for e in executed}=={'VitisAIExecutionProvider'},executed
errors=[]
for golden,candidate in zip(expected,actual,strict=True):
    assert np.isfinite(candidate).all()
    np.testing.assert_allclose(candidate,golden,rtol=0.10,atol=0.05)
    errors.append(float(np.max(np.abs(candidate-golden))))
result={'status':'PASS','model_sha256':hashlib.sha256(model.read_bytes()).hexdigest(),
        'onnxruntime':ort.__version__,'providers':providers,'cpu_fallback_disabled':True,
        'profile_path':str(profile.relative_to(project)),'profile_node_providers':sorted({e['args']['provider'] for e in executed}),
        'npu_device_fds':before,'after_npu_device_fds':after,'iterations':10,'elapsed_seconds':elapsed,
        'max_abs_errors':errors,'rtol':0.10,'atol':0.05}
(project/'docs/M5/cnn-result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2),flush=True)
