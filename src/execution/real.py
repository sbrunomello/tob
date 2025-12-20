"""Real trading executor (disabled by default)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from loguru import logger

from exchange.base import ExchangeClient
from exchange.precision import SymbolPrecision, normalize_price, normalize_qty, validate_order


@dataclass
class RealExecutionResult:
    status: str
    details: dict[str, Any]


def execute_trade(
    exchange: ExchangeClient,
    symbol: str,
    direction: str,
    qty: float,
    price: float,
    precision: SymbolPrecision,
    enabled: bool,
    dry_run: bool = True,
) -> RealExecutionResult:
    if not enabled:
        return RealExecutionResult("DISABLED", {"reason": "execute_real_trades=false"})

    norm_price = normalize_price(price, precision)
    norm_qty = normalize_qty(qty, precision)
    errors = validate_order(norm_price, norm_qty, precision)
    if errors:
        return RealExecutionResult("REJECTED", {"errors": errors})

    if dry_run:
        logger.info("dry_run_order symbol={} direction={} qty={} price={}", symbol, direction, norm_qty, norm_price)
        return RealExecutionResult("DRY_RUN", {"symbol": symbol, "qty": norm_qty, "price": norm_price})

    side = "buy" if direction == "LONG" else "sell"
    response = exchange.create_order(symbol, side, norm_qty, norm_price)
    return RealExecutionResult("SUBMITTED", {"response": response})

