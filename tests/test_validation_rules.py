from src.validation.rules import (
    check_commitment_consistency,
    check_distribution_component_sum,
    check_low_confidence_review,
    check_nav_roll_forward,
    check_required_field_completeness,
)


def test_required_field_completeness_passes_for_valid_capital_call() -> None:
    record = {
        "document_type": "capital_call",
        "fund_name_raw": "Example Fund",
        "fund_name_mapped": "Example Fund",
        "currency": "USD",
        "extracted_fields": {"due_date": "2026-05-24", "amount_due": 2.5},
    }
    result = check_required_field_completeness(record)
    assert result["status"] == "passed"


def test_required_field_completeness_fails_for_missing_amount_due() -> None:
    record = {
        "document_type": "capital_call",
        "fund_name_raw": "Example Fund",
        "currency": "USD",
        "extracted_fields": {"due_date": "2026-05-24", "amount_due": None},
    }
    result = check_required_field_completeness(record)
    assert result["status"] == "failed"


def test_commitment_consistency_passes_when_values_reconcile() -> None:
    record = {
        "document_type": "capital_statement",
        "extracted_fields": {"total_commitment": 60.0, "paid_in_capital": 40.0, "unfunded_commitment": 20.0},
    }
    result = check_commitment_consistency(record)
    assert result["status"] == "passed"


def test_commitment_consistency_fails_on_material_mismatch() -> None:
    record = {
        "document_type": "capital_statement",
        "extracted_fields": {"total_commitment": 60.0, "paid_in_capital": 40.0, "unfunded_commitment": 15.0},
    }
    result = check_commitment_consistency(record)
    assert result["status"] == "failed"


def test_nav_roll_forward_passes_on_valid_example() -> None:
    record = {
        "document_type": "capital_statement",
        "extracted_fields": {
            "beginning_nav": 10.0,
            "contributions": 2.0,
            "distributions": 1.0,
            "management_fees": 0.5,
            "partnership_expenses": 0.2,
            "realized_gain_loss": 1.0,
            "unrealized_gain_loss": 0.7,
            "ending_nav": 12.0,
        },
    }
    result = check_nav_roll_forward(record)
    assert result["status"] == "passed"


def test_distribution_component_sum_passes_on_valid_example() -> None:
    record = {
        "document_type": "distribution",
        "extracted_fields": {
            "return_of_capital": 2.0,
            "realized_gain": 1.0,
            "income": 0.5,
            "recallable_distribution": 0.0,
            "withholding": 0.5,
            "net_distribution": 3.0,
        },
    }
    result = check_distribution_component_sum(record)
    assert result["status"] == "passed"


def test_low_confidence_rule_warns_below_threshold() -> None:
    record = {"confidence_score": 0.7}
    result = check_low_confidence_review(record, threshold=0.85)
    assert result["status"] == "warning"
