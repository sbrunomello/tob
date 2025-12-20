"""Basic performance metrics."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class PerformanceMetrics:
    winrate: float
    expectancy: float
    max_drawdown: float
    sharpe: float


def compute_metrics(pnls: list[float]) -> PerformanceMetrics:
    if not pnls:
        return PerformanceMetrics(0.0, 0.0, 0.0, 0.0)
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]
    winrate = len(wins) / len(pnls)
    expectancy = float(np.mean(pnls))
    cumulative = np.cumsum(pnls)
    peak = np.maximum.accumulate(cumulative)
    drawdown = float(np.min(cumulative - peak)) if len(cumulative) > 0 else 0.0
    sharpe = float(np.mean(pnls) / (np.std(pnls) + 1e-9))
    return PerformanceMetrics(winrate, expectancy, drawdown, sharpe)

