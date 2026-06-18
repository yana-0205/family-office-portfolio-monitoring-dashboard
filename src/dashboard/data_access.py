from __future__ import annotations

import json
import warnings
from pathlib import Path

import pandas as pd

from src.config import CSV_DIR, OUTPUTS_DIR, PROCESSED_DATA_DIR, REPORTS_DIR, RISK_OUTPUTS_DIR
from src.data_loader import read_csv_table, safe_find_csv
from src.risk.market_data_loader import load_market_prices, load_proxy_map


def _empty_df(message: str, columns: list[str] | None = None) -> pd.DataFrame:
    warnings.warn(message, stacklevel=2)
    df = pd.DataFrame(columns=columns or [])
    df.attrs["warning"] = message
    return df


def load_processed_table(filename: str) -> pd.DataFrame:
    path = PROCESSED_DATA_DIR / filename
    if not path.exists():
        return _empty_df(f"Processed table not found: {path}")
    return pd.read_csv(path)


def load_private_positions() -> pd.DataFrame:
    return load_processed_table("private_positions_post_ingestion.csv")


def load_cash_accounts() -> pd.DataFrame:
    return load_processed_table("cash_accounts_post_ingestion.csv")


def load_capital_call_calendar() -> pd.DataFrame:
    return load_processed_table("capital_call_calendar.csv")


def load_private_market_cashflows() -> pd.DataFrame:
    return load_processed_table("private_market_cashflows.csv")


def load_document_processing_status() -> pd.DataFrame:
    return load_processed_table("document_processing_status.csv")


def load_fund_commentary() -> pd.DataFrame:
    return load_processed_table("fund_commentary_post_ingestion.csv")


def load_review_queue() -> pd.DataFrame:
    path = OUTPUTS_DIR / "validation" / "review_queue_actual.csv"
    if not path.exists():
        return _empty_df(f"Review queue not found: {path}")
    return pd.read_csv(path)


def load_validation_results() -> pd.DataFrame:
    path = OUTPUTS_DIR / "validation" / "validation_results_actual.csv"
    if not path.exists():
        return _empty_df(f"Validation results not found: {path}")
    return pd.read_csv(path)


def load_extracted_json_records(mode: str = "baseline") -> list[dict]:
    directory = OUTPUTS_DIR / "extracted_json" / mode
    if not directory.exists():
        warnings.warn(f"Extracted JSON directory not found: {directory}", stacklevel=2)
        return []
    records = []
    for path in sorted(directory.glob("*.json")):
        records.append(json.loads(path.read_text(encoding="utf-8")))
    if not records:
        warnings.warn(f"No extracted JSON records found in {directory}", stacklevel=2)
    return records


def load_baseline_allocation_if_available() -> pd.DataFrame:
    csv_path = safe_find_csv(["portfolio_holdings", "portfolio holdings"])
    if csv_path is None or not csv_path.exists():
        return _empty_df(
            f"Baseline allocation source not found in {CSV_DIR}.",
            columns=["asset_class", "final_value_usd_m", "allocation_pct"],
        )
    baseline_df = read_csv_table("portfolio_holdings")
    if baseline_df.empty:
        return _empty_df(
            "Baseline allocation table is empty.",
            columns=["asset_class", "final_value_usd_m", "allocation_pct"],
        )

    if {"asset_class", "final_value_usd_m", "allocation_pct"}.issubset(baseline_df.columns):
        grouped = (
            baseline_df.groupby("asset_class", as_index=False)[["final_value_usd_m", "allocation_pct"]]
            .sum()
            .sort_values("final_value_usd_m", ascending=False)
        )
        return grouped

    return _empty_df(
        "Baseline allocation table is missing expected columns.",
        columns=["asset_class", "final_value_usd_m", "allocation_pct"],
    )


def load_public_risk_metrics() -> pd.DataFrame:
    path = RISK_OUTPUTS_DIR / "public_risk_metrics.csv"
    if not path.exists():
        return _empty_df(f"Public risk metrics not found: {path}")
    return pd.read_csv(path)


def load_correlation_matrix() -> pd.DataFrame:
    path = RISK_OUTPUTS_DIR / "correlation_matrix.csv"
    if not path.exists():
        return _empty_df(f"Correlation matrix not found: {path}")
    return pd.read_csv(path, index_col=0)


def load_stress_test_results() -> pd.DataFrame:
    path = RISK_OUTPUTS_DIR / "stress_test_results.csv"
    if not path.exists():
        return _empty_df(f"Stress test results not found: {path}")
    return pd.read_csv(path)


def load_report_markdown(report_filename: str) -> str | None:
    path = REPORTS_DIR / report_filename
    if not path.exists():
        warnings.warn(f"Report file not found: {path}", stacklevel=2)
        return None
    return path.read_text(encoding="utf-8")


def load_extraction_accuracy_summary(mode: str = "baseline") -> pd.DataFrame:
    path = OUTPUTS_DIR / f"{mode}_extraction_accuracy_summary.csv"
    if not path.exists():
        return _empty_df(f"Extraction accuracy summary not found: {path}")
    return pd.read_csv(path)


def load_update_summary_report() -> str | None:
    return load_report_markdown("update_summary.md")


def _load_optional_raw_table(possible_names: list[str], primary_name: str) -> pd.DataFrame:
    csv_path = safe_find_csv(possible_names)
    if csv_path is None or not csv_path.exists():
        return _empty_df(f"Raw table not found for {primary_name}.")
    try:
        return read_csv_table(primary_name)
    except FileNotFoundError:
        return pd.read_csv(csv_path)


def load_portfolio_monthly_summary() -> pd.DataFrame:
    return _load_optional_raw_table(
        ["portfolio_monthly_summary", "portfolio monthly summary"],
        "portfolio_monthly_summary",
    )


def load_portfolio_monthly_by_holding() -> pd.DataFrame:
    return _load_optional_raw_table(
        ["portfolio_monthly_by_holding", "portfolio monthly by holding"],
        "portfolio_monthly_by_holding",
    )


def load_portfolio_holdings() -> pd.DataFrame:
    return _load_optional_raw_table(["portfolio_holdings", "portfolio holdings"], "portfolio_holdings")


def load_private_fund_monthly() -> pd.DataFrame:
    return _load_optional_raw_table(["private_fund_monthly", "private fund monthly"], "private_fund_monthly")


def load_position_exposure_history() -> pd.DataFrame:
    return _load_optional_raw_table(
        ["position_exposure_history", "position exposure history"],
        "position_exposure_history",
    )


def load_latest_position_exposure_snapshot() -> pd.DataFrame:
    history_df = load_position_exposure_history()
    if history_df.empty or "date" not in history_df.columns:
        return _empty_df("Position exposure history is unavailable.")
    snapshot_df = history_df.copy()
    snapshot_df["date"] = pd.to_datetime(snapshot_df["date"], errors="coerce")
    snapshot_df = snapshot_df.dropna(subset=["date"]).sort_values("date")
    if snapshot_df.empty:
        return _empty_df("Position exposure history is unavailable.")
    latest_date = snapshot_df["date"].max()
    return snapshot_df[snapshot_df["date"] == latest_date].copy()


def load_public_instrument_classification() -> pd.DataFrame:
    return _load_optional_raw_table(
        ["public_instrument_classification", "public instrument classification"],
        "public_instrument_classification",
    )


def load_risk_free_proxy_monthly() -> pd.DataFrame:
    return _load_optional_raw_table(
        ["risk_free_proxy_monthly", "risk free proxy monthly"],
        "risk_free_proxy_monthly",
    )


def load_public_monthly_prices() -> pd.DataFrame:
    result = load_market_prices(prefer_real=True)
    price_df = result["prices"]
    if price_df.empty:
        return _empty_df("Public monthly price table is unavailable.")
    price_df = price_df.copy()
    price_df["data_source"] = result["metadata"]["data_source"]
    return price_df


def load_public_proxy_map() -> pd.DataFrame:
    proxy_df = load_proxy_map()
    if proxy_df.empty:
        return _empty_df("Public market proxy mapping is unavailable.", columns=list(proxy_df.columns))
    return proxy_df


def load_region_taxonomy_reference() -> pd.DataFrame:
    return _load_optional_raw_table(
        ["region_taxonomy_reference", "region taxonomy reference"],
        "region_taxonomy_reference",
    )


def load_private_fund_positions_baseline() -> pd.DataFrame:
    return _load_optional_raw_table(["private_fund_positions", "private positions pre ingestion"], "private_fund_positions")


def load_asset_allocation_table() -> pd.DataFrame:
    holdings_df = load_portfolio_holdings()
    if holdings_df.empty:
        fallback = pd.DataFrame(
            [
                {"asset_class": "Global Public Equities", "final_value_usd_m": 225.0},
                {"asset_class": "Fixed Income & Liquid Credit", "final_value_usd_m": 97.5},
                {"asset_class": "Private Equity", "final_value_usd_m": 135.0},
                {"asset_class": "Venture Capital / Growth", "final_value_usd_m": 75.0},
                {"asset_class": "Private Credit", "final_value_usd_m": 67.5},
                {"asset_class": "Real Estate", "final_value_usd_m": 60.0},
                {"asset_class": "Hedge Funds / Absolute Return", "final_value_usd_m": 37.5},
                {"asset_class": "Infrastructure", "final_value_usd_m": 30.0},
                {"asset_class": "Cash & Liquidity", "final_value_usd_m": 22.5},
            ]
        )
        fallback["allocation_pct"] = fallback["final_value_usd_m"] / fallback["final_value_usd_m"].sum()
        fallback["data_source"] = "fallback from corrected project assumptions"
        return fallback

    if {"asset_class", "final_value_usd_m"}.issubset(holdings_df.columns):
        grouped = holdings_df.groupby("asset_class", as_index=False)["final_value_usd_m"].sum()
        grouped["allocation_pct"] = grouped["final_value_usd_m"] / grouped["final_value_usd_m"].sum()
        grouped["data_source"] = "raw portfolio holdings"
        return grouped.sort_values("final_value_usd_m", ascending=False)

    return _empty_df("Asset allocation table missing expected columns.")


def load_geography_exposure_if_available() -> pd.DataFrame:
    holdings_df = load_portfolio_holdings()
    region_column = None
    for candidate in ["region_taxonomy", "region"]:
        if candidate in holdings_df.columns:
            region_column = candidate
            break
    if holdings_df.empty or region_column is None or "final_value_usd_m" not in holdings_df.columns:
        return _empty_df("Geography exposure data is unavailable.", columns=["region", "final_value_usd_m"])
    grouped = holdings_df.groupby(region_column, as_index=False)["final_value_usd_m"].sum()
    grouped = grouped.rename(columns={region_column: "region"})
    return grouped.sort_values("final_value_usd_m", ascending=False)


def load_currency_exposure_if_available() -> pd.DataFrame:
    holdings_df = load_portfolio_holdings()
    if holdings_df.empty or not {"currency", "final_value_usd_m"}.issubset(holdings_df.columns):
        return _empty_df("Currency exposure data is unavailable.", columns=["currency", "final_value_usd_m"])
    return holdings_df.groupby("currency", as_index=False)["final_value_usd_m"].sum().sort_values("final_value_usd_m", ascending=False)


def load_overview_datasets() -> dict[str, pd.DataFrame]:
    return {
        "monthly_summary": load_portfolio_monthly_summary(),
        "monthly_by_holding": load_portfolio_monthly_by_holding(),
        "allocation": load_asset_allocation_table(),
        "private_positions": load_private_positions(),
        "cash_accounts": load_cash_accounts(),
        "document_status": load_document_processing_status(),
        "risk_free": load_risk_free_proxy_monthly(),
    }
