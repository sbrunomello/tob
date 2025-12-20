"""Paper trading execution engine."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class PaperTradeResult:
    status: str
    exit_price: float | None
    pnl_pct: float | None
    fees: float
    meta: dict[str, Any]


def simulate_trade(
    direction: str,
    entry_price: float,
    stop_price: float,
    take_price: float,
    candle_high: float,
    candle_low: float,
    fee_rate: float,
    worst_case_same_candle: bool = True,
) -> PaperTradeResult:
    """Simulate trade outcome for a single candle."""
    hit_stop = candle_low <= stop_price if direction == "LONG" else candle_high >= stop_price
    hit_take = candle_high >= take_price if direction == "LONG" else candle_low <= take_price

    exit_price = None
    status = "OPEN"
    if hit_stop and hit_take:
        exit_price = stop_price if worst_case_same_candle else take_price
        status = "STOP" if worst_case_same_candle else "TAKE"
    elif hit_stop:
        exit_price = stop_price
        status = "STOP"
    elif hit_take:
        exit_price = take_price
        status = "TAKE"

    pnl_pct = None
    if exit_price is not None:
        pnl_pct = (exit_price - entry_price) / entry_price
        if direction == "SHORT":
            pnl_pct = -pnl_pct

    fees = fee_rate * 2
    return PaperTradeResult(status=status, exit_price=exit_price, pnl_pct=pnl_pct, fees=fees, meta={})

