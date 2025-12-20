"""Rate limit guard with backoff and circuit breaker."""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable

from loguru import logger


@dataclass
class CircuitBreaker:
    max_failures: int = 5
    cooldown_seconds: int = 30
    failures: int = 0
    opened_at: float | None = None

    def can_execute(self) -> bool:
        if self.opened_at is None:
            return True
        if time.time() - self.opened_at > self.cooldown_seconds:
            self.failures = 0
            self.opened_at = None
            return True
        return False

    def record_failure(self) -> None:
        self.failures += 1
        if self.failures >= self.max_failures:
            self.opened_at = time.time()

    def record_success(self) -> None:
        self.failures = 0
        self.opened_at = None


class RateLimitGuard:
    """Simple retry/backoff guard for exchange calls."""

    def __init__(self, breaker: CircuitBreaker | None = None, max_retries: int = 4) -> None:
        self.breaker = breaker or CircuitBreaker()
        self.max_retries = max_retries

    def run(self, func: Callable[..., Any], *args: Any, context: dict[str, Any] | None = None, **kwargs: Any) -> Any:
        if not self.breaker.can_execute():
            raise RuntimeError("Circuit breaker open")
        context = context or {}
        delay = 1.0
        for attempt in range(1, self.max_retries + 1):
            try:
                result = func(*args, **kwargs)
                self.breaker.record_success()
                return result
            except Exception as exc:  # noqa: BLE001 - network errors vary
                self.breaker.record_failure()
                logger.warning(
                    "rate_limit_guard_error attempt={} error={} context={}",
                    attempt,
                    exc,
                    context,
                )
                if attempt == self.max_retries:
                    raise
                time.sleep(delay)
                delay *= 2

