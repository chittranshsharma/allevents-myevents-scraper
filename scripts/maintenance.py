"""Delete old terminal crawl telemetry only; preserve promotion evidence."""
import argparse
import sys
from pathlib import Path
from datetime import timedelta
from sqlalchemy import select,delete
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
from app.db import Session,utcnow
from app.models import CrawlJob,CrawlResult

parser=argparse.ArgumentParser()
parser.add_argument('--days',type=int,default=90)
parser.add_argument('--apply',action='store_true')
args=parser.parse_args()
if args.days < 7:parser.error('Keep at least 7 days of telemetry')
with Session() as db:
    ids=list(db.scalars(select(CrawlJob.id).where(CrawlJob.finished_at < utcnow()-timedelta(days=args.days),CrawlJob.active_slot==None)))
    print(f'{len(ids)} old terminal jobs eligible for telemetry cleanup.')
    if args.apply and ids:
        db.execute(delete(CrawlResult).where(CrawlResult.job_id.in_(ids)))
        db.execute(delete(CrawlJob).where(CrawlJob.id.in_(ids)));db.commit()
        print('Old crawl telemetry deleted; event and promotion evidence preserved.')
