from src.extraction.baseline_extractor import extract_document
from src.extraction.document_classifier import classify_document
from src.extraction.pdf_reader import read_all_pdfs


def test_extract_document_returns_required_common_fields() -> None:
    pdf_record = read_all_pdfs()[0]
    classification = classify_document(pdf_record["text"], filename=pdf_record["filename"])
    record = extract_document(pdf_record, classification)
    for field in [
        "document_id",
        "document_type",
        "document_filename",
        "extraction_mode",
        "source_path",
        "extracted_fields",
        "warnings",
    ]:
        assert field in record


def test_extracted_json_contains_extracted_fields() -> None:
    pdf_record = read_all_pdfs()[2]
    classification = classify_document(pdf_record["text"], filename=pdf_record["filename"])
    record = extract_document(pdf_record, classification)
    assert isinstance(record["extracted_fields"], dict)


def test_baseline_confidence_is_rule_based_and_explained() -> None:
    pdf_record = read_all_pdfs()[0]
    classification = classify_document(pdf_record["text"], filename=pdf_record["filename"])
    record = extract_document(pdf_record, classification)

    assert 0.0 <= record["confidence_score"] <= 1.0
    assert record["confidence_details"]["method"] == "rule_based_v1"
    assert set(record["confidence_details"]["components"]) == {
        "required_field_completeness",
        "label_match_quality",
        "fund_name_match_quality",
        "reconciliation_quality",
        "date_format_quality",
        "source_reference_quality",
    }
