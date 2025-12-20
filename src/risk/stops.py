"""Stop-loss and take-profit helpers."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Stops:
    stop: float
    take: float


def atr_stops(entry: float, atr_value: float, direction: str, stop_mult: float, take_mult: float) -> Stops:
    if direction == "LONG":
        stop = entry - atr_value * stop_mult
        take = entry + atr_value * take_mult
    else:
        stop = entry + atr_value * stop_mult
        take = entry - atr_value * take_mult
    return Stops(stop=stop, take=take)

