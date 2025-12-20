import pandas as pd

from strategy.indicators import adx, atr, bbands, donchian, ema, rsi


def _sample_df() -> pd.DataFrame:
    data = {
        "open": [1 + i * 0.1 for i in range(60)],
        "high": [1 + i * 0.12 for i in range(60)],
        "low": [1 + i * 0.08 for i in range(60)],
        "close": [1 + i * 0.1 for i in range(60)],
    }
    return pd.DataFrame(data)


def test_indicators_basic():
    df = _sample_df()
    assert ema(df["close"], 9).iloc[-1] > ema(df["close"], 21).iloc[-1]
    assert rsi(df, 14).iloc[-1] > 50
    assert atr(df, 14).iloc[-1] > 0
    assert adx(df, 14).iloc[-1] >= 0
    bands = bbands(df)
    assert bands["upper"].iloc[-1] > bands["lower"].iloc[-1]
    channel = donchian(df, 20)
    assert channel["high"].iloc[-1] >= df["high"].iloc[-1]
