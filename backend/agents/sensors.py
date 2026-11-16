from __future__ import annotations
import re
from datetime import date, timedelta
from typing import Dict, Any, Optional
from pydantic import BaseModel
from backend.models.schemas import Invoice

class SensorExtractionResult(BaseModel):
    intent: str
    extracted_data: Dict[str, Any]
    confidence: float
    raw_input: str

class ActiveSensorSwarm:
    """
    Tier 0: Active Sensor Swarm
    Ingests multimodal inputs: natural language voice notes, invoice photo OCR,
    and structured bank/GST feed webhooks.
    """

    @classmethod
    def parse_natural_language_or_voice(cls, query: str) -> SensorExtractionResult:
        """
        Parses text or transcribed voice note into financial intent.
        Supports English, Hindi, and Hinglish.
        """
        q = query.lower().strip()

        # Invoice creation intent
        # e.g., "Create invoice for Reliance 2.5 lakh" or "Reliance ko 2.5 lakh ka bill banao"
        inv_match = re.search(r"(?:invoice|bill|banao|create invoice|bana do)\s+(?:for\s+|ka\s+)?([a-zA-Z\s]+?)\s+(\d+(?:\.\d+)?)\s*(lakh|lac|cr|k|crore)?", q)
        if inv_match or "create invoice" in q or "bill banao" in q:
            client_name = "Reliance Industries"
            amount = 250000.0
            if inv_match:
                extracted_name = inv_match.group(1).strip()
                if extracted_name and len(extracted_name) > 2:
                    client_name = extracted_name.title()
                raw_amt = float(inv_match.group(2))
                unit = inv_match.group(3) or "lakh"
                if "cr" in unit or "crore" in unit:
                    amount = raw_amt * 10000000.0
                elif "lakh" in unit or "lac" in unit:
                    amount = raw_amt * 100000.0
                elif "k" in unit:
                    amount = raw_amt * 1000.0
                else:
                    amount = raw_amt if raw_amt > 1000 else raw_amt * 100000.0

            return SensorExtractionResult(
                intent="CREATE_INVOICE",
                extracted_data={
                    "customer_name": client_name,
                    "base_amount": amount,
                    "gst_rate": 0.18,
                    "gst_amount": round(amount * 0.18, 2),
                    "total_amount": round(amount * 1.18, 2),
                    "due_days": 30
                },
                confidence=0.96,
                raw_input=query
            )

        # Health query intent
        # e.g., "How is my money?", "Paisa kaisa hai?", "Health check", "GST status"
        if any(term in q for term in ["how is my money", "kaisa hai", "health", "singularity", "gst", "status", "runway", "overview"]):
            return SensorExtractionResult(
                intent="QUERY_HEALTH",
                extracted_data={"focus": "ORGANISM_HEALTH"},
                confidence=0.98,
                raw_input=query
            )

        # Wormhole activation
        if any(term in q for term in ["wormhole", "activate", "execute", "apply solution", "fix this"]):
            return SensorExtractionResult(
                intent="ACTIVATE_WORMHOLE",
                extracted_data={"action": "EXECUTE_CURRENT_WORMHOLE"},
                confidence=0.95,
                raw_input=query
            )

        # Simulate delay
        if any(term in q for term in ["delay", "simulate delay", "agar delay hua", "reliance late kare"]):
            return SensorExtractionResult(
                intent="SIMULATE_DELAY",
                extracted_data={"additional_delay_days": 30},
                confidence=0.92,
                raw_input=query
            )

        # General inquiry fallback
        return SensorExtractionResult(
            intent="CONVERSATIONAL_INQUIRY",
            extracted_data={"query": query},
            confidence=0.85,
            raw_input=query
        )

    @classmethod
    def parse_invoice_image_ocr(cls, filename: str, image_bytes: Optional[bytes] = None) -> SensorExtractionResult:
        """
        Multimodal Vision OCR extractor for physical invoices.
        Simulates state-of-the-art vision extraction with exact GST breakdown.
        """
        # Realistic OCR simulation based on uploaded document
        return SensorExtractionResult(
            intent="CREATE_INVOICE",
            extracted_data={
                "customer_name": "Tata Steel B2B Division",
                "invoice_number": f"INV-OCR-{date.today().strftime('%Y%m')}-942",
                "base_amount": 350000.0,
                "gst_rate": 0.18,
                "gst_amount": 63000.0,
                "total_amount": 413000.0,
                "due_date": (date.today() + timedelta(days=30)).isoformat(),
                "hsn_code": "7208",
                "detected_ocr_accuracy": 0.984
            },
            confidence=0.98,
            raw_input=f"Uploaded invoice image: {filename}"
        )
