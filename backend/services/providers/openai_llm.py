"""
services/providers/openai_llm.py — OpenAI LLM Provider.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from backend.core.config import settings
from backend.services.interfaces import LLMProvider
from backend.core.exceptions import LLMHallucinationRisk


# ── Structured output schemas ──────────────────────────────────

class SentimentResult(BaseModel):
    sentiment: str = Field(description="One of: positive, negative, neutral, uncertain, contradictory")
    score: float = Field(description="Score from -1.0 (extreme negative) to 1.0 (extreme positive)")
    confidence: float = Field(description="Confidence from 0.0 to 1.0")
    reasoning: str = Field(description="Explanation based ONLY on the provided text")


class ThesisResult(BaseModel):
    decision: str = Field(description="LONG, SHORT, or NO_TRADE")
    confidence: float = Field(description="Confidence from 0.0 to 1.0")
    time_horizon: str = Field(description="Expected time horizon for the trade")
    catalysts: List[str] = Field(description="List of verified catalysts from the source text")
    risks: List[str] = Field(description="Key risks identified")
    reasoning: str = Field(description="Full thesis explanation")


# ── Provider Implementation ────────────────────────────────────

class OpenAILLMProvider(LLMProvider):
    """OpenAI implementation using structured outputs for reliability."""

    def __init__(self) -> None:
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.OPENAI_MODEL
        self.embedding_model = settings.EMBEDDING_MODEL

    @property
    def provider_name(self) -> str:
        return "openai"

    @property
    def model_name(self) -> str:
        return self.model

    async def analyse_sentiment(
        self,
        text: str,
        context: Optional[str] = None,
    ) -> Dict[str, Any]:
        
        system_prompt = (
            "You are a strict financial analyst. Analyze the sentiment of the text "
            "with respect to the company's stock price. "
            "If the text is unclear or conflicting, output 'uncertain' or 'contradictory'."
        )
        if context:
            system_prompt += f"\nContext: {context}"

        response = await self.client.beta.chat.completions.parse(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text},
            ],
            response_format=SentimentResult,
            temperature=0.0,
        )

        result = response.choices[0].message.parsed
        if not result:
            raise LLMHallucinationRisk("Failed to parse sentiment result safely.")

        return result.model_dump()

    async def generate_thesis(
        self,
        symbol: str,
        event_description: str,
        source_texts: List[str],
        financial_context: str,
        technical_context: str,
        market_regime: str,
    ) -> Dict[str, Any]:
        
        system_prompt = (
            f"You are a quantitative trading system evaluating an event for {symbol}.\n"
            f"CRITICAL RULES:\n"
            f"1. You MUST NOT invent any facts, numbers, or dates.\n"
            f"2. You may ONLY rely on the provided source texts and context.\n"
            f"3. If the evidence is insufficient to form a highly confident thesis, output NO_TRADE.\n"
            f"4. Market Regime is {market_regime}. Adjust risk accordingly."
        )

        user_content = (
            f"Event: {event_description}\n\n"
            f"Source Texts:\n" + "\n".join(f"- {t}" for t in source_texts) + "\n\n"
            f"Financials:\n{financial_context}\n\n"
            f"Technicals:\n{technical_context}"
        )

        response = await self.client.beta.chat.completions.parse(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            response_format=ThesisResult,
            temperature=0.1,
        )

        result = response.choices[0].message.parsed
        if not result:
            raise LLMHallucinationRisk("Failed to parse thesis safely.")

        # Hallucination Guard: ensure NO_TRADE if confidence is low
        if result.confidence < (settings.MIN_SIGNAL_CONFIDENCE / 100.0) and result.decision != "NO_TRADE":
            result.decision = "NO_TRADE"
            result.reasoning = "[SYSTEM OVERRIDE: Confidence below threshold] " + result.reasoning

        return result.model_dump()

    async def generate_bull_bear_debate(
        self,
        symbol: str,
        source_texts: List[str],
        financial_context: str,
    ) -> Dict[str, Any]:
        """Simplified stub for the debate."""
        return {
            "bull_case": "Bull case based on X",
            "bear_case": "Bear case based on Y",
            "judge_verdict": "Neutral",
            "confidence": 0.5
        }

    async def assess_priced_in(
        self,
        symbol: str,
        event_description: str,
        price_history: str,
        abnormal_return: float,
    ) -> Dict[str, Any]:
        return {
            "priced_in_score": 0.5,
            "assessment": "Partially priced in",
            "reasoning": f"Stock moved {abnormal_return*100:.1f}%."
        }

    async def generate_journal_entry(self, trade_data: Dict[str, Any]) -> Dict[str, Any]:
        return {"journal_entry": "Trade executed."}

    async def get_embedding(self, text: str) -> List[float]:
        response = await self.client.embeddings.create(
            input=text,
            model=self.embedding_model,
        )
        return response.data[0].embedding
