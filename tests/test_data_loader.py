from pathlib import Path

from src import config
from src.data_loader import (
    list_csv_files,
    list_excel_sheets,
    list_pdf_files,
    read_csv_table,
    safe_find_csv,
)


def test_config_paths_are_path_objects() -> None:
    assert isinstance(config.REPO_ROOT, Path)
    assert isinstance(config.RAW_DATA_DIR, Path)
    assert isinstance(config.CSV_DIR, Path)
    assert isinstance(config.DOCUMENTS_DIR, Path)
    assert isinstance(config.WORKBOOK_PATH, Path)


def test_core_data_paths_exist() -> None:
    assert config.CSV_DIR.exists()
    assert config.DOCUMENTS_DIR.exists()
    assert config.WORKBOOK_PATH.exists()


def test_list_csv_files_returns_files() -> None:
    csv_files = list_csv_files()
    assert csv_files
    assert all(path.suffix == ".csv" for path in csv_files)


def test_list_pdf_files_returns_expected_count() -> None:
    pdf_files = list_pdf_files()
    assert len(pdf_files) == 6


def test_list_excel_sheets_returns_sheets() -> None:
    sheets = list_excel_sheets()
    assert "portfolio_monthly_summary" in sheets


def test_read_csv_table_supports_stem_name() -> None:
    df = read_csv_table("portfolio_monthly_summary")
    assert not df.empty


def test_safe_find_csv_supports_filename_or_close_match() -> None:
    assert safe_find_csv(["portfolio_monthly_summary"]).name == "portfolio_monthly_summary.csv"
    assert safe_find_csv(["portfolio monthly summary"]).name == "portfolio_monthly_summary.csv"
