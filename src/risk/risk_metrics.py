from __future__ import annotations

from typing import Any

import pandas as pd


def calculate_returns(price_df: pd.DataFrame, frequency: str = "monthly") -> pd.DataFrame:
    _ = frequency
    if price_df.empty:
        return pd.DataFrame(columns=["date", "ticker", "return"])
    sorted_df = price_df.sort_values(["ticker", "date"]).copy()
    sorted_df["return"] = sorted_df.groupby("ticker")["close"].pct_change()
    return sorted_df.dropna(subset=["return"])[["date", "ticker", "return"]]


def calculate_annualized_volatility(return_df: pd.DataFrame) -> pd.DataFrame:
    if return_df.empty:
        return pd.DataFrame(columns=["ticker", "annualized_volatility"])
    vol = (
        return_df.groupby("ticker")["return"]
        .std()
        .mul(12**0.5)
        .reset_index(name="annualized_volatility")
        .sort_values("annualized_volatility", ascending=False)
    )
    return vol


def calculate_max_drawdown(price_df: pd.DataFrame) -> pd.DataFrame:
    if price_df.empty:
        return pd.DataFrame(columns=["ticker", "max_drawdown"])
    frames = []
    for ticker, group in price_df.sort_values("date").groupby("ticker"):
        running_max = group["close"].cummax()
        drawdown = group["close"] / running_max - 1
        frames.append({"ticker": ticker, "max_drawdown": float(drawdown.min())})
    return pd.DataFrame(frames).sort_values("max_drawdown")


def calculate_correlation_matrix(return_df: pd.DataFrame) -> pd.DataFrame:
    if return_df.empty:
        return pd.DataFrame()
    pivot = return_df.pivot(index="date", columns="ticker", values="return")
    return pivot.corr()


def calculate_rolling_volatility(return_df: pd.DataFrame, window: int = 12) -> pd.DataFrame:
    if return_df.empty:
        return pd.DataFrame(columns=["date", "ticker", "rolling_volatility"])
    pivot = return_df.pivot(index="date", columns="ticker", values="return").sort_index()
    rolling = pivot.rolling(window=window).std() * (12**0.5)
    long_df = rolling.reset_index().melt(id_vars="date", var_name="ticker", value_name="rolling_volatility")
    return long_df.dropna(subset=["rolling_volatility"])


def run_simple_stress_tests(return_df: pd.DataFrame, proxy_map_df: pd.DataFrame | None = None) -> pd.DataFrame:
    if return_df.empty:
        return pd.DataFrame(columns=["scenario", "ticker", "stress_return"])

    proxy_map_df = proxy_map_df if proxy_map_df is not None else pd.DataFrame()
    tickers = sorted(return_df["ticker"].unique().tolist())

    category_map: dict[str, str] = {}
    if not proxy_map_df.empty and {"ticker_or_proxy", "holding_name"}.issubset(proxy_map_df.columns):
        for row in proxy_map_df.itertuples():
            name = str(row.holding_name).casefold()
            ticker = str(row.ticker_or_proxy)
            if "bond" in name or ticker in {"AGG", "TLT", "IGIB", "HYG", "EMB"}:
                category_map[ticker] = "credit"
            elif "hong kong" in name or "china" in name or ticker in {"BABA", "PDD", "JD", "CNYA", "2800.HK", "3067.HK"}:
                category_map[ticker] = "china_equity"
            else:
                category_map[ticker] = "equity"

    rows: list[dict[str, Any]] = []
    for ticker in tickers:
        category = category_map.get(ticker)
        if category is None:
            if ticker in {"AGG", "TLT", "IGIB", "HYG", "EMB"}:
                category = "credit"
            elif ticker in {"BABA", "PDD", "JD", "CNYA", "2800.HK", "3067.HK"}:
                category = "china_equity"
            else:
                category = "equity"

        scenarios = {
            "equity_down_10": -0.10 if category in {"equity", "china_equity"} else -0.03,
            "equity_down_20": -0.20 if category in {"equity", "china_equity"} else -0.05,
            "rates_up_credit_down": -0.08 if category == "credit" else -0.04,
            "china_equity_down_15": -0.15 if category == "china_equity" else -0.02,
            "global_risk_off": -0.12 if category in {"equity", "china_equity"} else -0.06,
        }
        for scenario, shock in scenarios.items():
            rows.append({"scenario": scenario, "ticker": ticker, "stress_return": shock, "exposure_category": category})
    return pd.DataFrame(rows)
