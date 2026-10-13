import asyncio
import socket
import httpx
import pytest
from app.security import normalize_url, validate_url, resolve_public, robots_allowed, SafeFetcher, AccessBlocked


def test_normalization():assert normalize_url('https://WWW.MEPASS.IN/events/one?utm_source=x#ticket')=='https://www.mepass.in/events/one'


@pytest.mark.parametrize('url',['http://www.mepass.in/events/a','https://user:pass@www.mepass.in/events/a','https://www.mepass.in:444/events/a','https://www.mepass.in/api/coupons','https://www.mepass.in/%61dmin/a','https://www.mepass.in/events?search=a','https://www.mepass.in.evil.org/events/a','https://allevents.in/city/event/123','https://127.0.0.1/events/a','file:///etc/passwd'])
def test_url_blocks(url, monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, 'allevents_authorized', False)
    with pytest.raises(AccessBlocked):validate_url(url,{'www.mepass.in','allevents.in'})


def test_private_dns(monkeypatch):
    monkeypatch.setattr(socket,'getaddrinfo',lambda *a,**k:[(socket.AF_INET,socket.SOCK_STREAM,6,'',('192.168.1.1',443))])
    with pytest.raises(AccessBlocked):resolve_public('www.mepass.in')


def test_robots_wildcards():
    rules='User-agent: *\nDisallow: /*?page=*\nDisallow: /admin/\nAllow: /admin/public$\nCrawl-delay: 8'
    assert robots_allowed(rules,'https://www.mepass.in/events?page=2')==(False,8)
    assert robots_allowed(rules,'https://www.mepass.in/admin/public')==(True,8)
    assert robots_allowed(rules,'https://www.mepass.in/admin/public/x')[0] is False


@pytest.mark.parametrize('status',[302,403,429])
def test_fetch_stops_redirect_and_challenges(status):
    def handler(req):
        if req.url.path=='/robots.txt':return httpx.Response(200,text='User-agent: *\nAllow: /',headers={'content-type':'text/plain'})
        return httpx.Response(status,headers={'content-type':'text/html','location':'https://127.0.0.1/private'})
    f=SafeFetcher({'www.mepass.in'},transport=httpx.MockTransport(handler));f.interval=0
    with pytest.raises(AccessBlocked):asyncio.run(f.fetch('https://www.mepass.in/events/a'))


def test_fail_closed_robots():
    f=SafeFetcher({'www.mepass.in'},transport=httpx.MockTransport(lambda req:httpx.Response(500)))
    with pytest.raises(httpx.HTTPStatusError):asyncio.run(f.fetch('https://www.mepass.in/events/a'))


def test_body_limit():
    def handler(req):
        return httpx.Response(200,text='User-agent: *\nAllow: /' if req.url.path=='/robots.txt' else 'x'*2_000_001,headers={'content-type':'text/plain'})
    f=SafeFetcher({'www.mepass.in'},transport=httpx.MockTransport(handler));f.interval=0
    with pytest.raises(AccessBlocked):asyncio.run(f.fetch('https://www.mepass.in/events/a'))
