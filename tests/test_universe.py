import numpy as np
import pandas as pd

from data.universe import UniverseBuilder, compute_beta, compute_corr


class DummyExchange:
    def fetch_markets(self):
        return []

    def fetch_tickers(self):
        return {}

    def fetch_ohlcv(self, *args, **kwargs):
        return []

    def create_order(self, *args, **kwargs):
        return {}

    def set_leverage(self, *args, **kwargs):
        return None


def _df_from_returns(returns: np.ndarray) -> pd.DataFrame:
    prices = 100 * np.exp(np.cumsum(returns))
    return pd.DataFrame(
        {
            "open": prices,
            "high": prices * 1.01,
            "low": prices * 0.99,
            "close": prices,
        }
    )


def test_beta_corr_and_selection():
    btc_returns = np.random.normal(0, 0.01, 300)
    alt_returns = btc_returns * 1.5 + np.random.normal(0, 0.002, 300)
    btc_df = _df_from_returns(btc_returns)
    alt_df = _df_from_returns(alt_returns)

    beta = compute_beta(pd.Series(alt_returns), pd.Series(btc_returns))
    corr = compute_corr(pd.Series(alt_returns), pd.Series(btc_returns))
    assert beta > 1.0
    assert corr > 0.5

    builder = UniverseBuilder(DummyExchange())

    class Settings:
        volume_percentile = 0.30
        min_atr_pct = 0.0001
        min_beta_btc = 1.0
        min_corr_btc = 0.3
        max_symbols = 1

        class Weights:
            volume = 0.5
            atr_pct = 0.3
            beta = 0.2

        weights = Weights()
        manual_override = []

    result = builder.build(
        btc_df,
        {"ALT/USDT": alt_df},
        {"ALT/USDT": {"quoteVolume": 1_000_000}},
        Settings(),
    )
    assert result.symbols == ["ALT/USDT"]
