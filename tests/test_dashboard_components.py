import importlib
from pathlib import Path

import pandas as pd

from src.dashboard.components import (
    build_public_proxy_basket_history,
    build_private_dimension_summary,
    build_private_nav_timeseries,
    build_private_statement_lag_table,
    build_risk_dimension_summary,
    build_stress_impact_tables,
    build_top_correlation_pairs,
    calculate_asset_class_metrics,
    calculate_commitment_summary,
    calculate_liquidity_horizon_table,
    calculate_liquidity_metrics,
    calculate_performance_statistics_table,
    calculate_portfolio_summary_metrics,
    calculate_public_market_summary,
    calculate_private_markets_summary,
    calculate_return_statistics_table,
    calculate_private_market_metrics,
    calculate_return_metrics,
    format_percentage,
    format_usd_millions,
    latest_value_from_timeseries,
    prepare_public_risk_overlay,
    safe_sum,
)


def test_dashboard_components_import() -> None:
    module = importlib.import_module("src.dashboard.components")
    assert hasattr(module, "metric_card")
    assert hasattr(module, "pipeline_status_summary")


def test_formatting_functions_work() -> None:
    assert format_usd_millions(12.34) == "USD 12.3m"
    assert format_usd_millions(None) == "N/A"
    assert format_percentage(0.1234) == "12.3%"


def test_safe_sum_returns_zero_for_missing_columns() -> None:
    df = pd.DataFrame({"a": [1, 2, 3]})
    assert safe_sum(df, ["missing"]) == 0.0


def test_app_can_be_imported_without_running_pipeline_code() -> None:
    module = importlib.import_module("app")
    assert hasattr(module, "main")


def test_new_workflow_helpers_exist() -> None:
    module = importlib.import_module("src.dashboard.components")
    assert hasattr(module, "section_header")
    assert hasattr(module, "synthetic_data_notice")
    assert hasattr(module, "empty_state")
    assert hasattr(module, "workflow_status_card")
    assert hasattr(module, "markdown_report_preview")
    assert hasattr(module, "status_filter_widget")
    assert hasattr(module, "show_json_preview")


def test_calculate_return_metrics_works() -> None:
    df = pd.DataFrame(
        {
            "date": ["2025-12-31", "2026-01-31", "2026-02-28"],
            "total_aum_usd_m": [100.0, 110.0, 121.0],
        }
    )
    metrics = calculate_return_metrics(df)
    assert metrics["latest_return"] is not None
    assert round(metrics["latest_return"], 4) == 0.1


def test_calculate_portfolio_summary_metrics_prefers_monthly_summary_for_total_aum() -> None:
    monthly = pd.DataFrame(
        {
            "date": ["2026-03-31", "2026-04-30"],
            "total_aum_usd_m": [740.0, 750.0],
            "public_markets_usd_m": [320.0, 330.0],
            "closed_end_private_fund_nav_usd_m": [358.0, 360.0],
            "cash_liquidity_usd_m": [22.0, 22.5],
        }
    )
    positions = pd.DataFrame({"current_nav_usd_m": [100.0], "unfunded_commitment_usd_m": [50.0]})
    cash = pd.DataFrame({"balance_usd_m": [10.0]})
    status = pd.DataFrame({"validation_review_status": ["approved", "needs_review"]})
    metrics = calculate_portfolio_summary_metrics(monthly, positions, cash, status)
    assert metrics["total_aum"] == 750.0


def test_latest_value_from_timeseries_uses_latest_date() -> None:
    df = pd.DataFrame(
        {
            "date": ["2026-04-30", "2026-03-31", "2026-05-31"],
            "value_a": [1.0, 2.0, 3.0],
        }
    )
    assert latest_value_from_timeseries(df, ["value_a"]) == 3.0


def test_calculate_commitment_summary_matches_corrected_totals() -> None:
    positions = pd.DataFrame(
        {
            "current_nav_usd_m": [200.0, 160.0],
            "commitment_usd_m": [300.0, 200.0],
            "paid_in_capital_usd_m": [220.0, 145.0],
            "unfunded_commitment_usd_m": [80.0, 55.0],
        }
    )
    summary = calculate_commitment_summary(positions)
    assert summary["private_fund_nav"] == 360.0
    assert summary["total_commitments"] == 500.0
    assert summary["paid_in_capital"] == 365.0
    assert summary["unfunded_commitments"] == 135.0


def test_calculate_private_market_metrics_uses_latest_cashflow_month() -> None:
    positions = pd.DataFrame(
        {
            "current_nav_usd_m": [360.0],
            "commitment_usd_m": [500.0],
            "paid_in_capital_usd_m": [365.0],
            "unfunded_commitment_usd_m": [135.0],
        }
    )
    cashflows = pd.DataFrame(
        {
            "cashflow_date": ["2026-04-30", "2026-05-31"],
            "expected_cash_inflow_usd_m": [1.0, 3.1],
        }
    )
    metrics = calculate_private_market_metrics(positions, cashflows)
    assert metrics["private_fund_nav"] == 360.0
    assert metrics["distributions_this_month"] == 3.1


def test_private_market_summary_and_dimension_helpers_work() -> None:
    positions_df = pd.DataFrame(
        {
            "as_of_date": ["2026-04-30", "2026-04-30"],
            "fund_id": ["F1", "F2"],
            "fund_name": ["Fund One", "Fund Two"],
            "strategy": ["Buyout", "VC"],
            "investment_geography": ["North America", "Southeast Asia"],
            "mandate_sector": ["Industrials", "Technology"],
            "proxy_mapping_flag": [True, False],
            "current_nav_usd_m": [35.0, 25.0],
            "commitment_usd_m": [60.0, 40.0],
            "paid_in_capital_usd_m": [40.0, 30.0],
            "unfunded_commitment_usd_m": [20.0, 10.0],
            "last_statement_date": ["2026-03-31", "2026-02-28"],
            "valuation_status": ["Synthetic baseline", "Synthetic baseline"],
        }
    )
    monthly_df = pd.DataFrame(
        {
            "date": pd.date_range("2025-04-30", periods=13, freq="ME").tolist() * 2,
            "fund_id": ["F1"] * 13 + ["F2"] * 13,
            "fund_name": ["Fund One"] * 13 + ["Fund Two"] * 13,
            "nav_usd_m": [20 + i for i in range(13)] + [15 + i for i in range(13)],
        }
    )
    cashflows_df = pd.DataFrame(
        {
            "cashflow_date": ["2026-05-31"],
            "expected_cash_inflow_usd_m": [3.0],
        }
    )

    summary = calculate_private_markets_summary(positions_df, monthly_df, cashflows_df)
    strategy_df = build_private_dimension_summary(positions_df, "strategy", "Strategy")
    lag_df = build_private_statement_lag_table(positions_df)
    total_nav_df = build_private_nav_timeseries(monthly_df)

    assert summary["fund_count"] == 2
    assert summary["strategy_count"] == 2
    assert summary["proxy_mapped_fund_count"] == 1
    assert summary["proxy_mapped_nav"] == 35.0
    assert round(float(summary["funded_ratio"]), 4) == 0.7
    assert summary["latest_statement_date"] is not None
    assert summary["trailing_12m_nav_growth"] is not None
    assert not strategy_df.empty
    assert strategy_df["Strategy"].tolist() == ["Buyout", "VC"]
    assert not lag_df.empty
    assert "statement_lag_days" in lag_df.columns
    assert not total_nav_df.empty
    assert {"date", "nav_usd_m"}.issubset(total_nav_df.columns)


def test_calculate_liquidity_metrics_handles_empty_capital_calls() -> None:
    cash_df = pd.DataFrame(
        {
            "currency": ["USD", "USD", "SGD"],
            "balance_usd_m": [11.0, 8.0, 3.5],
        }
    )
    cashflows_df = pd.DataFrame({"expected_cash_inflow_usd_m": [3.1]})
    metrics = calculate_liquidity_metrics(cash_df, pd.DataFrame(), cashflows_df)
    assert metrics["cash_liquidity"] == 22.5
    assert metrics["operating_cash"] == 0.0
    assert metrics["soft_eligible_liquidity"] == 0.0
    assert metrics["usd_cash"] == 19.0
    assert metrics["sgd_cash"] == 3.5
    assert metrics["upcoming_capital_calls"] == 0.0
    assert metrics["expected_distributions"] == 3.1
    assert metrics["net_projected_liquidity"] == 25.6
    assert metrics["cash_to_upcoming_calls_coverage"] is None


def test_calculate_liquidity_horizon_table_returns_expected_horizons() -> None:
    cash_df = pd.DataFrame(
        {
            "as_of_date": ["2026-04-30", "2026-04-30"],
            "balance_usd_m": [12.0, 10.5],
            "is_operating_cash": [True, False],
        }
    )
    capital_calls_df = pd.DataFrame(
        {
            "due_date": ["2026-05-15", "2026-08-15", "2027-02-01"],
            "amount_due_usd_m": [4.0, 3.0, 5.0],
        }
    )
    cashflows_df = pd.DataFrame(
        {
            "cashflow_date": ["2026-05-31", "2026-06-30", "2026-12-31"],
            "expected_cash_inflow_usd_m": [1.0, 2.0, 3.0],
        }
    )
    table = calculate_liquidity_horizon_table(cash_df, capital_calls_df, cashflows_df)
    assert table["Horizon"].tolist() == ["30D", "90D", "12M"]
    assert table.loc[0, "Upcoming Calls"] == 4.0
    assert table.loc[1, "Projected Distributions"] == 3.0


def test_calculate_asset_class_metrics_returns_summary() -> None:
    allocation = pd.DataFrame(
        {
            "asset_class": ["Global Public Equities", "Private Equity"],
            "final_value_usd_m": [225.0, 135.0],
        }
    )
    monthly = pd.DataFrame(
        {
            "date": ["2026-04-30", "2026-04-30"],
            "asset_class": ["Global Public Equities", "Private Equity"],
            "value_usd_m": [225.0, 135.0],
        }
    )
    metrics = calculate_asset_class_metrics(allocation, monthly)
    assert metrics["total_value"] == 360.0
    assert metrics["largest_asset_class"] == "Global Public Equities"


def test_calculate_performance_statistics_table_returns_expected_columns() -> None:
    df = pd.DataFrame(
        {
            "date": pd.date_range("2023-01-31", periods=40, freq="ME"),
            "total_aum_usd_m": [100 + i for i in range(40)],
        }
    )
    stats = calculate_performance_statistics_table(df)
    assert list(stats.columns) == ["Metric", "1 Year", "3 Years", "Since Inception"]
    assert "Annualized Return" in stats["Metric"].tolist()


def test_calculate_return_statistics_table_returns_expected_columns() -> None:
    returns_df = pd.DataFrame(
        {
            "date": pd.date_range("2023-01-31", periods=40, freq="ME"),
            "monthly_return": [0.01] * 40,
        }
    )
    stats = calculate_return_statistics_table(returns_df)
    assert list(stats.columns) == ["Metric", "1 Year", "3 Years", "Since Inception"]
    assert "Sharpe Ratio" in stats["Metric"].tolist()


def test_public_proxy_helpers_build_summary_and_basket() -> None:
    holdings_df = pd.DataFrame(
        {
            "holding_id": ["H1", "H2"],
            "holding_name": ["Long SPY", "Short QQQ"],
            "ticker": ["SPY", "QQQ"],
            "position_side_current": ["long", "short"],
            "current_delta_adjusted_exposure_usd_m": [20.0, -5.0],
            "final_value_usd_m": [18.0, 3.0],
        }
    )
    monthly_summary_df = pd.DataFrame(
        {
            "date": ["2026-03-31", "2026-04-30"],
            "total_aum_usd_m": [98.0, 100.0],
        }
    )
    prices_df = pd.DataFrame(
        {
            "date": pd.date_range("2023-01-31", periods=16, freq="ME").tolist() * 2,
            "ticker": ["SPY"] * 16 + ["QQQ"] * 16,
            "close": [100 + i for i in range(16)] + [200 + 2 * i for i in range(16)],
            "data_source": ["real"] * 32,
        }
    )
    proxy_map_df = pd.DataFrame(
        {
            "holding_id": ["H1", "H2"],
            "ticker_or_proxy": ["SPY", "QQQ"],
        }
    )

    summary = calculate_public_market_summary(holdings_df, monthly_summary_df, prices_df, proxy_map_df)
    basket_df = build_public_proxy_basket_history(holdings_df, prices_df, proxy_map_df)

    assert summary["proxy_tickers"] == 2
    assert summary["coverage_ratio"] == 1.0
    assert summary["gross_exposure"] == 0.25
    assert summary["net_exposure"] == 0.15
    assert not basket_df.empty
    assert {"date", "monthly_return", "cumulative_index", "drawdown"}.issubset(basket_df.columns)


def test_risk_overlay_helpers_build_dimension_and_stress_views() -> None:
    holdings_df = pd.DataFrame(
        {
            "holding_id": ["H1", "H2"],
            "holding_name": ["Long SPY", "Short QQQ"],
            "asset_class": ["Global Public Equities", "Global Public Equities"],
            "gics_sector": ["Information Technology", "Information Technology"],
            "region_taxonomy": ["North America", "North America"],
            "liquidity_bucket": ["Liquid", "Liquid"],
            "ticker": ["SPY", "QQQ"],
            "position_side_current": ["long", "short"],
            "current_delta_adjusted_exposure_usd_m": [20.0, -5.0],
        }
    )
    proxy_map_df = pd.DataFrame(
        {
            "holding_id": ["H1", "H2"],
            "ticker_or_proxy": ["SPY", "QQQ"],
            "risk_proxy_bucket": ["US Equity", "US Equity"],
            "mapping_confidence": [1.0, 1.0],
        }
    )
    risk_metrics_df = pd.DataFrame(
        {
            "ticker": ["SPY", "QQQ"],
            "annualized_volatility": [0.15, 0.25],
            "max_drawdown": [-0.20, -0.35],
            "data_source": ["real", "real"],
        }
    )
    monthly_summary_df = pd.DataFrame({"date": ["2026-04-30"], "total_aum_usd_m": [100.0]})
    stress_df = pd.DataFrame(
        {
            "scenario": ["equity_down_10", "equity_down_10"],
            "ticker": ["SPY", "QQQ"],
            "stress_return": [-0.10, -0.10],
        }
    )
    correlation_df = pd.DataFrame(
        {
            "ticker": ["SPY", "QQQ"],
            "SPY": [1.0, 0.8],
            "QQQ": [0.8, 1.0],
        }
    )

    overlay_df = prepare_public_risk_overlay(holdings_df, proxy_map_df, risk_metrics_df, monthly_summary_df)
    region_summary_df = build_risk_dimension_summary(overlay_df, "region_taxonomy", "Region")
    stress_summary_df, stress_detail_df = build_stress_impact_tables(overlay_df, stress_df, monthly_summary_df)
    correlation_pairs_df = build_top_correlation_pairs(correlation_df)

    assert not overlay_df.empty
    assert overlay_df["proxy_ticker"].tolist() == ["SPY", "QQQ"]
    assert round(float(overlay_df["gross_exposure_pct_nav"].sum()), 4) == 0.25
    assert not region_summary_df.empty
    assert region_summary_df.iloc[0]["Region"] == "North America"
    assert round(float(region_summary_df.iloc[0]["Exposure % NAV"]), 4) == 0.15
    assert not stress_summary_df.empty
    assert not stress_detail_df.empty
    assert round(float(stress_summary_df.iloc[0]["scenario_impact_pct_nav"]), 4) == -0.015
    assert not correlation_pairs_df.empty
    assert correlation_pairs_df.iloc[0]["Correlation"] == 0.8
