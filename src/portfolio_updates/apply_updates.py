from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from src.config import OUTPUTS_DIR, PROCESSED_DATA_DIR, REPORTS_DIR
from src.data_loader import read_csv_table, safe_find_table
from src.validation.review_decisions import apply_review_decisions_to_validation_results


def load_validation_status(mode: str = "baseline") -> dict[str, str]:
    _ = mode
    validation_path = OUTPUTS_DIR / "validation" / "validation_results_actual.csv"
    if not validation_path.exists():
        raise FileNotFoundError(f"Validation results not found: {validation_path}")
    results_df = apply_review_decisions_to_validation_results(pd.read_csv(validation_path))
    return results_df.groupby("document_id")["review_status"].first().to_dict()


def load_extracted_records(mode: str = "baseline") -> list[dict]:
    extracted_dir = OUTPUTS_DIR / "extracted_json" / mode
    if not extracted_dir.exists():
        raise FileNotFoundError(f"Extracted JSON directory not found: {extracted_dir}")
    records = []
    for path in sorted(extracted_dir.glob("*.json")):
        records.append(json.loads(path.read_text(encoding="utf-8")))
    if not records:
        raise FileNotFoundError(f"No extracted JSON files found in {extracted_dir}")
    return records


def _load_csv_if_available(possible_names: list[str]) -> pd.DataFrame | None:
    reference = safe_find_table(possible_names)
    if reference is None or reference.source != "csv":
        return None
    return read_csv_table(reference.name)


def load_baseline_positions() -> pd.DataFrame:
    table = _load_csv_if_available(["private_fund_positions", "private positions pre ingestion"])
    if table is None:
        raise FileNotFoundError("Unable to locate baseline private fund positions table.")
    return table.copy()


def load_baseline_cash_accounts() -> pd.DataFrame:
    table = _load_csv_if_available(["cash_accounts", "cash accounts"])
    if table is None:
        raise FileNotFoundError("Unable to locate baseline cash accounts table.")
    return table.copy()


def load_baseline_capital_calls() -> pd.DataFrame:
    table = _load_csv_if_available(["capital_calls"])
    return table.copy() if table is not None else pd.DataFrame()


def load_baseline_distributions() -> pd.DataFrame:
    table = _load_csv_if_available(["distributions"])
    return table.copy() if table is not None else pd.DataFrame()


def load_baseline_newsletters() -> pd.DataFrame:
    table = _load_csv_if_available(["newsletter_updates", "newsletter updates"])
    return table.copy() if table is not None else pd.DataFrame()


def load_expected_position_updates() -> pd.DataFrame:
    table = _load_csv_if_available(["expected_position_updates", "expected position updates"])
    return table.copy() if table is not None else pd.DataFrame()


def get_approved_records(records: list[dict], validation_status: dict[str, str]) -> list[dict]:
    return [record for record in records if validation_status.get(record["document_id"]) == "approved"]


def get_blocked_records(records: list[dict], validation_status: dict[str, str]) -> list[dict]:
    return [
        record
        for record in records
        if validation_status.get(record["document_id"]) in {"needs_review", "rejected"}
    ]


def _fund_name(record: dict) -> str | None:
    return record.get("fund_name_mapped") or record.get("fund_name_raw")


def _find_position_index(positions_df: pd.DataFrame, record: dict) -> int | None:
    fund_name = _fund_name(record)
    matches = positions_df.index[
        positions_df["fund_name"].astype(str).str.casefold() == str(fund_name).casefold()
    ].tolist()
    return matches[0] if matches else None


def _ensure_metadata_columns(df: pd.DataFrame) -> pd.DataFrame:
    for column in [
        "source_document_id",
        "update_type",
        "extraction_mode",
        "update_applied_flag",
        "update_reason",
    ]:
        if column not in df.columns:
            df[column] = None
    return df


def apply_capital_call_update(
    record: dict,
    positions_df: pd.DataFrame,
    cash_df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    positions_df = _ensure_metadata_columns(positions_df.copy())
    cash_df = _ensure_metadata_columns(cash_df.copy())
    extracted = record["extracted_fields"]
    position_index = _find_position_index(positions_df, record)

    if position_index is not None and extracted.get("amount_due") is not None:
        if pd.notna(positions_df.at[position_index, "paid_in_capital_usd_m"]):
            positions_df.at[position_index, "paid_in_capital_usd_m"] += extracted["amount_due"]
        if pd.notna(positions_df.at[position_index, "unfunded_commitment_usd_m"]):
            positions_df.at[position_index, "unfunded_commitment_usd_m"] -= extracted["amount_due"]
        positions_df.at[position_index, "source_document_id"] = record["document_id"]
        positions_df.at[position_index, "update_type"] = "capital_call"
        positions_df.at[position_index, "extraction_mode"] = record["extraction_mode"]
        positions_df.at[position_index, "update_applied_flag"] = True
        positions_df.at[position_index, "update_reason"] = "Applied approved capital call to baseline position."

    calendar_row = pd.DataFrame(
        [
            {
                "document_id": record["document_id"],
                "fund_name": _fund_name(record),
                "due_date": extracted.get("due_date"),
                "amount_due_usd_m": extracted.get("amount_due"),
                "currency": record.get("currency"),
                "source_document_id": record["document_id"],
                "update_type": "capital_call",
                "extraction_mode": record["extraction_mode"],
                "update_applied_flag": True,
                "update_reason": "Approved capital call added to projected call calendar; no booked cash change applied to the baseline state.",
            }
        ]
    )
    return positions_df, cash_df, calendar_row


def apply_distribution_update(record: dict, cash_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    cash_df = _ensure_metadata_columns(cash_df.copy())
    extracted = record["extracted_fields"]
    net_amount = extracted.get("net_distribution") or extracted.get("gross_distribution")
    payment_date = extracted.get("payment_date")

    cashflow_row = pd.DataFrame(
        [
            {
                "document_id": record["document_id"],
                "fund_name": _fund_name(record),
                "cashflow_type": "distribution",
                "cashflow_date": payment_date,
                "gross_distribution_usd_m": extracted.get("gross_distribution"),
                "net_distribution_usd_m": extracted.get("net_distribution"),
                "expected_cash_inflow_usd_m": net_amount,
                "currency": record.get("currency"),
                "source_document_id": record["document_id"],
                "update_type": "distribution",
                "liquidity_treatment": "projected_distribution",
                "extraction_mode": record["extraction_mode"],
                "update_applied_flag": True,
                "update_reason": "Approved distribution captured as a projected inflow; baseline cash remains unchanged until a future official close.",
            }
        ]
    )
    return cash_df, cashflow_row


def apply_capital_statement_update(record: dict, positions_df: pd.DataFrame) -> pd.DataFrame:
    positions_df = _ensure_metadata_columns(positions_df.copy())
    extracted = record["extracted_fields"]
    position_index = _find_position_index(positions_df, record)
    if position_index is None:
        return positions_df

    field_map = {
        "current_nav_usd_m": extracted.get("ending_nav"),
        "paid_in_capital_usd_m": extracted.get("paid_in_capital"),
        "unfunded_commitment_usd_m": extracted.get("unfunded_commitment"),
        "commitment_usd_m": extracted.get("total_commitment"),
        "last_statement_date": extracted.get("period_end_date"),
    }
    for column, value in field_map.items():
        if value is not None:
            positions_df.at[position_index, column] = value

    positions_df.at[position_index, "source_document_id"] = record["document_id"]
    positions_df.at[position_index, "update_type"] = "capital_statement"
    positions_df.at[position_index, "extraction_mode"] = record["extraction_mode"]
    positions_df.at[position_index, "update_applied_flag"] = True
    positions_df.at[position_index, "update_reason"] = "Applied approved capital statement to baseline position."
    return positions_df


def apply_newsletter_update(record: dict) -> pd.DataFrame:
    extracted = record["extracted_fields"]
    return pd.DataFrame(
        [
            {
                "document_id": record["document_id"],
                "fund_name": _fund_name(record),
                "reporting_period": record.get("reporting_period"),
                "market_themes": "; ".join(extracted.get("market_themes") or []),
                "risk_notes": "; ".join(extracted.get("risk_notes") or []),
                "valuation_commentary": "; ".join(extracted.get("valuation_commentary") or []),
                "expected_capital_activity": "; ".join(extracted.get("expected_capital_activity") or []),
                "source_document_id": record["document_id"],
                "update_type": "newsletter",
                "extraction_mode": record["extraction_mode"],
                "update_applied_flag": True,
                "update_reason": "Approved newsletter commentary captured for downstream review.",
            }
        ]
    )


def apply_expected_position_updates(
    positions_df: pd.DataFrame,
    approved_records: list[dict],
    expected_updates_df: pd.DataFrame,
) -> pd.DataFrame:
    if positions_df.empty or expected_updates_df.empty or "fund_id" not in positions_df.columns:
        return positions_df

    approved_document_ids = {record["document_id"] for record in approved_records}
    if not approved_document_ids:
        return positions_df

    updated_positions_df = positions_df.copy()
    working_updates_df = expected_updates_df.copy()
    if "update_status" in working_updates_df.columns:
        working_updates_df = working_updates_df[
            working_updates_df["update_status"].astype(str).str.casefold().eq("approved")
        ].copy()
    if working_updates_df.empty:
        return updated_positions_df

    for row in working_updates_df.itertuples():
        source_document_ids = {
            item.strip()
            for item in str(getattr(row, "source_document_ids", "")).split(",")
            if item and item.strip()
        }
        if not source_document_ids or not source_document_ids.issubset(approved_document_ids):
            continue

        match_index = updated_positions_df.index[updated_positions_df["fund_id"] == getattr(row, "fund_id")].tolist()
        if not match_index:
            continue
        position_index = match_index[0]

        field_map = {
            "paid_in_capital_usd_m": getattr(row, "post_paid_in_usd_m", None),
            "unfunded_commitment_usd_m": getattr(row, "post_unfunded_usd_m", None),
            "current_nav_usd_m": getattr(row, "post_nav_estimate_usd_m", None),
        }
        for column, value in field_map.items():
            if pd.notna(value):
                updated_positions_df.at[position_index, column] = value

        if hasattr(row, "as_of_date") and pd.notna(getattr(row, "as_of_date")) and "as_of_date" in updated_positions_df.columns:
            updated_positions_df.at[position_index, "as_of_date"] = getattr(row, "as_of_date")
        if "source_document_id" in updated_positions_df.columns:
            updated_positions_df.at[position_index, "source_document_id"] = ", ".join(sorted(source_document_ids))
        if "update_type" in updated_positions_df.columns:
            updated_positions_df.at[position_index, "update_type"] = "expected_position_update"
        if "update_reason" in updated_positions_df.columns:
            updated_positions_df.at[position_index, "update_reason"] = (
                "Applied approved expected position update from synthetic May document mapping."
            )
    return updated_positions_df


def _seed_historical_capital_call_cashflows(capital_calls_df: pd.DataFrame) -> pd.DataFrame:
    required = {"mapped_fund_name", "due_date", "amount_due_usd_m"}
    if capital_calls_df.empty or not required.issubset(capital_calls_df.columns):
        return pd.DataFrame()
    history_df = capital_calls_df.copy()
    history_df["review_status"] = history_df.get("review_status", "").astype(str)
    history_df["source"] = history_df.get("source", "").astype(str)
    history_df = history_df[
        history_df["review_status"].str.casefold().eq("approved")
        & history_df["source"].str.casefold().eq("historical_event")
    ].copy()
    if history_df.empty:
        return pd.DataFrame()
    history_df["amount_due_usd_m"] = pd.to_numeric(history_df["amount_due_usd_m"], errors="coerce")
    history_df = history_df.dropna(subset=["due_date", "amount_due_usd_m"])
    if history_df.empty:
        return pd.DataFrame()
    history_df = history_df.drop_duplicates(
        subset=[column for column in ["event_id", "mapped_fund_name", "due_date", "amount_due_usd_m"] if column in history_df.columns]
    )
    return pd.DataFrame(
        {
            "document_id": history_df.get("document_id"),
            "fund_name": history_df["mapped_fund_name"],
            "cashflow_type": "capital_call",
            "cashflow_date": history_df["due_date"],
            "gross_distribution_usd_m": None,
            "net_distribution_usd_m": None,
            "expected_cash_inflow_usd_m": -history_df["amount_due_usd_m"],
            "currency": history_df.get("currency"),
            "source_document_id": history_df.get("event_id"),
            "update_type": "historical_capital_call",
            "liquidity_treatment": "historical_reference",
            "extraction_mode": "baseline_history",
            "update_applied_flag": True,
            "update_reason": "Seeded approved historical capital call into private market cashflow history.",
        }
    )


def _seed_historical_distribution_cashflows(distributions_df: pd.DataFrame) -> pd.DataFrame:
    required = {"mapped_fund_name", "payment_date"}
    if distributions_df.empty or not required.issubset(distributions_df.columns):
        return pd.DataFrame()
    history_df = distributions_df.copy()
    history_df["review_status"] = history_df.get("review_status", "").astype(str)
    history_df["source"] = history_df.get("source", "").astype(str)
    history_df = history_df[
        history_df["review_status"].str.casefold().eq("approved")
        & history_df["source"].str.casefold().eq("historical_event")
    ].copy()
    if history_df.empty:
        return pd.DataFrame()
    amount_column = "net_distribution_usd_m" if "net_distribution_usd_m" in history_df.columns else "gross_distribution_usd_m"
    history_df[amount_column] = pd.to_numeric(history_df[amount_column], errors="coerce")
    history_df = history_df.dropna(subset=["payment_date", amount_column])
    if history_df.empty:
        return pd.DataFrame()
    history_df = history_df.drop_duplicates(
        subset=[
            column
            for column in ["event_id", "mapped_fund_name", "payment_date", "net_distribution_usd_m", "gross_distribution_usd_m"]
            if column in history_df.columns
        ]
    )
    return pd.DataFrame(
        {
            "document_id": history_df.get("document_id"),
            "fund_name": history_df["mapped_fund_name"],
            "cashflow_type": "distribution",
            "cashflow_date": history_df["payment_date"],
            "gross_distribution_usd_m": history_df.get("gross_distribution_usd_m"),
            "net_distribution_usd_m": history_df.get("net_distribution_usd_m"),
            "expected_cash_inflow_usd_m": history_df[amount_column],
            "currency": history_df.get("currency"),
            "source_document_id": history_df.get("event_id"),
            "update_type": "historical_distribution",
            "liquidity_treatment": "historical_reference",
            "extraction_mode": "baseline_history",
            "update_applied_flag": True,
            "update_reason": "Seeded approved historical distribution into private market cashflow history.",
        }
    )


def _deduplicate_cashflow_rows(cashflows_df: pd.DataFrame) -> pd.DataFrame:
    if cashflows_df.empty:
        return cashflows_df
    subset = [
        column
        for column in [
            "document_id",
            "fund_name",
            "cashflow_type",
            "cashflow_date",
            "expected_cash_inflow_usd_m",
            "gross_distribution_usd_m",
            "net_distribution_usd_m",
            "source_document_id",
            "update_type",
        ]
        if column in cashflows_df.columns
    ]
    if not subset:
        return cashflows_df
    return cashflows_df.drop_duplicates(subset=subset).reset_index(drop=True)


def _seed_historical_newsletters(newsletters_df: pd.DataFrame) -> pd.DataFrame:
    required = {"mapped_fund_name", "period"}
    if newsletters_df.empty or not required.issubset(newsletters_df.columns):
        return pd.DataFrame()
    history_df = newsletters_df.copy()
    history_df["review_status"] = history_df.get("review_status", "").astype(str)
    history_df["source"] = history_df.get("source", "").astype(str)
    history_df = history_df[
        history_df["review_status"].str.casefold().eq("approved")
        & history_df["source"].str.casefold().eq("historical_event")
    ].copy()
    if history_df.empty:
        return pd.DataFrame()
    return pd.DataFrame(
        {
            "document_id": history_df.get("document_id"),
            "fund_name": history_df["mapped_fund_name"],
            "reporting_period": history_df["period"],
            "market_themes": history_df.get("market_themes"),
            "risk_notes": history_df.get("risk_notes"),
            "valuation_commentary": history_df.get("valuation_commentary"),
            "expected_capital_activity": history_df.get("expected_capital_activity"),
            "source_document_id": history_df.get("update_id"),
            "update_type": "historical_newsletter",
            "extraction_mode": "baseline_history",
            "update_applied_flag": True,
            "update_reason": "Seeded approved historical newsletter commentary into post-ingestion commentary history.",
        }
    )


def _build_document_processing_status(
    records: list[dict],
    validation_status: dict[str, str],
    applied_document_ids: set[str],
) -> pd.DataFrame:
    blocked_reason_map: dict[str, str] = {}
    review_queue_path = OUTPUTS_DIR / "validation" / "review_queue_actual.csv"
    if review_queue_path.exists():
        review_queue_df = pd.read_csv(review_queue_path)
        blocked_reason_map = review_queue_df.set_index("document_id")["issue_summary"].to_dict()

    validation_results_path = OUTPUTS_DIR / "validation" / "validation_results_actual.csv"
    effective_validation_df = (
        apply_review_decisions_to_validation_results(pd.read_csv(validation_results_path))
        if validation_results_path.exists()
        else pd.DataFrame()
    )
    decision_columns = [
        "document_id",
        "extraction_mode",
        "system_review_status",
        "manual_review_status",
        "review_status_source",
        "reviewer_note",
        "reviewed_at_utc",
    ]
    if not effective_validation_df.empty:
        review_metadata_df = (
            effective_validation_df[decision_columns]
            .drop_duplicates(subset=["document_id", "extraction_mode"])
            .reset_index(drop=True)
        )
        review_metadata_lookup = {
            (str(row.document_id), str(row.extraction_mode)): row._asdict()
            for row in review_metadata_df.itertuples(index=False)
        }
    else:
        review_metadata_lookup = {}

    rows = []
    for record in records:
        review_status = validation_status.get(record["document_id"], "unknown")
        review_metadata = review_metadata_lookup.get((str(record["document_id"]), str(record["extraction_mode"])), {})
        rows.append(
            {
                "document_id": record["document_id"],
                "document_type": record["document_type"],
                "fund_name": _fund_name(record),
                "extraction_mode": record["extraction_mode"],
                "extraction_status": record["extraction_status"],
                "system_validation_review_status": review_metadata.get("system_review_status", review_status),
                "manual_review_status": review_metadata.get("manual_review_status"),
                "review_status_source": review_metadata.get("review_status_source", "system"),
                "reviewer_note": review_metadata.get("reviewer_note"),
                "reviewed_at_utc": review_metadata.get("reviewed_at_utc"),
                "validation_review_status": review_status,
                "update_applied_flag": record["document_id"] in applied_document_ids,
                "blocked_reason": "" if record["document_id"] in applied_document_ids else blocked_reason_map.get(record["document_id"], ""),
                "source_path": record["source_path"],
            }
        )
    return pd.DataFrame(rows)


def _write_update_summary(
    mode: str,
    records: list[dict],
    approved_records: list[dict],
    blocked_records: list[dict],
    applied_counts: dict[str, int],
    output_files: list[Path],
) -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    summary_path = REPORTS_DIR / "update_summary.md"
    timestamp = datetime.now(timezone.utc).isoformat()
    blocked_lines = [
        f"- `{record['document_id']}` | `{record['document_type']}` | status blocked"
        for record in blocked_records
    ]
    report_lines = [
        "# Update Summary",
        "",
        f"- Timestamp: `{timestamp}`",
        f"- Extraction mode: `{mode}`",
        f"- Number of extracted records: `{len(records)}`",
        f"- Number approved: `{len(approved_records)}`",
        f"- Number blocked: `{len(blocked_records)}`",
        "",
        "## Updates Applied By Document Type",
        "",
        *[f"- `{doc_type}`: `{count}`" for doc_type, count in applied_counts.items()],
        "",
        "## Blocked Documents",
        "",
        *(blocked_lines if blocked_lines else ["- None"]),
        "",
        "## Output Files Written",
        "",
        *[f"- `{path}`" for path in output_files],
        "",
        "## Assumptions",
        "",
        "- Only records with effective document-level validation status `approved` were applied.",
        "- The official portfolio baseline remains `2026-04-30`; approved May 2026 calls and distributions are tracked as projected overlay items rather than booked cash movements.",
        "- Newsletter updates create commentary output only and do not alter numeric portfolio state.",
        "",
        "## Recommended Next Step",
        "",
        "- Review any remaining blocked documents and promote only validated records into the portfolio overlay.",
    ]
    summary_path.write_text("\n".join(report_lines), encoding="utf-8")
    return summary_path


def run(mode: str = "baseline") -> dict[str, Any]:
    PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
    records = load_extracted_records(mode=mode)
    validation_status = load_validation_status(mode=mode)
    approved_records = get_approved_records(records, validation_status)
    blocked_records = get_blocked_records(records, validation_status)

    positions_df = load_baseline_positions()
    baseline_positions_df = positions_df.copy()
    cash_df = load_baseline_cash_accounts()
    baseline_capital_calls_df = load_baseline_capital_calls()
    baseline_distributions_df = load_baseline_distributions()
    baseline_newsletters_df = load_baseline_newsletters()
    expected_position_updates_df = load_expected_position_updates()
    positions_df = _ensure_metadata_columns(positions_df)
    cash_df = _ensure_metadata_columns(cash_df)

    capital_call_calendar_rows: list[pd.DataFrame] = []
    private_market_cashflow_rows: list[pd.DataFrame] = [
        _seed_historical_capital_call_cashflows(baseline_capital_calls_df),
        _seed_historical_distribution_cashflows(baseline_distributions_df),
    ]
    commentary_rows: list[pd.DataFrame] = [_seed_historical_newsletters(baseline_newsletters_df)]
    applied_counts = {"capital_call": 0, "distribution": 0, "capital_statement": 0, "newsletter": 0}
    applied_document_ids: set[str] = set()

    for record in approved_records:
        if record["document_type"] == "capital_call":
            positions_df, cash_df, calendar_row = apply_capital_call_update(record, positions_df, cash_df)
            capital_call_calendar_rows.append(calendar_row)
        elif record["document_type"] == "distribution":
            cash_df, cashflow_row = apply_distribution_update(record, cash_df)
            private_market_cashflow_rows.append(cashflow_row)
        elif record["document_type"] == "capital_statement":
            positions_df = apply_capital_statement_update(record, positions_df)
        elif record["document_type"] == "newsletter":
            commentary_rows.append(apply_newsletter_update(record))

        applied_counts[record["document_type"]] += 1
        applied_document_ids.add(record["document_id"])

    positions_df = apply_expected_position_updates(positions_df, approved_records, expected_position_updates_df)

    capital_call_calendar_df = (
        pd.concat(capital_call_calendar_rows, ignore_index=True)
        if capital_call_calendar_rows
        else pd.DataFrame(
            columns=[
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
        )
    )
    non_empty_cashflow_rows = [
        df.dropna(axis=1, how="all")
        for df in private_market_cashflow_rows
        if df is not None and not df.empty
    ]
    private_market_cashflows_df = (
        pd.concat(non_empty_cashflow_rows, ignore_index=True)
        if non_empty_cashflow_rows
        else pd.DataFrame(
            columns=[
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
        )
    )
    private_market_cashflows_df = _deduplicate_cashflow_rows(private_market_cashflows_df)
    commentary_df = (
        pd.concat([df for df in commentary_rows if df is not None and not df.empty], ignore_index=True)
        if any(df is not None and not df.empty for df in commentary_rows)
        else None
    )
    document_processing_status_df = _build_document_processing_status(records, validation_status, applied_document_ids)

    if not private_market_cashflows_df.empty and "cashflow_date" in private_market_cashflows_df.columns:
        private_market_cashflows_df["cashflow_date"] = pd.to_datetime(private_market_cashflows_df["cashflow_date"], errors="coerce")
        private_market_cashflows_df = private_market_cashflows_df.sort_values(["cashflow_date", "fund_name"]).reset_index(drop=True)
        private_market_cashflows_df["cashflow_date"] = private_market_cashflows_df["cashflow_date"].dt.strftime("%Y-%m-%d")
    if commentary_df is not None and not commentary_df.empty and "reporting_period" in commentary_df.columns:
        commentary_df = commentary_df.sort_values(["fund_name", "reporting_period"]).reset_index(drop=True)

    if "fund_id" in positions_df.columns and "fund_id" in baseline_positions_df.columns:
        baseline_lookup = baseline_positions_df.set_index("fund_id")
        for column in baseline_positions_df.columns:
            if column not in positions_df.columns:
                positions_df[column] = positions_df["fund_id"].map(baseline_lookup[column])

    outputs = {
        "private_positions": PROCESSED_DATA_DIR / "private_positions_post_ingestion.csv",
        "cash_accounts": PROCESSED_DATA_DIR / "cash_accounts_post_ingestion.csv",
        "capital_call_calendar": PROCESSED_DATA_DIR / "capital_call_calendar.csv",
        "private_market_cashflows": PROCESSED_DATA_DIR / "private_market_cashflows.csv",
        "document_processing_status": PROCESSED_DATA_DIR / "document_processing_status.csv",
    }
    positions_df.to_csv(outputs["private_positions"], index=False)
    cash_df.to_csv(outputs["cash_accounts"], index=False)
    capital_call_calendar_df.to_csv(outputs["capital_call_calendar"], index=False)
    private_market_cashflows_df.to_csv(outputs["private_market_cashflows"], index=False)
    document_processing_status_df.to_csv(outputs["document_processing_status"], index=False)

    output_files = list(outputs.values())
    if commentary_df is not None and not commentary_df.empty:
        commentary_path = PROCESSED_DATA_DIR / "fund_commentary_post_ingestion.csv"
        commentary_df.to_csv(commentary_path, index=False)
        output_files.append(commentary_path)

    summary_path = _write_update_summary(
        mode=mode,
        records=records,
        approved_records=approved_records,
        blocked_records=blocked_records,
        applied_counts=applied_counts,
        output_files=output_files,
    )
    output_files.append(summary_path)

    return {
        "records_processed": len(records),
        "approved_applied": len(approved_records),
        "blocked_count": len(blocked_records),
        "output_files": output_files,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply approved portfolio updates.")
    parser.add_argument("--mode", default="baseline", choices=["baseline", "intake", "llm"])
    args = parser.parse_args()
    results = run(mode=args.mode)
    print(
        f"processed={results['records_processed']} approved_applied={results['approved_applied']} "
        f"blocked={results['blocked_count']} outputs={len(results['output_files'])}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
