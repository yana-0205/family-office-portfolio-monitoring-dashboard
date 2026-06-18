# Private Markets Dataset Remake Spec

## Scope

This spec focuses on the two private-market display areas that previously lacked enough synthetic support:

1. `Statement Lag by Fund`
2. `Cashflows` and `Approved Fund Commentary`

## Statement Lag Requirements

| Display item | Purpose | Required fields | Minimum distribution requirement | Current remediation |
| --- | --- | --- | --- | --- |
| Statement Lag by Fund | Compare how stale each fund's most recent valuation is | `as_of_date`, `fund_name`, `last_statement_date` | At least 3 lag buckets across the fund set | Added 5 lag buckets: 10D, 20D, 30D, 46D, 61D |

## Cashflow Requirements

| Display item | Purpose | Required fields | Minimum volume requirement | Current remediation |
| --- | --- | --- | --- | --- |
| Capital Calls and Distributions | Show approved private-market inflows and outflows over time | `fund_name`, `cashflow_type`, `cashflow_date`, `expected_cash_inflow_usd_m`, `source_document_id`, `update_type` | At least 8 approved events across multiple dates and both directions | Expanded processed cashflows to 11 rows |
| Distribution Timeline | Show only approved distribution events | `fund_name`, `cashflow_type`, `cashflow_date`, `net_distribution_usd_m` or `gross_distribution_usd_m` | At least 4 approved distribution events across multiple dates | Expanded to 6 distribution events in raw history, 6 reflected in processed where applicable |

## Commentary Requirements

| Display item | Purpose | Required fields | Minimum volume requirement | Current remediation |
| --- | --- | --- | --- | --- |
| Approved Fund Commentary | Provide qualitative monitoring context by fund and period | `fund_name`, `reporting_period`, `market_themes`, `risk_notes`, `valuation_commentary`, `expected_capital_activity` | At least 4 approved commentary rows spanning multiple funds or periods | Expanded processed commentary to 5 rows |

## Remake Rules Applied

- Historical approved capital calls were carried into processed private-market cashflow history as negative cashflows.
- Historical approved distributions were carried into processed private-market cashflow history as positive cashflows.
- Historical approved newsletters were carried into processed post-ingestion commentary.
- Baseline private fund positions now use staggered `last_statement_date` values rather than a uniform 30-day lag.

## Resulting Expectations

- `Statement Lag by Fund` should no longer render as a uniform flat comparison.
- `Cashflows` should now show multiple approved events across time with both inflow and outflow directions.
- `Approved Fund Commentary` should now read as a monitoring layer rather than a single placeholder row.
