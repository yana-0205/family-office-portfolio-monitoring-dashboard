from __future__ import annotations

import argparse
import json
from pathlib import Path

from jsonschema import Draft202012Validator

from src.config import OUTPUTS_DIR, REPORTS_DIR
from src.extraction.baseline_extractor import extract_document
from src.extraction.document_classifier import classify_all_documents
from src.extraction.extraction_accuracy import compare_extraction_to_ground_truth, write_accuracy_outputs
from src.extraction.pdf_reader import read_all_pdfs
from src.extraction.schema_registry import load_schema


def _validate_record_against_schema(record: dict) -> list[str]:
    schema = load_schema(record["document_type"])
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(record), key=lambda err: err.path)
    return [error.message for error in errors]


def _write_extracted_json(records: list[dict], mode: str) -> list[Path]:
    output_dir = OUTPUTS_DIR / "extracted_json" / mode
    output_dir.mkdir(parents=True, exist_ok=True)
    written_paths = []
    for record in records:
        path = output_dir / f"{record['document_id']}.json"
        path.write_text(json.dumps(record, indent=2), encoding="utf-8")
        written_paths.append(path)
    return written_paths


def _write_run_summary(
    records: list[dict],
    classifications: list[dict],
    written_paths: list[Path],
    accuracy_paths: dict[str, Path],
    mode: str,
) -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    summary_path = REPORTS_DIR / f"{mode}_extraction_run_summary.md"
    summary_lines = [
        f"# {mode.title()} Extraction Run Summary",
        "",
        f"- Extraction mode: `{mode}`",
        f"- PDFs processed: `{len(records)}`",
        f"- JSON outputs written: `{len(written_paths)}`",
        f"- Accuracy report: `{accuracy_paths['report_path'].name}`",
        f"- Accuracy CSV: `{accuracy_paths['csv_path'].name}`",
        "",
        "## Documents",
        "",
    ]

    for pdf_record, extraction_record in zip(classifications, records):
        warnings = extraction_record.get("warnings", [])
        summary_lines.extend(
            [
                f"- `{extraction_record['document_id']}` -> `{extraction_record['document_type']}` | status=`{extraction_record['extraction_status']}` | confidence=`{extraction_record['confidence_score']}`",
                f"  schema warnings: {warnings if warnings else 'none'}",
                f"  classification reasons: {pdf_record['classification']['classification_reasons']}",
            ]
        )

    summary_path.write_text("\n".join(summary_lines), encoding="utf-8")
    return summary_path


def run(mode: str = "baseline") -> dict:
    if mode != "baseline":
        raise NotImplementedError(f"Extraction mode '{mode}' is not implemented in this phase.")

    pdf_records = read_all_pdfs()
    classified = classify_all_documents(pdf_records)

    extracted_records = []
    for item in classified:
        record = extract_document(item, item["classification"])
        schema_errors = _validate_record_against_schema(record)
        if schema_errors:
            record["warnings"].extend([f"Schema validation: {message}" for message in schema_errors])
        extracted_records.append(record)

    written_paths = _write_extracted_json(extracted_records, mode=mode)
    comparison_df = compare_extraction_to_ground_truth(extracted_records, mode=mode)
    accuracy_paths = write_accuracy_outputs(comparison_df, mode=mode)
    summary_path = _write_run_summary(extracted_records, classified, written_paths, accuracy_paths, mode=mode)

    return {
        "mode": mode,
        "pdf_count": len(pdf_records),
        "written_paths": written_paths,
        "summary_path": summary_path,
        "accuracy_report_path": accuracy_paths["report_path"],
        "accuracy_csv_path": accuracy_paths["csv_path"],
        "comparison_rows": len(comparison_df),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run document extraction pipeline.")
    parser.add_argument("--mode", default="baseline", choices=["baseline", "llm"])
    args = parser.parse_args()
    results = run(mode=args.mode)
    print(
        f"mode={results['mode']} pdfs={results['pdf_count']} json={len(results['written_paths'])} "
        f"summary={results['summary_path'].name} accuracy_rows={results['comparison_rows']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
