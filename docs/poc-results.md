# Proof-of-concept results

Checked **13 October 2026** using permitted Mepass public HTML. **No real coupon or 100%-off promotion was discovered.** No synthetic finding appears in the normal database.

Initial reconnaissance fetched a category hub and three linked event pages. It normalized three events with missing structured dates, prices and venues. The full implemented crawler then ran three bounded jobs (8, 8 and 10 successfully fetched pages, respectively). Those counts include repeat visits and the listing hub; they are not 26 distinct events.

The final job examined the hub and all nine event-detail URLs linked within the sampled scope. It completed with **10 pages, 0 network/access/parser errors**, and the database held **9 unique real event records**. Three had visible starting prices: Ultra Endurance Race Bangalore ₹2,500; Anybody Can Dandiya 6.0 – Palace Grounds ₹99; Anybody Can Dandiya 6.0 – Whitefield ₹99. These are published starting prices, not quotes for specific ticket categories. Structured dates and venues remained unknown in this sample.

| Measure | Actual result |
|---|---:|
| Unique real events normalized | 9 |
| Distinct public source documents in final sample | 10 (1 hub + 9 event pages) |
| Coupon candidates | 0 |
| Evidence-supported promotions | 0 |
| Potential 100%-off offers | 0 |
| Independently verified promotions | 0 |
| Final scan extraction/network errors | 0 |
| Candidate yield per 1,000 sampled events | 0 |
| Precision / false-positive rate | Not measurable: no reviewed candidates |
| Whole-platform coverage | Unknown |
| AllEvents collected events in this initial POC | 0; permission was reported later |

The first crawler iteration failed to recognize Festival subtypes and silently skipped some records; this was corrected, regression-tested and validated in the final scan. Parser-version cache invalidation now permits reprocessing after parser updates. Future missing metadata is explicitly surfaced in job results.

Public HTML evidence is distinct from checkout validation. No checkout was queried, no code was guessed and no ticket was issued. The sample is one Bengaluru discovery hub; no claim of comprehensive coupon coverage is justified. No organizer external source or authorized API credential was available for live testing. Official support documentation establishes AllEvents coupon features but supplies no live offer for this POC.

Exact event URLs, prices, fetch timestamps, hashes and job outcomes: [live-job-observations.json](live-job-observations.json). Initial observations: [poc-observations.json](poc-observations.json). Raw research snapshots are local ignored runtime files, not production fixtures.
