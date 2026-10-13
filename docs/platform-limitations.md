# Platform limitations

AllEvents public-page discovery is opt-in via `ALLEVENTS_AUTHORIZED=true`, based on the operator's reported direct permission. The default seed is Bangalore's public `/all` listing; its Event JSON-LD supplies event URLs and detail pages supply coupon evidence. No Apify actor, paid proxy, or private endpoint is used. Without this flag, AllEvents remains blocked. Organizer submissions import the organizer's own provided document.

Mepass allows the public crawl paths under the reviewed policies; private and query-filtered paths are excluded. Redirections require a source review and are not followed. HTTP 401/403/429 and detected challenges stop the host. Robots failures fail closed. Operators must review current terms before expanding sources or enabling schedules; terms changes are not automatically interpreted.

Empty JSON-LD offers do not mean free tickets. Missing time zones do not mean UTC. A platform-described organizer can be the platform rather than the actual event producer. Lower starting prices do not establish the price of a coupon-eligible category. No documented platform coupon-validation API was available. Neither ticket issuance nor redeemability was tested.
