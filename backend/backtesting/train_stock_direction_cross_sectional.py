"""Train a separate research-only regime-aware cross-sectional challenger."""

from __future__ import annotations

import asyncio
import json

from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv())

from backtesting.upstox_stock_history import fetch_upstox_daily_data
from intelligence.stock_direction_cross_sectional import (
    train_cross_sectional_candidate,
)


def main() -> None:
    historical_data, data_report = asyncio.run(fetch_upstox_daily_data())
    report = train_cross_sectional_candidate(
        historical_data,
        data_source=data_report["provider"],
        data_report=data_report,
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
