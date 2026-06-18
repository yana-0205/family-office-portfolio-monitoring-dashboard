# Public Market Risk Summary

- Data source used: `real`
- Source files: `yfinance_monthly_prices.csv`
- Tickers processed: `2800.HK, 3067.HK, ACWI, AGG, BABA, BIL, BRK.B, CNYA, DBC, DBMF, EEM, EMB, EWJ, EWS, EWY, GLD, GOOGL, HYG, IGIB, INDA, JD, LQD, MSFT, NVDA, PDD, QAI, QQQ, SPY, TLT, VNQ`
- Date range: `2016-06-30 -> 2026-06-12`

## Outputs

- `/Users/yana/Documents/GitHub/project_portfolio_dashboard/outputs/risk/public_risk_metrics.csv`
- `/Users/yana/Documents/GitHub/project_portfolio_dashboard/outputs/risk/correlation_matrix.csv`
- `/Users/yana/Documents/GitHub/project_portfolio_dashboard/outputs/risk/stress_test_results.csv`

## Notes

- This module monitors public-market proxy risk only.
- If real market files are absent, synthetic price seeds are used and should be treated as illustrative only.
- This is not investment advice.