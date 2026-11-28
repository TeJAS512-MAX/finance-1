from __future__ import annotations

import json

import pandas as pd
import pytest

from backtesting import yahoo_historical_fetcher as fetcher


def test_refresh_returns_only_newly_downloaded_symbols_and_keeps_cache(
    monkeypatch, tmp_path
):
    cache_file = tmp_path / "historical.json"
    cache_file.write_text(json.dumps({"STALE": [{"timestamp": "old"}]}))
    monkeypatch.setattr(fetcher, "CACHE_FILE", cache_file)
    monkeypatch.setattr(fetcher, "INSTRUMENT_KEYS", {"TEST": "NSE_EQ|TEST"})

    def download(ticker, **kwargs):
        assert ticker == "TEST.NS"
        assert kwargs["auto_adjust"] is True
        return pd.DataFrame(
            {
                "Open": [10.0, 11.0],
                "High": [12.0, 13.0],
                "Low": [9.0, 10.0],
                "Close": [11.0, 12.0],
                "Volume": [100, 110],
            },
            index=pd.to_datetime(["2026-11-25", "2026-11-26"]),
        )

    monkeypatch.setattr(fetcher.yf, "download", download)

    fresh = fetcher.fetch_yahoo_daily_data(fresh_only=True)
    saved = json.loads(cache_file.read_text())

    assert set(fresh) == {"TEST"}
    assert "STALE" in saved
    assert saved["TEST"][-1]["close"] == 12.0


def test_failed_refresh_does_not_overwrite_existing_history(monkeypatch, tmp_path):
    cache_file = tmp_path / "historical.json"
    original = json.dumps({"TEST": [{"timestamp": "old"}]})
    cache_file.write_text(original)
    monkeypatch.setattr(fetcher, "CACHE_FILE", cache_file)
    monkeypatch.setattr(fetcher, "INSTRUMENT_KEYS", {"TEST": "NSE_EQ|TEST"})
    def empty_download(ticker, **kwargs):
        assert ticker == "TEST.NS"
        assert kwargs["auto_adjust"] is True
        return pd.DataFrame()

    monkeypatch.setattr(fetcher.yf, "download", empty_download)

    with pytest.raises(RuntimeError, match="no fresh valid daily candles"):
        fetcher.fetch_yahoo_daily_data(fresh_only=True)

    assert cache_file.read_text() == original
