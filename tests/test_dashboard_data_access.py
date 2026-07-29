import importlib

import pandas as pd

from src.dashboard import data_access
from src.dashboard.data_access import (
    load_asset_allocation_table,
    load_cash_accounts,
    load_extracted_json_records,
    load_fund_commentary,
    load_ingestion_inbox_status,
    load_portfolio_holdings,
    load_region_taxonomy_reference,
    load_update_summary_report,
    load_private_fund_monthly,
    load_portfolio_monthly_summary,
    load_processed_table,
    load_report_markdown,
)


def test_dashboard_data_access_imports() -> None:
    module = importlib.import_module("src.dashboard.data_access")
    assert hasattr(module, "load_private_positions")
    assert hasattr(module, "load_review_queue")
    assert hasattr(module, "load_validation_results")
    assert hasattr(module, "load_document_processing_status")
    assert hasattr(module, "load_ingestion_inbox_status")


def test_loading_missing_optional_tables_does_not_crash() -> None:
    df = load_processed_table("definitely_missing.csv")
    assert df.empty
    assert "warning" in df.attrs


def test_load_extracted_json_records_returns_records_or_empty_list() -> None:
    records = load_extracted_json_records("baseline")
    assert isinstance(records, list)


def test_load_missing_report_markdown_returns_none() -> None:
    report = load_report_markdown("definitely_missing_report.md")
    assert report is None


def test_portfolio_data_loaders_return_frames() -> None:
    summary_df = load_portfolio_monthly_summary()
    allocation_df = load_asset_allocation_table()
    assert isinstance(summary_df, __import__("pandas").DataFrame)
    assert isinstance(allocation_df, __import__("pandas").DataFrame)


def test_processed_dashboard_loaders_return_frames() -> None:
    cash_df = load_cash_accounts()
    commentary_df = load_fund_commentary()
    assert isinstance(cash_df, __import__("pandas").DataFrame)
    assert isinstance(commentary_df, __import__("pandas").DataFrame)


def test_update_summary_report_loader_returns_text_or_none() -> None:
    report = load_update_summary_report()
    assert report is None or isinstance(report, str)


def test_load_region_taxonomy_reference_returns_frame() -> None:
    region_reference_df = load_region_taxonomy_reference()
    assert isinstance(region_reference_df, pd.DataFrame)
    if not region_reference_df.empty:
        assert {"region_code", "region_taxonomy"}.issubset(region_reference_df.columns)


def test_load_public_monthly_prices_prefers_market_loader(monkeypatch) -> None:
    fake_prices = pd.DataFrame(
        {
            "date": ["2026-01-31"],
            "ticker": ["SPY"],
            "close": [600.0],
        }
    )

    monkeypatch.setattr(
        data_access,
        "load_market_prices",
        lambda prefer_real=True: {
            "prices": fake_prices,
            "metadata": {"data_source": "real"},
        },
    )

    result = data_access.load_public_monthly_prices()

    assert not result.empty
    assert "data_source" in result.columns
    assert result["data_source"].iloc[0] == "real"


def test_load_ingestion_inbox_status_returns_frame() -> None:
    inbox_df = load_ingestion_inbox_status()
    assert isinstance(inbox_df, pd.DataFrame)


def test_external_market_through_date_requires_prices_and_risk_to_align(monkeypatch) -> None:
    monkeypatch.setattr(
        data_access,
        "load_public_risk_metrics",
        lambda: pd.DataFrame({"end_date": ["2026-04-30"]}),
    )
    monkeypatch.setattr(
        data_access,
        "load_public_monthly_prices",
        lambda: pd.DataFrame({"date": ["2026-05-31"], "ticker": ["SPY"], "close": [610.0]}),
    )

    result = data_access.load_external_market_through_date()

    assert result == pd.Timestamp("2026-04-30")


def test_external_market_through_date_uses_common_ticker_freshness(monkeypatch) -> None:
    monkeypatch.setattr(
        data_access,
        "load_public_risk_metrics",
        lambda: pd.DataFrame({"end_date": ["2026-05-31"]}),
    )
    monkeypatch.setattr(
        data_access,
        "load_public_monthly_prices",
        lambda: pd.DataFrame(
            {
                "date": ["2026-05-31", "2026-04-30"],
                "ticker": ["SPY", "QQQ"],
                "close": [610.0, 500.0],
            }
        ),
    )

    assert data_access.load_external_market_through_date() == pd.Timestamp("2026-04-30")


def test_load_portfolio_monthly_summary_appends_overlay_snapshot(monkeypatch) -> None:
    baseline_summary = pd.DataFrame(
        {
            "date": ["2026-04-30"],
            "total_aum_usd_m": [100.0],
            "public_markets_usd_m": [60.0],
            "closed_end_private_fund_nav_usd_m": [30.0],
            "cash_liquidity_usd_m": [10.0],
            "operating_cash_usd_m": [5.0],
            "hard_liquidity_usd_m": [5.0],
            "soft_liquidity_usd_m": [10.0],
            "source": ["baseline"],
            "return_series_label": ["baseline"],
            "source_label": ["baseline"],
            "portfolio_monthly_return": [0.01],
        }
    )
    monkeypatch.setattr(data_access, "_load_optional_raw_table", lambda possible_names, primary_name: baseline_summary.copy())
    monkeypatch.setattr(
        data_access,
        "load_private_positions",
        lambda: pd.DataFrame({"asset_class": ["Private Equity"], "current_nav_usd_m": [35.0]}),
    )
    monkeypatch.setattr(
        data_access,
        "load_cash_accounts",
        lambda: pd.DataFrame(
            {
                "balance_usd_m": [12.0],
                "is_operating_cash": [True],
                "is_soft_liquidity_eligible": [True],
            }
        ),
    )
    monkeypatch.setattr(
        data_access,
        "load_document_processing_status",
        lambda: pd.DataFrame(
            {
                "document_id": ["PDF_003"],
                "extraction_mode": ["intake"],
                "update_applied_flag": [True],
            }
        ),
    )
    monkeypatch.setattr(
        data_access,
        "_load_extracted_record_lookup",
        lambda: {
            ("intake", "PDF_003"): {
                "document_id": "PDF_003",
                "notice_date": "2026-05-10",
                "reporting_period": "May 2026 event",
                "extracted_fields": {"payment_date": "2026-05-31"},
            }
        },
    )

    result = data_access.load_portfolio_monthly_summary()

    assert len(result) == 2
    assert str(pd.to_datetime(result.iloc[-1]["date"]).date()) == "2026-05-31"
    assert result.iloc[-1]["source"] == "approved_document_overlay"


def test_load_portfolio_monthly_by_holding_appends_overlay_snapshot(monkeypatch) -> None:
    baseline_holdings = pd.DataFrame(
        {
            "date": ["2026-04-30", "2026-04-30"],
            "holding_id": ["PUB_1", "CASH_1"],
            "holding_name": ["Public Sleeve", "Cash"],
            "asset_class": ["Global Public Equities", "Cash & Liquidity"],
            "value_usd_m": [60.0, 10.0],
            "source": ["baseline", "baseline"],
        }
    )
    monkeypatch.setattr(data_access, "_load_optional_raw_table", lambda possible_names, primary_name: baseline_holdings.copy())
    monkeypatch.setattr(
        data_access,
        "load_private_positions",
        lambda: pd.DataFrame({"asset_class": ["Private Equity"], "current_nav_usd_m": [35.0]}),
    )
    monkeypatch.setattr(
        data_access,
        "load_cash_accounts",
        lambda: pd.DataFrame({"balance_usd_m": [12.0]}),
    )
    monkeypatch.setattr(
        data_access,
        "load_document_processing_status",
        lambda: pd.DataFrame(
            {
                "document_id": ["PDF_003"],
                "extraction_mode": ["intake"],
                "update_applied_flag": [True],
            }
        ),
    )
    monkeypatch.setattr(
        data_access,
        "_load_extracted_record_lookup",
        lambda: {
            ("intake", "PDF_003"): {
                "document_id": "PDF_003",
                "notice_date": "2026-05-10",
                "reporting_period": "May 2026 event",
                "extracted_fields": {"payment_date": "2026-05-31"},
            }
        },
    )

    result = data_access.load_portfolio_monthly_by_holding()

    latest_date = pd.to_datetime(result["date"]).max()
    latest_rows = result[pd.to_datetime(result["date"]) == latest_date]
    assert str(latest_date.date()) == "2026-05-31"
    assert "Private Equity" in latest_rows["asset_class"].tolist()
    assert "Global Public Equities" in latest_rows["asset_class"].tolist()


def test_load_portfolio_holdings_appends_overlay_snapshot(monkeypatch) -> None:
    baseline_holdings = pd.DataFrame(
        {
            "holding_id": ["PUB_1", "H_PF_TEST", "H_CASH_USD"],
            "holding_name": ["Public Sleeve", "Test Fund", "USD Cash"],
            "asset_class": ["Global Public Equities", "Private Equity", "Cash & Liquidity"],
            "region_taxonomy": ["North America", "North America", "Global / Multi-region"],
            "region": ["North America", "North America", "Global / Multi-region"],
            "country": ["United States", "North America", "Cash Pool"],
            "currency": ["USD", "USD", "USD"],
            "final_value_usd_m": [60.0, 30.0, 10.0],
            "instrument_type": ["equity", "private_fund", "cash"],
            "position_side_current": ["long", "long", "long"],
            "current_exposure_usd_m": [60.0, 30.0, 10.0],
            "current_gross_notional_usd_m": [60.0, 30.0, 10.0],
            "current_delta_adjusted_exposure_usd_m": [60.0, 30.0, 10.0],
            "as_of_date": ["2026-04-30", "2026-04-30", "2026-04-30"],
            "allocation_pct": [0.6, 0.3, 0.1],
        }
    )
    monkeypatch.setattr(data_access, "_load_optional_raw_table", lambda possible_names, primary_name: baseline_holdings.copy())
    monkeypatch.setattr(
        data_access,
        "load_private_positions",
        lambda: pd.DataFrame(
            {
                "fund_id": ["PF_TEST"],
                "fund_name": ["Test Fund"],
                "asset_class": ["Private Equity"],
                "sub_strategy": ["Buyout"],
                "investment_geography": ["North America"],
                "mandate_sector": ["Industrials"],
                "current_nav_usd_m": [35.0],
                "proxy_mapping_flag": [True],
            }
        ),
    )
    monkeypatch.setattr(
        data_access,
        "load_cash_accounts",
        lambda: pd.DataFrame(
            {
                "cash_account_id": ["CASH_USD"],
                "account_name": ["USD Cash"],
                "currency": ["USD"],
                "entity_id": ["ENT_1"],
                "balance_usd_m": [12.0],
                "liquidity_bucket": ["Cash"],
            }
        ),
    )
    monkeypatch.setattr(
        data_access,
        "load_document_processing_status",
        lambda: pd.DataFrame(
            {
                "document_id": ["PDF_003"],
                "extraction_mode": ["intake"],
                "update_applied_flag": [True],
            }
        ),
    )
    monkeypatch.setattr(
        data_access,
        "_load_extracted_record_lookup",
        lambda: {
            ("intake", "PDF_003"): {
                "document_id": "PDF_003",
                "notice_date": "2026-05-10",
                "extracted_fields": {"payment_date": "2026-05-31"},
            }
        },
    )

    result = load_portfolio_holdings()

    assert set(result["holding_id"]) == {"PUB_1", "H_PF_TEST", "H_CASH_USD"}
    assert set(pd.to_datetime(result["as_of_date"]).dt.strftime("%Y-%m-%d")) == {"2026-05-31"}
    assert float(result.loc[result["holding_id"] == "H_PF_TEST", "final_value_usd_m"].iloc[0]) == 35.0
    assert float(result.loc[result["holding_id"] == "H_CASH_USD", "final_value_usd_m"].iloc[0]) == 12.0


def test_load_private_fund_monthly_appends_overlay_snapshot(monkeypatch) -> None:
    baseline_private_monthly = pd.DataFrame(
        {
            "date": ["2026-04-30"],
            "fund_id": ["PF_TEST"],
            "fund_name": ["Test Fund"],
            "nav_usd_m": [30.0],
            "investment_geography": ["North America"],
            "mandate_sector": ["Industrials"],
            "strategy": ["Buyout"],
            "source": ["baseline"],
        }
    )
    monkeypatch.setattr(data_access, "_load_optional_raw_table", lambda possible_names, primary_name: baseline_private_monthly.copy())
    monkeypatch.setattr(
        data_access,
        "load_private_positions",
        lambda: pd.DataFrame(
            {
                "fund_id": ["PF_TEST"],
                "fund_name": ["Test Fund"],
                "current_nav_usd_m": [35.0],
                "investment_geography": ["North America"],
                "mandate_sector": ["Industrials"],
                "strategy": ["Buyout"],
            }
        ),
    )
    monkeypatch.setattr(
        data_access,
        "load_document_processing_status",
        lambda: pd.DataFrame(
            {
                "document_id": ["PDF_003"],
                "extraction_mode": ["intake"],
                "update_applied_flag": [True],
            }
        ),
    )
    monkeypatch.setattr(
        data_access,
        "_load_extracted_record_lookup",
        lambda: {
            ("intake", "PDF_003"): {
                "document_id": "PDF_003",
                "reporting_period": "May 2026",
                "extracted_fields": {"period_end_date": "2026-05-31"},
            }
        },
    )

    result = load_private_fund_monthly()

    latest_row = result.sort_values("date").iloc[-1]
    assert str(pd.to_datetime(latest_row["date"]).date()) == "2026-05-31"
    assert float(latest_row["nav_usd_m"]) == 35.0
    assert latest_row["source"] == "approved_document_overlay"
