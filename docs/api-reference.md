# API reference

Interactive OpenAPI: `http://127.0.0.1:8000/docs`; schema: `/openapi.json`.

Public GET routes: `/api/health`, `/api/platforms`, `/api/platforms/status`, `/api/sources`, `/api/events`, `/api/events/{id}`, `/api/events/{id}/promotions`, `/api/promotions`, `/api/promotions/full-discount`, `/api/promotions/{id}`, `/api/analytics/overview`, `/api/analytics/discovery`, `/api/jobs`, `/api/jobs/{id}`.

Token-protected routes: POST `/api/jobs/discovery`, POST `/api/submissions`, POST `/api/promotions/{id}/verify`, GET/POST `/api/watchlists`, DELETE `/api/watchlists/{id}`, GET `/api/notifications`. Use `Authorization: Bearer <ADMIN_TOKEN>`. Missing configured token disables mutations. Unknown records return 404. Validation uses Pydantic; HTTP errors use `error.code/message` and Pydantic validation errors use FastAPI's `detail` array.

Lists of events/promotions/jobs/notifications return `{items,total,page,page_size}`. Page size maximum is 100. Event filters: `q`, `platform`, `location`, `min_price`, `max_price`, `date_from`, `date_to`, `status`, `min_discount`, `full_discount`, `sort` (newest/date/price/name). Promotion filters: `q`, `platform`, `event_id`, `status`, `full_discount`. Dates use ISO 8601. Prices are decimal strings. Null means unknown.

Discovery POST body: `{ "max_pages":10, "max_depth":1, "kind":"discovery" }`. Maximum 30 pages and depth 2. An existing active job is returned rather than duplicated. Supported kind labels use the same bounded source pipeline; expiration monitoring runs separately in the worker. There is no arbitrary-URL crawl endpoint.

Watch kinds: event ID, organizer name, city, keyword, full_discount. The workspace has a single admin, not account-specific watches. Submission and verification body schemas are documented in OpenAPI. Every write endpoint requires authorization. In-memory API rate limit: 120 requests per IP per minute; body maximum 100 KB. Deploy behind an authenticated reverse proxy if exposed beyond loopback.
