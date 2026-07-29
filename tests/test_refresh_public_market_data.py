from __future__ import annotations

import pandas as pd

from src.risk import refresh_public_market_data


def test_build_fetch_end_date_uses_next_month_start() -> None:
    assert refresh_public_market_data.build_fetch_end_date("2026-05-31") == "2026-06-01"
    assert refresh_public_market_data.build_fetch_end_date("2026-05-12") == "2026-06-01"


def test_infer_market_data_start_date_uses_earliest_available_csv(tmp_path, monkeypatch) -> None:
    first_path = tmp_path / "first.csv"
    second_path = tmp_path / "second.csv"
    pd.DataFrame({"date": ["2021-03-31", "2021-04-30"]}).to_csv(first_path, index=False)
    pd.DataFrame({"date": ["2020-01-31", "2020-02-29"]}).to_csv(second_path, index=False)

    monkeypatch.setattr(refresh_public_market_data, "MARKET_PRICES_DIR", tmp_path)

    assert refresh_public_market_data.infer_market_data_start_date() == "2020-01-31"


def test_refresh_public_market_data_for_month_runs_fetch_and_risk(monkeypatch) -> None:
    captured_args: dict[str, object] = {}

    def fake_run_market_fetch(args):
        captured_args["start_date"] = args.start_date
        captured_args["end_date"] = args.end_date
        captured_args["interval"] = args.interval
        captured_args["output_filename"] = args.output_filename
        price_path = __import__("pathlib").Path("/tmp/fake_prices.csv")
        pd.DataFrame(
            {"date": ["2026-05-31"], "ticker": ["SPY"], "close": [610.0]}
        ).to_csv(price_path, index=False)
        return {
            "metadata": {
                "coverage_ratio": 1.0,
                "failed_tickers": [],
                "expected_tickers": ["SPY"],
            },
            "output_path": str(price_path),
        }

    def fake_run_risk_pipeline():
        return {
            "date_range": ("2020-01-31", "2026-05-31"),
        }

    monkeypatch.setattr(refresh_public_market_data, "run_market_fetch", fake_run_market_fetch)
    monkeypatch.setattr(
        refresh_public_market_data,
        "trim_market_price_file_to_month_end",
        lambda csv_path, target_month_end: {"row_count": 100, "max_date": "2026-05-31"},
    )
    monkeypatch.setattr(refresh_public_market_data, "run_risk_pipeline", fake_run_risk_pipeline)

    results = refresh_public_market_data.refresh_public_market_data_for_month("2026-05-31")

    assert results["target_month_end"] == "2026-05-31"
    assert results["start_date"] == "2026-05-01"
    assert results["end_date"] == "2026-06-01"
    assert captured_args == {
        "start_date": "2026-05-01",
        "end_date": "2026-06-01",
        "interval": "1d",
        "output_filename": "yfinance_monthly_prices.csv",
    }
    assert results["trim"] == {"row_count": 100, "max_date": "2026-05-31"}
    assert results["verified_through"] == "2026-05-31"
    assert results["target_month_coverage"] == 1.0


def test_refresh_rejects_stale_price_result(monkeypatch) -> None:
    monkeypatch.setattr(
        refresh_public_market_data,
        "run_market_fetch",
        lambda args: {"metadata": {"coverage_ratio": 1.0}, "output_path": "/tmp/fake_prices.csv"},
    )
    monkeypatch.setattr(
        refresh_public_market_data,
        "trim_market_price_file_to_month_end",
        lambda csv_path, target_month_end: {"row_count": 100, "max_date": "2026-04-30"},
    )

    try:
        refresh_public_market_data.refresh_public_market_data_for_month("2026-05-31")
    except RuntimeError as exc:
        assert "did not reach the requested month" in str(exc)
    else:
        raise AssertionError("Expected stale market refresh to fail.")


def test_trim_market_price_file_to_month_end_removes_rows_after_target_month(tmp_path) -> None:
    csv_path = tmp_path / "prices.csv"
    pd.DataFrame(
        {
            "date": ["2026-05-01", "2026-05-31", "2026-06-01", "2026-06-12"],
            "ticker": ["SPY", "SPY", "SPY", "SPY"],
            "close": [1.0, 2.0, 3.0, 4.0],
        }
    ).to_csv(csv_path, index=False)

    results = refresh_public_market_data.trim_market_price_file_to_month_end(csv_path, "2026-05-31")
    trimmed_df = pd.read_csv(csv_path)

    assert results == {"row_count": 2, "max_date": "2026-05-31"}
    assert trimmed_df["date"].tolist() == ["2026-05-01", "2026-05-31"]
