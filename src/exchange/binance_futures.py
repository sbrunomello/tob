"""Binance USDⓈ-M futures client via CCXT."""
from __future__ import annotations

from typing import Any, Iterable

import ccxt
from loguru import logger

from exchange.base import ExchangeClient
from exchange.rate_limit import RateLimitGuard


class BinanceFuturesClient(ExchangeClient):
    """CCXT wrapper for Binance USDⓈ-M futures."""

    def __init__(self, api_key: str | None = None, api_secret: str | None = None) -> None:
        self.client = ccxt.binanceusdm({
            "enableRateLimit": True,
            "apiKey": api_key or "",
            "secret": api_secret or "",
        })
        self.guard = RateLimitGuard()

    def fetch_ohlcv(self, symbol: str, timeframe: str, limit: int = 300) -> list[list[float]]:
        logger.info("fetch_ohlcv symbol={} timeframe={} limit={}", symbol, timeframe, limit)
        return self.guard.run(
            self.client.fetch_ohlcv,
            symbol,
            timeframe,
            limit=limit,
            context={"symbol": symbol, "endpoint": "fetch_ohlcv"},
        )

    def fetch_tickers(self) -> dict[str, Any]:
        logger.info("fetch_tickers")
        return self.guard.run(self.client.fetch_tickers, context={"endpoint": "fetch_tickers"})

    def fetch_markets(self) -> Iterable[dict[str, Any]]:
        logger.info("fetch_markets")
        return self.guard.run(self.client.fetch_markets, context={"endpoint": "fetch_markets"})

    def create_order(self, symbol: str, side: str, amount: float, price: float | None) -> Any:
        logger.info("create_order symbol={} side={} amount={} price={}", symbol, side, amount, price)
        return self.guard.run(
            self.client.create_order,
            symbol,
            "limit" if price else "market",
            side,
            amount,
            price,
            context={"symbol": symbol, "endpoint": "create_order"},
        )

    def set_leverage(self, symbol: str, leverage: int) -> None:
        try:
            self.guard.run(
                self.client.set_leverage,
                leverage,
                symbol,
                context={"symbol": symbol, "endpoint": "set_leverage"},
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("set_leverage_failed symbol={} leverage={} error={}", symbol, leverage, exc)

