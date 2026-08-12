from __future__ import annotations

from itertools import count

import pandas as pd
import plotly.express as px
import streamlit as st

from src.config import OUTPUTS_DIR
from src.dashboard.charts import (
    asset_allocation_chart,
    asset_class_category_evolution_chart,
    asset_class_exposure_filter_chart,
    asset_class_monthly_change_chart,
    asset_class_snapshot_bars,
    asset_class_snapshot_change_bars,
    asset_class_allocation_over_time_chart,
    asset_class_by_month_chart,
    asset_class_value_trend_chart,
    capital_call_calendar_chart,
    cash_by_account_chart,
    cash_by_currency_chart,
    commitment_vs_unfunded_chart,
    correlation_heatmap,
    dimension_exposure_filter_chart,
    dimension_net_exposure_trend_chart,
    distribution_timeline_chart,
    drawdown_chart,
    cumulative_return_chart,
    document_status_chart,
    currency_exposure_chart,
    geography_exposure_chart,
    classified_signed_exposure_chart,
    liquidity_coverage_chart,
    liquidity_horizon_coverage_chart,
    liquid_vs_illiquid_chart,
    market_cap_exposure_chart,
    monthly_return_chart,
    nav_by_fund_chart,
    portfolio_return_bars_cumulative_line_chart,
    portfolio_value_trend_chart,
    private_market_cashflow_chart,
    projected_distributions_by_fund_chart,
    private_nav_trend_chart,
    private_statement_lag_chart,
    private_total_nav_trend_chart,
    private_dimension_bar_chart,
    public_private_split_chart,
    public_holdings_chart,
    public_market_value_trend_chart,
    public_proxy_basket_chart,
    public_proxy_drawdown_timeseries_chart,
    public_proxy_performance_chart,
    paid_in_vs_unfunded_stacked_chart,
    region_exposure_chart,
    risk_dimension_chart,
    risk_metric_bar_chart,
    review_status_chart,
    cash_purpose_chart,
    sector_exposure_chart,
    stress_scenario_breakdown_chart,
    stress_scenario_impact_chart,
    stress_test_chart,
    top_holdings_chart,
    unfunded_commitments_by_fund_chart,
    usd_vs_non_usd_chart,
)
from src.dashboard.components import (
    calculate_asset_class_metrics,
    build_risk_dimension_summary,
    build_stress_impact_tables,
    build_top_correlation_pairs,
    prepare_public_risk_overlay,
    calculate_commitment_summary,
    calculate_liquidity_horizon_table,
    calculate_liquidity_metrics,
    calculate_performance_statistics_table,
    calculate_portfolio_summary_metrics,
    calculate_public_market_summary,
    calculate_private_market_metrics,
    calculate_private_markets_summary,
    calculate_return_statistics_table,
    calculate_return_metrics,
    build_public_proxy_basket_history,
    build_private_dimension_summary,
    build_private_nav_timeseries,
    build_private_statement_lag_table,
    dataframe_with_empty_state,
    empty_state,
    format_percentage,
    format_multiple,
    format_usd_millions,
    format_display_dataframe,
    latest_value_from_timeseries,
    markdown_report_preview,
    metric_card,
    metric_with_delta,
    filter_projected_distribution_cashflows,
    pipeline_status_summary,
    safe_sum,
    section_header,
    show_json_preview,
    status_filter_widget,
    synthetic_data_notice,
    workflow_status_card,
)
from src.dashboard.data_access import (
    load_asset_allocation_table,
    load_capital_call_calendar,
    load_cash_accounts,
    load_currency_exposure_if_available,
    load_external_market_through_date,
    load_extraction_accuracy_summary,
    load_document_processing_status,
    load_extracted_json_records,
    load_fund_commentary,
    load_geography_exposure_if_available,
    load_ingestion_inbox_status,
    load_official_baseline_month_end,
    load_latest_overlay_month_end,
    load_correlation_matrix,
    load_overview_datasets,
    load_portfolio_holdings,
    load_portfolio_monthly_by_holding,
    load_portfolio_monthly_summary,
    load_position_exposure_history,
    load_private_fund_monthly,
    load_private_market_cashflows,
    load_private_positions,
    load_public_monthly_prices,
    load_public_proxy_map,
    load_public_risk_metrics,
    load_region_taxonomy_reference,
    load_review_queue,
    load_risk_free_proxy_monthly,
    load_stress_test_results,
    load_update_summary_report,
    load_validation_results,
)
from src.ingestion import stage_uploaded_pdf, sync_ingestion_status
from src.portfolio_updates.apply_updates import run as run_apply_updates
from src.risk.refresh_public_market_data import refresh_public_market_data_for_month
from src.testing.prepare_upload_test_state import run as prepare_upload_test_state
from src.testing.run_intake_pipeline import run as run_intake_pipeline
from src.validation.review_decisions import (
    build_effective_review_queue,
    upsert_review_decision,
)


_PLOTLY_CHART_COUNTER = count()
_SEVERITY_RANK = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
_VALIDATION_STATUS_RANK = {"failed": 0, "warning": 1, "passed": 2}
_DOCUMENT_REVIEW_ORDER = {"rejected": 0, "needs_review": 1, "approved": 2}
_SOURCE_HELP = {
    "portfolio_overlay": "Uses the processed portfolio state: official baseline plus approved PDF overlay where available.",
    "official_baseline": "Uses the official baseline portfolio month from the raw monthly summary, not the staged inbox state.",
    "external_market": "Uses external public-market prices stored under data/raw/market_prices/ and the derived risk outputs.",
    "public_proxy": "Uses the public-proxy overlay only. This is not a full total-portfolio realized performance or risk series.",
}


def _normalize_review_status(value: object) -> str:
    if value is None or pd.isna(value):
        return "unknown"
    normalized = str(value).strip().casefold()
    return normalized if normalized in _DOCUMENT_REVIEW_ORDER else normalized


def _normalize_severity(value: object) -> str:
    if value is None or pd.isna(value):
        return "info"
    normalized = str(value).strip().casefold()
    return normalized if normalized in _SEVERITY_RANK else "info"


def _row_highlight_style(status: object) -> str:
    normalized = _normalize_review_status(status)
    if normalized == "rejected":
        return "background-color: rgba(239, 68, 68, 0.16);"
    if normalized == "needs_review":
        return "background-color: rgba(245, 158, 11, 0.16);"
    if normalized == "approved":
        return "background-color: rgba(34, 197, 94, 0.08);"
    return ""


def _style_review_rows(df: pd.DataFrame, *, status_column: str) -> pd.io.formats.style.Styler:
    def _style_row(row: pd.Series) -> list[str]:
        style = _row_highlight_style(row.get(status_column))
        return [style] * len(row)

    return df.style.apply(_style_row, axis=1)


def _status_palette(status: object) -> tuple[str, str, str]:
    normalized = _normalize_review_status(status)
    palette = {
        "rejected": ("rgba(239, 68, 68, 0.16)", "#dc2626", "#991b1b"),
        "needs_review": ("rgba(245, 158, 11, 0.16)", "#f59e0b", "#92400e"),
        "approved": ("rgba(34, 197, 94, 0.08)", "#22c55e", "#166534"),
    }
    return palette.get(normalized, ("rgba(148, 163, 184, 0.08)", "#94a3b8", "#475569"))


def _status_badge(label: str, status: object) -> None:
    normalized = _normalize_review_status(status)
    palette = {
        "rejected": ("#991b1b", "rgba(254, 226, 226, 0.92)", "rgba(239, 68, 68, 0.26)"),
        "needs_review": ("#92400e", "rgba(254, 243, 199, 0.92)", "rgba(245, 158, 11, 0.28)"),
        "approved": ("#166534", "rgba(220, 252, 231, 0.92)", "rgba(34, 197, 94, 0.24)"),
    }
    text_color, background, border = palette.get(normalized, ("#475569", "rgba(241, 245, 249, 0.92)", "rgba(148, 163, 184, 0.22)"))
    display_text = str(status).replace("_", " ").title()
    st.markdown(
        (
            f"<div style='margin:0.15rem 0 0.45rem 0;'>"
            f"<div style='font-size:0.78rem;color:#64748b;margin-bottom:0.3rem;font-weight:600;'>{label}</div>"
            f"<span style='display:inline-block;padding:0.36rem 0.72rem;border-radius:999px;"
            f"border:1px solid {border};background:{background};color:{text_color};"
            f"font-size:0.88rem;font-weight:700;'>{display_text}</span></div>"
        ),
        unsafe_allow_html=True,
    )


def _inject_dashboard_theme() -> None:
    st.markdown(
        """
        <style>
        :root {
            --fo-accent: #2563eb;
            --fo-accent-soft: rgba(37, 99, 235, 0.12);
            --fo-ink: #0f172a;
            --fo-muted: #64748b;
            --fo-panel: #ffffff;
            --fo-border: rgba(148, 163, 184, 0.18);
            --fo-shadow: 0 14px 34px rgba(15, 23, 42, 0.05);
        }

        .stApp {
            background:
                radial-gradient(circle at top right, rgba(37, 99, 235, 0.06), transparent 26%),
                linear-gradient(180deg, #f8fafc 0%, #f1f5f9 100%);
        }

        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, #f8fbff 0%, #eef4ff 100%);
            border-right: 1px solid rgba(148, 163, 184, 0.16);
            min-width: 21rem !important;
            max-width: 21rem !important;
        }

        section[data-testid="stSidebar"] > div {
            padding-top: 1.2rem;
            padding-left: 1.05rem;
            padding-right: 1.05rem;
        }

        .fo-sidebar-shell {
            padding: 0.55rem 0 1.2rem 0;
        }

        .fo-sidebar-badge {
            display: inline-block;
            font-size: 0.72rem;
            font-weight: 700;
            letter-spacing: 0.12em;
            text-transform: uppercase;
            color: #1d4ed8;
            background: rgba(37, 99, 235, 0.1);
            border: 1px solid rgba(37, 99, 235, 0.12);
            border-radius: 999px;
            padding: 0.2rem 0.55rem;
            margin-bottom: 0.75rem;
        }

        .fo-sidebar-title {
            color: var(--fo-ink);
            font-size: 1.35rem;
            font-weight: 700;
            line-height: 1.2;
            margin: 0 0 0.45rem 0;
        }

        .fo-sidebar-copy {
            color: var(--fo-muted);
            font-size: 0.95rem;
            line-height: 1.5;
            margin-bottom: 1.1rem;
        }

        .fo-sidebar-divider {
            height: 1px;
            background: linear-gradient(90deg, rgba(37, 99, 235, 0.38), rgba(37, 99, 235, 0.02));
            margin: 0.25rem 0 1rem 0;
        }

        .fo-sidebar-section {
            color: #94a3b8;
            font-size: 0.76rem;
            font-weight: 700;
            letter-spacing: 0.14em;
            text-transform: uppercase;
            margin-bottom: 0.8rem;
        }

        section[data-testid="stSidebar"] div.stButton {
            margin-bottom: 0.55rem;
        }

        section[data-testid="stSidebar"] div.stButton > button {
            width: 100%;
            justify-content: flex-start;
            min-height: 3.1rem;
            border-radius: 14px;
            border: 1px solid rgba(148, 163, 184, 0.14);
            background: rgba(255, 255, 255, 0.82);
            color: #1e293b;
            font-size: 1rem;
            font-weight: 600;
            padding: 0.82rem 0.95rem;
            transition: all 120ms ease;
            box-shadow: 0 4px 16px rgba(15, 23, 42, 0.03);
        }

        section[data-testid="stSidebar"] div.stButton > button:hover {
            background: rgba(239, 246, 255, 0.96);
            border-color: rgba(37, 99, 235, 0.22);
        }

        section[data-testid="stSidebar"] div.stButton > button[kind="primary"] {
            background: linear-gradient(180deg, rgba(239, 246, 255, 1), rgba(219, 234, 254, 0.96));
            border-color: rgba(37, 99, 235, 0.34);
            box-shadow:
                inset 0 0 0 1px rgba(191, 219, 254, 0.4),
                0 10px 24px rgba(37, 99, 235, 0.08);
            color: #1d4ed8;
        }

        section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
            color: var(--fo-ink);
        }

        .fo-sidebar-footer {
            margin-top: 1.3rem;
            padding-top: 1rem;
            border-top: 1px solid rgba(148, 163, 184, 0.14);
            color: var(--fo-muted);
            font-size: 0.88rem;
            line-height: 1.45;
        }

        div[data-testid="stMetric"] {
            background: rgba(255, 255, 255, 0.96);
            border: 1px solid rgba(148, 163, 184, 0.18);
            border-radius: 20px;
            padding: 0.95rem 1rem;
            box-shadow: var(--fo-shadow);
        }

        div[data-testid="stMetricLabel"] {
            color: var(--fo-muted);
        }

        div[data-testid="stTabs"] div[data-baseweb="tab-list"] {
            gap: 0;
            border-bottom: 1px solid rgba(148, 163, 184, 0.32);
        }

        div[data-testid="stTabs"] button[data-baseweb="tab"] {
            min-width: max-content;
            min-height: 3rem;
            margin: 0;
            padding: 0.7rem 1rem 0.8rem;
            border: 0;
            border-bottom: 4px solid transparent;
            border-radius: 0 !important;
            background: transparent;
            color: #64748b;
            font-weight: 600;
            box-shadow: none;
        }

        div[data-testid="stTabs"] button[data-baseweb="tab"]:hover {
            background: rgba(226, 232, 240, 0.48);
            color: #1e293b;
        }

        div[data-testid="stTabs"] button[data-baseweb="tab"][aria-selected="true"] {
            border-bottom-color: var(--fo-accent);
            border-radius: 0 !important;
            background: rgba(239, 246, 255, 0.72);
            color: var(--fo-accent);
        }

        div[data-testid="stTabs"] div[data-baseweb="tab-highlight"] {
            display: none;
        }

        div[data-testid="stInfo"],
        div[data-testid="stAlert"] {
            border-radius: 14px;
            border: 1px solid rgba(37, 99, 235, 0.08);
            background: rgba(255, 255, 255, 0.82);
        }

        .fo-chart-card {
            background: rgba(255, 255, 255, 0.97);
            border: 1px solid rgba(148, 163, 184, 0.18);
            border-radius: 24px;
            padding: 1rem 1rem 0.65rem 1rem;
            margin: 0.35rem 0 1.1rem 0;
            box-shadow: var(--fo-shadow);
            overflow: hidden;
        }

        .fo-chart-card div[data-testid="stPlotlyChart"] {
            border-radius: 18px;
            overflow: hidden;
        }

        .fo-chart-card .js-plotly-plot,
        .fo-chart-card .plot-container,
        .fo-chart-card .svg-container {
            border-radius: 18px !important;
        }

        .block-container {
            padding-top: 1.4rem;
            padding-bottom: 2rem;
        }

        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_document_ingestion_panel(
    *,
    form_key: str,
    section_title: str,
    section_subtitle: str,
    show_processed_baseline: bool,
    document_status_df: pd.DataFrame,
) -> pd.DataFrame:
    ingestion_inbox_df = load_ingestion_inbox_status()

    section_header(section_title, section_subtitle)
    with st.form(form_key, clear_on_submit=True):
        uploaded_files = st.file_uploader(
            "Stage PDF documents for review",
            type=["pdf"],
            accept_multiple_files=True,
            help="Uploaded PDFs are written to data/interim/document_ingestion/uploaded_pdfs and queued for offline extraction.",
        )
        submitted = st.form_submit_button("Stage Selected PDFs")

    if submitted:
        if not uploaded_files:
            st.warning("Add at least one PDF before staging. The intake area stays unchanged until a file is selected.")
        else:
            staged_records: list[dict[str, object]] = []
            duplicate_records: list[dict[str, object]] = []
            for uploaded_file in uploaded_files:
                result = stage_uploaded_pdf(uploaded_file.name, uploaded_file.getvalue())
                if result["action"] == "staged":
                    staged_records.append(result)
                else:
                    duplicate_records.append(result)

            if staged_records:
                st.success(f"Staged {len(staged_records)} PDF document(s) into the interim ingestion inbox.")
            if duplicate_records:
                st.info(f"Skipped {len(duplicate_records)} duplicate PDF document(s) already present in the ingestion inbox.")
            ingestion_inbox_df = load_ingestion_inbox_status()

    if not ingestion_inbox_df.empty and not document_status_df.empty and "document_id" in document_status_df.columns:
        status_columns = [
            "document_id",
            "validation_review_status",
            "system_validation_review_status",
            "manual_review_status",
            "review_status_source",
            "reviewer_note",
        ]
        available_status_columns = [column for column in status_columns if column in document_status_df.columns]
        if len(available_status_columns) > 1:
            ingestion_inbox_df = ingestion_inbox_df.merge(
                document_status_df[available_status_columns].drop_duplicates(subset=["document_id"]),
                on="document_id",
                how="left",
            )
            current_status_series = (
                ingestion_inbox_df["validation_review_status"]
                if "validation_review_status" in ingestion_inbox_df.columns
                else pd.Series(pd.NA, index=ingestion_inbox_df.index)
            )
            inbox_status_series = (
                ingestion_inbox_df["review_status"]
                if "review_status" in ingestion_inbox_df.columns
                else pd.Series(pd.NA, index=ingestion_inbox_df.index)
            )
            ingestion_inbox_df["display_review_status"] = current_status_series.where(
                current_status_series.notna(), inbox_status_series
            )
            manual_approval_mask = (
                ingestion_inbox_df.get("review_status_source", pd.Series("", index=ingestion_inbox_df.index))
                .astype(str)
                .eq("manual_override")
                & ingestion_inbox_df["display_review_status"].map(_normalize_review_status).eq("approved")
            )
            ingestion_inbox_df["approval_note"] = ingestion_inbox_df.get(
                "review_note", pd.Series("", index=ingestion_inbox_df.index)
            ).fillna("")
            ingestion_inbox_df.loc[manual_approval_mask, "approval_note"] = "Manually approved"
        else:
            ingestion_inbox_df["display_review_status"] = pd.NA
    else:
        ingestion_inbox_df["display_review_status"] = pd.NA

    inbox_summary_cols = st.columns(3)
    with inbox_summary_cols[0]:
        metric_card("Staged Inbox Documents", f"{len(ingestion_inbox_df):,}")
    with inbox_summary_cols[1]:
        metric_card("Inbox Portfolio Impact", "None")
    with inbox_summary_cols[2]:
        metric_card("Next Step", "Offline extraction")

    inbox_columns = [
        "document_id",
        "original_filename",
        "staged_at_utc",
        "ingestion_status",
        "pipeline_readiness",
        "display_review_status",
        "approval_note",
        "portfolio_state_impact",
        "stored_path",
    ]
    available_inbox_columns = [column for column in inbox_columns if column in ingestion_inbox_df.columns]
    display_inbox_df = ingestion_inbox_df[available_inbox_columns] if not ingestion_inbox_df.empty else ingestion_inbox_df
    if not display_inbox_df.empty:
        if "display_review_status" in display_inbox_df.columns:
            display_inbox_df = display_inbox_df.rename(columns={"display_review_status": "review_status"})
            display_inbox_df["_status_sort"] = display_inbox_df["review_status"].map(_normalize_review_status).map(_DOCUMENT_REVIEW_ORDER).fillna(3)
            display_inbox_df = display_inbox_df.sort_values(["_status_sort", "document_id"]).drop(columns=["_status_sort"])
            st.dataframe(
                _style_review_rows(display_inbox_df, status_column="review_status"),
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.dataframe(display_inbox_df, use_container_width=True, hide_index=True)
    else:
        dataframe_with_empty_state(display_inbox_df, "No staged uploads are currently present.")

    return ingestion_inbox_df


def _render_processed_baseline_documents(document_status_df: pd.DataFrame) -> None:
    section_header(
        "Processed Baseline Document Set",
        "These documents have already moved through the controlled extraction and validation workflow.",
    )
    columns = [
        "document_id",
        "document_type",
        "fund_name",
        "extraction_mode",
        "extraction_status",
        "source_path",
        "validation_review_status",
        "update_applied_flag",
    ]
    available = [column for column in columns if column in document_status_df.columns]
    display_document_status_df = (
        document_status_df.sort_values("document_id")
        if not document_status_df.empty and "document_id" in document_status_df.columns
        else document_status_df
    )
    dataframe_with_empty_state(
        display_document_status_df[available] if not display_document_status_df.empty else display_document_status_df,
        "Document processing status is unavailable.",
    )


def _render_demo_checklist() -> None:
    with st.expander("Demo Checklist", expanded=False):
        st.markdown(
            "\n".join(
                [
                    "1. `Reset To Demo Start State` if you want to begin from the locked baseline month.",
                    "2. Upload the target PDFs into the staged inbox.",
                    "3. Click `Process Staged PDFs And Update Dashboard` and confirm the approved overlay month appears.",
                    "4. Click `Refresh Public Markets And Risk Data` so market-linked pages align to that overlay month.",
                    "5. Review `Overview`, `Private Markets`, `Public Markets`, and `Risk Profile`.",
                    "6. Reset again only if you want to replay the same sequence for the next demo run.",
                ]
            )
        )
        st.caption(
            "This checklist is only a reusable presentation aid. The page layout itself stays application-first."
        )


def _render_demo_reset_panel() -> None:
    with st.expander("Demo Tools", expanded=False):
        section_header(
            "Reset Demo State",
            "Return the app to the baseline-only starting point, including the external public-market timeline.",
        )
        st.caption(
            "Use this only when you want to replay the demo from scratch. It clears staged uploads, removes the current approved overlay state, rewinds public-market data to the official baseline month, and backs up the current state under outputs/test_backups/."
        )
        if st.button("Reset To Demo Start State", type="secondary", use_container_width=True):
            results = prepare_upload_test_state()
            st.cache_data.clear()
            st.session_state["manual_review_cycle"] = st.session_state.get("manual_review_cycle", 0) + 1
            st.session_state.pop("manual_review_message", None)
            st.session_state.pop("intake_pipeline_message", None)
            st.session_state.pop("market_refresh_message", None)
            for key in list(st.session_state):
                if key.endswith(("_month_value", "_month_slider", "_month_jump")):
                    st.session_state.pop(key)
            st.session_state["demo_reset_message"] = (
                "Demo reset complete. "
                f"Backup written to {results['backup_root']}. "
                "Manual approvals were cleared, PDF review states will return to their system decisions when reprocessed, "
                "and public-market and risk data were realigned to the baseline month."
            )
            st.rerun()

        reset_message = st.session_state.get("demo_reset_message")
        if reset_message:
            st.success(reset_message)


def _render_intake_processing_panel() -> None:
    section_header(
        "Update Portfolio State",
        "Process the staged PDFs so approved documents move into the dashboard state.",
    )
    st.caption(
        "This reads the staged inbox, runs extraction and validation, and applies only the approved updates to the processed portfolio inputs."
    )
    staged_inbox_df = load_ingestion_inbox_status()
    if staged_inbox_df.empty:
        st.info("Nothing is staged yet. Upload PDFs above first, then return here to update the portfolio state.")
        return
    if st.button("Process Staged PDFs And Update Dashboard", type="primary", use_container_width=True):
        results = run_intake_pipeline()
        updated_status_df = load_document_processing_status()
        sync_ingestion_status(updated_status_df)
        st.session_state["intake_pipeline_message"] = (
            "Intake pipeline complete. "
            f"Processed {results['extraction']['pdf_count']} PDF(s), "
            f"validated {results['validation']['records_validated']} record(s), "
            f"applied {results['updates']['approved_applied']} approved update(s), "
            f"blocked {results['updates']['blocked_count']} document(s)."
        )
        st.rerun()

    intake_message = st.session_state.get("intake_pipeline_message")
    if intake_message:
        st.success(intake_message)


def _load_manual_review_candidates() -> pd.DataFrame:
    review_queue_path = OUTPUTS_DIR / "validation" / "review_queue_actual.csv"
    raw_review_queue_df = pd.read_csv(review_queue_path) if review_queue_path.exists() else pd.DataFrame()
    validation_results_df = load_validation_results()
    effective_review_queue_df = build_effective_review_queue(raw_review_queue_df, validation_results_df, unresolved_only=False)
    document_status_df = load_document_processing_status()
    if document_status_df.empty:
        return effective_review_queue_df

    base_columns = [
        "document_id",
        "document_type",
        "fund_name",
        "extraction_mode",
        "source_path",
        "validation_review_status",
        "system_validation_review_status",
        "manual_review_status",
        "reviewer_note",
        "reviewed_at_utc",
        "review_status_source",
        "blocked_reason",
    ]
    available_base_columns = [column for column in base_columns if column in document_status_df.columns]
    all_docs_df = document_status_df[available_base_columns].drop_duplicates(subset=["document_id", "extraction_mode"]).copy()
    if all_docs_df.empty:
        return effective_review_queue_df

    if "review_status" not in all_docs_df.columns:
        all_docs_df["review_status"] = all_docs_df.get("validation_review_status", "unknown")
    if "system_review_status" not in all_docs_df.columns:
        all_docs_df["system_review_status"] = all_docs_df.get("system_validation_review_status", all_docs_df["review_status"])
    all_docs_df["issue_summary"] = all_docs_df.get("blocked_reason", pd.Series("", index=all_docs_df.index)).fillna("")
    all_docs_df["issue_count"] = all_docs_df["issue_summary"].astype(str).map(lambda value: 0 if not value else len([part for part in value.split(";") if part.strip()]))
    all_docs_df["highest_severity"] = all_docs_df["review_status"].map(
        lambda status: "critical" if _normalize_review_status(status) == "rejected" else ("medium" if _normalize_review_status(status) == "needs_review" else "info")
    )
    all_docs_df["recommended_action"] = all_docs_df["review_status"].map(
        lambda status: (
            "Reject and correct extraction before downstream use."
            if _normalize_review_status(status) == "rejected"
            else (
                "Analyst review required before downstream use."
                if _normalize_review_status(status) == "needs_review"
                else "Already approved for downstream use."
            )
        )
    )

    if not effective_review_queue_df.empty:
        queue_columns = [column for column in effective_review_queue_df.columns if column in all_docs_df.columns]
        all_docs_df = all_docs_df.merge(
            effective_review_queue_df[["document_id", "extraction_mode"] + [column for column in queue_columns if column not in {"document_id", "extraction_mode"}]],
            on=["document_id", "extraction_mode"],
            how="left",
            suffixes=("", "_queue"),
        )
        for column in ["review_status", "system_review_status", "manual_review_status", "review_status_source", "reviewer_note", "reviewed_at_utc", "issue_summary", "issue_count", "highest_severity", "recommended_action"]:
            queue_column = f"{column}_queue"
            if queue_column in all_docs_df.columns:
                all_docs_df[column] = all_docs_df[queue_column].where(all_docs_df[queue_column].notna(), all_docs_df[column])
                all_docs_df = all_docs_df.drop(columns=[queue_column])

    all_docs_df["system_review_status"] = all_docs_df["system_review_status"].map(_normalize_review_status)
    all_docs_df["review_status"] = all_docs_df["review_status"].map(_normalize_review_status)
    all_docs_df["highest_severity"] = all_docs_df["highest_severity"].map(_normalize_severity)
    all_docs_df["_system_sort"] = all_docs_df["system_review_status"].map(_DOCUMENT_REVIEW_ORDER).fillna(3)
    all_docs_df["_severity_sort"] = all_docs_df["highest_severity"].map(_SEVERITY_RANK).fillna(99)
    all_docs_df = all_docs_df.sort_values(["_system_sort", "_severity_sort", "document_id"]).drop(columns=["_system_sort", "_severity_sort"])
    return all_docs_df.reset_index(drop=True)


def _render_manual_review_panel() -> None:
    section_header(
        "Resolve Flagged Documents",
        "Only unresolved reject and warning PDFs are shown here. Approved documents are removed from this checklist.",
    )
    review_candidates_df = _load_manual_review_candidates()
    if not review_candidates_df.empty:
        review_candidates_df = review_candidates_df[
            review_candidates_df["review_status"].map(_normalize_review_status) != "approved"
        ].reset_index(drop=True)
    if review_candidates_df.empty:
        st.success("No flagged documents require manual review.")
        return

    review_editor_df = review_candidates_df.copy()
    review_editor_df["approve"] = False
    review_editor_df["issues"] = review_editor_df.get("issue_summary", pd.Series("", index=review_editor_df.index)).fillna("")
    review_editor_df = review_editor_df.rename(
        columns={
            "document_id": "Document ID",
            "document_type": "Type",
            "fund_name": "Fund",
            "system_review_status": "System Status",
            "review_status": "Current Status",
            "highest_severity": "Severity",
            "issue_count": "Issue Count",
            "issues": "Issues",
            "approve": "Approve",
        }
    )
    display_columns = [
        "Approve",
        "Document ID",
        "Type",
        "Fund",
        "System Status",
        "Current Status",
        "Severity",
        "Issue Count",
        "Issues",
    ]
    available_display_columns = [column for column in display_columns if column in review_editor_df.columns]
    edited_review_df = st.data_editor(
        review_editor_df[available_display_columns],
        use_container_width=True,
        hide_index=True,
        disabled=[column for column in available_display_columns if column != "Approve"],
        column_config={
            "Approve": st.column_config.CheckboxColumn("Approve", help="Select documents to approve into the dashboard state."),
            "Issues": st.column_config.TextColumn("Issues", width="large"),
            "Fund": st.column_config.TextColumn("Fund", width="medium"),
        },
        key=f"manual_review_checklist_editor_{st.session_state.get('manual_review_cycle', 0)}",
    )

    submitted = st.button("Approve Selected Documents And Rebuild Dashboard", type="primary", use_container_width=True)
    if not submitted:
        return

    selected_document_ids = set(edited_review_df.loc[edited_review_df["Approve"], "Document ID"].astype(str))
    if not selected_document_ids:
        st.session_state["manual_review_message"] = "No documents were selected for approval."
        st.rerun()

    approved_count = 0
    for row in review_candidates_df.itertuples():
        if str(row.document_id) not in selected_document_ids:
            continue
        upsert_review_decision(
            document_id=str(row.document_id),
            extraction_mode=str(row.extraction_mode),
            manual_review_status="approved",
            reviewer_note="Approved from Document Intake checklist.",
        )
        approved_count += 1

    results = run_apply_updates(mode="intake")
    updated_status_df = load_document_processing_status()
    sync_ingestion_status(updated_status_df)
    st.cache_data.clear()
    st.session_state["manual_review_message"] = (
        f"Approved {approved_count} selected document(s). "
        f"Dashboard state rebuilt with {results['approved_applied']} approved document(s) and {results['blocked_count']} blocked document(s)."
    )
    st.rerun()


def _render_market_data_refresh_panel() -> None:
    section_header(
        "Refresh Market-Linked Pages",
        "Update Public Markets and Risk Profile so their external market timeline matches the current approved PDF month.",
    )
    latest_overlay_month_end = load_latest_overlay_month_end()
    if latest_overlay_month_end is None:
        st.info("Market-linked pages will refresh after the app has an approved PDF month. Process the staged uploads first.")
        return

    st.caption(
        "This re-downloads the external market price file under data/raw/market_prices/ and reruns the risk module so the market-linked pages stay aligned with the currently approved PDF month."
    )
    st.caption(f"Current target month end from approved PDFs: {latest_overlay_month_end.strftime('%Y-%m-%d')}")

    if st.button("Refresh Public Markets And Risk Data", type="primary", use_container_width=True):
        try:
            results = refresh_public_market_data_for_month(latest_overlay_month_end)
        except Exception as exc:
            st.session_state["market_data_refresh_error"] = str(exc)
            st.rerun()

        fetch_metadata = results["fetch"]["metadata"]
        risk_results = results["risk"]
        st.cache_data.clear()
        st.session_state["market_data_refresh_message"] = (
            "External market data refresh complete. "
            f"Verified through {results['verified_through']}, "
            f"target-month coverage {results['target_month_coverage']:.0%}, "
            f"price coverage {fetch_metadata.get('coverage_ratio', 0.0):.0%}, "
            f"failed tickers {len(fetch_metadata.get('failed_tickers', []))}, "
            f"risk date range {risk_results['date_range'][0]} to {risk_results['date_range'][1]}."
        )
        st.session_state.pop("market_data_refresh_error", None)
        st.rerun()

    refresh_message = st.session_state.get("market_data_refresh_message")
    if refresh_message:
        st.success(refresh_message)

    refresh_error = st.session_state.get("market_data_refresh_error")
    if refresh_error:
        st.error(
            "Public-market refresh could not complete. "
            "Typical causes are unavailable network access or a missing market-data dependency in the current environment. "
            f"Detail: {refresh_error}"
        )


def _render_sidebar_navigation(page_labels: list[str]) -> str:
    session_key = "selected_page"
    if session_key not in st.session_state or st.session_state[session_key] not in page_labels:
        st.session_state[session_key] = page_labels[0]

    st.sidebar.markdown(
        """
        <div class="fo-sidebar-shell">
            <div class="fo-sidebar-badge">Synthetic Demo</div>
            <div class="fo-sidebar-title">Family Office Portfolio Monitoring</div>
            <div class="fo-sidebar-copy">
                Portfolio-first monitoring with document workflow controls kept separate from the main investment view.
            </div>
            <div class="fo-sidebar-divider"></div>
            <div class="fo-sidebar-section">Navigation</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    for page_label in page_labels:
        if st.sidebar.button(
            page_label,
            key=f"sidebar_nav_{page_label}",
            type="primary" if st.session_state[session_key] == page_label else "secondary",
            use_container_width=True,
        ):
            if st.session_state[session_key] != page_label:
                st.session_state[session_key] = page_label
                st.rerun()

    official_baseline = _format_optional_date(load_official_baseline_month_end())
    overlay_month = _format_optional_date(load_latest_overlay_month_end())
    external_market = _format_optional_date(load_external_market_through_date())
    st.sidebar.markdown(
        f"""
        <div class="fo-sidebar-footer">
            Official baseline: <strong>{official_baseline}</strong><br/>
            Approved overlay month: <strong>{overlay_month}</strong><br/>
            External market through: <strong>{external_market}</strong>
        </div>
        """,
        unsafe_allow_html=True,
    )
    return st.session_state[session_key]


def _render_chart(chart_or_message):
    if isinstance(chart_or_message, str):
        empty_state(chart_or_message)
    else:
        chart_or_message.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#1f2937"),
            title_font=dict(color="#1f2937"),
            legend_title_font=dict(color="#475467"),
            legend_font=dict(color="#475467"),
            margin=dict(l=36, r=28, t=72, b=42),
        )
        st.markdown('<div class="fo-chart-card">', unsafe_allow_html=True)
        st.plotly_chart(
            chart_or_message,
            width="stretch",
            key=f"plotly_chart_{next(_PLOTLY_CHART_COUNTER)}",
        )
        st.markdown("</div>", unsafe_allow_html=True)


def _render_page_header(title: str, subtitle: str) -> None:
    st.title(title)
    st.caption(subtitle)


def _render_demo_state_status_bar(*, show_market_date: bool = True) -> None:
    official_baseline = load_official_baseline_month_end()
    overlay_month = load_latest_overlay_month_end()
    external_market_through = load_external_market_through_date() if show_market_date else None

    status_cols = st.columns(3 if show_market_date else 2)
    with status_cols[0]:
        metric_card(
            "Official Baseline Month",
            _format_optional_date(official_baseline),
            _SOURCE_HELP["official_baseline"],
        )
    with status_cols[1]:
        metric_card(
            "Approved Overlay Month",
            _format_optional_date(overlay_month),
            _SOURCE_HELP["portfolio_overlay"],
        )
    if show_market_date:
        with status_cols[2]:
            metric_card(
                "External Market Data Through",
                _format_optional_date(external_market_through),
                _SOURCE_HELP["external_market"],
            )


def _prepare_monthly_table(df: pd.DataFrame, date_column: str = "date") -> pd.DataFrame:
    if df.empty or date_column not in df.columns:
        return df
    working_df = df.copy()
    working_df[date_column] = pd.to_datetime(working_df[date_column], errors="coerce")
    return working_df.dropna(subset=[date_column]).sort_values(date_column)


def _sort_with_rank(
    df: pd.DataFrame,
    ranked_columns: dict[str, dict[str, int]],
    trailing_columns: list[str] | None = None,
) -> pd.DataFrame:
    if df.empty:
        return df

    working_df = df.copy()
    sort_columns: list[str] = []
    ascending: list[bool] = []
    for column, rank_map in ranked_columns.items():
        if column not in working_df.columns:
            continue
        rank_column = f"__rank_{column}"
        working_df[rank_column] = (
            working_df[column]
            .astype(str)
            .str.lower()
            .map(rank_map)
            .fillna(len(rank_map))
        )
        sort_columns.append(rank_column)
        ascending.append(True)

    for column in trailing_columns or []:
        if column in working_df.columns:
            sort_columns.append(column)
            ascending.append(True)

    if not sort_columns:
        return working_df

    working_df = working_df.sort_values(sort_columns, ascending=ascending)
    return working_df[[column for column in working_df.columns if not column.startswith("__rank_")]]


def _prepare_public_holdings(holdings_df: pd.DataFrame) -> pd.DataFrame:
    if holdings_df.empty:
        return holdings_df
    public_df = holdings_df.copy()
    if "ticker" in public_df.columns:
        public_df = public_df[public_df["ticker"].notna() & (public_df["ticker"].astype(str).str.strip() != "")]
    elif "asset_class" in public_df.columns:
        public_df = public_df[public_df["asset_class"].astype(str).str.contains("Public", case=False, na=False)]
    return public_df


def _prepare_asset_class_exposure_history(exposure_history_df: pd.DataFrame) -> pd.DataFrame:
    return _prepare_dimension_exposure_panel(exposure_history_df, "asset_class")


def _prepare_dimension_exposure_panel(exposure_history_df: pd.DataFrame, dimension_column: str) -> pd.DataFrame:
    required = {"date", "asset_class", "position_side", "net_weight", "gross_weight"}
    required = {"date", dimension_column, "position_side", "net_weight", "gross_weight"}
    if exposure_history_df.empty or not required.issubset(exposure_history_df.columns):
        return pd.DataFrame()

    chart_df = exposure_history_df.copy()
    chart_df["date"] = pd.to_datetime(chart_df["date"], errors="coerce")
    chart_df[dimension_column] = chart_df[dimension_column].astype(str).str.strip()
    chart_df["position_side"] = chart_df["position_side"].astype(str).str.lower().str.strip()
    chart_df["net_weight"] = pd.to_numeric(chart_df["net_weight"], errors="coerce")
    chart_df["gross_weight"] = pd.to_numeric(chart_df["gross_weight"], errors="coerce")
    chart_df = chart_df.dropna(subset=["date", dimension_column, "position_side", "net_weight", "gross_weight"])
    if chart_df.empty:
        return pd.DataFrame()

    grouped = (
        chart_df.groupby(["date", dimension_column], as_index=False)
        .agg(
            long_exposure=("net_weight", lambda values: values[values > 0].sum()),
            short_exposure=("net_weight", lambda values: values[values < 0].sum()),
            net_exposure=("net_weight", "sum"),
            gross_exposure=("gross_weight", "sum"),
        )
        .sort_values(["date", dimension_column])
    )
    grouped["category_label"] = grouped[dimension_column]
    for column in ["long_exposure", "short_exposure", "net_exposure", "gross_exposure"]:
        grouped[column] = pd.to_numeric(grouped[column], errors="coerce").fillna(0.0)
    return grouped


def _asset_class_month_labels(exposure_panel_df: pd.DataFrame) -> list[str]:
    return _panel_month_labels(exposure_panel_df)


def _panel_month_labels(exposure_panel_df: pd.DataFrame) -> list[str]:
    if exposure_panel_df.empty or "date" not in exposure_panel_df.columns:
        return []
    return (
        exposure_panel_df["date"]
        .dropna()
        .drop_duplicates()
        .sort_values()
        .dt.strftime("%Y-%m")
        .tolist()
    )


def _asset_class_month_snapshot(exposure_panel_df: pd.DataFrame, month_label: str) -> pd.DataFrame:
    return _panel_month_snapshot(exposure_panel_df, month_label)


def _panel_month_snapshot(exposure_panel_df: pd.DataFrame, month_label: str) -> pd.DataFrame:
    if exposure_panel_df.empty:
        return pd.DataFrame()
    snapshot_df = exposure_panel_df[exposure_panel_df["date"].dt.strftime("%Y-%m") == month_label].copy()
    if snapshot_df.empty:
        return snapshot_df
    return snapshot_df.sort_values("net_exposure", ascending=False)


def _asset_class_month_change_snapshot(exposure_panel_df: pd.DataFrame, month_label: str) -> pd.DataFrame:
    return _panel_month_change_snapshot(exposure_panel_df, month_label)


def _panel_month_change_snapshot(exposure_panel_df: pd.DataFrame, month_label: str) -> pd.DataFrame:
    month_labels = _panel_month_labels(exposure_panel_df)
    if not month_labels or month_label not in month_labels:
        return pd.DataFrame()

    month_index = month_labels.index(month_label)
    if month_index == 0:
        return pd.DataFrame()

    current_df = _panel_month_snapshot(exposure_panel_df, month_label)
    previous_df = _panel_month_snapshot(exposure_panel_df, month_labels[month_index - 1])
    if current_df.empty or previous_df.empty:
        return pd.DataFrame()

    merged = current_df.merge(
        previous_df[
            [
                "category_label",
                "long_exposure",
                "short_exposure",
                "net_exposure",
                "gross_exposure",
            ]
        ].rename(
            columns={
                "long_exposure": "previous_long_exposure",
                "short_exposure": "previous_short_exposure",
                "net_exposure": "previous_net_exposure",
                "gross_exposure": "previous_gross_exposure",
            }
        ),
        on="category_label",
        how="outer",
    ).fillna(0.0)

    merged["long_change"] = merged["long_exposure"] - merged["previous_long_exposure"]
    merged["short_change"] = merged["short_exposure"] - merged["previous_short_exposure"]
    merged["net_change"] = merged["net_exposure"] - merged["previous_net_exposure"]
    merged["gross_change"] = merged["gross_exposure"] - merged["previous_gross_exposure"]
    return merged.sort_values("net_change", ascending=False)


def _asset_class_category_change_history(exposure_panel_df: pd.DataFrame, category_label: str) -> pd.DataFrame:
    return _panel_category_change_history(exposure_panel_df, category_label)


def _panel_category_change_history(exposure_panel_df: pd.DataFrame, category_label: str) -> pd.DataFrame:
    if exposure_panel_df.empty:
        return pd.DataFrame()
    category_df = (
        exposure_panel_df[exposure_panel_df["category_label"] == category_label]
        .copy()
        .sort_values("date")
    )
    if category_df.empty:
        return category_df
    category_df["long_change"] = category_df["long_exposure"].diff().fillna(0.0)
    category_df["short_change"] = category_df["short_exposure"].diff().fillna(0.0)
    category_df["net_change"] = category_df["net_exposure"].diff().fillna(0.0)
    category_df["gross_change"] = category_df["gross_exposure"].diff().fillna(0.0)
    return category_df


def _asset_class_snapshot_metrics(snapshot_df: pd.DataFrame) -> dict[str, object]:
    return _panel_snapshot_metrics(snapshot_df)


def _panel_snapshot_metrics(snapshot_df: pd.DataFrame) -> dict[str, object]:
    if snapshot_df.empty:
        return {
            "gross_exposure": None,
            "net_exposure": None,
            "largest_long_category": None,
            "largest_long_value": None,
            "largest_short_category": None,
            "largest_short_value": None,
        }

    long_slice = snapshot_df.sort_values("long_exposure", ascending=False).head(1)
    short_slice = snapshot_df.sort_values("short_exposure", ascending=True).head(1)
    largest_long_category = long_slice["category_label"].iloc[0] if not long_slice.empty else None
    largest_long_value = float(long_slice["long_exposure"].iloc[0]) if not long_slice.empty else None
    largest_short_category = short_slice["category_label"].iloc[0] if not short_slice.empty else None
    largest_short_value = float(short_slice["short_exposure"].iloc[0]) if not short_slice.empty else None

    return {
        "gross_exposure": float(snapshot_df["gross_exposure"].sum()),
        "net_exposure": float(snapshot_df["net_exposure"].sum()),
        "largest_long_category": largest_long_category,
        "largest_long_value": largest_long_value,
        "largest_short_category": largest_short_category,
        "largest_short_value": largest_short_value,
    }


def _asset_class_attribution_panel(exposure_panel_df: pd.DataFrame) -> pd.DataFrame:
    return _panel_attribution_history(exposure_panel_df)


def _panel_attribution_history(exposure_panel_df: pd.DataFrame) -> pd.DataFrame:
    if exposure_panel_df.empty:
        return pd.DataFrame()

    attribution_df = exposure_panel_df.copy().sort_values(["category_label", "date"])
    for base_column in ["long_exposure", "short_exposure", "net_exposure", "gross_exposure"]:
        attribution_df[f"{base_column}_change"] = (
            attribution_df.groupby("category_label")[base_column].diff().fillna(0.0)
        )
    return attribution_df


def _asset_class_data_table(exposure_panel_df: pd.DataFrame, source_name: str, field_name: str) -> pd.DataFrame:
    return _panel_data_table(exposure_panel_df, source_name, field_name)


def _panel_data_table(exposure_panel_df: pd.DataFrame, source_name: str, field_name: str) -> pd.DataFrame:
    exposure_field_map = {
        "Net (Long+Short)": "net_exposure",
        "Long": "long_exposure",
        "Short": "short_exposure",
        "Gross (|L|+|S|)": "gross_exposure",
    }
    attribution_field_map = {
        "Net Change": "net_exposure_change",
        "Long Change": "long_exposure_change",
        "Short Change": "short_exposure_change",
        "Gross Change": "gross_exposure_change",
    }

    if source_name == "Exposure":
        value_column = exposure_field_map.get(field_name)
        table_df = exposure_panel_df.copy()
    else:
        value_column = attribution_field_map.get(field_name)
        table_df = _panel_attribution_history(exposure_panel_df)

    if table_df.empty or value_column is None or value_column not in table_df.columns:
        return pd.DataFrame()

    table_df["month"] = table_df["date"].dt.strftime("%Y-%m")
    pivot_df = (
        table_df.pivot_table(
            index="month",
            columns="category_label",
            values=value_column,
            aggfunc="sum",
            fill_value=0.0,
        )
        .sort_index(ascending=False)
    )
    if pivot_df.empty:
        return pivot_df
    pivot_df["Sum"] = pivot_df.sum(axis=1)
    return pivot_df


def _render_synced_month_controls(prefix: str, month_labels: list[str], default_value: str) -> str:
    if not month_labels:
        raise ValueError("Month controls require at least one month label.")
    if default_value not in month_labels:
        raise ValueError(f"Default month '{default_value}' is not available in month labels.")

    state_key = f"{prefix}_month_value"
    slider_key = f"{prefix}_month_slider"
    jump_key = f"{prefix}_month_jump"

    selected_value = st.session_state.get(state_key, default_value)
    if selected_value not in month_labels:
        selected_value = default_value

    for key in (state_key, slider_key, jump_key):
        if st.session_state.get(key) not in month_labels:
            st.session_state[key] = selected_value

    def _sync_from_slider():
        st.session_state[state_key] = st.session_state[slider_key]
        st.session_state[jump_key] = st.session_state[slider_key]

    def _sync_from_jump():
        st.session_state[state_key] = st.session_state[jump_key]
        st.session_state[slider_key] = st.session_state[jump_key]

    month_control_cols = st.columns([3, 1])
    with month_control_cols[0]:
        st.select_slider(
            "Month",
            options=month_labels,
            key=slider_key,
            on_change=_sync_from_slider,
        )
    with month_control_cols[1]:
        st.selectbox(
            "Jump to",
            month_labels,
            key=jump_key,
            on_change=_sync_from_jump,
        )
    return st.session_state[state_key]


def _build_exposure_trend(
    monthly_by_holding_df: pd.DataFrame,
    holdings_df: pd.DataFrame,
    group_column: str,
) -> pd.DataFrame:
    required_monthly = {"date", "holding_id", "value_usd_m"}
    required_holdings = {"holding_id", group_column}
    if monthly_by_holding_df.empty or not required_monthly.issubset(monthly_by_holding_df.columns):
        return pd.DataFrame()
    if holdings_df.empty or not required_holdings.issubset(holdings_df.columns):
        return pd.DataFrame()

    trend_df = monthly_by_holding_df.merge(
        holdings_df[["holding_id", group_column]].drop_duplicates(),
        on="holding_id",
        how="left",
    )
    trend_df = trend_df.dropna(subset=[group_column]).copy()
    trend_df["date"] = pd.to_datetime(trend_df["date"], errors="coerce")
    trend_df["value_usd_m"] = pd.to_numeric(trend_df["value_usd_m"], errors="coerce")
    trend_df = trend_df.dropna(subset=["date", "value_usd_m"])
    if trend_df.empty:
        return pd.DataFrame()
    return (
        trend_df.groupby(["date", group_column], as_index=False)["value_usd_m"]
        .sum()
        .sort_values(["date", "value_usd_m"], ascending=[True, False])
    )


def _exposure_trend_chart(trend_df: pd.DataFrame, category_column: str, title: str):
    required = {"date", category_column, "value_usd_m"}
    if trend_df.empty or not required.issubset(trend_df.columns):
        return f"{title} is unavailable."
    latest_top = (
        trend_df.sort_values("date")
        .groupby(category_column)
        .tail(1)
        .sort_values("value_usd_m", ascending=False)
        .head(8)[category_column]
        .tolist()
    )
    chart_df = trend_df[trend_df[category_column].isin(latest_top)]
    return px.line(chart_df, x="date", y="value_usd_m", color=category_column, title=title)


def _public_price_index_chart(public_prices_df: pd.DataFrame):
    required = {"date", "ticker", "close"}
    if public_prices_df.empty or not required.issubset(public_prices_df.columns):
        return "Public market performance history is unavailable."
    chart_df = public_prices_df.copy()
    chart_df["date"] = pd.to_datetime(chart_df["date"], errors="coerce")
    chart_df["close"] = pd.to_numeric(chart_df["close"], errors="coerce")
    chart_df = chart_df.dropna(subset=["date", "ticker", "close"]).sort_values(["ticker", "date"])
    if chart_df.empty:
        return "Public market performance history is unavailable."
    top_tickers = (
        chart_df.groupby("ticker")
        .tail(1)
        .sort_values("close", ascending=False)
        .head(8)["ticker"]
        .tolist()
    )
    chart_df = chart_df[chart_df["ticker"].isin(top_tickers)]
    first_close = chart_df.groupby("ticker")["close"].transform("first")
    chart_df["normalized_index"] = chart_df["close"] / first_close
    return px.line(chart_df, x="date", y="normalized_index", color="ticker", title="Public Market Proxy Performance Index")


def _monthly_public_returns_chart(public_prices_df: pd.DataFrame):
    required = {"date", "ticker", "close"}
    if public_prices_df.empty or not required.issubset(public_prices_df.columns):
        return "Public market monthly return view is unavailable."
    chart_df = public_prices_df.copy()
    chart_df["date"] = pd.to_datetime(chart_df["date"], errors="coerce")
    chart_df["close"] = pd.to_numeric(chart_df["close"], errors="coerce")
    chart_df = chart_df.dropna(subset=["date", "ticker", "close"]).sort_values(["ticker", "date"])
    if chart_df.empty:
        return "Public market monthly return view is unavailable."
    chart_df["monthly_return"] = chart_df.groupby("ticker")["close"].pct_change()
    chart_df = chart_df.dropna(subset=["monthly_return"])
    if chart_df.empty:
        return "Not enough public market history to calculate monthly returns."
    monthly_avg = chart_df.groupby("date", as_index=False)["monthly_return"].mean()
    return px.bar(monthly_avg, x="date", y="monthly_return", title="Average Proxy Monthly Return")


def _format_optional_date(value) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "N/A"
    timestamp = pd.to_datetime(value, errors="coerce")
    if pd.isna(timestamp):
        return "N/A"
    return timestamp.strftime("%Y-%m-%d")


def _metric_from_table(table_df: pd.DataFrame, metric_name: str, column_name: str) -> str:
    if table_df.empty or "Metric" not in table_df.columns or column_name not in table_df.columns:
        return "N/A"
    matches = table_df.loc[table_df["Metric"] == metric_name, column_name]
    if matches.empty:
        return "N/A"
    return str(matches.iloc[0])


def _prepare_public_holdings_review_table(
    public_holdings_df: pd.DataFrame,
    public_prices_df: pd.DataFrame,
    risk_metrics_df: pd.DataFrame,
    proxy_map_df: pd.DataFrame,
) -> pd.DataFrame:
    holdings_table = public_holdings_df.copy()
    if holdings_table.empty:
        return holdings_table

    if not proxy_map_df.empty and {"holding_id", "ticker_or_proxy"}.issubset(proxy_map_df.columns) and "holding_id" in holdings_table.columns:
        holdings_table = holdings_table.merge(
            proxy_map_df[["holding_id", "ticker_or_proxy"]],
            on="holding_id",
            how="left",
        )
        holdings_table["proxy_ticker"] = holdings_table["ticker_or_proxy"].fillna(holdings_table.get("ticker"))
    else:
        holdings_table["proxy_ticker"] = holdings_table.get("ticker")

    if not public_prices_df.empty and {"ticker", "date", "close"}.issubset(public_prices_df.columns):
        price_df = public_prices_df.copy()
        price_df["date"] = pd.to_datetime(price_df["date"], errors="coerce")
        price_df["close"] = pd.to_numeric(price_df["close"], errors="coerce")
        price_df = price_df.dropna(subset=["date", "close"]).sort_values(["ticker", "date"])
        price_df["monthly_return"] = price_df.groupby("ticker")["close"].pct_change()
        latest_price_stats = price_df.groupby("ticker").tail(1)[["ticker", "close", "monthly_return", "date"]]
        latest_price_stats = latest_price_stats.rename(
            columns={
                "ticker": "proxy_ticker",
                "close": "latest_close",
                "date": "latest_price_date",
            }
        )
        holdings_table = holdings_table.merge(latest_price_stats, on="proxy_ticker", how="left")

    if not risk_metrics_df.empty and "proxy_ticker" in holdings_table.columns and "ticker" in risk_metrics_df.columns:
        holdings_table = holdings_table.merge(
            risk_metrics_df[
                [column for column in ["ticker", "annualized_volatility", "max_drawdown"] if column in risk_metrics_df.columns]
            ].rename(columns={"ticker": "proxy_ticker"}),
            on="proxy_ticker",
            how="left",
        )

    exposure_column = "current_delta_adjusted_exposure_usd_m" if "current_delta_adjusted_exposure_usd_m" in holdings_table.columns else "current_exposure_usd_m"
    if exposure_column in holdings_table.columns:
        holdings_table["signed_exposure_usd_m"] = pd.to_numeric(holdings_table[exposure_column], errors="coerce")
        if "position_side_current" in holdings_table.columns:
            short_mask = holdings_table["position_side_current"].astype(str).str.casefold().eq("short")
            holdings_table.loc[short_mask, "signed_exposure_usd_m"] = -holdings_table.loc[short_mask, "signed_exposure_usd_m"].abs()
            holdings_table.loc[~short_mask, "signed_exposure_usd_m"] = holdings_table.loc[~short_mask, "signed_exposure_usd_m"].abs()
        holdings_table["abs_signed_exposure_usd_m"] = holdings_table["signed_exposure_usd_m"].abs()

    return holdings_table


def _build_concentration_table(df: pd.DataFrame, category_column: str, label: str) -> pd.DataFrame:
    if df.empty or category_column not in df.columns:
        return pd.DataFrame()

    exposure_column = "current_delta_adjusted_exposure_usd_m" if "current_delta_adjusted_exposure_usd_m" in df.columns else "current_exposure_usd_m"
    if exposure_column not in df.columns:
        exposure_column = "final_value_usd_m" if "final_value_usd_m" in df.columns else None
    if exposure_column is None:
        return pd.DataFrame()

    working_df = df.copy()
    working_df[exposure_column] = pd.to_numeric(working_df[exposure_column], errors="coerce")
    if "position_side_current" in working_df.columns:
        short_mask = working_df["position_side_current"].astype(str).str.casefold().eq("short")
        working_df.loc[short_mask, exposure_column] = -working_df.loc[short_mask, exposure_column].abs()
        working_df.loc[~short_mask, exposure_column] = working_df.loc[~short_mask, exposure_column].abs()
    working_df = working_df.dropna(subset=[category_column, exposure_column]).copy()
    if working_df.empty:
        return pd.DataFrame()

    grouped = (
        working_df.groupby(category_column, as_index=False)[exposure_column]
        .sum()
        .rename(columns={category_column: label, exposure_column: "Signed Exposure (USD m)"})
    )
    grouped["Abs Exposure"] = grouped["Signed Exposure (USD m)"].abs()
    grouped = grouped.sort_values("Abs Exposure", ascending=False).head(10).drop(columns=["Abs Exposure"])
    return grouped


def _build_value_share_table(df: pd.DataFrame, category_column: str, value_column: str, label: str) -> pd.DataFrame:
    if df.empty or category_column not in df.columns or value_column not in df.columns:
        return pd.DataFrame()
    working_df = df.copy()
    working_df[value_column] = pd.to_numeric(working_df[value_column], errors="coerce")
    working_df = working_df.dropna(subset=[category_column, value_column])
    if working_df.empty:
        return pd.DataFrame()
    grouped = (
        working_df.groupby(category_column, as_index=False)[value_column]
        .sum()
        .rename(columns={category_column: label, value_column: "Value (USD m)"})
        .sort_values("Value (USD m)", ascending=False)
    )
    total_value = float(grouped["Value (USD m)"].sum())
    grouped["Portfolio Share"] = grouped["Value (USD m)"] / total_value if total_value else None
    return grouped


def _render_public_classification_panel(
    public_holdings_df: pd.DataFrame,
    public_exposure_history_df: pd.DataFrame,
    *,
    holdings_category_column: str,
    history_category_column: str,
    label: str,
    prefix: str,
) -> None:
    panel_df = _prepare_dimension_exposure_panel(public_exposure_history_df, history_category_column)
    month_labels = _panel_month_labels(panel_df)
    latest_month_label = month_labels[-1] if month_labels else None
    latest_snapshot_df = _panel_month_snapshot(panel_df, latest_month_label) if latest_month_label else pd.DataFrame()
    latest_metrics = _panel_snapshot_metrics(latest_snapshot_df)

    signed_table_df = _build_concentration_table(public_holdings_df, holdings_category_column, label)
    value_table_df = _build_value_share_table(public_holdings_df, holdings_category_column, "final_value_usd_m", label)
    category_options = (
        latest_snapshot_df.sort_values("gross_exposure", ascending=False)["category_label"].astype(str).tolist()
        if not latest_snapshot_df.empty
        else sorted(
            public_holdings_df[holdings_category_column].dropna().astype(str).unique().tolist()
            if holdings_category_column in public_holdings_df.columns
            else []
        )
    )

    largest_signed_category = None
    largest_signed_value = None
    if not signed_table_df.empty:
        largest_signed_category = signed_table_df.iloc[0][label]
        largest_signed_value = signed_table_df.iloc[0]["Signed Exposure (USD m)"]

    largest_value_category = None
    largest_value = None
    if not value_table_df.empty:
        largest_value_category = value_table_df.iloc[0][label]
        largest_value = value_table_df.iloc[0]["Value (USD m)"]

    non_classifiable_share = None
    if not value_table_df.empty:
        category_series = value_table_df[label].astype(str).str.casefold()
        category_mask = category_series.isin({"non-classifiable", "unknown"})
        if category_mask.any():
            non_classifiable_share = float(value_table_df.loc[category_mask, "Portfolio Share"].sum())

    trend_tab, month_tab, category_tab, table_tab = st.tabs(["Trend", "By Month", "By Category", "Data Table"])

    with trend_tab:
        st.caption(
            f"{label} exposure view across public markets. All / Long / Short switching is based on signed exposure history, while current tables below use current holdings."
        )
        metric_cols = st.columns(4)
        with metric_cols[0]:
            metric_card("Gross Exposure", format_percentage(latest_metrics["gross_exposure"]))
        with metric_cols[1]:
            metric_card("Net Exposure", format_percentage(latest_metrics["net_exposure"]))
        with metric_cols[2]:
            metric_card(
                "Largest Long",
                format_percentage(latest_metrics["largest_long_value"]),
                help_text=latest_metrics["largest_long_category"],
            )
        with metric_cols[3]:
            metric_card(
                "Largest Short",
                format_percentage(latest_metrics["largest_short_value"]),
                help_text=latest_metrics["largest_short_category"],
            )

        secondary_metric_cols = st.columns(4)
        with secondary_metric_cols[0]:
            metric_card(
                f"Largest {label} by Signed Exposure",
                largest_signed_category or "N/A",
                help_text=format_usd_millions(largest_signed_value) if largest_signed_value is not None else None,
            )
        with secondary_metric_cols[1]:
            metric_card(
                f"Largest {label} by Value",
                largest_value_category or "N/A",
                help_text=format_usd_millions(largest_value) if largest_value is not None else None,
            )
        with secondary_metric_cols[2]:
            metric_card(f"{label} Categories", f"{len(category_options):,}")
        with secondary_metric_cols[3]:
            metric_card("Non-classifiable Share", format_percentage(non_classifiable_share))

        if not panel_df.empty:
            section_header(
                f"{label} · Exposure",
                f"Exposure percent of NAV by {label.lower()}. The legend stays fixed while the chart view switches between all, long-only, and short-only exposure.",
            )
            _render_chart(
                dimension_exposure_filter_chart(
                    public_exposure_history_df,
                    history_category_column,
                    f"{label} Exposure Trend (% NAV)",
                )
            )
            if not latest_snapshot_df.empty:
                latest_display_df = latest_snapshot_df[
                    ["category_label", "long_exposure", "short_exposure", "net_exposure", "gross_exposure"]
                ].rename(
                    columns={
                        "category_label": label,
                        "long_exposure": "Long",
                        "short_exposure": "Short",
                        "net_exposure": "Net",
                        "gross_exposure": "Gross",
                    }
                ).sort_values("Gross", ascending=False)
                latest_display_df = format_display_dataframe(
                    latest_display_df,
                    pct_columns=["Long", "Short", "Net", "Gross"],
                )
                section_header(
                    f"Latest {label} Summary",
                    f"Latest available month: {latest_month_label}. Gross keeps absolute long plus short exposure; net keeps signed exposure.",
                )
                dataframe_with_empty_state(latest_display_df, f"Latest {label.lower()} summary is unavailable.")
        else:
            empty_state(f"{label} exposure history is unavailable.")

        section_header(f"Current {label} Signed Exposure", "Current signed exposure is based on holdings-level delta-adjusted exposure where available.")
        _render_chart(classified_signed_exposure_chart(public_holdings_df, holdings_category_column, f"Current {label} Exposure"))
        display_signed_table_df = format_display_dataframe(
            signed_table_df,
            money_columns=["Signed Exposure (USD m)"],
        )
        dataframe_with_empty_state(display_signed_table_df, f"{label} signed exposure table is unavailable.")

        section_header(f"Current {label} by Value", "Current market value concentration is shown separately from signed exposure so cash and non-classifiable buckets remain explicit.")
        display_value_table_df = format_display_dataframe(
            value_table_df,
            money_columns=["Value (USD m)"],
            pct_columns=["Portfolio Share"],
        )
        dataframe_with_empty_state(display_value_table_df, f"{label} value snapshot is unavailable.")

    with month_tab:
        st.caption(f"Single-month {label.lower()} snapshot. The attribution view below is month-on-month exposure change, not return contribution.")
        if month_labels:
            selected_month_label = _render_synced_month_controls(prefix, month_labels, latest_month_label)
            snapshot_df = _panel_month_snapshot(panel_df, selected_month_label)
            change_snapshot_df = _panel_month_change_snapshot(panel_df, selected_month_label)
            snapshot_metrics = _panel_snapshot_metrics(snapshot_df)

            metric_cols = st.columns(4)
            with metric_cols[0]:
                metric_card("Gross Exposure", format_percentage(snapshot_metrics["gross_exposure"]))
            with metric_cols[1]:
                metric_card("Net Exposure", format_percentage(snapshot_metrics["net_exposure"]))
            with metric_cols[2]:
                metric_card(
                    "Largest Long",
                    format_percentage(snapshot_metrics["largest_long_value"]),
                    help_text=snapshot_metrics["largest_long_category"],
                )
            with metric_cols[3]:
                metric_card(
                    "Largest Short",
                    format_percentage(snapshot_metrics["largest_short_value"]),
                    help_text=snapshot_metrics["largest_short_category"],
                )

            section_header(
                "Exposure Snapshot",
                f"Exposure percent of NAV for {selected_month_label}, with long exposure on the right and short exposure on the left.",
            )
            _render_chart(asset_class_snapshot_bars(snapshot_df, "long_short", f"{label} Exposure Snapshot - {selected_month_label}"))

            section_header(
                "Attribution Snapshot",
                f"Month-on-month change in {label.lower()} exposure. This is a positioning-change view, not a return-contribution view.",
            )
            if change_snapshot_df.empty:
                empty_state(f"A prior month is required before month-on-month {label.lower()} exposure changes can be shown.")
            else:
                _render_chart(
                    asset_class_snapshot_change_bars(
                        change_snapshot_df,
                        f"Month-on-Month {label} Exposure Change - {selected_month_label}",
                    )
                )

            snapshot_table_df = snapshot_df[
                ["category_label", "long_exposure", "short_exposure", "net_exposure", "gross_exposure"]
            ].rename(
                columns={
                    "category_label": label,
                    "long_exposure": "Long",
                    "short_exposure": "Short",
                    "net_exposure": "Net",
                    "gross_exposure": "Gross",
                }
            ).sort_values("Gross", ascending=False)
            snapshot_table_df = format_display_dataframe(
                snapshot_table_df,
                pct_columns=["Long", "Short", "Net", "Gross"],
            )
            section_header("Snapshot Table", f"Table version of the selected month {label.lower()} snapshot.")
            dataframe_with_empty_state(snapshot_table_df, f"{label} monthly snapshot is unavailable.")
        else:
            empty_state(f"Monthly {label.lower()} exposure breakdown is unavailable.")

    with category_tab:
        st.caption(f"Five-year evolution of one selected {label.lower()} bucket, with long, short, and net exposure shown together.")
        if category_options:
            selected_category = st.selectbox("Category", category_options, index=0, key=f"{prefix}_category_selector")
            category_history_df = panel_df[panel_df["category_label"] == selected_category].copy().sort_values("date")
            category_change_df = _panel_category_change_history(panel_df, selected_category)
            latest_category_slice = category_history_df.sort_values("date").tail(1)
            latest_category_date = latest_category_slice["date"].iloc[0].strftime("%Y-%m") if not latest_category_slice.empty else None

            category_metric_cols = st.columns(4)
            with category_metric_cols[0]:
                metric_card("Latest Long", format_percentage(float(latest_category_slice["long_exposure"].iloc[0])) if not latest_category_slice.empty else "N/A")
            with category_metric_cols[1]:
                metric_card("Latest Short", format_percentage(float(latest_category_slice["short_exposure"].iloc[0])) if not latest_category_slice.empty else "N/A")
            with category_metric_cols[2]:
                metric_card("Latest Net", format_percentage(float(latest_category_slice["net_exposure"].iloc[0])) if not latest_category_slice.empty else "N/A")
            with category_metric_cols[3]:
                metric_card(
                    "Latest Gross",
                    format_percentage(float(latest_category_slice["gross_exposure"].iloc[0])) if not latest_category_slice.empty else "N/A",
                    help_text=latest_category_date,
                )

            section_header(
                "Exposure Evolution",
                "Long is shown as the positive sleeve, short remains below zero, and net shows the combined exposure.",
            )
            _render_chart(
                asset_class_category_evolution_chart(
                    category_history_df,
                    f"{selected_category} {label} Exposure Evolution",
                )
            )

            section_header(
                "Attribution by Month",
                f"Month-on-month change in long and short exposure for the selected {label.lower()} bucket.",
            )
            _render_chart(
                asset_class_monthly_change_chart(
                    category_change_df,
                    f"{selected_category} {label} Monthly Exposure Change",
                )
            )

            category_table_df = category_history_df[
                ["date", "long_exposure", "short_exposure", "net_exposure", "gross_exposure"]
            ].copy()
            category_table_df["date"] = category_table_df["date"].dt.strftime("%Y-%m")
            category_table_df = category_table_df.rename(
                columns={
                    "date": "Month",
                    "long_exposure": "Long",
                    "short_exposure": "Short",
                    "net_exposure": "Net",
                    "gross_exposure": "Gross",
                }
            ).sort_values("Month", ascending=False)
            category_table_df = format_display_dataframe(
                category_table_df,
                pct_columns=["Long", "Short", "Net", "Gross"],
            )
            section_header("Category Table", f"Monthly history for {selected_category}.")
            dataframe_with_empty_state(category_table_df, f"{label} category history is unavailable.")
        else:
            empty_state(f"{label} category history is unavailable.")

    with table_tab:
        st.caption(f"Monthly {label.lower()} exposure table across all categories, with an optional attribution view based on month-on-month exposure change.")
        source_col, field_col = st.columns([1, 2])
        with source_col:
            selected_source = st.selectbox("Source", ["Exposure", "Attribution"], index=0, key=f"{prefix}_table_source")
        with field_col:
            field_options = (
                ["Net (Long+Short)", "Long", "Short", "Gross (|L|+|S|)"]
                if selected_source == "Exposure"
                else ["Net Change", "Long Change", "Short Change", "Gross Change"]
            )
            selected_field = st.selectbox("Field", field_options, index=0, key=f"{prefix}_table_field")
        if selected_source == "Attribution":
            st.caption(f"Attribution here is implemented as month-on-month exposure change by {label.lower()}. It is not return contribution attribution.")
        table_df = _panel_data_table(panel_df, selected_source, selected_field)
        if table_df.empty:
            empty_state(f"{label} data table is unavailable.")
        else:
            display_table_df = table_df.copy().reset_index().rename(columns={"month": "Month"})
            for column in display_table_df.columns:
                if column != "Month":
                    display_table_df[column] = display_table_df[column].map(lambda value: f"{value:+.2%}")
            st.dataframe(display_table_df, use_container_width=True, height=520, hide_index=True)

        section_header("Current Signed Exposure Table", "Current signed exposure by category.")
        display_signed_table_df = format_display_dataframe(
            signed_table_df,
            money_columns=["Signed Exposure (USD m)"],
        )
        dataframe_with_empty_state(display_signed_table_df, f"{label} signed exposure table is unavailable.")

        section_header("Current Value Share Table", "Current market value concentration by category.")
        display_value_table_df = format_display_dataframe(
            value_table_df,
            money_columns=["Value (USD m)"],
            pct_columns=["Portfolio Share"],
        )
        dataframe_with_empty_state(display_value_table_df, f"{label} value share table is unavailable.")


def _capital_calls_this_month(capital_call_df: pd.DataFrame) -> float:
    if capital_call_df.empty or not {"due_date", "amount_due_usd_m"}.issubset(capital_call_df.columns):
        return 0.0
    working_df = capital_call_df.copy()
    working_df["due_date"] = pd.to_datetime(working_df["due_date"], errors="coerce")
    working_df = working_df.dropna(subset=["due_date"])
    if working_df.empty:
        return 0.0
    latest_period = working_df["due_date"].max().to_period("M")
    return safe_sum(working_df[working_df["due_date"].dt.to_period("M") == latest_period], ["amount_due_usd_m"])


def render_overview_page():
    overview_data = load_overview_datasets()
    monthly_summary_df = overview_data["monthly_summary"]
    monthly_by_holding_df = overview_data["monthly_by_holding"]
    positions_df = overview_data["private_positions"]
    cash_df = overview_data["cash_accounts"]
    document_status_df = overview_data["document_status"]
    ingestion_inbox_df = load_ingestion_inbox_status()
    allocation_df = overview_data["allocation"]
    risk_free_df = overview_data["risk_free"]

    _render_page_header(
        "Family Office Portfolio Overview",
        "Synthetic multi-asset portfolio monitoring with AI-assisted private-market document updates.",
    )
    synthetic_data_notice()
    _render_demo_state_status_bar()
    st.info(
        "This page mixes the official baseline portfolio state with approved PDF overlay updates. Public-market timing remains constrained by the external market refresh boundary."
    )

    summary_tab = st.tabs(["Summary"])[0]
    with summary_tab:
        metrics = calculate_portfolio_summary_metrics(monthly_summary_df, positions_df, cash_df, document_status_df)
        performance_table = calculate_performance_statistics_table(monthly_summary_df, risk_free_df=risk_free_df)
        baseline_month_end = load_official_baseline_month_end()
        baseline_date = _format_optional_date(baseline_month_end)
        baseline_total_aum = None
        if baseline_month_end is not None and not monthly_summary_df.empty and {"date", "total_aum_usd_m"}.issubset(monthly_summary_df.columns):
            baseline_rows = monthly_summary_df.copy()
            baseline_rows["date"] = pd.to_datetime(baseline_rows["date"], errors="coerce")
            baseline_rows = baseline_rows[baseline_rows["date"] == baseline_month_end]
            if not baseline_rows.empty:
                baseline_total_aum = pd.to_numeric(baseline_rows.iloc[-1]["total_aum_usd_m"], errors="coerce")
        public_private_df = pd.DataFrame(
            [
                {"label": "Public Markets", "value": metrics["public_market_value"]},
                {"label": "Private Fund NAV", "value": metrics["private_fund_nav"]},
                {"label": "Cash & Liquidity", "value": metrics["cash_liquidity"]},
            ]
        ).dropna()
        since_inception_stats = performance_table.set_index("Metric")["Since Inception"].to_dict() if not performance_table.empty else {}
        workflow_counts = (
            document_status_df["validation_review_status"].value_counts().to_dict()
            if not document_status_df.empty and "validation_review_status" in document_status_df.columns
            else {}
        )
        staged_uploads = len(ingestion_inbox_df)
        applied_updates = int(document_status_df["update_applied_flag"].fillna(False).sum()) if not document_status_df.empty and "update_applied_flag" in document_status_df.columns else 0
        workflow_summary = (
            f"{len(document_status_df)} processed | "
            f"{workflow_counts.get('approved', 0)} approved | "
            f"{workflow_counts.get('needs_review', 0)} needs review | "
            f"{workflow_counts.get('rejected', 0)} rejected | "
            f"{applied_updates} applied"
        )
        boundary_df = pd.DataFrame(
            [
                {
                    "State Layer": "Official Baseline",
                    "As Of": baseline_date,
                    "Scope": "Full monthly portfolio state",
                    "Indicator": format_usd_millions(baseline_total_aum),
                },
                {
                    "State Layer": "Approved Overlay",
                    "As Of": _format_optional_date(load_latest_overlay_month_end()),
                    "Scope": "Approved private-market workflow updates",
                    "Indicator": f"{applied_updates} applied | {workflow_counts.get('needs_review', 0)} needs review",
                },
                {
                    "State Layer": "Staged Upload Inbox",
                    "As Of": "Current app session",
                    "Scope": "Uploaded PDFs awaiting extraction and review",
                    "Indicator": f"{staged_uploads} staged | 0 portfolio impact before approval",
                },
            ]
        )

        section_header(
            "Portfolio State Boundary",
            "Use this section to distinguish the locked official baseline, the approved overlay month, and the staged inbox state.",
        )
        boundary_cols = st.columns(2)
        with boundary_cols[0]:
            metric_card("Official Baseline Date", baseline_date, _SOURCE_HELP["official_baseline"])
            metric_card("Baseline Total AUM", format_usd_millions(baseline_total_aum), _SOURCE_HELP["official_baseline"])
        with boundary_cols[1]:
            metric_card("Approved Overlay Updates", f"{applied_updates:,}")
            metric_card("Staged Uploads", f"{staged_uploads:,}")
        tertiary_cols = st.columns(2)
        with tertiary_cols[0]:
            metric_card("Pending / Rejected Docs", f"{workflow_counts.get('needs_review', 0) + workflow_counts.get('rejected', 0):,}")
        with tertiary_cols[1]:
            metric_card("Review Gate", "Approved only")
        dataframe_with_empty_state(boundary_df, "Portfolio state boundary summary is unavailable.")

        metric_cols = st.columns(4)
        with metric_cols[0]:
            metric_card("Total AUM", format_usd_millions(metrics["total_aum"]), _SOURCE_HELP["portfolio_overlay"])
            metric_with_delta("Latest Monthly Return", format_percentage(metrics["latest_return"]), help_text=_SOURCE_HELP["portfolio_overlay"])
        with metric_cols[1]:
            metric_with_delta("Annualized Return", since_inception_stats.get("Annualized Return", "N/A"), help_text=_SOURCE_HELP["portfolio_overlay"])
            metric_card("Cash & Liquidity", format_usd_millions(metrics["cash_liquidity"]), _SOURCE_HELP["portfolio_overlay"])
        with metric_cols[2]:
            metric_with_delta("Annualized Volatility", since_inception_stats.get("Annualized Volatility", "N/A"), help_text=_SOURCE_HELP["portfolio_overlay"])
            metric_card("Unfunded Commitments", format_usd_millions(metrics["unfunded_commitments"]), _SOURCE_HELP["portfolio_overlay"])
        with metric_cols[3]:
            metric_with_delta("Max Drawdown", since_inception_stats.get("Largest Drawdown", "N/A"), help_text=_SOURCE_HELP["portfolio_overlay"])
            metric_card("Liquidity Coverage", format_percentage(metrics["liquidity_coverage"]), _SOURCE_HELP["portfolio_overlay"])
        secondary_cols = st.columns(2)
        with secondary_cols[0]:
            metric_card("Sharpe Ratio", since_inception_stats.get("Sharpe Ratio", "N/A"), "Uses the processed portfolio monthly summary plus the Treasury-bill proxy when available.")
        with secondary_cols[1]:
            metric_card("Workflow Snapshot", workflow_summary)

        section_header("Performance Statistics", "Full-portfolio statistics derived from synthetic monthly AUM history. Sharpe uses the synthetic Treasury bill proxy when available.")
        dataframe_with_empty_state(performance_table, "Performance statistics are unavailable.")

        section_header("Portfolio Performance Trend", "Monthly return bars with cumulative return line from the full portfolio monthly summary.")
        _render_chart(portfolio_return_bars_cumulative_line_chart(monthly_summary_df))

        section_header("Allocation Summary")
        dataframe_with_empty_state(allocation_df, "Asset allocation data is unavailable.")
        _render_chart(asset_allocation_chart(allocation_df))

        section_header("Asset Class Allocation Over Time", "Composition trend aggregated from monthly holding history.")
        if not monthly_by_holding_df.empty and {"date", "asset_class", "value_usd_m"}.issubset(monthly_by_holding_df.columns):
            allocation_trend_df = monthly_by_holding_df.groupby(["date", "asset_class"], as_index=False)["value_usd_m"].sum()
            _render_chart(asset_class_allocation_over_time_chart(allocation_trend_df))
        else:
            empty_state("Asset class allocation history is unavailable.")

        section_header("Public vs Private vs Cash")
        _render_chart(public_private_split_chart(public_private_df))

        section_header("Workflow Snapshot", "Compact status only. Detailed execution and review remain in Workflow & Controls.")
        st.caption(f"May document update: {workflow_summary}")
        workflow_status_card(document_status_df)


def render_asset_class_page():
    allocation_df = load_asset_allocation_table()
    monthly_by_holding_df = load_portfolio_monthly_by_holding()
    exposure_history_df = load_position_exposure_history()
    exposure_panel_df = _prepare_asset_class_exposure_history(exposure_history_df)
    asset_metrics = calculate_asset_class_metrics(allocation_df, monthly_by_holding_df)
    month_labels = _asset_class_month_labels(exposure_panel_df)
    latest_month_label = month_labels[-1] if month_labels else None
    latest_snapshot_df = _asset_class_month_snapshot(exposure_panel_df, latest_month_label) if latest_month_label else pd.DataFrame()
    category_options = (
        latest_snapshot_df.sort_values("gross_exposure", ascending=False)["category_label"].tolist()
        if not latest_snapshot_df.empty
        else exposure_panel_df["category_label"].drop_duplicates().sort_values().tolist()
    )

    _render_page_header(
        "Asset Class Allocation & Performance",
        "This page monitors asset-class exposure, showing how long and short risk is distributed across the portfolio and how it changes through time. "
        "Views are exposure-based and use the synthetic holdings history plus approved workflow updates.",
    )
    trend_tab, month_tab, category_tab, table_tab = st.tabs(["Trend", "By Month", "By Category", "Data Table"])

    with trend_tab:
        st.caption("Exposure view across all asset classes. Use the built-in All / Long / Short control to isolate net, long-only, or short-only positioning.")
        trend_metrics = _asset_class_snapshot_metrics(latest_snapshot_df)
        metric_cols = st.columns(4)
        with metric_cols[0]:
            metric_card("Gross Exposure", format_percentage(trend_metrics["gross_exposure"]))
        with metric_cols[1]:
            metric_card("Net Exposure", format_percentage(trend_metrics["net_exposure"]))
        with metric_cols[2]:
            metric_card(
                "Largest Long",
                format_percentage(trend_metrics["largest_long_value"]),
                help_text=trend_metrics["largest_long_category"],
            )
        with metric_cols[3]:
            metric_card(
                "Largest Short",
                format_percentage(trend_metrics["largest_short_value"]),
                help_text=trend_metrics["largest_short_category"],
            )
        secondary_metric_cols = st.columns(3)
        with secondary_metric_cols[0]:
            metric_card("Total Value Tracked", format_usd_millions(asset_metrics["total_value"]), "Latest holdings market value aggregated across asset classes.")
        with secondary_metric_cols[1]:
            metric_card(
                "Largest Asset Class",
                asset_metrics["largest_asset_class"] or "N/A",
                help_text=format_usd_millions(asset_metrics["largest_asset_class_value"]),
            )
        with secondary_metric_cols[2]:
            metric_card("Liquid Assets by Value", format_usd_millions(asset_metrics["liquid_value"]), "Current market value classified as liquid rather than closed-end private capital.")
        if not exposure_history_df.empty:
            section_header(
                "Asset Class · Exposure",
                "Exposure percent of NAV by asset class. The legend stays fixed while the chart view switches between all, long-only, and short-only exposure.",
            )
            _render_chart(asset_class_exposure_filter_chart(exposure_history_df))
            if not latest_snapshot_df.empty:
                st.caption("Long, short, net, and gross are shown using the latest available month of exposure history.")
                latest_display_df = (
                    latest_snapshot_df[
                        ["category_label", "long_exposure", "short_exposure", "net_exposure", "gross_exposure"]
                    ]
                    .rename(
                        columns={
                            "category_label": "Asset Class",
                            "long_exposure": "Long",
                            "short_exposure": "Short",
                            "net_exposure": "Net",
                            "gross_exposure": "Gross",
                        }
                    )
                    .sort_values("Gross", ascending=False)
                )
                for column in ["Long", "Short", "Net", "Gross"]:
                    latest_display_df[column] = latest_display_df[column].map(lambda value: f"{value:+.2%}")
                section_header(
                    "Latest Exposure Summary",
                    f"Latest available month: {latest_month_label}. Gross keeps absolute long plus short exposure; net keeps signed exposure.",
                )
                st.dataframe(latest_display_df, use_container_width=True, hide_index=True)
        else:
            empty_state("Asset class exposure history is unavailable.")

    with month_tab:
        st.caption("Single-month snapshot view. This is exposure-based, not return attribution.")
        if month_labels:
            selected_month_label = _render_synced_month_controls(
                "asset_class",
                month_labels,
                latest_month_label,
            )
            snapshot_df = _asset_class_month_snapshot(exposure_panel_df, selected_month_label)
            change_snapshot_df = _asset_class_month_change_snapshot(exposure_panel_df, selected_month_label)
            snapshot_metrics = _asset_class_snapshot_metrics(snapshot_df)

            metric_cols = st.columns(4)
            with metric_cols[0]:
                metric_card("Gross Exposure", format_percentage(snapshot_metrics["gross_exposure"]))
            with metric_cols[1]:
                metric_card("Net Exposure", format_percentage(snapshot_metrics["net_exposure"]))
            with metric_cols[2]:
                metric_card(
                    "Largest Long",
                    format_percentage(snapshot_metrics["largest_long_value"]),
                    help_text=snapshot_metrics["largest_long_category"],
                )
            with metric_cols[3]:
                metric_card(
                    "Largest Short",
                    format_percentage(snapshot_metrics["largest_short_value"]),
                    help_text=snapshot_metrics["largest_short_category"],
                )

            section_header(
                "Exposure Snapshot",
                f"Exposure percent of NAV for {selected_month_label}, with long exposure on the right and short exposure on the left.",
            )
            _render_chart(asset_class_snapshot_bars(snapshot_df, "long_short", f"Asset Class Exposure Snapshot - {selected_month_label}"))

            section_header(
                "Exposure Change Snapshot",
                "Month-on-month change in exposure by asset class. This is a positioning change view, not a performance attribution view.",
            )
            if change_snapshot_df.empty:
                empty_state("A prior month is required before month-on-month exposure changes can be shown.")
            else:
                _render_chart(
                    asset_class_snapshot_change_bars(
                        change_snapshot_df,
                        f"Month-on-Month Exposure Change - {selected_month_label}",
                    )
                )
            snapshot_table_df = snapshot_df[
                ["category_label", "long_exposure", "short_exposure", "net_exposure", "gross_exposure"]
            ].rename(
                columns={
                    "category_label": "Asset Class",
                    "long_exposure": "Long",
                    "short_exposure": "Short",
                    "net_exposure": "Net",
                    "gross_exposure": "Gross",
                }
            )
            snapshot_table_df = snapshot_table_df.sort_values("Gross", ascending=False)
            for column in ["Long", "Short", "Net", "Gross"]:
                snapshot_table_df[column] = snapshot_table_df[column].map(lambda value: f"{value:+.2%}")
            section_header("Snapshot Table", "Table version of the selected month exposure snapshot.")
            st.dataframe(snapshot_table_df, use_container_width=True, hide_index=True)
        else:
            empty_state("Monthly asset class exposure breakdown is unavailable.")

    with category_tab:
        st.caption("Five-year evolution of a single asset class, with long, short, and net exposure shown together.")
        if category_options:
            selected_category = st.selectbox("Category", category_options, index=0, key="asset_class_category_selector")
            category_history_df = exposure_panel_df[exposure_panel_df["category_label"] == selected_category].copy().sort_values("date")
            category_change_df = _asset_class_category_change_history(exposure_panel_df, selected_category)
            latest_category_snapshot = category_history_df.sort_values("date").tail(1)
            latest_category_date = (
                latest_category_snapshot["date"].iloc[0].strftime("%Y-%m")
                if not latest_category_snapshot.empty
                else None
            )

            category_metric_cols = st.columns(4)
            with category_metric_cols[0]:
                metric_card(
                    "Latest Long",
                    format_percentage(float(latest_category_snapshot["long_exposure"].iloc[0])) if not latest_category_snapshot.empty else "N/A",
                )
            with category_metric_cols[1]:
                metric_card(
                    "Latest Short",
                    format_percentage(float(latest_category_snapshot["short_exposure"].iloc[0])) if not latest_category_snapshot.empty else "N/A",
                )
            with category_metric_cols[2]:
                metric_card(
                    "Latest Net",
                    format_percentage(float(latest_category_snapshot["net_exposure"].iloc[0])) if not latest_category_snapshot.empty else "N/A",
                )
            with category_metric_cols[3]:
                metric_card(
                    "Latest Gross",
                    format_percentage(float(latest_category_snapshot["gross_exposure"].iloc[0])) if not latest_category_snapshot.empty else "N/A",
                    help_text=latest_category_date,
                )

            section_header(
                "Exposure Evolution",
                "Long is shown as the positive sleeve, short remains below zero, and net shows the combined exposure.",
            )
            _render_chart(
                asset_class_category_evolution_chart(
                    category_history_df,
                    f"{selected_category} Exposure Evolution",
                )
            )

            section_header(
                "Monthly Exposure Change",
                "Month-on-month change in long and short exposure for the selected asset class.",
            )
            _render_chart(
                asset_class_monthly_change_chart(
                    category_change_df,
                    f"{selected_category} Monthly Exposure Change",
                )
            )
            category_table_df = category_history_df[
                ["date", "long_exposure", "short_exposure", "net_exposure", "gross_exposure"]
            ].copy()
            category_table_df["date"] = category_table_df["date"].dt.strftime("%Y-%m")
            category_table_df = category_table_df.rename(
                columns={
                    "date": "Month",
                    "long_exposure": "Long",
                    "short_exposure": "Short",
                    "net_exposure": "Net",
                    "gross_exposure": "Gross",
                }
            ).sort_values("Month", ascending=False)
            for column in ["Long", "Short", "Net", "Gross"]:
                category_table_df[column] = category_table_df[column].map(lambda value: f"{value:+.2%}")
            section_header("Category Table", f"Monthly history for {selected_category}.")
            st.dataframe(category_table_df, use_container_width=True, hide_index=True)
        else:
            empty_state("Asset class category history is unavailable.")

    with table_tab:
        st.caption("Monthly exposure table across all asset classes. Choose which exposure field to inspect.")
        source_col, field_col = st.columns([1, 2])
        with source_col:
            selected_source = st.selectbox("Source", ["Exposure", "Attribution"], index=0, key="asset_class_table_source")
        with field_col:
            field_options = (
                ["Net (Long+Short)", "Long", "Short", "Gross (|L|+|S|)"]
                if selected_source == "Exposure"
                else ["Net Change", "Long Change", "Short Change", "Gross Change"]
            )
            selected_field = st.selectbox("Field", field_options, index=0, key="asset_class_table_field")
        if selected_source == "Attribution":
            st.caption("Attribution here is implemented as month-on-month exposure change by asset class. It is not return contribution attribution.")
        table_df = _asset_class_data_table(exposure_panel_df, selected_source, selected_field)
        if table_df.empty:
            empty_state("Asset class data table is unavailable.")
        else:
            display_table_df = table_df.copy().reset_index().rename(columns={"month": "Month"})
            for column in display_table_df.columns:
                if column != "Month":
                    display_table_df[column] = display_table_df[column].map(lambda value: f"{value:+.2%}")
            st.dataframe(display_table_df, use_container_width=True, height=520, hide_index=True)


def render_region_currency_page():
    holdings_df = load_portfolio_holdings()
    geography_df = load_geography_exposure_if_available()
    currency_df = load_currency_exposure_if_available()
    region_reference_df = load_region_taxonomy_reference()
    exposure_history_df = load_position_exposure_history()
    region_panel_df = _prepare_dimension_exposure_panel(exposure_history_df, "region_taxonomy_pti")
    region_month_labels = _panel_month_labels(region_panel_df)
    latest_month_label = region_month_labels[-1] if region_month_labels else None
    latest_region_snapshot_df = _panel_month_snapshot(region_panel_df, latest_month_label) if latest_month_label else pd.DataFrame()
    latest_region_metrics = _panel_snapshot_metrics(latest_region_snapshot_df)
    region_value_table_df = _build_value_share_table(geography_df, "region", "final_value_usd_m", "Region")
    currency_value_table_df = _build_value_share_table(currency_df, "currency", "final_value_usd_m", "Currency")
    holdings_region_currency_df = pd.DataFrame()
    if not holdings_df.empty:
        current_holdings_columns = [
            column
            for column in [
                "holding_name",
                "asset_class",
                "region_taxonomy",
                "currency",
                "final_value_usd_m",
                "allocation_pct",
            ]
            if column in holdings_df.columns
        ]
        holdings_region_currency_df = holdings_df[current_holdings_columns].copy() if current_holdings_columns else pd.DataFrame()
        if not holdings_region_currency_df.empty:
            holdings_region_currency_df = holdings_region_currency_df.sort_values("final_value_usd_m", ascending=False)
    region_options = (
        latest_region_snapshot_df.sort_values("gross_exposure", ascending=False)["category_label"].tolist()
        if not latest_region_snapshot_df.empty
        else region_panel_df["category_label"].drop_duplicates().sort_values().tolist()
    )
    top_region = geography_df.iloc[0]["region"] if not geography_df.empty and "region" in geography_df.columns else None
    top_region_value = geography_df.iloc[0]["final_value_usd_m"] if not geography_df.empty and "final_value_usd_m" in geography_df.columns else None
    top_currency = currency_df.iloc[0]["currency"] if not currency_df.empty and "currency" in currency_df.columns else None
    top_currency_value = currency_df.iloc[0]["final_value_usd_m"] if not currency_df.empty and "final_value_usd_m" in currency_df.columns else None
    usd_value = safe_sum(currency_df[currency_df["currency"].astype(str).str.upper() == "USD"], ["final_value_usd_m"]) if not currency_df.empty and "currency" in currency_df.columns else 0.0
    total_currency_value = safe_sum(currency_df, ["final_value_usd_m"])
    non_usd_share = None if total_currency_value == 0 else 1.0 - (usd_value / total_currency_value)

    _render_page_header(
        "Region & Currency Exposure",
        "This page tracks geographic concentration as an exposure problem first, with reporting-currency exposure kept as a supporting current-state view. "
        "Region views are built from exposure history; currency views come from the current synthetic holdings snapshot.",
    )
    st.info("Region taxonomy follows the project dataset: North America, Greater China, Southeast Asia, India, Japan, Korea, and Global / Multi-region.")
    trend_tab, month_tab, category_tab, table_tab = st.tabs(["Trend", "By Month", "By Category", "Data Table"])

    with trend_tab:
        st.caption("Region exposure view across the portfolio. All / Long / Short switching is based on signed exposure history, not market value.")
        metric_cols = st.columns(4)
        with metric_cols[0]:
            metric_card("Gross Exposure", format_percentage(latest_region_metrics["gross_exposure"]), "Absolute long plus absolute short regional exposure as a percent of NAV.")
        with metric_cols[1]:
            metric_card("Net Exposure", format_percentage(latest_region_metrics["net_exposure"]), "Signed regional exposure after offsetting long and short positioning.")
        with metric_cols[2]:
            metric_card(
                "Largest Long",
                format_percentage(latest_region_metrics["largest_long_value"]),
                help_text=latest_region_metrics["largest_long_category"],
            )
        with metric_cols[3]:
            metric_card(
                "Largest Short",
                format_percentage(latest_region_metrics["largest_short_value"]),
                help_text=latest_region_metrics["largest_short_category"],
            )
        secondary_metric_cols = st.columns(4)
        with secondary_metric_cols[0]:
            metric_card("Largest Region by Value", top_region or "N/A", help_text=format_usd_millions(top_region_value) if top_region_value is not None else None)
        with secondary_metric_cols[1]:
            metric_card("Top Reporting Currency", top_currency or "N/A", help_text=format_usd_millions(top_currency_value) if top_currency_value is not None else None)
        with secondary_metric_cols[2]:
            metric_card("Region Categories", f"{len(region_options):,}", "Count of region buckets represented in the current exposure panel.")
        with secondary_metric_cols[3]:
            metric_card("Non-USD Share", format_percentage(non_usd_share), "Current holdings-based share of value reported outside USD.")
        if not exposure_history_df.empty and "region_taxonomy_pti" in exposure_history_df.columns:
            section_header(
                "Region · Exposure",
                "Exposure percent of NAV by region. The legend stays fixed while the chart view switches between all, long-only, and short-only exposure.",
            )
            _render_chart(
                dimension_exposure_filter_chart(
                    exposure_history_df,
                    "region_taxonomy_pti",
                    "Region Exposure Trend (% NAV)",
                )
            )
            if not latest_region_snapshot_df.empty:
                latest_display_df = (
                    latest_region_snapshot_df[
                        ["category_label", "long_exposure", "short_exposure", "net_exposure", "gross_exposure"]
                    ]
                    .rename(
                        columns={
                            "category_label": "Region",
                            "long_exposure": "Long",
                            "short_exposure": "Short",
                            "net_exposure": "Net",
                            "gross_exposure": "Gross",
                        }
                    )
                    .sort_values("Gross", ascending=False)
                )
                for column in ["Long", "Short", "Net", "Gross"]:
                    latest_display_df[column] = latest_display_df[column].map(lambda value: f"{value:+.2%}")
                section_header(
                    "Latest Region Summary",
                    f"Latest available month: {latest_month_label}. Gross keeps absolute long plus short exposure; net keeps signed exposure.",
                )
                st.dataframe(latest_display_df, use_container_width=True, hide_index=True)
        else:
            empty_state("Region exposure history is unavailable.")

        section_header("Region Snapshot by Value", "Current region concentration based on latest holdings market value.")
        display_region_value_table_df = format_display_dataframe(
            region_value_table_df,
            money_columns=["Value (USD m)"],
            pct_columns=["Portfolio Share"],
        )
        dataframe_with_empty_state(display_region_value_table_df, "Region value snapshot is unavailable.")
        _render_chart(region_exposure_chart(geography_df))

        section_header("Currency Snapshot", "Current reporting-currency concentration is value-based because currency history is not yet tracked in the exposure panel.")
        display_currency_value_table_df = format_display_dataframe(
            currency_value_table_df,
            money_columns=["Value (USD m)"],
            pct_columns=["Portfolio Share"],
        )
        dataframe_with_empty_state(display_currency_value_table_df, "Currency exposure data is unavailable.")
        _render_chart(currency_exposure_chart(currency_df))
        _render_chart(usd_vs_non_usd_chart(currency_df))

    with month_tab:
        st.caption("Single-month region snapshot. The attribution view below is month-on-month exposure change, not return contribution.")
        if region_month_labels:
            selected_month_label = _render_synced_month_controls(
                "region",
                region_month_labels,
                latest_month_label,
            )
            snapshot_df = _panel_month_snapshot(region_panel_df, selected_month_label)
            change_snapshot_df = _panel_month_change_snapshot(region_panel_df, selected_month_label)
            snapshot_metrics = _panel_snapshot_metrics(snapshot_df)

            metric_cols = st.columns(4)
            with metric_cols[0]:
                metric_card("Gross Exposure", format_percentage(snapshot_metrics["gross_exposure"]))
            with metric_cols[1]:
                metric_card("Net Exposure", format_percentage(snapshot_metrics["net_exposure"]))
            with metric_cols[2]:
                metric_card(
                    "Largest Long",
                    format_percentage(snapshot_metrics["largest_long_value"]),
                    help_text=snapshot_metrics["largest_long_category"],
                )
            with metric_cols[3]:
                metric_card(
                    "Largest Short",
                    format_percentage(snapshot_metrics["largest_short_value"]),
                    help_text=snapshot_metrics["largest_short_category"],
                )

            section_header(
                "Exposure Snapshot",
                f"Exposure percent of NAV for {selected_month_label}, with long exposure on the right and short exposure on the left.",
            )
            _render_chart(asset_class_snapshot_bars(snapshot_df, "long_short", f"Region Exposure Snapshot - {selected_month_label}"))

            section_header(
                "Attribution Snapshot",
                "Month-on-month change in region exposure. This is a positioning-change view, not a return-contribution view.",
            )
            if change_snapshot_df.empty:
                empty_state("A prior month is required before month-on-month region exposure changes can be shown.")
            else:
                _render_chart(
                    asset_class_snapshot_change_bars(
                        change_snapshot_df,
                        f"Month-on-Month Region Exposure Change - {selected_month_label}",
                    )
                )
            snapshot_table_df = snapshot_df[
                ["category_label", "long_exposure", "short_exposure", "net_exposure", "gross_exposure"]
            ].rename(
                columns={
                    "category_label": "Region",
                    "long_exposure": "Long",
                    "short_exposure": "Short",
                    "net_exposure": "Net",
                    "gross_exposure": "Gross",
                }
            ).sort_values("Gross", ascending=False)
            for column in ["Long", "Short", "Net", "Gross"]:
                snapshot_table_df[column] = snapshot_table_df[column].map(lambda value: f"{value:+.2%}")
            section_header("Snapshot Table", "Table version of the selected month region snapshot.")
            st.dataframe(snapshot_table_df, use_container_width=True, hide_index=True)
        else:
            empty_state("Monthly region exposure breakdown is unavailable.")

    with category_tab:
        st.caption("Five-year evolution of one selected region, with long, short, and net exposure shown together.")
        if region_options:
            selected_region = st.selectbox("Category", region_options, index=0, key="region_category_selector")
            region_history_df = region_panel_df[region_panel_df["category_label"] == selected_region].copy().sort_values("date")
            region_change_df = _panel_category_change_history(region_panel_df, selected_region)
            latest_region_slice = region_history_df.sort_values("date").tail(1)
            latest_region_date = latest_region_slice["date"].iloc[0].strftime("%Y-%m") if not latest_region_slice.empty else None

            region_metric_cols = st.columns(4)
            with region_metric_cols[0]:
                metric_card("Latest Long", format_percentage(float(latest_region_slice["long_exposure"].iloc[0])) if not latest_region_slice.empty else "N/A")
            with region_metric_cols[1]:
                metric_card("Latest Short", format_percentage(float(latest_region_slice["short_exposure"].iloc[0])) if not latest_region_slice.empty else "N/A")
            with region_metric_cols[2]:
                metric_card("Latest Net", format_percentage(float(latest_region_slice["net_exposure"].iloc[0])) if not latest_region_slice.empty else "N/A")
            with region_metric_cols[3]:
                metric_card(
                    "Latest Gross",
                    format_percentage(float(latest_region_slice["gross_exposure"].iloc[0])) if not latest_region_slice.empty else "N/A",
                    help_text=latest_region_date,
                )

            section_header(
                "Exposure Evolution",
                "Long is shown as the positive sleeve, short remains below zero, and net shows the combined region exposure.",
            )
            _render_chart(
                asset_class_category_evolution_chart(
                    region_history_df,
                    f"{selected_region} Region Exposure Evolution",
                )
            )

            section_header(
                "Attribution by Month",
                "Month-on-month change in long and short exposure for the selected region.",
            )
            _render_chart(
                asset_class_monthly_change_chart(
                    region_change_df,
                    f"{selected_region} Region Monthly Exposure Change",
                )
            )

            region_table_df = region_history_df[
                ["date", "long_exposure", "short_exposure", "net_exposure", "gross_exposure"]
            ].copy()
            region_table_df["date"] = region_table_df["date"].dt.strftime("%Y-%m")
            region_table_df = region_table_df.rename(
                columns={
                    "date": "Month",
                    "long_exposure": "Long",
                    "short_exposure": "Short",
                    "net_exposure": "Net",
                    "gross_exposure": "Gross",
                }
            ).sort_values("Month", ascending=False)
            for column in ["Long", "Short", "Net", "Gross"]:
                region_table_df[column] = region_table_df[column].map(lambda value: f"{value:+.2%}")
            section_header("Category Table", f"Monthly history for {selected_region}.")
            st.dataframe(region_table_df, use_container_width=True, hide_index=True)
            if not region_reference_df.empty and {"region_taxonomy", "parent_region", "description"}.issubset(region_reference_df.columns):
                selected_reference_df = region_reference_df[region_reference_df["region_taxonomy"].astype(str) == str(selected_region)].copy()
                section_header("Region Definition", "Reference taxonomy for the selected region.")
                dataframe_with_empty_state(selected_reference_df, "Region taxonomy reference is unavailable.")
        else:
            empty_state("Region category history is unavailable.")

    with table_tab:
        st.caption("Monthly region exposure table across all region categories. Currency remains a supporting current-state table below.")
        source_col, field_col = st.columns([1, 2])
        with source_col:
            selected_source = st.selectbox("Source", ["Exposure", "Attribution"], index=0, key="region_table_source")
        with field_col:
            field_options = (
                ["Net (Long+Short)", "Long", "Short", "Gross (|L|+|S|)"]
                if selected_source == "Exposure"
                else ["Net Change", "Long Change", "Short Change", "Gross Change"]
            )
            selected_field = st.selectbox("Field", field_options, index=0, key="region_table_field")
        if selected_source == "Attribution":
            st.caption("Attribution here is implemented as month-on-month exposure change by region. It is not return contribution attribution.")
        table_df = _panel_data_table(region_panel_df, selected_source, selected_field)
        if table_df.empty:
            empty_state("Region data table is unavailable.")
        else:
            display_table_df = table_df.copy().reset_index().rename(columns={"month": "Month"})
            for column in display_table_df.columns:
                if column != "Month":
                    display_table_df[column] = display_table_df[column].map(lambda value: f"{value:+.2%}")
            st.dataframe(display_table_df, use_container_width=True, height=520, hide_index=True)
        section_header("Currency Exposure Table", "Current holdings-based currency concentration.")
        dataframe_with_empty_state(display_currency_value_table_df, "Currency exposure table is unavailable.")
        section_header("Region Taxonomy Reference", "Reference list for the project region structure.")
        dataframe_with_empty_state(region_reference_df, "Region taxonomy reference is unavailable.")
        section_header("Current Holdings by Region and Currency", "Current holdings snapshot for tracing region and reporting-currency concentration.")
        holdings_region_currency_display_df = format_display_dataframe(
            holdings_region_currency_df,
            money_columns=["final_value_usd_m"],
            pct_columns=["allocation_pct"],
        )
        dataframe_with_empty_state(holdings_region_currency_display_df, "Current holdings region/currency snapshot is unavailable.")


def render_public_markets_page():
    holdings_df = load_portfolio_holdings()
    public_holdings_df = _prepare_public_holdings(holdings_df)
    public_exposure_history_df = load_position_exposure_history()
    if not public_exposure_history_df.empty and "asset_class" in public_exposure_history_df.columns:
        public_exposure_history_df = public_exposure_history_df[
            public_exposure_history_df["asset_class"].astype(str).isin(
                ["Global Public Equities", "Fixed Income & Liquid Credit", "Hedge Funds / Absolute Return"]
            )
        ].copy()
    public_prices_df = load_public_monthly_prices()
    proxy_map_df = load_public_proxy_map()
    monthly_summary_df = load_portfolio_monthly_summary()
    risk_metrics_df = load_public_risk_metrics()
    risk_free_df = load_risk_free_proxy_monthly()
    public_value_df = pd.DataFrame()
    if not monthly_summary_df.empty and {"date", "public_markets_usd_m"}.issubset(monthly_summary_df.columns):
        public_value_df = monthly_summary_df[["date", "public_markets_usd_m"]].rename(columns={"public_markets_usd_m": "value_usd_m"})
    public_summary = calculate_public_market_summary(
        public_holdings_df,
        monthly_summary_df,
        public_prices_df,
        proxy_map_df,
    )
    public_basket_df = build_public_proxy_basket_history(
        public_holdings_df,
        public_prices_df,
        proxy_map_df,
    )
    public_performance_table = calculate_return_statistics_table(
        public_basket_df,
        risk_free_df=risk_free_df,
    )
    holdings_table = _prepare_public_holdings_review_table(
        public_holdings_df,
        public_prices_df,
        risk_metrics_df,
        proxy_map_df,
    )

    _render_page_header(
        "Public Markets Monitoring",
        "This page monitors the public and liquid sleeve of the portfolio through a public-proxy overlay. "
        "Holdings are synthetic, and all performance / risk outputs here are proxy-based rather than full-portfolio realized returns.",
    )
    _render_demo_state_status_bar()
    overview_tab, performance_tab, sector_tab, holdings_tab = st.tabs(
        ["Overview", "Performance", "Sector & Market Cap", "Holdings"]
    )

    with overview_tab:
        data_source = (
            public_prices_df["data_source"].iloc[0]
            if not public_prices_df.empty and "data_source" in public_prices_df.columns
            else "unknown"
        )
        if data_source == "synthetic":
            st.info("Using synthetic public market proxy price history because the local real market price file is unavailable or below the minimum coverage threshold.")
        else:
            st.info(
                "Using local real public market prices from `data/raw/market_prices/` for the public-proxy overlay. "
                f"Coverage: {format_percentage(public_summary['coverage_ratio'])}. "
                f"Last price date: {_format_optional_date(public_summary['last_price_date'])}."
            )
        st.info("Scope: current public / liquid sleeve only. Private assets are excluded here except where a separate proxy mapping is used downstream in Risk Profile.")
        st.caption("Overview focuses on current public-sleeve value, signed exposure, concentration, and whether the local proxy price file is sufficiently complete.")
        metric_cols = st.columns(4)
        with metric_cols[0]:
            metric_card("Public Market Value", format_usd_millions(public_summary["total_public_value"]), _SOURCE_HELP["portfolio_overlay"])
        with metric_cols[1]:
            metric_card("Public Weight", format_percentage(public_summary["public_weight"]), "Uses current public holdings divided by the processed portfolio total AUM.")
        with metric_cols[2]:
            metric_card("Gross Exposure", format_percentage(public_summary["gross_exposure"]), _SOURCE_HELP["public_proxy"])
        with metric_cols[3]:
            metric_card("Net Exposure", format_percentage(public_summary["net_exposure"]), _SOURCE_HELP["public_proxy"])

        exposure_cols = st.columns(4)
        with exposure_cols[0]:
            metric_card("Long Exposure", format_percentage(public_summary["long_exposure"]))
        with exposure_cols[1]:
            metric_card("Short Exposure", format_percentage(public_summary["short_exposure"]))
        with exposure_cols[2]:
            metric_card(
                "Largest Long",
                format_percentage(public_summary["largest_long_value"]),
                help_text=public_summary["largest_long_name"],
            )
        with exposure_cols[3]:
            metric_card(
                "Largest Short",
                format_percentage(public_summary["largest_short_value"]),
                help_text=public_summary["largest_short_name"],
            )

        data_cols = st.columns(4)
        with data_cols[0]:
            metric_card("Public Holdings", f"{len(public_holdings_df):,}", _SOURCE_HELP["portfolio_overlay"])
        with data_cols[1]:
            metric_card("Proxy Tickers", f"{int(public_summary['proxy_tickers'] or 0):,}", _SOURCE_HELP["external_market"])
        with data_cols[2]:
            metric_card("Real Data Coverage", format_percentage(public_summary["coverage_ratio"]), _SOURCE_HELP["external_market"])
        with data_cols[3]:
            metric_card("Last Price Date", _format_optional_date(public_summary["last_price_date"]), _SOURCE_HELP["external_market"])

        section_header("Public Market Value Trend")
        _render_chart(public_market_value_trend_chart(public_value_df))
        section_header("Public Holdings by Value")
        _render_chart(public_holdings_chart(public_holdings_df))
        if not public_exposure_history_df.empty and {"date", "instrument_type", "position_side", "net_weight"}.issubset(public_exposure_history_df.columns):
            section_header("Instrument Mix Exposure")
            _render_chart(
                dimension_exposure_filter_chart(
                    public_exposure_history_df,
                    "instrument_type",
                    "Public Instrument Exposure (% NAV)",
                )
            )

    with performance_tab:
        st.caption("Performance is shown as a current-weight public proxy basket. It is proxy-based sleeve monitoring, not a full audited public-book return series.")
        latest_proxy_return = (
            float(public_basket_df.sort_values("date").iloc[-1]["monthly_return"])
            if not public_basket_df.empty and "monthly_return" in public_basket_df.columns
            else None
        )
        perf_metric_cols = st.columns(4)
        with perf_metric_cols[0]:
            metric_card("Latest Monthly Return", format_percentage(latest_proxy_return), _SOURCE_HELP["public_proxy"])
        with perf_metric_cols[1]:
            metric_card("Annualized Return", _metric_from_table(public_performance_table, "Annualized Return", "Since Inception"), _SOURCE_HELP["public_proxy"])
        with perf_metric_cols[2]:
            metric_card("Annualized Volatility", _metric_from_table(public_performance_table, "Annualized Volatility", "Since Inception"), _SOURCE_HELP["public_proxy"])
        with perf_metric_cols[3]:
            metric_card("Sharpe Ratio", _metric_from_table(public_performance_table, "Sharpe Ratio", "Since Inception"), "Proxy-basket Sharpe based on monthly returns and the Treasury-bill proxy where available.")
        drawdown_cols = st.columns(2)
        with drawdown_cols[0]:
            metric_card("Largest Drawdown", _metric_from_table(public_performance_table, "Largest Drawdown", "Since Inception"))
        with drawdown_cols[1]:
            metric_card("3Y Annualized Return", _metric_from_table(public_performance_table, "Annualized Return", "3 Years"))

        section_header("Public Proxy Basket", "Current public-sleeve signed exposures are mapped to approved proxy tickers and rolled into a local monthly proxy basket.")
        _render_chart(public_proxy_basket_chart(public_basket_df))
        section_header("Public Proxy Basket Drawdown")
        _render_chart(public_proxy_drawdown_timeseries_chart(public_basket_df))
        section_header("Performance Statistics", "Statistics use monthly public-proxy returns. Sharpe uses the Treasury-bill proxy series where available.")
        dataframe_with_empty_state(public_performance_table, "Public proxy performance statistics are unavailable.")
        section_header("Proxy Performance Breadth")
        _render_chart(public_proxy_performance_chart(public_prices_df))
        section_header("Average Monthly Proxy Returns")
        _render_chart(_monthly_public_returns_chart(public_prices_df))
        if not risk_metrics_df.empty:
            section_header("Proxy Volatility and Drawdown Table")
            display_risk_df = risk_metrics_df[
                [column for column in ["ticker", "annualized_volatility", "max_drawdown", "start_date", "end_date"] if column in risk_metrics_df.columns]
            ].copy()
            display_risk_df = format_display_dataframe(
                display_risk_df,
                pct_columns=["annualized_volatility", "max_drawdown"],
                date_columns=["start_date", "end_date"],
            )
            dataframe_with_empty_state(display_risk_df, "Risk metrics are unavailable.")

    with sector_tab:
        st.caption("Sector and market-cap views focus on current signed exposure plus exposure trends through time. Unknown and non-classifiable buckets remain visible rather than being hidden.")
        sector_dimension_tab, market_cap_dimension_tab = st.tabs(["Sector", "Market Cap"])

        with sector_dimension_tab:
            _render_public_classification_panel(
                public_holdings_df,
                public_exposure_history_df,
                holdings_category_column="gics_sector",
                history_category_column="gics_sector_pti",
                label="Sector",
                prefix="public_sector",
            )

        with market_cap_dimension_tab:
            _render_public_classification_panel(
                public_holdings_df,
                public_exposure_history_df,
                holdings_category_column="market_cap_bucket",
                history_category_column="market_cap_bucket_pti",
                label="Market Cap",
                prefix="public_market_cap",
            )

    with holdings_tab:
        st.caption("Holdings are shown as a review table with proxy ticker, signed exposure, delta-adjusted exposure, and classification fields used by the public-risk overlay.")
        filtered_holdings = holdings_table.copy()
        filter_cols = st.columns(5)
        if not filtered_holdings.empty:
            with filter_cols[0]:
                side_options = sorted(filtered_holdings["position_side_current"].dropna().astype(str).unique().tolist()) if "position_side_current" in filtered_holdings.columns else []
                selected_sides = st.multiselect("Side", side_options, default=side_options, key="public_holdings_side_filter")
            with filter_cols[1]:
                instrument_options = sorted(filtered_holdings["instrument_type"].dropna().astype(str).unique().tolist()) if "instrument_type" in filtered_holdings.columns else []
                selected_instruments = st.multiselect("Instrument", instrument_options, default=instrument_options, key="public_holdings_instrument_filter")
            with filter_cols[2]:
                sector_options = sorted(filtered_holdings["gics_sector"].dropna().astype(str).unique().tolist()) if "gics_sector" in filtered_holdings.columns else []
                selected_sectors = st.multiselect("Sector", sector_options, default=sector_options, key="public_holdings_sector_filter")
            with filter_cols[3]:
                market_cap_options = sorted(filtered_holdings["market_cap_bucket"].dropna().astype(str).unique().tolist()) if "market_cap_bucket" in filtered_holdings.columns else []
                selected_market_caps = st.multiselect("Market Cap", market_cap_options, default=market_cap_options, key="public_holdings_market_cap_filter")
            with filter_cols[4]:
                region_options = sorted(filtered_holdings["region"].dropna().astype(str).unique().tolist()) if "region" in filtered_holdings.columns else []
                selected_regions = st.multiselect("Region", region_options, default=region_options, key="public_holdings_region_filter")

            if side_options:
                filtered_holdings = filtered_holdings[filtered_holdings["position_side_current"].astype(str).isin(selected_sides)]
            if instrument_options:
                filtered_holdings = filtered_holdings[filtered_holdings["instrument_type"].astype(str).isin(selected_instruments)]
            if sector_options:
                filtered_holdings = filtered_holdings[filtered_holdings["gics_sector"].astype(str).isin(selected_sectors)]
            if market_cap_options:
                filtered_holdings = filtered_holdings[filtered_holdings["market_cap_bucket"].astype(str).isin(selected_market_caps)]
            if region_options:
                filtered_holdings = filtered_holdings[filtered_holdings["region"].astype(str).isin(selected_regions)]

        if "abs_signed_exposure_usd_m" in filtered_holdings.columns:
            filtered_holdings = filtered_holdings.sort_values("abs_signed_exposure_usd_m", ascending=False)
        display_columns = [
            column
            for column in [
                "holding_name",
                "ticker",
                "proxy_ticker",
                "asset_class",
                "instrument_type",
                "position_side_current",
                "gics_sector",
                "market_cap_bucket",
                "region",
                "currency",
                "final_value_usd_m",
                "signed_exposure_usd_m",
                "current_exposure_usd_m",
                "current_gross_notional_usd_m",
                "current_delta_adjusted_exposure_usd_m",
                "allocation_pct",
                "latest_close",
                "latest_price_date",
                "monthly_return",
                "annualized_volatility",
                "max_drawdown",
            ]
            if column in filtered_holdings.columns
        ]
        display_df = filtered_holdings[display_columns].copy() if display_columns else filtered_holdings.copy()
        display_df = format_display_dataframe(
            display_df,
            money_columns=[
                "final_value_usd_m",
                "signed_exposure_usd_m",
                "current_exposure_usd_m",
                "current_gross_notional_usd_m",
                "current_delta_adjusted_exposure_usd_m",
            ],
            pct_columns=["allocation_pct", "monthly_return", "annualized_volatility", "max_drawdown"],
            date_columns=["latest_price_date"],
        )
        if "latest_close" in display_df.columns:
            display_df["latest_close"] = pd.to_numeric(filtered_holdings["latest_close"], errors="coerce").map(lambda value: "N/A" if pd.isna(value) else f"{value:,.2f}")
        dataframe_with_empty_state(display_df, "Public holdings data is unavailable.")
        section_header("Proxy Mapping")
        if not proxy_map_df.empty:
            columns = [column for column in ["holding_name", "ticker_or_proxy", "use_in_final_risk_module", "notes"] if column in proxy_map_df.columns]
            dataframe_with_empty_state(proxy_map_df[columns] if columns else proxy_map_df, "Proxy mapping is unavailable.")
        else:
            empty_state("Proxy mapping is unavailable.")


def render_private_markets_page():
    positions_df = load_private_positions()
    private_monthly_df = load_private_fund_monthly()
    cashflows_df = load_private_market_cashflows()
    commentary_df = load_fund_commentary()
    capital_call_df = load_capital_call_calendar()
    metrics = calculate_private_markets_summary(positions_df, private_monthly_df, cashflows_df)
    metrics["capital_calls_this_month"] = _capital_calls_this_month(capital_call_df)
    total_private_nav_df = build_private_nav_timeseries(private_monthly_df)
    strategy_summary_df = build_private_dimension_summary(positions_df, "strategy", "Strategy")
    geography_summary_df = build_private_dimension_summary(positions_df, "investment_geography", "Geography")
    sector_summary_df = build_private_dimension_summary(positions_df, "mandate_sector", "Mandate Sector")
    statement_lag_df = build_private_statement_lag_table(positions_df)

    _render_page_header(
        "Private Markets Monitoring",
        "This page monitors private NAV, commitments, paid-in capital, unfunded exposure, and approved document-driven cashflow updates to the private portfolio layer. "
        "Figures reflect the synthetic baseline plus approved post-ingestion state.",
    )
    nav_tab, commitments_tab, cashflows_tab, table_tab = st.tabs(["NAV Trend", "Commitments", "Cashflows", "Fund Table"])

    with nav_tab:
        st.caption("Private market monitoring tracks NAV, statement date, valuation lag, strategy mix, and mandate geography using fund-level synthetic data plus approved post-ingestion updates.")
        metric_cols = st.columns(4)
        with metric_cols[0]:
            metric_card("Private Fund NAV", format_usd_millions(metrics["private_fund_nav"]))
            metric_card("Total Commitments", format_usd_millions(metrics["total_commitments"]))
        with metric_cols[1]:
            metric_card("Paid-in Capital", format_usd_millions(metrics["paid_in_capital"]))
            metric_card("Unfunded Commitments", format_usd_millions(metrics["unfunded_commitments"]), "Remaining callable capital across private funds.")
        with metric_cols[2]:
            metric_card("Fund Count", f"{int(metrics['fund_count']):,}")
            metric_card("Strategy Count", f"{int(metrics['strategy_count']):,}")
        with metric_cols[3]:
            metric_card("Capital Calls This Month", format_usd_millions(metrics["capital_calls_this_month"]))
            metric_card("Distributions This Month", format_usd_millions(metrics["distributions_this_month"]))
        secondary_cols = st.columns(4)
        with secondary_cols[0]:
            metric_card("12M NAV Growth", format_percentage(metrics["trailing_12m_nav_growth"]))
        with secondary_cols[1]:
            metric_card("NAV / Paid-in", format_multiple(metrics["nav_to_paid_in_ratio"]), "Current NAV divided by cumulative paid-in capital.")
        with secondary_cols[2]:
            metric_card("Latest Statement Date", _format_optional_date(metrics["latest_statement_date"]))
        with secondary_cols[3]:
            metric_card("Avg Statement Lag", "N/A" if metrics["average_statement_lag_days"] is None else f"{metrics['average_statement_lag_days']:.0f} days")
        section_header("Total Private NAV Trend")
        _render_chart(private_total_nav_trend_chart(total_private_nav_df))
        section_header("Private Fund NAV Trend")
        _render_chart(private_nav_trend_chart(private_monthly_df))
        section_header("NAV by Fund")
        _render_chart(nav_by_fund_chart(positions_df))
        section_header("NAV by Strategy")
        display_strategy_summary_df = format_display_dataframe(
            strategy_summary_df,
            money_columns=["nav_usd_m", "commitment_usd_m", "paid_in_capital_usd_m", "unfunded_commitment_usd_m"],
            pct_columns=["funded_ratio", "unfunded_ratio"],
            count_columns=["fund_count"],
        )
        dataframe_with_empty_state(display_strategy_summary_df, "Strategy summary is unavailable.")
        _render_chart(private_dimension_bar_chart(strategy_summary_df, "Strategy", "nav_usd_m", "NAV by Strategy"))
        section_header("Statement Lag by Fund")
        display_statement_lag_df = format_display_dataframe(
            statement_lag_df,
            money_columns=["current_nav_usd_m"],
            date_columns=["last_statement_date"],
            day_columns=["statement_lag_days"],
        )
        dataframe_with_empty_state(display_statement_lag_df, "Statement lag data is unavailable.")
        _render_chart(private_statement_lag_chart(statement_lag_df))

    with commitments_tab:
        st.caption("Family offices monitor total commitment, paid-in capital, unfunded commitment, commitment utilization, and concentration by strategy, geography, and mandate sector.")
        metric_cols = st.columns(4)
        with metric_cols[0]:
            metric_card("Funded Ratio", format_percentage(metrics["funded_ratio"]))
        with metric_cols[1]:
            metric_card("Proxy-Mapped Funds", f"{int(metrics['proxy_mapped_fund_count']):,}")
        with metric_cols[2]:
            metric_card("Proxy-Mapped NAV", format_usd_millions(metrics["proxy_mapped_nav"]))
        with metric_cols[3]:
            metric_card("Geography Count", f"{int(metrics['geography_count']):,}")
        section_header("Commitment vs Unfunded by Fund")
        _render_chart(commitment_vs_unfunded_chart(positions_df))
        section_header("Paid-in vs Unfunded Commitment")
        _render_chart(paid_in_vs_unfunded_stacked_chart(positions_df))
        section_header("Commitment by Geography")
        display_geography_summary_df = format_display_dataframe(
            geography_summary_df,
            money_columns=["nav_usd_m", "commitment_usd_m", "paid_in_capital_usd_m", "unfunded_commitment_usd_m"],
            pct_columns=["funded_ratio", "unfunded_ratio"],
            count_columns=["fund_count"],
        )
        dataframe_with_empty_state(display_geography_summary_df, "Geography summary is unavailable.")
        _render_chart(private_dimension_bar_chart(geography_summary_df, "Geography", "commitment_usd_m", "Commitment by Geography"))
        section_header("Unfunded by Strategy")
        _render_chart(private_dimension_bar_chart(strategy_summary_df, "Strategy", "unfunded_commitment_usd_m", "Unfunded Commitment by Strategy"))
        section_header("NAV by Mandate Sector")
        display_sector_summary_df = format_display_dataframe(
            sector_summary_df,
            money_columns=["nav_usd_m", "commitment_usd_m", "paid_in_capital_usd_m", "unfunded_commitment_usd_m"],
            pct_columns=["funded_ratio", "unfunded_ratio"],
            count_columns=["fund_count"],
        )
        dataframe_with_empty_state(display_sector_summary_df, "Mandate sector summary is unavailable.")
        _render_chart(private_dimension_bar_chart(sector_summary_df, "Mandate Sector", "nav_usd_m", "NAV by Mandate Sector"))

    with cashflows_tab:
        st.caption("Capital calls and distributions drive liquidity planning. Only approved document-driven cashflows and commentary appear here, so this tab is intentionally narrower than a full operations ledger.")
        metric_cols = st.columns(4)
        with metric_cols[0]:
            metric_card("Approved Cashflow Rows", f"{len(cashflows_df):,}")
        with metric_cols[1]:
            metric_card("Expected Cash Inflow", format_usd_millions(safe_sum(cashflows_df, ["expected_cash_inflow_usd_m"])))
        with metric_cols[2]:
            metric_card("Net Distribution", format_usd_millions(safe_sum(cashflows_df, ["net_distribution_usd_m"])))
        with metric_cols[3]:
            metric_card("Approved Commentary Rows", f"{len(commentary_df):,}")
        section_header("Capital Calls and Distributions")
        _render_chart(private_market_cashflow_chart(cashflows_df))
        section_header("Distribution Timeline")
        _render_chart(distribution_timeline_chart(cashflows_df))
        section_header("Approved Fund Commentary")
        commentary_display_df = commentary_df.copy()
        if not commentary_display_df.empty:
            commentary_columns = [
                column
                for column in [
                    "fund_name",
                    "reporting_period",
                    "market_themes",
                    "risk_notes",
                    "valuation_commentary",
                    "expected_capital_activity",
                    "source_document_id",
                ]
                if column in commentary_display_df.columns
            ]
            commentary_display_df = commentary_display_df[commentary_columns] if commentary_columns else commentary_display_df
        dataframe_with_empty_state(commentary_display_df, "No approved fund commentary is available yet.")

    with table_tab:
        st.caption("Use the filters below to review the current post-ingestion private portfolio state by strategy, geography, update provenance, and proxy mapping status.")
        filtered_positions_df = positions_df.copy()
        filter_cols = st.columns(4)
        with filter_cols[0]:
            strategy_options = sorted(filtered_positions_df["strategy"].dropna().astype(str).unique().tolist()) if not filtered_positions_df.empty and "strategy" in filtered_positions_df.columns else []
            selected_strategies = st.multiselect("Strategy", strategy_options, default=strategy_options, key="private_table_strategy_filter")
            if strategy_options:
                filtered_positions_df = filtered_positions_df[filtered_positions_df["strategy"].astype(str).isin(selected_strategies)]
        with filter_cols[1]:
            geography_options = sorted(filtered_positions_df["investment_geography"].dropna().astype(str).unique().tolist()) if not filtered_positions_df.empty and "investment_geography" in filtered_positions_df.columns else []
            selected_geographies = st.multiselect("Geography", geography_options, default=geography_options, key="private_table_geography_filter")
            if geography_options:
                filtered_positions_df = filtered_positions_df[filtered_positions_df["investment_geography"].astype(str).isin(selected_geographies)]
        with filter_cols[2]:
            update_options = sorted(filtered_positions_df["update_type"].dropna().astype(str).unique().tolist()) if not filtered_positions_df.empty and "update_type" in filtered_positions_df.columns else []
            selected_updates = st.multiselect("Update Type", update_options, default=update_options, key="private_table_update_filter")
            if update_options:
                filtered_positions_df = filtered_positions_df[filtered_positions_df["update_type"].astype(str).isin(selected_updates)]
        with filter_cols[3]:
            mapping_options = sorted(filtered_positions_df["proxy_mapping_flag"].dropna().astype(str).unique().tolist()) if not filtered_positions_df.empty and "proxy_mapping_flag" in filtered_positions_df.columns else []
            selected_mapping = st.multiselect("Proxy Mapping Flag", mapping_options, default=mapping_options, key="private_table_mapping_filter")
            if mapping_options:
                filtered_positions_df = filtered_positions_df[filtered_positions_df["proxy_mapping_flag"].astype(str).isin(selected_mapping)]
        section_header("Private Fund Table")
        columns = [
            "fund_name",
            "strategy",
            "sub_strategy",
            "reporting_cadence",
            "investment_geography",
            "mandate_sector",
            "current_nav_usd_m",
            "commitment_usd_m",
            "paid_in_capital_usd_m",
            "unfunded_commitment_usd_m",
            "last_statement_date",
            "valuation_status",
            "proxy_ticker_or_bucket",
            "proxy_mapping_confidence",
            "proxy_mapping_flag",
            "source_document_id",
            "update_type",
            "extraction_mode",
            "update_applied_flag",
        ]
        available = [column for column in columns if column in positions_df.columns]
        display_df = filtered_positions_df[available].copy() if not filtered_positions_df.empty else filtered_positions_df.copy()
        display_df = format_display_dataframe(
            display_df,
            money_columns=[
                "current_nav_usd_m",
                "commitment_usd_m",
                "paid_in_capital_usd_m",
                "unfunded_commitment_usd_m",
            ],
            pct_columns=["proxy_mapping_confidence"],
            date_columns=["last_statement_date"],
        )
        dataframe_with_empty_state(
            display_df if not filtered_positions_df.empty else filtered_positions_df,
            "Private positions post-ingestion are unavailable.",
        )


def render_liquidity_commitments_page():
    cash_df = load_cash_accounts()
    capital_call_df = load_capital_call_calendar()
    cashflows_df = load_private_market_cashflows()
    positions_df = load_private_positions()
    liquidity_metrics = calculate_liquidity_metrics(cash_df, capital_call_df, cashflows_df)
    liquidity_horizon_df = calculate_liquidity_horizon_table(cash_df, capital_call_df, cashflows_df)
    commitment_summary = calculate_commitment_summary(positions_df)

    _render_page_header(
        "Liquidity & Commitments",
        "This page separates current baseline cash from projected private-market flows. "
        "Operating cash remains the booked baseline state, while approved calls and distributions are shown as projected overlay items until a future official close.",
    )
    overview_tab, calls_tab, distributions_tab, accounts_tab = st.tabs(
        ["Overview", "Capital Calls", "Distributions", "Cash Accounts"]
    )

    with overview_tab:
        st.caption(
            "Liquidity monitoring tracks booked cash, soft-eligible liquidity, approved projected calls, approved projected distributions, "
            "and horizon-based coverage against private-market funding needs."
        )
        liquidity_boundary_df = pd.DataFrame(
            [
                {
                    "State Layer": "Booked Baseline Cash",
                    "Value": liquidity_metrics["cash_liquidity"],
                    "Definition": "Cash balances already present in the official 2026-04-30 baseline state.",
                },
                {
                    "State Layer": "Projected Overlay Flows",
                    "Value": liquidity_metrics["expected_distributions"] - liquidity_metrics["upcoming_capital_calls"],
                    "Definition": "Approved future distributions less approved projected capital calls.",
                },
            ]
        )
        section_header(
            "Booked vs Projected Boundary",
            "Booked cash stays in the baseline state. Approved calls and distributions remain projected overlay items until a future official close.",
        )
        boundary_cols = st.columns(2)
        with boundary_cols[0]:
            metric_card("Booked Baseline Cash", format_usd_millions(liquidity_metrics["cash_liquidity"]))
            metric_card("Operating Cash", format_usd_millions(liquidity_metrics["operating_cash"]), "Booked cash flagged as immediately usable for hard call coverage.")
        with boundary_cols[1]:
            metric_card("Projected Capital Calls", format_usd_millions(liquidity_metrics["upcoming_capital_calls"]))
            metric_card("Projected Distributions", format_usd_millions(liquidity_metrics["expected_distributions"]))
        liquidity_boundary_display_df = format_display_dataframe(liquidity_boundary_df, money_columns=["Value"])
        dataframe_with_empty_state(liquidity_boundary_display_df, "Liquidity boundary summary is unavailable.")

        metric_cols = st.columns(4)
        with metric_cols[0]:
            metric_card("Cash & Liquidity", format_usd_millions(liquidity_metrics["cash_liquidity"]))
            metric_card("Operating Cash", format_usd_millions(liquidity_metrics["operating_cash"]), "Cash flagged as immediately usable for hard capital-call coverage.")
        with metric_cols[1]:
            metric_card("Soft-Eligible Liquidity", format_usd_millions(liquidity_metrics["soft_eligible_liquidity"]), "Cash and near-cash balances that can support soft coverage analysis.")
            metric_card("Projected Capital Calls", format_usd_millions(liquidity_metrics["upcoming_capital_calls"]), "Approved upcoming private-market calls tracked as projected overlay items.")
        with metric_cols[2]:
            metric_card("Projected Distributions", format_usd_millions(liquidity_metrics["expected_distributions"]), "Approved future distributions not yet booked into baseline cash.")
            metric_card("Projected Net Liquidity", format_usd_millions(liquidity_metrics["net_projected_liquidity"]), "Current baseline cash plus projected distributions minus projected calls.")
        with metric_cols[3]:
            metric_card("Cash / Projected Calls Coverage", format_percentage(liquidity_metrics["cash_to_upcoming_calls_coverage"]), "Operating cash divided by currently approved projected capital calls.")
            metric_card("Unfunded Commitments", format_usd_millions(commitment_summary["unfunded_commitments"]))
        secondary_cols = st.columns(4)
        horizon_lookup = liquidity_horizon_df.set_index("Horizon").to_dict("index") if not liquidity_horizon_df.empty and "Horizon" in liquidity_horizon_df.columns else {}
        with secondary_cols[0]:
            metric_card("USD Cash", format_usd_millions(liquidity_metrics["usd_cash"]))
        with secondary_cols[1]:
            metric_card("SGD Cash", format_usd_millions(liquidity_metrics["sgd_cash"]))
        with secondary_cols[2]:
            metric_card(
                "30D Hard Coverage",
                format_percentage(horizon_lookup.get("30D", {}).get("Hard Coverage")),
                "Operating cash divided by approved projected 30-day capital calls.",
            )
        with secondary_cols[3]:
            metric_card(
                "90D Soft Coverage",
                format_percentage(horizon_lookup.get("90D", {}).get("Soft Coverage")),
                "Operating cash plus approved projected distributions divided by approved projected 90-day calls.",
            )
        section_header("Cash by Account")
        _render_chart(cash_by_account_chart(cash_df))
        section_header("Cash by Currency")
        _render_chart(cash_by_currency_chart(cash_df))
        section_header("Cash by Purpose")
        _render_chart(cash_purpose_chart(cash_df))
        section_header("Liquidity Coverage")
        _render_chart(liquidity_coverage_chart(cash_df, capital_call_df))
        section_header("Coverage by Horizon Chart", "Hard coverage uses booked operating cash only. Soft coverage adds approved projected distributions.")
        _render_chart(liquidity_horizon_coverage_chart(liquidity_horizon_df))
        section_header("Coverage by Horizon", "Hard coverage uses booked operating cash only. Soft coverage adds projected approved distributions.")
        if not liquidity_horizon_df.empty:
            display_df = format_display_dataframe(
                liquidity_horizon_df,
                money_columns=["Operating Cash", "Upcoming Calls", "Projected Distributions"],
                pct_columns=["Hard Coverage", "Soft Coverage"],
            )
            dataframe_with_empty_state(display_df, "Liquidity horizon coverage is unavailable.")
        else:
            empty_state("Liquidity horizon coverage is unavailable.")

    with calls_tab:
        st.caption("Approved capital calls below are projected overlay obligations. They do not reduce booked baseline cash until a future official close is defined.")
        if capital_call_df.empty:
            st.info("No approved capital calls are currently in the projected call calendar. Coverage metrics therefore reflect current cash against an empty approved call calendar.")
        section_header("Capital Call Calendar")
        _render_chart(capital_call_calendar_chart(capital_call_df))
        section_header("Unfunded Commitments by Fund")
        _render_chart(unfunded_commitments_by_fund_chart(positions_df))
        section_header("Upcoming Capital Calls Table")
        call_columns = [column for column in ["due_date", "fund_name", "amount_due_usd_m", "currency", "update_applied_flag"] if column in capital_call_df.columns]
        call_display_df = capital_call_df[call_columns].copy() if call_columns else capital_call_df.copy()
        call_display_df = format_display_dataframe(
            call_display_df,
            money_columns=["amount_due_usd_m"],
            date_columns=["due_date"],
        )
        dataframe_with_empty_state(call_display_df, "No approved capital calls are currently in the calendar.")

    with distributions_tab:
        projected_distribution_df = filter_projected_distribution_cashflows(
            cashflows_df,
            liquidity_metrics.get("as_of_date"),
        )
        st.caption("Projected distributions support soft coverage but are not available cash until booked.")
        distribution_amount = safe_sum(projected_distribution_df, ["expected_cash_inflow_usd_m"])
        distribution_funds = (
            projected_distribution_df["fund_name"].nunique()
            if not projected_distribution_df.empty and "fund_name" in projected_distribution_df.columns
            else 0
        )
        distribution_dates = (
            pd.to_datetime(projected_distribution_df["cashflow_date"], errors="coerce").dropna()
            if not projected_distribution_df.empty and "cashflow_date" in projected_distribution_df.columns
            else pd.Series(dtype="datetime64[ns]")
        )
        summary_cols = st.columns(3)
        with summary_cols[0]:
            metric_card("Projected Distribution Total", format_usd_millions(distribution_amount))
        with summary_cols[1]:
            metric_card("Next Expected Date", _format_optional_date(distribution_dates.min() if not distribution_dates.empty else None))
        with summary_cols[2]:
            metric_card("Funds", f"{distribution_funds:,}")
        section_header("Projected Distributions Timeline")
        _render_chart(distribution_timeline_chart(projected_distribution_df))
        section_header("Projected Distributions by Fund", "Expected cash inflows aggregated by fund; this is not a booking-status chart.")
        distribution_fund_count = (
            projected_distribution_df["fund_name"].nunique()
            if not projected_distribution_df.empty and "fund_name" in projected_distribution_df.columns
            else 0
        )
        if distribution_fund_count == 1 and len(projected_distribution_df) == 1:
            event = projected_distribution_df.iloc[0]
            with st.container(border=True):
                event_cols = st.columns([2.2, 1.2, 1.2, 1.4])
                with event_cols[0]:
                    st.caption("Fund")
                    st.markdown(f"**{event.get('fund_name', 'N/A')}**")
                with event_cols[1]:
                    st.caption("Expected Date")
                    st.markdown(f"**{_format_optional_date(event.get('cashflow_date'))}**")
                with event_cols[2]:
                    st.caption("Expected Inflow")
                    st.markdown(f"**{format_usd_millions(event.get('expected_cash_inflow_usd_m'))}**")
                with event_cols[3]:
                    st.caption("Status")
                    st.markdown("**Projected · Not Booked**")
            st.caption("A comparison chart is hidden because only one fund currently has an approved projected distribution.")
        else:
            _render_chart(projected_distributions_by_fund_chart(projected_distribution_df))
        section_header("Distributions and Cashflows Table")
        cashflow_display_df = format_display_dataframe(
            projected_distribution_df,
            money_columns=["gross_distribution_usd_m", "net_distribution_usd_m", "expected_cash_inflow_usd_m"],
            date_columns=["cashflow_date"],
        )
        dataframe_with_empty_state(cashflow_display_df, "No approved projected distributions are available.")

    with accounts_tab:
        st.caption("Cash accounts are shown with operating-cash and soft-liquidity flags because those attributes drive the hard-versus-soft coverage logic.")
        section_header("Cash Accounts")
        account_display_df = cash_df.copy()
        account_display_df = format_display_dataframe(
            account_display_df,
            money_columns=["balance_usd_m"],
            date_columns=["as_of_date"],
        )
        dataframe_with_empty_state(account_display_df, "Cash accounts post-ingestion are unavailable.")


def render_risk_profile_page():
    risk_metrics_df = load_public_risk_metrics()
    correlation_df = load_correlation_matrix()
    stress_df = load_stress_test_results()
    proxy_map_df = load_public_proxy_map()
    holdings_df = load_portfolio_holdings()
    monthly_summary_df = load_portfolio_monthly_summary()
    public_prices_df = load_public_monthly_prices()
    risk_free_df = load_risk_free_proxy_monthly()
    public_holdings_df = _prepare_public_holdings(holdings_df)
    public_summary = calculate_public_market_summary(public_holdings_df, monthly_summary_df, public_prices_df, proxy_map_df)
    basket_history_df = build_public_proxy_basket_history(public_holdings_df, public_prices_df, proxy_map_df)
    performance_table = calculate_return_statistics_table(basket_history_df, risk_free_df=risk_free_df)
    overlay_df = prepare_public_risk_overlay(public_holdings_df, proxy_map_df, risk_metrics_df, monthly_summary_df)
    asset_class_risk_df = build_risk_dimension_summary(overlay_df, "asset_class", "Asset Class")
    sector_risk_df = build_risk_dimension_summary(overlay_df, "gics_sector", "Sector")
    region_risk_df = build_risk_dimension_summary(overlay_df, "region_taxonomy", "Region")
    liquidity_risk_df = build_risk_dimension_summary(overlay_df, "liquidity_bucket", "Liquidity Bucket")
    proxy_risk_df = build_risk_dimension_summary(overlay_df, "proxy_ticker", "Proxy")
    stress_summary_df, stress_detail_df = build_stress_impact_tables(overlay_df, stress_df, monthly_summary_df)
    top_corr_pairs_df = build_top_correlation_pairs(correlation_df)

    _render_page_header(
        "Risk Profile",
        "This page summarizes a public-proxy risk overlay using the current public and liquid holdings sleeve. "
        "It is not a full total-portfolio risk engine, and private assets only enter where a defensible proxy mapping exists.",
    )
    _render_demo_state_status_bar()

    if risk_metrics_df.empty:
        st.warning("Public market risk outputs are unavailable. Run `python3 -m src.risk.run_risk` before opening this page.")
        return

    data_source = risk_metrics_df["data_source"].iloc[0] if "data_source" in risk_metrics_df.columns else "unknown"
    if data_source == "synthetic":
        st.info("Using synthetic public market proxy price history because no real market price files were found under `data/raw/market_prices/`.")
    elif data_source == "real":
        st.info(
            f"Using local real public proxy price history from {_format_optional_date(public_summary.get('real_price_start_date'))} "
            f"to {_format_optional_date(public_summary.get('real_price_end_date'))}. Private assets remain proxy-overlay only where defensible mappings exist."
        )
    st.info("Scope: this page is a public-proxy risk overlay, not a full cross-asset family office risk engine.")

    overview_tab, volatility_tab, drawdown_tab, stress_tab, correlation_tab = st.tabs(
        ["Overview", "Volatility", "Drawdown", "Stress Test", "Correlation"]
    )

    with overview_tab:
        st.caption("This is a public-proxy overlay only. Exposure is mapped from current holdings to liquid proxies, then aggregated across asset class, sector, region, liquidity bucket, and proxy.")
        metric_cols = st.columns(4)
        with metric_cols[0]:
            metric_card("Proxy Basket Ann. Vol", _metric_from_table(performance_table, "Annualized Volatility", "Since Inception"), _SOURCE_HELP["public_proxy"])
        with metric_cols[1]:
            metric_card("Proxy Basket Max Drawdown", _metric_from_table(performance_table, "Largest Drawdown", "Since Inception"), _SOURCE_HELP["public_proxy"])
        with metric_cols[2]:
            metric_card("Proxy Basket Sharpe", _metric_from_table(performance_table, "Sharpe Ratio", "Since Inception"), _SOURCE_HELP["public_proxy"])
        with metric_cols[3]:
            metric_card("Real Data Coverage", format_percentage(public_summary.get("coverage_ratio")), _SOURCE_HELP["external_market"])
        secondary_metric_cols = st.columns(4)
        with secondary_metric_cols[0]:
            metric_card("Proxy Tickers", f"{int(risk_metrics_df['ticker'].nunique()) if 'ticker' in risk_metrics_df.columns else 0:,}", _SOURCE_HELP["external_market"])
        with secondary_metric_cols[1]:
            metric_card("Mapped Holdings", f"{int(overlay_df['holding_id'].nunique()) if not overlay_df.empty and 'holding_id' in overlay_df.columns else 0:,}", _SOURCE_HELP["portfolio_overlay"])
        with secondary_metric_cols[2]:
            metric_card("Stress Scenarios", f"{int(stress_summary_df['scenario'].nunique()) if not stress_summary_df.empty and 'scenario' in stress_summary_df.columns else 0:,}", "Number of predefined proxy shock scenarios available in the stress module.")
        with secondary_metric_cols[3]:
            metric_card("Last Real Price Date", _format_optional_date(public_summary.get("last_price_date")), _SOURCE_HELP["external_market"])

        section_header(
            "Proxy Overlay Performance Statistics",
            "These statistics are for the current-weight public proxy basket, not the full family office portfolio.",
        )
        dataframe_with_empty_state(performance_table, "Public proxy performance statistics are unavailable.")

        section_header("Risk Overlay by Asset Class", "Signed and gross exposure are based on current holdings mapped into the risk layer.")
        display_asset_class_risk_df = format_display_dataframe(
            asset_class_risk_df,
            money_columns=["Signed Exposure (USD m)", "Gross Exposure (USD m)"],
            pct_columns=["Exposure % NAV", "Gross Exposure % NAV", "Exposure-Weighted Volatility", "Exposure-Weighted Drawdown"],
            count_columns=["Proxy Count"],
        )
        dataframe_with_empty_state(display_asset_class_risk_df, "Asset-class risk overlay is unavailable.")
        _render_chart(risk_dimension_chart(asset_class_risk_df, "Asset Class", "Exposure-Weighted Volatility", "Exposure-Weighted Volatility by Asset Class"))

        section_header("Risk Overlay by Liquidity Bucket")
        display_liquidity_risk_df = format_display_dataframe(
            liquidity_risk_df,
            money_columns=["Signed Exposure (USD m)", "Gross Exposure (USD m)"],
            pct_columns=["Exposure % NAV", "Gross Exposure % NAV", "Exposure-Weighted Volatility", "Exposure-Weighted Drawdown"],
            count_columns=["Proxy Count"],
        )
        dataframe_with_empty_state(display_liquidity_risk_df, "Liquidity-bucket overlay is unavailable.")
        _render_chart(risk_dimension_chart(liquidity_risk_df, "Liquidity Bucket", "Gross Exposure % NAV", "Gross Exposure % NAV by Liquidity Bucket"))

        section_header("Proxy Mapping")
        if not proxy_map_df.empty:
            columns = [
                column
                for column in [
                    "holding_name",
                    "ticker_or_proxy",
                    "risk_proxy_bucket",
                    "mapping_confidence",
                    "use_in_final_risk_module",
                    "mapping_notes",
                ]
                if column in proxy_map_df.columns
            ]
            proxy_display_df = proxy_map_df[columns].copy() if columns else proxy_map_df.copy()
            proxy_display_df = format_display_dataframe(proxy_display_df, pct_columns=["mapping_confidence"])
            dataframe_with_empty_state(proxy_display_df, "Proxy mapping is unavailable.")
        else:
            empty_state("Proxy mapping is unavailable.")

    with volatility_tab:
        section_header("Annualized Volatility", "Ticker-level volatility comes from the risk module. Dimension views are exposure-weighted overlays.")
        display_columns = [column for column in ["ticker", "annualized_volatility", "start_date", "end_date"] if column in risk_metrics_df.columns]
        risk_metrics_display_df = risk_metrics_df[display_columns].copy() if display_columns else risk_metrics_df.copy()
        risk_metrics_display_df = format_display_dataframe(
            risk_metrics_display_df,
            pct_columns=["annualized_volatility"],
            date_columns=["start_date", "end_date"],
        )
        dataframe_with_empty_state(risk_metrics_display_df, "Risk metrics are unavailable.")
        _render_chart(risk_metric_bar_chart(risk_metrics_df))
        section_header("Exposure-Weighted Volatility by Sector")
        sector_display_df = format_display_dataframe(
            sector_risk_df,
            money_columns=["Signed Exposure (USD m)", "Gross Exposure (USD m)"],
            pct_columns=["Exposure % NAV", "Gross Exposure % NAV", "Exposure-Weighted Volatility", "Exposure-Weighted Drawdown"],
            count_columns=["Proxy Count"],
        )
        dataframe_with_empty_state(sector_display_df, "Sector risk overlay is unavailable.")
        _render_chart(risk_dimension_chart(sector_risk_df, "Sector", "Exposure-Weighted Volatility", "Exposure-Weighted Volatility by Sector"))
        section_header("Exposure-Weighted Volatility by Region")
        region_display_df = format_display_dataframe(
            region_risk_df,
            money_columns=["Signed Exposure (USD m)", "Gross Exposure (USD m)"],
            pct_columns=["Exposure % NAV", "Gross Exposure % NAV", "Exposure-Weighted Volatility", "Exposure-Weighted Drawdown"],
            count_columns=["Proxy Count"],
        )
        dataframe_with_empty_state(region_display_df, "Region risk overlay is unavailable.")
        _render_chart(risk_dimension_chart(region_risk_df, "Region", "Exposure-Weighted Volatility", "Exposure-Weighted Volatility by Region"))
        if not proxy_risk_df.empty:
            section_header("Highest Volatility Proxy Exposures")
            top_proxy_vol_df = proxy_risk_df.sort_values("Exposure-Weighted Volatility", ascending=False).head(15)
            top_proxy_vol_df = format_display_dataframe(
                top_proxy_vol_df,
                money_columns=["Signed Exposure (USD m)", "Gross Exposure (USD m)"],
                pct_columns=["Exposure % NAV", "Gross Exposure % NAV", "Exposure-Weighted Volatility", "Exposure-Weighted Drawdown"],
                count_columns=["Proxy Count"],
            )
            dataframe_with_empty_state(top_proxy_vol_df, "Proxy volatility detail is unavailable.")

    with drawdown_tab:
        section_header("Public Proxy Basket Drawdown", "The time-series drawdown below is for the current-weight public proxy basket.")
        _render_chart(public_proxy_drawdown_timeseries_chart(basket_history_df))
        section_header("Max Drawdown by Proxy")
        _render_chart(drawdown_chart(risk_metrics_df))
        section_header("Exposure-Weighted Drawdown by Region")
        _render_chart(risk_dimension_chart(region_risk_df, "Region", "Exposure-Weighted Drawdown", "Exposure-Weighted Drawdown by Region"))
        section_header("Exposure-Weighted Drawdown by Sector")
        _render_chart(risk_dimension_chart(sector_risk_df, "Sector", "Exposure-Weighted Drawdown", "Exposure-Weighted Drawdown by Sector"))
        if not proxy_risk_df.empty:
            section_header("Deepest Proxy Drawdowns")
            worst_proxy_dd_df = proxy_risk_df.sort_values("Exposure-Weighted Drawdown").head(15)
            worst_proxy_dd_df = format_display_dataframe(
                worst_proxy_dd_df,
                money_columns=["Signed Exposure (USD m)", "Gross Exposure (USD m)"],
                pct_columns=["Exposure % NAV", "Gross Exposure % NAV", "Exposure-Weighted Volatility", "Exposure-Weighted Drawdown"],
                count_columns=["Proxy Count"],
            )
            dataframe_with_empty_state(worst_proxy_dd_df, "Proxy drawdown detail is unavailable.")

    with stress_tab:
        section_header("Scenario Summary", "Scenario P&L is estimated from current signed exposure mapped to proxy shocks.")
        stress_summary_display_df = format_display_dataframe(
            stress_summary_df,
            money_columns=["scenario_pnl_usd_m"],
            pct_columns=["scenario_impact_pct_nav"],
            count_columns=["proxy_count", "exposure_categories"],
        )
        dataframe_with_empty_state(stress_summary_display_df, "Stress scenario summary is unavailable.")
        _render_chart(stress_scenario_impact_chart(stress_summary_df))
        section_header("Scenario Shock Inputs")
        dataframe_with_empty_state(stress_df, "Stress test results are unavailable.")
        _render_chart(stress_test_chart(stress_df))
        if not stress_summary_df.empty:
            selected_scenario = st.selectbox("Scenario Detail", stress_summary_df["scenario"].tolist(), key="risk_profile_stress_scenario")
            selected_detail_df = stress_detail_df[stress_detail_df["scenario"] == selected_scenario].copy()
            section_header("Scenario Breakdown by Proxy", f"Breakdown for `{selected_scenario}` using current mapped exposures.")
            detail_columns = [
                column
                for column in [
                    "holding_name",
                    "proxy_ticker",
                    "asset_class",
                    "region_taxonomy",
                    "gics_sector",
                    "liquidity_bucket",
                    "stress_return",
                    "scenario_pnl_usd_m",
                    "scenario_impact_pct_nav",
                ]
                if column in selected_detail_df.columns
            ]
            selected_detail_display_df = selected_detail_df[detail_columns].copy() if detail_columns else selected_detail_df.copy()
            selected_detail_display_df = format_display_dataframe(
                selected_detail_display_df,
                money_columns=["scenario_pnl_usd_m"],
                pct_columns=["stress_return", "scenario_impact_pct_nav"],
            )
            dataframe_with_empty_state(selected_detail_display_df, "Scenario detail is unavailable.")
            _render_chart(stress_scenario_breakdown_chart(selected_detail_df, "proxy_ticker", f"{selected_scenario} Impact by Proxy"))

    with correlation_tab:
        section_header("Correlation Matrix", "Correlations are computed across the mapped public proxy universe.")
        dataframe_with_empty_state(correlation_df, "Correlation matrix is unavailable.")
        _render_chart(correlation_heatmap(correlation_df))
        section_header("Top Correlation Pairs")
        top_corr_pairs_display_df = format_display_dataframe(top_corr_pairs_df, pct_columns=["Correlation"])
        dataframe_with_empty_state(top_corr_pairs_display_df, "Top correlation pairs are unavailable.")
        section_header("Proxy Exposure Summary")
        proxy_risk_display_df = format_display_dataframe(
            proxy_risk_df,
            money_columns=["Signed Exposure (USD m)", "Gross Exposure (USD m)"],
            pct_columns=["Exposure % NAV", "Gross Exposure % NAV", "Exposure-Weighted Volatility", "Exposure-Weighted Drawdown"],
            count_columns=["Proxy Count"],
        )
        dataframe_with_empty_state(proxy_risk_display_df, "Proxy exposure summary is unavailable.")


def render_workflow_controls_page():
    document_status_df = load_document_processing_status()
    ingestion_inbox_df = load_ingestion_inbox_status()
    extracted_records = load_extracted_json_records("baseline")
    review_queue_df = load_review_queue()
    validation_results_df = load_validation_results()
    extraction_accuracy_df = load_extraction_accuracy_summary("baseline")
    update_summary_markdown = load_update_summary_report()

    _render_page_header(
        "Workflow & Controls",
        "This page is the support and control layer for the portfolio dashboard. "
        "Document extraction and validation outputs are used as controlled inputs to the portfolio data layer, and pending or rejected documents do not update portfolio state.",
    )
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
        [
            "Pipeline Summary",
            "Document Ingestion",
            "Extraction Results",
            "Validation Results",
            "Review Queue",
            "Approved Updates",
        ]
    )

    with tab1:
        section_header("Pipeline Summary")
        st.write("PDF -> extraction -> validation -> approved updates -> dashboard")
        st.info(
            "State boundary: staged uploads remain in the interim inbox, the official portfolio baseline remains unchanged, "
            "and only approved workflow outputs flow into the processed overlay."
        )
        gate_cols = st.columns(3)
        with gate_cols[0]:
            metric_card("Official Baseline", "Locked")
        with gate_cols[1]:
            metric_card("Staged Uploads", f"{len(ingestion_inbox_df):,}")
        with gate_cols[2]:
            metric_card("Portfolio Update Gate", "Approved only")
        pipeline_status_summary(document_status_df)
        workflow_status_card(document_status_df)
        _render_chart(document_status_chart(document_status_df))

    with tab2:
        section_header(
            "Document Ingestion",
            "Staged uploads are managed from the separate Document Intake page. This tab shows the processed baseline document set that has already moved through the controlled workflow.",
        )
        if not ingestion_inbox_df.empty:
            st.info(
                f"{len(ingestion_inbox_df)} staged upload(s) are currently waiting in the interim inbox. "
                "Go to Document Intake to add or inspect staged PDFs before extraction."
            )
        section_header(
            "Processed Baseline Document Set",
            "These are the documents already run through the controlled extraction and validation workflow.",
        )
        columns = [
            "document_id",
            "document_type",
            "fund_name",
            "extraction_mode",
            "extraction_status",
            "source_path",
            "validation_review_status",
            "update_applied_flag",
        ]
        available = [column for column in columns if column in document_status_df.columns]
        display_document_status_df = (
            document_status_df.sort_values("document_id")
            if not document_status_df.empty and "document_id" in document_status_df.columns
            else document_status_df
        )
        dataframe_with_empty_state(
            display_document_status_df[available] if not display_document_status_df.empty else display_document_status_df,
            "Document processing status is unavailable.",
        )


    with tab3:
        section_header("Extraction Results")
        show_json_preview(extracted_records)
        section_header("Extraction Accuracy Summary")
        dataframe_with_empty_state(extraction_accuracy_df, "Extraction accuracy summary is unavailable.")

    with tab4:
        section_header("Validation Results")
        filtered_validation_df = status_filter_widget(validation_results_df, "status")
        filtered_validation_df = status_filter_widget(filtered_validation_df, "severity")
        filtered_validation_df = _sort_with_rank(
            filtered_validation_df,
            {"status": _VALIDATION_STATUS_RANK, "severity": _SEVERITY_RANK},
            ["document_id", "rule_name"],
        )
        columns = [
            "rule_name",
            "status",
            "severity",
            "message",
            "document_id",
            "document_type",
            "fund_name",
        ]
        available = [column for column in columns if column in filtered_validation_df.columns]
        dataframe_with_empty_state(
            filtered_validation_df[available] if not filtered_validation_df.empty else filtered_validation_df,
            "Validation results are unavailable.",
        )

    with tab5:
        section_header("Review Queue", "Blocked documents do not update portfolio state.")
        st.warning("Human review is the control gate. Documents in review or rejected status remain blocked from portfolio updates.")
        display_review_queue_df = _sort_with_rank(
            review_queue_df,
            {"highest_severity": _SEVERITY_RANK},
            ["document_id"],
        )
        if not display_review_queue_df.empty and "issue_count" in display_review_queue_df.columns:
            display_review_queue_df = display_review_queue_df.sort_values(
                by=["highest_severity", "issue_count", "document_id"],
                ascending=[True, False, True],
            )
        dataframe_with_empty_state(display_review_queue_df, "No review queue entries are available.")
        if not review_queue_df.empty:
            _render_chart(review_status_chart(review_queue_df))

    with tab6:
        section_header("Approved Updates", "Only approved documents become portfolio overlay updates.")
        applied_df = document_status_df
        if not applied_df.empty and "update_applied_flag" in applied_df.columns:
            applied_df = applied_df[applied_df["update_applied_flag"] == True]  # noqa: E712
        if not applied_df.empty and "document_id" in applied_df.columns:
            applied_df = applied_df.sort_values("document_id")
        dataframe_with_empty_state(applied_df, "No approved updates are currently available.")

        section_header("Blocked Documents", "These records stay out of the portfolio state until they are resolved and approved.")
        blocked_df = document_status_df
        if not blocked_df.empty and "update_applied_flag" in blocked_df.columns:
            blocked_df = blocked_df[blocked_df["update_applied_flag"] == False]  # noqa: E712
        blocked_df = _sort_with_rank(
            blocked_df,
            {"validation_review_status": {"rejected": 0, "needs_review": 1, "approved": 2}},
            ["document_id"],
        )
        dataframe_with_empty_state(blocked_df, "No blocked documents are present.")

        if update_summary_markdown:
            with st.expander("Update Summary Report", expanded=False):
                st.markdown(update_summary_markdown)
        else:
            markdown_report_preview(None, "Update Summary Report")


def render_document_intake_page():
    document_status_df = load_document_processing_status()
    _render_page_header(
        "Document Intake",
        "Operational staging area for new PDF uploads. Files land in interim storage first and remain outside portfolio state until offline extraction, validation, and approval are completed.",
    )
    synthetic_data_notice()
    _render_demo_state_status_bar()
    st.info(
        "This page is the interaction layer for document intake. Uploads are staged into the interim inbox first, then move into portfolio state only after processing and approval."
    )
    _render_demo_checklist()
    inbox_df = _render_document_ingestion_panel(
        form_key="document_intake_upload_form",
        section_title="Stage New PDF Documents",
        section_subtitle="Use this page for interactive PDF intake. Uploaded files are stored in data/interim/document_ingestion/uploaded_pdfs and await offline extraction and review.",
        show_processed_baseline=False,
        document_status_df=document_status_df,
    )
    if inbox_df.empty:
        st.caption("Upload files above to populate the staged inbox, then continue here to update the portfolio state and market-linked pages.")
    _render_intake_processing_panel()
    manual_review_message = st.session_state.get("manual_review_message")
    if manual_review_message:
        st.success(manual_review_message)
    _render_manual_review_panel()
    _render_market_data_refresh_panel()
    _render_processed_baseline_documents(document_status_df)
    _render_demo_reset_panel()


def main():
    st.set_page_config(
        page_title="Family Office Portfolio Dashboard",
        page_icon="",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    _inject_dashboard_theme()

    pages = {
        "Overview": render_overview_page,
        "Asset Class": render_asset_class_page,
        "Region & Currency": render_region_currency_page,
        "Public Markets": render_public_markets_page,
        "Private Markets": render_private_markets_page,
        "Liquidity & Commitments": render_liquidity_commitments_page,
        "Risk Profile": render_risk_profile_page,
        "Document Intake": render_document_intake_page,
        "Workflow & Controls": render_workflow_controls_page,
    }

    selected_page = _render_sidebar_navigation(list(pages.keys()))
    pages[selected_page]()


if __name__ == "__main__":
    main()
