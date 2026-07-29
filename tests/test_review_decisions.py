from pathlib import Path

import pandas as pd

from src.validation import review_decisions


def test_upsert_review_decision_writes_and_clears_override(tmp_path: Path, monkeypatch) -> None:
    review_decisions_path = tmp_path / "manual_review_decisions.csv"
    monkeypatch.setattr(review_decisions, "REVIEW_DECISIONS_PATH", review_decisions_path)

    review_decisions.upsert_review_decision(
        document_id="PDF_001",
        extraction_mode="intake",
        manual_review_status="approved",
        reviewer_note="Reviewed manually.",
    )
    written_df = pd.read_csv(review_decisions_path)
    assert written_df.iloc[0]["manual_review_status"] == "approved"

    review_decisions.upsert_review_decision(
        document_id="PDF_001",
        extraction_mode="intake",
        manual_review_status=None,
        reviewer_note="",
    )
    cleared_df = pd.read_csv(review_decisions_path)
    assert cleared_df.empty


def test_apply_review_decisions_to_validation_results_overrides_review_status(tmp_path: Path, monkeypatch) -> None:
    review_decisions_path = tmp_path / "manual_review_decisions.csv"
    monkeypatch.setattr(review_decisions, "REVIEW_DECISIONS_PATH", review_decisions_path)
    pd.DataFrame(
        [
            {
                "document_id": "PDF_002",
                "extraction_mode": "intake",
                "manual_review_status": "approved",
                "reviewer_note": "Looks good.",
                "reviewed_at_utc": "2026-07-15T00:00:00Z",
            }
        ]
    ).to_csv(review_decisions_path, index=False)

    validation_results_df = pd.DataFrame(
        [
            {"document_id": "PDF_002", "extraction_mode": "intake", "review_status": "rejected"},
            {"document_id": "PDF_003", "extraction_mode": "intake", "review_status": "needs_review"},
        ]
    )

    effective_df = review_decisions.apply_review_decisions_to_validation_results(validation_results_df)

    overridden_row = effective_df.loc[effective_df["document_id"] == "PDF_002"].iloc[0]
    untouched_row = effective_df.loc[effective_df["document_id"] == "PDF_003"].iloc[0]
    assert overridden_row["system_review_status"] == "rejected"
    assert overridden_row["review_status"] == "approved"
    assert overridden_row["review_status_source"] == "manual_override"
    assert untouched_row["review_status"] == "needs_review"


def test_build_effective_review_queue_can_keep_manually_approved_rows_visible(tmp_path: Path, monkeypatch) -> None:
    review_decisions_path = tmp_path / "manual_review_decisions.csv"
    monkeypatch.setattr(review_decisions, "REVIEW_DECISIONS_PATH", review_decisions_path)
    pd.DataFrame(
        [
            {
                "document_id": "PDF_004",
                "extraction_mode": "intake",
                "manual_review_status": "approved",
                "reviewer_note": "Approved after review.",
                "reviewed_at_utc": "2026-07-15T00:00:00Z",
            }
        ]
    ).to_csv(review_decisions_path, index=False)

    review_queue_df = pd.DataFrame(
        [
            {
                "document_id": "PDF_004",
                "document_type": "capital_statement",
                "fund_name": "Example Fund",
                "extraction_mode": "intake",
                "review_status": "rejected",
            }
        ]
    )
    validation_results_df = pd.DataFrame(
        [{"document_id": "PDF_004", "extraction_mode": "intake", "review_status": "approved"}]
    )

    all_rows_df = review_decisions.build_effective_review_queue(
        review_queue_df,
        validation_results_df,
        unresolved_only=False,
    )
    unresolved_df = review_decisions.build_effective_review_queue(
        review_queue_df,
        validation_results_df,
        unresolved_only=True,
    )

    assert all_rows_df.iloc[0]["review_status"] == "approved"
    assert unresolved_df.empty
