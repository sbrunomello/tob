"""Exchange client interfaces."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Iterable


class ExchangeClient(ABC):
    """Abstract interface for exchange connectivity."""

    @abstractmethod
    def fetch_ohlcv(self, symbol: str, timeframe: str, limit: int = 300) -> list[list[float]]:
        raise NotImplementedError

    @abstractmethod
    def fetch_tickers(self) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def fetch_markets(self) -> Iterable[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def create_order(self, symbol: str, side: str, amount: float, price: float | None) -> Any:
        raise NotImplementedError

    @abstractmethod
    def set_leverage(self, symbol: str, leverage: int) -> None:
        raise NotImplementedError

