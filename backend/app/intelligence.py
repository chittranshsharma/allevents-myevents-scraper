import re
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from datetime import datetime, timezone

STATUSES = ['CONFIRMED FULL DISCOUNT', 'PUBLICLY ADVERTISED FULL DISCOUNT', 'POSSIBLE FULL DISCOUNT', 'VERIFIED PARTIAL DISCOUNT', 'UNVERIFIED CODE', 'EXPIRED', 'INELIGIBLE', 'UNKNOWN']
FULL_STATUSES = STATUSES[:3]


def money(value):
    if value is None:
        return None
    try:
        n = Decimal(str(value).replace(',', '').strip())
        return n.quantize(Decimal('.01'), rounding=ROUND_HALF_UP) if n.is_finite() and 0 <= n < Decimal('100000000000') else None
    except (InvalidOperation, ValueError):
        return None


def utc_date(value):
    if not value:
        return None
    try:
        d = datetime.fromisoformat(value.rstrip('.').replace('Z', '+00:00'))
        # Unknown local time zones must not be invented.
        return d.astimezone(timezone.utc) if d.tzinfo else None
    except (ValueError, AttributeError):
        return None


def calculate(price, kind, value, fees=None):
    if price is None or value is None or kind not in ('percentage', 'fixed'):
        return None, None, None
    price, value = Decimal(price), Decimal(value)
    if price < 0 or value < 0 or (kind == 'percentage' and value > 100):
        raise ValueError('Invalid discount')
    discount = min(price, price * value / 100 if kind == 'percentage' else value).quantize(Decimal('.01'), rounding=ROUND_HALF_UP)
    remaining = price - discount
    return discount, remaining, remaining + Decimal(fees) if fees is not None else None


def extract_promotions(text, official=False):
    """Extract explicit codes while allowing an offer label and code label on adjacent lines."""
    candidates = []
    raw_lines = [line.strip() for line in re.split(r'[\n\r]+', text) if line.strip()]
    code_hint = re.compile(r'\b(?:promo(?:tion)?\s+code|coupon(?:\s+code)?|use\s+(?:the\s+)?code)\b', re.I)
    offer_hint = re.compile(r'(?:\d{1,3}(?:\.\d+)?\s*%|(?:₹|INR\s*)[\d,]+|free|complimentary).{0,35}(?:off|discount|ticket|admission)', re.I)
    lines = []
    i = 0
    while i < len(raw_lines):
        line = raw_lines[i]
        if code_hint.search(line) and not offer_hint.search(line):
            if i + 1 < len(raw_lines) and offer_hint.search(raw_lines[i + 1]):
                line = f'{line} {raw_lines[i + 1]}'; i += 1
            elif lines and offer_hint.search(lines[-1]):
                line = f'{lines.pop()} {line}'
        lines.append(line)
        i += 1
    sentences = []
    for line in lines:
        sentences.extend(re.split(r'(?<=[.!?])\s+', line))
    for sentence in sentences:
        if len(sentence) > 1500:
            continue
        code = re.search(r'\b(?:promo(?:tion)?\s+code|coupon(?:\s+code)?|use\s+(?:the\s+)?code)\s*[:=\-]?\s*[\"\x27`]?([A-Za-z0-9][A-Za-z0-9_-]{2,49})\b', sentence, re.I)
        value = code.group(1) if code else None
        if code and (sentence[code.end():].startswith('@') or (value.isdigit() and len(value) >= 7)):
            continue
        if value and value.lower() in {'here', 'below', 'available', 'required', 'your', 'this', 'with', 'for', 'code', 'coupon', 'discount', 'at', 'the'}:
            continue
        percent = re.search(r'(?<![\d.])(100|\d{1,2})(?:\.0+)?\s*%\s*(?:off|discount)', sentence, re.I)
        fixed = re.search(r'(?:₹|INR\s*)([\d,]+(?:\.\d{1,2})?)\s*(?:off|discount)', sentence, re.I)
        full = bool(percent and percent.group(1) == '100') or bool(re.search(r'\b(?:free admission|complimentary tickets?|free (?:ticket|pass)|fully discounted)\b', sentence, re.I))
        if not code and not (percent and percent.group(1) == '100'):
            continue
        negated = bool(re.search(r'\b(?:not|no|never|isn[\x27’]t)\b.{0,35}(?:free|100\s*%)', sentence, re.I))
        kind = 'percentage' if percent or (full and not negated) else 'fixed' if fixed else None
        amount = Decimal(100) if full and not negated else Decimal(percent.group(1)) if percent else money(fixed.group(1)) if fixed else None
        if negated:
            kind, amount = None, None
        status = ('PUBLICLY ADVERTISED FULL DISCOUNT' if official else 'POSSIBLE FULL DISCOUNT') if full and not negated else 'UNVERIFIED CODE'
        expiration = re.search(r'(?:expires?|valid until|ends?)\s*:?\s*(\d{4}-\d{2}-\d{2}T[\d:+Z.-]+)', sentence, re.I)
        candidates.append(dict(coupon_code=value, discount_type=kind, discount_value=amount, verification_status=status, confidence='medium' if official and amount is not None else 'low', eligibility=sentence[:1000], expiration_at=utc_date(expiration.group(1)) if expiration else None, excerpt=sentence[:1500]))
    return candidates
