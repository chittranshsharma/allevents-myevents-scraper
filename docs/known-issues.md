# Known issues and remaining work

1. AllEvents direct discovery requires the operator's reported permission and an explicit local flag. Its free public HTML path is limited to bounded listing and detail pages. No coupon API integration exists for either platform.
2. No real public coupon or full-discount offer was found in the bounded test. Discovery usefulness at scale is unproven.
3. Event JSON-LD can omit dates, real venues, ticket categories and actual organizer identities. “Onwards” pricing is a starting price, not a guaranteed eligible category price.
4. Only deterministic English promotion patterns and INR fixed amounts are supported. Complex eligibility/expiry language, multilingual extraction, cross-source semantic matching and withdrawn-offer detection need review tooling.
5. HTTP-only crawler; no runtime public-page rendering, search-provider integration, social API connector or nested sitemap expansion. Redirects require manual source updates.
6. One trusted administrator and one worker. There is no multiuser login, distributed queue or external provider credential management. Do not expose this local service as a public SaaS without adding those controls.
7. DNS is checked before each approved-host request, but not pinned to the HTTP connection. Trusted-host allowlists constrain the risk; production requires outbound network rules for private/reserved ranges and untrusted DNS. In-memory rate limiting is per API process.
8. Current terms must be reviewed by the operator before enabling continuous collection or adding sources. Automated terms-change interpretation is not implemented.
9. PostgreSQL/Compose and Telegram delivery have not been exercised here. Tests use SQLite and mocked network responses. Starlette emits a deprecation warning for its HTTPX test-client integration.
10. Telegram has a bounded retry count, but ambiguous delivery failures can produce duplicate external messages. In-app deduplication is transactional. No Telegram alerts were sent.

Priorities: authorized sources and organizer feeds; PostgreSQL/Compose CI; authenticated user accounts; improved evidence review/expiry matching; measured discovery quality; then additional authorized notification channels and rendering adapters.
