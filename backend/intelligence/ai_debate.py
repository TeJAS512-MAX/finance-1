import json
import urllib.request
from typing import Dict, Any

class AIDebateEngine:
    """
    Phase 3: AI Debate System.
    Analyzes raw events from the Event Radar through a structured logical chain.
    """
    def __init__(self):
        self.live_news_cache = {}

    def build_prompt(self, event: Dict[str, Any], symbol_context: Dict[str, Any], ml_probability: float) -> str:
        return f"""
You are the Chief Investment Officer Arbiter of a quantitative hedge fund. 
Your primary quantitative model (AFML Triple-Barrier) has generated a signal with a raw mathematical win probability of: {ml_probability * 100:.1f}%.

Your job is META-LABELING: Decide whether to size up (TRADE) or veto (NO_TRADE) this mathematical signal based on the fundamental context.
An event has occurred for {event.get('symbol', 'UNKNOWN')}.
Event Type: {event.get('event_type', 'NONE')}
Headline: {event.get('headline', 'NO_CATALYST')}
Source: {event.get('source', 'UNKNOWN')}

Analyze this setup step-by-step through the following framework:
1. WHAT CHANGED? (Summarize the factual change)
2. IS IT MATERIAL? (Does this affect cash flows, growth, or systemic risk?)
3. WHAT DID THE MARKET EXPECT? (Pre-event consensus)
4. DOES THE CONTEXT SUPPORT THE QUANT MODEL? (The Quant model assigns {ml_probability*100:.1f}% probability to this trade. Does the news invalidate this edge?)
5. HOW MUCH WAS ALREADY PRICED IN? (Look at recent price action/technical context)
6. WHAT IS THE EXPECTED MARKET REACTION? (Bull and Bear cases)
7. WHAT COULD INVALIDATE THE THESIS? (Risks to the expected reaction)

Respond in strictly formatted JSON matching this schema:
{{
    "what_changed": "string",
    "is_material": boolean,
    "expectation_gap": "HIGH | MEDIUM | LOW | UNKNOWN",
    "priced_in": "HIGHLY | PARTIALLY | NOT_PRICED_IN | UNKNOWN",
    "bull_case": "string",
    "bear_case": "string",
    "invalidation_risk": "string",
    "meta_confidence": float,
    "quant_alignment": "SUPPORTS | CONTRADICTS | NEUTRAL",
    "final_decision": "TRADE | WATCH | NO_TRADE"
}}
"""

    def mock_llm_analyze(self, prompt: str, event: Dict[str, Any], ml_probability: float) -> Dict[str, Any]:
        """
        Mocks the LLM response acting as a Meta-Labeler.
        """
        if not event or event.get("headline") == "NO_CATALYST":
            # Aggressive Mode: Meta-labeler accepts ML predictions > 0.40 even without news
            if ml_probability >= 0.40:
                decision = "TRADE"
                meta_conf = ml_probability * 0.9
            else:
                decision = "NO_TRADE"
                meta_conf = ml_probability * 0.5
                
            return {
                "what_changed": "NO_CATALYST_IDENTIFIED",
                "is_material": False,
                "expectation_gap": "UNKNOWN",
                "priced_in": "UNKNOWN",
                "bull_case": "Purely technical flow indicating strong momentum.",
                "bear_case": "No fundamental tailwind to sustain a breakout; high risk of mean reversion.",
                "invalidation_risk": "Lack of catalyst means any macro news could instantly reverse the trend.",
                "meta_confidence": round(meta_conf, 2),
                "quant_alignment": "NEUTRAL",
                "final_decision": decision
            }
            
        headline = event.get("headline", "").lower()
        
        if "misses estimates" in headline:
            return {
                "what_changed": "Net profit missed estimates, NIM contracted.",
                "is_material": True,
                "expectation_gap": "HIGH",
                "priced_in": "PARTIALLY",
                "bull_case": "Valuations might become attractive for long-term buyers.",
                "bear_case": "Growth concerns and margin compression will lead to institutional selling.",
                "invalidation_risk": "Management provides strong forward guidance in the call.",
                "meta_confidence": 0.88 if ml_probability > 0.5 else 0.40,
                "quant_alignment": "SUPPORTS" if ml_probability < 0.5 else "CONTRADICTS", # Assumes short edge
                "final_decision": "TRADE" if ml_probability < 0.5 else "NO_TRADE"
            }
        elif "expansion deal" in headline:
            return {
                "what_changed": "$5B telecom expansion deal signed.",
                "is_material": True,
                "expectation_gap": "MEDIUM",
                "priced_in": "UNKNOWN",
                "bull_case": "Massive revenue visibility expansion over next 5 years.",
                "bear_case": "Execution risks and high CAPEX might impact short-term free cash flow.",
                "invalidation_risk": "Deal falls through or regulatory hurdles.",
                "meta_confidence": 0.70 if ml_probability > 0.6 else 0.30,
                "quant_alignment": "SUPPORTS" if ml_probability >= 0.6 else "CONTRADICTS",
                "final_decision": "TRADE" if ml_probability >= 0.6 else "NO_TRADE"
            }
        else:
            return {
                "what_changed": "Routine announcement.",
                "is_material": False,
                "expectation_gap": "UNKNOWN",
                "priced_in": "UNKNOWN",
                "bull_case": "Status quo.",
                "bear_case": "Status quo.",
                "invalidation_risk": "None.",
                "meta_confidence": round(ml_probability * 0.8, 2),
                "quant_alignment": "NEUTRAL",
                "final_decision": "TRADE" if ml_probability > 0.6 else "NO_TRADE"
            }

    def fetch_live_news(self, symbol: str) -> str:
        """
        Fetches real live news for the given symbol (fallback to NO_CATALYST if none).
        Uses Yahoo Finance API via urllib to avoid heavy dependencies.
        """
        if symbol in self.live_news_cache:
            return self.live_news_cache[symbol]
            
        try:
            # Map common Indian symbols to Yahoo Finance suffix if needed, or use raw.
            # Example: RELIANCE -> RELIANCE.NS
            query_sym = symbol + ".NS" if not symbol.endswith(".NS") else symbol
            url = f"https://query2.finance.yahoo.com/v1/finance/search?q={query_sym}&newsCount=1"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            
            with urllib.request.urlopen(req, timeout=3) as response:
                data = json.loads(response.read().decode())
                if 'news' in data and len(data['news']) > 0:
                    headline = data['news'][0]['title']
                    self.live_news_cache[symbol] = headline
                    return headline
        except Exception as e:
            pass
            
        self.live_news_cache[symbol] = "NO_CATALYST"
        return "NO_CATALYST"

    def analyze_event(self, event: Dict[str, Any], symbol_context: Dict[str, Any], ml_probability: float = 0.5) -> Dict[str, Any]:
        """
        Takes an event from EventRadar and the Quant model probability, queries the AI Debate system, and returns the analysis.
        """
        # 2. Live News API Integration
        # If running in live mode without a predefined mock headline, fetch real news.
        if event.get("headline", "NO_CATALYST") == "NO_CATALYST" and event.get("live_mode", False):
            real_headline = self.fetch_live_news(event.get('symbol', 'UNKNOWN'))
            event["headline"] = real_headline

        prompt = self.build_prompt(event, symbol_context, ml_probability)
        
        # Here we would call the actual LLM API. 
        # response = call_openai_api(prompt)
        analysis = self.mock_llm_analyze(prompt, event, ml_probability)
        
        return analysis

ai_debate_engine = AIDebateEngine()
