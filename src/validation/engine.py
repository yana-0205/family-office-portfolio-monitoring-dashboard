from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from src.config import OUTPUTS_DIR
from src.data_loader import read_csv_table, safe_find_table
from src.validation.rules import (
    check_cash_sufficiency,
    check_commitment_consistency,
    check_distribution_component_sum,
    check_due_date_urgency,
    check_fund_master_match,
    check_fuzzy_fund_name_warning,
    check_low_confidence_review,
    check_nav_roll_forward,
    check_required_field_completeness,
)


def load_extracted_records(mode: str = "baseline") -> list[dict]:
    extracted_dir = OUTPUTS_DIR / "extracted_json" / mode
    if not extracted_dir.exists():
        raise FileNotFoundError(f"Extracted JSON directory not found: {extracted_dir}")
    records = []
    for path in sorted(extracted_dir.glob("*.json")):
        records.append(json.loads(path.read_text(encoding="utf-8")))
    if not records:
        raise FileNotFoundError(f"No extracted JSON records found in {extracted_dir}")
    return records


def _load_optional_table(possible_names: list[str]) -> pd.DataFrame | None:
    reference = safe_find_table(possible_names)
    if reference is None or reference.source != "csv":
        return None
    return read_csv_table(reference.name)


def _load_validation_tables() -> dict[str, pd.DataFrame]:
    tables = {
        "private_fund_master": _load_optional_table(["private_fund_master"]),
        "fund_aliases": _load_optional_table(["fund_aliases"]),
        "private_fund_positions": _load_optional_table(["private_fund_positions"]),
        "cash_accounts": _load_optional_table(["cash_accounts"]),
        "validation_rules": _load_optional_table(["validation_rules"]),
    }
    return {key: value for key, value in tables.items() if value is not None}


def determine_review_status(rule_results: list[dict[str, Any]]) -> str:
    failed_results = [result for result in rule_results if result["status"] == "failed"]
    warning_results = [result for result in rule_results if result["status"] == "warning"]

    if any(result["severity"] == "critical" for result in failed_results):
        return "rejected"
    if any(result["rule_id"] in {"VR002", "VR005", "VR006"} for result in failed_results):
        return "rejected"
    if failed_results:
        return "needs_review"
    if any(result["severity"] in {"high", "critical"} for result in warning_results):
        return "needs_review"
    if warning_results:
        return "needs_review"
    return "approved"


def validate_record(record: dict, tables: dict[str, pd.DataFrame]) -> dict[str, Any]:
    rule_results = [
        check_fund_master_match(record, tables),
        check_required_field_completeness(record),
        check_due_date_urgency(record),
        check_cash_sufficiency(record, tables),
        check_commitment_consistency(record),
        check_nav_roll_forward(record),
        check_distribution_component_sum(record),
        check_fuzzy_fund_name_warning(record, tables),
        check_low_confidence_review(record),
    ]
    review_status = determine_review_status(rule_results)
    return {
        "record": record,
        "rule_results": rule_results,
        "review_status": review_status,
    }


def validate_all_records(mode: str = "baseline") -> list[dict[str, Any]]:
    records = load_extracted_records(mode=mode)
    tables = _load_validation_tables()
    return [validate_record(record, tables) for record in records]


def build_validation_results_df(records_with_results: list[dict[str, Any]]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for item in records_with_results:
        record = item["record"]
        fund_name = record.get("fund_name_mapped") or record.get("fund_name_raw")
        for result in item["rule_results"]:
            rows.append(
                {
                    "document_id": record.get("document_id"),
                    "document_type": record.get("document_type"),
                    "fund_name": fund_name,
                    "extraction_mode": record.get("extraction_mode"),
                    "rule_id": result["rule_id"],
                    "rule_name": result["rule_name"],
                    "status": result["status"],
                    "severity": result["severity"],
                    "field_name": result["field_name"],
                    "expected_value": result["expected_value"],
                    "actual_value": result["actual_value"],
                    "message": result["message"],
                    "review_status": item["review_status"],
                }
            )
    return pd.DataFrame(rows)


def build_review_queue_df(records_with_results: list[dict[str, Any]]) -> pd.DataFrame:
    severity_rank = {"info": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}
    queue_rows: list[dict[str, Any]] = []

    for item in records_with_results:
        review_status = item["review_status"]
        if review_status == "approved":
            continue

        record = item["record"]
        issues = [result for result in item["rule_results"] if result["status"] in {"warning", "failed"}]
        highest = max(issues, key=lambda result: severity_rank[result["severity"]]) if issues else None
        queue_rows.append(
            {
                "document_id": record.get("document_id"),
                "document_type": record.get("document_type"),
                "fund_name": record.get("fund_name_mapped") or record.get("fund_name_raw"),
                "extraction_mode": record.get("extraction_mode"),
                "review_status": review_status,
                "issue_count": len(issues),
                "highest_severity": highest["severity"] if highest else "info",
                "issue_summary": "; ".join(issue["rule_name"] for issue in issues),
                "recommended_action": (
                    "Reject and correct extraction before downstream use."
                    if review_status == "rejected"
                    else "Analyst review required before downstream use."
                ),
                "source_path": record.get("source_path"),
            }
        )

    return pd.DataFrame(queue_rows)
