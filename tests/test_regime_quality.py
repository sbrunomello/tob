import numpy as np
import pandas as pd

from market.quality import market_quality_score
from market.regime import detect_regime


def _trend_df() -> pd.DataFrame:
    prices = np.linspace(100, 120, 120)
    return pd.DataFrame(
        {
            "open": prices,
            "high": prices * 1.01,
            "low": prices * 0.99,
            "close": prices,
        }
    )


def _range_df() -> pd.DataFrame:
    prices = 100 + np.sin(np.linspace(0, 10, 120))
    return pd.DataFrame(
        {
            "open": prices,
            "high": prices * 1.005,
            "low": prices * 0.995,
            "close": prices,
        }
    )


def test_regime_and_quality_scores():
    trend_df = _trend_df()
    range_df = _range_df()
    regime_trend = detect_regime(trend_df)
    regime_range = detect_regime(range_df)
    assert regime_trend.regime in {"TREND_CLEAN", "TRANSITION"}
    assert regime_range.regime in {"RANGE", "TRANSITION"}

    class Settings:
        spread_penalty = 20
        atr_low_penalty = 15
        adx_low_penalty = 10
        wick_penalty = 10
        liquidity_bonus = 15
        direction_bonus = 10

    quality = market_quality_score(trend_df, spread=0.001, liquidity=2e7, settings=Settings())
    assert 0 <= quality.score <= 100
