from decimal import Decimal
from datetime import datetime
from sqlalchemy import String, Text, ForeignKey, Numeric, DateTime, UniqueConstraint, JSON, Boolean, Integer
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.orm import DeclarativeBase
from app.db import utcnow
class Base(DeclarativeBase):
    pass


class Platform(Base):
    __tablename__ = 'platforms'
    id: Mapped[str] = mapped_column(String(20), primary_key=True)
    domain: Mapped[str] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(40))
    reason: Mapped[str] = mapped_column(Text)


class Organizer(Base):
    __tablename__ = 'organizers'
    id: Mapped[int] = mapped_column(primary_key=True)
    platform: Mapped[str] = mapped_column(ForeignKey('platforms.id'))
    name: Mapped[str] = mapped_column(String(300))
    __table_args__ = (UniqueConstraint('platform', 'name'),)


class Event(Base):
    __tablename__ = 'events'
    id: Mapped[int] = mapped_column(primary_key=True)
    platform: Mapped[str] = mapped_column(ForeignKey('platforms.id'), index=True)
    organizer_id: Mapped[int | None] = mapped_column(ForeignKey('organizers.id'))
    name: Mapped[str] = mapped_column(String(500), index=True)
    url: Mapped[str] = mapped_column(String(1000), unique=True)
    date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    location: Mapped[str | None] = mapped_column(String(500))
    description: Mapped[str] = mapped_column(Text, default='')
    original_ticket_price: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    currency: Mapped[str | None] = mapped_column(String(10))
    last_checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    extraction_method: Mapped[str] = mapped_column(String(80), default='json-ld')
    provenance: Mapped[dict] = mapped_column(JSON, default=dict)


class TicketCategory(Base):
    __tablename__ = 'ticket_categories'
    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey('events.id'), index=True)
    name: Mapped[str] = mapped_column(String(300))
    price: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    currency: Mapped[str | None] = mapped_column(String(10))
    __table_args__ = (UniqueConstraint('event_id', 'name'),)


class CrawlSource(Base):
    __tablename__ = 'crawl_sources'
    id: Mapped[int] = mapped_column(primary_key=True)
    url: Mapped[str] = mapped_column(String(1000), unique=True)
    platform: Mapped[str] = mapped_column(ForeignKey('platforms.id'))
    source_type: Mapped[str] = mapped_column(String(40))
    permission_basis: Mapped[str] = mapped_column(Text)
    terms_url: Mapped[str] = mapped_column(String(1000))
    event_id: Mapped[int | None] = mapped_column(ForeignKey('events.id'))
    official: Mapped[bool] = mapped_column(Boolean, default=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)


class CrawlJob(Base):
    __tablename__ = 'crawl_jobs'
    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(40), default='discovery')
    # A nullable unique slot permits historical jobs, and only one active job.
    active_slot: Mapped[str | None] = mapped_column(String(30), unique=True)
    status: Mapped[str] = mapped_column(String(30), default='queued', index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    pages_processed: Mapped[int] = mapped_column(default=0)
    events_found: Mapped[int] = mapped_column(default=0)
    promotions_found: Mapped[int] = mapped_column(default=0)
    error_count: Mapped[int] = mapped_column(default=0)
    message: Mapped[str] = mapped_column(Text, default='')
    max_pages: Mapped[int] = mapped_column(default=10)
    max_depth: Mapped[int] = mapped_column(default=1)


class CrawlResult(Base):
    __tablename__ = 'crawl_results'
    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey('crawl_jobs.id'), index=True)
    source_id: Mapped[int] = mapped_column(ForeignKey('crawl_sources.id'))
    url: Mapped[str] = mapped_column(String(1000))
    source_type: Mapped[str] = mapped_column(String(40))
    discovery_depth: Mapped[int] = mapped_column(default=0)
    priority: Mapped[int] = mapped_column(default=0)
    discovered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    fetch_status: Mapped[str] = mapped_column(String(40), default='queued', index=True)
    content_hash: Mapped[str | None] = mapped_column(String(64))
    attempts: Mapped[int] = mapped_column(default=0)
    error: Mapped[str | None] = mapped_column(Text)
    __table_args__ = (UniqueConstraint('job_id', 'url'),)


class Promotion(Base):
    __tablename__ = 'promotion_candidates'
    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey('events.id'), index=True)
    platform: Mapped[str] = mapped_column(ForeignKey('platforms.id'), index=True)
    fingerprint: Mapped[str] = mapped_column(String(64), unique=True)
    coupon_code: Mapped[str | None] = mapped_column(String(100), index=True)
    discount_type: Mapped[str | None] = mapped_column(String(30))
    discount_value: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    expiration_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    eligibility: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[str] = mapped_column(String(30), default='low')
    verification_method: Mapped[str] = mapped_column(String(50), default='public_evidence')
    verification_status: Mapped[str] = mapped_column(String(80), index=True)
    discovered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    remaining_ticket_price: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    eligible_discount_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    mandatory_fees: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    estimated_final_price: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))


class Evidence(Base):
    __tablename__ = 'promotion_evidence'
    id: Mapped[int] = mapped_column(primary_key=True)
    promotion_id: Mapped[int] = mapped_column(ForeignKey('promotion_candidates.id'), index=True)
    source_url: Mapped[str] = mapped_column(String(1000))
    excerpt: Mapped[str] = mapped_column(Text)
    document_type: Mapped[str] = mapped_column(String(50), default='html')
    extraction_method: Mapped[str] = mapped_column(String(50), default='explicit-pattern')
    parser_version: Mapped[str] = mapped_column(String(20), default='1.0')
    official: Mapped[bool] = mapped_column(Boolean, default=False)
    extracted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    __table_args__ = (UniqueConstraint('promotion_id', 'source_url', 'excerpt'),)


class Verification(Base):
    __tablename__ = 'verification_history'
    id: Mapped[int] = mapped_column(primary_key=True)
    promotion_id: Mapped[int] = mapped_column(ForeignKey('promotion_candidates.id'), index=True)
    previous_status: Mapped[str] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(80))
    method: Mapped[str] = mapped_column(String(80))
    evidence_url: Mapped[str] = mapped_column(String(1000))
    note: Mapped[str] = mapped_column(Text)
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Watchlist(Base):
    __tablename__ = 'watchlists'
    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(30))
    value: Mapped[str] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    __table_args__ = (UniqueConstraint('kind', 'value'),)


class Notification(Base):
    __tablename__ = 'notifications'
    id: Mapped[int] = mapped_column(primary_key=True)
    dedup_key: Mapped[str] = mapped_column(String(200), unique=True)
    promotion_id: Mapped[int] = mapped_column(ForeignKey('promotion_candidates.id'))
    title: Mapped[str] = mapped_column(String(500))
    message: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    telegram_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    telegram_attempts: Mapped[int] = mapped_column(Integer, default=0)
    telegram_error: Mapped[str | None] = mapped_column(String(100))


class SystemLog(Base):
    __tablename__ = 'system_logs'
    id: Mapped[int] = mapped_column(primary_key=True)
    level: Mapped[str] = mapped_column(String(20))
    message: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

metadata = Base.metadata
