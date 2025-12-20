"""Indicator helpers."""
from __future__ import annotations

import pandas as pd
import ta


def ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def rsi(df: pd.DataFrame, period: int = 14) -> pd.Series:
    return ta.momentum.rsi(df["close"], window=period)


def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    return ta.volatility.average_true_range(df["high"], df["low"], df["close"], window=period)


def adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
    return ta.trend.adx(df["high"], df["low"], df["close"], window=period)


def bbands(df: pd.DataFrame, period: int = 20, std: float = 2.0) -> pd.DataFrame:
    indicator = ta.volatility.BollingerBands(df["close"], window=period, window_dev=std)
    return pd.DataFrame(
        {
            "lower": indicator.bollinger_lband(),
            "middle": indicator.bollinger_mavg(),
            "upper": indicator.bollinger_hband(),
        }
    )


def bb_width(df: pd.DataFrame, period: int = 20, std: float = 2.0) -> pd.Series:
    bands = bbands(df, period=period, std=std)
    return (bands["upper"] - bands["lower"]) / bands["middle"]


def donchian(df: pd.DataFrame, period: int = 20) -> pd.DataFrame:
    high = df["high"].rolling(window=period).max()
    low = df["low"].rolling(window=period).min()
    return pd.DataFrame({"high": high, "low": low})

