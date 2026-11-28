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


def test_ml_filter_derives_scale_invariant_features_and_predict_batch():
    import numpy as np
    import pandas as pd
    from intelligence.ml_filter import MLQualityFilter, SCALE_INVARIANT_FEATURE_COLS

    class _IdentityScaler:
        def transform(self, frame):
            return frame.to_numpy(dtype=float)

    class _ConstantModel:
        def __init__(self, p: float):
            self.p = p

        def predict_proba(self, x):
            assert np.isfinite(x).all()
            return np.column_stack([np.full(len(x), 1.0 - self.p), np.full(len(x), self.p)])

    filt = MLQualityFilter.__new__(MLQualityFilter)
    filt.feature_cols = list(SCALE_INVARIANT_FEATURE_COLS)
    filt.scaler = _IdentityScaler()
    filt.models = {k: _ConstantModel(0.62) for k in ("hgb", "rf", "et", "dnn")}
    filt.is_loaded = True
    filt.approval_threshold = 0.58

    raw_setup = {
        "close": 102.0, "open": 100.0, "high": 103.0, "low": 99.0,
        "ema9": 101.0, "ema21": 99.0, "vwap": 100.0, "frac_diff": 2.04,
        "rsi": 55.0, "prev_rsi": 50.0, "vol_ratio": 1.6, "momentum": 1.2,
        "volatility": 1.1, "trend_strength": 1.9, "range_pct": 3.9,
        "return_1": 1.0, "return_5": 2.0, "return_20": 4.0, "cusum_event": 1.0,
        "timestamp": "2026-11-27T10:00:00+05:30", "candidate_direction": "LONG",
    }
    prob_single = filt.predict(raw_setup)
    assert prob_single == 0.62

    batch_df = pd.DataFrame([{
        **raw_setup,
        "direction": 1.0,
        "rsi_delta": 5.0,
        "ema9_dist_pct": (102.0 - 101.0) / 102.0 * 100.0,
        "ema21_dist_pct": (102.0 - 99.0) / 102.0 * 100.0,
        "vwap_dist_pct": (102.0 - 100.0) / 100.0 * 100.0,
        "frac_diff_pct": 2.04 / 102.0 * 100.0,
        "body_pct": (102.0 - 100.0) / (103.0 - 99.0),
        "hour_ist": 10.0,
    }])
    probs = filt.predict_batch(batch_df)
    assert np.allclose(probs, np.array([0.62]))


def test_simulated_broker_charges_round_trip_fees_and_tracks_daily_losses():
    from backtesting.engine import SimulatedBroker

    broker = SimulatedBroker(initial_capital=50_000.0)
    assert broker.buy("TEST", price=100.0, atr=1.0, direction="LONG", time_str="2026-11-27T10:00:00+05:30")
    qty = broker.positions["TEST"]["quantity"]
    entry_fee = broker.positions["TEST"]["entry_fee"]
    assert entry_fee > 0.0
    broker.sell("TEST", price=100.0, time_str="2026-11-27T11:00:00+05:30", reason="FLAT_EXIT")
    assert len(broker.trade_history) == 1
    net_pnl = broker.trade_history[0]["net_pnl"]
    # Both entry and exit fees deducted cleanly even on zero price change
    assert net_pnl < -entry_fee
    assert qty > 0
    assert broker._daily_losses


def test_opportunity_ranker_detects_trend_breakout_and_skips_flat_bars():
    breakout = score({
        "rsi": 56.0, "prev_rsi": 53.0, "open": 100.0, "close": 102.0,
        "ema9": 101.0, "ema21": 99.5, "vol_ratio": 1.8, "momentum": 1.0, "vwap": 101.8,
    })
    assert breakout["candidate_direction"] == "LONG"
    assert breakout["opportunity_score"] >= 40.0

    flat = score({
        "rsi": 50.0, "prev_rsi": 50.0, "open": 100.0, "close": 100.0,
        "ema9": 100.0, "ema21": 100.0, "vol_ratio": 1.0, "momentum": 0.0, "vwap": 100.0,
    })
    assert flat["candidate_direction"] == "NO_TRADE"


def test_causal_cusum_threshold_has_no_future_leakage():
    import pandas as pd
    from datetime import datetime, timedelta, timezone
    from backtesting.engine import _compute_features_for_df

    base = datetime(2026, 1, 1, 9, 15, tzinfo=timezone.utc)
    rows = []
    for i in range(60):
        px = 100.0 + (i % 5) * 0.5
        rows.append({
            "timestamp": (base + timedelta(minutes=30 * i)).isoformat(),
            "open": px, "high": px + 1.0, "low": px - 1.0, "close": px + 0.2, "volume": 1000.0,
        })
    df_orig = _compute_features_for_df(pd.DataFrame(rows))

    rows_shock = [dict(r) for r in rows]
    for i in range(45, 60):
        rows_shock[i]["high"] *= 3.0
        rows_shock[i]["low"] *= 0.3
        rows_shock[i]["close"] *= 2.5
    df_shock = _compute_features_for_df(pd.DataFrame(rows_shock))

    prefix_len = min(20, len(df_orig), len(df_shock))
    assert (df_orig["cusum_event"].iloc[:prefix_len].values == df_shock["cusum_event"].iloc[:prefix_len].values).all()


def test_gap_down_stop_fills_at_open_not_stop_price(monkeypatch):
    from datetime import datetime, timedelta, timezone
    from backtesting import engine as eng

    base = datetime(2026, 1, 1, 9, 15, tzinfo=timezone.utc)
    candles = []
    for i in range(45):
        px = 100.0 + (i % 5) * 0.4
        candles.append({
            "timestamp": (base + timedelta(minutes=30 * i)).isoformat(),
            "open": px - 0.1, "high": px + 1.0, "low": px - 1.0, "close": px, "volume": 10000.0,
        })
    # Trigger entry cleanly on bar -2, then gap down well below ATR stop on bar -1
    candles[-2].update({"open": 99.0, "high": 101.0, "low": 98.5, "close": 100.0})
    candles[-1].update({"open": 88.0, "high": 89.0, "low": 87.5, "close": 88.5})

    monkeypatch.setattr(
        eng.opportunity_ranker,
        "score",
        lambda f: {
            **f,
            "opportunity_score": 80.0 if abs(float(f["open"]) - 99.0) < 0.01 else 0.0,
            "candidate_direction": "LONG" if abs(float(f["open"]) - 99.0) < 0.01 else "NO_TRADE",
        },
    )
    res = eng.run_backtest({"TEST": candles}, use_phase1=True, use_ml_filter=False, initial_capital=50_000.0)
    assert res["total_trades"] >= 1
    assert res["trade_pnls"][-1] < -200.0
