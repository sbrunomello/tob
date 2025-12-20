"""Hard risk rules and limits."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict


@dataclass
class RiskRules:
    max_daily_loss_r: float
    max_positions: int
    cooldown_candles: int

    daily_loss_r: float = 0.0
    positions_open: int = 0
    cooldowns: Dict[str, int] = field(default_factory=dict)
    kill_switch: bool = False

    def register_trade_result(self, pnl_r: float) -> None:
        self.daily_loss_r += min(0.0, pnl_r)
        if abs(self.daily_loss_r) >= self.max_daily_loss_r:
            self.kill_switch = True

    def can_open(self, symbol: str) -> bool:
        if self.kill_switch:
            return False
        if self.positions_open >= self.max_positions:
            return False
        if self.cooldowns.get(symbol, 0) > 0:
            return False
        return True

    def tick(self) -> None:
        for symbol in list(self.cooldowns.keys()):
            self.cooldowns[symbol] = max(0, self.cooldowns[symbol] - 1)

    def apply_cooldown(self, symbol: str) -> None:
        self.cooldowns[symbol] = self.cooldown_candles

