from __future__ import annotations
from datetime import date, timedelta
from typing import Dict, Any, List
from schemas.finance import AetherPravahState
from finance.calculators import fmt_compact, fmt_inr

def build_gst_plan(state: AetherPravahState, current_date: date) -> Dict[str, Any]:
    """
    Constructs a clear, scannable GST & Tax Planner ledger, action steps,
    and statutory calendar.
    """
    snap = state.gst_snapshot
    due_date = snap.gstr3b_due_date
    days_left = max(0, (due_date - current_date).days)
    
    output_gst = float(snap.output_gst_gross)
    itc_claimed = float(snap.input_tax_credit_booked)
    itc_at_risk = 12000.0 if state.business.archetype == "STEEL_TRADER" else 8000.0
    net_payable = float(snap.net_gst_cash_payable)
    in_vault = float(state.physics_state.tax_vault_balance)
    
    still_to_arrange = max(0.0, net_payable - in_vault)
    vault_coverage_pct = round((in_vault / net_payable * 100.0) if net_payable > 0 else 100.0, 1)
    
    bank_cash = float(state.physics_state.bank_cash)
    
    # Calculate senior obligations due before 20 Nov
    senior_obls_before_due = sum(
        float(o.amount) for o in state.obligations if o.due_date <= due_date
    )
    
    # Safe cash that can be transferred to Tax Vault right now
    safe_to_move = max(0.0, min(still_to_arrange, bank_cash - senior_obls_before_due))
    
    # Cash gap / shortfall at due date
    cash_gap = max(0.0, still_to_arrange - (bank_cash - senior_obls_before_due))
    
    gst_on_unpaid = float(snap.gst_on_unpaid_invoices)
    gst_on_unpaid_pct = round((gst_on_unpaid / output_gst * 100.0) if output_gst > 0 else 0.0, 1)
    
    severity = "CRITICAL" if cash_gap > 0 else ("MODERATE" if still_to_arrange > 0 else "BENIGN")
    tone = "bad" if cash_gap > 0 else ("warn" if still_to_arrange > 0 else "good")
    
    if cash_gap > 0:
        status_text = f"Short by {fmt_compact(cash_gap)} on {due_date.strftime('%d %b')}"
    elif still_to_arrange > 0:
        status_text = f"Need to allocate {fmt_compact(still_to_arrange)} to Tax Vault"
    else:
        status_text = "Tax fully ring-fenced & protected"
        
    # Actionable Steps
    steps: List[Dict[str, Any]] = []
    
    if safe_to_move > 0:
        steps.append({
            "title": f"Move {fmt_compact(safe_to_move)} into Tax Vault now",
            "detail": f"Protects tax cash while retaining {fmt_compact(senior_obls_before_due)} for senior loan EMIs and rent due before {due_date.strftime('%d %b')}.",
            "amount": safe_to_move,
            "tone": "neutral"
        })
        
    if cash_gap > 0:
        unpaid_large = [inv for inv in state.invoices if inv.status != "PAID" and inv.unpaid_cash >= 500000]
        names = ", ".join(inv.customer_name for inv in unpaid_large[:2])
        total_open = sum(inv.unpaid_cash for inv in unpaid_large)
        unlocked = total_open * 0.98
        steps.append({
            "title": f"Offer 2.0% prompt settlement discount to {names}",
            "detail": f"Unsettled receivables of {fmt_compact(total_open)} are delayed past the 20th. A 2% discount unlocks {fmt_compact(unlocked)} within 36 hours.",
            "amount": unlocked,
            "tone": "action",
            "chat": f"Draft a reminder with 2% discount for {names}"
        })
        
    steps.append({
        "title": f"Verify supplier invoices to safeguard {fmt_compact(itc_claimed)} in ITC",
        "detail": "Input tax credit is only valid under Section 16(2)(aa) if your suppliers have uploaded bills to GSTR-1. Ensure invoices appear in GSTR-2B.",
        "amount": itc_claimed,
        "tone": "neutral"
    })
    
    late_week_interest = round(still_to_arrange * (0.18 / 365.0) * 7.0, 2)
    late_week_fees = 50.0 * 7 # Section 47 late fee Rs 50/day
    steps.append({
        "title": f"File and pay GSTR-3B by {due_date.strftime('%d %b')}",
        "detail": f"Paying 7 days late on {fmt_compact(still_to_arrange)} incurs {fmt_inr(late_week_interest + late_week_fees)} in statutory interest (18% p.a.) and late fees.",
        "amount": 0.0,
        "tone": "neutral"
    })
    
    calendar = [
        {
            "date": due_date.strftime("%Y-%m-%d"),
            "label": "GSTR-3B: Monthly cash return & tax settlement",
            "days": days_left,
            "kind": "due"
        },
        {
            "date": (current_date + timedelta(days=25)).strftime("%Y-%m-%d"),
            "label": "GSTR-1: Outward sales return for current month",
            "days": 25,
            "kind": "file"
        },
        {
            "date": (current_date + timedelta(days=29)).strftime("%Y-%m-%d"),
            "label": "Advance Tax Q3 Installment (75% cumulative)",
            "days": 29,
            "kind": "tax"
        }
    ]
    
    causal_chain = [
        f"CGST Section 39 creates tax liabilities upon bill generation, preceding buyer settlement cycles.",
        f"₹{gst_on_unpaid:,.2f} of this tax represents GST on invoices whose buyers have NOT yet paid.",
        f"Available liquid bank cash is {fmt_inr(bank_cash)}, with senior loan EMIs and rent of {fmt_inr(senior_obls_before_due)}.",
        f"Tax Vault currently holds {fmt_inr(in_vault)}, leaving a cash gap of {fmt_inr(cash_gap)} at cut-off."
    ]
    
    return {
        "period": "2026-11",
        "due_date": due_date.strftime("%Y-%m-%d"),
        "due_label": due_date.strftime("%d %b"),
        "days_left": days_left,
        "output_gst": output_gst,
        "itc_claimed": itc_claimed,
        "itc_at_risk": itc_at_risk,
        "net_payable": net_payable,
        "in_vault": in_vault,
        "still_to_arrange": still_to_arrange,
        "vault_coverage_pct": vault_coverage_pct,
        "bank_cash": bank_cash,
        "senior_obligations_before_due": senior_obls_before_due,
        "safe_to_move_now": safe_to_move,
        "cash_gap": cash_gap,
        "gst_on_unpaid": gst_on_unpaid,
        "gst_on_unpaid_pct": gst_on_unpaid_pct,
        "tone": tone,
        "status_text": status_text,
        "severity": severity,
        "causal_chain": causal_chain,
        "steps": steps,
        "calendar": calendar
    }
