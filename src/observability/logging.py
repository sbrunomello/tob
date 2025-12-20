"""Logging setup."""
from __future__ import annotations

import sys

from loguru import logger


def configure_logging(json_logs: bool) -> None:
    logger.remove()
    if json_logs:
        logger.add(sys.stdout, serialize=True)
    else:
        logger.add(sys.stdout, format="{time} | {level} | {message}")

