# Testing report

Executed on 13 October 2026, Windows, Python 3.14.8, Node 24.21.0, Next.js 16.4.0.

| Command/check | Observed outcome |
|---|---|
| `backend/.venv/Scripts/python.exe -m pytest -q` (from backend use `.venv/...`) | 62 tests passed; one Starlette/HTTPX deprecation warning |
| `npm.cmd run build` in frontend | Successful optimized Next.js build with TypeScript checks |
| `npm.cmd run typecheck` in frontend | Successful `tsc --noEmit` |
| `python scripts/run_e2e.py` | 3 Chromium browser tests passed against isolated test database and servers |
| Alembic upgrade/downgrade roundtrip | Automated test passed on disposable SQLite database |
| Alembic PostgreSQL `upgrade head --sql` | SQL generation succeeded; no PostgreSQL connection tested |
| Implemented live HTTP crawler | Final 10-page Mepass scan completed; 9 real records; zero coupon candidates; zero final-scan errors |
| Opt-in AllEvents direct scan | 10-page job #8 completed with no errors; 131 unique AllEvents records from three public Bangalore listing pages, with event detail pages fetched alongside Mepass; zero coupon candidates |

Backend tests cover decimal money/rounding, fixed discount caps, unknown fees, timezone handling, event subtype parsing and deduplication, explicit coupon evidence, identity-code exclusion, negation, expiry, public-vs-confirmed statuses, authentication, request limits, event ingestion, API filters, persistence, notification deduplication, review history, migration roundtrips, frontier processing, source failure and stale lease recovery. Network fixtures are labeled tests; no mock data is seeded into production.

Browser tests cover API-connected dashboard/platform limits, empty filtered results, organizer-provided fixture import, displayed price and evidence, adding a watch, measured administrator review, in-app alert rendering, and mobile viewport width. The mocked worker integration test covers listing → event → promotion → stored evidence → notification; the live worker check establishes that the real public-source pipeline operates. The browser import flow deliberately avoids real checkout or redemption.

An additional browser check opened the real completed job #3 and displayed its ten source outcomes. A desktop screenshot was visually inspected; the page rendered nine real records (six recent cards on the overview), and the browser reported no JavaScript page errors. No fixtures appeared in that normal workspace.

Reproducible failures fixed: punctuation in expiry parsing; inconsistent decimal serialization; accessible navigation names containing decorative symbols; ambiguous test locators; Festival event subtypes. A temporary test-server startup path error was corrected. UTC serialization was hardened for SQLite timestamps. A dedicated E2E harness now prevents fixture insertion into the normal database.

Not run: Docker/real PostgreSQL deployment, Telegram live delivery, AllEvents API, authorized platform coupon validation, social integrations or automated public-page browser rendering. No credential or checkout claim is made. Evidence absence means precision and verification coverage cannot be established from live promotions.
