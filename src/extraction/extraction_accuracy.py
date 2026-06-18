from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from src.config import OUTPUTS_DIR, REPORTS_DIR
from src.data_loader import safe_find_csv


def load_ground_truth() -> pd.DataFrame | None:
    csv_path = safe_find_csv(["ground_truth_extractions", "ground truth extractions"])
    if csv_path is None or not csv_path.exists():
        return None
    return pd.read_csv(csv_path)


def flatten_extraction_record(record: dict) -> dict[str, Any]:
    extracted = record.get("extracted_fields", {})
    flat = {
        "document_id": record.get("document_id"),
        "document_type": record.get("document_type"),
        "fund_name": record.get("fund_name_mapped") or record.get("fund_name_raw"),
        "raw_fund_name": record.get("fund_name_raw"),
        "mapped_fund_name": record.get("fund_name_mapped"),
        "notice_date": record.get("notice_date"),
        "period": record.get("reporting_period"),
    }
    flat.update(extracted)

    if record.get("document_type") == "capital_call":
        flat["unfunded_commitment_after"] = extracted.get("unfunded_commitment")
    if record.get("document_type") == "capital_statement":
        flat["period_end"] = extracted.get("period_end_date")
        flat["fees_expenses"] = (extracted.get("management_fees") or 0.0) + (
            extracted.get("partnership_expenses") or 0.0
        )
        flat["commitment"] = extracted.get("total_commitment")
        flat["paid_in_plus_unfunded"] = (
            (extracted.get("paid_in_capital") or 0.0) + (extracted.get("unfunded_commitment") or 0.0)
        )
        flat["stated_ending_nav"] = extracted.get("ending_nav")
        if extracted.get("nav_roll_forward_variance") is not None and extracted.get("ending_nav") is not None:
            flat["calculated_ending_nav"] = round(
                extracted["ending_nav"] - extracted["nav_roll_forward_variance"], 4
            )
    if record.get("document_type") == "newsletter":
        for key in [
            "market_themes",
            "new_investments",
            "exits",
            "risk_notes",
            "valuation_commentary",
            "expected_capital_activity",
        ]:
            if isinstance(flat.get(key), list):
                flat[key] = "; ".join(flat[key])

    return flat


def _normalize_value(value: Any) -> Any:
    if pd.isna(value):
        return None
    if isinstance(value, str):
        value = value.strip()
        try:
            parsed_date = pd.to_datetime(value, errors="raise")
            return parsed_date.strftime("%Y-%m-%d")
        except Exception:
            pass
        try:
            return float(value)
        except ValueError:
            return value.casefold()
    return value


def _values_match(actual: Any, expected: Any, tolerance: float | None = None) -> bool:
    actual_norm = _normalize_value(actual)
    expected_norm = _normalize_value(expected)

    if actual_norm is None and expected_norm is None:
        return True
    if expected_norm == "missing":
        return actual_norm in (None, "", "missing")
    if isinstance(actual_norm, float) and isinstance(expected_norm, float):
        tol = tolerance if tolerance is not None and not pd.isna(tolerance) else 1e-6
        return abs(actual_norm - expected_norm) <= tol
    return actual_norm == expected_norm


def compare_extraction_to_ground_truth(extracted_records: list[dict], mode: str = "baseline") -> pd.DataFrame:
    ground_truth = load_ground_truth()
    if ground_truth is None:
        return pd.DataFrame(
            [
                {
                    "mode": mode,
                    "document_id": None,
                    "field_name": None,
                    "expected_value": None,
                    "actual_value": None,
                    "matched": False,
                    "warning": "Ground truth unavailable.",
                }
            ]
        )

    rows: list[dict[str, Any]] = []
    flattened = {record["document_id"]: flatten_extraction_record(record) for record in extracted_records}

    for gt_row in ground_truth.to_dict("records"):
        document_id = gt_row["document_id"]
        field_name = gt_row["field_name"]
        flat_record = flattened.get(document_id, {})
        actual_value = flat_record.get(field_name)
        matched = _values_match(actual_value, gt_row["expected_value"], gt_row.get("tolerance"))
        rows.append(
            {
                "mode": mode,
                "document_id": document_id,
                "field_name": field_name,
                "expected_value": gt_row["expected_value"],
                "actual_value": actual_value,
                "matched": matched,
                "warning": "",
            }
        )

    return pd.DataFrame(rows)


def write_accuracy_outputs(comparison_df: pd.DataFrame, mode: str = "baseline") -> dict[str, Path]:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    csv_path = OUTPUTS_DIR / f"{mode}_extraction_accuracy_summary.csv"
    report_path = REPORTS_DIR / f"{mode}_extraction_accuracy_summary.md"
    comparison_df.to_csv(csv_path, index=False)

    if "warning" in comparison_df.columns and comparison_df["warning"].astype(str).str.len().gt(0).any():
        report_lines = [
            f"# {mode.title()} Extraction Accuracy Summary",
            "",
            "- Warning: Ground truth data was unavailable, so no accuracy comparison was performed.",
        ]
    else:
        total = len(comparison_df)
        matched = int(comparison_df["matched"].sum())
        accuracy = matched / total if total else 0.0
        by_doc = comparison_df.groupby("document_id")["matched"].mean().sort_index()
        report_lines = [
            f"# {mode.title()} Extraction Accuracy Summary",
            "",
            f"- Total compared fields: `{total}`",
            f"- Matched fields: `{matched}`",
            f"- Accuracy: `{accuracy:.2%}`",
            "",
            "## Accuracy by Document",
            "",
            *[f"- `{document_id}`: `{score:.2%}`" for document_id, score in by_doc.items()],
        ]

    report_path.write_text("\n".join(report_lines), encoding="utf-8")
    return {"csv_path": csv_path, "report_path": report_path}
