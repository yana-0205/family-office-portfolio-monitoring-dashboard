import importlib

import pandas as pd

from src.dashboard import data_access
from src.dashboard.data_access import (
    load_asset_allocation_table,
    load_cash_accounts,
    load_extracted_json_records,
    load_fund_commentary,
    load_region_taxonomy_reference,
    load_update_summary_report,
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
