"""Precision utilities for Binance Futures."""
from __future__ import annotations

from dataclasses import dataclass
from math import floor


@dataclass
class SymbolPrecision:
    tick_size: float
    step_size: float
    min_qty: float
    min_notional: float


def _round_step(value: float, step: float) -> float:
    if step == 0:
        return value
    return floor(value / step) * step


def normalize_price(price: float, precision: SymbolPrecision) -> float:
    """Normalize price to tick size."""
    return _round_step(price, precision.tick_size)


def normalize_qty(qty: float, precision: SymbolPrecision) -> float:
    """Normalize quantity to step size."""
    return _round_step(qty, precision.step_size)


def validate_order(price: float, qty: float, precision: SymbolPrecision) -> list[str]:
    """Return validation errors for a proposed order."""
    errors: list[str] = []
    if qty < precision.min_qty:
        errors.append("min_qty")
    if price * qty < precision.min_notional:
        errors.append("min_notional")
    return errors

