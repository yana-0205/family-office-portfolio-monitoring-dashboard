from src.extraction.extraction_accuracy import compare_extraction_to_ground_truth, flatten_extraction_record


def test_flatten_extraction_record_returns_flat_dictionary() -> None:
    record = {
        "document_id": "PDF_999",
        "document_type": "capital_call",
        "fund_name_raw": "Example Fund",
        "fund_name_mapped": "Example Fund",
        "notice_date": "2026-05-01",
        "reporting_period": "May 2026 event",
        "extracted_fields": {"amount_due": 1.25, "unfunded_commitment": 8.75},
    }
    flat = flatten_extraction_record(record)
    assert flat["document_id"] == "PDF_999"
    assert flat["amount_due"] == 1.25
    assert flat["unfunded_commitment_after"] == 8.75


def test_accuracy_comparison_handles_missing_ground_truth_gracefully(monkeypatch) -> None:
    from src.extraction import extraction_accuracy as module

    monkeypatch.setattr(module, "load_ground_truth", lambda: None)
    df = compare_extraction_to_ground_truth([], mode="baseline")
    assert not df.empty
    assert "Ground truth unavailable." in df.iloc[0]["warning"]
