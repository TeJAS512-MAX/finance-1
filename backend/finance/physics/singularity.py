from __future__ import annotations
from datetime import date
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from schemas.finance import Invoice, Obligation, GSTLiabilitySnapshot, MoneyPhysicsState

class SingularityPrediction(BaseModel):
    is_singularity_imminent: bool
    event_horizon_date: date
    days_to_event_horizon: int
    singularity_depth: float = Field(..., description="Cash deficit in ₹ at event horizon")
    gst_accrual_trap_component: float = Field(..., description="GST owed on money not yet received")
    severity: str = Field(..., description="CRITICAL, HIGH, MODERATE, or BENIGN")
    probability_of_default: float = Field(..., ge=0.0, le=1.0)
    causal_root_chains: List[str]
    immediate_systemic_consequences: List[str]
    tax_vault_deficit: float

class GSTSingularityPredictor:
    """
    World-First GST Accrual Singularity Detector:
    Predicts the exact day and depth of liquidity black holes triggered
    by the Indian accrual GST regime (paying tax on uncollected receivables).
    """

    @classmethod
    def evaluate(
        cls,
        current_date: date,
        bank_cash: float,
        tax_vault_balance: float,
        invoices: List[Invoice],
        obligations: List[Obligation],
        gst_snapshot: GSTLiabilitySnapshot
    ) -> SingularityPrediction:
        event_horizon = gst_snapshot.gstr3b_due_date
        days_to_filing = (event_horizon - current_date).days
        effective_days = max(0, days_to_filing)

        # 1. Total Net GST cash required by filing date
        net_gst_due = max(0.0, gst_snapshot.net_gst_cash_payable)

        # 2. Senior non-negotiable obligations between today and filing date (Bank EMIs, Payroll)
        senior_obligations_due = sum(
            obl.amount for obl in obligations
            if current_date <= obl.due_date <= event_horizon and obl.priority <= 2
        )

        # 3. Probabilistic cash inflows expected strictly before event horizon
        # Only prompt payers or high-probability collections arriving before deadline
        expected_pre_filing_inflow = 0.0
        for inv in invoices:
            if inv.status in ("ISSUED", "PARTIALLY_PAID"):
                effective_realization = inv.due_date
                # Discount by predicted customer delay
                if (effective_realization - current_date).days + inv.delay_prediction_days <= effective_days:
                    expected_pre_filing_inflow += inv.unpaid_cash * 0.85

        # 4. Total available liquidity equation
        # Tax vault is specifically reserved, but if bank cash is negative, total money must suffice
        total_liquid_pool = bank_cash + tax_vault_balance + expected_pre_filing_inflow
        total_mandatory_outflow = net_gst_due + senior_obligations_due

        # Depth of black hole
        cash_delta = total_liquid_pool - total_mandatory_outflow

        is_imminent = cash_delta < 0
        depth = round(abs(cash_delta), 2) if is_imminent else 0.0

        # Accrual trap component: GST on unpaid invoices
        accrual_trap_gst = round(gst_snapshot.gst_on_unpaid_invoices, 2)
        tax_vault_deficit = max(0.0, net_gst_due - tax_vault_balance)

        # Probability and severity estimation
        if is_imminent:
            if effective_days <= 10 or depth > (bank_cash + 50000):
                severity = "CRITICAL"
                prob = round(min(0.98, 0.75 + (depth / max(1.0, total_mandatory_outflow)) * 0.25), 2)
            else:
                severity = "HIGH"
                prob = 0.72
        else:
            if cash_delta < 50000:
                severity = "MODERATE"
                prob = 0.35
            else:
                severity = "BENIGN"
                prob = 0.05

        # Construct causal chains
        causal_chains = [
            f"Accrued GST liability of ₹{net_gst_due:,.2f} is legally mandatory by {event_horizon.strftime('%d %b %Y')}.",
            f"Crucial Driver: ₹{accrual_trap_gst:,.2f} of this tax represents GST on invoices whose customers have NOT yet paid.",
            f"Bank liquid cash is only ₹{bank_cash:,.2f}, with senior obligations (EMIs/payroll) of ₹{senior_obligations_due:,.2f}.",
            f"Tax Vault reservation is only ₹{tax_vault_balance:,.2f}, leaving a direct statutory tax deficit of ₹{tax_vault_deficit:,.2f}."
        ]

        consequences = [
            "GST Portal locks E-way Bill generation under Rule 138E, halting physical transport of goods.",
            "Interest of 18% p.a. under Section 50(1) begins compounding daily.",
            "Bank account debit freezes initiated by statutory tax garnishee notices.",
            "Working capital freeze cascade: supplier payments bounce, vendor credit terms revoke."
        ]

        return SingularityPrediction(
            is_singularity_imminent=is_imminent,
            event_horizon_date=event_horizon,
            days_to_event_horizon=effective_days,
            singularity_depth=depth,
            gst_accrual_trap_component=accrual_trap_gst,
            severity=severity,
            probability_of_default=prob,
            causal_root_chains=causal_chains,
            immediate_systemic_consequences=consequences if is_imminent else [],
            tax_vault_deficit=round(tax_vault_deficit, 2)
        )
