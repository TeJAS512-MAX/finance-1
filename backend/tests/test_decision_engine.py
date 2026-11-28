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
