import pandas as pd

from src.dashboard.charts import (
    asset_class_allocation_over_time_chart,
    asset_class_by_month_chart,
    asset_class_category_evolution_chart,
    asset_class_exposure_filter_chart,
    asset_class_monthly_change_chart,
    asset_class_snapshot_bars,
    asset_class_snapshot_change_bars,
    asset_class_value_trend_chart,
    capital_call_calendar_chart,
    correlation_heatmap,
    dimension_exposure_filter_chart,
    dimension_net_exposure_trend_chart,
    distribution_timeline_chart,
    drawdown_chart,
    liquidity_coverage_chart,
    market_cap_exposure_chart,
    public_market_value_trend_chart,
    public_proxy_performance_chart,
    portfolio_return_bars_cumulative_line_chart,
    projected_distributions_by_fund_chart,
    sector_exposure_chart,
    usd_vs_non_usd_chart,
)


def test_chart_functions_handle_empty_dataframes_gracefully() -> None:
    assert isinstance(asset_class_value_trend_chart(pd.DataFrame()), str)
    assert isinstance(asset_class_by_month_chart(pd.DataFrame()), str)
    assert isinstance(asset_class_exposure_filter_chart(pd.DataFrame()), str)
    assert isinstance(asset_class_snapshot_bars(pd.DataFrame(), "net_exposure", "Snapshot"), str)
    assert isinstance(asset_class_snapshot_change_bars(pd.DataFrame(), "Snapshot Change"), str)
    assert isinstance(asset_class_category_evolution_chart(pd.DataFrame(), "Category Evolution"), str)
    assert isinstance(asset_class_monthly_change_chart(pd.DataFrame(), "Monthly Change"), str)
    assert isinstance(asset_class_allocation_over_time_chart(pd.DataFrame()), str)
    assert isinstance(dimension_exposure_filter_chart(pd.DataFrame(), "region_taxonomy_pti", "Region Exposure Trend"), str)
    assert isinstance(dimension_net_exposure_trend_chart(pd.DataFrame(), "region_taxonomy_pti", "Region Exposure Trend"), str)
    assert isinstance(public_market_value_trend_chart(pd.DataFrame()), str)
    assert isinstance(public_proxy_performance_chart(pd.DataFrame()), str)
    assert isinstance(portfolio_return_bars_cumulative_line_chart(pd.DataFrame()), str)
    assert isinstance(capital_call_calendar_chart(pd.DataFrame()), str)
    assert isinstance(distribution_timeline_chart(pd.DataFrame()), str)
    assert isinstance(projected_distributions_by_fund_chart(pd.DataFrame()), str)
    assert isinstance(liquidity_coverage_chart(pd.DataFrame(), pd.DataFrame()), str)
    assert isinstance(drawdown_chart(pd.DataFrame()), str)
    assert isinstance(sector_exposure_chart(pd.DataFrame()), str)
    assert isinstance(market_cap_exposure_chart(pd.DataFrame()), str)
    assert isinstance(usd_vs_non_usd_chart(pd.DataFrame()), str)


def test_correlation_heatmap_handles_empty_dataframe() -> None:
    assert isinstance(correlation_heatmap(pd.DataFrame()), str)


def test_single_distribution_keeps_a_date_axis() -> None:
    figure = distribution_timeline_chart(
        pd.DataFrame(
            {
                "cashflow_date": ["2026-09-30"],
                "fund_name": ["Example Fund"],
                "cashflow_type": ["distribution"],
                "expected_cash_inflow_usd_m": [2.5],
                "liquidity_treatment": ["projected_inflow"],
            }
        )
    )

    assert not isinstance(figure, str)
    assert figure.layout.xaxis.type == "date"
    assert figure.data[0].mode == "markers"


def test_projected_distributions_by_fund_has_no_cashflow_type_axis_or_legend() -> None:
    figure = projected_distributions_by_fund_chart(
        pd.DataFrame(
            {
                "fund_name": ["Example Fund"],
                "cashflow_type": ["distribution"],
                "expected_cash_inflow_usd_m": [2.5],
            }
        )
    )

    assert not isinstance(figure, str)
    assert figure.layout.xaxis.title.text == "Projected Distribution (USD m)"
    assert figure.layout.yaxis.title.text == "Fund"
    assert figure.layout.showlegend is False


def test_asset_class_exposure_filter_chart_returns_figure_for_valid_input() -> None:
    df = pd.DataFrame(
        {
            "date": ["2026-03-31", "2026-03-31", "2026-04-30", "2026-04-30"],
            "asset_class": ["Global Public Equities", "Global Public Equities", "Fixed Income & Liquid Credit", "Fixed Income & Liquid Credit"],
            "position_side": ["long", "short", "long", "short"],
            "net_weight": [0.40, -0.05, 0.20, -0.02],
        }
    )
    figure = asset_class_exposure_filter_chart(df)
    assert not isinstance(figure, str)
    trace_names = {trace.name for trace in figure.data}
    assert "Global Public Equities" in trace_names
    assert "Fixed Income & Liquid Credit" in trace_names


def test_dimension_exposure_filter_chart_returns_figure_for_valid_input() -> None:
    df = pd.DataFrame(
        {
            "date": ["2026-03-31", "2026-03-31", "2026-04-30", "2026-04-30"],
            "region_taxonomy_pti": ["North America", "Greater China", "North America", "Greater China"],
            "position_side": ["long", "short", "long", "short"],
            "net_weight": [0.40, -0.05, 0.42, -0.04],
        }
    )
    figure = dimension_exposure_filter_chart(df, "region_taxonomy_pti", "Region Exposure Trend")
    assert not isinstance(figure, str)
    assert figure.layout.yaxis.range is not None
    assert len(figure.layout.updatemenus[0].buttons) == 3


def test_dimension_net_exposure_trend_chart_returns_figure_for_valid_input() -> None:
    df = pd.DataFrame(
        {
            "date": ["2026-03-31", "2026-03-31", "2026-04-30", "2026-04-30"],
            "region_taxonomy_pti": ["North America", "Greater China", "North America", "Greater China"],
            "position_side": ["long", "short", "long", "short"],
            "net_weight": [0.40, -0.05, 0.42, -0.04],
        }
    )
    figure = dimension_net_exposure_trend_chart(df, "region_taxonomy_pti", "Region Exposure Trend")
    assert not isinstance(figure, str)
    assert figure.layout.updatemenus == ()


def test_asset_class_exposure_filter_chart_aggregates_long_and_short_in_all_view() -> None:
    df = pd.DataFrame(
        {
            "date": ["2026-03-31", "2026-03-31", "2026-04-30", "2026-04-30"],
            "asset_class": ["Global Public Equities"] * 4,
            "position_side": ["long", "short", "long", "short"],
            "net_weight": [0.40, -0.05, 0.42, -0.04],
        }
    )
    figure = asset_class_exposure_filter_chart(df)
    assert not isinstance(figure, str)
    all_trace = next(trace for trace in figure.data if trace.name == "Global Public Equities" and trace.visible is True)
    assert [round(value, 2) for value in all_trace.y] == [0.35, 0.38]
    assert figure.layout.yaxis.range is not None
    all_range = figure.layout.updatemenus[0].buttons[0].args[1]["yaxis.range"]
    long_range = figure.layout.updatemenus[0].buttons[1].args[1]["yaxis.range"]
    short_range = figure.layout.updatemenus[0].buttons[2].args[1]["yaxis.range"]
    assert all_range != short_range
    assert long_range != short_range


def test_asset_class_snapshot_helpers_return_figures_for_valid_input() -> None:
    snapshot_df = pd.DataFrame(
        {
            "category_label": ["Global Public Equities", "Private Equity"],
            "long_exposure": [0.45, 0.18],
            "short_exposure": [-0.06, 0.0],
            "net_exposure": [0.39, 0.18],
        }
    )
    change_df = pd.DataFrame(
        {
            "category_label": ["Global Public Equities", "Private Equity"],
            "long_change": [0.02, -0.01],
            "short_change": [-0.01, 0.0],
            "net_change": [0.01, -0.01],
        }
    )
    evolution_df = pd.DataFrame(
        {
            "date": ["2026-03-31", "2026-04-30"],
            "long_exposure": [0.45, 0.47],
            "short_exposure": [-0.06, -0.05],
            "net_exposure": [0.39, 0.42],
        }
    )
    monthly_change_df = pd.DataFrame(
        {
            "date": ["2026-03-31", "2026-04-30"],
            "long_change": [0.0, 0.02],
            "short_change": [0.0, 0.01],
        }
    )

    assert not isinstance(asset_class_snapshot_bars(snapshot_df, "net_exposure", "Snapshot"), str)
    assert not isinstance(asset_class_snapshot_bars(snapshot_df, "long_short", "Snapshot"), str)
    assert not isinstance(asset_class_snapshot_change_bars(change_df, "Snapshot Change"), str)
    assert not isinstance(asset_class_category_evolution_chart(evolution_df, "Category Evolution"), str)
    assert not isinstance(asset_class_monthly_change_chart(monthly_change_df, "Monthly Change"), str)
