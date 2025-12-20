import numpy as np
import pandas as pd

from market.clusters import build_clusters


def test_cluster_building():
    data = {
        "A": np.linspace(1, 2, 50),
        "B": np.linspace(1.01, 2.01, 50),
        "C": np.linspace(2, 1, 50),
    }
    returns = pd.DataFrame(data).pct_change().dropna()
    result = build_clusters(returns, threshold=0.8)
    assert result.clusters["A"] == result.clusters["B"]
