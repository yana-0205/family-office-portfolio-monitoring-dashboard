from __future__ import annotations

import argparse
from typing import Any

from src.extraction.run_extraction import run as run_extraction
from src.portfolio_updates.apply_updates import run as run_apply_updates
from src.validation.run_validation import run as run_validation


def run() -> dict[str, Any]:
    extraction_results = run_extraction(mode="intake")
    validation_results = run_validation(mode="intake")
    update_results = run_apply_updates(mode="intake")
    return {
        "extraction": extraction_results,
        "validation": validation_results,
        "updates": update_results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the staged-upload intake pipeline end to end.")
    _ = parser.parse_args()
    results = run()
    print(
        f"intake_pdfs={results['extraction']['pdf_count']} "
        f"validated={results['validation']['records_validated']} "
        f"approved_applied={results['updates']['approved_applied']} "
        f"blocked={results['updates']['blocked_count']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
