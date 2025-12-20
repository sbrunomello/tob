"""Data collection and persistence."""
from __future__ import annotations

from typing import Any

import pandas as pd

from exchange.base import ExchangeClient
from storage.repo import SQLiteRepository


class CandleCollector:
    """Fetch and store OHLCV candles."""

    def __init__(self, exchange: ExchangeClient, repo: SQLiteRepository, exchange_name: str = "binanceusdm") -> None:
        self.exchange = exchange
        self.repo = repo
        self.exchange_name = exchange_name

    def fetch_and_store(self, symbol: str, timeframe: str, limit: int = 300) -> pd.DataFrame:
        raw = self.exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
        df = pd.DataFrame(
            raw,
            columns=["open_time_ms", "open", "high", "low", "close", "volume"],
        )
        df["close_time_ms"] = df["open_time_ms"] + 15 * 60 * 1000
        rows: list[dict[str, Any]] = df.to_dict(orient="records")
        self.repo.upsert_candles(self.exchange_name, symbol, timeframe, rows)
        return df

