# Database schema

`platforms` establishes the two supported platforms. `organizers` has unique platform/name pairs. `events` has unique canonical URL, platform/organizer foreign keys, nullable price/date/location, extraction provenance and last-check time. `ticket_categories` stores published offers with unique event/name pairs.

`crawl_sources` stores permission basis and reviewed seed configuration. `crawl_jobs` stores state, lease/heartbeat, counters and page/depth budgets. Its unique nullable `active_slot` permits one active job. `crawl_results` is the persistent frontier, unique per job/URL, including attempts, hashes and parser version.

`promotion_candidates` is the canonical promotion table: code, discount, eligibility, status, monetary estimates, timestamps and a unique evidence/event fingerprint. A separate duplicated promotions table is unnecessary. `promotion_evidence` stores source URL, excerpt, authority assertion, extraction method/version and timestamp. `verification_history` stores every transition and authorized monetary measurements. Evidence is not replaced by reviews.

`watchlists` has unique kind/value pairs. `notifications` has a unique finding/status/value/expiry dedup key and Telegram delivery state. `system_logs` is available for operator records; routine API/worker logs use process output. Users are not collected: the MVP uses a single environment token, avoiding unnecessary personal records.

Alembic revisions: 001 frozen initial metadata; 002 monetary verification audit fields; 003 extraction cache parser version. Tests initialize isolated schemas, and a separate migration roundtrip test checks all revisions. SQLite foreign keys and busy timeout are enabled. Monetary fields use Numeric(14,2); event/status/timestamp lookup indexes and explicit uniqueness constrain duplication.

Source evidence persists until operator cleanup. Use `scripts/maintenance.py` to delete old terminal crawl jobs/results while preserving events, candidates and evidence. No automatic evidence deletion is performed.
