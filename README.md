# Project Portfolio Dashboard

This repository is an AI-enabled family office portfolio dashboard proof of concept built on synthetic data. The default demo uses a deterministic, API-free extraction pipeline from raw mock documents through validation, approved portfolio updates, and a Streamlit dashboard. A separate API-backed LLM extraction mode is available for optional comparison and future extension.

All family office data in this repository is synthetic. Mock PDF documents are included to support the baseline extraction and validation workflow, and Streamlit-staged uploads are written to `data/interim/document_ingestion/` before any offline extraction or review occurs.

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

- production portfolio update workflow beyond approved baseline records

## Workflow

Mock PDF documents or staged PDF uploads -> extraction schema -> structured JSON -> validation engine -> review queue -> approved updates -> portfolio dashboard -> public market risk monitoring

### Extraction Modes

- `baseline` — default for demonstrations and routine local use. It is deterministic, requires no API key, and produces the locked expected results.
- `intake` — processes PDFs staged through the dashboard intake workflow using the same API-free extraction logic.
- `llm` — optional API-backed extraction for experiments and comparison against ground truth. It is not required to start the dashboard or deliver the standard demo.

Unless you are specifically testing AI extraction quality, use `--mode baseline`.

## Demo Status

This repository is currently positioned as a presentation-ready demo rather than a live operating system.

The demo storyline is locked to the following synthetic baseline:

- initial portfolio snapshot date: `2026-04-30`
- 6 mock May 2026 private-market documents update the April baseline
- official portfolio date remains `2026-04-30`; approved May document outputs are treated as a processed overlay rather than a new official close
- extraction mode: `baseline`
- API requirement for the standard demo: `none`
- validation outcome: `3 approved`, `2 needs review`, `1 rejected`
- approved updates applied to processed portfolio state: `3`
- portfolio performance statistics are presented as a `synthetic portfolio return series`
- the risk module is presented as a `public proxy overlay only`, not a full total-portfolio risk engine
- liquidity views separate `booked baseline cash` from `projected approved calls and distributions`
- public-market risk overlay currently uses the committed real monthly proxy file under `data/raw/market_prices/yfinance_monthly_prices.csv`

Public demo app:

- [Streamlit demo](https://family-office-portfolio-monitoring-dashboard-nxy9cfnrmdwspj3fn.streamlit.app)

For demo purposes, static committed data is acceptable. The priority is that the pipeline logic is clear, the workflow states are traceable, and the dashboard pages render without errors.

## Final Delivery Checklist

This repository is being completed against a fixed demo-delivery standard rather than open-ended feature expansion.

### A. Must Deliver

1. End-to-end pipeline commands run successfully:
   - `python3 -m src.data_checks`
   - `python3 -m src.extraction.run_extraction --mode baseline`
   - `python3 -m src.validation.run_validation --mode baseline`
   - `python3 -m src.portfolio_updates.apply_updates --mode baseline`
   - `python3 -m src.risk.run_risk`
2. Demo status can be verified with:
   - `python3 -m src.demo_check`
3. Automated tests pass:
   - `pytest`
4. The Streamlit dashboard starts and the eight delivery pages render without errors:
   - `Overview`
   - `Asset Class`
   - `Region & Currency`
   - `Public Markets`
   - `Private Markets`
   - `Liquidity & Commitments`
   - `Risk Profile`
   - `Workflow & Controls`
5. The core business storyline is visible end to end:
   - `mock PDFs -> extraction -> validation / review -> approved-only updates -> processed portfolio state -> dashboard -> public proxy risk`
6. V1 portfolio monitoring coverage is present:
   - long / short exposure
   - sector
   - market cap
   - region taxonomy
   - performance statistics
   - liquidity and commitments
   - public-proxy portfolio risk overlay
7. Documentation is handoff-ready:
   - synthetic-data labeling is explicit
   - public-proxy labeling is explicit
   - run commands and output locations are documented

### B. Optional Polish

1. Page naming and explanatory text consistency
2. Better empty-state copy
3. Clearer tooltip and help-text coverage
4. Light presentation polish for charts, tables, and default ordering

### C. Explicitly Out Of Scope

- production-grade data platform work
- live runtime dependency on online market data fetches
- auth / multi-user product features
- institutional-grade analytics depth beyond demo needs
- unlimited visual or feature polish

## Current Delivery Status

At the current repository state, the project already meets the command-level delivery gate:

- `python3 -m src.data_checks`: passes
- `python3 -m src.demo_check`: passes and writes `outputs/reports/demo_readiness_report.md`
- `pytest`: passes

The remaining work should therefore focus on presentation consistency and controlled demo polish rather than new platform scope.

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

Use Python 3.9 or newer. Python 3.12 is the recommended local and deployment version.

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
python3 -m src.extraction.run_extraction --mode baseline
python3 -m src.validation.run_validation --mode baseline
python3 -m src.portfolio_updates.apply_updates --mode baseline
python3 -m src.risk.run_risk
streamlit run app.py
pytest
```

The dashboard reads processed outputs only. It does not run extraction, validation, or portfolio updates itself. Uploads from the `Document Intake` page are staged into `data/interim/document_ingestion/` and remain outside portfolio state until the offline extraction and review workflow is completed.

For upload-driven testing, use the helper scripts below:

- Reset the dashboard to baseline-only state and back up the current processed/overlay artifacts:
  - `python3 -m src.testing.prepare_upload_test_state`
- After staging PDFs through `Document Intake`, run the staged-upload pipeline:
  - `python3 -m src.testing.run_intake_pipeline`

In the app, the intended user flow is:

1. Open `Document Intake`
2. Upload PDFs into the staged inbox
3. Use `Update Portfolio State`
4. Use `Refresh Market-Linked Pages` when you want `Public Markets` and `Risk Profile` aligned to the approved PDF month
5. Use `Demo Tools -> Reset To Demo Start State` only when you want to replay the demo from the baseline month

## Demo Runbook

For a stable local demo, use this exact order:

```bash
python3 -m src.data_checks
python3 -m src.extraction.run_extraction --mode baseline
python3 -m src.validation.run_validation --mode baseline
python3 -m src.portfolio_updates.apply_updates --mode baseline
python3 -m src.risk.run_risk
python3 -m src.demo_check
streamlit run app.py
```

Expected demo state after a clean rerun:

- QA checks: `26 passed`, `0 failed`
- extraction outputs: `6` JSON files
- validation status: `3 approved`, `2 needs review`, `1 rejected`
- approved updates applied: `3`
- risk data source: `real`

`pytest` should also pass before presenting the project:

```bash
pytest
```

If you want a single demo-readiness confirmation after the pipeline finishes:

```bash
python3 -m src.demo_check
```

This writes [outputs/reports/demo_readiness_report.md](/Users/yana/Documents/GitHub/project_portfolio_dashboard/outputs/reports/demo_readiness_report.md) and confirms the locked demo counts, processed outputs, and public-risk source state.

### Document Intake Demo Loop

For the interactive upload demo inside the app, use this order:

1. If needed, open `Demo Tools` and click `Reset To Demo Start State`
2. Upload the target PDFs in `Document Intake`
3. Click `Process Staged PDFs And Update Dashboard`
4. Click `Refresh Public Markets And Risk Data`
5. Review `Overview`, `Public Markets`, `Private Markets`, and `Risk Profile`
6. Reset again only if you want to replay the same scenario for another demo run

Notes:

- `Update Portfolio State` changes the processed portfolio state only for approved documents
- `Refresh Market-Linked Pages` updates external-market-backed pages to the current approved PDF month
- `Reset To Demo Start State` also rewinds public market data and risk outputs back to the official baseline month

Expected checkpoints during the demo:

- after upload: the staged inbox count increases, but portfolio state does not move yet
- after `Update Portfolio State`: approved documents move into the processed overlay state
- after `Refresh Public Markets And Risk Data`: `Public Markets` and `Risk Profile` align to the current approved PDF month
- after reset: the approved overlay month and market-linked pages return to the official baseline month

## Run Individual Steps

### LLM Document Extraction

The locked demo and normal project operation use deterministic `baseline` extraction and do not consume API credits. A real API-backed LLM mode is retained only for optional extraction experiments against the same ground truth and JSON Schemas:

```bash
cp .env.example .env
# Open .env locally and replace the OPENAI_API_KEY placeholder.
python3 -m src.extraction.run_extraction --mode llm
python3 -m src.validation.run_validation --mode llm
python3 -m src.portfolio_updates.apply_updates --mode llm
```

The default model is `gpt-5.6-sol`. Set `OPENAI_EXTRACTION_MODEL` or pass `--model` to override it. LLM outputs are written under `outputs/extracted_json/llm/` and remain subject to the existing schema validation, review rules, and approved-only update controls. The pipeline raises an explicit error when credentials are missing; it never presents baseline output as LLM output. Do not use this mode during the standard presentation unless an API comparison is explicitly requested.

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

The standard demo uses the committed local real-price file, so no network refresh is required. To refresh public proxy prices manually, run:

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
- The current deployed demo app is [family-office-portfolio-monitoring-dashboard-nxy9cfnrmdwspj3fn.streamlit.app](https://family-office-portfolio-monitoring-dashboard-nxy9cfnrmdwspj3fn.streamlit.app).

## Dashboard Pages

The dashboard currently includes:

- Overview
- Document Intake
- Asset Class
- Region & Currency
- Public Markets
- Private Markets
- Liquidity & Commitments
- Risk Profile
- Workflow & Controls

- `Overview`: total portfolio metrics sourced from the full monthly summary, a clear boundary between the official April 2026 baseline and the approved May 2026 overlay, portfolio performance statistics, monthly return plus cumulative return trend, asset allocation summary, asset-class composition trend, and a compact workflow snapshot at the bottom
- `Asset Class`: exposure-first asset-class monitoring with four tabs: `Trend` for the All / Long / Short exposure chart plus latest long/short/net/gross summary, `By Month` for a slider and jump-to-month snapshot with month-on-month exposure-change view and snapshot table, `By Category` for one selected asset class through time with latest long/short/net/gross metrics and monthly history table, and `Data Table` for monthly exposure pivots plus an `Attribution` source that shows month-on-month exposure-change views by asset class
- `Region & Currency`: region-first exposure monitoring with `Trend`, `By Month`, `By Category`, and `Data Table` tabs built on the project region taxonomy, plus current region-by-value and currency-by-value share tables, USD vs non-USD views, region taxonomy reference, and current holdings region/currency traceability
- `Public Markets`: current public/liquid sleeve monitoring through a public-proxy overlay, including public market value, public weight, gross/net/long/short exposure, largest long and short positions, real-price coverage status, current-weight public proxy basket performance, drawdown, proxy performance statistics, and a `Sector & Market Cap` section with separate `Sector` and `Market Cap` views, each using `Trend`, `By Month`, `By Category`, and `Data Table` tabs for exposure-first analysis, plus a reviewable holdings/proxy mapping table
- `Private Markets`: private fund NAV, total private NAV trend, commitments, paid-in capital, unfunded commitments, statement-lag monitoring, strategy / geography / mandate-sector summaries, approved private market cashflows, distribution timeline, approved fund commentary, and a filterable post-ingestion fund table
- `Liquidity & Commitments`: a booked-versus-projected liquidity view that separates baseline cash from approved overlay flows, plus operating cash, soft-eligible liquidity, projected capital calls, projected distributions, liquidity coverage, 30D / 90D / 12M hard and soft coverage views, cash by purpose, unfunded commitments by fund, and account / capital call tables
- `Risk Profile`: a public-proxy risk overlay only, with proxy-basket statistics, exposure-weighted volatility and drawdown by asset class / sector / region / liquidity bucket, scenario stress impacts, correlation heatmap, and proxy mapping with real or synthetic source notice
- `Document Intake`: interactive PDF staging into the interim ingestion inbox, with no direct portfolio-state impact before offline extraction, validation, and approval
- `Workflow & Controls`: pipeline summary, processed document status, extraction results, validation results, review queue, and approved update audit trail

`Total AUM` is sourced from `portfolio_monthly_summary.csv` when available and should reflect the corrected `USD 750.0m` portfolio total rather than only processed private plus cash assets.

The current presentation pass also applies a portfolio-branded Streamlit theme with a redesigned left sidebar so the demo reads more like a curated monitoring product than a default developer console.

## Design Philosophy

The dashboard is portfolio-first. It starts with portfolio value, performance, allocation, liquidity, and risk. Interactive PDF intake is isolated on the `Document Intake` page, while `Workflow & Controls` explains how private-market PDFs are staged, extracted, validated, reviewed, and applied to the portfolio state.

Workflow and review controls remain available, but they are intentionally consolidated into `Workflow & Controls` instead of dominating the main portfolio pages.

Across portfolio pages, the dashboard now uses a shared display convention: money in `USD Xm`, percentages in `x.x%`, multiples in `x.xx`, counts as integers, and missing values as `N/A`.

Page-level captions also follow a shared rule: each page should state what it monitors, why the view matters, and whether the underlying view is baseline synthetic data, approved post-ingestion state, or a public-proxy overlay.

Empty states should also be graceful: when an optional file or table is missing, the dashboard should explain that the section is unavailable and, where possible, surface the upstream source detail instead of crashing.

Where a metric label is ambiguous, the dashboard should provide short help text that explains the measurement basis, such as gross versus net exposure, hard versus soft liquidity coverage, or public-proxy versus full-portfolio statistics.

For presentation use, tables should also default to a sensible business order, such as severity-first review queues and document-order workflow tables, so the first screen shown in a demo is already interpretable.

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
- `outputs/extracted_json/llm/`: optional API-backed comparison outputs; not used by the standard demo
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
