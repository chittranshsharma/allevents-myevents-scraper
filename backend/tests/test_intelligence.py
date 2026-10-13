from decimal import Decimal
import pytest
from app.intelligence import money, calculate, utc_date, extract_promotions
from app.extraction import parse_page
from app.schemas import VerificationRequest


@pytest.mark.parametrize('value,expected',[('499',Decimal('499.00')),('1,234.555',Decimal('1234.56')),('NaN',None),('Infinity',None),('-1',None),('free',None),(None,None)])
def test_money(value,expected):assert money(value)==expected


def test_full_discount_unknown_fees():assert calculate(Decimal('499'),'percentage',Decimal(100))==(Decimal('499.00'),Decimal('0.00'),None)
def test_decimal_rounding():assert calculate(Decimal('499.99'),'percentage',Decimal(15),Decimal('20.00'))==(Decimal('75.00'),Decimal('424.99'),Decimal('444.99'))
def test_fixed_cap():assert calculate(Decimal('99'),'fixed',Decimal('200'),Decimal(0))==(Decimal('99.00'),Decimal('0.00'),Decimal('0.00'))
def test_bad_percent():
    with pytest.raises(ValueError):calculate(Decimal('5'),'percentage',Decimal('101'))
def test_timezone():assert utc_date('2027-01-01T18:00:00+05:30').isoformat()=='2027-01-01T12:30:00+00:00'
def test_unknown_timezone():assert utc_date('2027-01-01T18:00:00') is None


def test_public_not_verified():
    p=extract_promotions('Use code PUBLICFREE for 100% off tickets.',True)[0]
    assert p['verification_status']=='PUBLICLY ADVERTISED FULL DISCOUNT'
    assert p['coupon_code']=='PUBLICFREE'


def test_untrusted_offer():assert extract_promotions('Use code PUBLICFREE for free admission.',False)[0]['verification_status']=='POSSIBLE FULL DISCOUNT'
def test_free_event_not_coupon():assert extract_promotions('Free tickets available!')==[]
def test_no_guessing():assert extract_promotions('Use code below for free admission.')==[]
def test_identity_codes_excluded():
    assert extract_promotions('Coupon code alice@example.org for 100% off.')==[]
    assert extract_promotions('Coupon code 9876543210 for 100% off.')==[]
def test_full_offer_without_code():assert extract_promotions('Get 100% off eligible tickets today.',True)[0]['coupon_code'] is None
def test_negated_full_offer():assert extract_promotions('Use code SAMPLE, not 100% off.',True)[0]['discount_value'] is None
def test_unrelated_sentence():assert extract_promotions('Use code MAYBE. Other tickets are 100% off.',True)[0]['discount_value'] is None
def test_partial_advertised_unverified():assert extract_promotions('Coupon code SAVE20 for 20% off.',True)[0]['verification_status']=='UNVERIFIED CODE'
def test_explicit_expiration():assert extract_promotions('Coupon code FREEPASS for 100% off, expires 2027-01-01T10:00:00Z.',True)[0]['expiration_at'] is not None


def test_structured_event(fixture_html):
    events,_,_=parse_page(fixture_html,'https://www.mepass.in/events/test-fixture')
    assert len(events)==1 and events[0]['original_ticket_price']==Decimal('499')
    assert events[0]['location']=='Test Hall, Fixture City'


def test_duplicate_jsonld(fixture_html):assert len(parse_page(fixture_html+fixture_html,'https://www.mepass.in/events/test-fixture')[0])==1
def test_event_subtype(fixture_html):assert len(parse_page(fixture_html.replace('"@type": "Event"','"@type": "Festival"'),'https://www.mepass.in/events/test-fixture')[0])==1
def test_invalid_jsonld():assert parse_page('<script type="application/ld+json">garbage</script>','https://www.mepass.in/events/bad')[0]==[]
def test_public_cannot_confirm():
    with pytest.raises(ValueError):VerificationRequest(status='CONFIRMED FULL DISCOUNT',method='public_evidence',evidence_url='https://example.org/proof',note='Fixture evidence test only.',authorized=True,eligible_original_price=499,measured_remaining_price=0)
