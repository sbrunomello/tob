"""Main runner loop."""
from __future__ import annotations

import time
from datetime import datetime
from pathlib import Path

import pandas as pd
from loguru import logger

from config.settings import Settings
from data.btc_state import detect_btc_state
from data.collector import CandleCollector
from data.universe import UniverseBuilder
from execution.paper import simulate_trade
from market.clusters import build_clusters
from market.quality import market_quality_score
from market.regime import detect_regime
from observability.logging import configure_logging
from risk.adaptive import AdaptiveState, adjust_risk
from risk.rules import RiskRules
from risk.sizing import position_size
from risk.stops import atr_stops
from storage.repo import SQLiteRepository
from strategy.breakout_donchian import BreakoutDonchianStrategy
from strategy.ensemble import ensemble
from strategy.mean_reversion_bb import MeanReversionBBStrategy
from strategy.trend_ema import TrendEmaStrategy
from strategy.indicators import atr


class TradingRunner:
    """Orchestrates data, strategies, risk, and execution."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.settings.data_dir.mkdir(parents=True, exist_ok=True)
        self.repo = SQLiteRepository(str(settings.db_path))
        configure_logging(settings.log_json)
        self.strategies = [
            TrendEmaStrategy(),
            BreakoutDonchianStrategy(),
            MeanReversionBBStrategy(),
        ]
        self.risk_rules = RiskRules(
            max_daily_loss_r=settings.risk.max_daily_loss_r,
            max_positions=settings.risk.max_positions,
            cooldown_candles=settings.risk.cooldown_candles,
        )
        self.adaptive_state = AdaptiveState()

    def run_once(self, symbol: str, df: pd.DataFrame, btc_df: pd.DataFrame) -> None:
        regime = detect_regime(df)
        btc_state = detect_btc_state(btc_df, self.settings.btc_state)
        spread = 0.001
        liquidity = 1e8
        quality = market_quality_score(df, spread, liquidity, self.settings.market_quality)

        decision = ensemble(
            symbol,
            df,
            self.strategies,
            regime.regime,
            btc_state.state,
            quality.score,
            self.settings,
        )

        if decision.signal.direction == "NONE":
            logger.info("no_signal symbol={} reasons={}", symbol, decision.reasons)
            return

        if not self.risk_rules.can_open(symbol):
            logger.info("risk_block symbol={}", symbol)
            return

        atr_value = atr(df, 14).iloc[-1]
        stops = atr_stops(
            entry=decision.signal.price,
            atr_value=atr_value,
            direction=decision.signal.direction,
            stop_mult=self.settings.risk.stop_atr_mult,
            take_mult=self.settings.risk.take_atr_mult,
        )
        risk_pct = adjust_risk(self.settings.risk.risk_per_trade_pct, self.adaptive_state)
        size = position_size(1000.0, risk_pct, decision.signal.price, stops.stop)

        candle = df.iloc[-1]
        trade = simulate_trade(
            decision.signal.direction,
            decision.signal.price,
            stops.stop,
            stops.take,
            candle_high=float(candle["high"]),
            candle_low=float(candle["low"]),
            fee_rate=self.settings.risk.fee_rate,
            worst_case_same_candle=self.settings.execution.worst_case_same_candle,
        )
        logger.info(
            "paper_trade symbol={} direction={} status={} pnl_pct={}",
            symbol,
            decision.signal.direction,
            trade.status,
            trade.pnl_pct,
        )

    def loop(self) -> None:
        logger.info("runner_start")
        while True:
            time.sleep(self.settings.runner.loop_seconds)


def main() -> None:
    settings = Settings.load()
    runner = TradingRunner(settings)
    logger.info("runner_ready")


if __name__ == "__main__":
    main()
