# EventPass

EventPass collects public event information for **Mepass** and keeps traceable promotion candidates. Personal AllEvents discovery can be enabled with the operator's direct authorization using `ALLEVENTS_AUTHORIZED=true`. It uses ordinary public HTML and no paid scraper service. Organizer-authorized document submissions can also be imported.

The application has a Next.js/TypeScript/Tailwind dashboard, FastAPI backend, SQLAlchemy database, Alembic migrations, a persistent single-worker queue, evidence review, watchlists and in-app alerts. PostgreSQL is the deployment database; SQLite makes local development possible without Docker. No sample coupons are installed in the normal database.

It cannot uncover private coupons, guess codes, confirm checkout validity through undocumented APIs, issue tickets, or redeem invitations. Publicly advertised 100% reductions concern the eligible ticket subtotal. Fees and eligibility can remain unknown.

## Local startup (PowerShell)

Requirements: Python 3.14, Node.js 24, npm. Run these from the repository root:

```powershell
python -m venv backend/.venv
backend/.venv/Scripts/python.exe -m pip install -r backend/requirements.lock
npm.cmd ci --prefix frontend
python scripts/configure_local.py
cd backend
.venv/Scripts/python.exe -m alembic upgrade head
.venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

In a second terminal, from the repository root:

```powershell
cd backend
.venv/Scripts/python.exe -m app.crawler
```

In a third terminal, from the repository root:

```powershell
cd frontend
npm.cmd run dev
```

Open [the dashboard](http://localhost:3000) and [API documentation](http://127.0.0.1:8000/docs). Open `backend/.env`, copy `ADMIN_TOKEN`, and enter it in the dashboard. Select **Start discovery**. The worker processes the queued job. Mepass has a default Bengaluru hub; with your local authorization flag, AllEvents adds its Bangalore public listing. Jobs default to 10 pages and one-level depth.

Alternatively, from `backend/`, run `.venv/Scripts/python.exe ../scripts/start_discovery.py --pages 10` to queue a scan and print its completed outcome. This calls the same protected API and requires the worker.

For Linux/macOS replace `Scripts/python.exe` with `bin/python` and `npm.cmd` with `npm`. Each Python service must run from `backend/` so its local `.env` and SQLite path resolve correctly.

## Configuration

`backend/.env.example` documents backend settings. `DATABASE_URL` supports PostgreSQL (`postgresql+psycopg://...`) or SQLite. `ADMIN_TOKEN` protects every mutation and private watch/notification reads. Reads of public event data are open. This is a single administrator workspace, not a multiuser service.

`SCHEDULE_MINUTES=0` disables scheduled scanning; a positive value enables worker-driven scans, with a 15-minute minimum. `ALLEVENTS_AUTHORIZED=true` enables a bounded public Bangalore listing and detail scan based on your reported permission; it makes no Apify calls and incurs no actor charges. `SOURCE_CONFIG` names a reviewed JSON source configuration file. See [discovery methodology](docs/discovery-methodology.md). `BACKEND_URL` is a frontend server variable; set it **before building** if the API address differs. Telegram delivery requires `TELEGRAM_ENABLED=true`, a bot token and a chat ID; enabling it authorizes sending configured watch alerts. It is disabled by default.

For Docker, copy root `.env.example` to `.env`, replace both credential placeholders with URL-safe random strings, then run:

```powershell
docker compose up --build
```

Compose initializes PostgreSQL, migrates the schema, and starts the API, worker and frontend. Docker/PostgreSQL execution was not available in this environment; see [testing report](docs/testing-report.md).

## Tests

```powershell
cd backend
.venv/Scripts/python.exe -m pytest -q
cd ../frontend
npm.cmd run build
```

Browser tests use a separate temporary database and servers on ports 8001/3001:

```powershell
cd ..
npm.cmd exec --prefix frontend -- playwright install chromium
python scripts/run_e2e.py
```

The harness marks its backend `APP_ENV=test`; fixture ingestion refuses a backend without that marker. It cleans up its owned processes and keeps test logs/databases under ignored `runtime/`. Tests never insert fixtures into the normal database.

## Interpretation

**CONFIRMED FULL DISCOUNT** requires administrator-recorded authorized measurements. **PUBLICLY ADVERTISED FULL DISCOUNT** means an official publication advertises a full reduction, with current redeemability unconfirmed. **POSSIBLE FULL DISCOUNT** means incomplete or submitted evidence. Partial advertised codes stay **UNVERIFIED CODE** until measured. Other statuses are **VERIFIED PARTIAL DISCOUNT**, **EXPIRED**, **INELIGIBLE**, and **UNKNOWN**. Reviews have an immutable history. No automatic checkout validation exists.

Research, actual findings, schema, limitations and startup details are in [docs](docs/setup.md), especially [POC results](docs/poc-results.md), [platform research](docs/platform-research.md), and [known issues](docs/known-issues.md).
