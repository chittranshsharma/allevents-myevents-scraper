import secrets
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from decimal import Decimal
from fastapi import FastAPI, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.encoders import jsonable_encoder
from sqlalchemy import select, func, or_, inspect
from sqlalchemy.exc import IntegrityError
from .config import settings
from .db import get_db, utcnow, Session
from .models import Platform, Event, Organizer, TicketCategory, Promotion, Evidence, Verification, CrawlJob, CrawlResult, Watchlist, Notification
from .platforms import initialize
from .schemas import JobRequest, WatchRequest, Submission, VerificationRequest
from .intelligence import FULL_STATUSES, calculate
from .crawler import enqueue, load_sources
from .extraction import parse_page
from .service import save_event, save_promotions, notify


@asynccontextmanager
async def lifespan(app):
    with Session() as db:
        initialize(db)
        load_sources(db)
    yield


app = FastAPI(title='EventPass', version='0.1.0', lifespan=lifespan, description='Public event promotion evidence. No checkout probing or private coupon enumeration.')
app.add_middleware(CORSMiddleware, allow_origins=[settings.frontend_origin], allow_methods=['GET','POST','DELETE'], allow_headers=['Authorization','Content-Type'])
requests = defaultdict(deque)


@app.middleware('http')
async def limits(request: Request, call_next):
    address = request.client.host if request.client else 'unknown'
    now = time.monotonic()
    if address not in requests and len(requests) >= 1000:
        requests.clear()
    bucket = requests[address]
    while bucket and bucket[0] < now - 60: bucket.popleft()
    if len(bucket) >= 120:
        return JSONResponse({'error':{'code':'rate_limit','message':'120 requests per minute limit'}}, status_code=429, headers={'Retry-After':'60'})
    bucket.append(now)
    if request.method in ('POST','PUT','PATCH'):
        body = bytearray()
        async for chunk in request.stream():
            body.extend(chunk)
            if len(body) > 100000:
                return JSONResponse({'error':{'code':'body_limit','message':'Request exceeds 100 KB'}},status_code=413)
        request._body = bytes(body)
    response = await call_next(request)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    return response


@app.exception_handler(HTTPException)
async def http_error(request, exc):
    return JSONResponse({'error':{'code':str(exc.status_code),'message':exc.detail}},status_code=exc.status_code)


def admin(request: Request):
    if not settings.admin_token:
        raise HTTPException(503, 'Set ADMIN_TOKEN to enable mutations')
    token = request.headers.get('Authorization','').removeprefix('Bearer ')
    if not secrets.compare_digest(token, settings.admin_token):
        raise HTTPException(401, 'Administrator token required')


def row(model):
    from datetime import datetime, timezone
    values = {a.key:getattr(model,a.key) for a in inspect(type(model)).column_attrs}
    values = {k:v.replace(tzinfo=timezone.utc) if isinstance(v,datetime) and v.tzinfo is None else v for k,v in values.items()}
    return jsonable_encoder(values, custom_encoder={Decimal:lambda d:format(d,'.2f')})


def require(db, model, id):
    obj = db.get(model,id)
    if obj is None: raise HTTPException(404, 'Record not found')
    return obj


def promotion_row(db, p):
    result = row(p)
    result['evidence'] = [row(e) for e in db.scalars(select(Evidence).where(Evidence.promotion_id==p.id))]
    result['event_name'] = db.get(Event,p.event_id).name
    result['event_url'] = db.get(Event,p.event_id).url
    result['price_basis'] = 'estimate from event starting price; eligibility unconfirmed' if p.verification_status not in ('CONFIRMED FULL DISCOUNT','VERIFIED PARTIAL DISCOUNT') else 'administrator-recorded authorized eligible ticket measurement'
    return result


def paginate(db, query, page, page_size):
    total = db.scalar(select(func.count()).select_from(query.order_by(None).subquery()))
    return {'items':[row(r) for r in db.scalars(query.offset((page-1)*page_size).limit(page_size))], 'total':total,'page':page,'page_size':page_size}


@app.get('/api/health')
def health(db=Depends(get_db)):
    db.execute(select(1))
    return {'status':'ok','database':'connected','mode':'live-public-sources','environment':settings.app_env,'checkout_verification':'unavailable'}


@app.get('/api/platforms')
@app.get('/api/platforms/status')
def platforms(db=Depends(get_db)):
    return [row(p) for p in db.scalars(select(Platform))]


@app.get('/api/sources')
def sources(db=Depends(get_db)):
    from .models import CrawlSource
    return [row(s) for s in db.scalars(select(CrawlSource))]


@app.get('/api/events')
def events(q:str='',platform:str|None=None,location:str|None=None,min_price:Decimal|None=None,max_price:Decimal|None=None,date_from:str|None=None,date_to:str|None=None,full_discount:bool=False,status:str|None=None,min_discount:Decimal|None=None,sort:str=Query('newest',pattern='^(newest|date|price|name)$'),page:int=Query(1,ge=1),page_size:int=Query(20,ge=1,le=100),db=Depends(get_db)):
    query=select(Event)
    if q: query=query.where(Event.name.ilike('%'+q[:200]+'%'))
    if platform: query=query.where(Event.platform==platform)
    if location: query=query.where(Event.location.ilike('%'+location[:200]+'%'))
    if min_price is not None: query=query.where(Event.original_ticket_price>=min_price)
    if max_price is not None: query=query.where(Event.original_ticket_price<=max_price)
    from datetime import datetime
    for value,column,lower in [(date_from,Event.date,True),(date_to,Event.date,False)]:
        if value:
            try: date=datetime.fromisoformat(value)
            except ValueError: raise HTTPException(422,'Dates must be ISO 8601')
            query=query.where(column>=date if lower else column<=date)
    if full_discount or status or min_discount is not None:
        matching=select(Promotion.event_id)
        if full_discount: matching=matching.where(Promotion.verification_status.in_(FULL_STATUSES))
        if status: matching=matching.where(Promotion.verification_status==status)
        if min_discount is not None: matching=matching.where(Promotion.discount_type=='percentage',Promotion.discount_value>=min_discount)
        query=query.where(Event.id.in_(matching))
    order={'newest':Event.last_checked_at.desc(),'date':Event.date.asc(),'price':Event.original_ticket_price.asc(),'name':Event.name.asc()}[sort]
    return paginate(db,query.order_by(order,Event.id),page,page_size)


@app.get('/api/events/{id}')
def event_details(id:int,db=Depends(get_db)):
    e=require(db,Event,id); result=row(e)
    result['organizer']=row(db.get(Organizer,e.organizer_id)) if e.organizer_id else None
    result['tickets']=[row(t) for t in db.scalars(select(TicketCategory).where(TicketCategory.event_id==id))]
    result['promotions']=[promotion_row(db,p) for p in db.scalars(select(Promotion).where(Promotion.event_id==id))]
    return result


@app.get('/api/events/{id}/promotions')
def event_promotions(id:int,db=Depends(get_db)):
    require(db,Event,id)
    return [promotion_row(db,p) for p in db.scalars(select(Promotion).where(Promotion.event_id==id))]


@app.get('/api/promotions')
@app.get('/api/promotions/full-discount')
def promotions(request:Request,q:str='',platform:str|None=None,event_id:int|None=None,status:str|None=None,full_discount:bool=False,page:int=Query(1,ge=1),page_size:int=Query(20,ge=1,le=100),db=Depends(get_db)):
    query=select(Promotion)
    if q: query=query.where(Promotion.coupon_code.ilike('%'+q[:100]+'%'))
    if platform:query=query.where(Promotion.platform==platform)
    if event_id:query=query.where(Promotion.event_id==event_id)
    if status:query=query.where(Promotion.verification_status==status)
    if full_discount or request.url.path.endswith('full-discount'):query=query.where(Promotion.verification_status.in_(FULL_STATUSES))
    total=db.scalar(select(func.count()).select_from(query.subquery()))
    return {'items':[promotion_row(db,p) for p in db.scalars(query.order_by(Promotion.discovered_at.desc(),Promotion.id).offset((page-1)*page_size).limit(page_size))],'total':total,'page':page,'page_size':page_size}


@app.get('/api/promotions/{id}')
def promotion(id:int,db=Depends(get_db)):
    p=require(db,Promotion,id); result=promotion_row(db,p)
    result['verification_history']=[row(v) for v in db.scalars(select(Verification).where(Verification.promotion_id==id).order_by(Verification.id.desc()))]
    return result


@app.post('/api/promotions/{id}/verify',dependencies=[Depends(admin)])
def verify(id:int,body:VerificationRequest,db=Depends(get_db)):
    p=require(db,Promotion,id)
    previous=p.verification_status
    if body.method=='official_documented_api':
        raise HTTPException(422,'No official validation adapter configured; record authorized manual evidence instead')
    if body.status=='PUBLICLY ADVERTISED FULL DISCOUNT' and not db.scalar(select(Evidence.id).where(Evidence.promotion_id==id,Evidence.official==True)):
        raise HTTPException(422,'Official-source evidence required for advertised status')
    db.add(Verification(promotion_id=id,previous_status=previous,status=body.status,method=body.method,evidence_url=body.evidence_url,note=body.note,eligible_original_price=body.eligible_original_price,measured_remaining_price=body.measured_remaining_price,mandatory_fees=body.mandatory_fees))
    p.verification_status,p.verification_method,p.last_checked_at=body.status,body.method,utcnow()
    if body.eligible_original_price is not None and body.measured_remaining_price is not None:
        p.eligible_discount_amount=body.eligible_original_price-body.measured_remaining_price
        p.remaining_ticket_price=body.measured_remaining_price
        p.mandatory_fees=body.mandatory_fees
        p.estimated_final_price=p.remaining_ticket_price+p.mandatory_fees if p.mandatory_fees is not None else None
    notify(db,p,db.get(Event,p.event_id));db.commit()
    return promotion_row(db,p)


@app.get('/api/analytics/overview')
def overview(db=Depends(get_db)):
    count=lambda model,*where:db.scalar(select(func.count()).select_from(model).where(*where))
    last=db.scalar(select(CrawlJob).where(CrawlJob.status.in_(['completed','partial'])).order_by(CrawlJob.finished_at.desc()))
    worker=db.scalar(select(CrawlJob).where(CrawlJob.status=='running').order_by(CrawlJob.id.desc()))
    return {'total_events':count(Event),'events_examined':count(Event),'candidates':count(Promotion),'advertised_full_discounts':count(Promotion,Promotion.verification_status=='PUBLICLY ADVERTISED FULL DISCOUNT'),'confirmed_full_discounts':count(Promotion,Promotion.verification_status=='CONFIRMED FULL DISCOUNT'),'possible_full_discounts':count(Promotion,Promotion.verification_status=='POSSIBLE FULL DISCOUNT'),'last_successful_job':row(last) if last else None,'worker_heartbeat':row(worker) if worker else None}


@app.get('/api/analytics/discovery')
def discovery_stats(db=Depends(get_db)):
    total=db.scalar(select(func.count(Event.id))) or 0
    candidates=db.scalar(select(func.count(Promotion.id))) or 0
    verified=db.scalar(select(func.count(Promotion.id)).where(Promotion.verification_status.in_(['CONFIRMED FULL DISCOUNT','VERIFIED PARTIAL DISCOUNT','INELIGIBLE']))) or 0
    groups=dict(db.execute(select(CrawlJob.status,func.count()).group_by(CrawlJob.status)).all())
    return {'candidate_yield_per_1000_events':candidates/total*1000 if total else None,'verification_coverage':verified/candidates if candidates else None,'coverage':None,'precision':None,'coverage_note':'Total eligible platform population and adjudicated relevance are unknown.','jobs_by_status':groups,'source_results':dict(db.execute(select(CrawlResult.fetch_status,func.count()).group_by(CrawlResult.fetch_status)).all())}


@app.get('/api/jobs')
def jobs(page:int=Query(1,ge=1),page_size:int=Query(20,ge=1,le=100),db=Depends(get_db)):
    return paginate(db,select(CrawlJob).order_by(CrawlJob.id.desc()),page,page_size)


@app.get('/api/jobs/{id}')
def job(id:int,db=Depends(get_db)):
    result=row(require(db,CrawlJob,id));result['results']=[row(r) for r in db.scalars(select(CrawlResult).where(CrawlResult.job_id==id))]
    return result


@app.post('/api/jobs/discovery',dependencies=[Depends(admin)])
def start_job(body:JobRequest,db=Depends(get_db)):
    return row(enqueue(db,body.max_pages,body.max_depth,body.kind))


@app.post('/api/submissions',dependencies=[Depends(admin)])
def submission(body:Submission,db=Depends(get_db)):
    records,text,_=parse_page(body.html,body.event_url)
    if not records:raise HTTPException(422,'Submission must contain valid Event JSON-LD')
    ids=[];count=0
    for record in records:
        record['extraction_method']='organizer-submission-json-ld'
        record['provenance']['permission_note']=body.permission_note
        e=save_event(db,record,body.platform);ids.append(e.id)
        # A submitter assertion alone is not an authenticated official publication.
        count+=save_promotions(db,e,e.description+'\n'+text,body.event_url,False,'organizer-submission')
    db.commit();return {'event_ids':ids,'promotions_added':count,'method':'organizer-submission'}


@app.get('/api/watchlists',dependencies=[Depends(admin)])
def watchlists(db=Depends(get_db)):
    return [row(w) for w in db.scalars(select(Watchlist))]


@app.post('/api/watchlists',dependencies=[Depends(admin)])
def add_watch(body:WatchRequest,db=Depends(get_db)):
    if body.kind=='event':
        try:require(db,Event,int(body.value))
        except ValueError:raise HTTPException(422,'Event watch value must be a numeric event ID')
    w=Watchlist(**body.model_dump());db.add(w)
    try:db.commit()
    except IntegrityError:
        db.rollback();w=db.scalar(select(Watchlist).where(Watchlist.kind==body.kind,Watchlist.value==body.value))
    return row(w)


@app.delete('/api/watchlists/{id}',dependencies=[Depends(admin)])
def remove_watch(id:int,db=Depends(get_db)):
    db.delete(require(db,Watchlist,id));db.commit();return {'deleted':id}


@app.get('/api/notifications',dependencies=[Depends(admin)])
def notifications(page:int=Query(1,ge=1),page_size:int=Query(20,ge=1,le=100),db=Depends(get_db)):
    return paginate(db,select(Notification).order_by(Notification.id.desc()),page,page_size)
