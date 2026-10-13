"""Run browser tests with an isolated database and owned local servers."""
import os
import shutil
import subprocess
import time
import urllib.request
from pathlib import Path
from uuid import uuid4

root = Path(__file__).resolve().parents[1]
runtime = root / 'runtime'
runtime.mkdir(exist_ok=True)
python = root / 'backend/.venv' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
env = os.environ.copy()
env.update(DATABASE_URL='sqlite:///' + (runtime / f'e2e-{uuid4().hex}.db').as_posix(), APP_ENV='test', BACKEND_URL='http://127.0.0.1:8001', E2E_API='http://127.0.0.1:8001', E2E_URL='http://localhost:3001', FRONTEND_ORIGIN='http://localhost:3001', EVENTPASS_E2E='1')
processes = []


def ready(url):
    for _ in range(120):
        try:
            with urllib.request.urlopen(url, timeout=2) as r:
                if r.status == 200: return
        except Exception: pass
        if any(p.poll() is not None for p in processes):
            raise RuntimeError('Test server exited; inspect runtime/e2e-*.log')
        time.sleep(.5)
    raise RuntimeError('Test server did not become ready')


try:
    subprocess.run([str(python), '-m', 'alembic', 'upgrade', 'head'], cwd=root/'backend', env=env, check=True)
    with (runtime/'e2e-api.log').open('w') as api_log, (runtime/'e2e-ui.log').open('w') as ui_log:
        processes.append(subprocess.Popen([str(python), '-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', '8001'], cwd=root/'backend',env=env,stdout=api_log,stderr=subprocess.STDOUT))
        ready(env['E2E_API']+'/api/health')
        processes.append(subprocess.Popen([shutil.which('node'), 'node_modules/next/dist/bin/next','dev','--hostname','127.0.0.1','--port','3001'],cwd=root/'frontend',env=env,stdout=ui_log,stderr=subprocess.STDOUT))
        ready(env['E2E_URL'])
        result = subprocess.run([shutil.which('node'),'node_modules/@playwright/test/cli.js','test'],cwd=root/'frontend',env=env)
        exit_code = result.returncode
finally:
    for p in processes:
        if os.name == 'nt':
            subprocess.run(['taskkill','/PID',str(p.pid),'/T','/F'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        else:
            p.terminate()
    for p in processes:
        try: p.wait(timeout=5)
        except subprocess.TimeoutExpired: p.kill()
raise SystemExit(exit_code)
