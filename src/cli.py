"""Command-line interface."""
from __future__ import annotations

import argparse
from datetime import datetime

import pandas as pd

from config.settings import Settings
from observability.report import generate_daily_report
from runner import TradingRunner, run_live


def _dummy_df() -> pd.DataFrame:
    data = {
        "open_time_ms": list(range(0, 60 * 15 * 1000 * 60, 15 * 60 * 1000)),
        "open": [100 + i * 0.1 for i in range(60)],
        "high": [100 + i * 0.12 for i in range(60)],
        "low": [100 + i * 0.08 for i in range(60)],
        "close": [100 + i * 0.1 for i in range(60)],
        "volume": [1000] * 60,
    }
    return pd.DataFrame(data)


def run_command(_: argparse.Namespace) -> None:
    settings = Settings.load()
    runner = TradingRunner(settings)
    df = _dummy_df()
    runner.run_once("BTC/USDT", df, df)


def backtest_command(_: argparse.Namespace) -> None:
    print("Backtest is not implemented in this minimal scaffold yet.")


def report_command(_: argparse.Namespace) -> None:
    report = generate_daily_report({"trades": 0}, {"strategies": []})
    print(report)


def universe_command(_: argparse.Namespace) -> None:
    print("Universe generation requires live exchange data.")


def healthcheck_command(_: argparse.Namespace) -> None:
    print(f"OK - {datetime.utcnow().isoformat()}Z")


def _parse_symbols(raw: str | None) -> list[str] | None:
    if not raw:
        return None
    return [symbol.strip() for symbol in raw.split(",") if symbol.strip()]


def run_live_command(args: argparse.Namespace) -> None:
    settings = Settings.load()
    run_live(
        symbols=_parse_symbols(args.symbols),
        max_symbols=args.max_symbols,
        once=args.once,
        loop_seconds=args.loop_seconds,
        timeframe=args.timeframe,
        settings=settings,
    )


def main() -> None:
    settings = Settings.load()
    parser = argparse.ArgumentParser(description="TOB trading platform")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("run")
    sub.add_parser("backtest")
    sub.add_parser("report")
    sub.add_parser("universe")
    sub.add_parser("healthcheck")
    run_live_parser = sub.add_parser("run-live")
    run_live_parser.add_argument("--symbols", help="Symbols CSV, e.g. BTC/USDT,ETH/USDT", default=None)
    run_live_parser.add_argument("--max-symbols", type=int, default=settings.universe.max_symbols)
    run_live_parser.add_argument("--once", action="store_true", help="Run a single cycle and exit")
    run_live_parser.add_argument("--loop-seconds", type=int, default=settings.live.loop_seconds)
    run_live_parser.add_argument("--timeframe", default=settings.live.timeframe)

    args = parser.parse_args()
    if args.command == "run":
        run_command(args)
    elif args.command == "backtest":
        backtest_command(args)
    elif args.command == "report":
        report_command(args)
    elif args.command == "universe":
        universe_command(args)
    elif args.command == "healthcheck":
        healthcheck_command(args)
    elif args.command == "run-live":
        run_live_command(args)


if __name__ == "__main__":
    main()
