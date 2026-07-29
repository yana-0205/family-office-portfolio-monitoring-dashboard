import json

import pytest

from src.extraction.llm_extractor import extract_document


class _FakeResponse:
    def __init__(self, payload: dict):
        self.output_text = json.dumps(payload)


class _FakeResponses:
    def __init__(self, payload: dict):
        self.payload = payload
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return _FakeResponse(self.payload)


class _FakeClient:
    def __init__(self, payload: dict):
        self.responses = _FakeResponses(payload)


def _capital_call_payload() -> dict:
    return {
        "document_id": "MODEL_VALUE",
        "document_type": "capital_call",
        "document_filename": "MODEL_VALUE.pdf",
        "extraction_mode": "llm",
        "source_path": "/model/value.pdf",
        "fund_name_raw": "Example Fund IV",
        "fund_name_mapped": "Example Fund IV",
        "investor_entity": "Example Family Office",
        "notice_date": "2026-05-01",
        "reporting_period": "2026-05",
        "currency": "USD",
        "extracted_fields": {
            "due_date": "2026-05-08",
            "amount_due": 2.5,
            "total_commitment": 40.0,
            "paid_in_capital": 20.0,
            "unfunded_commitment": 17.5,
            "management_fee": 0.1,
            "partnership_expense": 0.0,
            "investment_call": 2.4,
            "urgent_due_date_flag": True,
            "missing_required_field_flag": False,
            "bank_instruction_changed_flag": False,
            "transaction_components": [],
        },
        "source_references": [
            {"page": 1, "field_name": "amount_due", "evidence_text": "USD 2.5 million"}
        ],
        "confidence_score": 0.9,
        "extraction_status": "extracted",
        "validation_status": "pending",
        "review_status": "pending",
        "warnings": [],
    }


def test_llm_extractor_uses_strict_schema_and_pipeline_source_identity() -> None:
    client = _FakeClient(_capital_call_payload())
    pdf_record = {
        "document_id": "PDF_999",
        "filename": "PDF_999_capital_call.pdf",
        "path": "/trusted/PDF_999_capital_call.pdf",
        "text": "Capital Call",
        "pages": [{"page": 1, "text": "Total Amount Due USD 2.5 million"}],
    }

    result = extract_document(
        pdf_record,
        {"document_type": "capital_call"},
        client=client,
        model="test-model",
    )

    assert result["document_id"] == "PDF_999"
    assert result["source_path"] == "/trusted/PDF_999_capital_call.pdf"
    assert result["extraction_mode"] == "llm"
    call = client.responses.calls[0]
    assert call["model"] == "test-model"
    assert call["text"]["format"]["type"] == "json_schema"
    assert call["text"]["format"]["strict"] is True


def test_llm_extractor_requires_credentials_when_no_client(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        extract_document(
            {
                "document_id": "PDF_999",
                "filename": "PDF_999.pdf",
                "path": "/trusted/PDF_999.pdf",
                "text": "Capital Call",
                "pages": [],
            },
            {"document_type": "capital_call"},
        )
