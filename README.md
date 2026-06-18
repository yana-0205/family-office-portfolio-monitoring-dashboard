# Project Portfolio Dashboard

This repository is an AI-powered family office portfolio dashboard proof of concept built on synthetic data. The current implementation includes a complete baseline pipeline from raw mock documents through extraction, validation, approved portfolio updates, and a Streamlit dashboard that reads processed outputs.

All family office data in this repository is synthetic. Mock PDF documents are included to support future extraction and validation workflows.

## Project Purpose

The long-term goal is to support a workflow that turns mock private-market documents into reviewed portfolio updates and eventually into a dashboard with risk monitoring.

Current scope:

- synthetic V1 dataset generation and replacement
- repository restructuring
- configuration and path management
- robust raw data loading
- initial data QA report generation
- baseline PDF extraction pipeline
- validation engine for extracted records
- approved-only portfolio update layer
- Streamlit dashboard reading processed outputs

Out of scope for this phase:

- LLM API extraction
- production portfolio update workflow beyond approved baseline records

## Workflow

Mock PDF documents -> extraction schema -> structured JSON -> validation engine -> review queue -> approved updates -> portfolio dashboard -> public market risk monitoring

## Repository Structure

```text
project_portfolio_dashboard/
├── AGENTS.md
├── README.md
├── app.py
├── data/
│   ├── interim/
│   ├── processed/
│   └── raw/
│       └── family_office_corrected_dataset_v1/
├── notebooks/
├── outputs/
│   ├── extracted_json/
│   ├── figures/
│   ├── reports/
│   ├── risk/
│   └── validation/
├── requirements.txt
├── schemas/
├── src/
│   ├── __init__.py
│   ├── config.py
│   ├── data_checks.py
│   ├── data_loader.py
│   ├── dashboard/
│   ├── extraction/
│   ├── portfolio_updates/
│   ├── risk/
│   └── validation/
└── tests/
```

## Install Dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run The Full Pipeline

Run the pipeline in this order:

```bash
python3 -m src.generate_dataset
python3 -m src.data_checks
python3 -m src.risk.fetch_market_data --provider yfinance --start-date 2020-01-01
python3 -m src.extraction.run_extraction --mode baseline
python3 -m src.validation.run_validation --mode baseline
python3 -m src.portfolio_updates.apply_updates --mode baseline
python3 -m src.risk.run_risk
streamlit run app.py
pytest
```

The dashboard reads processed outputs only. It does not run extraction, validation, or portfolio updates itself.

## Run Individual Steps

### Generate The Synthetic V1 Dataset

```bash
python3 -m src.generate_dataset
```

This rewrites the raw synthetic data package under `data/raw/family_office_corrected_dataset_v1/` while preserving the 6 mock PDF documents.

The regenerated dataset adds:

- public/liquid long-short support with signed notional and delta-adjusted option exposure
- GICS sector classification
- market-cap buckets
- region taxonomy for Greater China, India, Southeast Asia, Japan, Korea, and Global / Multi-region
- synthetic monthly risk-free proxy data for Sharpe calculations
- public proxy risk mapping and position exposure history

### Data QA

```bash
python3 -m src.data_checks
```

This generates [outputs/reports/data_qa_report.md](/Users/yana/Documents/GitHub/project_portfolio_dashboard/outputs/reports/data_qa_report.md).

### Baseline Extraction

```bash
python3 -m src.extraction.run_extraction --mode baseline
```

This writes:

- `outputs/extracted_json/baseline/`
- `outputs/reports/baseline_extraction_run_summary.md`
- `outputs/reports/baseline_extraction_accuracy_summary.md`
- `outputs/baseline_extraction_accuracy_summary.csv`

### Validation Engine

```bash
python3 -m src.validation.run_validation --mode baseline
```

This writes:

- `outputs/validation/validation_results_actual.csv`
- `outputs/validation/review_queue_actual.csv`
- `outputs/reports/validation_summary.md`

### Approved Portfolio Updates

```bash
python3 -m src.portfolio_updates.apply_updates --mode baseline
```

This writes:

- `data/processed/private_positions_post_ingestion.csv`
- `data/processed/cash_accounts_post_ingestion.csv`
- `data/processed/capital_call_calendar.csv`
- `data/processed/private_market_cashflows.csv`
- `data/processed/document_processing_status.csv`
- `data/processed/fund_commentary_post_ingestion.csv`
- `outputs/reports/update_summary.md`

### Public Market Risk Module

To populate real public proxy prices before running risk, fetch them into `data/raw/market_prices/`:

```bash
python3 -m src.risk.fetch_market_data --provider yfinance --start-date 2020-01-01
```

This command reads the approved proxy universe from `real_public_market_proxy_map`, downloads monthly adjusted closes from Yahoo Finance via `yfinance`, and writes a CSV under `data/raw/market_prices/`.

If the fetched real-price file covers too little of the proxy universe, the loader automatically falls back to the synthetic public price history so the dashboard and risk module do not run on partial real data.

```bash
python3 -m src.risk.run_risk
```

This writes:

- `outputs/risk/public_risk_metrics.csv`
- `outputs/risk/correlation_matrix.csv`
- `outputs/risk/stress_test_results.csv`
- `outputs/reports/public_market_risk_summary.md`

Real market price files, whether fetched with `yfinance` or provided manually, should be placed under:

```text
data/raw/market_prices/
```

The repository now includes a local monthly real-price file for the public proxy universe at:

```text
data/raw/market_prices/yfinance_monthly_prices.csv
```

This file contains real monthly closes for the 30 proxy tickers used by the public-markets and risk modules, so the project can run from local data without re-fetching prices at dashboard runtime.

Supported market price CSV formats:

- `Date, Ticker, Close`
- `date, ticker, close`
- `Date` plus one column per ticker in wide format

### Streamlit Dashboard

```bash
streamlit run app.py
```

Open:

```text
http://localhost:8501
```

## Deploy To Streamlit Community Cloud

This project should be deployed to Streamlit Community Cloud rather than GitHub Pages because the app depends on Python, Streamlit, pandas, and local repository data files.

Before deploying:

- push this full project to a GitHub repository
- keep `app.py` at the repository root as the Streamlit entrypoint
- make sure the repository includes the dashboard runtime artifacts under `data/raw/`, `data/processed/`, `outputs/risk/`, `outputs/validation/`, and `outputs/extracted_json/baseline/`

Deployment steps:

1. Create a GitHub repository and upload this project.
2. Go to [Streamlit Community Cloud](https://share.streamlit.io/).
3. Click `Create app`.
4. Select your GitHub repository and branch.
5. Set the entrypoint file path to `app.py`.
6. In `Advanced settings`, select Python `3.12`.
7. Deploy the app.

Notes:

- This repository does not require API keys to render the current dashboard.
- Real public market prices are already stored locally under `data/raw/market_prices/yfinance_monthly_prices.csv`, so the deployed app does not need to fetch market data at runtime.
- The dashboard reads committed raw, processed, and output files. It does not rerun extraction, validation, updates, or risk scripts inside Streamlit.

## Dashboard Pages

The dashboard currently includes:

- Overview
- Asset Class
- Region & Currency
- Public Markets
- Private Markets
- Liquidity & Commitments
- Risk Profile
- Workflow & Controls

- `Overview`: total portfolio metrics sourced from the full monthly summary, portfolio performance statistics, monthly return plus cumulative return trend, asset allocation summary, asset-class composition trend, and a compact workflow snapshot at the bottom
- `Asset Class`: exposure-first asset-class monitoring with four tabs: `Trend` for the All / Long / Short exposure chart plus latest long/short/net/gross summary, `By Month` for a slider and jump-to-month snapshot with month-on-month exposure-change view and snapshot table, `By Category` for one selected asset class through time with latest long/short/net/gross metrics and monthly history table, and `Data Table` for monthly exposure pivots plus an `Attribution` source that shows month-on-month exposure-change views by asset class
- `Region & Currency`: region-first exposure monitoring with `Trend`, `By Month`, `By Category`, and `Data Table` tabs built on the project region taxonomy, plus current region-by-value and currency-by-value share tables, USD vs non-USD views, region taxonomy reference, and current holdings region/currency traceability
- `Public Markets`: public market value, public weight, gross/net/long/short exposure, largest long and short positions, real-price coverage status, current-weight public proxy basket performance, drawdown, proxy performance statistics, and a `Sector & Market Cap` section with separate `Sector` and `Market Cap` views, each using `Trend`, `By Month`, `By Category`, and `Data Table` tabs for exposure-first analysis, plus a reviewable holdings/proxy mapping table
- `Private Markets`: private fund NAV, total private NAV trend, commitments, paid-in capital, unfunded commitments, statement-lag monitoring, strategy / geography / mandate-sector summaries, approved private market cashflows, distribution timeline, approved fund commentary, and a filterable post-ingestion fund table
- `Liquidity & Commitments`: operating cash, soft-eligible liquidity, approved capital calls, expected distributions, liquidity coverage, 30D / 90D / 12M hard and soft coverage views, cash by purpose, unfunded commitments by fund, and account / capital call tables
- `Risk Profile`: exposure-aware public proxy risk overlay with proxy-basket statistics, exposure-weighted volatility and drawdown by asset class / sector / region / liquidity bucket, scenario stress impacts, correlation heatmap, and proxy mapping with real or synthetic source notice
- `Workflow & Controls`: pipeline summary, document ingestion, extraction results, validation results, review queue, and approved update audit trail

`Total AUM` is sourced from `portfolio_monthly_summary.csv` when available and should reflect the corrected `USD 750.0m` portfolio total rather than only processed private plus cash assets.

## Design Philosophy

The dashboard is portfolio-first. It starts with portfolio value, performance, allocation, liquidity, and risk. The AI document workflow is preserved as a separate `Workflow & Controls` page that explains how private-market PDFs are extracted, validated, reviewed, and applied to the portfolio state.

Workflow and review controls remain available, but they are intentionally consolidated into `Workflow & Controls` instead of dominating the main portfolio pages.

Across portfolio pages, the dashboard now uses a shared display convention: money in `USD Xm`, percentages in `x.x%`, multiples in `x.xx`, counts as integers, and missing values as `N/A`.

## Run Tests

```bash
pytest
```

Current test coverage includes:

- data loading and QA
- schema registry
- PDF reading and document classification
- baseline extraction
- validation rules and engine
- approved portfolio update logic
- dashboard data access and formatting helpers

## Key Output Areas

- `data/raw/`: immutable synthetic input package
- `outputs/extracted_json/baseline/`: schema-compliant extraction outputs
- `outputs/validation/`: validation rule results and review queue
- `data/processed/`: approved-only post-ingestion portfolio state
- `outputs/reports/`: QA, extraction, validation, and update summaries

## Dataset Notes

- Initial portfolio snapshot date: `2026-04-30`
- May 2026 documents update the April 2026 baseline
- Total AUM: `USD 750.0m`
- Public / liquid assets: `USD 367.5m`
- Closed-end private fund NAV: `USD 360.0m`
- Total private fund commitments: `USD 500.0m`
- Paid-in capital: `USD 365.0m`
- Unfunded commitments: `USD 135.0m`
- Cash and liquidity: `USD 22.5m`
- Expected mock May 2026 PDF documents: `6`
- All family office data is synthetic

## V1 Dataset Layer

The raw synthetic dataset now includes both the original workflow support tables and the richer V1 portfolio analytics tables.

Core V1 raw tables:

- `portfolio_monthly_summary.csv`
- `portfolio_holdings.csv`
- `portfolio_monthly_by_holding.csv`
- `private_fund_master.csv`
- `private_fund_positions.csv`
- `private_fund_monthly.csv`
- `cash_accounts.csv`
- `position_exposure_history.csv`
- `public_instrument_classification.csv`
- `public_proxy_risk_map.csv`
- `risk_free_proxy_monthly.csv`
- `region_taxonomy_reference.csv`

Design intent:

- `portfolio_monthly_summary.csv` remains the canonical source for `Total AUM`
- public/liquid assets now carry long / short, signed notional, and delta-adjusted exposure fields
- private assets remain fund-level in V1 and use mandate/proxy classification where appropriate
- synthetic and proxy-based performance inputs are explicit rather than implied
- private funds now carry mixed reporting cadence assumptions (`Monthly` and `Quarterly`) so statement-lag monitoring has realistic cross-sectional variation

## Working Rule

Project documentation should move with the code. As new pipeline stages, commands, outputs, or pages are added, `README.md` should be updated in the same change so the documented workflow stays accurate.
