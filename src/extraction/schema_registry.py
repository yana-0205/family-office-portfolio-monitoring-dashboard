from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from src.config import REPO_ROOT


SCHEMA_REGISTRY = {
    "capital_call": REPO_ROOT / "schemas" / "capital_call_schema.json",
    "distribution": REPO_ROOT / "schemas" / "distribution_schema.json",
    "capital_statement": REPO_ROOT / "schemas" / "capital_statement_schema.json",
    "newsletter": REPO_ROOT / "schemas" / "newsletter_schema.json",
}


def list_available_schemas() -> list[str]:
    return sorted(SCHEMA_REGISTRY)


def get_schema_path(document_type: str) -> Path:
    try:
        return SCHEMA_REGISTRY[document_type]
    except KeyError as exc:
        available = ", ".join(list_available_schemas())
        raise KeyError(f"Unknown document_type '{document_type}'. Available: {available}") from exc


def load_schema(document_type: str) -> dict:
    schema_path = get_schema_path(document_type)
    if not schema_path.exists():
        raise FileNotFoundError(f"Schema file not found: {schema_path}")
    with schema_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def validate_schema_file(document_type: str) -> dict[str, str | bool]:
    schema = load_schema(document_type)
    Draft202012Validator.check_schema(schema)
    return {
        "document_type": document_type,
        "path": str(get_schema_path(document_type)),
        "valid": True,
    }


def validate_all_schema_files() -> dict[str, object]:
    results = [validate_schema_file(document_type) for document_type in list_available_schemas()]
    return {
        "valid": all(item["valid"] for item in results),
        "results": results,
    }
