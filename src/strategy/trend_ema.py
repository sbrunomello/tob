"""Trend-following EMA strategy."""
from __future__ import annotations

import pandas as pd

from strategy.base import Signal, Strategy
from strategy.indicators import atr, ema, rsi


class TrendEmaStrategy(Strategy):
    name = "trend_ema"

    def generate(self, symbol: str, df: pd.DataFrame, settings: object) -> Signal:
        ema9 = ema(df["close"], 9)
        ema21 = ema(df["close"], 21)
        rsi_val = rsi(df, 14)
        atr_val = atr(df, 14)
        latest = df.iloc[-1]
        prev = df.iloc[-2]
        atr_pct = atr_val.iloc[-1] / latest["close"]

        reasons = {
            "ema9": float(ema9.iloc[-1]),
            "ema21": float(ema21.iloc[-1]),
            "rsi": float(rsi_val.iloc[-1]),
            "atr_pct": float(atr_pct),
        }

        if (
            ema9.iloc[-1] > ema21.iloc[-1]
            and rsi_val.iloc[-1] >= 52
            and latest["close"] > prev["close"]
            and latest["close"] > ema9.iloc[-1]
            and atr_pct >= settings.min_atr_pct
        ):
            return Signal(symbol, "LONG", float(latest["close"]), 1.0, reasons)
        if (
            ema9.iloc[-1] < ema21.iloc[-1]
            and rsi_val.iloc[-1] <= 48
            and latest["close"] < prev["close"]
            and latest["close"] < ema9.iloc[-1]
            and atr_pct >= settings.min_atr_pct
        ):
            return Signal(symbol, "SHORT", float(latest["close"]), 1.0, reasons)
        return Signal(symbol, "NONE", float(latest["close"]), 0.0, reasons)

