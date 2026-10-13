import json
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
from app.db import Base, get_db
from app.main import app, requests
from app.platforms import initialize
from app.config import settings


@pytest.fixture
def factory(monkeypatch):
    monkeypatch.setattr(settings,'allevents_authorized',False)
    engine = create_engine('sqlite://',connect_args={'check_same_thread':False},poolclass=StaticPool)
    Base.metadata.create_all(engine)
    sessions=sessionmaker(engine,expire_on_commit=False)
    with sessions() as db: initialize(db)
    monkeypatch.setattr('app.main.Session',sessions)
    monkeypatch.setattr('app.crawler.Session',sessions)
    monkeypatch.setattr('app.notifications.Session',sessions)
    monkeypatch.setattr(settings,'admin_token','test-token')
    monkeypatch.setattr(settings,'source_config','')
    monkeypatch.setattr(settings,'allevents_authorized',False)
    yield sessions
    engine.dispose()


@pytest.fixture
def client(factory):
    def override():
        with factory() as db:yield db
    app.dependency_overrides[get_db]=override
    requests.clear()
    with TestClient(app) as c:yield c
    app.dependency_overrides.clear()


@pytest.fixture
def fixture_html():
    record={'@context':'https://schema.org','@type':'Event','name':'TEST FIXTURE — EventPass Meetup','startDate':'2027-01-01T18:00:00+05:30','location':{'name':'Test Hall','address':{'addressLocality':'Fixture City'}},'offers':{'price':'499.00','priceCurrency':'INR','name':'General'},'organizer':{'name':'Test Organizer'},'description':'Use code FIXTUREFREE for 100% off eligible tickets. Expires 2027-01-01T10:00:00Z.'}
    return '<html><script type="application/ld+json">'+json.dumps(record)+'</script><p>'+record['description']+'</p></html>'


@pytest.fixture
def imported(client,fixture_html):
    result=client.post('/api/submissions',headers={'Authorization':'Bearer test-token'},json={'platform':'mepass','event_url':'https://www.mepass.in/events/test-fixture','html':fixture_html,'permission_note':'Test fixture document; not a real promotion.','organizer_authorized':True})
    assert result.status_code==200,result.text
    return result.json()
