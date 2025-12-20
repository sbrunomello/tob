from risk.adaptive import AdaptiveState, adjust_risk, update_streak


def test_adaptive_risk_reduction():
    state = AdaptiveState()
    base_risk = 0.01
    for _ in range(3):
        update_streak(state, pnl=-1)
    reduced = adjust_risk(base_risk, state)
    assert reduced < base_risk

    state.weekly_drawdown = 0.2
    defensive = adjust_risk(base_risk, state)
    assert defensive < reduced
    assert state.defensive_mode is True
