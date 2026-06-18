from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
RAW_DATA_DIR = REPO_ROOT / "data" / "raw" / "family_office_corrected_dataset_v1"
CSV_DIR = RAW_DATA_DIR / "csv"
DOCUMENTS_DIR = RAW_DATA_DIR / "documents"
WORKBOOK_PATH = RAW_DATA_DIR / "family_office_corrected_dataset_v1.xlsx"
OUTPUTS_DIR = REPO_ROOT / "outputs"
REPORTS_DIR = OUTPUTS_DIR / "reports"
RISK_OUTPUTS_DIR = OUTPUTS_DIR / "risk"
INTERIM_DATA_DIR = REPO_ROOT / "data" / "interim"
PROCESSED_DATA_DIR = REPO_ROOT / "data" / "processed"
MARKET_PRICES_DIR = REPO_ROOT / "data" / "raw" / "market_prices"
