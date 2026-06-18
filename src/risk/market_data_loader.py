from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import pandas as pd

from src.config import MARKET_PRICES_DIR
from src.data_loader import read_csv_table, safe_find_csv


def list_market_price_files() -> list[Path]:
    MARKET_PRICES_DIR.mkdir(parents=True, exist_ok=True)
    return sorted(MARKET_PRICES_DIR.glob("*.csv"))


def load_proxy_map() -> pd.DataFrame:
    csv_path = safe_find_csv(["real_public_market_proxy_map", "real public market proxy map"])
    if csv_path is None or not csv_path.exists():
        df = pd.DataFrame(columns=["holding_id", "ticker_or_proxy", "use_in_final_risk_module"])
        df.attrs["warning"] = "Proxy map not available."
        return df
    return read_csv_table("real_public_market_proxy_map")


def get_proxy_tickers() -> list[str]:
    proxy_df = load_proxy_map()
    if proxy_df.empty or "ticker_or_proxy" not in proxy_df.columns:
        return []
    working_df = proxy_df.copy()
    if "use_in_final_risk_module" in working_df.columns:
        working_df = working_df[working_df["use_in_final_risk_module"].fillna(False)]
    tickers = (
        working_df["ticker_or_proxy"]
        .dropna()
        .astype(str)
        .str.strip()
        .loc[lambda series: series != ""]
        .drop_duplicates()
        .tolist()
    )
    return sorted(tickers)


def _coverage_metadata(price_df: pd.DataFrame, expected_tickers: list[str]) -> dict[str, Any]:
    available_tickers = sorted(price_df["ticker"].dropna().astype(str).unique().tolist()) if not price_df.empty else []
    expected_set = set(expected_tickers)
    available_set = set(available_tickers)
    matched_tickers = sorted(expected_set & available_set)
    missing_tickers = sorted(expected_set - available_set)
    coverage_ratio = (len(matched_tickers) / len(expected_set)) if expected_set else 0.0
    return {
        "expected_tickers": expected_tickers,
        "matched_tickers": matched_tickers,
        "missing_tickers": missing_tickers,
        "coverage_ratio": coverage_ratio,
    }


def _normalize_yahoo_ticker(ticker: str) -> str:
    if "." not in ticker:
        return ticker
    prefix, suffix = ticker.rsplit(".", 1)
    if prefix.isdigit():
        return ticker
    if suffix.isalpha() and len(suffix) <= 2:
        return f"{prefix}-{suffix}"
    return ticker


def _normalize_long_price_columns(df: pd.DataFrame) -> pd.DataFrame:
    rename_map = {}
    for column in df.columns:
        lower = column.casefold()
        if lower == "date":
            rename_map[column] = "date"
        elif lower == "ticker":
            rename_map[column] = "ticker"
        elif lower == "close":
            rename_map[column] = "close"
        elif lower == "close_price":
            rename_map[column] = "close"
    df = df.rename(columns=rename_map)
    return df


def _normalize_price_file(df: pd.DataFrame, source_name: str) -> pd.DataFrame:
    df = _normalize_long_price_columns(df)
    columns_lower = {column.casefold(): column for column in df.columns}

    if {"date", "ticker", "close"}.issubset(df.columns):
        normalized = df[["date", "ticker", "close"]].copy()
    else:
        date_column = columns_lower.get("date")
        if date_column is None:
            raise ValueError(f"Price file '{source_name}' is missing a date column.")
        wide_df = df.copy()
        value_columns = [column for column in wide_df.columns if column != date_column]
        normalized = wide_df.melt(
            id_vars=[date_column],
            value_vars=value_columns,
            var_name="ticker",
            value_name="close",
        ).rename(columns={date_column: "date"})

    normalized["date"] = pd.to_datetime(normalized["date"], errors="coerce")
    normalized["close"] = pd.to_numeric(normalized["close"], errors="coerce")
    normalized["ticker"] = normalized["ticker"].astype(str).str.strip()
    normalized = normalized.dropna(subset=["date", "ticker", "close"])
    return normalized[["date", "ticker", "close"]]


def _build_metadata(price_df: pd.DataFrame, data_source: str, source_files: list[str]) -> dict[str, Any]:
    if price_df.empty:
        return {
            "data_source": data_source,
            "source_files": source_files,
            "tickers": [],
            "start_date": None,
            "end_date": None,
        }
    return {
        "data_source": data_source,
        "source_files": source_files,
        "tickers": sorted(price_df["ticker"].dropna().astype(str).unique().tolist()),
        "start_date": price_df["date"].min().strftime("%Y-%m-%d"),
        "end_date": price_df["date"].max().strftime("%Y-%m-%d"),
    }


def load_real_market_prices() -> dict[str, Any]:
    files = list_market_price_files()
    if not files:
        empty = pd.DataFrame(columns=["date", "ticker", "close"])
        return {
            "prices": empty,
            "metadata": {
                **_build_metadata(empty, "real", []),
                **_coverage_metadata(empty, get_proxy_tickers()),
            },
        }

    frames = []
    for path in files:
        raw_df = pd.read_csv(path)
        frames.append(_normalize_price_file(raw_df, path.name))
    prices = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=["date", "ticker", "close"])
    prices = prices.drop_duplicates(subset=["date", "ticker"]).sort_values(["ticker", "date"])
    metadata = _build_metadata(prices, "real", [path.name for path in files])
    metadata.update(_coverage_metadata(prices, get_proxy_tickers()))
    return {"prices": prices, "metadata": metadata}


def load_synthetic_public_prices() -> dict[str, Any]:
    csv_path = safe_find_csv(["public_monthly_prices_synthetic", "public monthly prices synthetic"])
    if csv_path is None or not csv_path.exists():
        empty = pd.DataFrame(columns=["date", "ticker", "close"])
        return {
            "prices": empty,
            "metadata": {
                **_build_metadata(empty, "synthetic", []),
                **_coverage_metadata(empty, get_proxy_tickers()),
            },
        }
    df = read_csv_table("public_monthly_prices_synthetic")
    prices = _normalize_price_file(df, csv_path.name)
    metadata = _build_metadata(prices, "synthetic", [csv_path.name])
    metadata.update(_coverage_metadata(prices, get_proxy_tickers()))
    return {"prices": prices, "metadata": metadata}


def load_market_prices(prefer_real: bool = True, minimum_real_coverage: float = 0.8) -> dict[str, Any]:
    real = load_real_market_prices()
    synthetic = load_synthetic_public_prices()

    if prefer_real and not real["prices"].empty and real["metadata"].get("coverage_ratio", 0.0) >= minimum_real_coverage:
        return real
    if not synthetic["prices"].empty:
        return synthetic
    if not real["prices"].empty:
        return real

    return {
        "prices": pd.DataFrame(columns=["date", "ticker", "close"]),
        "metadata": {
            "data_source": "synthetic" if not prefer_real else "real",
            "source_files": [],
            "tickers": [],
            "start_date": None,
            "end_date": None,
            "coverage_ratio": 0.0,
        },
    }


def fetch_market_prices_from_yfinance(
    tickers: list[str] | None = None,
    start_date: str = "2020-01-01",
    end_date: str | None = None,
    interval: str = "1mo",
    output_filename: str = "yfinance_monthly_prices.csv",
    max_retries: int = 3,
) -> dict[str, Any]:
    try:
        import yfinance as yf
    except ImportError as exc:
        raise ImportError(
            "yfinance is not installed. Install it with `pip install yfinance` before fetching real market data."
        ) from exc

    ticker_list = tickers or get_proxy_tickers()
    if not ticker_list:
        empty = pd.DataFrame(columns=["date", "ticker", "close"])
        return {
            "prices": empty,
            "metadata": {
                **_build_metadata(empty, "real", []),
                "provider": "yfinance",
                "failed_tickers": [],
            },
            "output_path": None,
        }

    MARKET_PRICES_DIR.mkdir(parents=True, exist_ok=True)
    frames: list[pd.DataFrame] = []
    failed_tickers: list[str] = []
    download_timestamp = pd.Timestamp.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

    for ticker in ticker_list:
        requested_ticker = ticker
        provider_ticker = _normalize_yahoo_ticker(ticker)
        history = pd.DataFrame()
        for attempt in range(max_retries):
            try:
                history = yf.Ticker(provider_ticker).history(
                    start=start_date,
                    end=end_date,
                    interval=interval,
                    auto_adjust=True,
                    actions=False,
                )
            except Exception:
                history = pd.DataFrame()
            if not history.empty and "Close" in history.columns:
                break
            if attempt < max_retries - 1:
                time.sleep(1.0)
        if history.empty or "Close" not in history.columns:
            failed_tickers.append(requested_ticker)
            continue
        history = history.reset_index()
        date_column = "Date" if "Date" in history.columns else "date"
        normalized = history[[date_column, "Close"]].rename(columns={date_column: "date", "Close": "close"})
        normalized["ticker"] = requested_ticker
        normalized["provider"] = "yfinance"
        normalized["downloaded_at"] = download_timestamp
        frames.append(normalized[["date", "ticker", "close", "provider", "downloaded_at"]])

    prices = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=["date", "ticker", "close", "provider", "downloaded_at"])
    if not prices.empty:
        prices["date"] = pd.to_datetime(prices["date"], errors="coerce")
        prices["close"] = pd.to_numeric(prices["close"], errors="coerce")
        prices = prices.dropna(subset=["date", "ticker", "close"]).drop_duplicates(subset=["date", "ticker"]).sort_values(["ticker", "date"])
        prices["date"] = prices["date"].dt.strftime("%Y-%m-%d")

    output_path = MARKET_PRICES_DIR / output_filename
    normalized_prices = (
        _normalize_price_file(prices[["date", "ticker", "close"]].copy(), output_filename)
        if not prices.empty
        else pd.DataFrame(columns=["date", "ticker", "close"])
    )
    metadata = _build_metadata(normalized_prices, "real", [output_path.name])
    metadata.update(_coverage_metadata(normalized_prices, ticker_list))
    metadata["provider"] = "yfinance"
    metadata["failed_tickers"] = failed_tickers
    metadata["requested_tickers"] = ticker_list

    retained_existing_output = False
    if output_path.exists():
        existing_df = pd.read_csv(output_path)
        existing_normalized = _normalize_price_file(existing_df, output_path.name)
        existing_coverage = _coverage_metadata(existing_normalized, ticker_list).get("coverage_ratio", 0.0)
        if existing_coverage > metadata.get("coverage_ratio", 0.0):
            retained_existing_output = True
            normalized_prices = existing_normalized
            metadata = _build_metadata(existing_normalized, "real", [output_path.name])
            metadata.update(_coverage_metadata(existing_normalized, ticker_list))
            metadata["provider"] = "yfinance"
            metadata["failed_tickers"] = failed_tickers
            metadata["requested_tickers"] = ticker_list
    if not retained_existing_output:
        prices.to_csv(output_path, index=False)
    metadata["retained_existing_output"] = retained_existing_output

    return {
        "prices": prices if not retained_existing_output else pd.read_csv(output_path),
        "metadata": metadata,
        "output_path": output_path,
    }
