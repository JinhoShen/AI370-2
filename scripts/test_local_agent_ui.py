import json
import tempfile
import threading
import unittest
import urllib.request
import urllib.error
from pathlib import Path
from unittest.mock import patch
from http.server import ThreadingHTTPServer
import local_agent_ui as ui


class UiTests(unittest.TestCase):
    def test_read_only_has_no_mutating_or_command_tools(self):
        a=ui.ReadOnlyAgent(ui.ROOT,task='test')
        names={t['function']['name'] for t in a._tool_specs()}
        self.assertEqual(names,{'list_files','read_file'})
        for name in ['apply_patch','apply_replacement','run_check','run_xsim','run_hls']:
            with self.assertRaises(ui.AgentError):a._tool(name,{})

    def test_retired_and_missing_model_cannot_be_loaded(self):
        rows={'data':[{'id':'Qwen3.6-old','checkpoint':str(ui.MODEL_ROOT/'missing.gguf')}]}
        with patch.object(ui,'api',return_value=rows):
            result=ui.models()
        self.assertFalse(result[0]['available'])
        self.assertTrue(result[0]['retired'])

    def test_task_cannot_auto_switch_or_fallback(self):
        with patch.object(ui,'models',return_value=[dict(id='chosen',available=True)]),patch.object(ui,'api',return_value={'all_models_loaded':[dict(type='llm',model_name='other',backend_alive=True)]}):
            with self.assertRaisesRegex(ValueError,'先載入'):ui.ready_model('chosen')

    def test_http_rejects_cross_origin_dns_rebinding_and_missing_csrf(self):
        server=ThreadingHTTPServer(('127.0.0.1',0),ui.Handler)
        server.token='test-token'
        class Fake:
            def status(self):return {'jobs':[]}
            def stop(self):return {'status':'STOP_REQUESTED'}
        server.controller=Fake()
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        base='http://127.0.0.1:'+str(server.server_port)
        opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
        def post(headers):
            req=urllib.request.Request(base+'/api/stop',data=b'{}',headers={'Content-Type':'application/json',**headers})
            return opener.open(req)
        try:
            for headers in [{},{'X-UI-Token':'test-token','Origin':'https://evil.example'},{'X-UI-Token':'test-token','Host':'evil.example'}]:
                with self.assertRaises(urllib.error.HTTPError) as error:post(headers)
                self.assertEqual(error.exception.code,403)
            with post({'X-UI-Token':'test-token','Origin':base}) as response:self.assertEqual(response.status,200)
            with opener.open(base+'/') as response:
                self.assertIn("frame-ancestors 'none'",response.headers['Content-Security-Policy'])
                self.assertIn('AI370-2',response.read().decode())
        finally:
            server.shutdown();server.server_close();thread.join()

    def test_formal_reload_passes_all_profile_options_explicitly_without_saving(self):
        command = ui.load_command(ui.FORMAL)
        self.assertNotIn('--save-options',command)
        self.assertEqual(command[command.index('--ctx-size')+1],'16384')
        self.assertEqual(command[command.index('--llamacpp')+1],'vulkan')
        args = command[command.index('--llamacpp-args')+1]
        for value in ['--n-gpu-layers 99','--threads 24' if len(__import__('os').sched_getaffinity(0))==24 else '--threads ', '--batch-size 2048','--ubatch-size 512','--cache-type-k f16','--offline']:
            self.assertIn(value,args)

    def test_guarded_load_stays_blocked_after_ui_restart(self):
        with tempfile.TemporaryDirectory() as temp,patch.object(ui,'DATA',Path(temp)):
            folder=Path(temp)/'trial';folder.mkdir()
            (folder/'job.json').write_text(json.dumps(dict(action='load',model='chosen',status='FAIL',result='記憶體／Swap guard，工作停止')))
            c=ui.Controller()
            self.assertIn('chosen',c.blocked_loads)

    def test_synthesis_only_uses_fixed_part_source_and_sandbox(self):
        import subprocess
        with tempfile.TemporaryDirectory() as temp:
            work=Path(temp);(work/'rtl').mkdir();(work/'rtl/local_model_axi_lite.v').write_text('module local_model_axi_lite; endmodule')
            class Agent:
                def _trace(self,event):pass
                def _run_bounded(inner,command,**kwargs):
                    self.assertEqual(command[0],'/home/shen/tools/Xilinx/2026.1/2026.1/Vivado/bin/vivado')
                    self.assertEqual(kwargs,dict(share_net=True,timeout=180))
                    tcl=(work/'vivado-synthesis/synthesis.tcl').read_text()
                    self.assertIn('synth_design -top local_model_axi_lite -part xc7s100fgga676-2',tcl)
                    self.assertNotIn('program_hw_devices',tcl)
                    for name in ['utilization.rpt','timing.rpt']:(work/'vivado-synthesis'/name).write_text('fixture report')
                    return subprocess.CompletedProcess(command,0,'LOCAL_UI_VIVADO_SYNTHESIS_PASS','')
            result=ui.fixed_synthesis(Agent(),work)
            self.assertEqual(result['status'],'PASS')
            self.assertTrue(result['source_unchanged_by_controller'])

    def test_synthesis_exit_zero_without_marker_is_failure(self):
        import subprocess
        with tempfile.TemporaryDirectory() as temp:
            work=Path(temp);(work/'rtl').mkdir();(work/'rtl/local_model_axi_lite.v').write_text('module m; endmodule')
            class Agent:
                def _trace(self,event):pass
                def _run_bounded(self,*args,**kwargs):return subprocess.CompletedProcess([],0,'no success marker','')
            with self.assertRaisesRegex(ui.AgentError,'未通過'):ui.fixed_synthesis(Agent(),work)

    def test_no_parallel_job(self):
        with tempfile.TemporaryDirectory() as temp,patch.object(ui,'DATA',Path(temp)),patch.object(ui,'models',return_value=[dict(id='chosen',available=True)]):
            c=ui.Controller();c.active='existing'
            with self.assertRaisesRegex(ValueError,'仍在執行'):c.submit(dict(action='load',model='chosen'))


    def test_only_flat_model_root_payloads_are_available(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)/'models';(root/'Legacy_Cache/hf/snapshots/x').mkdir(parents=True);(root/'Ross_Offline_Resources').mkdir()
            (root/'GGUF').symlink_to('.')
            (root/'flat.gguf').write_bytes(b'flat')
            (root/'Legacy_Cache/hf/snapshots/x/legacy.gguf').write_bytes(b'legacy')
            (root/'Ross_Offline_Resources/embed.gguf').write_bytes(b'embed')
            (root/'linked.gguf').symlink_to(root/'Legacy_Cache/hf/snapshots/x/legacy.gguf')
            rows={'data':[dict(id='flat',checkpoint=str(root/'GGUF/flat.gguf')),
                          dict(id='legacy',checkpoint=str(root/'Legacy_Cache/hf/snapshots/x/legacy.gguf')),
                          dict(id='legacy-via-gguf-link',checkpoint=str(root/'GGUF/Legacy_Cache/hf/snapshots/x/legacy.gguf')),
                          dict(id='flat-link-into-legacy',checkpoint=str(root/'linked.gguf')),
                          dict(id='nested-resource',checkpoint=str(root/'Ross_Offline_Resources/embed.gguf')),
                          dict(id='missing',checkpoint=str(root/'missing.gguf'))]}
            with patch.object(ui,'MODEL_ROOT',root/'GGUF'),patch.object(ui,'api',return_value=rows):
                result={row['id']:row for row in ui.models()}
        self.assertTrue(result['flat']['available'])
        self.assertEqual(result['flat']['bytes'],4)
        for name in ['legacy','legacy-via-gguf-link','flat-link-into-legacy','nested-resource','missing']:
            self.assertFalse(result[name]['available'],name)
            self.assertIsNone(result[name]['bytes'],name)

if __name__=='__main__':unittest.main()
