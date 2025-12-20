"""Position sizing based on risk per trade."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PositionSize:
    qty: float
    risk_amount: float


def position_size(equity: float, risk_pct: float, entry: float, stop: float) -> PositionSize:
    risk_amount = equity * risk_pct
    risk_per_unit = abs(entry - stop)
    if risk_per_unit == 0:
        return PositionSize(0.0, risk_amount)
    qty = risk_amount / risk_per_unit
    return PositionSize(qty=qty, risk_amount=risk_amount)

