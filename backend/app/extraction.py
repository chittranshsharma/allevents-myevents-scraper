import json
import re
from bs4 import BeautifulSoup
from .intelligence import money, utc_date

EVENT_TYPES = {'Event','BusinessEvent','ChildrensEvent','ComedyEvent','CourseInstance','DanceEvent','DeliveryEvent','EducationEvent','ExhibitionEvent','Festival','FoodEvent','Hackathon','LiteraryEvent','MusicEvent','PublicationEvent','SaleEvent','ScreeningEvent','SocialEvent','SportsEvent','TheaterEvent','VisualArtsEvent'}


def structured_nodes(value):
    if isinstance(value, list):
        for item in value:
            yield from structured_nodes(item)
    elif isinstance(value, dict):
        yield value
        if '@graph' in value:
            yield from structured_nodes(value['@graph'])


def parse_page(html, url, use_node_urls=False):
    soup = BeautifulSoup(html, 'html.parser')
    events = []
    for script in soup.select('script[type="application/ld+json"]'):
        try:
            nodes = structured_nodes(json.loads(script.string or script.get_text()))
            for node in nodes:
                typ = node.get('@type', [])
                types = set(typ) if isinstance(typ,list) else {typ}
                if not types.intersection(EVENT_TYPES) or not node.get('name'):
                    continue
                offers = node.get('offers', [])
                offers = offers if isinstance(offers, list) else [offers]
                tickets = [dict(name=str(o.get('name') or 'Published offer')[:300], price=money(o.get('price', o.get('lowPrice'))), currency=o.get('priceCurrency')) for o in offers if isinstance(o, dict)]
                location = node.get('location') or {}
                location = location[0] if isinstance(location, list) and location else location
                address = location.get('address') or {} if isinstance(location, dict) else {}
                organizer = node.get('organizer') or {}
                organizer = organizer[0] if isinstance(organizer, list) and organizer else organizer
                description = BeautifulSoup(str(node.get('description', '')), 'html.parser').get_text(' ', strip=True)
                prices = [t['price'] for t in tickets if t['price'] is not None]
                currency = next((t['currency'] for t in tickets if t['currency']), None)
                event_url = node.get('url') if use_node_urls else url
                if not isinstance(event_url, str) or (use_node_urls and not event_url.startswith('https://allevents.in/')):
                    continue
                events.append(dict(name=str(node['name'])[:500], url=event_url, date=utc_date(node.get('startDate')), location=', '.join(str(x) for x in [location.get('name') if isinstance(location, dict) else location, address.get('addressLocality') if isinstance(address, dict) else address] if x and x != 'TBD') or None, organizer=str(organizer.get('name'))[:300] if isinstance(organizer, dict) and organizer.get('name') else None, description=description[:20000], original_ticket_price=min(prices) if prices and len({t['currency'] for t in tickets}) == 1 else None, currency=currency, tickets=tickets, provenance={'source_url':url,'document_type':'html','parser_version':'1.0','method':'json-ld','raw_start_date':node.get('startDate'),'excerpt':description[:1500]}))
        except (json.JSONDecodeError, TypeError, ValueError, AttributeError):
            continue
    # HTML price fallback is confined to explicit ticket-price/onwards text.
    text = soup.get_text(' ', strip=True)
    price = re.search(r'₹\s*([\d,]+(?:\.\d{1,2})?)\s*onwards', text, re.I)
    unique = {event['url']: event for event in events}
    for e in unique.values():
        if e['original_ticket_price'] is None and price:
            e['original_ticket_price'], e['currency'] = money(price.group(1)), 'INR'
            e['provenance']['price_method'] = 'visible-onwards-price'
            e['provenance']['price_excerpt'] = price.group(0)
    for tag in soup(['script', 'style', 'nav', 'footer', 'header']):
        tag.decompose()
    # Preserve block boundaries so unrelated offers are not one huge sentence.
    content = '\n'.join(dict.fromkeys(p.get_text(' ', strip=True) for p in soup.select('p,li,h1,h2,h3') if p.get_text(strip=True)))
    leaf_text = [p.get_text(' ', strip=True) for p in soup.select('div,span') if not p.find(['p','div','li','span']) and p.get_text(strip=True)]
    content += '\n' + '\n'.join(dict.fromkeys(leaf_text))
    links = [a.get('href') for a in soup.select('a[href]')]
    return list(unique.values()), content, links
