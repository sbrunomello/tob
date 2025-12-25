"""Data collection and persistence."""
from __future__ import annotations

from typing import Any

import pandas as pd
from loguru import logger

from exchange.base import ExchangeClient
from storage.repo import SQLiteRepository


class CandleCollector:
    """Fetch and store OHLCV candles."""

    def __init__(self, exchange: ExchangeClient, repo: SQLiteRepository, exchange_name: str = "binanceusdm") -> None:
        self.exchange = exchange
        self.repo = repo
        self.exchange_name = exchange_name

    @staticmethod
    def _timeframe_to_ms(timeframe: str) -> int:
        unit = timeframe[-1]
        value = int(timeframe[:-1])
        if unit == "m":
            return value * 60 * 1000
        if unit == "h":
            return value * 60 * 60 * 1000
        if unit == "d":
            return value * 24 * 60 * 60 * 1000
        raise ValueError(f"Unsupported timeframe: {timeframe}")

    def sync_candles(self, symbol: str, timeframe: str, limit: int = 300) -> int:
        """Fetch candles and upsert into SQLite. Returns number of new candles."""
        raw = self.exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
        if not raw:
            logger.warning("no_candles_fetched symbol={} timeframe={}", symbol, timeframe)
            return 0

        df = pd.DataFrame(raw, columns=["open_time_ms", "open", "high", "low", "close", "volume"])
        close_delta = self._timeframe_to_ms(timeframe)
        df["close_time_ms"] = df["open_time_ms"] + close_delta
        rows: list[dict[str, Any]] = df.to_dict(orient="records")

        last_open_time = self.repo.fetch_latest_candle_open_time(
            self.exchange_name,
            symbol,
            timeframe,
        )
        new_count = len(df) if last_open_time is None else int((df["open_time_ms"] > last_open_time).sum())
        self.repo.upsert_candles(self.exchange_name, symbol, timeframe, rows)
        return new_count

    def latest_closed_candle_open_time(self, symbol: str, timeframe: str) -> int | None:
        """Return the latest closed candle open_time_ms for a symbol/timeframe."""
        return self.repo.fetch_latest_closed_candle_open_time(self.exchange_name, symbol, timeframe)
