from decimal import Decimal
from typing import Literal
from pydantic import BaseModel, Field, field_validator, model_validator
from .security import normalize_url
from .intelligence import STATUSES


class JobRequest(BaseModel):
    max_pages: int = Field(default=10, ge=1, le=30)
    max_depth: int = Field(default=1, ge=0, le=2)
    kind: Literal['discovery','event_refresh','promotion_refresh','source_health'] = 'discovery'


class WatchRequest(BaseModel):
    kind: Literal['event','organizer','city','full_discount','keyword']
    value: str = Field(min_length=1, max_length=200)

    @field_validator('value')
    @classmethod
    def nonempty(cls, value):
        if not value.strip(): raise ValueError('Value is required')
        return value.strip()


class Submission(BaseModel):
    platform: Literal['allevents','mepass']
    event_url: str
    html: str = Field(min_length=20, max_length=80000)
    permission_note: str = Field(min_length=15, max_length=1000)
    organizer_authorized: Literal[True]

    @field_validator('event_url')
    @classmethod
    def validate_link(cls, v):
        return normalize_url(v)

    @model_validator(mode='after')
    def platform_matches(self):
        from urllib.parse import urlsplit
        allowed = {'allevents':{'allevents.in','www.allevents.in'}, 'mepass':{'mepass.in','www.mepass.in'}}
        if urlsplit(self.event_url).hostname not in allowed[self.platform]:
            raise ValueError('Event URL must belong to the selected platform')
        return self


class VerificationRequest(BaseModel):
    status: str
    method: Literal['manual_authorized','official_documented_api','public_evidence']
    evidence_url: str
    note: str = Field(min_length=20, max_length=2000)
    authorized: Literal[True]
    eligible_original_price: Decimal | None = Field(default=None, gt=0, max_digits=14, decimal_places=2)
    measured_remaining_price: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    mandatory_fees: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)

    @field_validator('status')
    @classmethod
    def valid_status(cls, v):
        if v not in STATUSES: raise ValueError('Unsupported status')
        return v

    @field_validator('evidence_url')
    @classmethod
    def valid_url(cls, v):
        return normalize_url(v)

    @model_validator(mode='after')
    def check_measurement(self):
        if (self.eligible_original_price is None) != (self.measured_remaining_price is None):
            raise ValueError('Provide both original and measured remaining prices, or neither')
        if self.eligible_original_price is not None and self.measured_remaining_price > self.eligible_original_price:
            raise ValueError('Remaining subtotal cannot exceed the original eligible price')
        if self.status in ('CONFIRMED FULL DISCOUNT','VERIFIED PARTIAL DISCOUNT'):
            if self.method == 'public_evidence' or self.eligible_original_price is None or self.measured_remaining_price is None:
                raise ValueError('Confirmation requires an authorized measured eligible ticket price and remaining subtotal')
            if self.status == 'CONFIRMED FULL DISCOUNT' and self.measured_remaining_price != 0:
                raise ValueError('Full discount requires zero remaining subtotal')
            if self.status == 'VERIFIED PARTIAL DISCOUNT' and not 0 < self.measured_remaining_price < self.eligible_original_price:
                raise ValueError('Partial discount requires a positive reduction and a positive remaining subtotal')
        return self
