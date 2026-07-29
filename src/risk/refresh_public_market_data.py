from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.config import MARKET_PRICES_DIR
from src.risk.fetch_market_data import run as run_market_fetch
from src.risk.fetch_market_data import build_parser as build_market_fetch_parser
from src.risk.run_risk import run as run_risk_pipeline


def infer_market_data_start_date(default_start_date: str = "2020-01-01") -> str:
    csv_paths = sorted(MARKET_PRICES_DIR.glob("*.csv"))
    candidate_dates: list[pd.Timestamp] = []
    for csv_path in csv_paths:
        try:
            market_df = pd.read_csv(csv_path, usecols=["date"])
        except ValueError:
            continue
        parsed_dates = pd.to_datetime(market_df["date"], errors="coerce").dropna()
        if not parsed_dates.empty:
            candidate_dates.append(parsed_dates.min())
    if not candidate_dates:
        return default_start_date
    return min(candidate_dates).strftime("%Y-%m-%d")


def normalize_target_month_end(target_month_end: str | pd.Timestamp) -> pd.Timestamp:
    parsed = pd.to_datetime(target_month_end, errors="coerce")
    if pd.isna(parsed):
        raise ValueError(f"Invalid target month end: {target_month_end}")
    return pd.Timestamp(parsed).to_period("M").to_timestamp("M")


def build_fetch_end_date(target_month_end: str | pd.Timestamp) -> str:
    month_end = normalize_target_month_end(target_month_end)
    next_month_start = month_end + pd.offsets.Day(1)
    return next_month_start.strftime("%Y-%m-%d")


def trim_market_price_file_to_month_end(csv_path: Path, target_month_end: str | pd.Timestamp) -> dict[str, object]:
    month_end = normalize_target_month_end(target_month_end)
    market_df = pd.read_csv(csv_path)
    market_df["date"] = pd.to_datetime(market_df["date"], errors="coerce")
    market_df = market_df.dropna(subset=["date"])
    trimmed_df = market_df[market_df["date"] <= month_end].copy().sort_values(["ticker", "date"])
    trimmed_df["date"] = trimmed_df["date"].dt.strftime("%Y-%m-%d")
    trimmed_df.to_csv(csv_path, index=False)
    return {
        "row_count": len(trimmed_df),
        "max_date": None if trimmed_df.empty else trimmed_df["date"].max(),
    }


def refresh_public_market_data_for_month(
    target_month_end: str | pd.Timestamp,
    *,
    start_date: str | None = None,
    output_filename: str = "yfinance_monthly_prices.csv",
) -> dict[str, object]:
    normalized_month_end = normalize_target_month_end(target_month_end)
    effective_start_date = start_date or normalized_month_end.to_period("M").to_timestamp().strftime("%Y-%m-%d")
    effective_end_date = build_fetch_end_date(normalized_month_end)

    parser = build_market_fetch_parser()
    fetch_args = parser.parse_args(
        [
            "--provider",
            "yfinance",
            "--start-date",
            effective_start_date,
            "--end-date",
            effective_end_date,
            "--interval",
            "1d",
            "--output-filename",
            output_filename,
        ]
    )
    fetch_results = run_market_fetch(fetch_args)
    output_path = fetch_results.get("output_path")
    trim_results = None
    if output_path:
        trim_results = trim_market_price_file_to_month_end(Path(output_path), normalized_month_end)
    if not trim_results or not trim_results.get("max_date"):
        raise RuntimeError("Market refresh produced no usable price rows.")
    refreshed_price_month = normalize_target_month_end(trim_results["max_date"])
    if refreshed_price_month < normalized_month_end:
        raise RuntimeError(
            "Market refresh did not reach the requested month. "
            f"Target={normalized_month_end.strftime('%Y-%m-%d')}, "
            f"latest price={refreshed_price_month.strftime('%Y-%m-%d')}."
        )
    refreshed_price_df = pd.read_csv(Path(output_path))
    refreshed_price_df["date"] = pd.to_datetime(refreshed_price_df["date"], errors="coerce")
    expected_tickers = set(fetch_results.get("metadata", {}).get("expected_tickers", []))
    target_tickers = set(
        refreshed_price_df.loc[
            refreshed_price_df["date"].dt.to_period("M") == normalized_month_end.to_period("M"),
            "ticker",
        ].dropna().astype(str)
    )
    target_coverage = (len(target_tickers & expected_tickers) / len(expected_tickers)) if expected_tickers else 0.0
    if target_coverage < 1.0:
        missing_tickers = sorted(expected_tickers - target_tickers)
        raise RuntimeError(
            "Market refresh did not provide complete target-month coverage. "
            f"Target={normalized_month_end.strftime('%Y-%m-%d')}, coverage={target_coverage:.0%}, "
            f"missing={', '.join(missing_tickers)}."
        )
    risk_results = run_risk_pipeline()
    risk_end_date = pd.to_datetime(risk_results.get("date_range", (None, None))[1], errors="coerce")
    if pd.isna(risk_end_date) or normalize_target_month_end(risk_end_date) < normalized_month_end:
        raise RuntimeError(
            "Risk outputs were not rebuilt through the requested month. "
            f"Target={normalized_month_end.strftime('%Y-%m-%d')}, risk end={risk_end_date}."
        )
    return {
        "target_month_end": normalized_month_end.strftime("%Y-%m-%d"),
        "start_date": effective_start_date,
        "end_date": effective_end_date,
        "fetch": fetch_results,
        "trim": trim_results,
        "risk": risk_results,
        "verified_through": normalized_month_end.strftime("%Y-%m-%d"),
        "target_month_coverage": target_coverage,
    }
