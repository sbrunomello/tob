import pandas as pd

from strategy.base import Signal, Strategy
from strategy.ensemble import ensemble


class DummyStrategy(Strategy):
    def __init__(self, name: str, direction: str):
        self.name = name
        self.direction = direction

    def generate(self, symbol: str, df: pd.DataFrame, settings):
        return Signal(symbol, self.direction, float(df["close"].iloc[-1]), 1.0, {"dir": self.direction})


def test_ensemble_voting():
    df = pd.DataFrame(
        {
            "open": [1, 1.1, 1.2],
            "high": [1.1, 1.2, 1.3],
            "low": [0.9, 1.0, 1.1],
            "close": [1.0, 1.1, 1.2],
        }
    )

    class Settings:
        class MarketQuality:
            min_trade_score = 70

        market_quality = MarketQuality()

        class Trend:
            pass

        class Breakout:
            pass

        class Mean:
            pass

        trend = Trend()
        breakout = Breakout()
        mean_reversion = Mean()

    strategies = [
        DummyStrategy("trend_ema", "LONG"),
        DummyStrategy("breakout_donchian", "LONG"),
        DummyStrategy("mean_reversion_bb", "SHORT"),
    ]
    decision = ensemble("BTC/USDT", df, strategies, "TREND_CLEAN", "EXPANDING_UP", 80, Settings())
    assert decision.signal.direction == "LONG"
