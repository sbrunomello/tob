"""BTC macro state engine."""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from strategy.indicators import atr, bb_width, ema


@dataclass
class BtcStateResult:
    state: str
    meta: dict


def detect_btc_state(df: pd.DataFrame, settings: object) -> BtcStateResult:
    """Detect BTC state based on ATR/BB width and trend slope."""
    atr_val = atr(df, period=14).iloc[-1]
    atr_pct = atr_val / df["close"].iloc[-1]
    width = bb_width(df, period=20, std=2.0).iloc[-1]
    ema50 = ema(df["close"], period=50)
    slope = (ema50.iloc[-1] - ema50.iloc[-5]) / ema50.iloc[-5]

    if atr_pct <= settings.squeeze_atr_pct and width <= settings.squeeze_bb_width:
        return BtcStateResult("SQUEEZE", {"atr_pct": atr_pct, "bb_width": width})
    if atr_pct >= settings.expanding_atr_pct and slope >= settings.trend_slope:
        return BtcStateResult("EXPANDING_UP", {"atr_pct": atr_pct, "slope": slope})
    if atr_pct >= settings.expanding_atr_pct and slope <= -settings.trend_slope:
        return BtcStateResult("EXPANDING_DOWN", {"atr_pct": atr_pct, "slope": slope})
    return BtcStateResult("CHOP", {"atr_pct": atr_pct, "slope": slope})

