"""Market quality scoring."""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from strategy.indicators import adx, atr


@dataclass
class QualityResult:
    score: int
    meta: dict


def _wick_ratio(df: pd.DataFrame) -> float:
    body = (df["close"] - df["open"]).abs()
    wicks = (df["high"] - df[["close", "open"]].max(axis=1)) + (
        df[["close", "open"]].min(axis=1) - df["low"]
    )
    return float((wicks / body.replace(0, 1)).tail(20).mean())


def market_quality_score(df: pd.DataFrame, spread: float, liquidity: float, settings: object) -> QualityResult:
    atr_val = atr(df, 14).iloc[-1]
    atr_pct = atr_val / df["close"].iloc[-1]
    adx_val = adx(df, 14).iloc[-1]
    wick_ratio = _wick_ratio(df)

    score = 100
    if spread > 0.002:
        score -= settings.spread_penalty
    if atr_pct < 0.003:
        score -= settings.atr_low_penalty
    if adx_val < 18:
        score -= settings.adx_low_penalty
    if wick_ratio > 2.5:
        score -= settings.wick_penalty
    if liquidity > 1e7:
        score += settings.liquidity_bonus
    if adx_val > 25:
        score += settings.direction_bonus

    score = max(0, min(100, int(score)))
    meta = {
        "atr_pct": float(atr_pct),
        "adx": float(adx_val),
        "wick_ratio": float(wick_ratio),
        "spread": float(spread),
        "liquidity": float(liquidity),
    }
    return QualityResult(score, meta)

