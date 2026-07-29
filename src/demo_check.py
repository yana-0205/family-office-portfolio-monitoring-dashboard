from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from src.config import OUTPUTS_DIR, PROCESSED_DATA_DIR, REPORTS_DIR


EXPECTED_EXTRACTED_JSON_COUNT = 6
EXPECTED_APPROVED_COUNT = 3
EXPECTED_NEEDS_REVIEW_COUNT = 2
EXPECTED_REJECTED_COUNT = 1
EXPECTED_APPLIED_UPDATES = 3
EXPECTED_BLOCKED_UPDATES = 3
EXPECTED_PROXY_TICKERS = 30
EXPECTED_RISK_DATA_SOURCE = "real"


@dataclass
class DemoCheckResult:
    name: str
    status: str
    details: str


def _record(results: list[DemoCheckResult], name: str, passed: bool, details: str) -> None:
    results.append(DemoCheckResult(name=name, status="passed" if passed else "failed", details=details))


def _check_path(results: list[DemoCheckResult], path: Path, label: str) -> None:
    _record(results, label, path.exists(), f"{path} exists={path.exists()}")


def _status_count(document_status_df: pd.DataFrame, status: str) -> int:
    if document_status_df.empty or "validation_review_status" not in document_status_df.columns:
        return 0
    return int((document_status_df["validation_review_status"].astype(str) == status).sum())


def _write_report(
    report_path: Path,
    passed: list[DemoCheckResult],
    failed: list[DemoCheckResult],
    summary: dict[str, Any],
) -> None:
    timestamp = datetime.now(timezone.utc).isoformat()
    lines = [
        "# Demo Readiness Report",
        "",
        f"- Generated at: `{timestamp}`",
        f"- Extracted JSON files: `{summary['extracted_json_count']}`",
        f"- Validation status: `{summary['approved_count']} approved / {summary['needs_review_count']} needs_review / {summary['rejected_count']} rejected`",
        f"- Applied updates: `{summary['applied_updates']}`",
        f"- Blocked updates: `{summary['blocked_updates']}`",
        f"- Risk data source: `{summary['risk_data_source']}`",
        f"- Risk proxy tickers: `{summary['risk_proxy_tickers']}`",
        "",
        "## Passed Checks",
        *(["- None"] if not passed else [f"- {item.name}: {item.details}" for item in passed]),
        "",
        "## Failed Checks",
        *(["- None"] if not failed else [f"- {item.name}: {item.details}" for item in failed]),
        "",
        "## Recommended Next Step",
        "- If all checks pass, launch `streamlit run app.py` for demo presentation.",
    ]
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_demo_check(write_report: bool = True) -> dict[str, Any]:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    results: list[DemoCheckResult] = []

    extracted_dir = OUTPUTS_DIR / "extracted_json" / "baseline"
    validation_path = OUTPUTS_DIR / "validation" / "validation_results_actual.csv"
    review_queue_path = OUTPUTS_DIR / "validation" / "review_queue_actual.csv"
    risk_metrics_path = OUTPUTS_DIR / "risk" / "public_risk_metrics.csv"
    update_summary_path = REPORTS_DIR / "update_summary.md"
    document_status_path = PROCESSED_DATA_DIR / "document_processing_status.csv"

    required_processed_outputs = [
        PROCESSED_DATA_DIR / "private_positions_post_ingestion.csv",
        PROCESSED_DATA_DIR / "cash_accounts_post_ingestion.csv",
        PROCESSED_DATA_DIR / "capital_call_calendar.csv",
        PROCESSED_DATA_DIR / "private_market_cashflows.csv",
        PROCESSED_DATA_DIR / "document_processing_status.csv",
        PROCESSED_DATA_DIR / "fund_commentary_post_ingestion.csv",
    ]

    for path, label in [
        (extracted_dir, "baseline extraction output directory exists"),
        (validation_path, "validation results output exists"),
        (review_queue_path, "review queue output exists"),
        (risk_metrics_path, "risk metrics output exists"),
        (update_summary_path, "update summary report exists"),
        (document_status_path, "document processing status exists"),
    ]:
        _check_path(results, path, label)

    for path in required_processed_outputs:
        _check_path(results, path, f"processed output exists: {path.name}")

    extracted_json_count = len(list(extracted_dir.glob("*.json"))) if extracted_dir.exists() else 0
    _record(
        results,
        "baseline extraction produced 6 JSON files",
        extracted_json_count == EXPECTED_EXTRACTED_JSON_COUNT,
        f"actual={extracted_json_count}, expected={EXPECTED_EXTRACTED_JSON_COUNT}",
    )

    document_status_df = pd.read_csv(document_status_path) if document_status_path.exists() else pd.DataFrame()
    approved_count = _status_count(document_status_df, "approved")
    needs_review_count = _status_count(document_status_df, "needs_review")
    rejected_count = _status_count(document_status_df, "rejected")
    applied_updates = (
        int(document_status_df["update_applied_flag"].fillna(False).astype(bool).sum())
        if not document_status_df.empty and "update_applied_flag" in document_status_df.columns
        else 0
    )
    blocked_updates = len(document_status_df) - applied_updates if not document_status_df.empty else 0

    for name, actual, expected in [
        ("approved documents count is 3", approved_count, EXPECTED_APPROVED_COUNT),
        ("needs_review documents count is 2", needs_review_count, EXPECTED_NEEDS_REVIEW_COUNT),
        ("rejected documents count is 1", rejected_count, EXPECTED_REJECTED_COUNT),
        ("applied updates count is 3", applied_updates, EXPECTED_APPLIED_UPDATES),
        ("blocked updates count is 3", blocked_updates, EXPECTED_BLOCKED_UPDATES),
    ]:
        _record(results, name, actual == expected, f"actual={actual}, expected={expected}")

    risk_metrics_df = pd.read_csv(risk_metrics_path) if risk_metrics_path.exists() else pd.DataFrame()
    risk_data_source = None
    risk_proxy_tickers = 0
    if not risk_metrics_df.empty:
        if "data_source" in risk_metrics_df.columns:
            unique_sources = sorted(risk_metrics_df["data_source"].dropna().astype(str).unique().tolist())
            risk_data_source = unique_sources[0] if len(unique_sources) == 1 else ",".join(unique_sources)
        if "ticker" in risk_metrics_df.columns:
            risk_proxy_tickers = int(risk_metrics_df["ticker"].nunique())

    _record(
        results,
        "risk data source is real",
        risk_data_source == EXPECTED_RISK_DATA_SOURCE,
        f"actual={risk_data_source}, expected={EXPECTED_RISK_DATA_SOURCE}",
    )
    _record(
        results,
        "risk proxy ticker count is 30",
        risk_proxy_tickers == EXPECTED_PROXY_TICKERS,
        f"actual={risk_proxy_tickers}, expected={EXPECTED_PROXY_TICKERS}",
    )

    summary = {
        "extracted_json_count": extracted_json_count,
        "approved_count": approved_count,
        "needs_review_count": needs_review_count,
        "rejected_count": rejected_count,
        "applied_updates": applied_updates,
        "blocked_updates": blocked_updates,
        "risk_data_source": risk_data_source,
        "risk_proxy_tickers": risk_proxy_tickers,
    }

    passed = [item for item in results if item.status == "passed"]
    failed = [item for item in results if item.status == "failed"]
    report_path = REPORTS_DIR / "demo_readiness_report.md"
    if write_report:
        _write_report(report_path, passed, failed, summary)

    return {
        "summary": summary,
        "passed": [asdict(item) for item in passed],
        "failed": [asdict(item) for item in failed],
        "report_path": report_path,
    }


def main() -> None:
    results = run_demo_check(write_report=True)
    print("Demo readiness complete.")
    print(f"Passed checks: {len(results['passed'])}")
    print(f"Failed checks: {len(results['failed'])}")
    print(f"Report: {results['report_path']}")


if __name__ == "__main__":
    main()
