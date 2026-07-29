from __future__ import annotations

import argparse
import shutil
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from src.config import (
    CSV_DIR,
    INGESTION_FILES_DIR,
    INGESTION_MANIFEST_PATH,
    MARKET_PRICES_DIR,
    OUTPUTS_DIR,
    PROCESSED_DATA_DIR,
    REVIEW_DECISIONS_PATH,
    REPORTS_DIR,
    RISK_OUTPUTS_DIR,
)
from src.portfolio_updates.apply_updates import (
    _ensure_metadata_columns,
    load_baseline_cash_accounts,
    load_baseline_positions,
)
from src.risk.refresh_public_market_data import trim_market_price_file_to_month_end
from src.risk.run_risk import run as run_risk_pipeline


def _backup_tree(paths: list[Path], destination_root: Path) -> list[Path]:
    copied_paths: list[Path] = []
    for path in paths:
        if not path.exists():
            continue
        target = destination_root / path.relative_to(path.parent.parent if path.parent != path else path.parent)
        if path.is_dir():
            shutil.copytree(path, target, dirs_exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
        copied_paths.append(target)
    return copied_paths


def _empty_frame(columns: list[str]) -> pd.DataFrame:
    return pd.DataFrame(columns=columns)


def _load_official_baseline_month_end() -> pd.Timestamp:
    baseline_summary_path = CSV_DIR / "portfolio_monthly_summary.csv"
    if not baseline_summary_path.exists():
        raise FileNotFoundError(f"Baseline monthly summary not found: {baseline_summary_path}")
    baseline_summary_df = pd.read_csv(baseline_summary_path)
    if "date" not in baseline_summary_df.columns:
        raise ValueError("Baseline monthly summary is missing a date column.")
    baseline_dates = pd.to_datetime(baseline_summary_df["date"], errors="coerce").dropna()
    if baseline_dates.empty:
        raise ValueError("Baseline monthly summary does not contain any valid dates.")
    return baseline_dates.max().to_period("M").to_timestamp("M")


def _reset_processed_outputs() -> list[Path]:
    PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)

    positions_df = _ensure_metadata_columns(load_baseline_positions().copy())
    cash_df = _ensure_metadata_columns(load_baseline_cash_accounts().copy())

    for df in (positions_df, cash_df):
        for column in ["source_document_id", "update_type", "extraction_mode", "update_reason"]:
            if column in df.columns:
                df[column] = None
        if "update_applied_flag" in df.columns:
            df["update_applied_flag"] = False

    outputs = {
        "private_positions_post_ingestion.csv": positions_df,
        "cash_accounts_post_ingestion.csv": cash_df,
        "capital_call_calendar.csv": _empty_frame(
            [
                "document_id",
                "fund_name",
                "due_date",
                "amount_due_usd_m",
                "currency",
                "source_document_id",
                "update_type",
                "extraction_mode",
                "update_applied_flag",
                "update_reason",
            ]
        ),
        "private_market_cashflows.csv": _empty_frame(
            [
                "document_id",
                "fund_name",
                "cashflow_type",
                "cashflow_date",
                "gross_distribution_usd_m",
                "net_distribution_usd_m",
                "expected_cash_inflow_usd_m",
                "currency",
                "source_document_id",
                "update_type",
                "liquidity_treatment",
                "extraction_mode",
                "update_applied_flag",
                "update_reason",
            ]
        ),
        "document_processing_status.csv": _empty_frame(
            [
                "document_id",
                "document_type",
                "fund_name",
                "extraction_mode",
                "extraction_status",
                "validation_review_status",
                "update_applied_flag",
                "blocked_reason",
                "source_path",
            ]
        ),
        "fund_commentary_post_ingestion.csv": _empty_frame(
            [
                "document_id",
                "fund_name",
                "reporting_period",
                "market_themes",
                "risk_notes",
                "valuation_commentary",
                "expected_capital_activity",
                "source_document_id",
                "update_type",
                "extraction_mode",
                "update_applied_flag",
                "update_reason",
            ]
        ),
    }

    written_paths: list[Path] = []
    for filename, dataframe in outputs.items():
        path = PROCESSED_DATA_DIR / filename
        dataframe.to_csv(path, index=False)
        written_paths.append(path)
    return written_paths


def _reset_intake_artifacts() -> list[Path]:
    written_paths: list[Path] = []
    intake_extracted_dir = OUTPUTS_DIR / "extracted_json" / "intake"
    if intake_extracted_dir.exists():
        shutil.rmtree(intake_extracted_dir)
    intake_extracted_dir.mkdir(parents=True, exist_ok=True)
    written_paths.append(intake_extracted_dir)

    validation_dir = OUTPUTS_DIR / "validation"
    validation_dir.mkdir(parents=True, exist_ok=True)
    for filename, columns in {
        "validation_results_actual.csv": [
            "document_id",
            "document_type",
            "fund_name",
            "extraction_mode",
            "rule_id",
            "rule_name",
            "status",
            "severity",
            "field_name",
            "expected_value",
            "actual_value",
            "message",
            "review_status",
        ],
        "review_queue_actual.csv": [
            "document_id",
            "document_type",
            "fund_name",
            "extraction_mode",
            "review_status",
            "issue_count",
            "highest_severity",
            "issue_summary",
            "recommended_action",
            "source_path",
        ],
    }.items():
        path = validation_dir / filename
        _empty_frame(columns).to_csv(path, index=False)
        written_paths.append(path)

    update_summary_path = REPORTS_DIR / "update_summary.md"
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    update_summary_path.write_text(
        "\n".join(
            [
                "# Update Summary",
                "",
                "- Reset for intake upload test.",
                "- No uploaded documents have been extracted or applied yet.",
            ]
        ),
        encoding="utf-8",
    )
    written_paths.append(update_summary_path)

    if INGESTION_FILES_DIR.exists():
        shutil.rmtree(INGESTION_FILES_DIR)
    INGESTION_FILES_DIR.mkdir(parents=True, exist_ok=True)
    written_paths.append(INGESTION_FILES_DIR)

    if INGESTION_MANIFEST_PATH.exists():
        INGESTION_MANIFEST_PATH.unlink()
    INGESTION_MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    _empty_frame(
        [
            "document_id",
            "original_filename",
            "stored_filename",
            "stored_path",
            "file_size_bytes",
            "sha256",
            "source_type",
            "ingestion_status",
            "pipeline_readiness",
            "portfolio_state_impact",
            "review_status",
            "approval_source",
            "review_note",
            "staged_at_utc",
        ]
    ).to_csv(INGESTION_MANIFEST_PATH, index=False)
    written_paths.append(INGESTION_MANIFEST_PATH)

    if REVIEW_DECISIONS_PATH.exists():
        REVIEW_DECISIONS_PATH.unlink()
    REVIEW_DECISIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
    _empty_frame(
        [
            "document_id",
            "extraction_mode",
            "manual_review_status",
            "reviewer_note",
            "reviewed_at_utc",
        ]
    ).to_csv(REVIEW_DECISIONS_PATH, index=False)
    written_paths.append(REVIEW_DECISIONS_PATH)

    return written_paths


def _reset_external_market_outputs() -> list[Path]:
    baseline_month_end = _load_official_baseline_month_end()
    written_paths: list[Path] = []

    market_prices_path = MARKET_PRICES_DIR / "yfinance_monthly_prices.csv"
    if market_prices_path.exists():
        trim_market_price_file_to_month_end(market_prices_path, baseline_month_end)
        written_paths.append(market_prices_path)

    risk_results = run_risk_pipeline()
    written_paths.extend(Path(path) for path in risk_results["output_files"])
    return written_paths


def run() -> dict[str, object]:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_root = OUTPUTS_DIR / "test_backups" / f"upload_intake_prep_{timestamp}"
    backup_root.mkdir(parents=True, exist_ok=True)

    backed_up_paths = _backup_tree(
        [
            PROCESSED_DATA_DIR,
            MARKET_PRICES_DIR,
            RISK_OUTPUTS_DIR,
            OUTPUTS_DIR / "validation",
            OUTPUTS_DIR / "extracted_json" / "baseline",
            OUTPUTS_DIR / "extracted_json" / "intake",
            REPORTS_DIR / "update_summary.md",
            INGESTION_MANIFEST_PATH,
            INGESTION_FILES_DIR,
            REVIEW_DECISIONS_PATH,
        ],
        backup_root,
    )
    reset_paths = _reset_processed_outputs() + _reset_intake_artifacts() + _reset_external_market_outputs()

    return {
        "backup_root": backup_root,
        "backed_up_paths": backed_up_paths,
        "reset_paths": reset_paths,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare baseline-only dashboard state for intake upload testing.")
    _ = parser.parse_args()
    results = run()
    print(
        f"backup_root={results['backup_root']} backed_up={len(results['backed_up_paths'])} "
        f"reset_outputs={len(results['reset_paths'])}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
