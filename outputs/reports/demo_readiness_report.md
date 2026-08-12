# Demo Readiness Report

- Generated at: `2026-08-12T20:37:31.325088+00:00`
- Extracted JSON files: `6`
- Validation status: `5 approved / 0 needs_review / 1 rejected`
- Applied updates: `5`
- Blocked updates: `1`
- Risk data source: `real`
- Risk proxy tickers: `30`

## Passed Checks
- baseline extraction output directory exists: /Users/yana/Documents/GitHub/project_portfolio_dashboard/outputs/extracted_json/baseline exists=True
- validation results output exists: /Users/yana/Documents/GitHub/project_portfolio_dashboard/outputs/validation/validation_results_actual.csv exists=True
- review queue output exists: /Users/yana/Documents/GitHub/project_portfolio_dashboard/outputs/validation/review_queue_actual.csv exists=True
- risk metrics output exists: /Users/yana/Documents/GitHub/project_portfolio_dashboard/outputs/risk/public_risk_metrics.csv exists=True
- update summary report exists: /Users/yana/Documents/GitHub/project_portfolio_dashboard/outputs/reports/update_summary.md exists=True
- document processing status exists: /Users/yana/Documents/GitHub/project_portfolio_dashboard/data/processed/document_processing_status.csv exists=True
- processed output exists: private_positions_post_ingestion.csv: /Users/yana/Documents/GitHub/project_portfolio_dashboard/data/processed/private_positions_post_ingestion.csv exists=True
- processed output exists: cash_accounts_post_ingestion.csv: /Users/yana/Documents/GitHub/project_portfolio_dashboard/data/processed/cash_accounts_post_ingestion.csv exists=True
- processed output exists: capital_call_calendar.csv: /Users/yana/Documents/GitHub/project_portfolio_dashboard/data/processed/capital_call_calendar.csv exists=True
- processed output exists: private_market_cashflows.csv: /Users/yana/Documents/GitHub/project_portfolio_dashboard/data/processed/private_market_cashflows.csv exists=True
- processed output exists: document_processing_status.csv: /Users/yana/Documents/GitHub/project_portfolio_dashboard/data/processed/document_processing_status.csv exists=True
- processed output exists: fund_commentary_post_ingestion.csv: /Users/yana/Documents/GitHub/project_portfolio_dashboard/data/processed/fund_commentary_post_ingestion.csv exists=True
- baseline extraction produced 6 JSON files: actual=6, expected=6
- approved documents count is 5: actual=5, expected=5
- needs_review documents count is 0: actual=0, expected=0
- rejected documents count is 1: actual=1, expected=1
- applied updates count is 5: actual=5, expected=5
- blocked updates count is 1: actual=1, expected=1
- risk data source is real: actual=real, expected=real
- risk proxy ticker count is 30: actual=30, expected=30

## Failed Checks
- None

## Recommended Next Step
- If all checks pass, launch `streamlit run app.py` for demo presentation.
