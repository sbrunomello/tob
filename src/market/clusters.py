"""Cluster risk management based on rolling correlations."""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass
class ClusterResult:
    clusters: dict[str, int]
    matrix: pd.DataFrame


def _union_find(items: list[str], pairs: list[tuple[str, str]]) -> dict[str, int]:
    parent = {item: item for item in items}

    def find(item: str) -> str:
        while parent[item] != item:
            parent[item] = parent[parent[item]]
            item = parent[item]
        return item

    def union(a: str, b: str) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    for a, b in pairs:
        union(a, b)

    root_map: dict[str, int] = {}
    clusters: dict[str, int] = {}
    next_id = 0
    for item in items:
        root = find(item)
        if root not in root_map:
            root_map[root] = next_id
            next_id += 1
        clusters[item] = root_map[root]
    return clusters


def build_clusters(returns: pd.DataFrame, threshold: float) -> ClusterResult:
    corr = returns.corr()
    pairs: list[tuple[str, str]] = []
    symbols = list(corr.columns)
    for i, sym_a in enumerate(symbols):
        for sym_b in symbols[i + 1 :]:
            if corr.loc[sym_a, sym_b] >= threshold:
                pairs.append((sym_a, sym_b))
    clusters = _union_find(symbols, pairs)
    return ClusterResult(clusters, corr)

