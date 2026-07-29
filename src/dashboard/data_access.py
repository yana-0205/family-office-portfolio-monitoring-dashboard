from __future__ import annotations

import json
import re
import warnings
from pathlib import Path

import pandas as pd

from src.config import CSV_DIR, OUTPUTS_DIR, PROCESSED_DATA_DIR, REPORTS_DIR, RISK_OUTPUTS_DIR
from src.data_loader import read_csv_table, safe_find_csv
from src.ingestion.inbox import load_ingestion_inbox
from src.risk.market_data_loader import load_market_prices, load_proxy_map
from src.validation.review_decisions import (
    apply_review_decisions_to_validation_results,
    build_effective_review_queue,
)


_MONTH_YEAR_PATTERN = re.compile(r"([A-Za-z]+)\s+(20\d{2})")


def _empty_df(message: str, columns: list[str] | None = None) -> pd.DataFrame:
    warnings.warn(message, stacklevel=2)
    df = pd.DataFrame(columns=columns or [])
    df.attrs["warning"] = message
    return df


def _safe_sum(df: pd.DataFrame, possible_columns: list[str]) -> float:
    if df.empty:
        return 0.0
    for column in possible_columns:
        if column in df.columns:
            return float(pd.to_numeric(df[column], errors="coerce").fillna(0).sum())
    return 0.0


def load_processed_table(filename: str) -> pd.DataFrame:
    path = PROCESSED_DATA_DIR / filename
    if not path.exists():
        return _empty_df(f"Processed table not found: {path}")
    return pd.read_csv(path)


def load_private_positions() -> pd.DataFrame:
    return load_processed_table("private_positions_post_ingestion.csv")


def load_cash_accounts() -> pd.DataFrame:
    return load_processed_table("cash_accounts_post_ingestion.csv")


def load_capital_call_calendar() -> pd.DataFrame:
    return load_processed_table("capital_call_calendar.csv")


def load_private_market_cashflows() -> pd.DataFrame:
    return load_processed_table("private_market_cashflows.csv")


def load_document_processing_status() -> pd.DataFrame:
    return load_processed_table("document_processing_status.csv")


def load_latest_overlay_month_end() -> pd.Timestamp | None:
    return _derive_overlay_date(load_document_processing_status())


def load_official_baseline_month_end() -> pd.Timestamp | None:
    baseline_summary_path = CSV_DIR / "portfolio_monthly_summary.csv"
    if not baseline_summary_path.exists():
        warnings.warn(f"Official baseline monthly summary not found: {baseline_summary_path}", stacklevel=2)
        return None
    baseline_summary_df = pd.read_csv(baseline_summary_path)
    if "date" not in baseline_summary_df.columns:
        warnings.warn("Official baseline monthly summary is missing a date column.", stacklevel=2)
        return None
    baseline_dates = pd.to_datetime(baseline_summary_df["date"], errors="coerce").dropna()
    if baseline_dates.empty:
        warnings.warn("Official baseline monthly summary does not contain valid dates.", stacklevel=2)
        return None
    return baseline_dates.max().to_period("M").to_timestamp("M")


def load_external_market_through_date() -> pd.Timestamp | None:
    completed_dates: list[pd.Timestamp] = []
    risk_metrics_df = load_public_risk_metrics()
    if not risk_metrics_df.empty and "end_date" in risk_metrics_df.columns:
        end_dates = pd.to_datetime(risk_metrics_df["end_date"], errors="coerce").dropna()
        if not end_dates.empty:
            completed_dates.append(end_dates.max().to_period("M").to_timestamp("M"))
    price_df = load_public_monthly_prices()
    if not price_df.empty and "date" in price_df.columns:
        price_dates = pd.to_datetime(price_df["date"], errors="coerce").dropna()
        if not price_dates.empty:
            price_working_df = price_df.assign(_parsed_date=pd.to_datetime(price_df["date"], errors="coerce")).dropna(subset=["_parsed_date"])
            if "ticker" in price_working_df.columns:
                common_price_date = price_working_df.groupby("ticker")["_parsed_date"].max().min()
            else:
                common_price_date = price_dates.max()
            completed_dates.append(common_price_date.to_period("M").to_timestamp("M"))
    return min(completed_dates) if completed_dates else None


def load_ingestion_inbox_status() -> pd.DataFrame:
    inbox_df = load_ingestion_inbox()
    if inbox_df.empty:
        return inbox_df
    return inbox_df.sort_values("staged_at_utc", ascending=False).reset_index(drop=True)


def load_fund_commentary() -> pd.DataFrame:
    return load_processed_table("fund_commentary_post_ingestion.csv")


def load_review_queue() -> pd.DataFrame:
    path = OUTPUTS_DIR / "validation" / "review_queue_actual.csv"
    if not path.exists():
        return _empty_df(f"Review queue not found: {path}")
    review_queue_df = pd.read_csv(path)
    validation_results_df = load_validation_results()
    return build_effective_review_queue(review_queue_df, validation_results_df)


def load_validation_results() -> pd.DataFrame:
    path = OUTPUTS_DIR / "validation" / "validation_results_actual.csv"
    if not path.exists():
        return _empty_df(f"Validation results not found: {path}")
    return apply_review_decisions_to_validation_results(pd.read_csv(path))


def load_extracted_json_records(mode: str = "baseline") -> list[dict]:
    directory = OUTPUTS_DIR / "extracted_json" / mode
    if not directory.exists():
        warnings.warn(f"Extracted JSON directory not found: {directory}", stacklevel=2)
        return []
    records = []
    for path in sorted(directory.glob("*.json")):
        records.append(json.loads(path.read_text(encoding="utf-8")))
    if not records:
        warnings.warn(f"No extracted JSON records found in {directory}", stacklevel=2)
    return records


def load_baseline_allocation_if_available() -> pd.DataFrame:
    csv_path = safe_find_csv(["portfolio_holdings", "portfolio holdings"])
    if csv_path is None or not csv_path.exists():
        return _empty_df(
            f"Baseline allocation source not found in {CSV_DIR}.",
            columns=["asset_class", "final_value_usd_m", "allocation_pct"],
        )
    baseline_df = read_csv_table("portfolio_holdings")
    if baseline_df.empty:
        return _empty_df(
            "Baseline allocation table is empty.",
            columns=["asset_class", "final_value_usd_m", "allocation_pct"],
        )

    if {"asset_class", "final_value_usd_m", "allocation_pct"}.issubset(baseline_df.columns):
        grouped = (
            baseline_df.groupby("asset_class", as_index=False)[["final_value_usd_m", "allocation_pct"]]
            .sum()
            .sort_values("final_value_usd_m", ascending=False)
        )
        return grouped

    return _empty_df(
        "Baseline allocation table is missing expected columns.",
        columns=["asset_class", "final_value_usd_m", "allocation_pct"],
    )


def load_public_risk_metrics() -> pd.DataFrame:
    path = RISK_OUTPUTS_DIR / "public_risk_metrics.csv"
    if not path.exists():
        return _empty_df(f"Public risk metrics not found: {path}")
    return pd.read_csv(path)


def load_correlation_matrix() -> pd.DataFrame:
    path = RISK_OUTPUTS_DIR / "correlation_matrix.csv"
    if not path.exists():
        return _empty_df(f"Correlation matrix not found: {path}")
    return pd.read_csv(path, index_col=0)


def load_stress_test_results() -> pd.DataFrame:
    path = RISK_OUTPUTS_DIR / "stress_test_results.csv"
    if not path.exists():
        return _empty_df(f"Stress test results not found: {path}")
    return pd.read_csv(path)


def load_report_markdown(report_filename: str) -> str | None:
    path = REPORTS_DIR / report_filename
    if not path.exists():
        warnings.warn(f"Report file not found: {path}", stacklevel=2)
        return None
    return path.read_text(encoding="utf-8")


def load_extraction_accuracy_summary(mode: str = "baseline") -> pd.DataFrame:
    path = OUTPUTS_DIR / f"{mode}_extraction_accuracy_summary.csv"
    if not path.exists():
        return _empty_df(f"Extraction accuracy summary not found: {path}")
    return pd.read_csv(path)


def load_update_summary_report() -> str | None:
    return load_report_markdown("update_summary.md")


def _load_extracted_record_lookup() -> dict[tuple[str, str], dict]:
    lookup: dict[tuple[str, str], dict] = {}
    for mode in ["baseline", "intake"]:
        directory = OUTPUTS_DIR / "extracted_json" / mode
        if not directory.exists():
            continue
        for path in sorted(directory.glob("*.json")):
            record = json.loads(path.read_text(encoding="utf-8"))
            lookup[(mode, record.get("document_id", ""))] = record
    return lookup


def _parse_possible_date(value: object) -> pd.Timestamp | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.notna(parsed):
        return pd.Timestamp(parsed)
    text = str(value)
    match = _MONTH_YEAR_PATTERN.search(text)
    if not match:
        return None
    parsed = pd.to_datetime(f"1 {match.group(1)} {match.group(2)}", errors="coerce")
    if pd.isna(parsed):
        return None
    return pd.Timestamp(parsed)


def _derive_overlay_date(document_status_df: pd.DataFrame) -> pd.Timestamp | None:
    if document_status_df.empty or "update_applied_flag" not in document_status_df.columns:
        return None
    applied_df = document_status_df[document_status_df["update_applied_flag"].fillna(False)].copy()
    if applied_df.empty or "document_id" not in applied_df.columns:
        return None

    extracted_lookup = _load_extracted_record_lookup()
    candidate_dates: list[pd.Timestamp] = []
    for row in applied_df.itertuples():
        mode = getattr(row, "extraction_mode", "baseline") or "baseline"
        document_id = getattr(row, "document_id", "")
        record = extracted_lookup.get((str(mode), str(document_id)))
        if record is None:
            continue
        possible_values = [
            record.get("notice_date"),
            record.get("reporting_period"),
            record.get("extracted_fields", {}).get("due_date"),
            record.get("extracted_fields", {}).get("payment_date"),
            record.get("extracted_fields", {}).get("period_end_date"),
        ]
        for value in possible_values:
            parsed = _parse_possible_date(value)
            if parsed is not None:
                candidate_dates.append(parsed)
    if not candidate_dates:
        return None
    return max(candidate_dates).to_period("M").to_timestamp("M")


def _append_overlay_monthly_summary(
    monthly_summary_df: pd.DataFrame,
    positions_df: pd.DataFrame,
    cash_df: pd.DataFrame,
    document_status_df: pd.DataFrame,
) -> pd.DataFrame:
    if monthly_summary_df.empty:
        return monthly_summary_df

    overlay_date = _derive_overlay_date(document_status_df)
    if overlay_date is None:
        return monthly_summary_df

    working_df = monthly_summary_df.copy()
    working_df["date"] = pd.to_datetime(working_df["date"], errors="coerce")
    working_df = working_df.dropna(subset=["date"]).sort_values("date")
    if working_df.empty:
        return monthly_summary_df

    latest_baseline = working_df.iloc[-1]
    if overlay_date <= latest_baseline["date"]:
        return monthly_summary_df

    public_markets = pd.to_numeric(latest_baseline.get("public_markets_usd_m"), errors="coerce")
    public_markets = float(public_markets) if pd.notna(public_markets) else 0.0
    private_nav = _safe_sum(positions_df, ["current_nav_usd_m"])
    cash_liquidity = _safe_sum(cash_df, ["balance_usd_m"])
    operating_cash = 0.0
    soft_liquidity = 0.0
    if not cash_df.empty and "balance_usd_m" in cash_df.columns:
        if "is_operating_cash" in cash_df.columns:
            operating_cash = _safe_sum(
                cash_df[cash_df["is_operating_cash"].fillna(False).astype(bool)],
                ["balance_usd_m"],
            )
        if "is_soft_liquidity_eligible" in cash_df.columns:
            soft_liquidity = _safe_sum(
                cash_df[cash_df["is_soft_liquidity_eligible"].fillna(False).astype(bool)],
                ["balance_usd_m"],
            )
    total_aum = public_markets + private_nav + cash_liquidity
    previous_total = pd.to_numeric(latest_baseline.get("total_aum_usd_m"), errors="coerce")
    monthly_return = None
    if pd.notna(previous_total) and float(previous_total) != 0:
        monthly_return = total_aum / float(previous_total) - 1

    overlay_row = {
        "date": overlay_date,
        "total_aum_usd_m": total_aum,
        "public_markets_usd_m": public_markets,
        "closed_end_private_fund_nav_usd_m": private_nav,
        "cash_liquidity_usd_m": cash_liquidity,
        "operating_cash_usd_m": operating_cash,
        "hard_liquidity_usd_m": operating_cash,
        "soft_liquidity_usd_m": soft_liquidity,
        "source": "approved_document_overlay",
        "return_series_label": "approved_overlay_snapshot",
        "source_label": "approved_document_overlay",
        "portfolio_monthly_return": monthly_return,
    }
    return pd.concat([working_df, pd.DataFrame([overlay_row])], ignore_index=True)


def _append_overlay_monthly_by_holding(
    monthly_by_holding_df: pd.DataFrame,
    positions_df: pd.DataFrame,
    cash_df: pd.DataFrame,
    document_status_df: pd.DataFrame,
) -> pd.DataFrame:
    if monthly_by_holding_df.empty:
        return monthly_by_holding_df

    overlay_date = _derive_overlay_date(document_status_df)
    if overlay_date is None:
        return monthly_by_holding_df

    working_df = monthly_by_holding_df.copy()
    working_df["date"] = pd.to_datetime(working_df["date"], errors="coerce")
    working_df = working_df.dropna(subset=["date"]).sort_values("date")
    if working_df.empty:
        return monthly_by_holding_df

    latest_date = working_df["date"].max()
    if overlay_date <= latest_date:
        return monthly_by_holding_df

    latest_rows = working_df[working_df["date"] == latest_date].copy()
    replace_asset_classes = set()
    if not positions_df.empty and "asset_class" in positions_df.columns:
        replace_asset_classes.update(positions_df["asset_class"].dropna().astype(str).tolist())
    if not cash_df.empty:
        replace_asset_classes.add("Cash & Liquidity")

    carry_forward_rows = latest_rows[~latest_rows["asset_class"].astype(str).isin(replace_asset_classes)].copy()
    carry_forward_rows["date"] = overlay_date
    carry_forward_rows["source"] = "approved_document_overlay"

    generated_rows: list[dict[str, object]] = []
    if not positions_df.empty and {"asset_class", "current_nav_usd_m"}.issubset(positions_df.columns):
        private_grouped = positions_df.groupby("asset_class", as_index=False)["current_nav_usd_m"].sum()
        for row in private_grouped.itertuples():
            generated_rows.append(
                {
                    "date": overlay_date,
                    "holding_id": f"OVERLAY_{str(row.asset_class).upper().replace(' ', '_').replace('&', 'AND').replace('/', '_')}",
                    "holding_name": f"{row.asset_class} Overlay Snapshot",
                    "asset_class": row.asset_class,
                    "value_usd_m": row.current_nav_usd_m,
                    "source": "approved_document_overlay",
                }
            )
    cash_total = _safe_sum(cash_df, ["balance_usd_m"])
    generated_rows.append(
        {
            "date": overlay_date,
            "holding_id": "OVERLAY_CASH_AND_LIQUIDITY",
            "holding_name": "Cash & Liquidity Overlay Snapshot",
            "asset_class": "Cash & Liquidity",
            "value_usd_m": cash_total,
            "source": "approved_document_overlay",
        }
    )
    overlay_rows_df = pd.DataFrame(generated_rows)
    return pd.concat([working_df, carry_forward_rows, overlay_rows_df], ignore_index=True)


def _append_overlay_position_exposure_history(
    exposure_history_df: pd.DataFrame,
    positions_df: pd.DataFrame,
    cash_df: pd.DataFrame,
    document_status_df: pd.DataFrame,
) -> pd.DataFrame:
    if exposure_history_df.empty:
        return exposure_history_df

    overlay_date = _derive_overlay_date(document_status_df)
    if overlay_date is None:
        return exposure_history_df

    working_df = exposure_history_df.copy()
    working_df["date"] = pd.to_datetime(working_df["date"], errors="coerce")
    working_df = working_df.dropna(subset=["date"]).sort_values("date")
    if working_df.empty:
        return exposure_history_df

    latest_date = working_df["date"].max()
    if overlay_date <= latest_date:
        return exposure_history_df

    latest_rows = working_df[working_df["date"] == latest_date].copy()
    overlay_rows = latest_rows.copy()
    overlay_rows["date"] = overlay_date
    overlay_rows["classification_status"] = overlay_rows.get("classification_status", pd.Series(index=overlay_rows.index)).fillna("overlay")

    if not positions_df.empty and {"fund_id", "current_nav_usd_m"}.issubset(positions_df.columns):
        positions_lookup = positions_df.set_index("fund_id")
        for index, row in overlay_rows.iterrows():
            holding_id = str(row.get("holding_id", ""))
            if not holding_id.startswith("H_PF_"):
                continue
            fund_id = holding_id.replace("H_", "", 1)
            if fund_id not in positions_lookup.index:
                continue
            current_nav = pd.to_numeric(positions_lookup.at[fund_id, "current_nav_usd_m"], errors="coerce")
            if pd.isna(current_nav):
                continue
            overlay_rows.at[index, "market_value_usd_m"] = float(current_nav)
            overlay_rows.at[index, "signed_notional_usd_m"] = float(current_nav)
            overlay_rows.at[index, "gross_notional_usd_m"] = float(abs(current_nav))
            overlay_rows.at[index, "delta_adjusted_exposure_usd_m"] = float(current_nav)

    total_aum = pd.to_numeric(overlay_rows["market_value_usd_m"], errors="coerce").fillna(0).sum()
    if total_aum <= 0:
        return exposure_history_df

    overlay_rows["nav_weight"] = pd.to_numeric(overlay_rows["market_value_usd_m"], errors="coerce").fillna(0) / total_aum
    overlay_rows["gross_weight"] = pd.to_numeric(overlay_rows["gross_notional_usd_m"], errors="coerce").fillna(0) / total_aum
    overlay_rows["net_weight"] = pd.to_numeric(overlay_rows["delta_adjusted_exposure_usd_m"], errors="coerce").fillna(0) / total_aum

    return pd.concat([working_df, overlay_rows], ignore_index=True)


def _append_overlay_portfolio_holdings(
    holdings_df: pd.DataFrame,
    positions_df: pd.DataFrame,
    cash_df: pd.DataFrame,
    document_status_df: pd.DataFrame,
) -> pd.DataFrame:
    if holdings_df.empty:
        return holdings_df

    overlay_date = _derive_overlay_date(document_status_df)
    if overlay_date is None:
        return holdings_df

    working_df = holdings_df.copy()
    latest_as_of_date = None
    if "as_of_date" in working_df.columns:
        working_df["as_of_date"] = pd.to_datetime(working_df["as_of_date"], errors="coerce")
        latest_as_of_date = working_df["as_of_date"].max()
    if latest_as_of_date is not None and pd.notna(latest_as_of_date) and overlay_date <= latest_as_of_date:
        return holdings_df

    latest_rows = working_df.copy()
    private_holding_ids = {f"H_{fund_id}" for fund_id in positions_df["fund_id"].dropna().astype(str)} if "fund_id" in positions_df.columns else set()
    cash_holding_ids = {f"H_{account_id}" for account_id in cash_df["cash_account_id"].dropna().astype(str)} if "cash_account_id" in cash_df.columns else set()
    replace_holding_ids = private_holding_ids | cash_holding_ids

    carry_forward_rows = latest_rows[~latest_rows["holding_id"].astype(str).isin(replace_holding_ids)].copy()
    if "as_of_date" in carry_forward_rows.columns:
        carry_forward_rows["as_of_date"] = overlay_date
    if "data_source" in carry_forward_rows.columns:
        carry_forward_rows["data_source"] = "approved_document_overlay"
    if "notes" in carry_forward_rows.columns:
        carry_forward_rows["notes"] = "Carried forward into approved document overlay month."

    latest_lookup = latest_rows.set_index("holding_id", drop=False) if "holding_id" in latest_rows.columns else pd.DataFrame()
    generated_rows: list[dict[str, object]] = []

    if not positions_df.empty and "fund_id" in positions_df.columns:
        for row in positions_df.itertuples():
            holding_id = f"H_{row.fund_id}"
            base_row = latest_lookup.loc[holding_id].to_dict() if not latest_lookup.empty and holding_id in latest_lookup.index else {}
            generated_row = dict(base_row)
            generated_row.update(
                {
                    "holding_id": holding_id,
                    "holding_name": getattr(row, "fund_name", base_row.get("holding_name", holding_id)),
                    "asset_class": getattr(row, "asset_class", base_row.get("asset_class")),
                    "sub_asset_class": getattr(row, "sub_strategy", base_row.get("sub_asset_class")),
                    "region_taxonomy": getattr(row, "investment_geography", base_row.get("region_taxonomy")),
                    "region": getattr(row, "investment_geography", base_row.get("region")),
                    "country": getattr(row, "investment_geography", base_row.get("country")),
                    "currency": base_row.get("currency", "USD"),
                    "final_value_usd_m": getattr(row, "current_nav_usd_m", None),
                    "instrument_type": base_row.get("instrument_type", "private_fund"),
                    "position_side_current": "long",
                    "current_exposure_usd_m": getattr(row, "current_nav_usd_m", None),
                    "current_gross_notional_usd_m": getattr(row, "current_nav_usd_m", None),
                    "current_delta_adjusted_exposure_usd_m": getattr(row, "current_nav_usd_m", None),
                    "gics_sector": getattr(row, "mandate_sector", base_row.get("gics_sector")),
                    "gics_industry_group": base_row.get("gics_industry_group"),
                    "market_cap_bucket": base_row.get("market_cap_bucket", "Non-classifiable"),
                    "lookthrough_method": base_row.get("lookthrough_method", "direct"),
                    "classification_status": base_row.get("classification_status", "direct"),
                    "proxy_mapping_status": base_row.get("proxy_mapping_status", "direct" if getattr(row, "proxy_mapping_flag", False) else "unmapped"),
                    "liquidity_bucket": base_row.get("liquidity_bucket", "Illiquid"),
                    "data_source": "approved_document_overlay",
                    "notes": "Updated from approved private fund documents.",
                    "entity_id": base_row.get("entity_id"),
                    "current_market_cap_bucket": base_row.get("current_market_cap_bucket", "Non-classifiable"),
                    "is_public_liquid_asset": False,
                    "is_private_asset": True,
                    "as_of_date": overlay_date,
                }
            )
            generated_rows.append(generated_row)

    if not cash_df.empty and "cash_account_id" in cash_df.columns:
        for row in cash_df.itertuples():
            holding_id = f"H_{row.cash_account_id}"
            base_row = latest_lookup.loc[holding_id].to_dict() if not latest_lookup.empty and holding_id in latest_lookup.index else {}
            generated_row = dict(base_row)
            generated_row.update(
                {
                    "holding_id": holding_id,
                    "holding_name": getattr(row, "account_name", base_row.get("holding_name", holding_id)),
                    "asset_class": "Cash & Liquidity",
                    "sub_asset_class": base_row.get("sub_asset_class", "Cash Accounts"),
                    "region_taxonomy": base_row.get("region_taxonomy", "Global / Multi-region"),
                    "region": base_row.get("region", "Global / Multi-region"),
                    "country": base_row.get("country", "Cash Pool"),
                    "currency": getattr(row, "currency", base_row.get("currency")),
                    "final_value_usd_m": getattr(row, "balance_usd_m", None),
                    "instrument_type": base_row.get("instrument_type", "cash"),
                    "position_side_current": "long",
                    "current_exposure_usd_m": getattr(row, "balance_usd_m", None),
                    "current_gross_notional_usd_m": getattr(row, "balance_usd_m", None),
                    "current_delta_adjusted_exposure_usd_m": getattr(row, "balance_usd_m", None),
                    "gics_sector": base_row.get("gics_sector", "Cash"),
                    "gics_industry_group": base_row.get("gics_industry_group", "Cash"),
                    "market_cap_bucket": base_row.get("market_cap_bucket", "Non-classifiable"),
                    "lookthrough_method": base_row.get("lookthrough_method", "direct"),
                    "classification_status": base_row.get("classification_status", "direct"),
                    "proxy_mapping_status": base_row.get("proxy_mapping_status", "direct"),
                    "liquidity_bucket": base_row.get("liquidity_bucket", getattr(row, "liquidity_bucket", "Cash")),
                    "data_source": "approved_document_overlay",
                    "notes": "Cash snapshot carried into approved document overlay month.",
                    "entity_id": getattr(row, "entity_id", base_row.get("entity_id")),
                    "current_market_cap_bucket": base_row.get("current_market_cap_bucket", "Non-classifiable"),
                    "is_public_liquid_asset": False,
                    "is_private_asset": False,
                    "as_of_date": overlay_date,
                }
            )
            generated_rows.append(generated_row)

    combined_df = pd.concat([carry_forward_rows, pd.DataFrame(generated_rows)], ignore_index=True)
    if "final_value_usd_m" in combined_df.columns:
        total_value = pd.to_numeric(combined_df["final_value_usd_m"], errors="coerce").fillna(0).sum()
        if total_value > 0:
            combined_df["allocation_pct"] = pd.to_numeric(combined_df["final_value_usd_m"], errors="coerce").fillna(0) / total_value
    return combined_df


def _append_overlay_private_fund_monthly(
    private_fund_monthly_df: pd.DataFrame,
    positions_df: pd.DataFrame,
    document_status_df: pd.DataFrame,
) -> pd.DataFrame:
    if private_fund_monthly_df.empty:
        return private_fund_monthly_df

    overlay_date = _derive_overlay_date(document_status_df)
    if overlay_date is None:
        return private_fund_monthly_df

    working_df = private_fund_monthly_df.copy()
    working_df["date"] = pd.to_datetime(working_df["date"], errors="coerce")
    working_df = working_df.dropna(subset=["date"]).sort_values("date")
    if working_df.empty:
        return private_fund_monthly_df

    latest_date = working_df["date"].max()
    if overlay_date <= latest_date or positions_df.empty:
        return private_fund_monthly_df

    overlay_rows = positions_df.copy()
    overlay_rows = overlay_rows.rename(
        columns={
            "as_of_date": "date",
            "current_nav_usd_m": "nav_usd_m",
        }
    )
    overlay_rows["date"] = overlay_date
    overlay_rows["source"] = "approved_document_overlay"
    overlay_rows = overlay_rows[
        [column for column in ["date", "fund_id", "fund_name", "nav_usd_m", "investment_geography", "mandate_sector", "strategy", "source"] if column in overlay_rows.columns]
    ].copy()
    return pd.concat([working_df, overlay_rows], ignore_index=True)


def _load_optional_raw_table(possible_names: list[str], primary_name: str) -> pd.DataFrame:
    csv_path = safe_find_csv(possible_names)
    if csv_path is None or not csv_path.exists():
        return _empty_df(f"Raw table not found for {primary_name}.")
    try:
        return read_csv_table(primary_name)
    except FileNotFoundError:
        return pd.read_csv(csv_path)


def load_portfolio_monthly_summary() -> pd.DataFrame:
    monthly_summary_df = _load_optional_raw_table(
        ["portfolio_monthly_summary", "portfolio monthly summary"],
        "portfolio_monthly_summary",
    )
    if monthly_summary_df.empty:
        return monthly_summary_df
    return _append_overlay_monthly_summary(
        monthly_summary_df,
        load_private_positions(),
        load_cash_accounts(),
        load_document_processing_status(),
    )


def load_portfolio_monthly_by_holding() -> pd.DataFrame:
    monthly_by_holding_df = _load_optional_raw_table(
        ["portfolio_monthly_by_holding", "portfolio monthly by holding"],
        "portfolio_monthly_by_holding",
    )
    if monthly_by_holding_df.empty:
        return monthly_by_holding_df
    return _append_overlay_monthly_by_holding(
        monthly_by_holding_df,
        load_private_positions(),
        load_cash_accounts(),
        load_document_processing_status(),
    )


def load_portfolio_holdings() -> pd.DataFrame:
    holdings_df = _load_optional_raw_table(["portfolio_holdings", "portfolio holdings"], "portfolio_holdings")
    if holdings_df.empty:
        return holdings_df
    return _append_overlay_portfolio_holdings(
        holdings_df,
        load_private_positions(),
        load_cash_accounts(),
        load_document_processing_status(),
    )


def load_private_fund_monthly() -> pd.DataFrame:
    private_fund_monthly_df = _load_optional_raw_table(["private_fund_monthly", "private fund monthly"], "private_fund_monthly")
    if private_fund_monthly_df.empty:
        return private_fund_monthly_df
    return _append_overlay_private_fund_monthly(
        private_fund_monthly_df,
        load_private_positions(),
        load_document_processing_status(),
    )


def load_position_exposure_history() -> pd.DataFrame:
    exposure_history_df = _load_optional_raw_table(
        ["position_exposure_history", "position exposure history"],
        "position_exposure_history",
    )
    if exposure_history_df.empty:
        return exposure_history_df
    return _append_overlay_position_exposure_history(
        exposure_history_df,
        load_private_positions(),
        load_cash_accounts(),
        load_document_processing_status(),
    )


def load_latest_position_exposure_snapshot() -> pd.DataFrame:
    history_df = load_position_exposure_history()
    if history_df.empty or "date" not in history_df.columns:
        return _empty_df("Position exposure history is unavailable.")
    snapshot_df = history_df.copy()
    snapshot_df["date"] = pd.to_datetime(snapshot_df["date"], errors="coerce")
    snapshot_df = snapshot_df.dropna(subset=["date"]).sort_values("date")
    if snapshot_df.empty:
        return _empty_df("Position exposure history is unavailable.")
    latest_date = snapshot_df["date"].max()
    return snapshot_df[snapshot_df["date"] == latest_date].copy()


def load_public_instrument_classification() -> pd.DataFrame:
    return _load_optional_raw_table(
        ["public_instrument_classification", "public instrument classification"],
        "public_instrument_classification",
    )


def load_risk_free_proxy_monthly() -> pd.DataFrame:
    return _load_optional_raw_table(
        ["risk_free_proxy_monthly", "risk free proxy monthly"],
        "risk_free_proxy_monthly",
    )


def load_public_monthly_prices() -> pd.DataFrame:
    result = load_market_prices(prefer_real=True)
    price_df = result["prices"]
    if price_df.empty:
        return _empty_df("Public monthly price table is unavailable.")
    price_df = price_df.copy()
    price_df["data_source"] = result["metadata"]["data_source"]
    return price_df


def load_public_proxy_map() -> pd.DataFrame:
    proxy_df = load_proxy_map()
    if proxy_df.empty:
        return _empty_df("Public market proxy mapping is unavailable.", columns=list(proxy_df.columns))
    return proxy_df


def load_region_taxonomy_reference() -> pd.DataFrame:
    return _load_optional_raw_table(
        ["region_taxonomy_reference", "region taxonomy reference"],
        "region_taxonomy_reference",
    )


def load_private_fund_positions_baseline() -> pd.DataFrame:
    return _load_optional_raw_table(["private_fund_positions", "private positions pre ingestion"], "private_fund_positions")


def load_asset_allocation_table() -> pd.DataFrame:
    holdings_df = load_portfolio_holdings()
    if holdings_df.empty:
        fallback = pd.DataFrame(
            [
                {"asset_class": "Global Public Equities", "final_value_usd_m": 225.0},
                {"asset_class": "Fixed Income & Liquid Credit", "final_value_usd_m": 97.5},
                {"asset_class": "Private Equity", "final_value_usd_m": 135.0},
                {"asset_class": "Venture Capital / Growth", "final_value_usd_m": 75.0},
                {"asset_class": "Private Credit", "final_value_usd_m": 67.5},
                {"asset_class": "Real Estate", "final_value_usd_m": 60.0},
                {"asset_class": "Hedge Funds / Absolute Return", "final_value_usd_m": 37.5},
                {"asset_class": "Infrastructure", "final_value_usd_m": 30.0},
                {"asset_class": "Cash & Liquidity", "final_value_usd_m": 22.5},
            ]
        )
        fallback["allocation_pct"] = fallback["final_value_usd_m"] / fallback["final_value_usd_m"].sum()
        fallback["data_source"] = "fallback from corrected project assumptions"
        return fallback

    if {"asset_class", "final_value_usd_m"}.issubset(holdings_df.columns):
        grouped = holdings_df.groupby("asset_class", as_index=False)["final_value_usd_m"].sum()
        grouped["allocation_pct"] = grouped["final_value_usd_m"] / grouped["final_value_usd_m"].sum()
        grouped["data_source"] = "raw portfolio holdings"
        return grouped.sort_values("final_value_usd_m", ascending=False)

    return _empty_df("Asset allocation table missing expected columns.")


def load_geography_exposure_if_available() -> pd.DataFrame:
    holdings_df = load_portfolio_holdings()
    region_column = None
    for candidate in ["region_taxonomy", "region"]:
        if candidate in holdings_df.columns:
            region_column = candidate
            break
    if holdings_df.empty or region_column is None or "final_value_usd_m" not in holdings_df.columns:
        return _empty_df("Geography exposure data is unavailable.", columns=["region", "final_value_usd_m"])
    grouped = holdings_df.groupby(region_column, as_index=False)["final_value_usd_m"].sum()
    grouped = grouped.rename(columns={region_column: "region"})
    return grouped.sort_values("final_value_usd_m", ascending=False)


def load_currency_exposure_if_available() -> pd.DataFrame:
    holdings_df = load_portfolio_holdings()
    if holdings_df.empty or not {"currency", "final_value_usd_m"}.issubset(holdings_df.columns):
        return _empty_df("Currency exposure data is unavailable.", columns=["currency", "final_value_usd_m"])
    return holdings_df.groupby("currency", as_index=False)["final_value_usd_m"].sum().sort_values("final_value_usd_m", ascending=False)


def load_overview_datasets() -> dict[str, pd.DataFrame]:
    return {
        "monthly_summary": load_portfolio_monthly_summary(),
        "monthly_by_holding": load_portfolio_monthly_by_holding(),
        "allocation": load_asset_allocation_table(),
        "private_positions": load_private_positions(),
        "cash_accounts": load_cash_accounts(),
        "document_status": load_document_processing_status(),
        "risk_free": load_risk_free_proxy_monthly(),
    }
