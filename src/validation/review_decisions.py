from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd

from src.config import REVIEW_DECISIONS_PATH


REVIEW_DECISION_COLUMNS = [
    "document_id",
    "extraction_mode",
    "manual_review_status",
    "reviewer_note",
    "reviewed_at_utc",
]
VALID_REVIEW_STATUSES = {"approved", "needs_review", "rejected"}


def _empty_review_decisions() -> pd.DataFrame:
    return pd.DataFrame(columns=REVIEW_DECISION_COLUMNS)


def _normalize_review_status(value: object) -> str | None:
    if value is None or pd.isna(value):
        return None
    normalized = str(value).strip().casefold()
    return normalized if normalized in VALID_REVIEW_STATUSES else None


def load_review_decisions() -> pd.DataFrame:
    if not REVIEW_DECISIONS_PATH.exists():
        return _empty_review_decisions()

    decisions_df = pd.read_csv(REVIEW_DECISIONS_PATH)
    if decisions_df.empty:
        return _empty_review_decisions()

    for column in REVIEW_DECISION_COLUMNS:
        if column not in decisions_df.columns:
            decisions_df[column] = pd.NA

    decisions_df["manual_review_status"] = decisions_df["manual_review_status"].map(_normalize_review_status)
    decisions_df = decisions_df.dropna(subset=["document_id"])
    return decisions_df[REVIEW_DECISION_COLUMNS].copy()


def write_review_decisions(decisions_df: pd.DataFrame) -> None:
    REVIEW_DECISIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
    normalized_df = _empty_review_decisions() if decisions_df.empty else decisions_df.copy()
    for column in REVIEW_DECISION_COLUMNS:
        if column not in normalized_df.columns:
            normalized_df[column] = pd.NA
    normalized_df[REVIEW_DECISION_COLUMNS].to_csv(REVIEW_DECISIONS_PATH, index=False)


def upsert_review_decision(
    *,
    document_id: str,
    extraction_mode: str,
    manual_review_status: str | None,
    reviewer_note: str = "",
) -> pd.DataFrame:
    decisions_df = load_review_decisions()
    mask = (
        decisions_df["document_id"].astype(str).eq(str(document_id))
        & decisions_df["extraction_mode"].astype(str).eq(str(extraction_mode))
    )
    normalized_status = _normalize_review_status(manual_review_status)

    if normalized_status is None:
        if mask.any():
            decisions_df = decisions_df.loc[~mask].reset_index(drop=True)
    else:
        row = {
            "document_id": str(document_id),
            "extraction_mode": str(extraction_mode),
            "manual_review_status": normalized_status,
            "reviewer_note": reviewer_note.strip(),
            "reviewed_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        }
        if mask.any():
            row_index = decisions_df.index[mask][0]
            for key, value in row.items():
                decisions_df.at[row_index, key] = value
        else:
            decisions_df = pd.concat([decisions_df, pd.DataFrame([row])], ignore_index=True)

    write_review_decisions(decisions_df)
    return decisions_df


def apply_review_decisions_to_validation_results(validation_results_df: pd.DataFrame) -> pd.DataFrame:
    if validation_results_df.empty:
        return validation_results_df.copy()

    effective_df = validation_results_df.copy()
    if "review_status" not in effective_df.columns or "document_id" not in effective_df.columns:
        return effective_df

    effective_df["system_review_status"] = effective_df["review_status"].astype(str).str.casefold()
    effective_df["manual_review_status"] = pd.NA
    effective_df["review_status_source"] = "system"
    effective_df["reviewer_note"] = pd.NA
    effective_df["reviewed_at_utc"] = pd.NA

    decisions_df = load_review_decisions()
    if decisions_df.empty:
        effective_df["review_status"] = effective_df["system_review_status"]
        return effective_df

    decision_lookup = {
        (str(row.document_id), str(row.extraction_mode)): row
        for row in decisions_df.itertuples()
        if _normalize_review_status(row.manual_review_status) is not None
    }

    for index, row in effective_df.iterrows():
        key = (str(row.get("document_id", "")), str(row.get("extraction_mode", "")))
        decision = decision_lookup.get(key)
        if decision is None:
            continue
        effective_df.at[index, "manual_review_status"] = decision.manual_review_status
        effective_df.at[index, "review_status"] = decision.manual_review_status
        effective_df.at[index, "review_status_source"] = "manual_override"
        effective_df.at[index, "reviewer_note"] = decision.reviewer_note
        effective_df.at[index, "reviewed_at_utc"] = decision.reviewed_at_utc

    effective_df["review_status"] = effective_df["review_status"].astype(str).str.casefold()
    return effective_df


def build_effective_review_queue(
    review_queue_df: pd.DataFrame,
    validation_results_df: pd.DataFrame,
    *,
    unresolved_only: bool = True,
) -> pd.DataFrame:
    if review_queue_df.empty:
        return review_queue_df.copy()

    effective_df = review_queue_df.copy()
    effective_df["system_review_status"] = effective_df.get("review_status", pd.Series(dtype=str)).astype(str).str.casefold()
    effective_df["manual_review_status"] = pd.NA
    effective_df["review_status_source"] = "system"
    effective_df["reviewer_note"] = pd.NA
    effective_df["reviewed_at_utc"] = pd.NA

    decisions_df = load_review_decisions()
    if not decisions_df.empty:
        decision_lookup = {
            (str(row.document_id), str(row.extraction_mode)): row
            for row in decisions_df.itertuples()
            if _normalize_review_status(row.manual_review_status) is not None
        }
        for index, row in effective_df.iterrows():
            key = (str(row.get("document_id", "")), str(row.get("extraction_mode", "")))
            decision = decision_lookup.get(key)
            if decision is None:
                continue
            effective_df.at[index, "manual_review_status"] = decision.manual_review_status
            effective_df.at[index, "review_status"] = decision.manual_review_status
            effective_df.at[index, "review_status_source"] = "manual_override"
            effective_df.at[index, "reviewer_note"] = decision.reviewer_note
            effective_df.at[index, "reviewed_at_utc"] = decision.reviewed_at_utc

    if not validation_results_df.empty and {"document_id", "review_status"}.issubset(validation_results_df.columns):
        effective_status_by_document = (
            validation_results_df.groupby(["document_id", "extraction_mode"], dropna=False)["review_status"].first().to_dict()
            if "extraction_mode" in validation_results_df.columns
            else validation_results_df.groupby("document_id")["review_status"].first().to_dict()
        )
        for index, row in effective_df.iterrows():
            if "extraction_mode" in validation_results_df.columns:
                lookup_key = (row.get("document_id"), row.get("extraction_mode"))
            else:
                lookup_key = row.get("document_id")
            effective_status = effective_status_by_document.get(lookup_key)
            if effective_status:
                effective_df.at[index, "review_status"] = str(effective_status).casefold()

    if unresolved_only:
        effective_df = effective_df[effective_df["review_status"].astype(str).str.casefold() != "approved"].reset_index(drop=True)
    return effective_df
