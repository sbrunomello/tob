"""Universe builder to select symbols daily."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

import numpy as np
import pandas as pd
from loguru import logger

from exchange.base import ExchangeClient
from strategy.indicators import atr


@dataclass
class UniverseResult:
    symbols: list[str]
    scores: dict[str, float]
    meta: dict[str, Any]


def _normalize(series: pd.Series) -> pd.Series:
    if series.max() == series.min():
        return pd.Series(np.ones(len(series)), index=series.index)
    return (series - series.min()) / (series.max() - series.min())


def compute_beta(returns: pd.Series, btc_returns: pd.Series) -> float:
    cov = np.cov(returns, btc_returns)[0][1]
    var = np.var(btc_returns)
    if var == 0:
        return 0.0
    return float(cov / var)


def compute_corr(returns: pd.Series, btc_returns: pd.Series) -> float:
    if returns.empty or btc_returns.empty:
        return 0.0
    return float(np.corrcoef(returns, btc_returns)[0][1])


class UniverseBuilder:
    """Build a universe of tradable symbols based on liquidity and volatility."""

    def __init__(self, exchange: ExchangeClient) -> None:
        self.exchange = exchange

    def build(
        self,
        btc_candles: pd.DataFrame,
        symbol_candles: dict[str, pd.DataFrame],
        tickers: dict[str, Any],
        settings: Any,
    ) -> UniverseResult:
        if settings.manual_override:
            return UniverseResult(symbols=settings.manual_override, scores={}, meta={"override": True})

        btc_returns = np.log(btc_candles["close"]).diff().dropna()
        records: list[dict[str, Any]] = []
        for symbol, df in symbol_candles.items():
            atr_val = atr(df, period=14).iloc[-1]
            atr_pct = atr_val / df["close"].iloc[-1]
            returns = np.log(df["close"]).diff().dropna()
            beta = compute_beta(returns, btc_returns)
            corr = compute_corr(returns, btc_returns)
            volume = tickers.get(symbol, {}).get("quoteVolume", 0)
            records.append(
                {
                    "symbol": symbol,
                    "volume": volume,
                    "atr_pct": atr_pct,
                    "beta": beta,
                    "corr": corr,
                }
            )

        data = pd.DataFrame(records).set_index("symbol")
        if data.empty:
            return UniverseResult(symbols=[], scores={}, meta={"reason": "no_data"})

        volume_unavailable = data["volume"].sum() == 0
        if volume_unavailable:
            logger.warning("volume_unavailable_fallback")
            filtered = data.copy()
        else:
            volume_threshold = data["volume"].quantile(1 - settings.volume_percentile)
            filtered = data[data["volume"] >= volume_threshold]
        filtered = filtered[filtered["atr_pct"] >= settings.min_atr_pct]
        filtered = filtered[filtered["beta"] >= settings.min_beta_btc]
        filtered = filtered[filtered["corr"] >= settings.min_corr_btc]
        if filtered.empty:
            return UniverseResult(symbols=[], scores={}, meta={"reason": "filtered_empty"})

        volume_score = (
            _normalize(filtered["volume"])
            if not volume_unavailable
            else pd.Series(0.0, index=filtered.index)
        )
        scores = (
            settings.weights.volume * volume_score
            + settings.weights.atr_pct * _normalize(filtered["atr_pct"])
            + settings.weights.beta * _normalize(filtered["beta"])
        )
        ranked = scores.sort_values(ascending=False).head(settings.max_symbols)
        return UniverseResult(
            symbols=list(ranked.index),
            scores=ranked.to_dict(),
            meta={"candidates": len(filtered), "volume_unavailable": volume_unavailable},
        )
