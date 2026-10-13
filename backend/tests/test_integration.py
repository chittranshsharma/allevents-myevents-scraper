import asyncio
from datetime import timedelta
from decimal import Decimal
import httpx
from sqlalchemy import select
from app.models import Event, Promotion, CrawlJob, CrawlResult, CrawlSource, Watchlist, Notification, Platform
from app.db import utcnow
from app.crawler import enqueue,run_job,recover_jobs
from app.security import SafeFetcher
from app.service import expire_promotions
from app.config import settings
from app.platforms import initialize

AUTH={'Authorization':'Bearer test-token'}


def test_health_and_blocked_platform(client):
    assert client.get('/api/health').json()['status']=='ok'
    assert client.get('/api/platforms').json()[0]['status']=='blocked'


def test_write_auth(client):
    assert client.post('/api/jobs/discovery',json={}).status_code==401
    assert client.get('/api/watchlists').status_code==401


def test_submission_roundtrip(client,imported):
    event=client.get('/api/events/1').json()
    assert event['original_ticket_price']=='499.00' and len(event['promotions'])==1
    assert event['promotions'][0]['verification_status']=='POSSIBLE FULL DISCOUNT'
    assert event['promotions'][0]['estimated_final_price'] is None
    assert client.get('/api/promotions/full-discount').json()['total']==1


def test_idempotent_submission(client,imported,fixture_html):
    result=client.post('/api/submissions',headers=AUTH,json={'platform':'mepass','event_url':'https://www.mepass.in/events/test-fixture','html':fixture_html,'permission_note':'Test fixture document authorized.','organizer_authorized':True})
    assert result.json()['promotions_added']==0
    assert client.get('/api/events').json()['total']==1


def test_filters(client,imported):
    assert client.get('/api/events?platform=allevents').json()['total']==0
    assert client.get('/api/events?min_price=500').json()['total']==0
    assert client.get('/api/events?full_discount=true').json()['total']==1
    assert client.get('/api/events?date_from=nonsense').status_code==422
    assert client.get('/api/events?page_size=1000').status_code==422


def test_no_network_on_submission(client,fixture_html):
    result=client.post('/api/submissions',headers=AUTH,json={'platform':'mepass','event_url':'https://127.0.0.1/private','html':fixture_html,'permission_note':'Fixture permission test.','organizer_authorized':True})
    assert result.status_code==422


def test_job_deduplication(client):
    first=client.post('/api/jobs/discovery',headers=AUTH,json={}).json()
    second=client.post('/api/jobs/discovery',headers=AUTH,json={}).json()
    assert first['id']==second['id']


def test_watch_notifications_and_manual_verification(client,imported):
    assert client.post('/api/watchlists',headers=AUTH,json={'kind':'event','value':'1'}).status_code==200
    payload={'status':'CONFIRMED FULL DISCOUNT','method':'manual_authorized','evidence_url':'https://example.org/fixture-proof','note':'Authorized test fixture measurement; no actual ticket.','authorized':True,'eligible_original_price':'499','measured_remaining_price':'0','mandatory_fees':'25'}
    result=client.post('/api/promotions/1/verify',headers=AUTH,json=payload)
    assert result.status_code==200 and result.json()['estimated_final_price']=='25.00'
    client.post('/api/promotions/1/verify',headers=AUTH,json=payload)
    assert client.get('/api/notifications',headers=AUTH).json()['total']==1
    assert len(client.get('/api/promotions/1').json()['verification_history'])==2


def test_expiration(factory,client,imported):
    with factory() as db:
        p=db.get(Promotion,1);p.expiration_at=utcnow()-timedelta(days=1);db.commit();expire_promotions(db)
    assert client.get('/api/promotions/1').json()['verification_status']=='EXPIRED'
    assert client.get('/api/promotions/full-discount').json()['total']==0


def test_worker_complete_flow(factory,fixture_html):
    def handler(req):
        if req.url.path=='/robots.txt':html='User-agent: *\nAllow: /'
        elif '/category/' in req.url.path:html='<a href="/events/test-fixture">Fixture</a><a href="/api/private">Private</a>'
        else:html=fixture_html
        return httpx.Response(200,text=html,headers={'content-type':'text/html'})
    fetcher=SafeFetcher({'www.mepass.in'},transport=httpx.MockTransport(handler));fetcher.interval=0
    with factory() as db:
        db.add(Watchlist(kind='full_discount',value='All'));db.commit();job=enqueue(db,max_pages=5);id=job.id
    asyncio.run(run_job(id,fetcher))
    with factory() as db:
        job=db.get(CrawlJob,id)
        assert job.status=='completed' and job.pages_processed==2 and job.promotions_found==1
        assert db.scalar(select(Promotion)).verification_status=='PUBLICLY ADVERTISED FULL DISCOUNT'
        assert db.scalar(select(Notification)) is not None
        next_job=enqueue(db,max_pages=5);next_id=next_job.id
    asyncio.run(run_job(next_id,fetcher))
    with factory() as db:
        assert db.get(CrawlJob,next_id).promotions_found==0
        assert len(list(db.scalars(select(Promotion))))==1


def test_worker_network_failure(factory):
    f=SafeFetcher({'www.mepass.in'},transport=httpx.MockTransport(lambda req:httpx.Response(503)));f.interval=0
    with factory() as db:id=enqueue(db).id
    asyncio.run(run_job(id,f))
    with factory() as db:
        assert db.get(CrawlJob,id).status=='failed'
        assert db.scalar(select(CrawlResult)).error is not None


def test_authorized_allevents_listing_and_detail(factory, monkeypatch):
    import json
    monkeypatch.setattr(settings, 'allevents_authorized', True)
    event_url = 'https://allevents.in/bangalore/test-event/12345'
    node = {'@context':'https://schema.org','@type':'Event','name':'Test Event','url':event_url,
            'startDate':'2027-01-01T18:00:00+05:30','location':{'name':'Test Hall','address':{'addressLocality':'Bangalore'}},
            'offers':{'name':'General','price':'499','priceCurrency':'INR'}}
    listing = '<script type="application/ld+json">'+json.dumps([node,dict(node,url='https://evil.example/event/1')])+'</script><p>Use code WRONGFREE for 100% off.</p>'
    detail = '<script type="application/ld+json">'+json.dumps(node)+'</script><p>Use code TESTFREE for 100% off.</p>'
    mepass_detail = '<script type="application/ld+json">'+json.dumps(dict(node,name='Mepass Event'))+'</script>'
    def handler(req):
        if req.url.path == '/robots.txt': body='User-agent: *\nAllow: /'
        elif '/category/' in req.url.path: body='<a href="/events/mepass-one">One</a><a href="/events/mepass-two">Two</a>'
        elif req.url.path == '/bangalore/all': body=listing
        elif '/events/mepass-' in req.url.path: body=mepass_detail
        else: body=detail
        return httpx.Response(200,text=body,headers={'content-type':'text/html'})
    fetcher = SafeFetcher({'allevents.in','www.mepass.in'},transport=httpx.MockTransport(handler)); fetcher.interval=0
    with factory() as db:
        initialize(db)
        job_id=enqueue(db,max_pages=4).id
    asyncio.run(run_job(job_id,fetcher))
    with factory() as db:
        job=db.get(CrawlJob,job_id)
        assert job.status=='completed' and job.pages_processed==4 and job.events_found==3
        assert db.scalar(select(Platform).where(Platform.id=='allevents')).status=='public_html'
        assert db.scalar(select(Event).where(Event.platform=='allevents')).url==event_url
        promotions=list(db.scalars(select(Promotion)))
        assert len(promotions)==1 and promotions[0].coupon_code=='TESTFREE'


def test_stale_worker_recovery(factory):
    with factory() as db:
        j=enqueue(db);j.status='running';j.heartbeat_at=utcnow()-timedelta(minutes=11);db.commit();recover_jobs(db)
        assert j.status=='queued'


def test_oversize_body(client):assert client.post('/api/submissions',content='x'*100001,headers=AUTH).status_code==413
def test_not_found(client):assert client.get('/api/events/1234').status_code==404
