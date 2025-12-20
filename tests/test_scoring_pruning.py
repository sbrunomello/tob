from strategy.scoring import compute_performance, should_disable


def test_scoring_and_pruning():
    pnls = [1, -0.5, 0.2, -0.3, 0.4]
    perf = compute_performance(pnls)
    assert perf.expectancy != 0
    assert 0 <= perf.winrate <= 1

    assert should_disable(-0.1, trades=30, min_trades=30) is True
    assert should_disable(0.1, trades=30, min_trades=30) is False
