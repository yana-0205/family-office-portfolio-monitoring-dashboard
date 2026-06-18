from __future__ import annotations

from difflib import get_close_matches
from typing import Any

import pandas as pd


def _build_result(
    rule_id: str,
    rule_name: str,
    status: str,
    severity: str,
    message: str,
    field_name: str,
    expected_value: Any = None,
    actual_value: Any = None,
) -> dict[str, Any]:
    return {
        "rule_id": rule_id,
        "rule_name": rule_name,
        "status": status,
        "severity": severity,
        "message": message,
        "field_name": field_name,
        "expected_value": expected_value,
        "actual_value": actual_value,
    }


def _normalized(value: Any) -> str:
    return str(value or "").strip().casefold()


def _get_fund_names(record: dict) -> tuple[str | None, str | None]:
    return record.get("fund_name_raw"), record.get("fund_name_mapped")


def _find_fund_master_match(record: dict, tables: dict[str, pd.DataFrame]) -> dict[str, Any]:
    fund_master = tables.get("private_fund_master")
    fund_aliases = tables.get("fund_aliases")
    raw_name, mapped_name = _get_fund_names(record)
    candidates = [name for name in [mapped_name, raw_name] if name]

    if fund_master is None or fund_master.empty:
        return {"match_type": "missing_table", "matched_name": None}

    master_names = fund_master["fund_name"].astype(str).tolist()
    normalized_master = {_normalized(name): name for name in master_names}

    for name in candidates:
        if _normalized(name) in normalized_master:
            return {
                "match_type": "exact",
                "matched_name": normalized_master[_normalized(name)],
                "matched_on": name,
            }

    if fund_aliases is not None and not fund_aliases.empty:
        alias_map = {
            _normalized(alias): canonical
            for alias, canonical in zip(
                fund_aliases["alias"].astype(str),
                fund_aliases["canonical_fund_name"].astype(str),
            )
        }
        for name in candidates:
            if _normalized(name) in alias_map:
                return {
                    "match_type": "alias",
                    "matched_name": alias_map[_normalized(name)],
                    "matched_on": name,
                }

    normalized_values = list(normalized_master.keys())
    for name in candidates:
        match = get_close_matches(_normalized(name), normalized_values, n=1, cutoff=0.88)
        if match:
            return {
                "match_type": "fuzzy",
                "matched_name": normalized_master[match[0]],
                "matched_on": name,
            }

    return {"match_type": "none", "matched_name": None, "matched_on": mapped_name or raw_name}


def check_fund_master_match(record: dict, tables: dict[str, pd.DataFrame]) -> dict[str, Any]:
    match_result = _find_fund_master_match(record, tables)
    actual_name = record.get("fund_name_mapped") or record.get("fund_name_raw")

    if match_result["match_type"] == "missing_table":
        return _build_result(
            "VR001",
            "Fund master match",
            "warning",
            "medium",
            "Fund master table unavailable; unable to verify fund name.",
            "fund_name_mapped",
            None,
            actual_name,
        )
    if match_result["match_type"] == "exact":
        return _build_result(
            "VR001",
            "Fund master match",
            "passed",
            "info",
            "Fund name matched private fund master exactly.",
            "fund_name_mapped",
            match_result["matched_name"],
            actual_name,
        )
    if match_result["match_type"] in {"alias", "fuzzy"}:
        return _build_result(
            "VR001",
            "Fund master match",
            "warning",
            "medium" if match_result["match_type"] == "alias" else "high",
            f"Fund name matched via {match_result['match_type']} resolution.",
            "fund_name_mapped",
            match_result["matched_name"],
            match_result["matched_on"],
        )
    return _build_result(
        "VR001",
        "Fund master match",
        "failed",
        "high",
        "Fund name could not be matched to private fund master.",
        "fund_name_mapped",
        "Known fund in private_fund_master",
        actual_name,
    )


def check_required_field_completeness(record: dict) -> dict[str, Any]:
    extracted = record.get("extracted_fields", {})
    doc_type = record.get("document_type")
    fund_present = bool(record.get("fund_name_mapped") or record.get("fund_name_raw"))
    missing: list[str] = []

    if not fund_present:
        missing.append("fund_name")

    if doc_type == "capital_call":
        if extracted.get("due_date") is None:
            missing.append("due_date")
        if extracted.get("amount_due") is None:
            missing.append("amount_due")
        if record.get("currency") is None:
            missing.append("currency")
    elif doc_type == "distribution":
        if extracted.get("payment_date") is None:
            missing.append("payment_date")
        if extracted.get("gross_distribution") is None and extracted.get("net_distribution") is None:
            missing.append("gross_distribution_or_net_distribution")
        if record.get("currency") is None:
            missing.append("currency")
    elif doc_type == "capital_statement":
        for field_name in [
            "period_end_date",
            "ending_nav",
            "total_commitment",
            "paid_in_capital",
            "unfunded_commitment",
        ]:
            if extracted.get(field_name) is None:
                missing.append(field_name)
        if record.get("currency") is None:
            missing.append("currency")
    elif doc_type == "newsletter":
        qualitative = any(
            extracted.get(field_name)
            for field_name in [
                "market_themes",
                "risk_notes",
                "valuation_commentary",
                "expected_capital_activity",
            ]
        )
        if not qualitative:
            missing.append("qualitative_content")

    if missing:
        return _build_result(
            "VR002",
            "Required field completeness",
            "failed",
            "high",
            "Missing required fields: " + ", ".join(missing),
            "required_fields",
            "All required fields populated",
            ", ".join(missing),
        )
    return _build_result(
        "VR002",
        "Required field completeness",
        "passed",
        "info",
        "All required fields are populated.",
        "required_fields",
        "All required fields populated",
        "complete",
    )


def check_due_date_urgency(record: dict, reference_date: str = "2026-05-01") -> dict[str, Any]:
    if record.get("document_type") != "capital_call":
        return _build_result("VR003", "Due date urgency", "passed", "info", "Rule not applicable.", "due_date")

    due_date = record.get("extracted_fields", {}).get("due_date")
    if due_date is None:
        return _build_result(
            "VR003",
            "Due date urgency",
            "failed",
            "high",
            "Due date missing for capital call.",
            "due_date",
            "Valid due date",
            due_date,
        )

    days_until_due = (pd.to_datetime(due_date) - pd.to_datetime(reference_date)).days
    if days_until_due <= 7:
        return _build_result(
            "VR003",
            "Due date urgency",
            "warning",
            "high",
            f"Due date is within 7 days of reference date ({days_until_due} days).",
            "due_date",
            "> 7 days from reference date",
            due_date,
        )
    if days_until_due <= 14:
        return _build_result(
            "VR003",
            "Due date urgency",
            "warning",
            "medium",
            f"Due date is within 14 days of reference date ({days_until_due} days).",
            "due_date",
            "> 14 days from reference date",
            due_date,
        )
    return _build_result(
        "VR003",
        "Due date urgency",
        "passed",
        "info",
        "Due date is not urgent relative to reference date.",
        "due_date",
        "> 14 days from reference date",
        due_date,
    )


def check_cash_sufficiency(record: dict, tables: dict[str, pd.DataFrame]) -> dict[str, Any]:
    if record.get("document_type") != "capital_call":
        return _build_result("VR004", "Cash sufficiency", "passed", "info", "Rule not applicable.", "amount_due")

    amount_due = record.get("extracted_fields", {}).get("amount_due")
    cash_accounts = tables.get("cash_accounts")
    if cash_accounts is None or cash_accounts.empty:
        return _build_result(
            "VR004",
            "Cash sufficiency",
            "warning",
            "medium",
            "Cash accounts table unavailable; unable to verify liquidity coverage.",
            "amount_due",
            None,
            amount_due,
        )

    usd_accounts = cash_accounts.loc[cash_accounts["currency"].astype(str).str.upper() == "USD"]
    operating_cash = usd_accounts.loc[
        usd_accounts["account_name"].astype(str).str.contains("Operating Cash", case=False, na=False)
    ]["balance_usd_m"].sum()
    total_usd_cash = usd_accounts["balance_usd_m"].sum()

    if amount_due is None:
        return _build_result(
            "VR004",
            "Cash sufficiency",
            "warning",
            "medium",
            "Amount due missing; unable to verify liquidity coverage.",
            "amount_due",
            "Known amount due",
            amount_due,
        )
    if amount_due > total_usd_cash:
        return _build_result(
            "VR004",
            "Cash sufficiency",
            "failed",
            "critical",
            "Amount due exceeds total available USD cash.",
            "amount_due",
            total_usd_cash,
            amount_due,
        )
    if amount_due > operating_cash:
        return _build_result(
            "VR004",
            "Cash sufficiency",
            "warning",
            "high",
            "Amount due exceeds USD operating cash and may require liquidation of short-term liquidity.",
            "amount_due",
            operating_cash,
            amount_due,
        )
    return _build_result(
        "VR004",
        "Cash sufficiency",
        "passed",
        "info",
        "Amount due is covered by available USD operating cash.",
        "amount_due",
        operating_cash,
        amount_due,
    )


def check_commitment_consistency(record: dict) -> dict[str, Any]:
    if record.get("document_type") not in {"capital_call", "capital_statement"}:
        return _build_result("VR005", "Commitment consistency", "passed", "info", "Rule not applicable.", "total_commitment")

    extracted = record.get("extracted_fields", {})
    total_commitment = extracted.get("total_commitment")
    paid_in = extracted.get("paid_in_capital")
    unfunded = extracted.get("unfunded_commitment")
    if None in (total_commitment, paid_in, unfunded):
        severity = "high" if record.get("document_type") == "capital_statement" else "medium"
        status = "failed" if record.get("document_type") == "capital_statement" else "warning"
        return _build_result(
            "VR005",
            "Commitment consistency",
            status,
            severity,
            "Insufficient commitment fields to reconcile total commitment.",
            "total_commitment",
            "paid_in_capital + unfunded_commitment == total_commitment",
            {
                "total_commitment": total_commitment,
                "paid_in_capital": paid_in,
                "unfunded_commitment": unfunded,
            },
        )

    variance = round((paid_in + unfunded) - total_commitment, 4)
    if abs(variance) > 0.05:
        return _build_result(
            "VR005",
            "Commitment consistency",
            "failed",
            "high",
            "Paid-in capital plus unfunded commitment does not reconcile to total commitment.",
            "total_commitment",
            total_commitment,
            paid_in + unfunded,
        )
    return _build_result(
        "VR005",
        "Commitment consistency",
        "passed",
        "info",
        "Commitment fields reconcile within tolerance.",
        "total_commitment",
        total_commitment,
        paid_in + unfunded,
    )


def check_nav_roll_forward(record: dict) -> dict[str, Any]:
    if record.get("document_type") != "capital_statement":
        return _build_result("VR006", "NAV roll-forward check", "passed", "info", "Rule not applicable.", "ending_nav")

    extracted = record.get("extracted_fields", {})
    needed = [
        "beginning_nav",
        "contributions",
        "distributions",
        "management_fees",
        "partnership_expenses",
        "realized_gain_loss",
        "unrealized_gain_loss",
        "ending_nav",
    ]
    missing = [field for field in needed if extracted.get(field) is None]
    if missing:
        return _build_result(
            "VR006",
            "NAV roll-forward check",
            "warning",
            "medium",
            "Missing fields for NAV roll-forward: " + ", ".join(missing),
            "ending_nav",
            "Complete roll-forward fields",
            ", ".join(missing),
        )

    distributions = abs(extracted["distributions"])
    management_fees = abs(extracted["management_fees"])
    partnership_expenses = abs(extracted["partnership_expenses"])
    calculated = (
        extracted["beginning_nav"]
        + extracted["contributions"]
        - distributions
        - management_fees
        - partnership_expenses
        + extracted["realized_gain_loss"]
        + extracted["unrealized_gain_loss"]
    )
    variance = round(calculated - extracted["ending_nav"], 4)
    if abs(variance) > 0.05:
        return _build_result(
            "VR006",
            "NAV roll-forward check",
            "failed",
            "critical",
            "NAV roll-forward does not reconcile to ending NAV.",
            "ending_nav",
            round(calculated, 4),
            extracted["ending_nav"],
        )
    return _build_result(
        "VR006",
        "NAV roll-forward check",
        "passed",
        "info",
        "NAV roll-forward reconciles within tolerance.",
        "ending_nav",
        round(calculated, 4),
        extracted["ending_nav"],
    )


def check_distribution_component_sum(record: dict) -> dict[str, Any]:
    if record.get("document_type") != "distribution":
        return _build_result("VR007", "Component sum check", "passed", "info", "Rule not applicable.", "net_distribution")

    extracted = record.get("extracted_fields", {})
    required_components = ["return_of_capital", "realized_gain", "income"]
    if any(extracted.get(field) is None for field in required_components):
        return _build_result(
            "VR007",
            "Component sum check",
            "warning",
            "medium",
            "Missing distribution components required for reconciliation.",
            "net_distribution",
            "Complete distribution components",
            {field: extracted.get(field) for field in required_components},
        )

    component_total = (
        (extracted.get("return_of_capital") or 0.0)
        + (extracted.get("realized_gain") or 0.0)
        + (extracted.get("income") or 0.0)
        + (extracted.get("recallable_distribution") or 0.0)
        - (extracted.get("withholding") or 0.0)
    )
    target = extracted.get("net_distribution")
    if target is None:
        target = extracted.get("gross_distribution")
    if target is None:
        return _build_result(
            "VR007",
            "Component sum check",
            "warning",
            "medium",
            "Distribution total missing; unable to reconcile components.",
            "net_distribution",
            "Known net or gross distribution",
            None,
        )
    if abs(component_total - target) > 0.05:
        return _build_result(
            "VR007",
            "Component sum check",
            "failed",
            "high",
            "Distribution components do not reconcile to distribution total.",
            "net_distribution",
            round(component_total, 4),
            target,
        )
    return _build_result(
        "VR007",
        "Component sum check",
        "passed",
        "info",
        "Distribution components reconcile within tolerance.",
        "net_distribution",
        round(component_total, 4),
        target,
    )


def check_fuzzy_fund_name_warning(record: dict, tables: dict[str, pd.DataFrame]) -> dict[str, Any]:
    match_result = _find_fund_master_match(record, tables)
    raw_name, mapped_name = _get_fund_names(record)
    if match_result["match_type"] in {"alias", "fuzzy"} or (
        raw_name and mapped_name and _normalized(raw_name) != _normalized(mapped_name)
    ):
        return _build_result(
            "VR008",
            "Fuzzy fund name warning",
            "warning",
            "medium",
            "Fund name required alias or fuzzy normalization and should be reviewed.",
            "fund_name_raw",
            mapped_name,
            raw_name,
        )
    return _build_result(
        "VR008",
        "Fuzzy fund name warning",
        "passed",
        "info",
        "No alias or fuzzy normalization warning required.",
        "fund_name_raw",
        mapped_name,
        raw_name,
    )


def check_low_confidence_review(record: dict, threshold: float = 0.85) -> dict[str, Any]:
    confidence_score = record.get("confidence_score")
    if confidence_score is None:
        return _build_result(
            "VR009",
            "Low confidence review",
            "warning",
            "medium",
            "Confidence score missing.",
            "confidence_score",
            threshold,
            confidence_score,
        )
    if confidence_score < threshold:
        return _build_result(
            "VR009",
            "Low confidence review",
            "warning",
            "medium",
            f"Confidence score below threshold {threshold}.",
            "confidence_score",
            threshold,
            confidence_score,
        )
    return _build_result(
        "VR009",
        "Low confidence review",
        "passed",
        "info",
        "Confidence score is at or above threshold.",
        "confidence_score",
        threshold,
        confidence_score,
    )
