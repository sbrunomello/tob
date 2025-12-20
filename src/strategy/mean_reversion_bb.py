"""Mean reversion Bollinger strategy."""
from __future__ import annotations

import pandas as pd

from strategy.base import Signal, Strategy
from strategy.indicators import bbands


class MeanReversionBBStrategy(Strategy):
    name = "mean_reversion_bb"

    def generate(self, symbol: str, df: pd.DataFrame, settings: object) -> Signal:
        bands = bbands(df, period=settings.bb_period, std=settings.bb_std)
        latest = df.iloc[-1]
        prev = df.iloc[-2]
        lower = bands["lower"].iloc[-1]
        upper = bands["upper"].iloc[-1]

        reasons = {
            "lower": float(lower),
            "upper": float(upper),
            "prev_close": float(prev["close"]),
            "close": float(latest["close"]),
        }

        if prev["close"] < lower and latest["close"] > lower:
            return Signal(symbol, "LONG", float(latest["close"]), 1.0, reasons)
        if prev["close"] > upper and latest["close"] < upper:
            return Signal(symbol, "SHORT", float(latest["close"]), 1.0, reasons)
        return Signal(symbol, "NONE", float(latest["close"]), 0.0, reasons)

