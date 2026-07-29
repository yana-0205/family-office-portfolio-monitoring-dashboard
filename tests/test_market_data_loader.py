from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.risk import market_data_loader
from src.risk.market_data_loader import (
    _normalize_yahoo_ticker,
    fetch_market_prices_from_yfinance,
    get_proxy_tickers,
    load_market_prices,
    load_synthetic_public_prices,
)


def test_market_data_loader_handles_missing_real_data_gracefully() -> None:
    result = load_market_prices(prefer_real=True)
    assert "prices" in result
    assert "metadata" in result
    assert "coverage_ratio" in result["metadata"]


def test_synthetic_fallback_works_if_synthetic_public_prices_exist() -> None:
    result = load_synthetic_public_prices()
    assert not result["prices"].empty
    assert result["metadata"]["data_source"] == "synthetic"


def test_load_market_prices_falls_back_when_real_coverage_is_too_low(monkeypatch) -> None:
    real_result = {
        "prices": pd.DataFrame({"date": ["2026-01-31"], "ticker": ["SPY"], "close": [600.0]}),
        "metadata": {"data_source": "real", "coverage_ratio": 0.1},
    }
    synthetic_result = {
        "prices": pd.DataFrame({"date": ["2026-01-31"], "ticker": ["SYN"], "close": [100.0]}),
        "metadata": {"data_source": "synthetic"},
    }

    monkeypatch.setattr(market_data_loader, "load_real_market_prices", lambda: real_result)
    monkeypatch.setattr(market_data_loader, "load_synthetic_public_prices", lambda: synthetic_result)

    result = load_market_prices(prefer_real=True, minimum_real_coverage=0.8)

    assert result["metadata"]["data_source"] == "synthetic"


def test_get_proxy_tickers_returns_values_from_proxy_map() -> None:
    tickers = get_proxy_tickers()
    assert tickers
    assert all(isinstance(ticker, str) for ticker in tickers)


def test_normalize_yahoo_ticker_preserves_exchange_suffixes() -> None:
    assert _normalize_yahoo_ticker("BRK.B") == "BRK-B"
    assert _normalize_yahoo_ticker("2800.HK") == "2800.HK"


def test_fetch_market_prices_from_yfinance_writes_csv(monkeypatch, tmp_path: Path) -> None:
    class FakeTicker:
        def __init__(self, ticker: str) -> None:
            self.ticker = ticker

        def history(
            self,
            start: str | None = None,
            end: str | None = None,
            interval: str | None = None,
            auto_adjust: bool | None = None,
            actions: bool | None = None,
        ) -> pd.DataFrame:
            return pd.DataFrame(
                {
                    "Date": pd.to_datetime(["2026-01-31", "2026-02-28"]),
                    "Close": [100.0, 101.5],
                }
            )

    class FakeYFinance:
        @staticmethod
        def Ticker(ticker: str) -> FakeTicker:
            return FakeTicker(ticker)

        @staticmethod
        def download(tickers, **kwargs) -> pd.DataFrame:
            return pd.DataFrame(
                [[510.0]],
                index=pd.to_datetime(["2026-05-29"]),
                columns=pd.MultiIndex.from_tuples([("Close", "QQQ")]),
            )

    monkeypatch.setitem(__import__("sys").modules, "yfinance", FakeYFinance())
    monkeypatch.setattr(market_data_loader, "MARKET_PRICES_DIR", tmp_path)

    result = fetch_market_prices_from_yfinance(
        tickers=["SPY", "QQQ"],
        start_date="2026-01-01",
        interval="1mo",
        output_filename="test_prices.csv",
    )

    assert result["metadata"]["provider"] == "yfinance"
    assert result["metadata"]["requested_tickers"] == ["SPY", "QQQ"]
    assert result["metadata"]["failed_tickers"] == []
    assert result["metadata"]["coverage_ratio"] == 1.0
    assert result["output_path"] == tmp_path / "test_prices.csv"
    assert result["output_path"].exists()
    written = pd.read_csv(result["output_path"])
    assert set(written["ticker"]) == {"SPY", "QQQ"}


def test_fetch_market_prices_merges_fresh_rows_with_existing_tickers(monkeypatch, tmp_path: Path) -> None:
    class FakeTicker:
        def __init__(self, ticker: str) -> None:
            self.ticker = ticker

        def history(self, **kwargs) -> pd.DataFrame:
            if self.ticker == "QQQ":
                return pd.DataFrame()
            return pd.DataFrame({"Date": pd.to_datetime(["2026-05-01"]), "Close": [610.0]})

    class FakeYFinance:
        @staticmethod
        def Ticker(ticker: str) -> FakeTicker:
            return FakeTicker(ticker)

        @staticmethod
        def download(tickers, **kwargs) -> pd.DataFrame:
            return pd.DataFrame(
                [[510.0]],
                index=pd.to_datetime(["2026-05-29"]),
                columns=pd.MultiIndex.from_tuples([("Close", "QQQ")]),
            )

    output_path = tmp_path / "prices.csv"
    pd.DataFrame(
        {
            "date": ["2026-04-30", "2026-04-30"],
            "ticker": ["SPY", "QQQ"],
            "close": [600.0, 500.0],
        }
    ).to_csv(output_path, index=False)
    monkeypatch.setitem(__import__("sys").modules, "yfinance", FakeYFinance())
    monkeypatch.setattr(market_data_loader, "MARKET_PRICES_DIR", tmp_path)

    result = fetch_market_prices_from_yfinance(
        tickers=["SPY", "QQQ"],
        start_date="2026-04-01",
        end_date="2026-06-01",
        interval="1mo",
        output_filename="prices.csv",
        max_retries=1,
    )

    written = pd.read_csv(output_path)
    assert set(written["ticker"]) == {"SPY", "QQQ"}
    assert "2026-05-31" in written.loc[written["ticker"] == "SPY", "date"].tolist()
    assert result["metadata"]["end_date"] == "2026-05-31"
    assert result["metadata"]["coverage_ratio"] == 1.0
    assert result["metadata"]["failed_tickers"] == []
