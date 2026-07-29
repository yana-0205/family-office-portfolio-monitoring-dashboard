from pathlib import Path

import importlib
import pandas as pd

prepare_upload_test_state = importlib.import_module("src.testing.prepare_upload_test_state")


def test_prepare_upload_test_state_resets_outputs(tmp_path: Path, monkeypatch) -> None:
    processed_dir = tmp_path / "processed"
    outputs_dir = tmp_path / "outputs"
    reports_dir = outputs_dir / "reports"
    risk_outputs_dir = outputs_dir / "risk"
    validation_dir = outputs_dir / "validation"
    extracted_intake_dir = outputs_dir / "extracted_json" / "intake"
    ingestion_files_dir = tmp_path / "interim" / "uploaded_pdfs"
    ingestion_manifest_path = tmp_path / "interim" / "ingestion_inbox.csv"
    csv_dir = tmp_path / "csv"
    market_prices_dir = tmp_path / "market_prices"
    review_decisions_path = tmp_path / "interim" / "manual_review_decisions.csv"

    processed_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)
    risk_outputs_dir.mkdir(parents=True, exist_ok=True)
    validation_dir.mkdir(parents=True, exist_ok=True)
    extracted_intake_dir.mkdir(parents=True, exist_ok=True)
    ingestion_files_dir.mkdir(parents=True, exist_ok=True)
    csv_dir.mkdir(parents=True, exist_ok=True)
    market_prices_dir.mkdir(parents=True, exist_ok=True)
    (processed_dir / "stale.csv").write_text("x\n1\n", encoding="utf-8")
    (reports_dir / "update_summary.md").write_text("stale", encoding="utf-8")
    (validation_dir / "validation_results_actual.csv").write_text("stale", encoding="utf-8")
    (extracted_intake_dir / "old.json").write_text("{}", encoding="utf-8")
    (ingestion_files_dir / "old.pdf").write_bytes(b"%PDF old")
    pd.DataFrame(
        [
            {
                "document_id": "PDF_001",
                "extraction_mode": "intake",
                "manual_review_status": "approved",
                "reviewer_note": "Old approval",
                "reviewed_at_utc": "2026-07-15T00:00:00Z",
            }
        ]
    ).to_csv(review_decisions_path, index=False)
    pd.DataFrame({"date": ["2026-04-30"]}).to_csv(csv_dir / "portfolio_monthly_summary.csv", index=False)
    pd.DataFrame({"date": ["2026-04-30", "2026-05-31"], "ticker": ["SPY", "SPY"], "close": [100.0, 110.0]}).to_csv(
        market_prices_dir / "yfinance_monthly_prices.csv",
        index=False,
    )

    monkeypatch.setattr(prepare_upload_test_state, "PROCESSED_DATA_DIR", processed_dir)
    monkeypatch.setattr(prepare_upload_test_state, "OUTPUTS_DIR", outputs_dir)
    monkeypatch.setattr(prepare_upload_test_state, "REPORTS_DIR", reports_dir)
    monkeypatch.setattr(prepare_upload_test_state, "RISK_OUTPUTS_DIR", risk_outputs_dir)
    monkeypatch.setattr(prepare_upload_test_state, "INGESTION_FILES_DIR", ingestion_files_dir)
    monkeypatch.setattr(prepare_upload_test_state, "INGESTION_MANIFEST_PATH", ingestion_manifest_path)
    monkeypatch.setattr(prepare_upload_test_state, "CSV_DIR", csv_dir)
    monkeypatch.setattr(prepare_upload_test_state, "MARKET_PRICES_DIR", market_prices_dir)
    monkeypatch.setattr(prepare_upload_test_state, "REVIEW_DECISIONS_PATH", review_decisions_path)

    monkeypatch.setattr(
        prepare_upload_test_state,
        "load_baseline_positions",
        lambda: pd.DataFrame([{"fund_id": "F1", "fund_name": "Fund One", "current_nav_usd_m": 10.0}]),
    )
    monkeypatch.setattr(
        prepare_upload_test_state,
        "load_baseline_cash_accounts",
        lambda: pd.DataFrame([{"account_name": "Cash", "balance_usd_m": 5.0}]),
    )
    def fake_run_risk_pipeline():
        risk_output_path = risk_outputs_dir / "public_risk_metrics.csv"
        risk_output_path.write_text("ticker,start_date,end_date\nSPY,2016-06-30,2026-04-30\n", encoding="utf-8")
        return {
            "output_files": [risk_output_path],
        }

    monkeypatch.setattr(prepare_upload_test_state, "run_risk_pipeline", fake_run_risk_pipeline)

    results = prepare_upload_test_state.run()

    assert Path(results["backup_root"]).exists()
    assert (processed_dir / "private_positions_post_ingestion.csv").exists()
    assert (processed_dir / "document_processing_status.csv").exists()
    assert (validation_dir / "validation_results_actual.csv").exists()
    assert (risk_outputs_dir / "public_risk_metrics.csv").exists()
    assert list(ingestion_files_dir.glob("*")) == []
    manifest_df = pd.read_csv(ingestion_manifest_path)
    assert manifest_df.empty
    assert {"review_status", "approval_source", "review_note"}.issubset(manifest_df.columns)
    review_decisions_df = pd.read_csv(review_decisions_path)
    assert review_decisions_df.empty
    market_prices_df = pd.read_csv(market_prices_dir / "yfinance_monthly_prices.csv")
    assert market_prices_df["date"].tolist() == ["2026-04-30"]
