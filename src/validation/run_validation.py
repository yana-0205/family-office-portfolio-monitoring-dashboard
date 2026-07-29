from __future__ import annotations

import argparse

from src.config import OUTPUTS_DIR, REPORTS_DIR
from src.validation.engine import (
    build_review_queue_df,
    build_validation_results_df,
    validate_all_records,
)


def _write_summary(results_df, review_queue_df) -> str:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    summary_path = REPORTS_DIR / "validation_summary.md"

    approved_count = int((results_df["review_status"] == "approved").groupby(results_df["document_id"]).first().sum())
    needs_review_count = int((results_df["review_status"] == "needs_review").groupby(results_df["document_id"]).first().sum())
    rejected_count = int((results_df["review_status"] == "rejected").groupby(results_df["document_id"]).first().sum())

    summary_lines = [
        "# Validation Summary",
        "",
        f"- Records validated: `{results_df['document_id'].nunique()}`",
        f"- Approved: `{approved_count}`",
        f"- Needs review: `{needs_review_count}`",
        f"- Rejected: `{rejected_count}`",
        "",
        "## Review Queue",
        "",
    ]

    if review_queue_df.empty:
        summary_lines.append("- No records required manual review.")
    else:
        summary_lines.extend(
            [
                f"- `{row.document_id}` | `{row.review_status}` | `{row.highest_severity}` | {row.issue_summary}"
                for row in review_queue_df.itertuples()
            ]
        )

    summary_path.write_text("\n".join(summary_lines), encoding="utf-8")
    return str(summary_path)


def run(mode: str = "baseline") -> dict[str, str | int]:
    records_with_results = validate_all_records(mode=mode)
    results_df = build_validation_results_df(records_with_results)
    review_queue_df = build_review_queue_df(records_with_results)

    validation_dir = OUTPUTS_DIR / "validation"
    validation_dir.mkdir(parents=True, exist_ok=True)
    validation_results_path = validation_dir / "validation_results_actual.csv"
    review_queue_path = validation_dir / "review_queue_actual.csv"

    results_df.to_csv(validation_results_path, index=False)
    review_queue_df.to_csv(review_queue_path, index=False)
    summary_path = _write_summary(results_df, review_queue_df)

    review_status_by_document = results_df.groupby("document_id")["review_status"].first()
    approved_count = int((review_status_by_document == "approved").sum())
    needs_review_count = int((review_status_by_document == "needs_review").sum())
    rejected_count = int((review_status_by_document == "rejected").sum())

    return {
        "records_validated": int(results_df["document_id"].nunique()),
        "approved_count": approved_count,
        "needs_review_count": needs_review_count,
        "rejected_count": rejected_count,
        "validation_results_path": str(validation_results_path),
        "review_queue_path": str(review_queue_path),
        "summary_path": summary_path,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run validation engine for extracted records.")
    parser.add_argument("--mode", default="baseline", choices=["baseline", "intake", "llm"])
    args = parser.parse_args()
    results = run(mode=args.mode)
    print(
        f"records={results['records_validated']} approved={results['approved_count']} "
        f"needs_review={results['needs_review_count']} rejected={results['rejected_count']} "
        f"validation_results={results['validation_results_path']} review_queue={results['review_queue_path']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
