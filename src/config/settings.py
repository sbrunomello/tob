"""Application configuration using Pydantic Settings."""
from __future__ import annotations

from pathlib import Path
from typing import List

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings

DEFAULTS_PATH = Path(__file__).with_name("defaults.yaml")


class RiskSettings(BaseModel):
    risk_per_trade_pct: float = 0.005
    max_daily_loss_r: float = 3.0
    max_positions: int = 2
    cooldown_candles: int = 2
    trailing_stop: bool = False
    fee_rate: float = 0.0004
    stop_atr_mult: float = 1.2
    take_atr_mult: float = 1.8
    cluster_corr_threshold: float = 0.75
    max_positions_per_cluster: int = 1


class UniverseWeights(BaseModel):
    volume: float = 0.45
    atr_pct: float = 0.35
    beta: float = 0.20


class UniverseSettings(BaseModel):
    volume_percentile: float = 0.30
    min_atr_pct: float = 0.004
    min_beta_btc: float = 1.2
    min_corr_btc: float = 0.5
    max_symbols: int = 15
    weights: UniverseWeights = Field(default_factory=UniverseWeights)
    manual_override: List[str] = Field(default_factory=list)


class MarketQualitySettings(BaseModel):
    min_trade_score: int = 70
    reduced_risk_score: int = 50
    spread_penalty: int = 20
    atr_low_penalty: int = 15
    adx_low_penalty: int = 10
    wick_penalty: int = 10
    liquidity_bonus: int = 15
    direction_bonus: int = 10


class TrendSettings(BaseModel):
    min_atr_pct: float = 0.004


class BreakoutSettings(BaseModel):
    donchian_period: int = 20
    atr_zscore_spike: float = 2.5


class MeanReversionSettings(BaseModel):
    bb_period: int = 20
    bb_std: float = 2.0


class StrategySettings(BaseModel):
    trend: TrendSettings = Field(default_factory=TrendSettings)
    breakout: BreakoutSettings = Field(default_factory=BreakoutSettings)
    mean_reversion: MeanReversionSettings = Field(default_factory=MeanReversionSettings)


class ScoringSettings(BaseModel):
    min_trades: int = 30
    disable_candles: int = 96


class BtcStateSettings(BaseModel):
    squeeze_bb_width: float = 0.04
    squeeze_atr_pct: float = 0.003
    expanding_atr_pct: float = 0.006
    trend_slope: float = 0.0005


class RunnerSettings(BaseModel):
    timeframe: str = "15m"
    loop_seconds: int = 30


class ExecutionSettings(BaseModel):
    execute_real_trades: bool = False
    entry_on: str = "close"
    worst_case_same_candle: bool = True


class Settings(BaseSettings):
    """Runtime settings loaded from env and config file."""

    data_dir: Path = Field(default_factory=lambda: Path("data"))
    db_path: Path = Field(default_factory=lambda: Path("data") / "tob.sqlite")
    log_json: bool = False
    binance_api_key: str | None = None
    binance_api_secret: str | None = None
    execute_real_trades: bool = False

    risk: RiskSettings = Field(default_factory=RiskSettings)
    universe: UniverseSettings = Field(default_factory=UniverseSettings)
    market_quality: MarketQualitySettings = Field(default_factory=MarketQualitySettings)
    strategy: StrategySettings = Field(default_factory=StrategySettings)
    scoring: ScoringSettings = Field(default_factory=ScoringSettings)
    btc_state: BtcStateSettings = Field(default_factory=BtcStateSettings)
    runner: RunnerSettings = Field(default_factory=RunnerSettings)
    execution: ExecutionSettings = Field(default_factory=ExecutionSettings)

    model_config = {
        "env_prefix": "TOB_",
        "case_sensitive": False,
    }

    @classmethod
    def load(cls, config_path: Path | None = None) -> "Settings":
        config_data: dict = {}
        if DEFAULTS_PATH.exists():
            config_data.update(yaml.safe_load(DEFAULTS_PATH.read_text()) or {})
        if config_path and config_path.exists():
            config_data.update(yaml.safe_load(config_path.read_text()) or {})
        return cls(**config_data)

