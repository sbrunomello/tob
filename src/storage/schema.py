"""SQLite schema creation."""
from __future__ import annotations

import sqlite3

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS candles (
  exchange TEXT NOT NULL,
  symbol TEXT NOT NULL,
  timeframe TEXT NOT NULL,
  open_time_ms INTEGER NOT NULL,
  open REAL NOT NULL,
  high REAL NOT NULL,
  low REAL NOT NULL,
  close REAL NOT NULL,
  volume REAL NOT NULL,
  close_time_ms INTEGER NOT NULL,
  PRIMARY KEY (exchange, symbol, timeframe, open_time_ms)
);

CREATE TABLE IF NOT EXISTS universe_daily (
  day TEXT PRIMARY KEY,
  symbols_json TEXT NOT NULL,
  meta_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS btc_state (
  time_ms INTEGER PRIMARY KEY,
  state TEXT NOT NULL,
  meta_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS market_quality (
  time_ms INTEGER NOT NULL,
  symbol TEXT NOT NULL,
  score INTEGER NOT NULL,
  meta_json TEXT NOT NULL,
  PRIMARY KEY (time_ms, symbol)
);

CREATE TABLE IF NOT EXISTS signals (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  symbol TEXT NOT NULL,
  timeframe TEXT NOT NULL,
  signal_time_ms INTEGER NOT NULL,
  type TEXT NOT NULL,
  price REAL NOT NULL,
  confidence REAL NOT NULL,
  reasons_json TEXT NOT NULL,
  created_at_ms INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS trades_simulated (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  signal_id INTEGER NOT NULL,
  direction TEXT NOT NULL,
  entry_price REAL NOT NULL,
  stop_price REAL NOT NULL,
  take_price REAL NOT NULL,
  status TEXT NOT NULL,
  exit_time_ms INTEGER,
  exit_price REAL,
  pnl_pct REAL,
  fees_estimate REAL,
  meta_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS positions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  symbol TEXT NOT NULL,
  direction TEXT NOT NULL,
  entry_price REAL NOT NULL,
  qty REAL NOT NULL,
  leverage INTEGER NOT NULL,
  status TEXT NOT NULL,
  opened_at_ms INTEGER NOT NULL,
  updated_at_ms INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS strategy_performance (
  strategy_name TEXT NOT NULL,
  symbol TEXT NOT NULL,
  window_trades INTEGER NOT NULL,
  expectancy REAL NOT NULL,
  winrate REAL NOT NULL,
  dd REAL NOT NULL,
  enabled INTEGER NOT NULL,
  updated_at_ms INTEGER NOT NULL,
  PRIMARY KEY (strategy_name, symbol)
);

CREATE TABLE IF NOT EXISTS metrics_daily (
  day TEXT PRIMARY KEY,
  trades_count INTEGER NOT NULL,
  winrate REAL NOT NULL,
  expectancy REAL NOT NULL,
  max_drawdown REAL NOT NULL,
  updated_at_ms INTEGER NOT NULL
);
"""


def create_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA_SQL)
    conn.commit()

