import importlib

import pandas as pd

from src.risk.risk_metrics import (
    calculate_annualized_volatility,
    calculate_correlation_matrix,
    calculate_max_drawdown,
    calculate_returns,
    run_simple_stress_tests,
)


def _sample_prices():
    return pd.DataFrame(
        {
            "date": pd.to_datetime(["2024-01-31", "2024-02-29", "2024-03-31", "2024-01-31", "2024-02-29", "2024-03-31"]),
            "ticker": ["AAA", "AAA", "AAA", "BBB", "BBB", "BBB"],
            "close": [100.0, 110.0, 105.0, 50.0, 52.0, 51.0],
        }
    )


def test_calculate_returns_works_on_simple_price_series() -> None:
    returns = calculate_returns(_sample_prices())
    assert not returns.empty
    assert "return" in returns.columns


def test_annualized_volatility_is_non_negative() -> None:
    returns = calculate_returns(_sample_prices())
    vol = calculate_annualized_volatility(returns)
    assert (vol["annualized_volatility"] >= 0).all()


def test_max_drawdown_is_less_than_or_equal_to_zero() -> None:
    drawdown = calculate_max_drawdown(_sample_prices())
    assert (drawdown["max_drawdown"] <= 0).all()


def test_correlation_matrix_is_square() -> None:
    returns = calculate_returns(_sample_prices())
    corr = calculate_correlation_matrix(returns)
    assert corr.shape[0] == corr.shape[1]


def test_stress_test_output_is_not_empty() -> None:
    returns = calculate_returns(_sample_prices())
    stress = run_simple_stress_tests(returns)
    assert not stress.empty


def test_run_risk_can_be_imported_without_side_effects() -> None:
    module = importlib.import_module("src.risk.run_risk")
    assert hasattr(module, "run")
    assert hasattr(module, "main")
