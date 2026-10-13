# EventPass

EventPass is a local event-discovery and promotion-evidence workspace. It collects public event pages from Mepass and, when explicitly enabled, AllEvents, then stores event details, promotion candidates, source excerpts, review history, watchlists, and alerts in one searchable dashboard.

The project is designed for personal use and free operation. It does not require Apify, paid proxies, a paid API, or a hosted service.

## What it does

- Discovers event listings and event detail pages with a bounded, persistent worker queue.
- Extracts event names, dates, venues, organizers, ticket prices, and structured metadata.
- Finds promotion evidence only when a page contains an explicit code or discount statement.
- Preserves the source URL, excerpt, parser method, timestamp, and content hash for each result.
- Separates advertised discounts from administrator-confirmed checkout measurements.
- Supports event, city, keyword, organizer, and full-discount watchlists with in-app notifications.
- Provides a Next.js dashboard and a FastAPI JSON API.
- Runs with SQLite locally or PostgreSQL through Docker Compose.

## What it does not do

EventPass does not guess coupon codes, enumerate private coupons, bypass authentication or anti-bot controls, probe undocumented checkout endpoints, issue tickets, or redeem invitations. A “100% off” finding means the eligible ticket subtotal may be zero; fees, eligibility, availability, and platform rules can still affect the final amount.

AllEvents collection is disabled by default. Enable it only when you have permission to collect the pages for your use case. The free connector uses ordinary public HTML, robots checks, a three-second minimum host interval, and bounded page budgets. It does not use an Apify actor or proxy service.

## Stack

- **Frontend:** Next.js, React, TypeScript, Tailwind CSS
- **Backend:** FastAPI, SQLAlchemy, Alembic, Python
- **Storage:** SQLite for local use; PostgreSQL for Compose deployments
- **Extraction:** Schema.org JSON-LD plus conservative visible-text patterns
- **Notifications:** In-app alerts; optional Telegram delivery

## Quick start on Windows

From the repository root, create the Python environment, install dependencies, generate local credentials, and migrate the database:

```powershell
python -m venv backend/.venv
backend/.venv/Scripts/python.exe -m pip install -r backend/requirements.lock
npm.cmd ci --prefix frontend
python scripts/configure_local.py
cd backend
.venv/Scripts/python.exe -m alembic upgrade head
```

Start the API in one terminal:

```powershell
cd backend
.venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Start the worker in a second terminal:

```powershell
cd backend
.venv/Scripts/python.exe -m app.crawler
```

Start the dashboard in a third terminal:

```powershell
cd frontend
npm.cmd run dev
```

Open [the dashboard](http://localhost:3000) and [the API docs](http://127.0.0.1:8000/docs). Copy `ADMIN_TOKEN` from `backend/.env` into the dashboard before starting a discovery job.

The default scan uses the reviewed Mepass Bengaluru listing. To include the first three public AllEvents Bangalore listing pages, set this in `backend/.env` and restart both the API and worker:

```dotenv
ALLEVENTS_AUTHORIZED=true
```

To queue a scan without using the dashboard:

```powershell
cd backend
.venv/Scripts/python.exe ../scripts/start_discovery.py --pages 10
```

For Linux or macOS, replace `Scripts/python.exe` with `bin/python` and `npm.cmd` with `npm`.

## Configuration

Copy the available settings from [backend/.env.example](backend/.env.example). The important values are:

| Setting | Purpose |
| --- | --- |
| `DATABASE_URL` | SQLite or PostgreSQL connection string |
| `ADMIN_TOKEN` | Protects mutations, watchlists, reviews, and notifications |
| `ALLEVENTS_AUTHORIZED` | Enables the direct AllEvents connector when `true` |
| `SCHEDULE_MINUTES` | Enables recurring scans; `0` keeps scheduling off |
| `REQUEST_INTERVAL_SECONDS` | Minimum request spacing, never below the safe built-in floor |
| `SOURCE_CONFIG` | Optional JSON file containing reviewed additional sources |
| `TELEGRAM_ENABLED` | Enables optional Telegram delivery when credentials are set |

The frontend reads `BACKEND_URL` at build time when the API is not at its default address.

## Docker Compose

Copy the root environment template, replace the two credential placeholders, and start the stack:

```powershell
Copy-Item .env.example .env
docker compose up --build
```

The API, worker, frontend, and PostgreSQL containers bind to loopback addresses. Set `ALLEVENTS_AUTHORIZED=true` in the root `.env` if the authorized AllEvents connector should run in Compose.

## Tests and checks

Backend unit and integration tests:

```powershell
cd backend
.venv/Scripts/python.exe -m pytest -q
```

Frontend type checking and production build:

```powershell
cd frontend
npm.cmd run typecheck
npm.cmd run build
```

Browser tests use an isolated temporary database and local servers:

```powershell
cd ..
npm.cmd exec --prefix frontend -- playwright install chromium
python scripts/run_e2e.py
```

The live smoke check has successfully fetched public Mepass and authorized AllEvents pages. It produced event records with zero network errors; it did not produce a real coupon candidate or perform checkout validation.

## Evidence statuses

- **Confirmed full discount:** an administrator recorded an authorized measurement.
- **Publicly advertised full discount:** an official source explicitly advertises the reduction; current redemption is unconfirmed.
- **Possible full discount:** incomplete or submitted evidence needs review.
- **Verified partial discount:** an administrator recorded an authorized partial-discount measurement.
- **Unverified code:** a code was published, but its discount or eligibility is not established.
- **Expired, ineligible, or unknown:** the corresponding evidence state is recorded without guessing.

## Repository map

```text
backend/app/        API, crawler, extraction, models, security, services
backend/migrations/ Database migrations
backend/tests/      Backend and worker tests
frontend/app/       Dashboard UI
frontend/tests/     Browser tests
docs/               Architecture, research, limitations, and test reports
scripts/            Local setup, discovery, maintenance, and E2E helpers
```

Useful references:

- [Setup notes](docs/setup.md)
- [Discovery methodology](docs/discovery-methodology.md)
- [Platform research](docs/platform-research.md)
- [Technical feasibility](docs/technical-feasibility.md)
- [Known issues](docs/known-issues.md)
- [API reference](docs/api-reference.md)
- [Testing report](docs/testing-report.md)

## Current limitations

Coverage is bounded by the configured page budget and the public information each platform exposes. Structured event data may omit dates, ticket categories, venues, or the actual organizer. Coupon discovery is evidence-based and intentionally conservative; private, identity-linked, or server-side-only promotions remain outside the system. PostgreSQL deployment, Telegram delivery, and real checkout verification require separate operational testing.

## License and personal-use note

This repository is a personal-use project. Before enabling a source, review its current terms, robots policy, and any permission you rely on. Keep credentials in ignored `.env` files and never commit them.
