# Coupon classification

| Status | Meaning |
|---|---|
| CONFIRMED FULL DISCOUNT | Authorized administrator records positive eligible original price and zero measured remaining subtotal |
| PUBLICLY ADVERTISED FULL DISCOUNT | Reviewed official source explicitly advertises full discount; redemption unconfirmed |
| POSSIBLE FULL DISCOUNT | Submitted or nonofficial evidence suggests a full discount |
| VERIFIED PARTIAL DISCOUNT | Authorized positive reduction leaves a positive subtotal |
| UNVERIFIED CODE | Explicit code reference without current validity evidence |
| EXPIRED | Explicit timezone-aware expiry has elapsed, or documented manual review establishes expiry |
| INELIGIBLE | Administrator records an authorized ineligibility outcome |
| UNKNOWN | Insufficient evidence |

The parser reads explicitly labeled codes. Ordinary free events are not interpreted as coupon offers. An explicit 100%-off offer can exist with a null code. Generic marketing, missing eligibility, negation and unspecified fees are handled conservatively. Only explicit ISO timestamps with a timezone are automatically parsed as expiry.

Money uses Decimal. Percentage discounts and fixed INR discounts are capped at the ticket price. Fixed INR offers are not calculated against another currency. Public price estimates use the event's starting price and do not establish eligibility. Final price remains null when mandatory fees are unknown. Authorized review measurements survive public refreshes and are stored in the audit trail.

“Official documented API” is reserved but rejected until an authorized adapter exists. Manual evidence must include a URL, substantive note and explicit authorization assertion. Administrator assertions are audited, not independently authenticated by a ticketing platform. A review never issues a ticket.
