import numpy as np
import pandas as pd

from strategy.breakout_donchian import BreakoutDonchianStrategy
from strategy.mean_reversion_bb import MeanReversionBBStrategy
from strategy.trend_ema import TrendEmaStrategy


def _trend_df() -> pd.DataFrame:
    prices = np.linspace(100, 130, 60)
    return pd.DataFrame(
        {
            "open": prices,
            "high": prices * 1.01,
            "low": prices * 0.99,
            "close": prices,
        }
    )


def test_trend_strategy_long():
    df = _trend_df()

    class Settings:
        min_atr_pct = 0.0001

    strat = TrendEmaStrategy()
    signal = strat.generate("BTC/USDT", df, Settings())
    assert signal.direction == "LONG"


def test_breakout_strategy_long():
    prices = np.concatenate([np.linspace(100, 110, 40), np.linspace(110, 120, 20)])
    df = pd.DataFrame(
        {
            "open": prices,
            "high": prices * 1.01,
            "low": prices * 0.99,
            "close": prices,
        }
    )

    class Settings:
        donchian_period = 20
        atr_zscore_spike = 5.0

    strat = BreakoutDonchianStrategy()
    signal = strat.generate("BTC/USDT", df, Settings())
    assert signal.direction in {"LONG", "NONE"}


def test_mean_reversion_signal():
    prices = np.array([100] * 55 + [90, 92, 95, 97, 100])
    df = pd.DataFrame(
        {
            "open": prices,
            "high": prices * 1.01,
            "low": prices * 0.99,
            "close": prices,
        }
    )

    class Settings:
        bb_period = 20
        bb_std = 2.0

    strat = MeanReversionBBStrategy()
    signal = strat.generate("BTC/USDT", df, Settings())
    assert signal.direction in {"LONG", "NONE"}
