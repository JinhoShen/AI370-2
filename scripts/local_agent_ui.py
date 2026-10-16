#!/usr/bin/env python3
"""Loopback-only UI for the existing Local Agent; no cloud, shell or downloads."""
import argparse
import hashlib
import hmac
import json
import os
import secrets
import shutil
import signal
import subprocess
import sys
import threading
import time
import urllib.request
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'output/local-ui'
API = 'http://127.0.0.1:13305/api/v1/'
FORMAL = 'Qwen3.8-27B-UD-Q4_K_XL'
ROSS = 'http://172.18.0.4:8080/mcp/doc-search'
MODEL_ROOT = ROOT / 'resources/Agent_Tools_Docs/04_Local_AI/GGUF'
ASSETS = Path(__file__).parent / 'local_ui'


def api(name):
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(API + name, timeout=5) as response:
        return json.load(response)


def models():
    result = []
    for row in api('models').get('data', []):
        path = Path(row.get('checkpoint', ''))
        present = path.is_file() and path.resolve().parent == MODEL_ROOT.resolve()
        retired = 'qwen3.6' in row['id'].lower()
        result.append(dict(id=row['id'], bytes=path.stat().st_size if present else None,
                           available=present and not retired, retired=retired,
                           verified_engineering=row['id'] in {FORMAL, 'gemma-4-31b-jang-crack-Q4_K_M'}))
    return result


def ready_model(selected):
    row = next((r for r in models() if r['id'] == selected), None)
    if not row or not row['available']:
        raise ValueError('模型不存在、未登錄或已退休；不會下載')
    health = api('health')
    loaded = [m for m in health.get('all_models_loaded', []) if m.get('type') == 'llm']
    if len(loaded) != 1 or loaded[0].get('model_name') != selected or not loaded[0].get('backend_alive'):
        raise ValueError('請先載入選定模型，模型就緒後才能送出工作')
    if loaded[0].get('is_busy'):
        raise ValueError('模型正由其他工作使用')
    if selected == FORMAL:
        from verify_local_agent_runtime import verify
        verify(smoke=False)
    return health


def load_command(selected):
    threads = len(os.sched_getaffinity(0))
    extra = ' --batch-size 2048 --ubatch-size 512 --flash-attn auto --cache-type-k f16 --cache-type-v f16' if selected == FORMAL else ''
    return ['/usr/bin/lemonade', 'load', selected, '--ctx-size', '16384',
            '--llamacpp', 'vulkan', '--llamacpp-device', 'Vulkan0', '--no-merge-args',
            '--llamacpp-args', f'--n-gpu-layers 99 --parallel 1 --reasoning off --threads {threads} --threads-batch {threads} --offline'+extra]


def memory():
    return {s.split(':')[0]: int(s.split()[1]) for s in Path('/proc/meminfo').read_text().splitlines() if s.endswith(' kB')}


def save(path, data):
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    temp.replace(path)


from local_agent import LocalAgent, AgentError


class ReadOnlyAgent(LocalAgent):
    def _tool_specs(self):
        return [t for t in super()._tool_specs() if t['function']['name'] in {'list_files', 'read_file', 'ross_skill_read', 'ross_doc_search'}]
    def _tool(self, name, arguments):
        if name not in {'list_files', 'read_file', 'ross_skill_read', 'ross_doc_search'}:
            raise AgentError('UI 唯讀模式禁止修改與執行命令')
        return super()._tool(name, arguments)

def fixed_synthesis(agent, workspace):
    """Trusted one-source batch flow; no model-supplied Tcl or shell accepted."""
    directory = workspace / 'vivado-synthesis'
    directory.mkdir()
    source = workspace / 'rtl/local_model_axi_lite.v'
    before = hashlib.sha256(source.read_bytes()).hexdigest()
    script = directory / 'synthesis.tcl'
    script.write_text(
        'set_param general.maxThreads '+str(min(32,len(os.sched_getaffinity(0))))+'\n'
        'read_verilog -sv {'+str(source)+'}\n'
        'synth_design -top local_model_axi_lite -part xc7s100fgga676-2\n'
        'create_clock -name aclk -period 10.000 [get_ports aclk]\n'
        'report_utilization -file {'+str(directory/'utilization.rpt')+'}\n'
        'report_timing_summary -file {'+str(directory/'timing.rpt')+'}\n'
        'puts LOCAL_UI_VIVADO_SYNTHESIS_PASS\nexit\n')
    command = ['/home/shen/tools/Xilinx/2026.1/2026.1/Vivado/bin/vivado',
               '-mode','batch','-notrace','-source',str(script),
               '-log',str(directory/'vivado.log'),'-journal',str(directory/'vivado.jou')]
    agent._trace({'event':'tool_call','name':'fixed_vivado_synthesis','arguments':{'part':'xc7s100fgga676-2'}})
    result = agent._run_bounded(command,share_net=True,timeout=180)
    (directory/'stdout.log').write_text(result.stdout)
    (directory/'stderr.log').write_text(result.stderr)
    same = hashlib.sha256(source.read_bytes()).hexdigest() == before
    passed = (result.returncode == 0 and 'LOCAL_UI_VIVADO_SYNTHESIS_PASS' in result.stdout
              and all((directory/name).is_file() for name in ['utilization.rpt','timing.rpt']) and same)
    value = dict(status='PASS' if passed else 'FAIL',exit_code=result.returncode,
                 source_sha256=before,source_unchanged_by_controller=same,
                 timing='REPORT_ONLY; IO delays unconstrained; not timing closure',command=command)
    save(directory/'result.json',value)
    agent._trace({'event':'tool_result','name':'fixed_vivado_synthesis','result':value})
    if not passed:
        raise AgentError('Vivado synthesis 未通過；保留完整 log，不宣稱工程 PASS')
    return value


def worker(config_path):
    from local_agent import LocalAgent, AgentError
    cfg = json.loads(config_path.read_text())
    mode = cfg['mode']
    engineering = mode in {'xsim','vivado'}
    cls = LocalAgent if engineering else ReadOnlyAgent
    agent = cls(Path(cfg['workspace']), task=cfg['task'], model=cfg['model'],
                timeout=180, total_timeout=600, max_completion_tokens=2048, max_calls=12,
                trace=config_path.parent / 'trace.jsonl',
                editable_paths={'rtl/local_model_axi_lite.v'} if engineering else set(),
                xsim_enabled=engineering, ross_docsearch_url=ROSS if cfg['ross'] else None,
                ross_context_chars=1800, ross_mcp_chars=1200)
    try:
        text = agent.run()
        if engineering and not (agent.xsim_passed and agent.patch_count >= 1 and agent.validation_count >= 2):
            raise AgentError('沒有完整 model patch 與 XSim 驗證證據')
        synthesis = fixed_synthesis(agent,Path(cfg['workspace'])) if mode == 'vivado' else None
        if synthesis:
            text += ' Fixed Vivado synthesis PASS; utilization/timing reports retained (not timing closure).'
        print(json.dumps(dict(status='PASS' if engineering else 'COMPLETED', result=text, synthesis=synthesis,
                             patches=agent.patch_count, validations=agent.validation_count), ensure_ascii=False))
    finally:
        agent.close()


class Controller:
    def __init__(self):
        DATA.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.lock = threading.Lock()
        self.active = None
        self.blocked_loads = {}
        self.cancel = threading.Event()
        self.process = None
        for path in DATA.glob('*/job.json'):
            try:
                job = json.loads(path.read_text())
                if job.get('action') == 'load' and job.get('status') == 'FAIL' and 'Swap guard' in job.get('result',''):
                    self.blocked_loads[job['model']] = '先前載入觸發資源 guard；本配置暫停，需先診斷'
                if job.get('status') == 'RUNNING':
                    job.update(status='INTERRUPTED', result='介面服務重新啟動；先前工作未確認完成，不會自動重跑')
                    save(path, job)
            except (OSError, ValueError):
                pass

    def status(self):
        jobs = []
        for path in sorted(DATA.glob('*/job.json'), reverse=True)[:30]:
            try:
                job = json.loads(path.read_text())
                trace = path.parent / 'trace.jsonl'
                job['events'] = []
                if trace.is_file():
                    for line in trace.read_text().splitlines()[-12:]:
                        event = json.loads(line)
                        job['events'].append({'event': event.get('event'), 'name': event.get('name'), 'call': event.get('call')})
                jobs.append(job)
            except (OSError, ValueError):
                continue
        try:
            health = api('health')
            runtime = {'status': health.get('status'), 'model': health.get('model_loaded'),
                       'loaded': [{'model': m.get('model_name'), 'ready': m.get('backend_alive'),
                                   'device': m.get('device')} for m in health.get('all_models_loaded', []) if m.get('type') == 'llm']}
            catalog = models()
            for row in catalog:
                row['load_blocked_reason'] = self.blocked_loads.get(row['id'])
            error = None
        except Exception as exc:
            runtime, catalog, error = {}, [], str(exc)
        return dict(active=self.active, jobs=jobs, runtime=runtime, models=catalog, error=error,
                    ram_available_gib=round(memory()['MemAvailable']/1024**2, 1))

    def submit(self, data):
        action = data.get('action')
        if action not in {'task', 'load'}:
            raise ValueError('不支援此操作')
        selected = data.get('model')
        row = next((r for r in models() if r['id'] == selected), None)
        if not row or not row['available']:
            raise ValueError('不可選用此模型')
        mode = data.get('mode', 'read')
        task = data.get('task', '').strip()
        if action == 'task' and (mode not in {'read', 'xsim', 'vivado'} or not 1 <= len(task) <= 12000):
            raise ValueError('請輸入工作要求（1–12000 字元）')
        with self.lock:
            if action == 'load' and selected in self.blocked_loads:
                raise ValueError(self.blocked_loads[selected])
            if self.active:
                raise ValueError('目前工作仍在執行，請等待或停止')
            health = api('health')
            if any(m.get('is_busy') for m in health.get('all_models_loaded', [])):
                raise ValueError('模型正由其他工作使用')
            if action == 'task':
                ready_model(selected)
            m = memory()
            if m['MemAvailable'] < max(6*1024**2, m['MemTotal']//8):
                raise ValueError('可用記憶體不足，未啟動工作')
            key = datetime.now().astimezone().strftime('%Y%m%dT%H%M%S') + '-' + secrets.token_hex(3)
            directory = DATA / key
            directory.mkdir(mode=0o700)
            job = dict(id=key, action=action, model=selected, mode=mode, task=task,
                       ross=bool(data.get('ross')), status='RUNNING', started=datetime.now().astimezone().isoformat(),
                       evidence=str(directory))
            self.active = key
            self.cancel.clear()
            save(directory/'job.json', job)
            threading.Thread(target=self.run, args=(directory, job), daemon=True).start()
            return {'id': key}

    def run(self, directory, job):
        from run_local_model_lab_practical import stop
        begin = time.monotonic()
        load_started = False
        swap0 = memory()['SwapTotal'] - memory()['SwapFree']
        try:
            last_audit = 0
            if job['action'] == 'load':
                settings = json.loads((Path.home()/'.config/lemonade/config.json').read_text())
                if settings.get('offline') is not True or settings.get('no_fetch_executables') is not True:
                    raise RuntimeError('需要既有 offline/no-fetch 設定，未載入或下載任何模型')
                # No --save-options: changing selection never rewrites formal recipes.
                # CLI unload is explicit before load, so no second large model remains.
                health = api('health')
                already_ready = False
                try:
                    ready_model(job['model'])
                    already_ready = True
                except (ValueError, RuntimeError):
                    pass
                if already_ready:
                    command = None
                else:
                    for model in health.get('all_models_loaded', []):
                        if model.get('type') == 'llm':
                            subprocess.run(['/usr/bin/lemonade', 'unload', model['model_name']], check=True,
                                           capture_output=True, timeout=45)
                    command = load_command(job['model'])
            else:
                workspace = ROOT
                task = job['task']
                if job['mode'] in {'xsim','vivado'}:
                    source = ROOT/'docs/M13/evidence/2026-10-12/local-qwen-standalone-agent-rtl/source'
                    workspace = directory/'workspace'
                    for relative, original in [('rtl/local_model_axi_lite.v','seeded_rtl.v'),('sim/tb_local_model_axi_lite.sv','testbench.sv'),('run_validation.sh','run_validation.sh'),('TASK_SPEC.md','task_spec.md')]:
                        target = workspace/relative
                        target.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(source/original, target)
                    task = ('Read TASK_SPEC.md and RTL, run unchanged baseline first, diagnose actual failure, make a source-only repair and rerun XSim. Never change testbench/runner. User request: '+task)
                    if job['ross']:
                        task += ' Use ross_skill_read (vivado-simulate-rtl and references/xsim.md) and ross_doc_search before source changes.'
                cfg = dict(job, workspace=str(workspace), task=task)
                save(directory/'config.json', cfg)
                command = [sys.executable, str(Path(__file__).resolve()), '--worker', str(directory/'config.json')]
            save(directory/'command.json', command)
            if command:
                with (directory/'stdout.log').open('w') as stdout, (directory/'stderr.log').open('w') as stderr:
                    load_started = job['action'] == 'load'
                    self.process = subprocess.Popen(command, cwd=ROOT, stdout=stdout, stderr=stderr, start_new_session=True)
                    while self.process.poll() is None:
                        if self.cancel.wait(.5):
                            raise RuntimeError('CANCELLED')
                        m = memory()
                        if m['MemAvailable'] < max(6*1024**2,m['MemTotal']//8) or m['SwapTotal']-m['SwapFree']-swap0 > 64*1024:
                            raise RuntimeError('記憶體／Swap guard，工作停止')
                        if time.monotonic()-last_audit > 10:
                            from run_local_model_lab_practical import fault_audit
                            audit = fault_audit(job['started'])
                            if audit['read_exit'] or audit['faults']:
                                raise RuntimeError('Kernel fault audit failed; 已停止本工作')
                            last_audit = time.monotonic()
                        if time.monotonic()-begin > 650:
                            raise TimeoutError('有界工作逾時')
                    if self.cancel.is_set():
                        raise RuntimeError('CANCELLED')
                    if self.process.returncode:
                        raise RuntimeError((directory/'stderr.log').read_text()[-2000:] or '工具執行失敗')
            if job['action'] == 'load':
                ready_model(job['model'])
                job['status'], job['result'] = 'COMPLETED', '模型已就緒；未修改儲存的正式 recipe。'
            else:
                result = json.loads((directory/'stdout.log').read_text().splitlines()[-1])
                job.update(status=result['status'], result=result['result'])
        except Exception as exc:
            job.update(status='CANCELLED' if self.cancel.is_set() else 'FAIL', result=str(exc))
            if job['action'] == 'load' and 'Swap guard' in str(exc):
                self.blocked_loads[job['model']] = '先前載入觸發資源 guard；本配置暫停，需先診斷'
        finally:
            stop(self.process)
            # A cancelled CLI load may leave its server-owned model request running.
            if load_started and job['status'] not in {'COMPLETED','PASS'}:
                try:
                    subprocess.run(['/usr/bin/lemonade','unload',job['model']], timeout=45, capture_output=True)
                except Exception:
                    job['cleanup_warning'] = '模型卸載未確認；送出下一工作前請檢查目前模型'
            self.process = None
            job.update(elapsed_seconds=round(time.monotonic()-begin,3), completed=datetime.now().astimezone().isoformat())
            save(directory/'job.json',job)
            with self.lock:
                self.active = None

    def stop(self):
        self.cancel.set()
        return {'status': 'STOP_REQUESTED'}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def send(self, status, body, mime='application/json; charset=utf-8'):
        payload = body if isinstance(body,bytes) else json.dumps(body,ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header('Content-Type', mime)
        self.send_header('Content-Length',str(len(payload)))
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Content-Security-Policy',"default-src 'self'; connect-src 'self'; style-src 'self'; script-src 'self'; frame-ancestors 'none'; form-action 'self'")
        self.end_headers()
        self.wfile.write(payload)

    def allowed(self):
        expected = '127.0.0.1:'+str(self.server.server_port)
        return self.headers.get('Host') == expected and self.headers.get('Origin', 'http://'+expected) == 'http://'+expected and self.headers.get('Sec-Fetch-Site','same-origin') in {'same-origin','none'}

    def do_GET(self):
        if not self.allowed():
            return self.send(403,{'error':'只允許本機同源介面'})
        if self.path == '/api/state':
            return self.send(200,self.server.controller.status())
        if self.path == '/api/session':
            return self.send(200,{'token':self.server.token})
        asset = {'/':'index.html','/app.js':'app.js','/style.css':'style.css'}.get(self.path)
        if not asset:
            return self.send(404,{'error':'不存在'})
        return self.send(200,(ASSETS/asset).read_bytes(),{'index.html':'text/html; charset=utf-8','app.js':'text/javascript; charset=utf-8','style.css':'text/css; charset=utf-8'}[asset])

    def do_POST(self):
        if not self.allowed() or not hmac.compare_digest(self.headers.get('X-UI-Token',''),self.server.token):
            return self.send(403,{'error':'本機同源驗證失敗，請重新整理'})
        try:
            length = int(self.headers.get('Content-Length','0'))
            if length < 1 or length > 20000 or self.headers.get('Content-Type','').split(';')[0] != 'application/json':
                raise ValueError('要求格式或長度不正確')
            data = json.loads(self.rfile.read(length))
            if not isinstance(data,dict):
                raise ValueError('需要 JSON object')
            if self.path == '/api/stop':
                result = self.server.controller.stop()
            elif self.path == '/api/jobs':
                result = self.server.controller.submit(data)
            else:
                return self.send(404,{'error':'不存在'})
            self.send(200,result)
        except Exception as exc:
            self.send(400,{'error':str(exc)})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port',type=int,default=13306)
    parser.add_argument('--worker',type=Path)
    args = parser.parse_args()
    os.umask(0o077)
    if args.worker:
        worker(args.worker)
        return
    controller = Controller()
    server = ThreadingHTTPServer(('127.0.0.1',args.port),Handler)
    server.controller,server.token = controller,secrets.token_urlsafe(32)
    def shutdown(*_):
        controller.stop()
        threading.Thread(target=server.shutdown,daemon=True).start()
    signal.signal(signal.SIGTERM,shutdown)
    try:
        print(f'Local Agent UI http://127.0.0.1:{args.port}',flush=True)
        server.serve_forever()
    finally:
        controller.stop()
        deadline = time.monotonic()+25
        while controller.active and time.monotonic()<deadline:
            time.sleep(.1)
        server.server_close()


if __name__ == '__main__':
    main()
