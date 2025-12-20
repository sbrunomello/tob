"""Adaptive risk controls."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class AdaptiveState:
    losing_streak: int = 0
    weekly_drawdown: float = 0.0
    monthly_drawdown: float = 0.0
    defensive_mode: bool = False


def adjust_risk(base_risk: float, state: AdaptiveState) -> float:
    risk = base_risk
    if state.losing_streak >= 3:
        risk *= 0.5
    if state.weekly_drawdown >= 0.1 or state.monthly_drawdown >= 0.2:
        state.defensive_mode = True
        risk *= 0.3
    return risk


def update_streak(state: AdaptiveState, pnl: float) -> None:
    if pnl < 0:
        state.losing_streak += 1
    else:
        state.losing_streak = 0

