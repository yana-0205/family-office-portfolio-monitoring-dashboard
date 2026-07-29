from __future__ import annotations

import math
from pathlib import Path

import pandas as pd
import streamlit as st


def format_usd_millions(value) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "N/A"
    return f"USD {value:,.1f}m"


def format_percentage(value) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "N/A"
    return f"{value * 100:.1f}%"


def format_multiple(value) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "N/A"
    return f"{value:.2f}x"


def format_days(value) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "N/A"
    return f"{int(round(float(value)))} days"


def format_count(value) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "N/A"
    return f"{int(round(float(value))):,}"


def safe_sum(df: pd.DataFrame, possible_columns: list[str]) -> float:
    if df.empty:
        return 0.0
    for column in possible_columns:
        if column in df.columns:
            return float(pd.to_numeric(df[column], errors="coerce").fillna(0).sum())
    return 0.0


def latest_value_from_timeseries(df: pd.DataFrame, value_column_candidates: list[str]):
    if df.empty:
        return None
    value_column = next((column for column in value_column_candidates if column in df.columns), None)
    if value_column is None:
        return None
    working_df = df.copy()
    if "date" in working_df.columns:
        working_df["date"] = pd.to_datetime(working_df["date"], errors="coerce")
        working_df = working_df.dropna(subset=["date"]).sort_values("date")
    elif "as_of_date" in working_df.columns:
        working_df["as_of_date"] = pd.to_datetime(working_df["as_of_date"], errors="coerce")
        working_df = working_df.dropna(subset=["as_of_date"]).sort_values("as_of_date")
    values = pd.to_numeric(working_df[value_column], errors="coerce").dropna()
    if values.empty:
        return None
    return float(values.iloc[-1])


def metric_card(label, value, help_text=None):
    st.metric(label, value, help=help_text)


def metric_with_delta(label, value, delta=None, help_text=None):
    st.metric(label, value, delta=delta, help=help_text)


def section_header(title, subtitle=None):
    st.subheader(title)
    if subtitle:
        st.caption(subtitle)


def empty_state(message: str, hint: str | None = None):
    normalized_message = message.strip()
    if normalized_message and normalized_message[-1] not in ".!?":
        normalized_message = f"{normalized_message}."
    final_message = normalized_message
    if hint:
        final_message = f"{normalized_message}\n\n{hint.strip()}"
    st.info(final_message)


def dataframe_with_empty_state(df: pd.DataFrame, empty_message: str):
    if df.empty:
        source_warning = df.attrs.get("warning")
        if source_warning and source_warning != empty_message:
            empty_state(
                empty_message,
                f"Source detail: {source_warning}",
            )
        else:
            empty_state(
                empty_message,
                "This section is optional in the current demo state. If needed, rerun the relevant upstream step to repopulate it.",
            )
    else:
        st.dataframe(df, use_container_width=True)


def format_display_dataframe(
    df: pd.DataFrame,
    *,
    money_columns: list[str] | None = None,
    pct_columns: list[str] | None = None,
    date_columns: list[str] | None = None,
    multiple_columns: list[str] | None = None,
    day_columns: list[str] | None = None,
    count_columns: list[str] | None = None,
) -> pd.DataFrame:
    if df.empty:
        return df

    display_df = df.copy()
    money_columns = money_columns or []
    pct_columns = pct_columns or []
    date_columns = date_columns or []
    multiple_columns = multiple_columns or []
    day_columns = day_columns or []
    count_columns = count_columns or []

    for column in money_columns:
        if column in display_df.columns:
            display_df[column] = pd.to_numeric(display_df[column], errors="coerce").map(format_usd_millions)
    for column in pct_columns:
        if column in display_df.columns:
            display_df[column] = pd.to_numeric(display_df[column], errors="coerce").map(format_percentage)
    for column in multiple_columns:
        if column in display_df.columns:
            display_df[column] = pd.to_numeric(display_df[column], errors="coerce").map(format_multiple)
    for column in day_columns:
        if column in display_df.columns:
            display_df[column] = pd.to_numeric(display_df[column], errors="coerce").map(format_days)
    for column in count_columns:
        if column in display_df.columns:
            display_df[column] = pd.to_numeric(display_df[column], errors="coerce").map(format_count)
    for column in date_columns:
        if column in display_df.columns:
            converted = pd.to_datetime(display_df[column], errors="coerce")
            display_df[column] = converted.dt.strftime("%Y-%m-%d")
            display_df[column] = display_df[column].where(converted.notna(), "N/A")

    return display_df


def synthetic_data_notice():
    st.info("All family office portfolio data shown here is synthetic and for proof-of-concept use only.")


def pipeline_status_summary(document_status_df: pd.DataFrame):
    if document_status_df.empty or "validation_review_status" not in document_status_df.columns:
        st.warning("Document processing status is unavailable.")
        return
    counts = document_status_df["validation_review_status"].value_counts().to_dict()
    st.write(
        f"Processed {len(document_status_df)} documents: "
        f"{counts.get('approved', 0)} approved, "
        f"{counts.get('needs_review', 0)} needing review, "
        f"{counts.get('rejected', 0)} rejected. "
        "Only approved records flow into the processed portfolio overlay."
    )


def calculate_return_metrics(monthly_summary_df: pd.DataFrame) -> dict:
    if monthly_summary_df.empty or "total_aum_usd_m" not in monthly_summary_df.columns:
        return {
            "monthly_returns_df": pd.DataFrame(),
            "latest_return": None,
            "ytd_return": None,
            "one_year_return": None,
            "trailing_12m_return": None,
            "best_monthly_return": None,
            "worst_monthly_return": None,
        }

    df = monthly_summary_df.copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date", "total_aum_usd_m"]).sort_values("date")
    df["monthly_return"] = df["total_aum_usd_m"].pct_change()
    monthly_returns = df.dropna(subset=["monthly_return"]).copy()

    latest_date = df["date"].max()
    latest_value = df.iloc[-1]["total_aum_usd_m"]
    ytd_return = None
    year_rows = df[df["date"].dt.year == latest_date.year]
    if not year_rows.empty and year_rows.iloc[0]["total_aum_usd_m"]:
        ytd_return = latest_value / year_rows.iloc[0]["total_aum_usd_m"] - 1

    one_year_return = None
    if len(df) >= 13 and df.iloc[-13]["total_aum_usd_m"]:
        one_year_return = latest_value / df.iloc[-13]["total_aum_usd_m"] - 1

    return {
        "monthly_returns_df": monthly_returns[["date", "monthly_return", "total_aum_usd_m"]],
        "latest_return": monthly_returns.iloc[-1]["monthly_return"] if not monthly_returns.empty else None,
        "ytd_return": ytd_return,
        "one_year_return": one_year_return,
        "trailing_12m_return": one_year_return,
        "best_monthly_return": monthly_returns["monthly_return"].max() if not monthly_returns.empty else None,
        "worst_monthly_return": monthly_returns["monthly_return"].min() if not monthly_returns.empty else None,
    }


def calculate_portfolio_summary_metrics(
    monthly_summary_df: pd.DataFrame,
    positions_df: pd.DataFrame,
    cash_df: pd.DataFrame,
    document_status_df: pd.DataFrame,
) -> dict:
    return_metrics = calculate_return_metrics(monthly_summary_df)
    total_aum = None
    public_market_value = None
    private_fund_nav = None
    cash_liquidity = None
    if not monthly_summary_df.empty:
        latest_df = monthly_summary_df.copy()
        latest_df["date"] = pd.to_datetime(latest_df["date"], errors="coerce")
        latest = latest_df.dropna(subset=["date"]).sort_values("date").iloc[-1]
        total_aum = latest.get("total_aum_usd_m")
        public_market_value = latest.get("public_markets_usd_m")
        private_fund_nav = latest.get("closed_end_private_fund_nav_usd_m")
        cash_liquidity = latest.get("cash_liquidity_usd_m")

    tracked_processed_assets = safe_sum(positions_df, ["current_nav_usd_m"]) + safe_sum(cash_df, ["balance_usd_m"])
    unfunded_commitments = safe_sum(positions_df, ["unfunded_commitment_usd_m"])
    liquidity_coverage = None
    if cash_liquidity not in (None, 0) and unfunded_commitments not in (None, 0):
        liquidity_coverage = cash_liquidity / unfunded_commitments

    counts = document_status_df["validation_review_status"].value_counts().to_dict() if not document_status_df.empty and "validation_review_status" in document_status_df.columns else {}
    return {
        "total_aum": total_aum,
        "tracked_processed_assets": tracked_processed_assets,
        "public_market_value": public_market_value,
        "private_fund_nav": private_fund_nav,
        "cash_liquidity": cash_liquidity if cash_liquidity is not None else safe_sum(cash_df, ["balance_usd_m"]),
        "unfunded_commitments": unfunded_commitments,
        "liquidity_coverage": liquidity_coverage,
        "approved_docs": counts.get("approved", 0),
        "needs_review_docs": counts.get("needs_review", 0),
        "rejected_docs": counts.get("rejected", 0),
        "applied_updates": int(document_status_df.get("update_applied_flag", pd.Series(dtype=bool)).fillna(False).sum())
        if not document_status_df.empty and "update_applied_flag" in document_status_df.columns
        else 0,
        **return_metrics,
    }


def _annualized_return_from_series(return_series: pd.Series) -> float | None:
    clean = pd.to_numeric(return_series, errors="coerce").dropna()
    if clean.empty:
        return None
    total_growth = float((1 + clean).prod())
    periods = len(clean)
    if periods <= 0 or total_growth <= 0:
        return None
    return total_growth ** (12 / periods) - 1


def _annualized_volatility_from_series(return_series: pd.Series) -> float | None:
    clean = pd.to_numeric(return_series, errors="coerce").dropna()
    if len(clean) < 2:
        return None
    return float(clean.std(ddof=1) * math.sqrt(12))


def _max_drawdown_from_value_series(value_series: pd.Series) -> float | None:
    clean = pd.to_numeric(value_series, errors="coerce").dropna()
    if clean.empty:
        return None
    running_peak = clean.cummax()
    drawdown = clean / running_peak - 1
    return float(drawdown.min())


def _extract_risk_free_series(risk_free_df: pd.DataFrame, dates: pd.Series) -> pd.Series:
    if risk_free_df.empty or not {"date", "rf_monthly_return"}.issubset(risk_free_df.columns):
        return pd.Series(dtype=float)
    rf_df = risk_free_df.copy()
    rf_df["date"] = pd.to_datetime(rf_df["date"], errors="coerce")
    rf_df["rf_monthly_return"] = pd.to_numeric(rf_df["rf_monthly_return"], errors="coerce")
    rf_df = rf_df.dropna(subset=["date", "rf_monthly_return"])
    if rf_df.empty:
        return pd.Series(dtype=float)
    merged = pd.DataFrame({"date": dates}).merge(
        rf_df[["date", "rf_monthly_return"]],
        on="date",
        how="left",
    )
    return merged["rf_monthly_return"]


def _sharpe_ratio_from_series(return_series: pd.Series, risk_free_series: pd.Series | None = None) -> float | None:
    clean_returns = pd.to_numeric(return_series, errors="coerce")
    if risk_free_series is not None and not risk_free_series.empty:
        aligned_rf = pd.to_numeric(risk_free_series, errors="coerce")
        excess_returns = (clean_returns - aligned_rf).dropna()
    else:
        excess_returns = clean_returns.dropna()
    if len(excess_returns) < 2:
        return None
    annualized_excess = float(excess_returns.mean() * 12.0)
    annualized_vol = float(excess_returns.std(ddof=1) * math.sqrt(12))
    if annualized_vol == 0:
        return None
    return annualized_excess / annualized_vol


def calculate_return_statistics_table(
    returns_df: pd.DataFrame,
    risk_free_df: pd.DataFrame | None = None,
    date_column: str = "date",
    return_column: str = "monthly_return",
) -> pd.DataFrame:
    if returns_df.empty or not {date_column, return_column}.issubset(returns_df.columns):
        return pd.DataFrame(
            {
                "Metric": ["Annualized Return", "Annualized Volatility", "Largest Drawdown", "Sharpe Ratio"],
                "1 Year": ["N/A"] * 4,
                "3 Years": ["N/A"] * 4,
                "Since Inception": ["N/A"] * 4,
            }
        )

    df = returns_df.copy()
    df[date_column] = pd.to_datetime(df[date_column], errors="coerce")
    df[return_column] = pd.to_numeric(df[return_column], errors="coerce")
    df = df.dropna(subset=[date_column, return_column]).sort_values(date_column)
    if df.empty:
        return pd.DataFrame(
            {
                "Metric": ["Annualized Return", "Annualized Volatility", "Largest Drawdown", "Sharpe Ratio"],
                "1 Year": ["N/A"] * 4,
                "3 Years": ["N/A"] * 4,
                "Since Inception": ["N/A"] * 4,
            }
        )

    df["cumulative_index"] = (1.0 + df[return_column]).cumprod()
    latest_date = df[date_column].max()
    windows = {
        "1 Year": df[df[date_column] >= latest_date - pd.DateOffset(years=1)],
        "3 Years": df[df[date_column] >= latest_date - pd.DateOffset(years=3)],
        "Since Inception": df,
    }

    stats_by_window: dict[str, dict[str, float | None]] = {}
    for label, window_df in windows.items():
        minimum_observations = 12 if label == "1 Year" else 36 if label == "3 Years" else 1
        clean_returns = window_df[return_column].dropna()
        if len(clean_returns) < minimum_observations:
            stats_by_window[label] = {
                "annualized_return": None,
                "annualized_volatility": None,
                "max_drawdown": None,
                "sharpe_ratio": None,
            }
            continue

        rf_series = _extract_risk_free_series(
            risk_free_df if risk_free_df is not None else pd.DataFrame(),
            window_df[date_column],
        )
        stats_by_window[label] = {
            "annualized_return": _annualized_return_from_series(window_df[return_column]),
            "annualized_volatility": _annualized_volatility_from_series(window_df[return_column]),
            "max_drawdown": _max_drawdown_from_value_series(window_df["cumulative_index"]),
            "sharpe_ratio": _sharpe_ratio_from_series(window_df[return_column], rf_series),
        }

    return pd.DataFrame(
        {
            "Metric": ["Annualized Return", "Annualized Volatility", "Largest Drawdown", "Sharpe Ratio"],
            "1 Year": [
                format_percentage(stats_by_window["1 Year"]["annualized_return"]),
                format_percentage(stats_by_window["1 Year"]["annualized_volatility"]),
                format_percentage(stats_by_window["1 Year"]["max_drawdown"]),
                "N/A" if stats_by_window["1 Year"]["sharpe_ratio"] is None else f"{stats_by_window['1 Year']['sharpe_ratio']:.2f}",
            ],
            "3 Years": [
                format_percentage(stats_by_window["3 Years"]["annualized_return"]),
                format_percentage(stats_by_window["3 Years"]["annualized_volatility"]),
                format_percentage(stats_by_window["3 Years"]["max_drawdown"]),
                "N/A" if stats_by_window["3 Years"]["sharpe_ratio"] is None else f"{stats_by_window['3 Years']['sharpe_ratio']:.2f}",
            ],
            "Since Inception": [
                format_percentage(stats_by_window["Since Inception"]["annualized_return"]),
                format_percentage(stats_by_window["Since Inception"]["annualized_volatility"]),
                format_percentage(stats_by_window["Since Inception"]["max_drawdown"]),
                "N/A" if stats_by_window["Since Inception"]["sharpe_ratio"] is None else f"{stats_by_window['Since Inception']['sharpe_ratio']:.2f}",
            ],
        }
    )


def calculate_public_market_summary(
    public_holdings_df: pd.DataFrame,
    monthly_summary_df: pd.DataFrame,
    public_prices_df: pd.DataFrame,
    proxy_map_df: pd.DataFrame,
) -> dict[str, object]:
    total_aum = latest_value_from_timeseries(monthly_summary_df, ["total_aum_usd_m"])
    summary: dict[str, object] = {
        "total_public_value": safe_sum(public_holdings_df, ["final_value_usd_m"]),
        "public_weight": None,
        "long_exposure": None,
        "short_exposure": None,
        "gross_exposure": None,
        "net_exposure": None,
        "largest_long_name": None,
        "largest_long_value": None,
        "largest_short_name": None,
        "largest_short_value": None,
        "coverage_ratio": None,
        "last_price_date": None,
        "proxy_tickers": 0,
        "real_price_start_date": None,
        "real_price_end_date": None,
    }
    if total_aum not in (None, 0):
        summary["public_weight"] = summary["total_public_value"] / total_aum

    holdings_df = public_holdings_df.copy()
    if holdings_df.empty:
        return summary

    exposure_source = None
    for candidate in [
        "current_delta_adjusted_exposure_usd_m",
        "current_exposure_usd_m",
        "final_value_usd_m",
    ]:
        if candidate in holdings_df.columns:
            exposure_source = candidate
            break
    if exposure_source is None:
        return summary

    holdings_df["signed_exposure_usd_m"] = pd.to_numeric(holdings_df[exposure_source], errors="coerce")
    if "position_side_current" in holdings_df.columns:
        short_mask = holdings_df["position_side_current"].astype(str).str.casefold().eq("short")
        holdings_df.loc[short_mask, "signed_exposure_usd_m"] = -holdings_df.loc[short_mask, "signed_exposure_usd_m"].abs()
        holdings_df.loc[~short_mask, "signed_exposure_usd_m"] = holdings_df.loc[~short_mask, "signed_exposure_usd_m"].abs()
    holdings_df = holdings_df.dropna(subset=["signed_exposure_usd_m"])

    long_exposure_usd_m = float(holdings_df.loc[holdings_df["signed_exposure_usd_m"] > 0, "signed_exposure_usd_m"].sum())
    short_exposure_usd_m = float(holdings_df.loc[holdings_df["signed_exposure_usd_m"] < 0, "signed_exposure_usd_m"].sum())
    net_exposure_usd_m = float(holdings_df["signed_exposure_usd_m"].sum())
    gross_exposure_usd_m = float(holdings_df["signed_exposure_usd_m"].abs().sum())

    if total_aum not in (None, 0):
        summary["long_exposure"] = long_exposure_usd_m / total_aum
        summary["short_exposure"] = short_exposure_usd_m / total_aum
        summary["gross_exposure"] = gross_exposure_usd_m / total_aum
        summary["net_exposure"] = net_exposure_usd_m / total_aum

    long_holdings = holdings_df.loc[holdings_df["signed_exposure_usd_m"] > 0].sort_values("signed_exposure_usd_m", ascending=False)
    short_holdings = holdings_df.loc[holdings_df["signed_exposure_usd_m"] < 0].sort_values("signed_exposure_usd_m")
    if not long_holdings.empty:
        top_long = long_holdings.iloc[0]
        summary["largest_long_name"] = top_long.get("holding_name")
        summary["largest_long_value"] = (
            float(top_long["signed_exposure_usd_m"]) / total_aum if total_aum not in (None, 0) else float(top_long["signed_exposure_usd_m"])
        )
    if not short_holdings.empty:
        top_short = short_holdings.iloc[0]
        summary["largest_short_name"] = top_short.get("holding_name")
        summary["largest_short_value"] = (
            float(top_short["signed_exposure_usd_m"]) / total_aum if total_aum not in (None, 0) else float(top_short["signed_exposure_usd_m"])
        )

    if not public_prices_df.empty and {"date", "ticker", "close"}.issubset(public_prices_df.columns):
        prices_df = public_prices_df.copy()
        prices_df["date"] = pd.to_datetime(prices_df["date"], errors="coerce")
        prices_df = prices_df.dropna(subset=["date", "ticker", "close"])
        if not prices_df.empty:
            summary["last_price_date"] = prices_df["date"].max()
            summary["real_price_start_date"] = prices_df["date"].min()
            summary["real_price_end_date"] = prices_df["date"].max()
            available_tickers = set(prices_df["ticker"].astype(str).unique().tolist())
            expected_tickers = (
                set(proxy_map_df["ticker_or_proxy"].dropna().astype(str).unique().tolist())
                if not proxy_map_df.empty and "ticker_or_proxy" in proxy_map_df.columns
                else available_tickers
            )
            summary["proxy_tickers"] = len(available_tickers)
            summary["coverage_ratio"] = (len(available_tickers & expected_tickers) / len(expected_tickers)) if expected_tickers else None

    return summary


def prepare_public_risk_overlay(
    public_holdings_df: pd.DataFrame,
    proxy_map_df: pd.DataFrame,
    risk_metrics_df: pd.DataFrame,
    monthly_summary_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    overlay_df = public_holdings_df.copy()
    if overlay_df.empty:
        return overlay_df

    if not proxy_map_df.empty and {"holding_id", "ticker_or_proxy"}.issubset(proxy_map_df.columns) and "holding_id" in overlay_df.columns:
        map_columns = [
            column
            for column in [
                "holding_id",
                "ticker_or_proxy",
                "proxy_name",
                "risk_proxy_bucket",
                "region_taxonomy",
                "liquidity_bucket",
                "mapping_confidence",
                "mapping_method",
                "use_in_final_risk_module",
            ]
            if column in proxy_map_df.columns
        ]
        overlay_df = overlay_df.merge(proxy_map_df[map_columns].drop_duplicates(), on="holding_id", how="left")
        overlay_df["proxy_ticker"] = overlay_df["ticker_or_proxy"].fillna(overlay_df.get("ticker"))
    else:
        overlay_df["proxy_ticker"] = overlay_df.get("ticker")

    exposure_source = next(
        (
            column
            for column in [
                "current_delta_adjusted_exposure_usd_m",
                "current_exposure_usd_m",
                "final_value_usd_m",
            ]
            if column in overlay_df.columns
        ),
        None,
    )
    if exposure_source is None:
        return pd.DataFrame()

    overlay_df["signed_exposure_usd_m"] = pd.to_numeric(overlay_df[exposure_source], errors="coerce")
    if "position_side_current" in overlay_df.columns:
        short_mask = overlay_df["position_side_current"].astype(str).str.casefold().eq("short")
        overlay_df.loc[short_mask, "signed_exposure_usd_m"] = -overlay_df.loc[short_mask, "signed_exposure_usd_m"].abs()
        overlay_df.loc[~short_mask, "signed_exposure_usd_m"] = overlay_df.loc[~short_mask, "signed_exposure_usd_m"].abs()
    overlay_df["abs_signed_exposure_usd_m"] = overlay_df["signed_exposure_usd_m"].abs()
    overlay_df = overlay_df.dropna(subset=["signed_exposure_usd_m"])
    if overlay_df.empty:
        return overlay_df

    if not risk_metrics_df.empty and "ticker" in risk_metrics_df.columns:
        metric_columns = [
            column
            for column in ["ticker", "annualized_volatility", "max_drawdown", "data_source", "start_date", "end_date"]
            if column in risk_metrics_df.columns
        ]
        overlay_df = overlay_df.merge(
            risk_metrics_df[metric_columns].rename(columns={"ticker": "proxy_ticker"}),
            on="proxy_ticker",
            how="left",
        )

    total_aum_source = monthly_summary_df if monthly_summary_df is not None else pd.DataFrame()
    total_aum = latest_value_from_timeseries(total_aum_source, ["total_aum_usd_m"])
    if total_aum not in (None, 0):
        overlay_df["exposure_pct_nav"] = overlay_df["signed_exposure_usd_m"] / total_aum
        overlay_df["gross_exposure_pct_nav"] = overlay_df["abs_signed_exposure_usd_m"] / total_aum

    return overlay_df


def build_risk_dimension_summary(
    overlay_df: pd.DataFrame,
    dimension_column: str,
    label: str,
) -> pd.DataFrame:
    required_columns = {dimension_column, "signed_exposure_usd_m", "abs_signed_exposure_usd_m"}
    if overlay_df.empty or not required_columns.issubset(overlay_df.columns):
        return pd.DataFrame()

    working_df = overlay_df.copy()
    working_df[dimension_column] = working_df[dimension_column].fillna("Unknown").astype(str).str.strip()
    working_df = working_df[working_df[dimension_column] != ""].copy()
    if working_df.empty:
        return pd.DataFrame()

    def _weighted_average(frame: pd.DataFrame, value_column: str) -> float | None:
        if value_column not in frame.columns:
            return None
        values = pd.to_numeric(frame[value_column], errors="coerce")
        weights = pd.to_numeric(frame["abs_signed_exposure_usd_m"], errors="coerce")
        valid = values.notna() & weights.notna() & (weights > 0)
        if not valid.any():
            return None
        return float((values[valid] * weights[valid]).sum() / weights[valid].sum())

    rows: list[dict[str, object]] = []
    for category, frame in working_df.groupby(dimension_column):
        rows.append(
            {
                label: category,
                "Signed Exposure (USD m)": float(frame["signed_exposure_usd_m"].sum()),
                "Gross Exposure (USD m)": float(frame["abs_signed_exposure_usd_m"].sum()),
                "Exposure % NAV": float(frame["exposure_pct_nav"].sum()) if "exposure_pct_nav" in frame.columns else None,
                "Gross Exposure % NAV": float(frame["gross_exposure_pct_nav"].sum()) if "gross_exposure_pct_nav" in frame.columns else None,
                "Exposure-Weighted Volatility": _weighted_average(frame, "annualized_volatility"),
                "Exposure-Weighted Drawdown": _weighted_average(frame, "max_drawdown"),
                "Proxy Count": int(frame["proxy_ticker"].dropna().astype(str).nunique()) if "proxy_ticker" in frame.columns else 0,
            }
        )

    summary_df = pd.DataFrame(rows)
    if summary_df.empty:
        return summary_df
    return summary_df.sort_values("Gross Exposure (USD m)", ascending=False)


def build_stress_impact_tables(
    overlay_df: pd.DataFrame,
    stress_df: pd.DataFrame,
    monthly_summary_df: pd.DataFrame | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    required_overlay = {"proxy_ticker", "holding_name", "signed_exposure_usd_m"}
    required_stress = {"scenario", "ticker", "stress_return"}
    if overlay_df.empty or stress_df.empty or not required_overlay.issubset(overlay_df.columns) or not required_stress.issubset(stress_df.columns):
        return pd.DataFrame(), pd.DataFrame()

    total_aum_source = monthly_summary_df if monthly_summary_df is not None else pd.DataFrame()
    total_aum = latest_value_from_timeseries(total_aum_source, ["total_aum_usd_m"])
    detail_df = overlay_df.merge(
        stress_df.rename(columns={"ticker": "proxy_ticker"}),
        on="proxy_ticker",
        how="inner",
    )
    if detail_df.empty:
        return pd.DataFrame(), pd.DataFrame()

    detail_df["stress_return"] = pd.to_numeric(detail_df["stress_return"], errors="coerce")
    detail_df["signed_exposure_usd_m"] = pd.to_numeric(detail_df["signed_exposure_usd_m"], errors="coerce")
    detail_df = detail_df.dropna(subset=["stress_return", "signed_exposure_usd_m"])
    if detail_df.empty:
        return pd.DataFrame(), pd.DataFrame()

    detail_df["scenario_pnl_usd_m"] = detail_df["signed_exposure_usd_m"] * detail_df["stress_return"]
    if total_aum not in (None, 0):
        detail_df["scenario_impact_pct_nav"] = detail_df["scenario_pnl_usd_m"] / total_aum

    summary_rows: list[dict[str, object]] = []
    for scenario, frame in detail_df.groupby("scenario"):
        summary_rows.append(
            {
                "scenario": scenario,
                "scenario_pnl_usd_m": float(frame["scenario_pnl_usd_m"].sum()),
                "scenario_impact_pct_nav": float(frame["scenario_impact_pct_nav"].sum()) if "scenario_impact_pct_nav" in frame.columns else None,
                "proxy_count": int(frame["proxy_ticker"].dropna().astype(str).nunique()),
                "exposure_categories": int(frame["exposure_category"].dropna().astype(str).nunique()) if "exposure_category" in frame.columns else 0,
            }
        )
    summary_df = pd.DataFrame(summary_rows).sort_values("scenario_pnl_usd_m")
    detail_df = detail_df.sort_values(["scenario", "scenario_pnl_usd_m"])
    return summary_df, detail_df


def build_top_correlation_pairs(correlation_df: pd.DataFrame, limit: int = 15) -> pd.DataFrame:
    if correlation_df.empty:
        return pd.DataFrame()

    working_df = correlation_df.copy()
    if "ticker" in working_df.columns:
        working_df = working_df.set_index("ticker")
    if working_df.empty:
        return pd.DataFrame()

    working_df = working_df.apply(pd.to_numeric, errors="coerce")
    pairs: list[dict[str, object]] = []
    tickers = list(working_df.index)
    for i, left in enumerate(tickers):
        for right in tickers[i + 1 :]:
            if right not in working_df.columns:
                continue
            corr_value = working_df.at[left, right] if left in working_df.index else None
            if pd.isna(corr_value):
                continue
            pairs.append(
                {
                    "Ticker 1": left,
                    "Ticker 2": right,
                    "Correlation": float(corr_value),
                    "Abs Correlation": abs(float(corr_value)),
                }
            )
    if not pairs:
        return pd.DataFrame()

    pairs_df = pd.DataFrame(pairs).sort_values("Abs Correlation", ascending=False).head(limit)
    return pairs_df.drop(columns=["Abs Correlation"])


def build_public_proxy_basket_history(
    public_holdings_df: pd.DataFrame,
    public_prices_df: pd.DataFrame,
    proxy_map_df: pd.DataFrame,
) -> pd.DataFrame:
    required_price_columns = {"date", "ticker", "close"}
    if public_holdings_df.empty or public_prices_df.empty or not required_price_columns.issubset(public_prices_df.columns):
        return pd.DataFrame(columns=["date", "monthly_return", "cumulative_index", "drawdown"])

    holdings_df = public_holdings_df.copy()
    if "holding_id" not in holdings_df.columns:
        return pd.DataFrame(columns=["date", "monthly_return", "cumulative_index", "drawdown"])

    proxy_lookup = proxy_map_df[["holding_id", "ticker_or_proxy"]].copy() if not proxy_map_df.empty and {"holding_id", "ticker_or_proxy"}.issubset(proxy_map_df.columns) else pd.DataFrame(columns=["holding_id", "ticker_or_proxy"])
    holdings_df = holdings_df.merge(proxy_lookup, on="holding_id", how="left")
    holdings_df["proxy_ticker"] = holdings_df["ticker_or_proxy"].fillna(holdings_df.get("ticker"))
    holdings_df["proxy_ticker"] = holdings_df["proxy_ticker"].astype(str).str.strip()
    holdings_df = holdings_df[holdings_df["proxy_ticker"] != ""].copy()
    if holdings_df.empty:
        return pd.DataFrame(columns=["date", "monthly_return", "cumulative_index", "drawdown"])

    exposure_source = None
    for candidate in [
        "current_delta_adjusted_exposure_usd_m",
        "current_exposure_usd_m",
        "final_value_usd_m",
    ]:
        if candidate in holdings_df.columns:
            exposure_source = candidate
            break
    if exposure_source is None:
        return pd.DataFrame(columns=["date", "monthly_return", "cumulative_index", "drawdown"])

    holdings_df["signed_exposure_usd_m"] = pd.to_numeric(holdings_df[exposure_source], errors="coerce")
    if "position_side_current" in holdings_df.columns:
        short_mask = holdings_df["position_side_current"].astype(str).str.casefold().eq("short")
        holdings_df.loc[short_mask, "signed_exposure_usd_m"] = -holdings_df.loc[short_mask, "signed_exposure_usd_m"].abs()
        holdings_df.loc[~short_mask, "signed_exposure_usd_m"] = holdings_df.loc[~short_mask, "signed_exposure_usd_m"].abs()
    holdings_df = holdings_df.dropna(subset=["signed_exposure_usd_m"])
    if holdings_df.empty:
        return pd.DataFrame(columns=["date", "monthly_return", "cumulative_index", "drawdown"])

    basket_weights = (
        holdings_df.groupby("proxy_ticker", as_index=False)["signed_exposure_usd_m"]
        .sum()
        .rename(columns={"proxy_ticker": "ticker"})
    )
    gross_exposure = float(basket_weights["signed_exposure_usd_m"].abs().sum())
    if gross_exposure == 0:
        return pd.DataFrame(columns=["date", "monthly_return", "cumulative_index", "drawdown"])
    basket_weights["weight"] = basket_weights["signed_exposure_usd_m"] / gross_exposure

    prices_df = public_prices_df.copy()
    prices_df["date"] = pd.to_datetime(prices_df["date"], errors="coerce")
    prices_df["close"] = pd.to_numeric(prices_df["close"], errors="coerce")
    prices_df = prices_df.dropna(subset=["date", "ticker", "close"]).sort_values(["ticker", "date"])
    prices_df["monthly_return"] = prices_df.groupby("ticker")["close"].pct_change()
    prices_df = prices_df.dropna(subset=["monthly_return"])
    if prices_df.empty:
        return pd.DataFrame(columns=["date", "monthly_return", "cumulative_index", "drawdown"])

    basket_df = prices_df.merge(basket_weights[["ticker", "weight"]], on="ticker", how="inner")
    if basket_df.empty:
        return pd.DataFrame(columns=["date", "monthly_return", "cumulative_index", "drawdown"])

    basket_df["weighted_return"] = basket_df["monthly_return"] * basket_df["weight"]
    monthly_df = basket_df.groupby("date", as_index=False)["weighted_return"].sum().rename(columns={"weighted_return": "monthly_return"})
    monthly_df = monthly_df.sort_values("date")
    monthly_df["cumulative_index"] = (1.0 + monthly_df["monthly_return"]).cumprod()
    monthly_df["running_peak"] = monthly_df["cumulative_index"].cummax()
    monthly_df["drawdown"] = monthly_df["cumulative_index"] / monthly_df["running_peak"] - 1.0
    return monthly_df[["date", "monthly_return", "cumulative_index", "drawdown"]]


def _build_period_stats(df: pd.DataFrame, risk_free_df: pd.DataFrame | None = None) -> dict[str, float | None]:
    if df.empty or "total_aum_usd_m" not in df.columns:
        return {
            "annualized_return": None,
            "annualized_volatility": None,
            "max_drawdown": None,
            "sharpe_ratio": None,
        }
    working_df = df.copy()
    working_df["total_aum_usd_m"] = pd.to_numeric(working_df["total_aum_usd_m"], errors="coerce")
    working_df = working_df.dropna(subset=["total_aum_usd_m"])
    if working_df.empty:
        return {
            "annualized_return": None,
            "annualized_volatility": None,
            "max_drawdown": None,
            "sharpe_ratio": None,
        }
    return_series = working_df["total_aum_usd_m"].pct_change().dropna()
    risk_free_series = _extract_risk_free_series(
        risk_free_df if risk_free_df is not None else pd.DataFrame(),
        working_df.loc[return_series.index, "date"] if "date" in working_df.columns else pd.Series(dtype="datetime64[ns]"),
    )
    return {
        "annualized_return": _annualized_return_from_series(return_series),
        "annualized_volatility": _annualized_volatility_from_series(return_series),
        "max_drawdown": _max_drawdown_from_value_series(working_df["total_aum_usd_m"]),
        "sharpe_ratio": _sharpe_ratio_from_series(return_series, risk_free_series),
    }


def calculate_performance_statistics_table(
    monthly_summary_df: pd.DataFrame,
    risk_free_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    if monthly_summary_df.empty or not {"date", "total_aum_usd_m"}.issubset(monthly_summary_df.columns):
        return pd.DataFrame(
            {
                "Metric": ["Annualized Return", "Annualized Volatility", "Largest Drawdown", "Sharpe Ratio"],
                "1 Year": ["N/A"] * 4,
                "3 Years": ["N/A"] * 4,
                "Since Inception": ["N/A"] * 4,
            }
        )

    df = monthly_summary_df.copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"]).sort_values("date")
    latest_date = df["date"].max()

    windows = {
        "1 Year": df[df["date"] >= latest_date - pd.DateOffset(years=1)],
        "3 Years": df[df["date"] >= latest_date - pd.DateOffset(years=3)],
        "Since Inception": df,
    }

    stats_by_window: dict[str, dict[str, float | None]] = {}
    for label, window_df in windows.items():
        minimum_points = 13 if label == "1 Year" else 37 if label == "3 Years" else 2
        if len(window_df) < minimum_points:
            stats_by_window[label] = {
                "annualized_return": None,
                "annualized_volatility": None,
                "max_drawdown": None,
                "sharpe_ratio": None,
            }
        else:
            stats_by_window[label] = _build_period_stats(window_df, risk_free_df=risk_free_df)

    return pd.DataFrame(
        {
            "Metric": ["Annualized Return", "Annualized Volatility", "Largest Drawdown", "Sharpe Ratio"],
            "1 Year": [
                format_percentage(stats_by_window["1 Year"]["annualized_return"]),
                format_percentage(stats_by_window["1 Year"]["annualized_volatility"]),
                format_percentage(stats_by_window["1 Year"]["max_drawdown"]),
                "N/A" if stats_by_window["1 Year"]["sharpe_ratio"] is None else f"{stats_by_window['1 Year']['sharpe_ratio']:.2f}",
            ],
            "3 Years": [
                format_percentage(stats_by_window["3 Years"]["annualized_return"]),
                format_percentage(stats_by_window["3 Years"]["annualized_volatility"]),
                format_percentage(stats_by_window["3 Years"]["max_drawdown"]),
                "N/A" if stats_by_window["3 Years"]["sharpe_ratio"] is None else f"{stats_by_window['3 Years']['sharpe_ratio']:.2f}",
            ],
            "Since Inception": [
                format_percentage(stats_by_window["Since Inception"]["annualized_return"]),
                format_percentage(stats_by_window["Since Inception"]["annualized_volatility"]),
                format_percentage(stats_by_window["Since Inception"]["max_drawdown"]),
                "N/A" if stats_by_window["Since Inception"]["sharpe_ratio"] is None else f"{stats_by_window['Since Inception']['sharpe_ratio']:.2f}",
            ],
        }
    )


def calculate_asset_class_metrics(
    allocation_df: pd.DataFrame,
    monthly_by_holding_df: pd.DataFrame | None = None,
) -> dict:
    metrics = {
        "total_value": safe_sum(allocation_df, ["final_value_usd_m", "value_usd_m"]),
        "largest_asset_class": None,
        "largest_asset_class_value": None,
        "liquid_value": 0.0,
        "illiquid_value": 0.0,
    }
    if not allocation_df.empty and {"asset_class", "final_value_usd_m"}.issubset(allocation_df.columns):
        largest = allocation_df.sort_values("final_value_usd_m", ascending=False).iloc[0]
        metrics["largest_asset_class"] = largest.get("asset_class")
        metrics["largest_asset_class_value"] = float(largest.get("final_value_usd_m"))

    if monthly_by_holding_df is not None and not monthly_by_holding_df.empty and "asset_class" in monthly_by_holding_df.columns:
        latest_df = monthly_by_holding_df.copy()
        if "date" in latest_df.columns:
            latest_df["date"] = pd.to_datetime(latest_df["date"], errors="coerce")
            latest_df = latest_df.dropna(subset=["date"]).sort_values("date")
            if not latest_df.empty:
                latest_df = latest_df[latest_df["date"] == latest_df["date"].max()]
        liquid_mask = latest_df["asset_class"].astype(str).str.contains("Public|Cash|Fixed Income|Hedge", case=False, na=False)
        metrics["liquid_value"] = safe_sum(latest_df[liquid_mask], ["value_usd_m"])
        metrics["illiquid_value"] = safe_sum(latest_df[~liquid_mask], ["value_usd_m"])
    return metrics


def calculate_commitment_summary(private_positions_df: pd.DataFrame) -> dict:
    return {
        "private_fund_nav": safe_sum(private_positions_df, ["current_nav_usd_m", "nav_usd_m"]),
        "total_commitments": safe_sum(private_positions_df, ["commitment_usd_m"]),
        "paid_in_capital": safe_sum(private_positions_df, ["paid_in_capital_usd_m"]),
        "unfunded_commitments": safe_sum(private_positions_df, ["unfunded_commitment_usd_m"]),
    }


def calculate_private_market_metrics(private_positions_df: pd.DataFrame, cashflows_df: pd.DataFrame | None = None) -> dict:
    metrics = calculate_commitment_summary(private_positions_df)
    metrics["distributions_this_month"] = 0.0
    metrics["capital_calls_this_month"] = 0.0
    if cashflows_df is None or cashflows_df.empty or "cashflow_date" not in cashflows_df.columns:
        return metrics

    working_df = cashflows_df.copy()
    working_df["cashflow_date"] = pd.to_datetime(working_df["cashflow_date"], errors="coerce")
    working_df = working_df.dropna(subset=["cashflow_date"])
    if working_df.empty:
        return metrics

    latest_period = working_df["cashflow_date"].max().to_period("M")
    latest_df = working_df[working_df["cashflow_date"].dt.to_period("M") == latest_period]
    metrics["distributions_this_month"] = safe_sum(
        latest_df,
        ["expected_cash_inflow_usd_m", "net_distribution_usd_m", "gross_distribution_usd_m"],
    )
    return metrics


def calculate_private_markets_summary(
    private_positions_df: pd.DataFrame,
    private_monthly_df: pd.DataFrame | None = None,
    cashflows_df: pd.DataFrame | None = None,
) -> dict[str, object]:
    summary = calculate_private_market_metrics(
        private_positions_df,
        cashflows_df if cashflows_df is not None else pd.DataFrame(),
    )
    summary.update(
        {
            "fund_count": 0,
            "strategy_count": 0,
            "geography_count": 0,
            "proxy_mapped_fund_count": 0,
            "proxy_mapped_nav": 0.0,
            "funded_ratio": None,
            "nav_to_paid_in_ratio": None,
            "latest_statement_date": None,
            "average_statement_lag_days": None,
            "latest_total_nav": None,
            "trailing_12m_nav_growth": None,
        }
    )
    if private_positions_df.empty:
        return summary

    positions_df = private_positions_df.copy()
    positions_df["current_nav_usd_m"] = pd.to_numeric(positions_df.get("current_nav_usd_m"), errors="coerce")
    positions_df["commitment_usd_m"] = pd.to_numeric(positions_df.get("commitment_usd_m"), errors="coerce")
    positions_df["paid_in_capital_usd_m"] = pd.to_numeric(positions_df.get("paid_in_capital_usd_m"), errors="coerce")
    positions_df["proxy_mapping_flag"] = positions_df.get("proxy_mapping_flag", False).fillna(False)

    summary["fund_count"] = int(positions_df["fund_id"].nunique()) if "fund_id" in positions_df.columns else int(len(positions_df))
    summary["strategy_count"] = int(positions_df["strategy"].dropna().astype(str).nunique()) if "strategy" in positions_df.columns else 0
    summary["geography_count"] = int(positions_df["investment_geography"].dropna().astype(str).nunique()) if "investment_geography" in positions_df.columns else 0
    mapped_df = positions_df[positions_df["proxy_mapping_flag"].astype(bool)]
    summary["proxy_mapped_fund_count"] = int(mapped_df["fund_id"].nunique()) if "fund_id" in mapped_df.columns else int(len(mapped_df))
    summary["proxy_mapped_nav"] = float(pd.to_numeric(mapped_df.get("current_nav_usd_m"), errors="coerce").fillna(0).sum())

    total_commitment = summary.get("total_commitments")
    paid_in = summary.get("paid_in_capital")
    current_nav = summary.get("private_fund_nav")
    if total_commitment not in (None, 0):
        summary["funded_ratio"] = paid_in / total_commitment if paid_in is not None else None
    if paid_in not in (None, 0):
        summary["nav_to_paid_in_ratio"] = current_nav / paid_in if current_nav is not None else None

    if {"as_of_date", "last_statement_date"}.issubset(positions_df.columns):
        lag_df = positions_df.copy()
        lag_df["as_of_date"] = pd.to_datetime(lag_df["as_of_date"], errors="coerce")
        lag_df["last_statement_date"] = pd.to_datetime(lag_df["last_statement_date"], errors="coerce")
        lag_df = lag_df.dropna(subset=["as_of_date", "last_statement_date"])
        if not lag_df.empty:
            lag_df["statement_lag_days"] = (lag_df["as_of_date"] - lag_df["last_statement_date"]).dt.days
            summary["average_statement_lag_days"] = float(pd.to_numeric(lag_df["statement_lag_days"], errors="coerce").mean())
            summary["latest_statement_date"] = lag_df["last_statement_date"].max()

    if private_monthly_df is not None and not private_monthly_df.empty and {"date", "nav_usd_m"}.issubset(private_monthly_df.columns):
        monthly_df = private_monthly_df.copy()
        monthly_df["date"] = pd.to_datetime(monthly_df["date"], errors="coerce")
        monthly_df["nav_usd_m"] = pd.to_numeric(monthly_df["nav_usd_m"], errors="coerce")
        monthly_df = monthly_df.dropna(subset=["date", "nav_usd_m"])
        if not monthly_df.empty:
            total_nav_df = monthly_df.groupby("date", as_index=False)["nav_usd_m"].sum().sort_values("date")
            summary["latest_total_nav"] = float(total_nav_df.iloc[-1]["nav_usd_m"])
            if len(total_nav_df) >= 13:
                base_value = float(total_nav_df.iloc[-13]["nav_usd_m"])
                latest_value = float(total_nav_df.iloc[-1]["nav_usd_m"])
                if base_value != 0:
                    summary["trailing_12m_nav_growth"] = latest_value / base_value - 1.0

    return summary


def build_private_dimension_summary(
    private_positions_df: pd.DataFrame,
    dimension_column: str,
    label: str,
) -> pd.DataFrame:
    required = {dimension_column, "current_nav_usd_m", "commitment_usd_m", "paid_in_capital_usd_m", "unfunded_commitment_usd_m"}
    if private_positions_df.empty or not required.issubset(private_positions_df.columns):
        return pd.DataFrame()

    working_df = private_positions_df.copy()
    working_df[dimension_column] = working_df[dimension_column].fillna("Unknown").astype(str).str.strip()
    for column in ["current_nav_usd_m", "commitment_usd_m", "paid_in_capital_usd_m", "unfunded_commitment_usd_m"]:
        working_df[column] = pd.to_numeric(working_df[column], errors="coerce")
    working_df = working_df.dropna(subset=[dimension_column])
    if working_df.empty:
        return pd.DataFrame()

    grouped = (
        working_df.groupby(dimension_column, as_index=False)
        .agg(
            nav_usd_m=("current_nav_usd_m", "sum"),
            commitment_usd_m=("commitment_usd_m", "sum"),
            paid_in_capital_usd_m=("paid_in_capital_usd_m", "sum"),
            unfunded_commitment_usd_m=("unfunded_commitment_usd_m", "sum"),
            fund_count=("fund_name", "nunique" if "fund_name" in working_df.columns else "size"),
        )
        .rename(columns={dimension_column: label})
        .sort_values("nav_usd_m", ascending=False)
    )
    grouped["funded_ratio"] = grouped["paid_in_capital_usd_m"] / grouped["commitment_usd_m"].replace(0, pd.NA)
    grouped["unfunded_ratio"] = grouped["unfunded_commitment_usd_m"] / grouped["commitment_usd_m"].replace(0, pd.NA)
    return grouped


def build_private_statement_lag_table(private_positions_df: pd.DataFrame) -> pd.DataFrame:
    if private_positions_df.empty or not {"fund_name", "as_of_date", "last_statement_date"}.issubset(private_positions_df.columns):
        return pd.DataFrame()
    lag_df = private_positions_df.copy()
    lag_df["as_of_date"] = pd.to_datetime(lag_df["as_of_date"], errors="coerce")
    lag_df["last_statement_date"] = pd.to_datetime(lag_df["last_statement_date"], errors="coerce")
    lag_df = lag_df.dropna(subset=["fund_name", "as_of_date", "last_statement_date"])
    if lag_df.empty:
        return pd.DataFrame()
    lag_df["statement_lag_days"] = (lag_df["as_of_date"] - lag_df["last_statement_date"]).dt.days
    columns = [
        column
        for column in [
            "fund_name",
            "strategy",
            "investment_geography",
            "current_nav_usd_m",
            "last_statement_date",
            "statement_lag_days",
            "valuation_status",
        ]
        if column in lag_df.columns
    ]
    return lag_df[columns].sort_values("statement_lag_days", ascending=False)


def build_private_nav_timeseries(private_monthly_df: pd.DataFrame) -> pd.DataFrame:
    if private_monthly_df.empty or not {"date", "nav_usd_m"}.issubset(private_monthly_df.columns):
        return pd.DataFrame()
    working_df = private_monthly_df.copy()
    working_df["date"] = pd.to_datetime(working_df["date"], errors="coerce")
    working_df["nav_usd_m"] = pd.to_numeric(working_df["nav_usd_m"], errors="coerce")
    working_df = working_df.dropna(subset=["date", "nav_usd_m"])
    if working_df.empty:
        return pd.DataFrame()
    return working_df.groupby("date", as_index=False)["nav_usd_m"].sum().sort_values("date")


def calculate_liquidity_coverage(cash_df: pd.DataFrame, capital_calls_df: pd.DataFrame) -> float | None:
    operating_mask = cash_df.get("is_operating_cash", pd.Series(False, index=cash_df.index)).fillna(False)
    total_cash = safe_sum(cash_df[operating_mask], ["balance_usd_m"])
    if total_cash <= 0:
        total_cash = safe_sum(cash_df, ["balance_usd_m"])
    upcoming_calls = safe_sum(capital_calls_df, ["amount_due_usd_m"])
    if upcoming_calls <= 0:
        return None
    return total_cash / upcoming_calls


def _cash_as_of_date(cash_df: pd.DataFrame) -> pd.Timestamp:
    as_of_series = pd.to_datetime(cash_df.get("as_of_date"), errors="coerce")
    if as_of_series is not None:
        clean = as_of_series.dropna()
        if not clean.empty:
            return clean.max()
    return pd.Timestamp.today().normalize()


def filter_projected_distribution_cashflows(
    cashflows_df: pd.DataFrame,
    as_of_date: pd.Timestamp | None = None,
) -> pd.DataFrame:
    if cashflows_df.empty:
        return pd.DataFrame()
    working_df = cashflows_df.copy()
    if "cashflow_type" in working_df.columns:
        working_df = working_df[
            working_df["cashflow_type"].astype(str).str.casefold().eq("distribution")
        ].copy()
    if working_df.empty:
        return pd.DataFrame()
    if "liquidity_treatment" in working_df.columns:
        working_df = working_df[
            ~working_df["liquidity_treatment"].astype(str).str.casefold().eq("booked_in_cash")
        ].copy()
    if working_df.empty or "cashflow_date" not in working_df.columns:
        return pd.DataFrame()
    working_df["cashflow_date"] = pd.to_datetime(working_df["cashflow_date"], errors="coerce")
    working_df = working_df.dropna(subset=["cashflow_date"])
    if working_df.empty:
        return pd.DataFrame()
    if as_of_date is not None:
        working_df = working_df[working_df["cashflow_date"] > as_of_date].copy()
    return working_df.sort_values("cashflow_date").reset_index(drop=True)


def calculate_liquidity_metrics(
    cash_df: pd.DataFrame,
    capital_calls_df: pd.DataFrame | None = None,
    cashflows_df: pd.DataFrame | None = None,
) -> dict:
    capital_calls_df = capital_calls_df if capital_calls_df is not None else pd.DataFrame()
    cashflows_df = cashflows_df if cashflows_df is not None else pd.DataFrame()

    total_cash = safe_sum(cash_df, ["balance_usd_m"])
    operating_cash = safe_sum(
        cash_df[cash_df.get("is_operating_cash", pd.Series(False, index=cash_df.index)).fillna(False)],
        ["balance_usd_m"],
    )
    soft_eligible_liquidity = safe_sum(
        cash_df[cash_df.get("is_soft_liquidity_eligible", pd.Series(False, index=cash_df.index)).fillna(False)],
        ["balance_usd_m"],
    )
    currency_cash = (
        cash_df.groupby("currency", as_index=False)["balance_usd_m"].sum()
        if not cash_df.empty and {"currency", "balance_usd_m"}.issubset(cash_df.columns)
        else pd.DataFrame(columns=["currency", "balance_usd_m"])
    )
    if currency_cash.empty:
        usd_cash = 0.0
        sgd_cash = 0.0
    else:
        currency_cash["currency"] = currency_cash["currency"].astype(str).str.upper()
        usd_cash = safe_sum(currency_cash[currency_cash["currency"] == "USD"], ["balance_usd_m"])
        sgd_cash = safe_sum(currency_cash[currency_cash["currency"] == "SGD"], ["balance_usd_m"])
    as_of_date = _cash_as_of_date(cash_df)
    upcoming_calls = safe_sum(capital_calls_df, ["amount_due_usd_m"])
    projected_distributions_df = filter_projected_distribution_cashflows(cashflows_df, as_of_date=as_of_date)
    expected_distributions = safe_sum(
        projected_distributions_df,
        ["expected_cash_inflow_usd_m", "net_distribution_usd_m", "gross_distribution_usd_m"],
    )
    net_projected_liquidity = total_cash + expected_distributions - upcoming_calls

    return {
        "cash_liquidity": total_cash,
        "operating_cash": operating_cash,
        "soft_eligible_liquidity": soft_eligible_liquidity,
        "usd_cash": usd_cash,
        "sgd_cash": sgd_cash,
        "as_of_date": as_of_date,
        "upcoming_capital_calls": upcoming_calls,
        "expected_distributions": expected_distributions,
        "net_projected_liquidity": net_projected_liquidity,
        "cash_to_upcoming_calls_coverage": calculate_liquidity_coverage(cash_df, capital_calls_df),
    }


def calculate_liquidity_horizon_table(
    cash_df: pd.DataFrame,
    capital_calls_df: pd.DataFrame | None = None,
    cashflows_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    capital_calls_df = capital_calls_df if capital_calls_df is not None else pd.DataFrame()
    cashflows_df = cashflows_df if cashflows_df is not None else pd.DataFrame()

    if cash_df.empty:
        return pd.DataFrame(
            columns=[
                "Horizon",
                "Operating Cash",
                "Upcoming Calls",
                "Projected Distributions",
                "Hard Coverage",
                "Soft Coverage",
            ]
        )

    as_of_date = _cash_as_of_date(cash_df)
    operating_cash = safe_sum(
        cash_df[cash_df.get("is_operating_cash", pd.Series(False, index=cash_df.index)).fillna(False)],
        ["balance_usd_m"],
    )

    calls_df = capital_calls_df.copy()
    if not calls_df.empty and "due_date" in calls_df.columns:
        calls_df["due_date"] = pd.to_datetime(calls_df["due_date"], errors="coerce")
        calls_df = calls_df.dropna(subset=["due_date"])

    flows_df = filter_projected_distribution_cashflows(cashflows_df, as_of_date=as_of_date)

    horizons = [("30D", 30), ("90D", 90), ("12M", 365)]
    rows: list[dict[str, object]] = []
    for label, days in horizons:
        horizon_end = as_of_date + pd.Timedelta(days=days)
        upcoming_calls = 0.0
        projected_distributions = 0.0
        if not calls_df.empty:
            window_calls = calls_df[(calls_df["due_date"] >= as_of_date) & (calls_df["due_date"] <= horizon_end)]
            upcoming_calls = safe_sum(window_calls, ["amount_due_usd_m"])
        if not flows_df.empty:
            window_flows = flows_df[(flows_df["cashflow_date"] >= as_of_date) & (flows_df["cashflow_date"] <= horizon_end)]
            projected_distributions = safe_sum(
                window_flows,
                ["expected_cash_inflow_usd_m", "net_distribution_usd_m", "gross_distribution_usd_m"],
            )

        hard_coverage = None if upcoming_calls <= 0 else operating_cash / upcoming_calls
        soft_coverage = None if upcoming_calls <= 0 else (operating_cash + projected_distributions) / upcoming_calls
        rows.append(
            {
                "Horizon": label,
                "Operating Cash": operating_cash,
                "Upcoming Calls": upcoming_calls,
                "Projected Distributions": projected_distributions,
                "Hard Coverage": hard_coverage,
                "Soft Coverage": soft_coverage,
            }
        )
    return pd.DataFrame(rows)


def workflow_status_card(document_status_df: pd.DataFrame):
    if document_status_df.empty or "validation_review_status" not in document_status_df.columns:
        st.info("Workflow status is unavailable.")
        return
    counts = document_status_df["validation_review_status"].value_counts().to_dict()
    applied_count = (
        int(document_status_df["update_applied_flag"].fillna(False).sum())
        if "update_applied_flag" in document_status_df.columns
        else 0
    )
    blocked_count = counts.get("needs_review", 0) + counts.get("rejected", 0)
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Processed", len(document_status_df))
    with col2:
        st.metric("Approved", counts.get("approved", 0))
    with col3:
        st.metric("Blocked", blocked_count)
    with col4:
        st.metric("Applied", applied_count)


def markdown_report_preview(path: str | Path | None, title: str):
    if not path:
        st.info(f"{title} is unavailable.")
        return
    report_path = Path(path)
    if not report_path.exists():
        st.info(f"{title} is unavailable.")
        return
    with st.expander(title, expanded=False):
        st.markdown(report_path.read_text(encoding="utf-8"))


def status_filter_widget(df: pd.DataFrame, column_name: str) -> pd.DataFrame:
    if df.empty or column_name not in df.columns:
        return df
    options = sorted(df[column_name].dropna().astype(str).unique().tolist())
    selected = st.multiselect(f"Filter by {column_name}", options, default=options)
    if not selected:
        return df.iloc[0:0]
    return df[df[column_name].astype(str).isin(selected)]


def show_json_preview(records: list[dict], document_id_column: str = "document_id"):
    if not records:
        st.info("No extracted JSON records are available for preview.")
        return
    record_map = {record[document_id_column]: record for record in records if document_id_column in record}
    if not record_map:
        st.info("No previewable JSON records are available.")
        return
    selected_document = st.selectbox("Select document_id", sorted(record_map))
    selected_record = record_map[selected_document]
    meta_cols = st.columns(3)
    with meta_cols[0]:
        st.metric("Confidence", selected_record.get("confidence_score", "N/A"))
    with meta_cols[1]:
        st.metric("Extraction Status", selected_record.get("extraction_status", "N/A"))
    with meta_cols[2]:
        st.metric("Mode", selected_record.get("extraction_mode", "N/A"))
    st.json(selected_record)
