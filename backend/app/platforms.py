from .models import Platform, CrawlSource
from sqlalchemy import select
from .config import settings


def initialize(session):
    platforms = [
        ('allevents', 'allevents.in', 'public_html' if settings.allevents_authorized else 'blocked', 'Owner-authorized public HTML only; bounded direct discovery. No coupon validation API.' if settings.allevents_authorized else 'Explicit owner authorization is required for automated collection.'),
        ('mepass', 'www.mepass.in', 'public_html', 'Public HTML only; robots checked per job. API, private paths and filtered search blocked. No coupon validation API established.'),
    ]
    for id, domain, status, reason in platforms:
        platform = session.get(Platform, id)
        if not platform:
            session.add(Platform(id=id, domain=domain, status=status, reason=reason))
        elif id == 'allevents':
            platform.status, platform.reason = status, reason
    session.flush()
    url = 'https://www.mepass.in/city/bengaluru/event/category/default'
    if not session.scalar(select(CrawlSource).where(CrawlSource.url == url)):
        session.add(CrawlSource(url=url, platform='mepass', source_type='listing', permission_basis='Robots explicitly allows public crawling; terms reviewed 2026-10-13, no automation prohibition observed.', terms_url='https://www.mepass.in/terms-condition', official=True))
    allevents_url = 'https://allevents.in/bangalore/all'
    source = session.scalar(select(CrawlSource).where(CrawlSource.url == allevents_url))
    if settings.allevents_authorized and not source:
        session.add(CrawlSource(url=allevents_url, platform='allevents', source_type='listing', permission_basis='Owner reported direct AllEvents authorization for personal use on 2026-10-13.', terms_url='https://allevents.in/conditions', official=True))
    elif source:
        source.enabled = settings.allevents_authorized
    session.commit()
