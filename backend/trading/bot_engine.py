import asyncio
import os
import json
from datetime import datetime, timezone
from typing import List, Dict, Optional
from risk.risk_manager import RiskManager
from services.providers.upstox_market_data import get_live_quote


SYMBOL_SECTORS: Dict[str, str] = {
    "TCS": "IT", "INFY": "IT", "WIPRO": "IT", "HCLTECH": "IT", "TECHM": "IT",
    "LTIM": "IT", "PERSISTENT": "IT", "COFORGE": "IT",
    "SBIN": "BANKING_FINANCE", "ICICIBANK": "BANKING_FINANCE", "HDFCBANK": "BANKING_FINANCE",
    "BAJFINANCE": "BANKING_FINANCE", "AXISBANK": "BANKING_FINANCE", "KOTAKBANK": "BANKING_FINANCE",
    "BAJAJFINSV": "BANKING_FINANCE", "CHOLAFIN": "BANKING_FINANCE", "SHRIRAMFIN": "BANKING_FINANCE",
    "BANKBARODA": "BANKING_FINANCE", "PNB": "BANKING_FINANCE",
    "RELIANCE": "ENERGY_POWER", "NTPC": "ENERGY_POWER", "POWERGRID": "ENERGY_POWER",
    "COALINDIA": "ENERGY_POWER", "ONGC": "ENERGY_POWER", "TATAPOWER": "ENERGY_POWER", "GAIL": "ENERGY_POWER",
    "MARUTI": "AUTO", "M&M": "AUTO", "EICHERMOT": "AUTO", "BAJAJ-AUTO": "AUTO",
    "HEROMOTOCO": "AUTO", "TVSMOTOR": "AUTO",
    "ITC": "CONSUMER", "TITAN": "CONSUMER", "ASIANPAINT": "CONSUMER",
    "HINDUNILVR": "CONSUMER", "NESTLEIND": "CONSUMER", "ZOMATO": "CONSUMER", "TRENT": "CONSUMER",
    "BRITANNIA": "CONSUMER", "GODREJCP": "CONSUMER", "DABUR": "CONSUMER", "VBL": "CONSUMER", "COLPAL": "CONSUMER",
    "SUNPHARMA": "PHARMA", "DRREDDY": "PHARMA", "CIPLA": "PHARMA",
    "DIVISLAB": "PHARMA", "APOLLOHOSP": "PHARMA", "TORNTPHARM": "PHARMA", "LUPIN": "PHARMA",
    "LT": "METALS_IND", "ULTRACEMCO": "METALS_IND", "TATASTEEL": "METALS_IND",
    "JSWSTEEL": "METALS_IND", "ADANIPORTS": "METALS_IND", "GRASIM": "METALS_IND", "BEL": "METALS_IND",
    "HAL": "INDUSTRIALS", "SIEMENS": "INDUSTRIALS", "ABB": "INDUSTRIALS", "BHEL": "INDUSTRIALS",
    "PIDILITIND": "INDUSTRIALS", "HAVELLS": "INDUSTRIALS", "DLF": "REALTY", "INDIGO": "AVIATION",
    "BHARTIARTL": "TELECOM",
}


class AITradingEngine:
    def __init__(self):
        self.is_running = False
        self.logs: List[Dict] = []
        self.trade_journal: List[Dict] = []
        self.task = None
        self.broker = None  # Shared broker instance — used by portfolio API too
        self.market_mode = "stocks"
        # Track open position exit levels keyed by symbol
        self._exit_plans: Dict[str, Dict] = {}
        self._entry_times: Dict[str, datetime] = {}
        self.manifest = self._load_manifest()
        self.risk_manager = RiskManager()
        self.consecutive_losses = 0
        self.daily_realised_loss = 0.0
        self.trading_date = None
        self.regime_stats = {
            "trending": {"trades": 0, "wins": 0, "pnl": 0.0},
            "ranging": {"trades": 0, "wins": 0, "pnl": 0.0},
            "high_volatility": {"trades": 0, "wins": 0, "pnl": 0.0},
            "low_volatility": {"trades": 0, "wins": 0, "pnl": 0.0},
        }

    def _load_manifest(self):
        manifest_path = os.path.join(os.path.dirname(__file__), "..", "core", "freeze_manifest.json")
        try:
            with open(manifest_path, "r") as f:
                return json.load(f)
        except Exception:
            return {"model_version": "UNKNOWN", "strategy_parameters": {"ml_probability_threshold": 0.6}}

    def add_log(self, level: str, message: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        # Safely encode to ASCII to prevent UnicodeEncodeError on Windows cp1252
        safe_message = message.encode("ascii", errors="replace").decode("ascii")
        self.logs.append({"time": timestamp, "level": level, "message": safe_message})
        if len(self.logs) > 200:
            self.logs = self.logs[-200:]

    def start(self, market_mode: str = "stocks"):
        if not self.is_running:
            if market_mode not in {"stocks", "crypto"}:
                raise ValueError("market_mode must be 'stocks' or 'crypto'")
            self.market_mode = market_mode
            if market_mode == "crypto":
                self.add_log("WARN", "[CRYPTO] CoinDCX adapter is not configured. Stock engine remains unchanged.")
                return False

            self.is_running = True
            model_ver = self.manifest.get('model_version', 'Phase-1')
            ml_thresh = self.manifest.get('strategy_parameters', {}).get('ml_probability_threshold', 0.6)
            self.add_log("INFO", f"[START] AI Trading Engine ({model_ver}) Started from Web Dashboard")
            self.add_log("INFO", f"[FROZEN] MANIFEST LOADED. ML Threshold: {ml_thresh}")
            
            # --- Data Integrity Kill-Switches ---
            self.kill_switches = {
                "LIVE_TRADING_ENABLED": False,
                "PAPER_TRADING_ENABLED": True,
                "PIT_VIOLATION_KILL": True,
                "STALE_DATA_KILL": True,
                "MISSING_EVENT_TIMESTAMP_KILL": False,
                "INVALID_MODEL_VERSION_KILL": True
            }
            if self.kill_switches["INVALID_MODEL_VERSION_KILL"] and model_ver == "UNKNOWN":
                self.add_log("ERROR", "[FATAL] Invalid Model Version in manifest. Stopping engine.")
                self.is_running = False
                return

            self.task = asyncio.create_task(self._trade_loop())
            return True
        return False

    def stop(self):
        if self.is_running:
            self.is_running = False
            self.add_log("WARN", "[STOP] AI Trading Engine Stopped")
            if self.task:
                self.task.cancel()
                self.task = None

    async def _trade_loop(self):
        try:
            from core.config import get_settings
            settings = get_settings()

            if settings.live_trading_enabled:
                from trading.live_broker import LiveBroker
                broker = LiveBroker(
                    api_key=os.environ.get("UPSTOX_API_KEY", ""),
                    api_secret=os.environ.get("UPSTOX_API_SECRET", ""),
                    redirect_uri="https://127.0.0.1"
                )
                self.add_log("WARN", "[LIVE] LIVE TRADING ENABLED. Using Real Upstox Account.")
            else:
                from trading.paper_broker import PaperBroker
                broker = PaperBroker(market_mode=self.market_mode)
                self.add_log("INFO", f"[PAPER] PAPER TRADING ENABLED. Capital: Rs.{settings.paper_trading_initial_capital}")

            self.broker = broker

            from services.providers.upstox_market_data import INSTRUMENT_KEYS

            # Full watchlist synced with canonical Upstox instrument keys
            INSTRUMENTS = dict(INSTRUMENT_KEYS)

            account = await broker.get_account()
            self.add_log("INFO", f"[OK] Broker connected. Cash: Rs.{account.get('cash', 0):.2f}")

        except Exception as e:
            import traceback
            self.add_log("ERROR", f"CRITICAL BOOT ERROR: {e}")
            self.add_log("ERROR", traceback.format_exc())
            self.is_running = False
            return

        # ── Intelligence imports (done once here for performance) ──────────────
        try:
            from services.providers.upstox_market_data import compute_features
            from intelligence import strategy_v1, opportunity_ranker, exit_engine
            from intelligence.ml_filter import ml_filter
            from intelligence.event_radar import event_radar
            from intelligence.ai_debate import ai_debate_engine
            from intelligence.rss_ingester import ingest_public_news
        except Exception as e:
            import traceback
            self.add_log("ERROR", f"CRITICAL IMPORT ERROR: {e}")
            self.add_log("ERROR", traceback.format_exc())
            self.is_running = False
            return

        # ── Main Loop ──────────────────────────────────────────────────────────
        while self.is_running:
            try:
                self.add_log("INFO", "=" * 55)
                self.add_log("INFO", f"🔍 FULL WATCHLIST SCAN — {datetime.now().strftime('%H:%M:%S')}")
                
                # Check date rollover
                import zoneinfo
                current_date = datetime.now(zoneinfo.ZoneInfo("Asia/Kolkata")).date()
                if self.trading_date != current_date:
                    self.trading_date = current_date
                    self.daily_realised_loss = 0.0
                    self.consecutive_losses = 0
                    self.add_log("INFO", "🌅 New trading day! Resetting daily loss trackers.")

                # ── STEP 0: Ingest Real Public News ────────────────────────────
                try:
                    await ingest_public_news()
                except Exception as e:
                    self.add_log("WARN", f"  ⚠ RSS Ingestion failed: {e}")

                # ── STEP 1: Fetch features for ALL symbols with concurrency bound ─────────
                processing_start_time = datetime.now(timezone.utc)
                sem = asyncio.Semaphore(6)
                async def fetch(sym):
                    async with sem:
                        try:
                            return await compute_features(sym, interval="30m")
                        except Exception as e:
                            message = str(e)
                            if "No candle data returned" in message:
                                return None
                            self.add_log("WARN", f"  ⚠ {sym}: data fetch failed — {e}")
                            return None

                raw_results = await asyncio.gather(*[fetch(s) for s in INSTRUMENTS])
                all_features = [r for r in raw_results if r is not None]

                if not all_features:
                    self.add_log("WARN", "⚠️  No data fetched. Market closed or token expired. Waiting 60s...")
                    await asyncio.sleep(60)
                    continue

                self.add_log("INFO", f"📊 Got data for {len(all_features)}/{len(INSTRUMENTS)} symbols")

                # Mark open paper positions to the newest observed price before
                # evaluating exits. Only query live quotes for held tickers to stay
                # within Upstox rate limits, falling back to candle close on error/0.
                if getattr(broker, "is_paper", False):
                    held_positions = await broker.get_positions()
                    held_tickers = {p.get("ticker", p.get("symbol", "")) for p in held_positions}
                    for feat in all_features:
                        token_key = INSTRUMENTS.get(feat["symbol"], feat["symbol"])
                        fallback_ltp = feat.get("ltp")
                        if token_key in held_tickers or feat["symbol"] in held_tickers:
                            try:
                                live_q = await get_live_quote(feat["symbol"])
                                live_ltp = live_q.get("ltp")
                                px = live_ltp if (live_ltp and live_ltp > 0) else fallback_ltp
                            except Exception:
                                px = fallback_ltp
                        else:
                            px = fallback_ltp
                        if px and px > 0:
                            broker.update_price(token_key, px)

                # ── STEP 2: Run strategy_v1 (SHADOW — no execution) ───────────
                self.add_log("INFO", "🔶 [BASELINE v1] Running shadow RSI/SMA evaluation...")
                v1_decisions = {}
                for feat in all_features:
                    v1_dec = strategy_v1.evaluate(feat)
                    v1_decisions[feat["symbol"]] = v1_dec
                    action = "▲ WOULD BUY" if v1_dec["would_execute"] else "— skip"
                    self.add_log(
                        "INFO",
                        f"  [v1] {feat['symbol']:12s} RSI={feat['rsi']:5.1f} | "
                        f"conf={v1_dec['confidence']:4.1f}% | {action}"
                    )
                v1_would_buys = [s for s, d in v1_decisions.items() if d["would_execute"]]
                self.add_log("INFO", f"  [v1] Would trade: {v1_would_buys or 'NONE (sitting out)'}")

                # -- STEP 3: Phase-1 -- Score and rank all symbols --
                self.add_log("INFO", "[PHASE-1] Scoring opportunities...")
                
                # Integrity check: Stale Data Kill-Switch
                valid_features = []
                for f in all_features:
                    candle_ts = f.get('timestamp')
                    if not candle_ts:
                        if self.kill_switches.get("STALE_DATA_KILL"):
                            self.add_log("WARN", f"  [KILL] [{f['symbol']}] STALE_DATA_KILL: Missing candle timestamp")
                            continue
                    
                    if candle_ts and candle_ts > processing_start_time.isoformat():
                        if self.kill_switches.get("PIT_VIOLATION_KILL"):
                            self.add_log("WARN", f"  [KILL] [{f['symbol']}] PIT_VIOLATION_KILL: Candle TS ahead of cutoff")
                            continue
                            
                    valid_features.append(f)

                # Evaluate Phase-2A ML scores across non-held watchlist setups
                scored = [opportunity_ranker.score(f) for f in valid_features]
                ranked = opportunity_ranker.rank(scored)
                max_positions = min(5, max(1, int(self.manifest.get("strategy_parameters", {}).get("max_positions", 3))))

                for r in ranked[:5]:   # Log top 5 only
                    self.add_log(
                        "INFO",
                        f"  [p1] {r['symbol']:12s} score={r['opportunity_score']:5.1f} | "
                        f"dir={r['candidate_direction']:8s} | "
                        f"RSI={r['rsi']:5.1f} | vol_ratio={r.get('vol_ratio', 0):.2f}x"
                    )

                best = opportunity_ranker.best_candidate(ranked, min_score=40.0)
                if best is None and getattr(ml_filter, "is_loaded", False):
                    # Also screen trend-active setups directly via ML Tribunal when rule threshold didn't match
                    ml_screened = []
                    for f in valid_features:
                        if f["close"] == f["open"] and f.get("vol_ratio", 1.0) <= 1.0:
                            continue
                        for cdir in ("LONG", "SHORT"):
                            cand = {**f, "candidate_direction": cdir, "direction": cdir}
                            p = ml_filter.predict(cand)
                            if p >= float(getattr(ml_filter, "approval_threshold", 0.58)):
                                ml_screened.append({**cand, "opportunity_score": round(p * 100, 1), "_ml_prob": p})
                    if ml_screened:
                        ml_screened.sort(key=lambda x: x["_ml_prob"], reverse=True)
                        best = ml_screened[0]

                # ── STEP 4: Log strategy comparison ───────────────────────────
                if best:
                    v1_on_best  = v1_decisions.get(best["symbol"], {})
                    self.add_log("INFO", f"  ┌── STRATEGY COMPARISON for {best['symbol']} ──")
                    self.add_log("INFO", f"  │ v1 decision:     {v1_on_best.get('direction','?')} | conf={v1_on_best.get('confidence', 0):.1f}% | would_execute={v1_on_best.get('would_execute', False)}")
                    self.add_log("INFO", f"  │ Phase-2A setup:  {best['candidate_direction']} | score={best['opportunity_score']:.1f}/100")
                    self.add_log("INFO", f"  └────────────────────────────────────────────")
                else:
                    self.add_log("INFO", "  [p2a] No symbol cleared opportunity or ML threshold. Sitting out.")
                    self.add_log("INFO", f"  [v1] Would have traded: {v1_would_buys or 'NONE'}")

                # ── STEP 5: Execute trade up to max_positions concurrent slots ──
                open_tokens = set(self._exit_plans.keys())
                if best and INSTRUMENTS.get(best["symbol"], best["symbol"]) in open_tokens:
                    best = None
                if best and len(open_tokens) >= max_positions:
                    self.add_log("INFO", f"⏳ Holding {len(open_tokens)}/{max_positions} max positions. Waiting for exit slot.")
                    best = None

                # Evaluate Circuit Breaker
                if self.consecutive_losses >= 3:
                    self.add_log("ERROR", "CIRCUIT BREAKER: 3 consecutive losses. Halting new entries.")
                    best = None
                
                if best and best["candidate_direction"] == "SHORT" and getattr(broker, "is_paper", False):
                    self.add_log("INFO", "Skipping SHORT candidate: Cash equity paper trading is long-only.")
                    best = None

                if best and best["candidate_direction"] in ("LONG", "SHORT") and len(open_tokens) < max_positions:
                    
                    # --- Phase 2A: ML Quality Filter ---
                    prob = ml_filter.predict(best)
                    self.add_log("INFO", f"  🧠 ML Quality Score: {prob:.1%}")

                    ml_threshold = float(getattr(ml_filter, "approval_threshold", 0.6))
                    if prob < ml_threshold:
                        self.add_log(
                            "WARN",
                            f"  \u26a0\ufe0f Setup Rejected by ML Filter "
                            f"(prob {prob:.1%} < {ml_threshold:.1%})",
                        )
                        best = None
                    else:
                        self.add_log("INFO", f"  \u2705 Setup APPROVED by ML Filter (prob {prob:.1%})")
                        
                        # --- Phase 3: Event Radar & AI Debate ---
                        self.add_log("INFO", f"  📡 [EVENT RADAR] Scanning for catalysts on {best['symbol']}...")
                        events = event_radar.fetch_recent_events(best['symbol'], include_simulated=False)
                        
                        ev_to_analyze = events[0] if events else {"headline": "NO_CATALYST", "symbol": best['symbol'], "event_type": "NONE", "source": "NONE"}
                        
                        if not events:
                            self.add_log("INFO", f"  🤷 No recent events found. Technical execution relies purely on flow.")
                        else:
                            self.add_log("INFO", f"  📰 Found Catalyst: {ev_to_analyze['headline']}")
                            
                        self.add_log("INFO", f"  🤖 [AI DEBATE] Arbiter analyzing...")
                        analysis = ai_debate_engine.analyze_event(
                            ev_to_analyze, best, ml_probability=prob
                        )
                        
                        self.add_log("INFO", f"  🧠 AI Thesis: {analysis['what_changed']}")
                        if analysis.get('expectation_gap') != "UNKNOWN":
                            self.add_log("INFO", f"  ⚖️ Expectation Gap: {analysis['expectation_gap']} | Priced In: {analysis['priced_in']}")
                        
                        # --- PIT Verification & Latency Tracking ---
                        processing_end_time = datetime.now(timezone.utc)
                        latency_ms = (processing_end_time - processing_start_time).total_seconds() * 1000
                        decision_price = best.get('ltp', 0)
                        
                        # Event Integrity Checks
                        latest_event_avail = ev_to_analyze.get('available_at')
                        if self.kill_switches.get("MISSING_EVENT_TIMESTAMP_KILL") and ev_to_analyze.get('event_type') != "NONE" and not latest_event_avail:
                            self.add_log("WARN", f"  ⛔ [{best['symbol']}] MISSING_EVENT_TIMESTAMP_KILL: Event lacks available_at timestamp. NO TRADE.")
                            analysis['final_decision'] = "NO_TRADE"
                            analysis['bear_case'] = "MISSING_EVENT_TIMESTAMP_KILL: Event lacks available_at timestamp."
                            
                        elif self.kill_switches.get("PIT_VIOLATION_KILL") and latest_event_avail and latest_event_avail > processing_end_time.isoformat():
                            self.add_log("WARN", f"  ⛔ [{best['symbol']}] PIT_VIOLATION_KILL: Event available {latest_event_avail} > Decision Time {processing_end_time.isoformat()}. NO TRADE.")
                            analysis['final_decision'] = "NO_TRADE"
                            analysis['bear_case'] = f"PIT_VIOLATION_KILL: Event available {latest_event_avail} > Decision Time"

                        # Simulate a market fill with realistic latency and spread (0.05% slippage on paper)
                        simulated_fill_price = (
                            decision_price * 1.0005
                            if best.get("candidate_direction") == "LONG"
                            else decision_price * 0.9995
                        )

                        journal_entry = {
                            "timestamp": processing_end_time.isoformat(),
                            "market_mode": self.market_mode,
                            "symbol": best['symbol'],
                            "technical_score": best.get('opportunity_score', 0),
                            "ml_probability": prob,
                            "event_headline": ev_to_analyze.get("headline", "NO_CATALYST"),
                            "event_source": ev_to_analyze.get("source", "NONE"),
                            "analysis": analysis,
                            "final_decision": analysis['final_decision'],
                            
                            # Shadow Benchmark tracking
                            "v1_decision": v1_decisions.get(best['symbol'], {}).get('direction', 'NO_TRADE'),
                            "phase1_decision": best['candidate_direction'],
                            "phase2_decision": "TRADE" if prob >= ml_threshold else "NO_TRADE",

                            # Paper Execution Realism
                            "decision_price": decision_price,
                            "simulated_fill_price": simulated_fill_price,
                            "decision_to_fill_latency_ms": latency_ms,
                            "slippage": abs(simulated_fill_price - decision_price),
                            
                            # Zero Future-Information Test
                            "pit_compliance": {
                                "decision_time": processing_end_time.isoformat(),
                                "market_data_cutoff": processing_start_time.isoformat(),
                                "latest_event_available_at": latest_event_avail,
                                "latest_candle_timestamp": best.get('timestamp'),
                                "model_version": self.manifest.get('model_version')
                            }
                        }
                        self.trade_journal.insert(0, journal_entry)
                        if len(self.trade_journal) > 50:
                            self.trade_journal = self.trade_journal[:50]

                        if analysis['final_decision'] == "NO_TRADE":
                            self.add_log("WARN", f"  ⛔ Trade REJECTED by AI Arbiter: {analysis['bear_case']}")
                            best = None
                        else:
                            self.add_log("INFO", f"  ✅ Trade APPROVED by AI Arbiter (Uncertainty: {analysis.get('overall_uncertainty', 0.0):.2f})")
                            best['event_attribution'] = {
                                "event_id": ev_to_analyze.get("event_id", "NO_CATALYST"),
                                "headline": ev_to_analyze.get("headline", "NO_CATALYST"),
                                "thesis": analysis
                            }

                if best and best["candidate_direction"] in ("LONG", "SHORT") and len(self._exit_plans) < max_positions:
                    sym      = best["symbol"]
                    
                    # Fetch real-time quote for execution sizing and limits
                    try:
                        live_q = await get_live_quote(sym)
                        ltp = live_q.get("ltp", best["ltp"])
                    except Exception:
                        live_q = {}
                        ltp = best["ltp"]

                    atr14    = best.get("atr14", 0.0)
                    direction = best["candidate_direction"]
                    token    = INSTRUMENTS.get(sym, sym)
                    
                    # Classify Regime
                    trend_strength = best.get('trend_strength', 0)
                    range_pct = best.get('range_pct', 0)
                    volatility = best.get('volatility', 0)
                    
                    if abs(trend_strength) > 1.5:
                        regime = "trending"
                    elif volatility > 1.5:
                        regime = "high_volatility"
                    elif range_pct < 0.5:
                        regime = "low_volatility"
                    else:
                        regime = "ranging"
                        
                    best["regime"] = regime
                    
                    regime_stats = self.regime_stats[regime]
                    if regime_stats["trades"] >= 3 and (regime_stats["wins"] / max(1, regime_stats["trades"])) < 0.3:
                        self.add_log("WARN", f"Skipping trade: Model is underperforming in {regime} regime.")
                        best = None

                    if best:
                        ema_aligned = (
                            bool(best.get("ema9", 0) > best.get("ema21", 0))
                            if direction == "LONG"
                            else bool(best.get("ema9", 0) < best.get("ema21", 0))
                        )
                        # Compute ATR-based exits aligned with 30m 15-bar triple-barrier horizon
                        exit_plan = exit_engine.compute_exits(
                            entry_price=ltp,
                            atr14=atr14,
                            direction=direction,
                            max_hold_minutes=exit_engine.MAX_HOLD_MINUTES,
                            ema_trend_aligned=ema_aligned,
                        )
                        self.add_log(
                            "WARN",
                            f"🚨 PHASE-1 ENTRY: {direction} {sym} @ ₹{ltp:.2f} | "
                            f"TP=₹{exit_plan['take_profit']} (+{exit_plan['tp_pct']}%) | "
                            f"SL=₹{exit_plan['stop_loss']} (-{exit_plan['sl_pct']}%) | "
                            f"R:R={exit_plan['reward_risk']}"
                        )
    
                        try:
                            account = await broker.get_account()
                            buying_power = account.get("cash", 0)
                            total_equity = account.get("total_equity", buying_power)
                            
                            # 1. Size based on Risk (0.5% of equity per trade)
                            sl_distance = abs(ltp - exit_plan["stop_loss"])
                            risk_per_trade = total_equity * 0.005 # 0.5% risk
                            qty_based_on_risk = int(risk_per_trade / sl_distance) if sl_distance > 0 else 0
                            
                            # 2. Hard limits
                            estimated_cost_per_share = ltp * 1.001
                            max_position_value = total_equity * settings.max_position_size_pct / 100
                            affordable_value = min(buying_power, max_position_value)
                            max_qty = int(affordable_value / estimated_cost_per_share) if affordable_value > estimated_cost_per_share else 0
                            
                            qty = min(qty_based_on_risk, max_qty)
                            
                            if qty > 0:
                                # Fetch latest positions to calculate portfolio exposure
                                current_positions = await broker.get_positions()
                                portfolio_positions_map = {p.get("ticker", p.get("symbol")): p for p in current_positions}
                                
                                try:
                                    live_q_ts = datetime.fromisoformat(live_q["timestamp"].replace("Z", "+00:00")) if "timestamp" in live_q else datetime.now(timezone.utc)
                                    price_age = (datetime.now(timezone.utc) - live_q_ts).total_seconds()
                                except Exception:
                                    price_age = 0.0
                                
                                # 3. Wire RiskManager with real sector exposure calculation
                                trade_sector = SYMBOL_SECTORS.get(sym, "OTHER")
                                sector_notional = 0.0
                                for p in current_positions:
                                    p_tk = p.get("ticker", p.get("symbol", ""))
                                    p_sym = next((k for k, v in INSTRUMENTS.items() if v == p_tk or k == p_tk), p.get("symbol", ""))
                                    if SYMBOL_SECTORS.get(p_sym, "OTHER") == trade_sector:
                                        sector_notional += abs(float(p.get("quantity", 0)) * float(p.get("current_price", p.get("avg_price", 0))))
                                sector_current_pct = (sector_notional / total_equity * 100.0) if total_equity > 0 else 0.0

                                risk_decision = self.risk_manager.evaluate_trade(
                                    ticker=token,
                                    direction="BUY" if direction == "LONG" else "SELL",
                                    quantity=qty,
                                    price=ltp,
                                    portfolio_equity=total_equity,
                                    portfolio_positions=portfolio_positions_map,
                                    portfolio_cash=buying_power,
                                    portfolio_drawdown=account.get("drawdown_pct", 0.0),
                                    sector=trade_sector,
                                    sector_current_pct=sector_current_pct,
                                    daily_realised_loss_pct=abs(self.daily_realised_loss) / total_equity * 100 if total_equity > 0 else 0,
                                    price_age_seconds=max(0, price_age),
                                    is_live=not getattr(broker, "is_paper", False),
                                )
                                
                                if not risk_decision.approved:
                                    self.add_log("ERROR", f"RISK REJECTED {sym}: {', '.join(risk_decision.reasons)}")
                                    qty = 0
                                else:
                                    qty = int(risk_decision.approved_quantity)
                                
                                if qty > 0:
                                    resp = await broker.place_order(
                                        ticker=token,
                                        direction="BUY" if direction == "LONG" else "SELL",
                                        quantity=qty,
                                        order_type="MARKET",
                                        price=ltp,
                                    )
                                    status = resp.get("status", "?") if isinstance(resp, dict) else str(resp)
                                    self.add_log("INFO", f"✅ Order placed: {qty} shares of {sym}. Status: {status}")
                                    if status in ("FILLED", "EXCHANGE_PENDING", "COMPLETE"):
                                        exit_plan["regime"] = regime
                                        self._exit_plans[token] = exit_plan
                                        self._entry_times[token] = datetime.now(timezone.utc)
                                    else:
                                        self.add_log("WARN", f"❌ Entry for {sym} was not filled: {resp.get('rejection_reason', status)}")
                            else:
                                self.add_log("WARN", f"❌ Insufficient margin/risk-budget for {sym}. Need ₹{ltp:.2f}, power=₹{buying_power:.2f}")
    
                        except Exception as e:
                            self.add_log("ERROR", f"❌ Order failed: {e}")
    
                        self.add_log("INFO", "⏳ Cooldown 60s after entry...")
                        await asyncio.sleep(60)

                # ── STEP 6: Evaluate exits for all open positions ──────────────
                self.add_log("INFO", "🛡️  Checking exit conditions for open positions...")
                positions = await broker.get_positions()
                for pos in positions:
                    position_ticker = pos.get("ticker", pos.get("symbol", ""))
                    sym = next((name for name, key in INSTRUMENTS.items() if key == position_ticker), pos.get("symbol", ""))
                    qty = abs(pos.get("quantity", 0))
                    if qty <= 0:
                        continue

                    current_price = pos.get("current_price", pos.get("ltp", 0.0))
                    plan  = self._exit_plans.get(position_ticker)
                    etime = self._entry_times.get(position_ticker)
                    feats = next((f for f in all_features if f["symbol"] == sym), None)

                    if plan:
                        if plan.get("pending"):
                            continue

                        now_ist_clock = datetime.now(zoneinfo.ZoneInfo("Asia/Kolkata")).time()
                        if now_ist_clock.hour > 15 or (now_ist_clock.hour == 15 and now_ist_clock.minute >= 15):
                            decision = {"exit": True, "reason": "NSE_EOD_SQUAREOFF (15:15 IST)", "urgency": "SOFT"}
                        else:
                            decision = exit_engine.should_exit(
                                position=pos,
                                current_price=current_price,
                                exits=plan,
                                current_features=feats,
                                entry_time=etime,
                            )
                        if decision["exit"]:
                            urgency_emoji = "🛑" if decision["urgency"] == "HARD" else "🎯"
                            self.add_log(
                                "WARN" if decision["urgency"] == "HARD" else "INFO",
                                f"{urgency_emoji} EXIT {sym}: {decision['reason']}"
                            )
                            try:
                                side = pos.get("side", "LONG")
                                exit_dir = "BUY" if side == "SHORT" else "SELL"
                                
                                exit_resp = await broker.place_order(
                                    ticker=position_ticker,
                                    direction=exit_dir,
                                    quantity=qty,
                                    order_type="MARKET",
                                    price=current_price,
                                )
                                closed_regime = plan.get("regime", "ranging")
                                
                                status = exit_resp.get("status", "?") if isinstance(exit_resp, dict) else str(exit_resp)
                                if status == "FILLED":
                                    fill_price = exit_resp.get("fill_price", exit_resp.get("price", current_price)) if isinstance(exit_resp, dict) else current_price
                                    entry_price = pos.get("avg_price", current_price)
                                    realised_pnl = exit_resp.get("realized_pnl", (fill_price - entry_price) * qty if side == "LONG" else (entry_price - fill_price) * qty) if isinstance(exit_resp, dict) else 0.0
                                    
                                    self.daily_realised_loss += min(0, realised_pnl)
                                    
                                    if realised_pnl > 0:
                                        self.consecutive_losses = 0
                                        self.regime_stats[closed_regime]["wins"] += 1
                                    else:
                                        self.consecutive_losses += 1
                                        
                                    self.regime_stats[closed_regime]["trades"] += 1
                                    self.regime_stats[closed_regime]["pnl"] += realised_pnl
                                    
                                    self._exit_plans.pop(position_ticker, None)
                                    self._entry_times.pop(position_ticker, None)
                                    self.add_log("INFO", f"✅ Closed {qty} shares of {sym} | P&L: ₹{realised_pnl:.2f} | Regime: {closed_regime}")
                                elif status in ("EXCHANGE_PENDING", "PENDING", "COMPLETE"):
                                    plan["pending"] = True
                                    self.add_log("INFO", f"⏳ Exit order pending for {sym}. Awaiting fill.")
                                else:
                                    self.add_log("WARN", f"❌ Exit order rejected for {sym}: {status}")
                            except Exception as e:
                                self.add_log("ERROR", f"❌ Exit order failed for {sym}: {e}")
                    else:
                        # Fallback: v1 hard-coded exit for positions opened before phase-1
                        # Fallback: v1 hard-coded exit for positions opened before phase-1
                        pnl_pct = pos.get("pnl_pct", 0.0)
                        side = pos.get("side", "LONG")
                        exit_dir = "BUY" if side == "SHORT" else "SELL"
                        
                        if pnl_pct > 1.5:
                            self.add_log("WARN", f"[v1-exit] 🎯 TAKE PROFIT: {sym} +{pnl_pct:.2f}%")
                            await broker.place_order(ticker=INSTRUMENTS.get(sym, sym), direction=exit_dir, quantity=qty, order_type="MARKET", price=current_price)
                        elif pnl_pct < -1.0:
                            self.add_log("ERROR", f"[v1-exit] 🛑 STOP LOSS: {sym} {pnl_pct:.2f}%")
                            await broker.place_order(ticker=INSTRUMENTS.get(sym, sym), direction=exit_dir, quantity=qty, order_type="MARKET", price=current_price)

                # ── STEP 7: Check configurable daily limits ──────────────────────────
                # For safety, checking if daily loss exceeds limits natively in the engine as backup
                if hasattr(settings, 'max_daily_loss_pct'):
                    account = await broker.get_account()
                    equity = account.get("total_equity", 1.0)
                    if (abs(self.daily_realised_loss) / max(1.0, equity) * 100) > settings.max_daily_loss_pct:
                        self.add_log("ERROR", f"🛑 DAILY LOSS LIMIT HIT (engine layer). Halting.")
                        self.is_running = False
                        break

                await asyncio.sleep(30)   # Phase-1 scans every 30 seconds

            except asyncio.CancelledError:
                break
            except Exception as e:
                import traceback
                self.add_log("ERROR", f"Unexpected error: {e}")
                self.add_log("ERROR", traceback.format_exc()[:300])
                await asyncio.sleep(10)


# Singleton instance
engine = AITradingEngine()
