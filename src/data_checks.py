from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from src.config import (
    CSV_DIR,
    DOCUMENTS_DIR,
    INTERIM_DATA_DIR,
    PROCESSED_DATA_DIR,
    RAW_DATA_DIR,
    REPORTS_DIR,
    REPO_ROOT,
    WORKBOOK_PATH,
)
from src.data_loader import (
    list_csv_files,
    list_excel_sheets,
    list_pdf_files,
    read_csv_table,
    safe_find_csv,
    safe_find_table,
)


BASELINE_DATE = "2026-04-30"
EXPECTED_TOTAL_AUM = 750.0
EXPECTED_PRIVATE_NAV = 360.0
EXPECTED_TOTAL_COMMITMENTS = 500.0
EXPECTED_PAID_IN = 365.0
EXPECTED_UNFUNDED = 135.0
EXPECTED_CASH = 22.5
EXPECTED_PDF_COUNT = 6


@dataclass
class CheckResult:
    name: str
    status: str
    details: str


def _path_summary() -> list[str]:
    return [
        f"Repository root: `{REPO_ROOT}`",
        f"Raw data dir: `{RAW_DATA_DIR}`",
        f"CSV dir: `{CSV_DIR}`",
        f"Documents dir: `{DOCUMENTS_DIR}`",
        f"Workbook: `{WORKBOOK_PATH}`",
        f"Dataset README: `{RAW_DATA_DIR / 'README_corrected_data_package.md'}`",
        f"Dataset QA summary: `{RAW_DATA_DIR / 'QA_validation_summary.md'}`",
        f"Interim data dir: `{INTERIM_DATA_DIR}`",
        f"Processed data dir: `{PROCESSED_DATA_DIR}`",
        f"Reports dir: `{REPORTS_DIR}`",
    ]


def _record(results: list[CheckResult], name: str, passed: bool, details: str) -> None:
    results.append(CheckResult(name=name, status="passed" if passed else "failed", details=details))


def _record_warning(warnings: list[str], message: str) -> None:
    warnings.append(message)


def _check_path_exists(results: list[CheckResult], name: str, path: Path) -> None:
    _record(results, name, path.exists(), f"{path} exists={path.exists()}")


def _resolve_table(
    logical_name: str,
    aliases: list[str],
    assumptions: list[str],
    warnings: list[str],
    required: bool = False,
) -> pd.DataFrame | None:
    reference = safe_find_table(aliases)
    if reference is None:
        if required:
            raise FileNotFoundError(
                f"Required table '{logical_name}' could not be located in CSV or workbook sources."
            )
        _record_warning(
            warnings,
            f"Optional table '{logical_name}' could not be located in CSV or workbook sources.",
        )
        return None
    if not reference.exact_match:
        assumptions.append(
            f"Used closest table match '{reference.name}' for requested table '{logical_name}'."
        )
    if reference.source == "csv":
        direct_csv_match = safe_find_csv(aliases)
        if direct_csv_match is not None and direct_csv_match.name != f"{logical_name}.csv":
            assumptions.append(
                f"Resolved CSV for '{logical_name}' as '{direct_csv_match.name}'."
            )
    if reference.source == "csv":
        return read_csv_table(reference.name)
    return pd.read_excel(WORKBOOK_PATH, sheet_name=reference.name)


def _check_numeric(
    results: list[CheckResult],
    name: str,
    actual: float,
    expected: float,
    tolerance: float = 1e-6,
) -> None:
    passed = abs(actual - expected) <= tolerance
    _record(results, name, passed, f"actual={actual:.6f}, expected={expected:.6f}")


def run_all_checks(write_report: bool = True) -> dict[str, Any]:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    results: list[CheckResult] = []
    warnings: list[str] = []
    assumptions: list[str] = []

    _check_path_exists(results, "repository root exists", REPO_ROOT)
    _check_path_exists(results, "raw dataset folder exists", RAW_DATA_DIR)
    _check_path_exists(results, "csv folder exists", CSV_DIR)
    _check_path_exists(results, "documents folder exists", DOCUMENTS_DIR)
    _check_path_exists(results, "workbook exists", WORKBOOK_PATH)

    csv_files = list_csv_files() if CSV_DIR.exists() else []
    pdf_files = list_pdf_files() if DOCUMENTS_DIR.exists() else []
    excel_sheets = list_excel_sheets() if WORKBOOK_PATH.exists() else []

    summary = _resolve_table(
        "portfolio_monthly_summary",
        ["portfolio_monthly_summary", "portfolio monthly summary"],
        assumptions,
        warnings,
        required=True,
    )
    baseline_summary = summary.loc[summary["date"].astype(str) == BASELINE_DATE]
    if baseline_summary.empty:
        raise FileNotFoundError(
            f"No portfolio_monthly_summary row found for baseline date {BASELINE_DATE}"
        )
    baseline_row = baseline_summary.iloc[0]
    _check_numeric(results, "total AUM equals 750.0", float(baseline_row["total_aum_usd_m"]), EXPECTED_TOTAL_AUM)
    _check_numeric(
        results,
        "closed-end private fund NAV equals 360.0",
        float(baseline_row["closed_end_private_fund_nav_usd_m"]),
        EXPECTED_PRIVATE_NAV,
    )
    _check_numeric(
        results,
        "cash and liquidity equals 22.5",
        float(baseline_row["cash_liquidity_usd_m"]),
        EXPECTED_CASH,
    )

    holdings = _resolve_table(
        "portfolio_holdings",
        ["portfolio_holdings", "portfolio holdings"],
        assumptions,
        warnings,
        required=True,
    )
    allocation_sum = float(holdings["allocation_pct"].sum())
    _check_numeric(
        results,
        "asset allocation sums to 100%",
        allocation_sum,
        1.0,
        tolerance=1e-3,
    )

    private_positions = _resolve_table(
        "private_fund_positions",
        ["private_fund_positions", "private positions pre ingestion"],
        assumptions,
        warnings,
        required=True,
    )
    private_baseline = private_positions.loc[
        private_positions["as_of_date"].astype(str) == BASELINE_DATE
    ]
    if private_baseline.empty:
        raise FileNotFoundError(
            f"No private_fund_positions rows found for baseline date {BASELINE_DATE}"
        )
    total_commitments = float(private_baseline["commitment_usd_m"].sum())
    paid_in = float(private_baseline["paid_in_capital_usd_m"].sum())
    unfunded = float(private_baseline["unfunded_commitment_usd_m"].sum())
    private_nav = float(private_baseline["current_nav_usd_m"].sum())
    _check_numeric(results, "total private fund commitments equal 500.0", total_commitments, EXPECTED_TOTAL_COMMITMENTS)
    _check_numeric(results, "paid-in capital equals 365.0", paid_in, EXPECTED_PAID_IN)
    _check_numeric(results, "unfunded commitments equal 135.0", unfunded, EXPECTED_UNFUNDED)
    _check_numeric(results, "closed-end private fund NAV from positions equals 360.0", private_nav, EXPECTED_PRIVATE_NAV)
    _check_numeric(results, "paid-in + unfunded equals total commitments", paid_in + unfunded, total_commitments)

    cash_accounts = _resolve_table(
        "cash_accounts",
        ["cash_accounts", "cash accounts"],
        assumptions,
        warnings,
        required=True,
    )
    cash_baseline = cash_accounts.loc[cash_accounts["as_of_date"].astype(str) == BASELINE_DATE]
    if cash_baseline.empty:
        raise FileNotFoundError(f"No cash_accounts rows found for baseline date {BASELINE_DATE}")
    cash_total = float(cash_baseline["balance_usd_m"].sum())
    _check_numeric(results, "cash account total equals 22.5", cash_total, EXPECTED_CASH)

    _record(
        results,
        "exactly 6 mock PDF documents exist",
        len(pdf_files) == EXPECTED_PDF_COUNT,
        f"pdf_count={len(pdf_files)}, expected={EXPECTED_PDF_COUNT}",
    )

    optional_tables = {
        "document_metadata": ["document_metadata", "document metadata"],
        "ground_truth_extractions": ["ground_truth_extractions", "ground truth extractions"],
        "validation_rules": ["validation_rules", "validation rules"],
        "table_name_map": ["table_name_map", "table name map"],
        "position_exposure_history": ["position_exposure_history", "position exposure history"],
        "public_instrument_classification": ["public_instrument_classification", "public instrument classification"],
        "public_proxy_risk_map": ["public_proxy_risk_map", "public proxy risk map"],
        "risk_free_proxy_monthly": ["risk_free_proxy_monthly", "risk free proxy monthly"],
        "region_taxonomy_reference": ["region_taxonomy_reference", "region taxonomy reference"],
    }
    optional_frames: dict[str, pd.DataFrame | None] = {}
    for logical_name, aliases in optional_tables.items():
        frame = _resolve_table(logical_name, aliases, assumptions, warnings)
        optional_frames[logical_name] = frame
        _record(
            results,
            f"{logical_name} table exists if available",
            frame is not None,
            "table located" if frame is not None else "table not located",
        )

    document_metadata = optional_frames.get("document_metadata")
    if document_metadata is not None:
        may_documents = document_metadata.loc[
            document_metadata["received_date"].astype(str).str.startswith("2026-05")
        ]
        if may_documents.empty:
            _record_warning(
                warnings,
                "document_metadata was found, but no May 2026 rows were detected for filename comparison.",
            )
        else:
            metadata_filenames = set(may_documents["file_name"].astype(str))
            available_filenames = {path.name for path in pdf_files}
            matched = metadata_filenames == available_filenames
            _record(
                results,
                "May document IDs in document_metadata match available PDF filenames if both are available",
                matched,
                f"metadata_files={sorted(metadata_filenames)}, available_files={sorted(available_filenames)}",
            )
    else:
        _record_warning(
            warnings,
            "Skipped May document filename reconciliation because document_metadata was unavailable.",
        )

    report_path = REPORTS_DIR / "data_qa_report.md"
    timestamp = datetime.now(timezone.utc).isoformat()
    passed_checks = [result for result in results if result.status == "passed"]
    failed_checks = [result for result in results if result.status == "failed"]

    report_lines = [
        "# Data QA Report",
        "",
        f"- Timestamp: `{timestamp}`",
        "",
        "## Repository Structure Summary",
        "",
        *[f"- {line}" for line in _path_summary()],
        "",
        "## Raw Files Found",
        "",
        *[f"- `{path.relative_to(REPO_ROOT)}`" for path in sorted(RAW_DATA_DIR.rglob("*")) if path.is_file()],
        "",
        "## CSV Files Found",
        "",
        *[f"- `{path.name}`" for path in csv_files],
        "",
        "## PDF Documents Found",
        "",
        *[f"- `{path.name}`" for path in pdf_files],
        "",
        "## Excel Sheets Found",
        "",
        *[f"- `{sheet}`" for sheet in excel_sheets],
        "",
        "## Checks Passed",
        "",
        *[f"- {item.name}: {item.details}" for item in passed_checks],
        "",
        "## Checks Failed",
        "",
        *(["- None"] if not failed_checks else [f"- {item.name}: {item.details}" for item in failed_checks]),
        "",
        "## Warnings",
        "",
        *(["- None"] if not warnings else [f"- {item}" for item in warnings]),
        "",
        "## Assumptions",
        "",
        *(["- Used CSV sources in preference to workbook sheets when both were available."] + [f"- {item}" for item in assumptions] if assumptions else ["- Used CSV sources in preference to workbook sheets when both were available."]),
        "",
        "## Recommended Next Step",
        "",
        "- Build schema definitions in `schemas/` and prepare the extraction module interface without modifying raw data.",
        "",
    ]
    if write_report:
        report_path.write_text("\n".join(report_lines), encoding="utf-8")

    return {
        "timestamp": timestamp,
        "passed": [asdict(item) for item in passed_checks],
        "failed": [asdict(item) for item in failed_checks],
        "warnings": warnings,
        "assumptions": assumptions,
        "csv_files": [str(path) for path in csv_files],
        "pdf_files": [str(path) for path in pdf_files],
        "excel_sheets": excel_sheets,
        "report_path": report_path,
    }


def main() -> int:
    results = run_all_checks(write_report=True)
    print(f"QA report written to {results['report_path']}")
    print(f"Passed checks: {len(results['passed'])}")
    print(f"Failed checks: {len(results['failed'])}")
    print(f"Warnings: {len(results['warnings'])}")
    return 0 if not results["failed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
