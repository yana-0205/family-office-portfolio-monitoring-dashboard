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
