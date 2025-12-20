"""Market regime detection."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from strategy.indicators import adx, atr, bb_width, ema


@dataclass
class RegimeResult:
    regime: str
    meta: dict


def detect_regime(df: pd.DataFrame) -> RegimeResult:
    adx_val = adx(df, 14).iloc[-1]
    ema50 = ema(df["close"], 50)
    slope = (ema50.iloc[-1] - ema50.iloc[-5]) / ema50.iloc[-5]
    width = bb_width(df, period=20, std=2.0).iloc[-1]
    atr_series = atr(df, 14)
    atr_z = float(((atr_series - atr_series.mean()) / atr_series.std(ddof=0)).iloc[-1])

    meta = {
        "adx": float(adx_val),
        "slope": float(slope),
        "bb_width": float(width),
        "atr_z": atr_z,
    }

    if adx_val >= 25 and abs(slope) > 0.002:
        return RegimeResult("TREND_CLEAN", meta)
    if width < 0.05 and abs(slope) <= 0.002:
        return RegimeResult("RANGE", meta)
    if np.isnan(atr_z) or abs(atr_z) > 2.5:
        return RegimeResult("CHAOTIC", meta)
    return RegimeResult("TRANSITION", meta)
