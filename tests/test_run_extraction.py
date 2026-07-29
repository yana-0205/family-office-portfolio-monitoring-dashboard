import importlib
import json
from pathlib import Path

from src.extraction.run_extraction import run


def test_run_extraction_can_be_imported_without_side_effects() -> None:
    module = importlib.import_module("src.extraction.run_extraction")
    assert hasattr(module, "run")
    assert hasattr(module, "main")


def test_run_extraction_supports_custom_source_dir(tmp_path: Path) -> None:
    sample_pdf = next(Path("data/raw/family_office_corrected_dataset_v1/documents").glob("*.pdf"))
    copied_pdf = tmp_path / sample_pdf.name
    copied_pdf.write_bytes(sample_pdf.read_bytes())

    results = run(mode="intake", source_dir=tmp_path)

    assert results["pdf_count"] == 1
    assert results["mode"] == "intake"


def test_run_extraction_supports_llm_mode_with_injected_client(tmp_path: Path, monkeypatch) -> None:
    sample_pdf = next(Path("data/raw/family_office_corrected_dataset_v1/documents").glob("*.pdf"))
    copied_pdf = tmp_path / sample_pdf.name
    copied_pdf.write_bytes(sample_pdf.read_bytes())

    baseline_record = {
        "document_id": "PDF_001",
        "document_type": "capital_call",
        "document_filename": copied_pdf.name,
        "extraction_mode": "llm",
        "source_path": str(copied_pdf),
        "fund_name_raw": "Northstar Buyout Fund IV",
        "fund_name_mapped": "Northstar Buyout Fund IV",
        "investor_entity": "Example Family Office",
        "notice_date": "2026-05-01",
        "reporting_period": "2026-05",
        "currency": "USD",
        "extracted_fields": {
            "due_date": "2026-05-08", "amount_due": 2.5, "total_commitment": 40.0,
            "paid_in_capital": 20.0, "unfunded_commitment": 17.5, "management_fee": 0.1,
            "partnership_expense": 0.0, "investment_call": 2.4,
            "urgent_due_date_flag": True, "missing_required_field_flag": False,
            "bank_instruction_changed_flag": False, "transaction_components": [],
        },
        "source_references": [], "confidence_score": 0.9, "extraction_status": "extracted",
        "validation_status": "pending", "review_status": "pending", "warnings": [],
    }

    class FakeResponse:
        output_text = json.dumps(baseline_record)

    class FakeResponses:
        def create(self, **kwargs):
            return FakeResponse()

    class FakeClient:
        responses = FakeResponses()

    monkeypatch.setattr(
        "src.extraction.run_extraction.compare_extraction_to_ground_truth",
        lambda records, mode: __import__("pandas").DataFrame(
            [{"mode": mode, "document_id": "PDF_001", "field_name": "amount_due", "expected_value": 2.5, "actual_value": 2.5, "matched": True, "warning": ""}]
        ),
    )
    results = run(mode="llm", source_dir=tmp_path, llm_client=FakeClient(), llm_model="test-model")

    assert results["pdf_count"] == 1
    assert results["mode"] == "llm"
