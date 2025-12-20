"""SQLite repository helpers."""
from __future__ import annotations

import json
import sqlite3
from typing import Any, Iterable

from storage.schema import create_schema


class SQLiteRepository:
    """Thin repository for SQLite storage."""

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        self._conn = sqlite3.connect(self.db_path)
        self._conn.row_factory = sqlite3.Row
        create_schema(self._conn)

    def upsert_candles(
        self,
        exchange: str,
        symbol: str,
        timeframe: str,
        rows: Iterable[dict[str, Any]],
    ) -> None:
        with self._conn:
            self._conn.executemany(
                """
                INSERT OR REPLACE INTO candles (
                  exchange, symbol, timeframe, open_time_ms, open, high, low, close, volume, close_time_ms
                ) VALUES (
                  :exchange, :symbol, :timeframe, :open_time_ms, :open, :high, :low, :close, :volume, :close_time_ms
                )
                """,
                [
                    {
                        "exchange": exchange,
                        "symbol": symbol,
                        "timeframe": timeframe,
                        **row,
                    }
                    for row in rows
                ],
            )

    def fetch_candles(self, symbol: str, timeframe: str, limit: int = 200) -> list[sqlite3.Row]:
        cursor = self._conn.execute(
            """
            SELECT * FROM candles
            WHERE symbol = ? AND timeframe = ?
            ORDER BY open_time_ms DESC
            LIMIT ?
            """,
            (symbol, timeframe, limit),
        )
        return list(cursor.fetchall())

    def store_universe(self, day: str, symbols: list[str], meta: dict[str, Any]) -> None:
        with self._conn:
            self._conn.execute(
                """
                INSERT OR REPLACE INTO universe_daily (day, symbols_json, meta_json)
                VALUES (?, ?, ?)
                """,
                (day, json.dumps(symbols), json.dumps(meta)),
            )

    def store_btc_state(self, time_ms: int, state: str, meta: dict[str, Any]) -> None:
        with self._conn:
            self._conn.execute(
                """
                INSERT OR REPLACE INTO btc_state (time_ms, state, meta_json)
                VALUES (?, ?, ?)
                """,
                (time_ms, state, json.dumps(meta)),
            )

    def store_market_quality(self, time_ms: int, symbol: str, score: int, meta: dict[str, Any]) -> None:
        with self._conn:
            self._conn.execute(
                """
                INSERT OR REPLACE INTO market_quality (time_ms, symbol, score, meta_json)
                VALUES (?, ?, ?, ?)
                """,
                (time_ms, symbol, score, json.dumps(meta)),
            )

    def store_signal(
        self,
        symbol: str,
        timeframe: str,
        signal_time_ms: int,
        signal_type: str,
        price: float,
        confidence: float,
        reasons: dict[str, Any],
        created_at_ms: int,
    ) -> int:
        cursor = self._conn.execute(
            """
            INSERT INTO signals (symbol, timeframe, signal_time_ms, type, price, confidence, reasons_json, created_at_ms)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                symbol,
                timeframe,
                signal_time_ms,
                signal_type,
                price,
                confidence,
                json.dumps(reasons),
                created_at_ms,
            ),
        )
        self._conn.commit()
        return int(cursor.lastrowid)

    def store_trade_simulated(
        self,
        signal_id: int,
        direction: str,
        entry_price: float,
        stop_price: float,
        take_price: float,
        status: str,
        exit_time_ms: int | None,
        exit_price: float | None,
        pnl_pct: float | None,
        fees_estimate: float,
        meta: dict[str, Any],
    ) -> None:
        with self._conn:
            self._conn.execute(
                """
                INSERT INTO trades_simulated (
                  signal_id, direction, entry_price, stop_price, take_price, status, exit_time_ms,
                  exit_price, pnl_pct, fees_estimate, meta_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    signal_id,
                    direction,
                    entry_price,
                    stop_price,
                    take_price,
                    status,
                    exit_time_ms,
                    exit_price,
                    pnl_pct,
                    fees_estimate,
                    json.dumps(meta),
                ),
            )

    def store_strategy_performance(
        self,
        strategy_name: str,
        symbol: str,
        window_trades: int,
        expectancy: float,
        winrate: float,
        dd: float,
        enabled: bool,
        updated_at_ms: int,
    ) -> None:
        with self._conn:
            self._conn.execute(
                """
                INSERT OR REPLACE INTO strategy_performance (
                  strategy_name, symbol, window_trades, expectancy, winrate, dd, enabled, updated_at_ms
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    strategy_name,
                    symbol,
                    window_trades,
                    expectancy,
                    winrate,
                    dd,
                    1 if enabled else 0,
                    updated_at_ms,
                ),
            )

    def store_metrics_daily(
        self,
        day: str,
        trades_count: int,
        winrate: float,
        expectancy: float,
        max_drawdown: float,
        updated_at_ms: int,
    ) -> None:
        with self._conn:
            self._conn.execute(
                """
                INSERT OR REPLACE INTO metrics_daily (day, trades_count, winrate, expectancy, max_drawdown, updated_at_ms)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (day, trades_count, winrate, expectancy, max_drawdown, updated_at_ms),
            )

