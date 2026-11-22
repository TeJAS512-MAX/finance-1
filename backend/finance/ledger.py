from __future__ import annotations
from datetime import date, timedelta
from typing import Dict, Any, List
from backend.models.schemas import AetherPravahState
from backend.finance.calculators import fmt_compact, fmt_inr

def generate_reminder_draft(inv_number: str, customer_name: str, amount: float, days_overdue: int, due_date: date) -> Dict[str, Any]:
    """Generates professional WhatsApp and Email reminder copy."""
    amt_str = fmt_inr(amount)
    
    if days_overdue > 15:
        subject = f"Urgent: Overdue Payment Notice - Invoice {inv_number} ({amt_str})"
        message = (
            f"Dear Accounts Team at {customer_name},\n\n"
            f"This is an urgent follow-up regarding Invoice #{inv_number} for {amt_str}, "
            f"which was due on {due_date.strftime('%d %b %Y')} and is now {days_overdue} days overdue.\n\n"
            f"Under Section 16 of the MSMED Act, delayed payments beyond agreed terms attract statutory interest. "
            f"Please share the payment UTR number or advise on the bank release schedule today.\n\n"
            f"Thank you for your prompt attention."
        )
        channel = "WHATSAPP_URGENT"
        tone = "urgent"
    elif days_overdue > 0:
        subject = f"Friendly Reminder: Payment for Invoice {inv_number} ({amt_str})"
        message = (
            f"Hi {customer_name} Team,\n\n"
            f"A gentle reminder that Invoice #{inv_number} for {amt_str} was due on {due_date.strftime('%d %b %Y')} "
            f"({days_overdue} days ago). Please let us know if you need any document clarification or when the RTGS is scheduled.\n\n"
            f"Best regards."
        )
        channel = "WHATSAPP_GENTLE"
        tone = "warm"
    else:
        subject = f"Upcoming Due Date Notice: Invoice {inv_number} ({amt_str})"
        message = (
            f"Hi {customer_name} Team,\n\n"
            f"Sharing a courteous reminder regarding Invoice #{inv_number} for {amt_str}, "
            f"due on {due_date.strftime('%d %b %Y')}.\n\n"
            f"We are offering a 2.0% prompt settlement rebate ({fmt_inr(amount * 0.02)} discount) if cleared within 48 hours. "
            f"Please let us know if you would like to avail this discount."
        )
        channel = "DISCOUNT_OFFER"
        tone = "discount"

    return {
        "invoice_number": inv_number,
        "customer_name": customer_name,
        "amount": amount,
        "days_overdue": days_overdue,
        "subject": subject,
        "message": message,
        "channel": channel,
        "tone": tone
    }

def receivables_view(state: AetherPravahState, current_date: date) -> Dict[str, Any]:
    """Generates Who Owes Me (Debtors) ledger with aging analysis and reminder drafts."""
    items: List[Dict[str, Any]] = []
    total_pending = 0.0
    overdue_amount = 0.0
    expected_30_days = 0.0
    gst_inside_unpaid = 0.0

    for inv in state.invoices:
        if inv.status == "PAID":
            continue

        unpaid = float(inv.unpaid_cash)
        total_pending += unpaid
        gst_inside_unpaid += float(inv.gst_amount)

        days_overdue = max(0, (current_date - inv.due_date).days)
        if days_overdue > 0:
            overdue_amount += unpaid

        expected_date = inv.due_date + timedelta(days=int(inv.delay_prediction_days))
        days_to_expected = (expected_date - current_date).days
        if 0 <= days_to_expected <= 30:
            expected_30_days += unpaid

        status_label = "OVERDUE" if days_overdue > 0 else ("TRAP" if inv.delay_prediction_days > 20 else "NORMAL")

        reminder = generate_reminder_draft(inv.invoice_number, inv.customer_name, unpaid, days_overdue, inv.due_date)

        items.append({
            "id": inv.id,
            "invoice_number": inv.invoice_number,
            "customer_name": inv.customer_name,
            "amount": unpaid,
            "gst_amount": float(inv.gst_amount),
            "issue_date": inv.issue_date.strftime("%Y-%m-%d"),
            "due_date": inv.due_date.strftime("%Y-%m-%d"),
            "due_label": inv.due_date.strftime("%d %b"),
            "days_overdue": days_overdue,
            "delay_prediction_days": int(inv.delay_prediction_days),
            "expected_date": expected_date.strftime("%Y-%m-%d"),
            "expected_label": expected_date.strftime("%d %b"),
            "status": status_label,
            "reminder": reminder
        })

    # Sort: overdue first, then largest amounts
    items.sort(key=lambda x: (x["days_overdue"] > 0, x["amount"]), reverse=True)

    return {
        "invoices": items,
        "summary": {
            "total_pending": round(total_pending, 2),
            "overdue_amount": round(overdue_amount, 2),
            "expected_30_days": round(expected_30_days, 2),
            "gst_inside": round(gst_inside_unpaid, 2),
            "count": len(items)
        }
    }

def payables_view(state: AetherPravahState, current_date: date) -> Dict[str, Any]:
    """Generates Who I Owe (Creditors, Loans, Taxes, Rent) ledger."""
    items: List[Dict[str, Any]] = []
    total_payables = 0.0

    # 1. Senior obligations (Bank EMIs, Lease, Payroll)
    for obl in state.obligations:
        amt = float(obl.amount)
        total_payables += amt
        days_left = (obl.due_date - current_date).days
        items.append({
            "id": obl.id,
            "name": obl.name,
            "category": obl.obligation_type.replace("_", " ").title(),
            "amount": amt,
            "due_date": obl.due_date.strftime("%Y-%m-%d"),
            "due_label": obl.due_date.strftime("%d %b"),
            "days_left": days_left,
            "priority": obl.priority, # 1=Senior Bank, 2=Critical, 3=General
            "priority_label": "High (Priority 1)" if obl.priority == 1 else "Medium (Priority 2)",
            "status": "DUE_SOON" if days_left <= 7 else "PENDING"
        })

    # 2. Raw Material Suppliers
    for supp in state.suppliers:
        amt = float(supp.total_payable)
        total_payables += amt
        supp_due = current_date + timedelta(days=12)
        items.append({
            "id": supp.id,
            "name": supp.name,
            "category": "Raw Material Supplier",
            "amount": amt,
            "due_date": supp_due.strftime("%Y-%m-%d"),
            "due_label": supp_due.strftime("%d %b"),
            "days_left": 12,
            "priority": 2,
            "priority_label": "Supplier Credit",
            "status": "DUE_SOON"
        })

    # 3. Statutory GST GSTR-3B Tax
    net_gst = float(state.gst_snapshot.net_gst_cash_payable)
    gst_due = state.gst_snapshot.gstr3b_due_date
    days_to_gst = max(0, (gst_due - current_date).days)
    items.append({
        "id": "TAX-GSTR3B",
        "name": f"GST GSTR-3B Sovereign Tax Settlement ({gst_due.strftime('%B %Y')})",
        "category": "Statutory Government Tax",
        "amount": net_gst,
        "due_date": gst_due.strftime("%Y-%m-%d"),
        "due_label": gst_due.strftime("%d %b"),
        "days_left": days_to_gst,
        "priority": 1,
        "priority_label": "Non-Negotiable (Legal Mandate)",
        "status": "CRITICAL" if days_to_gst <= 5 else "DUE_SOON"
    })
    total_payables += net_gst

    # Sort by priority, then days left
    items.sort(key=lambda x: (x["priority"], x["days_left"]))

    return {
        "liabilities": items,
        "summary": {
            "total_payables": round(total_payables, 2),
            "bank_cash": float(state.physics_state.bank_cash),
            "coverage_deficit": round(max(0.0, total_payables - float(state.physics_state.bank_cash)), 2),
            "count": len(items)
        }
    }
