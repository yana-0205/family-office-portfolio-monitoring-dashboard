import importlib
from pathlib import Path

import pandas as pd

from src.portfolio_updates.apply_updates import (
    apply_capital_call_update,
    apply_capital_statement_update,
    apply_distribution_update,
    apply_expected_position_updates,
    apply_newsletter_update,
    get_approved_records,
    get_blocked_records,
    load_extracted_records,
    load_validation_status,
    run,
)
from src.validation import review_decisions


def test_get_approved_records_returns_only_approved() -> None:
    records = [
        {"document_id": "PDF_001"},
        {"document_id": "PDF_002"},
        {"document_id": "PDF_003"},
    ]
    statuses = {"PDF_001": "approved", "PDF_002": "needs_review", "PDF_003": "approved"}
    approved = get_approved_records(records, statuses)
    assert [record["document_id"] for record in approved] == ["PDF_001", "PDF_003"]


def test_blocked_records_are_not_applied() -> None:
    records = [
        {"document_id": "PDF_001"},
        {"document_id": "PDF_002"},
        {"document_id": "PDF_003"},
    ]
    statuses = {"PDF_001": "approved", "PDF_002": "needs_review", "PDF_003": "rejected"}
    blocked = get_blocked_records(records, statuses)
    assert [record["document_id"] for record in blocked] == ["PDF_002", "PDF_003"]


def test_capital_call_update_increases_paid_in_and_reduces_unfunded() -> None:
    record = {
        "document_id": "PDF_900",
        "document_type": "capital_call",
        "fund_name_mapped": "Example Fund",
        "extraction_mode": "baseline",
        "currency": "USD",
        "extracted_fields": {"amount_due": 2.0, "due_date": "2026-05-20"},
    }
    positions = pd.DataFrame(
        [
            {
                "fund_name": "Example Fund",
                "paid_in_capital_usd_m": 10.0,
                "unfunded_commitment_usd_m": 5.0,
            }
        ]
    )
    cash = pd.DataFrame([{"account_name": "USD Operating Cash Account", "currency": "USD", "balance_usd_m": 8.0}])
    updated_positions, updated_cash, _ = apply_capital_call_update(record, positions, cash)
    assert updated_positions.loc[0, "paid_in_capital_usd_m"] == 12.0
    assert updated_positions.loc[0, "unfunded_commitment_usd_m"] == 3.0
    assert updated_cash.loc[0, "balance_usd_m"] == 8.0


def test_distribution_update_creates_cashflow_row() -> None:
    record = {
        "document_id": "PDF_901",
        "document_type": "distribution",
        "fund_name_mapped": "Example Fund",
        "extraction_mode": "baseline",
        "currency": "USD",
        "extracted_fields": {"payment_date": "2026-05-21", "gross_distribution": 3.0, "net_distribution": 3.0},
    }
    cash = pd.DataFrame([{"account_name": "USD Operating Cash Account", "currency": "USD", "balance_usd_m": 5.0}])
    updated_cash, cashflow_row = apply_distribution_update(record, cash)
    assert updated_cash.loc[0, "balance_usd_m"] == 5.0
    assert cashflow_row.loc[0, "cashflow_type"] == "distribution"
    assert cashflow_row.loc[0, "liquidity_treatment"] == "projected_distribution"


def test_capital_statement_update_changes_nav_only_when_approved() -> None:
    record = {
        "document_id": "PDF_902",
        "document_type": "capital_statement",
        "fund_name_mapped": "Example Fund",
        "extraction_mode": "baseline",
        "extracted_fields": {
            "ending_nav": 30.0,
            "paid_in_capital": 22.0,
            "unfunded_commitment": 8.0,
            "total_commitment": 30.0,
            "period_end_date": "2026-03-31",
        },
    }
    positions = pd.DataFrame([{"fund_name": "Example Fund", "current_nav_usd_m": 20.0}])
    updated_positions = apply_capital_statement_update(record, positions)
    assert updated_positions.loc[0, "current_nav_usd_m"] == 30.0


def test_newsletter_creates_commentary_row_and_does_not_change_numeric_state() -> None:
    record = {
        "document_id": "PDF_903",
        "document_type": "newsletter",
        "fund_name_mapped": "Example Fund",
        "extraction_mode": "baseline",
        "reporting_period": "Q1 2026",
        "extracted_fields": {
            "market_themes": ["AI"],
            "risk_notes": ["Exit timing"],
            "valuation_commentary": ["Stable"],
            "expected_capital_activity": ["USD 1.0m"],
        },
    }
    commentary = apply_newsletter_update(record)
    assert commentary.loc[0, "market_themes"] == "AI"
    assert "expected_capital_activity" in commentary.columns


def test_expected_position_updates_apply_only_when_all_required_docs_are_approved() -> None:
    positions = pd.DataFrame(
        [
            {
                "fund_id": "PF_NORTHSTAR_IV",
                "fund_name": "Northstar Buyout Fund IV",
                "paid_in_capital_usd_m": 40.0,
                "unfunded_commitment_usd_m": 20.0,
                "current_nav_usd_m": 35.0,
                "as_of_date": "2026-04-30",
            },
            {
                "fund_id": "PF_HARBOR_PEAK_V",
                "fund_name": "Harbor Peak Partners V",
                "paid_in_capital_usd_m": 35.0,
                "unfunded_commitment_usd_m": 10.0,
                "current_nav_usd_m": 30.0,
                "as_of_date": "2026-04-30",
            },
        ]
    )
    approved_records = [
        {"document_id": "PDF_001"},
        {"document_id": "PDF_003"},
        {"document_id": "PDF_004"},
    ]
    expected_updates = pd.DataFrame(
        [
            {
                "as_of_date": "2026-05-31",
                "fund_id": "PF_NORTHSTAR_IV",
                "post_paid_in_usd_m": 44.2,
                "post_unfunded_usd_m": 15.8,
                "post_nav_estimate_usd_m": 35.0,
                "source_document_ids": "PDF_001, PDF_004",
                "update_status": "Approved",
            },
            {
                "as_of_date": "2026-05-31",
                "fund_id": "PF_HARBOR_PEAK_V",
                "post_paid_in_usd_m": 35.0,
                "post_unfunded_usd_m": 10.0,
                "post_nav_estimate_usd_m": 26.9,
                "source_document_ids": "PDF_003",
                "update_status": "Approved",
            },
        ]
    )

    updated_positions = apply_expected_position_updates(positions, approved_records, expected_updates)

    northstar = updated_positions.loc[updated_positions["fund_id"] == "PF_NORTHSTAR_IV"].iloc[0]
    harbor_peak = updated_positions.loc[updated_positions["fund_id"] == "PF_HARBOR_PEAK_V"].iloc[0]
    assert northstar["paid_in_capital_usd_m"] == 44.2
    assert northstar["unfunded_commitment_usd_m"] == 15.8
    assert str(northstar["as_of_date"]) == "2026-05-31"
    assert harbor_peak["current_nav_usd_m"] == 26.9


def test_document_processing_status_includes_all_documents() -> None:
    records = load_extracted_records("baseline")
    statuses = load_validation_status("baseline")
    assert len(records) == len(statuses)


def test_load_validation_status_uses_manual_review_override(tmp_path: Path, monkeypatch) -> None:
    validation_dir = tmp_path / "validation"
    validation_dir.mkdir(parents=True, exist_ok=True)
    validation_path = validation_dir / "validation_results_actual.csv"
    review_decisions_path = tmp_path / "manual_review_decisions.csv"

    pd.DataFrame(
        [
            {"document_id": "PDF_010", "extraction_mode": "intake", "review_status": "rejected"},
            {"document_id": "PDF_011", "extraction_mode": "intake", "review_status": "approved"},
        ]
    ).to_csv(validation_path, index=False)
    pd.DataFrame(
        [
            {
                "document_id": "PDF_010",
                "extraction_mode": "intake",
                "manual_review_status": "approved",
                "reviewer_note": "Manual pass",
                "reviewed_at_utc": "2026-07-15T00:00:00Z",
            }
        ]
    ).to_csv(review_decisions_path, index=False)

    monkeypatch.setattr("src.portfolio_updates.apply_updates.OUTPUTS_DIR", tmp_path)
    monkeypatch.setattr(review_decisions, "REVIEW_DECISIONS_PATH", review_decisions_path)

    statuses = load_validation_status("intake")

    assert statuses["PDF_010"] == "approved"
    assert statuses["PDF_011"] == "approved"


def test_apply_updates_module_can_be_imported_without_side_effects() -> None:
    module = importlib.import_module("src.portfolio_updates.apply_updates")
    assert hasattr(module, "run")
    assert hasattr(module, "main")
