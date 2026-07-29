from pathlib import Path

from src.ingestion import inbox


def test_stage_uploaded_pdf_writes_manifest_and_file(tmp_path, monkeypatch) -> None:
    manifest_path = tmp_path / "ingestion_inbox.csv"
    files_dir = tmp_path / "uploaded_pdfs"
    monkeypatch.setattr(inbox, "INGESTION_MANIFEST_PATH", manifest_path)
    monkeypatch.setattr(inbox, "INGESTION_FILES_DIR", files_dir)

    result = inbox.stage_uploaded_pdf("PDF_999_Test_Document.pdf", b"%PDF-1.4 test bytes")

    assert result["action"] == "staged"
    assert manifest_path.exists()
    assert files_dir.exists()
    assert Path(result["stored_path"]).exists()
    loaded_df = inbox.load_ingestion_inbox()
    assert len(loaded_df) == 1
    assert loaded_df.iloc[0]["document_id"] == "PDF_999"
    assert loaded_df.iloc[0]["portfolio_state_impact"] == "none_until_reviewed"
    assert loaded_df.iloc[0]["review_status"] == "pending"


def test_stage_uploaded_pdf_skips_duplicate_content(tmp_path, monkeypatch) -> None:
    manifest_path = tmp_path / "ingestion_inbox.csv"
    files_dir = tmp_path / "uploaded_pdfs"
    monkeypatch.setattr(inbox, "INGESTION_MANIFEST_PATH", manifest_path)
    monkeypatch.setattr(inbox, "INGESTION_FILES_DIR", files_dir)

    first = inbox.stage_uploaded_pdf("PDF_001_First.pdf", b"%PDF duplicate bytes")
    second = inbox.stage_uploaded_pdf("PDF_001_First_Copy.pdf", b"%PDF duplicate bytes")

    assert first["action"] == "staged"
    assert second["action"] == "duplicate"
    assert len(inbox.load_ingestion_inbox()) == 1


def test_stage_uploaded_pdf_requires_pdf_extension(tmp_path, monkeypatch) -> None:
    manifest_path = tmp_path / "ingestion_inbox.csv"
    files_dir = tmp_path / "uploaded_pdfs"
    monkeypatch.setattr(inbox, "INGESTION_MANIFEST_PATH", manifest_path)
    monkeypatch.setattr(inbox, "INGESTION_FILES_DIR", files_dir)

    try:
        inbox.stage_uploaded_pdf("not_a_pdf.txt", b"plain text")
    except ValueError as exc:
        assert "must be a PDF" in str(exc)
    else:
        raise AssertionError("Expected ValueError for non-PDF upload.")


def test_sync_ingestion_status_updates_manifest_fields(tmp_path, monkeypatch) -> None:
    manifest_path = tmp_path / "ingestion_inbox.csv"
    files_dir = tmp_path / "uploaded_pdfs"
    monkeypatch.setattr(inbox, "INGESTION_MANIFEST_PATH", manifest_path)
    monkeypatch.setattr(inbox, "INGESTION_FILES_DIR", files_dir)

    inbox.stage_uploaded_pdf("PDF_003_Test.pdf", b"%PDF-1.4 test bytes")
    document_status_df = __import__("pandas").DataFrame(
        {
            "document_id": ["PDF_003"],
            "validation_review_status": ["approved"],
            "update_applied_flag": [True],
            "review_status_source": ["manual_override"],
            "reviewer_note": ["Checked against the source PDF."],
        }
    )

    updated_df = inbox.sync_ingestion_status(document_status_df)

    assert updated_df.iloc[0]["ingestion_status"] == "processed"
    assert updated_df.iloc[0]["pipeline_readiness"] == "approved_and_applied"
    assert updated_df.iloc[0]["portfolio_state_impact"] == "approved_overlay_applied"
    assert updated_df.iloc[0]["review_status"] == "approved"
    assert updated_df.iloc[0]["approval_source"] == "manual"
    assert updated_df.iloc[0]["review_note"] == "Manually approved. Checked against the source PDF."
