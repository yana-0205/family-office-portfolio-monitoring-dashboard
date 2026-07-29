from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from src.config import INGESTION_FILES_DIR, INGESTION_MANIFEST_PATH
from src.extraction.pdf_reader import extract_document_id


INBOX_COLUMNS = [
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


def _empty_inbox() -> pd.DataFrame:
    return pd.DataFrame(columns=INBOX_COLUMNS)


def _sanitize_filename(filename: str) -> str:
    basename = Path(filename).name.strip()
    if not basename:
        raise ValueError("Uploaded file must have a valid filename.")
    sanitized = re.sub(r"[^A-Za-z0-9._-]+", "_", basename)
    return sanitized.strip("._") or "uploaded_document.pdf"


def _ensure_inbox_dirs() -> None:
    INGESTION_FILES_DIR.mkdir(parents=True, exist_ok=True)
    INGESTION_MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)


def load_ingestion_inbox() -> pd.DataFrame:
    if not INGESTION_MANIFEST_PATH.exists():
        return _empty_inbox()

    inbox_df = pd.read_csv(INGESTION_MANIFEST_PATH)
    if inbox_df.empty:
        return _empty_inbox()

    for column in INBOX_COLUMNS:
        if column not in inbox_df.columns:
            inbox_df[column] = pd.NA

    return inbox_df[INBOX_COLUMNS].copy()


def stage_uploaded_pdf(filename: str, file_bytes: bytes, source_type: str = "streamlit_upload") -> dict[str, object]:
    if not filename.lower().endswith(".pdf"):
        raise ValueError(f"Uploaded file must be a PDF: {filename}")
    if not file_bytes:
        raise ValueError(f"Uploaded PDF is empty: {filename}")

    _ensure_inbox_dirs()

    safe_name = _sanitize_filename(filename)
    sha256 = hashlib.sha256(file_bytes).hexdigest()
    inbox_df = load_ingestion_inbox()

    if not inbox_df.empty and "sha256" in inbox_df.columns:
        existing_rows = inbox_df[inbox_df["sha256"].astype(str) == sha256]
        if not existing_rows.empty:
            existing_record = existing_rows.iloc[0].to_dict()
            existing_record["action"] = "duplicate"
            return existing_record

    staged_at = datetime.now(timezone.utc).replace(microsecond=0)
    timestamp = staged_at.strftime("%Y%m%dT%H%M%SZ")
    stored_filename = f"{timestamp}_{sha256[:8]}_{safe_name}"
    stored_path = INGESTION_FILES_DIR / stored_filename
    stored_path.write_bytes(file_bytes)

    record = {
        "document_id": extract_document_id(safe_name),
        "original_filename": safe_name,
        "stored_filename": stored_filename,
        "stored_path": str(stored_path),
        "file_size_bytes": len(file_bytes),
        "sha256": sha256,
        "source_type": source_type,
        "ingestion_status": "staged",
        "pipeline_readiness": "awaiting_offline_extraction",
        "portfolio_state_impact": "none_until_reviewed",
        "review_status": "pending",
        "approval_source": "",
        "review_note": "",
        "staged_at_utc": staged_at.isoformat().replace("+00:00", "Z"),
    }

    updated_df = pd.concat([inbox_df, pd.DataFrame([record])], ignore_index=True)
    updated_df.to_csv(INGESTION_MANIFEST_PATH, index=False)

    result = dict(record)
    result["action"] = "staged"
    return result


def sync_ingestion_status(document_status_df: pd.DataFrame) -> pd.DataFrame:
    inbox_df = load_ingestion_inbox()
    if inbox_df.empty:
        return inbox_df

    status_lookup = {}
    if not document_status_df.empty and "document_id" in document_status_df.columns:
        status_lookup = document_status_df.set_index("document_id").to_dict(orient="index")

    updated_df = inbox_df.copy()
    for column in ["review_status", "approval_source", "review_note"]:
        updated_df[column] = updated_df[column].astype("object")
    for index, row in updated_df.iterrows():
        document_status = status_lookup.get(str(row["document_id"]))
        if document_status is None:
            continue

        review_status = str(document_status.get("validation_review_status", "unknown"))
        applied_flag = bool(document_status.get("update_applied_flag", False))
        review_status_source = str(document_status.get("review_status_source", "system"))
        reviewer_note = document_status.get("reviewer_note", "")
        reviewer_note = "" if pd.isna(reviewer_note) else str(reviewer_note).strip()
        updated_df.at[index, "ingestion_status"] = "processed"
        updated_df.at[index, "review_status"] = review_status
        updated_df.at[index, "approval_source"] = (
            "manual" if review_status_source == "manual_override" else "system"
        )
        updated_df.at[index, "review_note"] = (
            f"Manually approved. {reviewer_note}".strip()
            if review_status == "approved" and review_status_source == "manual_override"
            else ("System approved." if review_status == "approved" else "")
        )
        updated_df.at[index, "pipeline_readiness"] = (
            "approved_and_applied"
            if applied_flag
            else f"processed_{review_status}"
        )
        updated_df.at[index, "portfolio_state_impact"] = (
            "approved_overlay_applied" if applied_flag else "no_overlay_update"
        )

    updated_df.to_csv(INGESTION_MANIFEST_PATH, index=False)
    return updated_df
