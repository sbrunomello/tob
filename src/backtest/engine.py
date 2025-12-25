"""Simple backtest engine for historical candles.

This module provides a lightweight, single-candle backtest that reuses the
existing signal generation and paper execution logic. It is intentionally
conservative and does not attempt to model multi-candle position management.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import pandas as pd
from loguru import logger

from config.settings import Settings
from data.btc_state import detect_btc_state
from execution.paper import simulate_trade
from market.quality import market_quality_score
from market.regime import detect_regime
from risk.adaptive import AdaptiveState, adjust_risk
from risk.sizing import position_size
from risk.stops import atr_stops
from storage.repo import SQLiteRepository
from strategy.breakout_donchian import BreakoutDonchianStrategy
from strategy.ensemble import ensemble
from strategy.indicators import atr
from strategy.mean_reversion_bb import MeanReversionBBStrategy
from strategy.trend_ema import TrendEmaStrategy


@dataclass
class BacktestTrade:
    """Represents a single simulated trade in the backtest."""

    time_ms: int
    symbol: str
    direction: str
    entry_price: float
    stop_price: float
    take_price: float
    status: str
    pnl_pct: float | None


@dataclass
class BacktestSummary:
    """Aggregated results for the backtest run."""

    total_trades: int
    closed_trades: int
    winrate: float
    expectancy: float
    max_drawdown: float


@dataclass
class BacktestResult:
    """Full backtest output, including summary and individual trades."""

    summary: BacktestSummary
    trades: list[BacktestTrade]


def _rows_to_df(rows: Iterable[object]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame([dict(row) for row in rows])
    return df.sort_values("open_time_ms").reset_index(drop=True)


def _calculate_drawdown(pnls: list[float]) -> float:
    if not pnls:
        return 0.0
    cumulative = []
    running = 0.0
    for pnl in pnls:
        running += pnl
        cumulative.append(running)
    peak = cumulative[0]
    max_dd = 0.0
    for value in cumulative:
        peak = max(peak, value)
        max_dd = min(max_dd, value - peak)
    return float(abs(max_dd))


def run_backtest(
    symbol: str,
    timeframe: str,
    *,
    settings: Settings,
    repo: SQLiteRepository,
    limit: int = 1000,
    min_window: int = 100,
) -> BacktestResult:
    """Run a simple single-candle backtest over stored candle data."""
    rows = repo.fetch_candles(symbol, timeframe, limit=limit)
    df = _rows_to_df(rows)
    if df.empty or len(df) < min_window:
        logger.warning("backtest_empty symbol={} timeframe={} rows={}", symbol, timeframe, len(df))
        return BacktestResult(
            summary=BacktestSummary(
                total_trades=0,
                closed_trades=0,
                winrate=0.0,
                expectancy=0.0,
                max_drawdown=0.0,
            ),
            trades=[],
        )

    btc_rows = repo.fetch_candles("BTC/USDT", timeframe, limit=limit)
    btc_df = _rows_to_df(btc_rows)
    if btc_df.empty:
        btc_df = df.copy()

    strategies = [
        TrendEmaStrategy(),
        BreakoutDonchianStrategy(),
        MeanReversionBBStrategy(),
    ]
    adaptive_state = AdaptiveState()

    trades: list[BacktestTrade] = []
    for idx in range(min_window, len(df)):
        window = df.iloc[: idx + 1]
        last_time = int(window.iloc[-1]["open_time_ms"])
        btc_window = btc_df[btc_df["open_time_ms"] <= last_time]
        if btc_window.empty:
            btc_window = window

        regime = detect_regime(window)
        btc_state = detect_btc_state(btc_window, settings.btc_state)
        quality = market_quality_score(window, 0.001, 1e8, settings.market_quality)
        decision = ensemble(
            symbol,
            window,
            strategies,
            regime.regime,
            btc_state.state,
            quality.score,
            settings,
        )
        if decision.signal.direction == "NONE":
            continue

        atr_value = float(atr(window, 14).iloc[-1])
        stops = atr_stops(
            entry=float(decision.signal.price),
            atr_value=atr_value,
            direction=decision.signal.direction,
            stop_mult=settings.risk.stop_atr_mult,
            take_mult=settings.risk.take_atr_mult,
        )
        risk_pct = adjust_risk(settings.risk.risk_per_trade_pct, adaptive_state)
        position_size(1000.0, risk_pct, decision.signal.price, stops.stop)

        candle = window.iloc[-1]
        trade_result = simulate_trade(
            decision.signal.direction,
            float(decision.signal.price),
            stops.stop,
            stops.take,
            candle_high=float(candle["high"]),
            candle_low=float(candle["low"]),
            fee_rate=settings.risk.fee_rate,
            worst_case_same_candle=settings.execution.worst_case_same_candle,
        )
        trades.append(
            BacktestTrade(
                time_ms=int(candle["close_time_ms"]),
                symbol=symbol,
                direction=decision.signal.direction,
                entry_price=float(decision.signal.price),
                stop_price=stops.stop,
                take_price=stops.take,
                status=trade_result.status,
                pnl_pct=trade_result.pnl_pct,
            )
        )

    closed_trades = [trade for trade in trades if trade.pnl_pct is not None]
    wins = [trade for trade in closed_trades if trade.pnl_pct and trade.pnl_pct > 0]
    winrate = float(len(wins) / len(closed_trades)) if closed_trades else 0.0
    expectancy = float(
        sum(trade.pnl_pct for trade in closed_trades if trade.pnl_pct is not None) / len(closed_trades)
    ) if closed_trades else 0.0
    drawdown = _calculate_drawdown([trade.pnl_pct or 0.0 for trade in closed_trades])

    summary = BacktestSummary(
        total_trades=len(trades),
        closed_trades=len(closed_trades),
        winrate=winrate,
        expectancy=expectancy,
        max_drawdown=drawdown,
    )
    return BacktestResult(summary=summary, trades=trades)
