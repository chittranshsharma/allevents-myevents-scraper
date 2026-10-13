"""Queue a bounded scan through the authenticated API and report its outcome."""
import argparse
import sys
import time
from pathlib import Path
import httpx

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / 'backend'))
from app.config import settings

parser = argparse.ArgumentParser()
parser.add_argument('--pages', type=int, default=10, choices=range(1,31))
args = parser.parse_args()
if not settings.admin_token:
    parser.error('Run from backend/ with ADMIN_TOKEN configured')
with httpx.Client(base_url='http://127.0.0.1:8000', timeout=10) as client:
    response = client.post('/api/jobs/discovery', headers={'Authorization':'Bearer '+settings.admin_token}, json={'max_pages':args.pages,'max_depth':1})
    response.raise_for_status()
    job_id = response.json()['id']
    print(f'Queued job #{job_id}. The separate worker must be running.')
    for _ in range(180):
        response = client.get(f'/api/jobs/{job_id}')
        response.raise_for_status()
        job = response.json()
        if job['status'] in ('completed','partial','failed'):
            print(job['message'])
            raise SystemExit(0 if job['status'] == 'completed' else 1)
        time.sleep(2)
    raise SystemExit('Job is still queued/running; inspect the Discovery monitor and worker.')
