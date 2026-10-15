import json
import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch
import verify_local_agent_runtime as runtime


class RuntimeTests(unittest.TestCase):
    def fixture(self,base):
        model=base/'fixture.gguf';model.write_bytes(b'fixture; never loaded')
        ref=dict(bytes=model.stat().st_size,mtime_ns=model.stat().st_mtime_ns,sha256='recorded-sha')
        p=base/'docs/LOCAL_MODEL_LAB/evidence/qwen-performance-2026-10-14/result.json';p.parent.mkdir(parents=True);p.write_text(json.dumps({'integrity':ref}))
        cfg=base/'.config/lemonade/config.json';cfg.parent.mkdir(parents=True);cfg.write_text(json.dumps(dict(offline=True,no_fetch_executables=True,auto_check_model_updates=False,auto_update_models=False,telemetry={'enabled':False})))
        argv=['/fixture/build-vulkan/bin/llama-server','--ctx-size','16384','--n-gpu-layers','99','--threads','3','--threads-batch','3']
        return model,cfg,argv

    def context(self,base,model,argv):
        stack=ExitStack()
        stack.enter_context(patch.object(runtime.lab,'ROOT',base))
        stack.enter_context(patch.object(runtime.lab,'load_config',return_value={}))
        stack.enter_context(patch.object(runtime.lab,'model_for',return_value=dict(runtime_model_path=str(model),model_id='fixture',sha256='recorded-sha')))
        stack.enter_context(patch.object(runtime.lab,'active_llama_server',return_value=argv))
        stack.enter_context(patch.object(runtime.Path,'home',return_value=base))
        stack.enter_context(patch.object(runtime.os,'sched_getaffinity',return_value={0,1,2}))
        return stack

    def test_uses_detected_capacity_and_does_not_infer_when_not_requested(self):
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp);model,cfg,argv=self.fixture(base)
            with self.context(base,model,argv),patch.object(runtime.urllib.request,'urlopen') as net:
                self.assertEqual(runtime.verify(smoke=False)['status'],'PASS')
                net.assert_not_called()

    def test_missing_or_wrong_backend_is_rejected_before_api_autoload(self):
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp);model,cfg,argv=self.fixture(base)
            for wrong in [[],['/fixture/build-cpu/bin/llama-server']]:
                with self.context(base,model,wrong),patch.object(runtime.urllib.request,'urlopen') as net:
                    with self.assertRaises(RuntimeError):runtime.verify()
                    net.assert_not_called()

    def test_changed_artifact_and_online_settings_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp);model,cfg,argv=self.fixture(base)
            d=json.loads(cfg.read_text());d['offline']=False;cfg.write_text(json.dumps(d))
            with self.context(base,model,argv):
                with self.assertRaisesRegex(RuntimeError,'Offline'):runtime.verify(smoke=False)
            model.write_bytes(b'changed artifact')
            with self.context(base,model,argv):
                with self.assertRaisesRegex(RuntimeError,'Model changed'):runtime.verify(smoke=False)


if __name__=='__main__':
    unittest.main()
