from execution.paper import simulate_trade


def test_paper_execution_worst_case():
    result = simulate_trade(
        direction="LONG",
        entry_price=100,
        stop_price=95,
        take_price=105,
        candle_high=106,
        candle_low=94,
        fee_rate=0.0004,
        worst_case_same_candle=True,
    )
    assert result.status == "STOP"


def test_paper_execution_take():
    result = simulate_trade(
        direction="SHORT",
        entry_price=100,
        stop_price=105,
        take_price=95,
        candle_high=103,
        candle_low=94,
        fee_rate=0.0004,
        worst_case_same_candle=True,
    )
    assert result.status == "TAKE"
