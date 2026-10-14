"""Test metric validity and restoration preconditions without loading a model."""
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import optimize_qwen_performance as perf


class Stream(io.BytesIO):
    pass


class MeasurementTests(unittest.TestCase):
    def test_offload_proof_survives_long_log_and_rejects_zero_layers(self):
        log = 'load_tensors: offloaded 66/66 layers to GPU\n' + 'buffer size = 1 MiB\n'*100
        self.assertEqual(len(perf.positive_offload_lines(log)),1)
        self.assertEqual(perf.positive_offload_lines('offloaded 0/66 layers to GPU'),[])

    def test_complete_sse_has_fixed_tokens_and_first_content(self):
        final = {'stop': True, 'tokens_predicted':32, 'timings':{'prompt_n':64,'predicted_n':32,'prompt_per_second':100,'predicted_per_second':5}}
        data = b'data: {"content":"word","stop":false}\n\n' + ('data: '+json.dumps(final)+'\n\n').encode()
        with tempfile.TemporaryDirectory() as d, patch.object(perf.urllib.request,'urlopen',return_value=Stream(data)) as call:
            row = perf.request(Path(d),'test')
            request = json.loads(call.call_args.args[0].data)
            self.assertFalse(request['cache_prompt'])
            self.assertTrue(request['ignore_eos'])
            self.assertEqual(row['output_tokens'],32)
            self.assertIsNotNone(row['ttft_seconds'])
            self.assertTrue((Path(d)/'test-sse.txt').exists())

    def test_incomplete_generation_is_not_pass(self):
        data = b'data: {"stop":true,"tokens_predicted":3}\n\n'
        with tempfile.TemporaryDirectory() as d, patch.object(perf.urllib.request,'urlopen',return_value=Stream(data)):
            with self.assertRaisesRegex(RuntimeError,'incomplete'):
                perf.request(Path(d),'test')

    def test_gpu_and_cpu_command_device_and_scope_are_explicit(self):
        base = dict(backend='vulkan',threads=24,threads_batch=24,layers=99,context=16384,batch=2048,ubatch=512,fa='auto',cache_k='f16',cache_v='f16',mtp=False)
        c = perf.command(base)
        self.assertEqual(c[c.index('--device')+1],'Vulkan0')
        self.assertIn('--offline',c)
        self.assertNotIn('--spec-type',c)
        c = perf.command(dict(base,backend='cpu',layers=0,mtp=True))
        self.assertEqual(c[c.index('--device')+1],'none')
        self.assertEqual(c[c.index('--spec-type')+1],'draft-mtp')


if __name__=='__main__':
    unittest.main()
