# Synthetic Family Office Dataset V1

This package is the regenerated synthetic V1 dataset for the project portfolio dashboard proof of concept.

## Baseline Assumptions

- Baseline snapshot date: `2026-04-30`
- Total AUM: `USD 750.0m`
- Public / liquid assets: `USD 367.5m`
- Closed-end private fund NAV: `USD 360.0m`
- Cash and liquidity: `USD 22.5m`
- Total private commitments: `USD 500.0m`
- Paid-in capital: `USD 365.0m`
- Unfunded commitments: `USD 135.0m`

## V1 Dataset Features

- public/liquid long-short support with signed notional and delta-adjusted option exposure
- GICS sector classification for public holdings
- market-cap buckets for public and equity-linked exposure
- region taxonomy including Greater China, India, Southeast Asia, Japan, Korea, and Global / Multi-region
- synthetic monthly risk-free proxy for Sharpe calculations
- public proxy risk overlay mapping

## Tables

- `capital_calls.csv`
- `capital_statements.csv`
- `cash_accounts.csv`
- `cash_accounts_post_approved.csv`
- `data_dictionary.csv`
- `distributions.csv`
- `document_metadata.csv`
- `document_update_map.csv`
- `expected_position_updates.csv`
- `family_entities.csv`
- `fund_aliases.csv`
- `fx_rates.csv`
- `ground_truth_extractions.csv`
- `newsletter_updates.csv`
- `portfolio_holdings.csv`
- `portfolio_monthly_by_holding.csv`
- `portfolio_monthly_summary.csv`
- `position_exposure_history.csv`
- `private_fund_master.csv`
- `private_fund_monthly.csv`
- `private_fund_positions.csv`
- `public_instrument_classification.csv`
- `public_monthly_prices_synthetic.csv`
- `public_proxy_risk_map.csv`
- `real_public_market_proxy_map.csv`
- `region_taxonomy_reference.csv`
- `review_queue.csv`
- `risk_free_proxy_monthly.csv`
- `table_name_map.csv`
- `validation_results.csv`
- `validation_rules.csv`