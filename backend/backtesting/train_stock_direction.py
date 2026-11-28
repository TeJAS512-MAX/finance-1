"""Train and evaluate the research-only next-session net-return candidate."""

from __future__ import annotations

import asyncio
import json
import os
import shutil
from pathlib import Path
from tempfile import TemporaryDirectory

from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv())

from backtesting.upstox_stock_history import (
    MAX_DAILY_HISTORY_DAYS,
    fetch_upstox_daily_data,
)
from intelligence.stock_direction import (
    METADATA_PATH,
    MODEL_PATH,
    SHADOW_MODEL_PATH,
    train_stock_direction_candidate,
)

TRAINING_REPORT_PATH = MODEL_PATH.with_name("stock_direction_last_training_report.json")


def main() -> None:
    days_back = int(
        os.environ.get("STOCK_DIRECTION_DAYS_BACK", str(MAX_DAILY_HISTORY_DAYS))
    )
    configured_symbols = os.environ.get("STOCK_DIRECTION_SYMBOLS", "").strip()
    symbols = (
        [symbol.strip().upper() for symbol in configured_symbols.split(",") if symbol.strip()]
        if configured_symbols
        else None
    )
    historical_data, data_report = asyncio.run(
        fetch_upstox_daily_data(days_back=days_back, symbols=symbols)
    )
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(
        prefix="stock_direction_candidate_", dir=MODEL_PATH.parent
    ) as staging_dir:
        staged_model = Path(staging_dir) / MODEL_PATH.name
        staged_metadata = Path(staging_dir) / METADATA_PATH.name
        report = train_stock_direction_candidate(
            historical_data,
            model_path=staged_model,
            metadata_path=staged_metadata,
            data_source=data_report["provider"],
            data_report=data_report,
            training_sessions=None,
            test_sessions=90,
            allow_historical_promotion=False,
        )
        shadow_temporary_path = SHADOW_MODEL_PATH.with_suffix(
            SHADOW_MODEL_PATH.suffix + ".tmp"
        )
        shutil.copy2(staged_model, shadow_temporary_path)
        shadow_temporary_path.replace(SHADOW_MODEL_PATH)
        report["shadow_candidate_saved"] = True
        report["shadow_candidate_file"] = SHADOW_MODEL_PATH.name
        if report["eligible_for_live_display"]:
            staged_model.replace(MODEL_PATH)
            staged_metadata.replace(METADATA_PATH)

    temporary_report_path = TRAINING_REPORT_PATH.with_suffix(
        TRAINING_REPORT_PATH.suffix + ".tmp"
    )
    temporary_report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    temporary_report_path.replace(TRAINING_REPORT_PATH)

    print(json.dumps(report, indent=2))
    if report["eligible_for_live_display"]:
        print(
            "\nCandidate passed the gate and replaced the research-display model; "
            "a shadow copy was also saved."
        )
    elif not report["historical_promotion_enabled"]:
        print(
            "\nThe previously inspected historical holdout cannot promote this model. "
            "The separate shadow candidate is available for forward evaluation."
        )
    else:
        print(
            "\nCandidate did not pass the display gate. The installed model was preserved; "
            "the separate shadow candidate is available for forward evaluation."
        )


if __name__ == "__main__":
    main()
