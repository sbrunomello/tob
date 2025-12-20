"""Confluence engine for multiple strategies."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

import pandas as pd

from strategy.base import Signal, Strategy


@dataclass
class EnsembleDecision:
    signal: Signal
    votes: dict[str, str]
    reasons: dict[str, Any]


def _filter_strategies(
    strategies: Iterable[Strategy],
    regime: str,
    btc_state: str,
    mqs: int,
) -> list[Strategy]:
    if mqs < 50 or regime == "CHAOTIC":
        return []
    allowed = []
    for strat in strategies:
        if strat.name == "mean_reversion_bb" and regime != "RANGE":
            continue
        if strat.name in {"trend_ema", "breakout_donchian"} and btc_state in {"SQUEEZE", "CHOP"}:
            continue
        allowed.append(strat)
    return allowed


def _strategy_settings(settings: Any, name: str) -> Any:
    """Return the per-strategy settings block from either Settings or StrategySettings."""
    # Support both the top-level Settings (settings.strategy.*) and direct StrategySettings
    # to avoid attribute errors when callers pass the full Settings object.
    strategy_settings = getattr(settings, "strategy", settings)
    if name == "trend_ema":
        return strategy_settings.trend
    if name == "breakout_donchian":
        return strategy_settings.breakout
    if name == "mean_reversion_bb":
        return strategy_settings.mean_reversion
    return strategy_settings


def ensemble(
    symbol: str,
    df: pd.DataFrame,
    strategies: list[Strategy],
    regime: str,
    btc_state: str,
    mqs: int,
    settings: Any,
) -> EnsembleDecision:
    allowed = _filter_strategies(strategies, regime, btc_state, mqs)
    votes: dict[str, str] = {}
    reasons: dict[str, Any] = {
        "regime": regime,
        "btc_state": btc_state,
        "mqs": mqs,
    }

    if not allowed:
        signal = Signal(symbol, "NONE", float(df["close"].iloc[-1]), 0.0, reasons)
        return EnsembleDecision(signal, votes, reasons)

    for strat in allowed:
        strat_settings = _strategy_settings(settings, strat.name)
        result = strat.generate(symbol, df, strat_settings)
        votes[strat.name] = result.direction
        reasons[strat.name] = result.reasons

    long_votes = sum(1 for v in votes.values() if v == "LONG")
    short_votes = sum(1 for v in votes.values() if v == "SHORT")
    total = len(votes)

    required = 2 if total >= 3 else total
    if 50 <= mqs < settings.market_quality.min_trade_score:
        required = total

    direction = "NONE"
    if long_votes >= required and long_votes > short_votes:
        direction = "LONG"
    elif short_votes >= required and short_votes > long_votes:
        direction = "SHORT"

    confidence = max(long_votes, short_votes) / total if total else 0.0
    signal = Signal(symbol, direction, float(df["close"].iloc[-1]), confidence, reasons)
    return EnsembleDecision(signal, votes, reasons)
