# Update Summary

- Timestamp: `2026-06-18T07:30:18.616725+00:00`
- Extraction mode: `baseline`
- Number of extracted records: `6`
- Number approved: `3`
- Number blocked: `3`

## Updates Applied By Document Type

- `capital_call`: `0`
- `distribution`: `1`
- `capital_statement`: `1`
- `newsletter`: `1`

## Blocked Documents

- `PDF_001` | `capital_call` | status blocked
- `PDF_002` | `capital_call` | status blocked
- `PDF_005` | `capital_statement` | status blocked

## Output Files Written

- `/Users/yana/Documents/GitHub/project_portfolio_dashboard/data/processed/private_positions_post_ingestion.csv`
- `/Users/yana/Documents/GitHub/project_portfolio_dashboard/data/processed/cash_accounts_post_ingestion.csv`
- `/Users/yana/Documents/GitHub/project_portfolio_dashboard/data/processed/capital_call_calendar.csv`
- `/Users/yana/Documents/GitHub/project_portfolio_dashboard/data/processed/private_market_cashflows.csv`
- `/Users/yana/Documents/GitHub/project_portfolio_dashboard/data/processed/document_processing_status.csv`
- `/Users/yana/Documents/GitHub/project_portfolio_dashboard/data/processed/fund_commentary_post_ingestion.csv`

## Assumptions

- Only records with document-level validation status `approved` were applied.
- Distribution cash inflows within May 2026 were projected into USD operating cash.
- Newsletter updates create commentary output only and do not alter numeric portfolio state.

## Recommended Next Step

- Build a downstream review-to-approval workflow so `needs_review` documents can be corrected and re-applied safely.