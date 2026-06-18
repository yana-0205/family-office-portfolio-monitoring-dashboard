import json

from src.extraction.schema_registry import (
    get_schema_path,
    list_available_schemas,
    load_schema,
    validate_all_schema_files,
)


EXPECTED_SCHEMA_TYPES = [
    "capital_call",
    "distribution",
    "capital_statement",
    "newsletter",
]

COMMON_REQUIRED_FIELDS = {
    "document_id",
    "document_type",
    "document_filename",
    "extraction_mode",
    "source_path",
    "fund_name_raw",
    "fund_name_mapped",
    "investor_entity",
    "notice_date",
    "reporting_period",
    "currency",
    "extracted_fields",
    "source_references",
    "confidence_score",
    "extraction_status",
    "validation_status",
    "review_status",
    "warnings",
}


def test_all_schema_files_exist() -> None:
    for document_type in EXPECTED_SCHEMA_TYPES:
        assert get_schema_path(document_type).exists()


def test_all_schema_files_are_valid_json() -> None:
    for document_type in EXPECTED_SCHEMA_TYPES:
        with get_schema_path(document_type).open("r", encoding="utf-8") as handle:
            loaded = json.load(handle)
        assert isinstance(loaded, dict)


def test_schema_registry_lists_all_schemas() -> None:
    assert list_available_schemas() == sorted(EXPECTED_SCHEMA_TYPES)


def test_schema_registry_can_load_each_schema() -> None:
    for document_type in EXPECTED_SCHEMA_TYPES:
        schema = load_schema(document_type)
        assert schema["type"] == "object"


def test_each_schema_contains_common_required_top_level_fields() -> None:
    for document_type in EXPECTED_SCHEMA_TYPES:
        schema = load_schema(document_type)
        assert COMMON_REQUIRED_FIELDS.issubset(set(schema["required"]))


def test_each_schema_has_expected_document_type_constraint() -> None:
    for document_type in EXPECTED_SCHEMA_TYPES:
        schema = load_schema(document_type)
        document_type_property = schema["properties"]["document_type"]
        if "const" in document_type_property:
            assert document_type_property["const"] == document_type
        else:
            assert document_type in document_type_property["enum"]


def test_validate_all_schema_files_returns_success() -> None:
    results = validate_all_schema_files()
    assert results["valid"] is True
    assert len(results["results"]) == 4
