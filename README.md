# TOB - Trading Orchestration for Binance USDⓈ-M Futures

Plataforma local de trading algorítmico **paper por padrão** (sem ordens reais), focada em capital pequeno e sobrevivência. Inclui seleção dinâmica de ativos (Universe Builder), filtros de regime, confluência (ensemble), engine de risco, execução simulada e executor real desativado por padrão.

> **NÃO NEGOCIÁVEL**: por padrão `EXECUTE_REAL_TRADES=false` e nenhuma ordem real é enviada.

## Stack
- Python 3.12
- CCXT (Binance USDⓈ-M Futures)
- pandas, numpy, ta
- loguru
- pydantic / pydantic-settings
- sqlite3
- pytest

## Setup (Poetry)
```bash
poetry install
```

## Configuração
- Defaults: `src/config/defaults.yaml`
- Config custom (opcional): crie `config.yaml` e passe para o carregamento manual no código.

### Variáveis de ambiente
- `TOB_BINANCE_API_KEY` (opcional no paper)
- `TOB_BINANCE_API_SECRET` (opcional no paper)
- `TOB_EXECUTE_REAL_TRADES` (default: false)

**Segurança:** não há segredos hardcoded.

## Executando
```bash
poetry run tob run
```

### Outros comandos
```bash
poetry run tob backtest
poetry run tob report
poetry run tob universe
poetry run tob healthcheck
```

## Trading real (feature-flag)
Para habilitar execução real (NÃO recomendado por padrão):
```bash
export TOB_EXECUTE_REAL_TRADES=true
```

## Banco de dados
O SQLite é criado automaticamente em `data/tob.sqlite`.

## Testes
```bash
poetry run pytest
```

## Aviso de risco
Trading envolve risco significativo de perda. Este projeto é educacional e **não** fornece garantia de lucro.
