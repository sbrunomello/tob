"""Daily reporting utilities."""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any


def generate_daily_report(metrics: dict[str, Any], strategies: dict[str, Any]) -> str:
    payload = {
        "date": datetime.utcnow().strftime("%Y-%m-%d"),
        "metrics": metrics,
        "strategies": strategies,
    }
    return json.dumps(payload, indent=2)

