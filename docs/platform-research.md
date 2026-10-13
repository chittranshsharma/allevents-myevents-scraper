# Platform research

Checked **13 October 2026**. Policy research preceded event collection. Tool-based web results can be cached; direct Mepass robots/terms requests also returned HTTP 200.

## AllEvents

Official domain: [allevents.in](https://allevents.in). Its [terms](https://allevents.in/conditions), acceptable-use clause, prohibit crawling/scraping, including manual methods, and unauthorized automated harvesting. The operator reports direct permission for this personal project; AllEvents collection is therefore opt-in and records that reported basis. [Robots](https://allevents.in/robots.txt) has path and referral-query restrictions; the crawler still checks them per job.

The public Bangalore `/all` listing returned Event JSON-LD on 13 October 2026, and a linked event detail page returned richer Event JSON-LD. The free direct connector uses those documents. The official [Events API offering](https://allevents.in/pages/events-api) advertises REST JSON event data, stable identifiers and access by request; pricing, credentials and endpoint contracts were not obtained. No coupon validation capability is documented there, and no API call was attempted. Apify actors were evaluated but not adopted because this project requires zero paid services.

The official [coupon support article](https://support.allevents.in/article/197-how-do-i-create-public-private-discount-code) documents public/private code visibility, fixed and percentage discounts, selectable ticket types, expiry and usage limits. [Creation guidance](https://support.allevents.in/article/161-creating-coupon-codes-two-ways-to-use-the-feature) also documents account-linked codes; those restricted identity-based invitations are excluded. This establishes coupon infrastructure, not a discovered live coupon, 100% support or authorized third-party validation. No checkout endpoint was investigated.

## Mepass

Official domain: [mepass.in](https://mepass.in), also [www.mepass.in](https://www.mepass.in). The official [about page](https://www.mepass.in/about-us) identifies an Indian event ticketing platform, distinct from MeetPass or other similarly named products.

[Robots](https://www.mepass.in/robots.txt) explicitly allows public crawling, blocks `/admin/`, `/api/`, `/_next/`, `/tmp/` and search/filter/page/sort queries, and advertises [sitemap.xml](https://www.mepass.in/sitemap.xml). The sitemap was identified, not exhaustively crawled. [Terms](https://www.mepass.in/terms-condition) were read: accounts and ticket sharing are restricted, checkout may include fees, and content is protected. No automation prohibition was observed in this reviewed version. The integration is confined to published HTML under those robots rules; this does not establish a general redistribution license.

Public navigation includes city/category hubs, `/events/<slug>` and `/city/<city>/events/<slug>`. Server HTML carries duplicate JSON-LD nodes; both `Event` and `Festival` types were observed. Some nodes have empty offers, missing dates and `TBD` locations. Explicit visible INR “onwards” pricing is used when structured prices are absent. Unknown information is kept null. No private application state or external JavaScript assets were collected. Pagination queries are blocked.

No official public coupon validation API, coupon feed, documented 100%-discount support, coupon eligibility rules or public social API authorization was established. Search-engine research surfaced event pages but no usable public coupon discovery capability. The bounded POC found no coupon references; this is not evidence that no coupons exist.

Schema subtype parsing follows [Schema.org Event](https://schema.org/Event). The actual URLs, fetch outcomes and measurements are recorded separately in `poc-observations.json` and `live-job-observations.json`.
