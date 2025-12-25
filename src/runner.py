"""Main runner loop."""
from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any, Iterable

import pandas as pd
from loguru import logger

from config.settings import Settings
from data.btc_state import detect_btc_state
from data.collector import CandleCollector
from data.universe import UniverseBuilder
from exchange.base import ExchangeClient
from exchange.binance_futures import BinanceFuturesClient
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


def _rows_to_df(rows: Iterable[Any]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame([dict(row) for row in rows])
    return df.sort_values("open_time_ms").reset_index(drop=True)


def _calculate_spread_liquidity(ticker: dict[str, Any] | None) -> tuple[float, float]:
    if not ticker:
        return 0.001, 1e8
    bid = ticker.get("bid") or 0.0
    ask = ticker.get("ask") or 0.0
    spread = (ask - bid) / bid if bid else 0.001
    liquidity = ticker.get("quoteVolume") or 1e8
    return float(spread), float(liquidity)


def _now_ms() -> int:
    return int(time.time() * 1000)


def _resolve_universe(
    symbols_override: list[str] | None,
    exchange: ExchangeClient,
    collector: CandleCollector,
    repo: SQLiteRepository,
    settings: Settings,
    timeframe: str,
    candle_limit: int,
) -> list[str]:
    if symbols_override:
        logger.info("universe_updated source=override symbols={}", symbols_override)
        return symbols_override

    today = datetime.now(timezone.utc).date().isoformat()
    cached = repo.fetch_universe(today)
    if cached:
        symbols, _meta = cached
        logger.info("universe_updated source=cache symbols={}", symbols)
        return symbols

    markets = list(exchange.fetch_markets())
    symbols = [
        market["symbol"]
        for market in markets
        if market.get("quote") == "USDT"
        and market.get("contract")
        and market.get("linear")
        and market.get("active", True)
    ]
    if not symbols:
        logger.warning("universe_empty reason=no_markets")
        return []

    tickers = exchange.fetch_tickers() or {}
    btc_symbol = "BTC/USDT"
    collector.sync_candles(btc_symbol, timeframe=timeframe, limit=candle_limit)
    btc_rows = repo.fetch_recent_candles(btc_symbol, timeframe, candle_limit)
    btc_df = _rows_to_df(btc_rows)
    if btc_df.empty:
        logger.warning("universe_empty reason=btc_missing")
        return []
    symbol_candles: dict[str, pd.DataFrame] = {}
    for symbol in symbols:
        collector.sync_candles(symbol, timeframe=timeframe, limit=candle_limit)
        rows = repo.fetch_recent_candles(symbol, timeframe, candle_limit)
        df = _rows_to_df(rows)
        if not df.empty:
            symbol_candles[symbol] = df

    builder = UniverseBuilder(exchange)
    result = builder.build(btc_df, symbol_candles, tickers, settings.universe)
    repo.store_universe(today, result.symbols, result.meta | {"scores": result.scores})
    logger.info("universe_updated source=builder symbols={}", result.symbols)
    return result.symbols


def run_live(
    *,
    symbols: list[str] | None = None,
    max_symbols: int | None = None,
    once: bool = False,
    loop_seconds: int | None = None,
    timeframe: str | None = None,
    settings: Settings | None = None,
    exchange: ExchangeClient | None = None,
    repo: SQLiteRepository | None = None,
) -> None:
    """Run the live paper-trading pipeline using real market data."""
    settings = settings or Settings.load()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    configure_logging(settings.log_json)

    repo = repo or SQLiteRepository(str(settings.db_path))
    exchange = exchange or BinanceFuturesClient(settings.binance_api_key, settings.binance_api_secret)
    collector = CandleCollector(exchange, repo)

    if settings.execute_real_trades or settings.execution.execute_real_trades:
        logger.warning("real_trades_disabled run_live_only_paper=true")

    timeframe = timeframe or settings.live.timeframe
    loop_seconds = loop_seconds or settings.live.loop_seconds
    candle_limit = settings.live.candle_limit
    if max_symbols is None:
        max_symbols = settings.universe.max_symbols

    symbols_override = symbols[:max_symbols] if symbols else None
    last_processed: dict[str, int] = {}
    adaptive_state = AdaptiveState()
    risk_rules = RiskRules(
        max_daily_loss_r=settings.risk.max_daily_loss_r,
        max_positions=settings.risk.max_positions,
        cooldown_candles=settings.risk.cooldown_candles,
    )

    while True:
        cycle_id = _now_ms()
        logger.info("live_cycle_start cycle_id={} timeframe={}", cycle_id, timeframe)

        universe = _resolve_universe(
            symbols_override=symbols_override,
            exchange=exchange,
            collector=collector,
            repo=repo,
            settings=settings,
            timeframe=timeframe,
            candle_limit=candle_limit,
        )
        if symbols_override is None and max_symbols:
            universe = universe[:max_symbols]

        tickers = exchange.fetch_tickers() or {}
        btc_symbol = "BTC/USDT"
        collector.sync_candles(btc_symbol, timeframe=timeframe, limit=candle_limit)
        btc_rows = repo.fetch_recent_candles(btc_symbol, timeframe, candle_limit)
        btc_df = _rows_to_df(btc_rows)

        open_positions = repo.get_open_positions()
        open_by_symbol: dict[str, list[Any]] = {}
        for row in open_positions:
            open_by_symbol.setdefault(row["symbol"], []).append(row)
        risk_rules.positions_open = len(open_positions)

        returns_by_symbol: dict[str, pd.Series] = {}
        candle_frames: dict[str, pd.DataFrame] = {}
        for symbol in universe:
            new_count = collector.sync_candles(symbol, timeframe=timeframe, limit=candle_limit)
            rows = repo.fetch_recent_candles(symbol, timeframe, candle_limit)
            df = _rows_to_df(rows)
            if df.empty:
                continue
            candle_frames[symbol] = df
            returns_by_symbol[symbol] = pd.Series(df["close"]).pct_change().dropna()
            logger.info(
                "candles_ingested symbol={} timeframe={} rows={} new={}",
                symbol,
                timeframe,
                len(df),
                new_count,
            )

        clusters = {}
        if len(returns_by_symbol) >= 2:
            returns_df = pd.DataFrame(returns_by_symbol)
            cluster_result = build_clusters(returns_df, settings.risk.cluster_corr_threshold)
            clusters = cluster_result.clusters

        for symbol, df in candle_frames.items():
            latest_closed = collector.latest_closed_candle_open_time(symbol, timeframe)
            if latest_closed is None:
                continue
            if last_processed.get(symbol) == latest_closed:
                continue

            ticker = tickers.get(symbol, {})
            spread, liquidity = _calculate_spread_liquidity(ticker)

            closed_df = df[df["open_time_ms"] <= latest_closed]
            if closed_df.empty:
                continue
            candle = closed_df.iloc[-1]
            last_processed[symbol] = int(candle["open_time_ms"])

            # Close open positions based on the latest closed candle.
            for trade in open_by_symbol.get(symbol, []):
                trade_result = simulate_trade(
                    trade["direction"],
                    float(trade["entry_price"]),
                    float(trade["stop_price"]),
                    float(trade["take_price"]),
                    candle_high=float(candle["high"]),
                    candle_low=float(candle["low"]),
                    fee_rate=settings.risk.fee_rate,
                    worst_case_same_candle=settings.execution.worst_case_same_candle,
                )
                if trade_result.status != "OPEN":
                    repo.close_trade(
                        trade_id=int(trade["id"]),
                        exit_price=float(trade_result.exit_price),
                        exit_time_ms=int(candle["close_time_ms"]),
                        pnl_pct=float(trade_result.pnl_pct),
                        status=trade_result.status,
                    )
                    pnl_r = trade_result.pnl_pct / settings.risk.risk_per_trade_pct
                    risk_rules.register_trade_result(pnl_r)
                    risk_rules.apply_cooldown(symbol)
                    risk_rules.positions_open = max(0, risk_rules.positions_open - 1)
                    logger.info(
                        "paper_trade_closed symbol={} status={} pnl_pct={}",
                        symbol,
                        trade_result.status,
                        trade_result.pnl_pct,
                    )
                    open_by_symbol[symbol] = [
                        pos for pos in open_by_symbol.get(symbol, []) if pos["id"] != trade["id"]
                    ]
                    if not open_by_symbol[symbol]:
                        open_by_symbol.pop(symbol, None)

            regime = detect_regime(closed_df)
            btc_state = detect_btc_state(btc_df, settings.btc_state)
            quality = market_quality_score(closed_df, spread, liquidity, settings.market_quality)

            decision = ensemble(
                symbol,
                closed_df,
                [
                    TrendEmaStrategy(),
                    BreakoutDonchianStrategy(),
                    MeanReversionBBStrategy(),
                ],
                regime.regime,
                btc_state.state,
                quality.score,
                settings,
            )

            signal_id = repo.store_signal(
                symbol=symbol,
                timeframe=timeframe,
                signal_time_ms=int(candle["close_time_ms"]),
                signal_type=decision.signal.direction,
                price=float(decision.signal.price),
                confidence=float(decision.signal.confidence),
                reasons=decision.reasons,
                created_at_ms=_now_ms(),
            )
            logger.info(
                "signal_generated symbol={} direction={} cycle_id={}",
                symbol,
                decision.signal.direction,
                cycle_id,
            )

            if decision.signal.direction == "NONE":
                continue

            if symbol in open_by_symbol:
                logger.info("risk_block_open_position symbol={}", symbol)
                continue

            if not risk_rules.can_open(symbol):
                logger.info("risk_block symbol={}", symbol)
                continue

            cluster_id = clusters.get(symbol)
            if cluster_id is not None:
                cluster_positions = sum(
                    1
                    for sym in open_by_symbol
                    if clusters.get(sym) == cluster_id
                )
                if cluster_positions >= settings.risk.max_positions_per_cluster:
                    logger.info("risk_block_cluster symbol={} cluster={}", symbol, cluster_id)
                    continue

            if settings.execution.entry_on == "next_open":
                next_candle = df[df["open_time_ms"] > latest_closed].head(1)
                if next_candle.empty:
                    logger.info("await_next_open symbol={}", symbol)
                    continue
                entry_price = float(next_candle.iloc[0]["open"])
            else:
                entry_price = float(candle["close"])

            atr_value = atr(closed_df, 14).iloc[-1]
            stops = atr_stops(
                entry=entry_price,
                atr_value=atr_value,
                direction=decision.signal.direction,
                stop_mult=settings.risk.stop_atr_mult,
                take_mult=settings.risk.take_atr_mult,
            )
            risk_pct = adjust_risk(settings.risk.risk_per_trade_pct, adaptive_state)
            size = position_size(1000.0, risk_pct, entry_price, stops.stop)

            trade_id = repo.open_trade(
                signal_id=signal_id,
                direction=decision.signal.direction,
                entry_price=entry_price,
                stop_price=stops.stop,
                take_price=stops.take,
                fees_estimate=settings.risk.fee_rate * 2,
                meta={
                    "entry_on": settings.execution.entry_on,
                    "cycle_id": cycle_id,
                    "size": size,
                },
            )
            risk_rules.positions_open += 1
            open_by_symbol.setdefault(symbol, []).append(
                {
                    "id": trade_id,
                    "symbol": symbol,
                    "direction": decision.signal.direction,
                    "entry_price": entry_price,
                    "stop_price": stops.stop,
                    "take_price": stops.take,
                }
            )
            logger.info(
                "paper_trade_opened symbol={} trade_id={} direction={} entry_price={}",
                symbol,
                trade_id,
                decision.signal.direction,
                entry_price,
            )

        risk_rules.tick()

        if once:
            logger.info("live_cycle_complete cycle_id={}", cycle_id)
            break

        time.sleep(loop_seconds)


def main() -> None:
    settings = Settings.load()
    runner = TradingRunner(settings)
    logger.info("runner_ready")


if __name__ == "__main__":
    main()
