# Update Summary

- Timestamp: `2026-07-17T06:57:28.314029+00:00`
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

- Only records with effective document-level validation status `approved` were applied.
- The official portfolio baseline remains `2026-04-30`; approved May 2026 calls and distributions are tracked as projected overlay items rather than booked cash movements.
- Newsletter updates create commentary output only and do not alter numeric portfolio state.

## Recommended Next Step

- Review any remaining blocked documents and promote only validated records into the portfolio overlay.