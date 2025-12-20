"""Donchian breakout strategy."""
from __future__ import annotations

import pandas as pd

from strategy.base import Signal, Strategy
from strategy.indicators import atr, donchian, rsi


class BreakoutDonchianStrategy(Strategy):
    name = "breakout_donchian"

    def generate(self, symbol: str, df: pd.DataFrame, settings: object) -> Signal:
        channel = donchian(df, period=settings.donchian_period)
        latest = df.iloc[-1]
        rsi_val = rsi(df, 14).iloc[-1]
        atr_series = atr(df, 14)
        atr_z = (atr_series - atr_series.mean()) / atr_series.std(ddof=0)
        spike = atr_z.iloc[-1] >= settings.atr_zscore_spike

        reasons = {
            "donchian_high": float(channel["high"].iloc[-1]),
            "donchian_low": float(channel["low"].iloc[-1]),
            "rsi": float(rsi_val),
            "atr_zscore": float(atr_z.iloc[-1]),
            "spike": bool(spike),
        }

        if spike:
            return Signal(symbol, "NONE", float(latest["close"]), 0.0, reasons)

        if latest["close"] > channel["high"].iloc[-1] and rsi_val >= 50:
            return Signal(symbol, "LONG", float(latest["close"]), 1.0, reasons)
        if latest["close"] < channel["low"].iloc[-1] and rsi_val <= 50:
            return Signal(symbol, "SHORT", float(latest["close"]), 1.0, reasons)
        return Signal(symbol, "NONE", float(latest["close"]), 0.0, reasons)

