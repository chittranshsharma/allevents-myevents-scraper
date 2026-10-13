import asyncio
import ipaddress
import re
import socket
import time
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
import httpx
from .config import settings

USER_AGENT = 'EventPass/0.1 (+public promotion research; conservative crawler)'
MEPASS_HOSTS = {'www.mepass.in', 'mepass.in'}
ALLEVENTS_HOSTS = {'allevents.in', 'www.allevents.in'}


class AccessBlocked(ValueError):
    pass


def normalize_url(url):
    if len(url) > 1000 or re.search(r'[\x00-\x20\\]', url):
        raise AccessBlocked('Invalid URL')
    p = urlsplit(url)
    if p.scheme != 'https' or not p.hostname or p.username or p.password or p.port not in (None, 443):
        raise AccessBlocked('Only HTTPS public URLs on port 443 are allowed')
    host = p.hostname.lower().encode('idna').decode()
    query = urlencode(sorted((k, v) for k, v in parse_qsl(p.query) if not k.lower().startswith('utm_') and k.lower() not in ('fbclid', 'gclid')))
    return urlunsplit(('https', host, p.path or '/', query, ''))


def validate_url(url, allowed_hosts):
    normalized = normalize_url(url)
    p = urlsplit(normalized)
    if (p.hostname in ALLEVENTS_HOSTS and not settings.allevents_authorized) or p.hostname not in allowed_hosts:
        raise AccessBlocked('Host is blocked or has no reviewed permission')
    # Do not normalize away a prohibited query or encoded private path.
    from urllib.parse import unquote
    path = unquote(p.path).lower()
    if p.hostname in MEPASS_HOSTS and (any(path.startswith(x) for x in ('/api', '/admin', '/_next', '/tmp', '/checkout', '/login', '/profile')) or p.query):
        raise AccessBlocked('Only unfiltered public Mepass pages are supported')
    return normalized


def resolve_public(host):
    addresses = {x[4][0] for x in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)}
    if not addresses or any(not ipaddress.ip_address(ip).is_global for ip in addresses):
        raise AccessBlocked('Private or reserved network target')
    return addresses


def robots_allowed(text, url):
    """Robots wildcard/end-anchor semantics, longest matching rule wins."""
    groups, agents, rules = [], [], []
    for raw in text.splitlines():
        line = raw.split('#', 1)[0].strip()
        if ':' not in line:
            continue
        key, value = [p.strip() for p in line.split(':', 1)]
        key = key.lower()
        if key == 'user-agent':
            if rules:
                groups.append((agents, rules)); agents, rules = [], []
            agents.append(value.lower())
        elif key in ('allow', 'disallow', 'crawl-delay') and agents:
            rules.append((key, value))
    groups.append((agents, rules))
    specific = [r for a, r in groups if any(agent != '*' and agent in USER_AGENT.lower() for agent in a)]
    selected = specific or [r for a, r in groups if '*' in a]
    p = urlsplit(url)
    target = p.path + ('?' + p.query if p.query else '')
    matches, delays = [], []
    for group in selected:
        for key, value in group:
            if key == 'crawl-delay':
                try: delays.append(float(value))
                except ValueError: pass
            elif value:
                anchored = value.endswith('$')
                pattern = re.escape(value[:-1] if anchored else value).replace(r'\*', '.*')
                if re.match('^' + pattern + ('$' if anchored else ''), target):
                    matches.append((len(value.replace('*', '').rstrip('$')), key == 'allow'))
    return (max(matches)[1] if matches else True), max(delays, default=0)


class SafeFetcher:
    def __init__(self, allowed_hosts, interval=3, transport=None):
        self.allowed_hosts = allowed_hosts
        self.interval = max(3, interval)
        self.last_fetch = {}
        self.transport = transport
        self.robots = {}
        self.stopped_hosts = set()

    async def _request(self, url):
        host = urlsplit(url).hostname
        if host in self.stopped_hosts:
            raise AccessBlocked('Host paused after access or rate-limit response')
        if self.transport is None:
            await asyncio.to_thread(resolve_public, host)
        delay = self.interval - (time.monotonic() - self.last_fetch.get(host, 0))
        if delay > 0:
            await asyncio.sleep(delay)
        self.last_fetch[host] = time.monotonic()
        async with httpx.AsyncClient(timeout=20, follow_redirects=False, trust_env=False, transport=self.transport, headers={'User-Agent':USER_AGENT}) as client:
            async with client.stream('GET', url) as response:
                if response.status_code in (401, 403, 429):
                    self.stopped_hosts.add(host)
                    raise AccessBlocked(f'Host stopped: HTTP {response.status_code}')
                if response.status_code in (301, 302, 303, 307, 308):
                    raise AccessBlocked('Redirect requires source review; not followed')
                response.raise_for_status()
                content_type = response.headers.get('content-type', '')
                if not any(t in content_type for t in ('text/html', 'text/plain', 'application/xml', 'text/xml')):
                    raise AccessBlocked('Unsupported document type')
                body = bytearray()
                async for chunk in response.aiter_bytes():
                    body.extend(chunk)
                    if len(body) > 2_000_000:
                        raise AccessBlocked('Document exceeds 2 MB limit')
                return body.decode('utf-8', errors='replace')

    async def fetch(self, url):
        url = validate_url(url, self.allowed_hosts)
        host = urlsplit(url).hostname
        if host not in self.robots:
            self.robots[host] = await self._request(f'https://{host}/robots.txt')
        allowed, delay = robots_allowed(self.robots[host], url)
        if not allowed:
            raise AccessBlocked('Robots disallows URL')
        self.interval = max(self.interval, delay)
        html = await self._request(url)
        if re.search(r'<title>[^<]*(?:captcha|just a moment|access denied)', html, re.I):
            self.stopped_hosts.add(host)
            raise AccessBlocked('Access challenge; no bypass attempted')
        return html
