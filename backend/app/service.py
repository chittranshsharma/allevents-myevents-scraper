import hashlib
from sqlalchemy import select
from .db import utcnow
from .models import Event, Organizer, TicketCategory, Promotion, Evidence, Watchlist, Notification, Verification
from .intelligence import extract_promotions, calculate, FULL_STATUSES


def save_event(db, record, platform):
    data = record.copy()
    organizer_name, tickets = data.pop('organizer', None), data.pop('tickets', [])
    organizer_id = None
    if organizer_name:
        organizer = db.scalar(select(Organizer).where(Organizer.platform == platform, Organizer.name == organizer_name))
        if not organizer:
            organizer = Organizer(platform=platform, name=organizer_name); db.add(organizer); db.flush()
        organizer_id = organizer.id
    event = db.scalar(select(Event).where(Event.url == data['url']))
    if not event:
        event = Event(platform=platform, **data); db.add(event)
    else:
        for key, value in data.items():
            setattr(event, key, value)
    event.organizer_id, event.last_checked_at = organizer_id, utcnow()
    db.flush()
    for ticket in tickets:
        existing = db.scalar(select(TicketCategory).where(TicketCategory.event_id == event.id, TicketCategory.name == ticket['name']))
        if existing:
            existing.price, existing.currency = ticket['price'], ticket['currency']
        else:
            db.add(TicketCategory(event_id=event.id, **ticket))
    return event


def notify(db, promotion, event):
    watched = False
    organizer = db.get(Organizer, event.organizer_id) if event.organizer_id else None
    for watch in db.scalars(select(Watchlist)):
        watched |= (watch.kind == 'event' and watch.value == str(event.id)) or (watch.kind == 'city' and watch.value.lower() in (event.location or '').lower()) or (watch.kind == 'keyword' and watch.value.lower() in (event.name + ' ' + event.description).lower()) or (watch.kind == 'organizer' and organizer and watch.value.lower() == organizer.name.lower()) or (watch.kind == 'full_discount' and promotion.verification_status in FULL_STATUSES)
    if not watched:
        return
    key = f'{promotion.id}:{promotion.verification_status}:{promotion.discount_value}:{promotion.expiration_at}'
    if db.scalar(select(Notification).where(Notification.dedup_key == key)):
        return
    db.add(Notification(dedup_key=key, promotion_id=promotion.id, title=f'{event.name}: {promotion.verification_status}', message=f'Public code {promotion.coupon_code or "unknown"}. Fees and eligibility may apply. Open evidence before booking.'))


def save_promotions(db, event, text, source_url, official=False, method='explicit-pattern'):
    count = 0
    for record in extract_promotions(text, official):
        excerpt = record.pop('excerpt')
        fingerprint = hashlib.sha256(f'{event.id}:{record["coupon_code"]}:{source_url}:{excerpt}'.encode()).hexdigest()
        promotion = db.scalar(select(Promotion).where(Promotion.fingerprint == fingerprint))
        if not promotion:
            promotion = Promotion(event_id=event.id, platform=event.platform, fingerprint=fingerprint, **record)
            db.add(promotion); db.flush(); count += 1
            db.add(Evidence(promotion_id=promotion.id, source_url=source_url, excerpt=excerpt, official=official, extraction_method=method))
        promotion.last_checked_at = utcnow()
        # Authorized measured values survive subsequent public-source refreshes.
        if promotion.verification_status not in ('CONFIRMED FULL DISCOUNT','VERIFIED PARTIAL DISCOUNT'):
            compatible = promotion.discount_type != 'fixed' or event.currency == 'INR'
            discount, remaining, final = calculate(event.original_ticket_price if compatible else None, promotion.discount_type, promotion.discount_value, promotion.mandatory_fees)
            promotion.eligible_discount_amount, promotion.remaining_ticket_price, promotion.estimated_final_price = discount, remaining, final
        notify(db, promotion, event)
    return count


def expire_promotions(db):
    for promotion in db.scalars(select(Promotion).where(Promotion.expiration_at <= utcnow(), Promotion.verification_status != 'EXPIRED')):
        previous = promotion.verification_status
        promotion.verification_status = 'EXPIRED'
        promotion.last_checked_at = utcnow()
        db.add(Verification(promotion_id=promotion.id, previous_status=previous, status='EXPIRED', method='documented_expiration', evidence_url=db.scalar(select(Evidence.source_url).where(Evidence.promotion_id == promotion.id)) or db.get(Event, promotion.event_id).url, note='Recorded explicit expiry has elapsed.'))
        notify(db, promotion, db.get(Event, promotion.event_id))
    db.commit()
