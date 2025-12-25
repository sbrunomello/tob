"""Streamlit-based GUI for configuring and observing TOB."""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st
import yaml

# Ensure project root is on sys.path for local execution via Streamlit.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backtest.engine import run_backtest
from config.settings import Settings
from runner import run_live
from storage.repo import SQLiteRepository

CONFIG_PATH = PROJECT_ROOT / "config.yaml"
ENV_PATH = PROJECT_ROOT / ".env"


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text()) or {}


def _write_yaml(path: Path, data: dict[str, Any]) -> None:
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True))


def _load_env(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    entries = {}
    for line in path.read_text().splitlines():
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        entries[key.strip()] = value.strip()
    return entries


def _write_env(path: Path, entries: dict[str, str]) -> None:
    lines = [f"{key}={value}" for key, value in entries.items() if value]
    path.write_text("\n".join(lines) + "\n")


def _settings_to_config(settings: Settings) -> dict[str, Any]:
    payload = settings.model_dump(mode="json")
    payload.pop("binance_api_key", None)
    payload.pop("binance_api_secret", None)
    return payload


def _read_table(db_path: Path, query: str, params: tuple[Any, ...] = ()) -> pd.DataFrame:
    if not db_path.exists():
        return pd.DataFrame()
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(query, params).fetchall()
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame([dict(row) for row in rows])


def render_sidebar(settings: Settings) -> None:
    st.sidebar.title("TOB - GUI")
    st.sidebar.caption("Configuração e observabilidade")
    st.sidebar.write(f"Banco: `{settings.db_path}`")


def render_api_keys(settings: Settings) -> None:
    st.header("Chaves e Ambiente")
    st.caption("As chaves são armazenadas no arquivo .env local (não versionado).")

    env_entries = _load_env(ENV_PATH)
    key_default = env_entries.get("TOB_BINANCE_API_KEY", settings.binance_api_key or "")
    secret_default = env_entries.get("TOB_BINANCE_API_SECRET", settings.binance_api_secret or "")

    with st.form("api_keys_form"):
        api_key = st.text_input("Binance API Key", value=key_default, type="password")
        api_secret = st.text_input("Binance API Secret", value=secret_default, type="password")
        save_env = st.form_submit_button("Salvar .env")

    if save_env:
        _write_env(
            ENV_PATH,
            {
                "TOB_BINANCE_API_KEY": api_key,
                "TOB_BINANCE_API_SECRET": api_secret,
            },
        )
        st.success("Chaves salvas em .env")


def render_settings_editor(settings: Settings) -> Settings:
    st.header("Configuração")
    st.caption("Atualize parâmetros e salve em config.yaml.")

    config_payload = _settings_to_config(settings)

    with st.form("settings_form"):
        col1, col2 = st.columns(2)
        with col1:
            execute_real_trades = st.checkbox(
                "Executar trades reais", value=settings.execute_real_trades
            )
            log_json = st.checkbox("Log JSON", value=settings.log_json)
        with col2:
            data_dir = st.text_input("Diretório de dados", value=str(settings.data_dir))
            db_path = st.text_input("Caminho do SQLite", value=str(settings.db_path))

        st.subheader("Risco")
        risk = settings.risk
        risk_per_trade_pct = st.number_input(
            "Risco por trade (%)", min_value=0.0, value=risk.risk_per_trade_pct * 100, step=0.1
        )
        max_daily_loss_r = st.number_input(
            "Máx perda diária (R)", min_value=0.0, value=risk.max_daily_loss_r, step=0.1
        )
        max_positions = st.number_input(
            "Máx posições", min_value=1, value=risk.max_positions, step=1
        )
        cooldown_candles = st.number_input(
            "Cooldown (candles)", min_value=0, value=risk.cooldown_candles, step=1
        )
        trailing_stop = st.checkbox("Trailing stop", value=risk.trailing_stop)
        fee_rate = st.number_input("Taxa (fee)", min_value=0.0, value=risk.fee_rate, step=0.0001)
        stop_atr_mult = st.number_input(
            "Stop ATR mult", min_value=0.1, value=risk.stop_atr_mult, step=0.1
        )
        take_atr_mult = st.number_input(
            "Take ATR mult", min_value=0.1, value=risk.take_atr_mult, step=0.1
        )
        cluster_corr_threshold = st.number_input(
            "Cluster corr threshold",
            min_value=0.0,
            max_value=1.0,
            value=risk.cluster_corr_threshold,
            step=0.05,
        )
        max_positions_per_cluster = st.number_input(
            "Máx posições por cluster", min_value=1, value=risk.max_positions_per_cluster, step=1
        )

        st.subheader("Universe")
        universe = settings.universe
        volume_percentile = st.number_input(
            "Volume percentile", min_value=0.0, max_value=1.0, value=universe.volume_percentile, step=0.05
        )
        min_atr_pct = st.number_input(
            "ATR mínimo (%)", min_value=0.0, value=universe.min_atr_pct * 100, step=0.1
        )
        min_beta_btc = st.number_input(
            "Beta mínimo BTC", min_value=0.0, value=universe.min_beta_btc, step=0.1
        )
        min_corr_btc = st.number_input(
            "Correlação mínima BTC", min_value=0.0, max_value=1.0, value=universe.min_corr_btc, step=0.05
        )
        max_symbols = st.number_input(
            "Máx símbolos", min_value=1, value=universe.max_symbols, step=1
        )
        weight_volume = st.number_input(
            "Peso volume", min_value=0.0, value=universe.weights.volume, step=0.05
        )
        weight_atr = st.number_input(
            "Peso ATR", min_value=0.0, value=universe.weights.atr_pct, step=0.05
        )
        weight_beta = st.number_input(
            "Peso beta", min_value=0.0, value=universe.weights.beta, step=0.05
        )
        manual_override = st.text_input(
            "Override manual (CSV)", value=",".join(universe.manual_override)
        )

        st.subheader("Qualidade de mercado")
        quality = settings.market_quality
        min_trade_score = st.number_input(
            "Score mínimo", min_value=0, value=quality.min_trade_score, step=1
        )
        reduced_risk_score = st.number_input(
            "Score reduzido", min_value=0, value=quality.reduced_risk_score, step=1
        )
        spread_penalty = st.number_input(
            "Penalidade spread", min_value=0, value=quality.spread_penalty, step=1
        )
        atr_low_penalty = st.number_input(
            "Penalidade ATR baixo", min_value=0, value=quality.atr_low_penalty, step=1
        )
        adx_low_penalty = st.number_input(
            "Penalidade ADX baixo", min_value=0, value=quality.adx_low_penalty, step=1
        )
        wick_penalty = st.number_input(
            "Penalidade wick", min_value=0, value=quality.wick_penalty, step=1
        )
        liquidity_bonus = st.number_input(
            "Bônus liquidez", min_value=0, value=quality.liquidity_bonus, step=1
        )
        direction_bonus = st.number_input(
            "Bônus direção", min_value=0, value=quality.direction_bonus, step=1
        )

        st.subheader("Execução")
        execution = settings.execution
        execution_entry_on = st.selectbox(
            "Entrada", options=["close", "next_open"], index=0 if execution.entry_on == "close" else 1
        )
        worst_case_same_candle = st.checkbox(
            "Worst-case no mesmo candle", value=execution.worst_case_same_candle
        )

        st.subheader("Live")
        live = settings.live
        live_timeframe = st.text_input("Timeframe", value=live.timeframe)
        live_loop_seconds = st.number_input(
            "Loop segundos", min_value=1, value=live.loop_seconds, step=1
        )
        live_candle_limit = st.number_input(
            "Limite de candles", min_value=100, value=live.candle_limit, step=10
        )

        save_config = st.form_submit_button("Salvar config.yaml")

    if save_config:
        config_payload.update(
            {
                "execute_real_trades": execute_real_trades,
                "log_json": log_json,
                "data_dir": data_dir,
                "db_path": db_path,
                "risk": {
                    "risk_per_trade_pct": risk_per_trade_pct / 100,
                    "max_daily_loss_r": max_daily_loss_r,
                    "max_positions": int(max_positions),
                    "cooldown_candles": int(cooldown_candles),
                    "trailing_stop": trailing_stop,
                    "fee_rate": fee_rate,
                    "stop_atr_mult": stop_atr_mult,
                    "take_atr_mult": take_atr_mult,
                    "cluster_corr_threshold": cluster_corr_threshold,
                    "max_positions_per_cluster": int(max_positions_per_cluster),
                },
                "universe": {
                    "volume_percentile": volume_percentile,
                    "min_atr_pct": min_atr_pct / 100,
                    "min_beta_btc": min_beta_btc,
                    "min_corr_btc": min_corr_btc,
                    "max_symbols": int(max_symbols),
                    "weights": {
                        "volume": weight_volume,
                        "atr_pct": weight_atr,
                        "beta": weight_beta,
                    },
                    "manual_override": [
                        item.strip() for item in manual_override.split(",") if item.strip()
                    ],
                },
                "market_quality": {
                    "min_trade_score": int(min_trade_score),
                    "reduced_risk_score": int(reduced_risk_score),
                    "spread_penalty": int(spread_penalty),
                    "atr_low_penalty": int(atr_low_penalty),
                    "adx_low_penalty": int(adx_low_penalty),
                    "wick_penalty": int(wick_penalty),
                    "liquidity_bonus": int(liquidity_bonus),
                    "direction_bonus": int(direction_bonus),
                },
                "execution": {
                    "execute_real_trades": execute_real_trades,
                    "entry_on": execution_entry_on,
                    "worst_case_same_candle": worst_case_same_candle,
                },
                "live": {
                    "loop_seconds": int(live_loop_seconds),
                    "timeframe": live_timeframe,
                    "candle_limit": int(live_candle_limit),
                },
            }
        )
        _write_yaml(CONFIG_PATH, config_payload)
        st.success("Configuração salva em config.yaml")

    return Settings.load(CONFIG_PATH)


def render_live_controls(settings: Settings) -> None:
    st.header("Execução Live (paper)")
    st.caption("Executa um ciclo de coleta e sinais em paper trading.")

    with st.form("live_form"):
        symbols_raw = st.text_input("Símbolos (CSV)", value="")
        max_symbols = st.number_input(
            "Máx símbolos", min_value=1, value=settings.universe.max_symbols, step=1
        )
        timeframe = st.text_input("Timeframe", value=settings.live.timeframe)
        run_once = st.form_submit_button("Rodar ciclo único")

    if run_once:
        symbols = [item.strip() for item in symbols_raw.split(",") if item.strip()] or None
        with st.spinner("Executando ciclo live..."):
            run_live(
                symbols=symbols,
                max_symbols=int(max_symbols),
                once=True,
                loop_seconds=settings.live.loop_seconds,
                timeframe=timeframe,
                settings=settings,
            )
        st.success("Ciclo finalizado.")


def render_backtest(settings: Settings) -> None:
    st.header("Backtest")
    st.caption("Backtest simples baseado em candles armazenados no SQLite.")

    with st.form("backtest_form"):
        symbol = st.text_input("Símbolo", value="BTC/USDT")
        timeframe = st.text_input("Timeframe", value=settings.live.timeframe)
        limit = st.number_input("Limite de candles", min_value=200, value=1000, step=100)
        min_window = st.number_input("Janela mínima", min_value=50, value=100, step=10)
        run_bt = st.form_submit_button("Executar backtest")

    if run_bt:
        repo = SQLiteRepository(str(settings.db_path))
        with st.spinner("Processando backtest..."):
            result = run_backtest(
                symbol=symbol,
                timeframe=timeframe,
                settings=settings,
                repo=repo,
                limit=int(limit),
                min_window=int(min_window),
            )
        st.success("Backtest concluído.")
        summary = result.summary
        st.metric("Trades", summary.total_trades)
        st.metric("Trades fechados", summary.closed_trades)
        st.metric("Winrate", f"{summary.winrate:.2%}")
        st.metric("Expectancy", f"{summary.expectancy:.4f}")
        st.metric("Max drawdown", f"{summary.max_drawdown:.4f}")

        if result.trades:
            trade_df = pd.DataFrame([trade.__dict__ for trade in result.trades])
            st.dataframe(trade_df, use_container_width=True)
        else:
            st.info("Sem trades para exibir.")


def render_observability(settings: Settings) -> None:
    st.header("Observabilidade")
    st.caption("Resumo rápido do que está acontecendo.")

    if not Path(settings.db_path).exists():
        st.warning("Banco de dados não encontrado. Execute o live para gerar dados.")
        return

    st.subheader("Sinais recentes")
    signals = _read_table(
        Path(settings.db_path),
        """
        SELECT symbol, timeframe, signal_time_ms, type, price, confidence
        FROM signals
        ORDER BY signal_time_ms DESC
        LIMIT 50
        """,
    )
    st.dataframe(signals, use_container_width=True)

    st.subheader("Trades simulados")
    trades = _read_table(
        Path(settings.db_path),
        """
        SELECT id, signal_id, direction, entry_price, stop_price, take_price, status, pnl_pct
        FROM trades_simulated
        ORDER BY id DESC
        LIMIT 50
        """,
    )
    st.dataframe(trades, use_container_width=True)

    st.subheader("Métricas diárias")
    metrics = _read_table(
        Path(settings.db_path),
        """
        SELECT day, trades_count, winrate, expectancy, max_drawdown
        FROM metrics_daily
        ORDER BY day DESC
        LIMIT 30
        """,
    )
    st.dataframe(metrics, use_container_width=True)


def main() -> None:
    st.set_page_config(page_title="TOB GUI", layout="wide")
    settings = Settings.load(CONFIG_PATH)

    render_sidebar(settings)
    render_api_keys(settings)
    settings = render_settings_editor(settings)
    render_live_controls(settings)
    render_backtest(settings)
    render_observability(settings)


if __name__ == "__main__":
    main()
