from __future__ import annotations

from pathlib import Path

from src.config import REPORTS_DIR, RISK_OUTPUTS_DIR
from src.risk.market_data_loader import load_market_prices, load_proxy_map
from src.risk.risk_metrics import (
    calculate_annualized_volatility,
    calculate_correlation_matrix,
    calculate_max_drawdown,
    calculate_returns,
    run_simple_stress_tests,
)


def run() -> dict[str, object]:
    RISK_OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    proxy_map_df = load_proxy_map()
    market_data = load_market_prices(prefer_real=True)
    price_df = market_data["prices"]
    metadata = market_data["metadata"]

    returns_df = calculate_returns(price_df)
    vol_df = calculate_annualized_volatility(returns_df)
    drawdown_df = calculate_max_drawdown(price_df)
    correlation_df = calculate_correlation_matrix(returns_df)
    stress_df = run_simple_stress_tests(returns_df, proxy_map_df=proxy_map_df)

    metrics_df = vol_df.merge(drawdown_df, on="ticker", how="outer")
    metrics_df["data_source"] = metadata["data_source"]
    metrics_df["start_date"] = metadata["start_date"]
    metrics_df["end_date"] = metadata["end_date"]

    risk_metrics_path = RISK_OUTPUTS_DIR / "public_risk_metrics.csv"
    correlation_path = RISK_OUTPUTS_DIR / "correlation_matrix.csv"
    stress_path = RISK_OUTPUTS_DIR / "stress_test_results.csv"
    report_path = REPORTS_DIR / "public_market_risk_summary.md"

    metrics_df.to_csv(risk_metrics_path, index=False)
    correlation_df.to_csv(correlation_path)
    stress_df.to_csv(stress_path, index=False)

    report_lines = [
        "# Public Market Risk Summary",
        "",
        f"- Data source used: `{metadata['data_source']}`",
        f"- Source files: `{', '.join(metadata['source_files']) if metadata['source_files'] else 'None'}`",
        f"- Tickers processed: `{', '.join(metadata['tickers']) if metadata['tickers'] else 'None'}`",
        f"- Date range: `{metadata['start_date']} -> {metadata['end_date']}`",
        "",
        "## Outputs",
        "",
        f"- `{risk_metrics_path}`",
        f"- `{correlation_path}`",
        f"- `{stress_path}`",
        "",
        "## Notes",
        "",
        "- This module monitors public-market proxy risk only.",
        "- If real market files are absent, synthetic price seeds are used and should be treated as illustrative only.",
        "- This is not investment advice.",
    ]
    report_path.write_text("\n".join(report_lines), encoding="utf-8")

    return {
        "data_source": metadata["data_source"],
        "tickers": metadata["tickers"],
        "date_range": (metadata["start_date"], metadata["end_date"]),
        "output_files": [risk_metrics_path, correlation_path, stress_path, report_path],
    }


def main() -> int:
    results = run()
    print(
        f"data_source={results['data_source']} tickers={len(results['tickers'])} "
        f"date_range={results['date_range'][0]}:{results['date_range'][1]} outputs={len(results['output_files'])}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
