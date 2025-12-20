"""Strategy performance scoring and pruning."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class StrategyPerformance:
    expectancy: float
    winrate: float
    max_drawdown: float


def compute_performance(pnls: list[float]) -> StrategyPerformance:
    if not pnls:
        return StrategyPerformance(0.0, 0.0, 0.0)
    wins = len([p for p in pnls if p > 0])
    winrate = wins / len(pnls)
    expectancy = float(np.mean(pnls))
    cumulative = np.cumsum(pnls)
    peak = np.maximum.accumulate(cumulative)
    dd = float(np.min(cumulative - peak)) if len(cumulative) else 0.0
    return StrategyPerformance(expectancy, winrate, dd)


def should_disable(expectancy: float, trades: int, min_trades: int) -> bool:
    return trades >= min_trades and expectancy < 0

