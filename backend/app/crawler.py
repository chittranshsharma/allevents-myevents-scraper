import asyncio
import hashlib
import json
from datetime import timedelta
from pathlib import Path
from urllib.parse import urljoin, urlsplit
import httpx
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from .config import settings
from .db import Session, utcnow
from .models import CrawlJob, CrawlSource, CrawlResult, Event
from .security import SafeFetcher, validate_url, AccessBlocked, MEPASS_HOSTS
from .extraction import parse_page
from .service import save_event, save_promotions, expire_promotions


def enqueue(db, max_pages=10, max_depth=1, kind='discovery'):
    job = CrawlJob(max_pages=max_pages, max_depth=max_depth, kind=kind, active_slot='discovery')
    db.add(job)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return db.scalar(select(CrawlJob).where(CrawlJob.active_slot == 'discovery'))
    return job


def load_sources(db):
    if not settings.source_config:
        return
    records = json.loads(Path(settings.source_config).read_text(encoding='utf-8'))
    for r in records:
        if r['platform'] not in ('allevents', 'mepass') or not r.get('permission_basis') or not r.get('terms_url'):
            raise ValueError('Source requires platform, terms URL and permission basis')
        host = urlsplit(r['url']).hostname
        url = validate_url(r['url'], {host})
        if host not in MEPASS_HOSTS and not r.get('event_id'):
            raise ValueError('External organizer sources must be explicitly linked to an existing event')
        if r.get('event_id') and not db.get(Event, r['event_id']):
            raise ValueError('Unknown event_id')
        if not db.scalar(select(CrawlSource).where(CrawlSource.url == url)):
            db.add(CrawlSource(url=url, platform=r['platform'], source_type=r.get('source_type','promotion'), permission_basis=r['permission_basis'], terms_url=r['terms_url'], event_id=r.get('event_id'), official=bool(r.get('official',False))))
    db.commit()


async def run_job(job_id, fetcher=None):
    with Session() as db:
        job = db.get(CrawlJob, job_id)
        sources = list(db.scalars(select(CrawlSource).where(CrawlSource.enabled == True)))
        allowed = {urlsplit(s.url).hostname for s in sources}
        fetcher = fetcher or SafeFetcher(allowed, settings.request_interval_seconds)
        if not db.scalar(select(CrawlResult.id).where(CrawlResult.job_id == job_id)):
            for source in sources:
                db.add(CrawlResult(job_id=job_id, source_id=source.id, url=source.url, source_type=source.source_type, priority=100 if source.event_id else 50))
            db.commit()
        deadline = asyncio.get_running_loop().time() + 300
        while job.pages_processed + job.error_count < job.max_pages:
            if asyncio.get_running_loop().time() >= deadline:
                job.message = 'Five-minute budget reached; remaining pages checkpointed.'; break
            frontier = list(db.scalars(select(CrawlResult).where(CrawlResult.job_id == job_id)))
            queued = [item for item in frontier if item.fetch_status == 'queued']
            if not queued:
                break
            checked = {source.id: sum(item.source_id == source.id and item.fetch_status != 'queued' for item in frontier) for source in sources}
            result = min(queued, key=lambda item: (checked[item.source_id], -item.priority, item.id))
            source = db.get(CrawlSource, result.source_id)
            job.heartbeat_at = utcnow(); db.commit()
            try:
                if result.attempts >= 3:
                    raise AccessBlocked('Retry budget exhausted before recovery')
                for attempt in range(3 - result.attempts):
                    result.attempts += 1; db.commit()
                    try:
                        html = await fetcher.fetch(result.url)
                        break
                    except (httpx.TimeoutException, httpx.NetworkError) as exc:
                        if result.attempts >= 3: raise exc
                        await asyncio.sleep(2 ** result.attempts)
                digest = hashlib.sha256(html.encode()).hexdigest()
                old = db.scalar(select(CrawlResult).where(CrawlResult.url == result.url, CrawlResult.content_hash == digest, CrawlResult.parser_version == '1.1', CrawlResult.fetch_status.in_(['ok','unchanged']), CrawlResult.id != result.id))
                result.content_hash, result.last_fetched_at = digest, utcnow()
                events, text, links = parse_page(html, result.url, use_node_urls=source.platform == 'allevents')
                result.fetch_status = 'unchanged' if old else 'ok'
                if result.source_type == 'event' and not events:
                    result.fetch_status = 'no_event_metadata'
                    result.error = 'Public page fetched, but no supported Event structured data was extracted.'
                    job.error_count += 1
                if not old:
                    for record in events:
                        event = save_event(db, record, source.platform)
                        job.events_found += 1
                        if result.source_type == 'event':
                            job.promotions_found += save_promotions(db, event, event.description + '\n' + text, result.url, source.official)
                    if source.event_id:
                        event = db.get(Event, source.event_id)
                        job.promotions_found += save_promotions(db, event, text, result.url, source.official)
                else:
                    for event in db.scalars(select(Event).where(Event.url == result.url)):
                        event.last_checked_at = utcnow()
                # Only event links on the reviewed source host; budgets also bound queue size.
                if result.discovery_depth < job.max_depth and source.source_type in ('listing', 'sitemap'):
                    if source.platform == 'allevents':
                        links = [event['url'] for event in events]
                    if source.source_type == 'sitemap':
                        import xml.etree.ElementTree as ET
                        links = [loc.text for loc in ET.fromstring(html).iter() if loc.tag.split('}')[-1] == 'loc' and loc.text]
                    for link in links:
                        try:
                            url = validate_url(urljoin(result.url, link), allowed)
                            if urlsplit(url).hostname != urlsplit(source.url).hostname or (source.platform != 'allevents' and '/events/' not in url):
                                continue
                            if not db.scalar(select(CrawlResult.id).where(CrawlResult.job_id == job_id, CrawlResult.url == url)):
                                total = len(list(db.scalars(select(CrawlResult.id).where(CrawlResult.job_id == job_id))))
                                source_total = len(list(db.scalars(select(CrawlResult.id).where(CrawlResult.job_id == job_id, CrawlResult.source_id == source.id))))
                                # Reserve frontier space for each enabled source.
                                if total < job.max_pages * 3 and source_total < max(2, job.max_pages * 3 // len(sources)):
                                    previous = db.scalar(select(CrawlResult.last_fetched_at).where(CrawlResult.url == url, CrawlResult.last_fetched_at != None).order_by(CrawlResult.last_fetched_at.desc()))
                                    # New pages outrank recently seen ones; older pages get an aging bonus.
                                    age = min(40, int((utcnow() - previous.replace(tzinfo=utcnow().tzinfo)).total_seconds()/3600)) if previous else 50
                                    rank = 40 + age + (10 if urlsplit(url).path.startswith('/events/') else 0) + (5 if any(word in url.lower() for word in ('promo','discount','free-pass')) else 0) + (1 if source.platform == 'allevents' else 0)
                                    db.add(CrawlResult(job_id=job_id, source_id=source.id, url=url, source_type='event', discovery_depth=result.discovery_depth+1, priority=rank))
                                    db.flush()
                        except (ValueError, TypeError):
                            continue
                job.pages_processed += 1
            except (AccessBlocked, httpx.HTTPError) as exc:
                db.rollback(); result = db.get(CrawlResult, result.id); job = db.get(CrawlJob, job_id)
                result.fetch_status = 'blocked' if isinstance(exc, AccessBlocked) else 'failed'
                result.error = str(exc)[:300]; result.last_fetched_at = utcnow(); job.error_count += 1
            job.heartbeat_at = utcnow(); db.commit()
        job.status = 'completed' if not job.error_count else 'partial' if job.pages_processed else 'failed'
        job.finished_at, job.active_slot = utcnow(), None
        job.message = job.message or f'{job.pages_processed} pages checked; {job.promotions_found} new candidates; {job.error_count} errors.'
        db.commit()
        expire_promotions(db)


def recover_jobs(db):
    cutoff = utcnow() - timedelta(minutes=10)
    for job in db.scalars(select(CrawlJob).where(CrawlJob.status == 'running', CrawlJob.heartbeat_at < cutoff)):
        job.status = 'queued'; job.message = 'Recovered stale worker lease; resuming checkpoint.'
    db.commit()


async def worker():
    from .notifications import deliver_telegram
    while True:
        with Session() as db:
            recover_jobs(db)
            expire_promotions(db)
            if settings.schedule_minutes > 0:
                last = db.scalar(select(CrawlJob).order_by(CrawlJob.created_at.desc()))
                if not last or (last.created_at.replace(tzinfo=utcnow().tzinfo) + timedelta(minutes=max(15,settings.schedule_minutes))) < utcnow():
                    enqueue(db)
            queued = db.scalar(select(CrawlJob).where(CrawlJob.status == 'queued').order_by(CrawlJob.id))
            job_id = queued.id if queued else None
            if job_id:
                claimed = db.execute(update(CrawlJob).where(CrawlJob.id == job_id, CrawlJob.status == 'queued').values(status='running', started_at=utcnow(), heartbeat_at=utcnow())).rowcount
                db.commit()
                if not claimed: job_id = None
        if job_id:
            try:
                await asyncio.wait_for(run_job(job_id), timeout=330)
            except Exception as exc:
                with Session() as db:
                    job = db.get(CrawlJob, job_id); job.status = 'failed'; job.message = f'Worker failure: {type(exc).__name__}'; job.active_slot = None; job.finished_at = utcnow(); db.commit()
        await deliver_telegram()
        await asyncio.sleep(2)


if __name__ == '__main__':
    with Session() as db:
        load_sources(db)
    asyncio.run(worker())
