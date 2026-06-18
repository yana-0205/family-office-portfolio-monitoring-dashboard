import importlib

from src.validation.engine import determine_review_status, validate_all_records


def test_determine_review_status_returns_approved() -> None:
    assert determine_review_status([{"status": "passed", "severity": "info", "rule_id": "VR001"}]) == "approved"


def test_determine_review_status_returns_needs_review() -> None:
    results = [{"status": "warning", "severity": "medium", "rule_id": "VR009"}]
    assert determine_review_status(results) == "needs_review"


def test_determine_review_status_returns_rejected() -> None:
    results = [{"status": "failed", "severity": "critical", "rule_id": "VR006"}]
    assert determine_review_status(results) == "rejected"


def test_validate_all_records_can_process_baseline_jsons() -> None:
    records_with_results = validate_all_records(mode="baseline")
    assert records_with_results
    assert len(records_with_results) == 6


def test_run_validation_can_be_imported_without_side_effects() -> None:
    module = importlib.import_module("src.validation.run_validation")
    assert hasattr(module, "run")
    assert hasattr(module, "main")
