# Setup

See the [README](../README.md) for exact installation/start commands. Python services run from `backend/`; frontend commands run from `frontend/`. `scripts/configure_local.py` generates ignored local credentials and preserves an existing `.env`.

Run Alembic before starting either Python process. SQLite is the zero-infrastructure local database. Set `DATABASE_URL` for PostgreSQL and rerun migrations when using a server database. Do not point the API and worker at different files. Root `.env` is for Compose; `backend/.env` is for local Python settings. The administrator token is never compiled into browser JavaScript.

To scan: start the worker, enter the token, click Start discovery and inspect Discovery. If a job stays queued, the worker is not running against the same database. Missing tables mean migrations were not run. API connection errors mean the backend is unavailable or `BACKEND_URL` was wrong at build time. A 503 mutation response means ADMIN_TOKEN is empty. Blocked/failed source outcomes are shown in job details.

Scheduling is disabled until explicitly configured. Telegram is disabled, and no message was sent during development. Reviewed external sources are optional; AllEvents is added when `ALLEVENTS_AUTHORIZED=true` is set for both API and worker. Production frontend: `npm.cmd run build` then `npm.cmd start`. Compose binds published ports to loopback.
