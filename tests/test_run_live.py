from __future__ import annotations

import sqlite3
import time
from typing import Any, Iterable

from config.settings import Settings
from exchange.base import ExchangeClient
from runner import run_live


class MockExchange(ExchangeClient):
    def __init__(self, ohlcv_data: dict[str, list[list[float]]], tickers: dict[str, Any]) -> None:
        self.ohlcv_data = ohlcv_data
        self.tickers = tickers
        self.create_order_called = False

    def fetch_ohlcv(self, symbol: str, timeframe: str, limit: int = 300) -> list[list[float]]:
        return self.ohlcv_data.get(symbol, [])[-limit:]

    def fetch_tickers(self) -> dict[str, Any]:
        return self.tickers

    def fetch_markets(self) -> Iterable[dict[str, Any]]:
        return [
            {
                "symbol": symbol,
                "quote": "USDT",
                "contract": True,
                "linear": True,
                "active": True,
            }
            for symbol in self.ohlcv_data.keys()
        ]

    def create_order(self, symbol: str, side: str, amount: float, price: float | None) -> Any:
        self.create_order_called = True
        raise AssertionError("Real order should never be created in run-live paper mode.")

    def set_leverage(self, symbol: str, leverage: int) -> None:
        return None


def _make_ohlcv(symbol: str, candles: int = 50, timeframe_minutes: int = 15) -> list[list[float]]:
    now_ms = int(time.time() * 1000)
    start_ms = now_ms - candles * timeframe_minutes * 60 * 1000
    rows = []
    price = 100.0 if symbol == "BTC/USDT" else 50.0
    for i in range(candles):
        open_time = start_ms + i * timeframe_minutes * 60 * 1000
        open_price = price + i * 0.1
        close_price = open_price + 0.05
        high = close_price + 0.1
        low = open_price - 0.1
        volume = 1000 + i
        rows.append([open_time, open_price, high, low, close_price, volume])
    return rows


def test_run_live_once_persists_candles_and_signal(tmp_path: Any) -> None:
    symbol = "BTC/USDT"
    ohlcv = {symbol: _make_ohlcv(symbol)}
    exchange = MockExchange(
        ohlcv_data=ohlcv,
        tickers={symbol: {"bid": 100.0, "ask": 100.1, "quoteVolume": 100000}},
    )

    settings = Settings.load()
    settings.db_path = tmp_path / "test.sqlite"
    settings.data_dir = tmp_path
    settings.live.candle_limit = 50

    run_live(
        symbols=[symbol],
        once=True,
        settings=settings,
        exchange=exchange,
    )

    conn = sqlite3.connect(settings.db_path)
    candles = conn.execute("SELECT COUNT(*) FROM candles").fetchone()[0]
    signals = conn.execute("SELECT COUNT(*) FROM signals").fetchone()[0]
    conn.close()

    assert candles > 0
    assert signals > 0


def test_run_live_never_executes_real_trades(tmp_path: Any) -> None:
    symbol = "BTC/USDT"
    ohlcv = {symbol: _make_ohlcv(symbol)}
    exchange = MockExchange(
        ohlcv_data=ohlcv,
        tickers={symbol: {"bid": 100.0, "ask": 100.1, "quoteVolume": 100000}},
    )

    settings = Settings.load()
    settings.db_path = tmp_path / "test.sqlite"
    settings.data_dir = tmp_path
    settings.live.candle_limit = 50
    settings.execute_real_trades = True
    settings.execution.execute_real_trades = True

    run_live(
        symbols=[symbol],
        once=True,
        settings=settings,
        exchange=exchange,
    )

    assert exchange.create_order_called is False
