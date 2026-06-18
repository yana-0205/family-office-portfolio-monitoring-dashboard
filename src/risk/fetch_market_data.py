from __future__ import annotations

import argparse

from src.risk.market_data_loader import fetch_market_prices_from_yfinance, get_proxy_tickers


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Fetch real public market proxy data.")
    parser.add_argument("--provider", default="yfinance", choices=["yfinance"])
    parser.add_argument("--start-date", default="2020-01-01")
    parser.add_argument("--end-date", default=None)
    parser.add_argument("--interval", default="1mo")
    parser.add_argument("--tickers", nargs="*", default=None, help="Optional explicit tickers. Defaults to proxy map tickers.")
    parser.add_argument("--output-filename", default="yfinance_monthly_prices.csv")
    return parser


def run(args: argparse.Namespace) -> dict[str, object]:
    tickers = args.tickers or get_proxy_tickers()
    if args.provider == "yfinance":
        return fetch_market_prices_from_yfinance(
            tickers=tickers,
            start_date=args.start_date,
            end_date=args.end_date,
            interval=args.interval,
            output_filename=args.output_filename,
        )
    raise ValueError(f"Unsupported provider: {args.provider}")


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    results = run(args)
    metadata = results["metadata"]
    output_path = results.get("output_path")
    print(
        "provider={provider} data_source={data_source} tickers={tickers} failed={failed} "
        "coverage={coverage:.0%} date_range={start}:{end} output={output}".format(
            provider=metadata.get("provider", "unknown"),
            data_source=metadata.get("data_source", "unknown"),
            tickers=len(metadata.get("tickers", [])),
            failed=len(metadata.get("failed_tickers", [])),
            coverage=metadata.get("coverage_ratio", 0.0),
            start=metadata.get("start_date"),
            end=metadata.get("end_date"),
            output=output_path,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
