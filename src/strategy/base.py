"""Strategy interfaces and models."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd


@dataclass
class Signal:
    symbol: str
    direction: str  # LONG, SHORT, NONE
    price: float
    confidence: float
    reasons: dict[str, Any]


class Strategy:
    name: str

    def generate(self, symbol: str, df: pd.DataFrame, settings: Any) -> Signal:
        raise NotImplementedError

