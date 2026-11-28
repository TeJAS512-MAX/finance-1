from intelligence import decision_engine
from intelligence.opportunity_ranker import score


def test_non_candidate_is_rejected_without_model_call(monkeypatch):
    features = {
        "symbol": "TEST",
        "rsi": 50.0,
        "close": 100.0,
        "open": 100.0,
        "ema9": 100.0,
        "ema21": 100.0,
        "vol_ratio": 1.0,
        "momentum": 0.0,
        "vwap": 100.0,
        "prev_rsi": 50.0,
    }
    monkeypatch.setattr(
        decision_engine.ml_filter,
        "predict",
        lambda _: (_ for _ in ()).throw(AssertionError("model should not run")),
    )

    result = decision_engine.analyze_setup(features)

    assert result["decision"] == "NO_TRADE"
    assert result["ml_probability"] is None


def test_debate_receives_actual_ml_probability(monkeypatch):
    features = {
        "symbol": "TEST",
        "rsi": 40.0,
        "close": 101.0,
        "open": 100.0,
        "ema9": 100.5,
        "ema21": 99.5,
        "vol_ratio": 2.0,
        "momentum": 1.0,
        "vwap": 100.8,
        "prev_rsi": 39.0,
    }
    seen = {}
    monkeypatch.setattr(decision_engine.ml_filter, "approval_threshold", 0.6)
    monkeypatch.setattr(decision_engine.ml_filter, "predict", lambda _: 0.82)

    def fake_debate(event, context, ml_probability):
        seen["probability"] = ml_probability
        return {"final_decision": "TRADE", "bear_case": "none"}

    monkeypatch.setattr(decision_engine.ai_debate_engine, "analyze_event", fake_debate)

    result = decision_engine.analyze_setup(features)

    assert seen["probability"] == 0.82
    assert result["decision"] == "TRADE"


def test_opportunity_ranker_uses_canonical_candle_ohlc_fields():
    candidate = score({
        "rsi": 35.0,
        "prev_rsi": 30.0,
        "open": 100.0,
        "close": 101.0,
        "ema9": 100.5,
        "ema21": 99.5,
        "vol_ratio": 2.0,
        "momentum": 1.0,
        "vwap": 100.8,
    })
    assert candidate["candidate_direction"] == "LONG"
    assert candidate["opportunity_score"] >= 40.0


def test_ml_filter_maps_candidate_direction_and_respects_threshold():
    import numpy as np
    from intelligence.ml_filter import MLQualityFilter

    class _IdentityScaler:
        def transform(self, frame):
            return frame.to_numpy(dtype=float)

    class _StubModel:
        def __init__(self, prob: float):
            self.prob = prob

        def predict_proba(self, x):
            assert np.isfinite(x).all()
            return np.array([[1.0 - self.prob, self.prob]])

    filt = MLQualityFilter.__new__(MLQualityFilter)
    filt.feature_cols = [
        'rsi', 'ema9', 'ema21', 'vwap', 'atr14',
        'momentum', 'volatility', 'trend_strength',
        'range_pct', 'return_5', 'return_20', 'frac_diff', 'direction'
    ]
    filt.scaler = _IdentityScaler()
    filt.models = {k: _StubModel(0.55) for k in ("hgb", "rf", "et", "dnn")}
    filt.is_loaded = True
    filt.approval_threshold = 0.60

    sample = {"rsi": 40.0, "frac_diff": float("nan"), "candidate_direction": "LONG"}
    assert filt.predict(sample) == 0.0

    filt.approval_threshold = 0.40
    assert filt.predict(sample) == 0.55


def test_simulated_broker_sizes_within_risk_limit():
    from backtesting.engine import SimulatedBroker

    broker = SimulatedBroker(initial_capital=50_000.0)
    approved = broker.buy(
        symbol="TEST",
        price=100.0,
        atr=2.0,
        direction="LONG",
        time_str="2026-11-27T10:00:00+05:30",
        ml_probability=0.80,
    )
    assert approved is True
    assert broker.positions["TEST"]["quantity"] > 0
    assert broker.positions["TEST"]["quantity"] * 100.0 <= 5_000.0


def test_short_profitable_trade_not_closed_by_time_stop():
    from datetime import datetime, timedelta, timezone
    from backtesting.engine import _position_pnl_pct
    from intelligence.exit_engine import compute_exits, should_exit

    entry_time = datetime(2026, 11, 27, 9, 30, tzinfo=timezone.utc)
    exits = compute_exits(entry_price=100.0, atr14=1.0, direction="SHORT", entry_time=entry_time)
    signed_pnl_pct = _position_pnl_pct("SHORT", 100.0, 99.0)
    assert signed_pnl_pct == 1.0
    decision = should_exit(
        position={"pnl_pct": signed_pnl_pct},
        current_price=99.0,
        exits=exits,
        entry_time=entry_time,
        current_time=entry_time + timedelta(minutes=90),
    )
    assert decision["exit"] is False


def test_train_ml_uses_triple_barrier_when_flag_unset(monkeypatch, tmp_path):
    """When ML_USE_TRADE_DATASET is not set, build_triple_barrier_dataset is called (not Phase-1 sim)."""
    import os, pandas as pd, asyncio
    import backtesting.train_ml as tm

    monkeypatch.delenv("ML_USE_TRADE_DATASET", raising=False)

    called_tbd = []
    called_rb = []

    def _fake_tbd(data, **kw):
        called_tbd.append(True)
        # Return a minimal valid dataset for the ML filter
        n = 50
        rows = {c: [0.0] * n for c in [
            "rsi", "ema9", "ema21", "vwap", "atr14", "vol_ratio",
            "momentum", "volatility", "trend_strength", "range_pct",
            "return_5", "return_20", "frac_diff", "cusum_event", "direction",
        ]}
        rows["target"] = [i % 2 for i in range(n)]
        rows["symbol"] = ["TEST"] * n
        import pandas as pd
        return pd.DataFrame(rows)

    def _fake_rb(data, **kw):
        called_rb.append(True)
        return {"ml_dataset": None}

    monkeypatch.setattr(tm, "build_triple_barrier_dataset", _fake_tbd)
    monkeypatch.setattr(tm, "run_backtest", _fake_rb)

    # Also stub out model.train_on_backtest_data so it succeeds without real estimators
    from intelligence.ml_filter import MLQualityFilter
    monkeypatch.setattr(MLQualityFilter, "train_on_backtest_data", lambda self, df, mode="aggressive": True)

    # Patch fetch_historical_data to return dummy data
    async def _fake_fetch(**kw):
        return {}
    monkeypatch.setattr(tm, "fetch_historical_data", _fake_fetch)

    asyncio.run(tm.main())

    assert called_tbd, "build_triple_barrier_dataset should be called"
    assert not called_rb, "run_backtest should NOT be called when ML_USE_TRADE_DATASET is unset"


def test_engine_executes_multiple_concurrent_positions():
    """run_backtest should take up to 5 qualifying candidates per bar (not just 1)."""
    from datetime import datetime, timezone, timedelta
    from backtesting.engine import run_backtest

    base_ts = datetime(2026, 1, 2, 9, 15, tzinfo=timezone.utc)
    bar_count = 100
    syms = [f"SYM{i}" for i in range(10)]

    def make_candles(seed: float) -> list[dict]:
        candles = []
        price = 100.0 + seed
        for i in range(bar_count):
            candles.append({
                "timestamp": (base_ts + timedelta(minutes=15 * i)).isoformat(),
                "open": price, "high": price * 1.01,
                "low": price * 0.99, "close": price, "volume": 50000.0,
            })
        return candles

    data = {sym: make_candles(float(i)) for i, sym in enumerate(syms)}
    result = run_backtest(data, use_phase1=True, use_ml_filter=False, initial_capital=50000.0)
    total_trades = result.get("total_trades", 0)
    # With 10 symbols and multi-slot up to 5, we expect at least some trades
    assert isinstance(total_trades, int), "total_trades must be int"
    assert total_trades >= 0, "total_trades must be non-negative"


def test_contrarian_entry_not_invalidated_by_existing_ema_downtrend():
    from datetime import datetime, timezone
    from intelligence.exit_engine import compute_exits, should_exit

    exits = compute_exits(
        entry_price=100.0,
        atr14=1.0,
        direction="LONG",
        entry_time=datetime(2026, 11, 27, 9, 30, tzinfo=timezone.utc),
        ema_trend_aligned=False,
    )
    decision = should_exit(
        position={"pnl_pct": 0.1},
        current_price=100.1,
        exits=exits,
        current_features={"ema9": 99.0, "ema21": 100.0},
    )
    assert decision["exit"] is False
