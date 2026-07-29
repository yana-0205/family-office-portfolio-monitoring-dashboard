from __future__ import annotations

import json
import os
from copy import deepcopy
from typing import Any, Protocol

from dotenv import load_dotenv

from src.extraction.schema_registry import load_schema


DEFAULT_LLM_MODEL = "gpt-5.6-sol"

# Load project-local credentials without overriding explicitly exported values.
load_dotenv()


class ResponsesClient(Protocol):
    class _Responses(Protocol):
        def create(self, **kwargs: Any) -> Any: ...

    responses: _Responses


def _structured_output_schema(document_type: str) -> dict[str, Any]:
    """Return the repository schema without documentation-only JSON Schema keys."""
    schema = deepcopy(load_schema(document_type))

    def clean(value: Any) -> Any:
        if isinstance(value, dict):
            return {
                key: clean(item)
                for key, item in value.items()
                if key not in {"$schema", "$id", "examples", "title", "format"}
            }
        if isinstance(value, list):
            return [clean(item) for item in value]
        return value

    return clean(schema)


def _build_prompt(pdf_record: dict[str, Any], classification: dict[str, Any]) -> str:
    pages = "\n\n".join(
        f"--- PAGE {page.get('page')} ---\n{page.get('text', '')}"
        for page in pdf_record.get("pages", [])
    )
    return (
        "Extract the private-market document into the supplied JSON schema.\n"
        "Use only facts supported by the document text. Never infer a missing monetary value.\n"
        "All monetary amounts must use the document's displayed unit (this demo uses USD millions).\n"
        "For source_references, quote concise evidence text and the correct page number.\n"
        "Set validation_status and review_status to 'pending'.\n"
        "Set extraction_mode to 'llm'.\n"
        f"Expected document type: {classification['document_type']}\n"
        f"Document ID: {pdf_record['document_id']}\n"
        f"Filename: {pdf_record['filename']}\n\n"
        f"{pages or pdf_record.get('text', '')}"
    )


def _create_client(api_key: str | None = None) -> ResponsesClient:
    resolved_key = api_key or os.getenv("OPENAI_API_KEY")
    if not resolved_key:
        raise RuntimeError(
            "LLM extraction requires OPENAI_API_KEY. Baseline extraction remains available with --mode baseline."
        )
    try:
        from openai import OpenAI
    except ImportError as exc:  # pragma: no cover - depends on installation state
        raise RuntimeError(
            "LLM extraction requires the 'openai' package. Install requirements.txt first."
        ) from exc

    return OpenAI(api_key=resolved_key)


def _response_output_text(response: Any) -> str:
    output_text = getattr(response, "output_text", None)
    if isinstance(output_text, str) and output_text.strip():
        return output_text
    if isinstance(response, dict) and isinstance(response.get("output_text"), str):
        return response["output_text"]
    raise RuntimeError("The LLM response did not contain structured output text.")


def extract_document(
    pdf_record: dict[str, Any],
    classification: dict[str, Any],
    *,
    client: ResponsesClient | None = None,
    model: str | None = None,
    api_key: str | None = None,
) -> dict[str, Any]:
    document_type = classification["document_type"]
    schema = _structured_output_schema(document_type)
    resolved_client = client or _create_client(api_key=api_key)
    resolved_model = model or os.getenv("OPENAI_EXTRACTION_MODEL", DEFAULT_LLM_MODEL)

    response = resolved_client.responses.create(
        model=resolved_model,
        input=[
            {
                "role": "system",
                "content": (
                    "You extract auditable private-market document data. "
                    "Return only schema-conforming facts grounded in the supplied document."
                ),
            },
            {"role": "user", "content": _build_prompt(pdf_record, classification)},
        ],
        text={
            "format": {
                "type": "json_schema",
                "name": f"{document_type}_extraction",
                "strict": True,
                "schema": schema,
            }
        },
    )

    try:
        record = json.loads(_response_output_text(response))
    except json.JSONDecodeError as exc:
        raise RuntimeError("The LLM response was not valid JSON.") from exc

    # Source identity is controlled by the pipeline rather than trusted to the model.
    record["document_id"] = pdf_record["document_id"]
    record["document_type"] = document_type
    record["document_filename"] = pdf_record["filename"]
    record["source_path"] = pdf_record["path"]
    record["extraction_mode"] = "llm"
    record["validation_status"] = "pending"
    record["review_status"] = "pending"
    return record
