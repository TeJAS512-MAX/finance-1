from __future__ import annotations
import re
from datetime import date, timedelta
from typing import Dict, Any, List, Optional
from backend.models.schemas import AetherPravahState
from backend.finance.calculators import (
    calculate_emi, loan_summary, debt_service_verdict, profit_model,
    fmt_inr, fmt_compact, extract_amounts, extract_days, extract_rate_pct, extract_tenure_months
)
from backend.finance.forecast import run_forecast, Scenario
from backend.finance.gst_plan import build_gst_plan
from backend.finance import ledger
from backend.finance.knowledge import find_topic
from backend.finance.defaults import finance_defaults

DEFAULT_SUGGESTIONS = [
    "How is my money?",
    "What GST do I owe this month?",
    "Who owes me money?",
    "Can I afford a 5 lakh machine?"
]

class FinanceAssistant:
    """
    Comprehensive AI Finance Assistant for Indian MSMEs:
    Handles invoices, GST & tax, loans & EMIs, expenses, cash flow, debt collection,
    reminders, and compliance advice.
    """

    def __init__(self, cns: Any):
        self.cns = cns
        self.ctx: Dict[str, Any] = {}

    @property
    def state(self) -> AetherPravahState:
        return self.cns.state

    @property
    def today(self) -> date:
        return self.cns.current_date

    def _resp(
        self,
        summary: str,
        *,
        intent: str,
        numbers: str = "",
        causal: str = "",
        actions: Optional[List[str]] = None,
        what_if: str = "",
        cards: Optional[List[Dict[str, Any]]] = None,
        suggestions: Optional[List[str]] = None,
        open_tool: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        sing = self.cns.predict_current_singularity()
        w = self.state.active_wormholes[0].model_dump() if self.state.active_wormholes else None
        self.ctx["last_intent"] = intent
        
        return {
            "plain_language_summary": summary,
            "exact_numbers": numbers,
            "causal_explanation": causal,
            "top_recommended_actions": actions or [],
            "what_if_ignore": what_if,
            "cards": cards or [],
            "suggestions": suggestions if suggestions is not None else DEFAULT_SUGGESTIONS,
            "open_tool": open_tool,
            "intent": intent,
            "source": "finance_assistant",
            "singularity": sing.model_dump(),
            "wormhole": w,
            "state": self.state.model_dump()
        }

    def try_answer(self, message: str, history: Optional[List[Dict[str, str]]] = None) -> Optional[Dict[str, Any]]:
        q = message.lower().strip()

        # 1. Invoice creation commands stay with original CNS logic
        if re.search(r"\b(create|make|generate|raise|issue|bill)\b.*\binvoice|bill banao|invoice banao", q):
            return None
        # 2. Wormhole activation commands stay with original CNS logic
        if re.search(r"\b(activate|execute|trigger|apply)\b.*\bwormhole|apply solution", q):
            return None

        # 3. Topic explanations (ITC, MSME 45-day rule, e-invoicing, etc.)
        topic = find_topic(q)
        if topic and any(w in q for w in ["what is", "explain", "meaning", "samjhao", "rules", "tell me about"]):
            return self._explain_topic(topic)

        # 4. Debtors / Receivables ("who owes me money?")
        if any(w in q for w in ["who owes", "debtor", "receivable", "unpaid bill", "pending bill", "kiska paisa"]):
            return self._receivables_reply()

        # 5. Payables / Creditors / Upcoming Bills ("who do I owe?", "when is my EMI due?")
        if any(w in q for w in ["who do i owe", "whom do i owe", "what do i owe", "payable", "supplier", "vendor", "upcoming bill", "kisko dena", "when is my emi", "due date of emi"]):
            return self._payables_reply()

        # 6. Affordability & Capex Check ("Can I afford ₹5L machine?", "Can I spend 3 lakhs?")
        if any(w in q for w in ["can i afford", "can i buy", "can i spend", "khareed sakta", "le sakta", "should i buy"]):
            return self._affordability_reply(q)

        # 7. Loans & EMI calculations ("Calculate EMI for 10L at 11% for 5 years")
        if "emi" in q or "loan" in q:
            return self._emi_reply(q)

        # 8. GST & Tax inquiries ("What GST do I owe?", "When is GSTR-3B due?", "gst late fee")
        if "gst" in q or "gstr" in q or "tax due" in q:
            return self._gst_reply(q)

        # 9. Cash flow forecast & runway ("How long will cash last?", "What is my runway?", "Show forecast")
        if any(w in q for w in ["runway", "cash flow", "forecast", "how long will my cash", "balance after"]):
            return self._cashflow_reply()

        # 10. What-If Simulation ("What if customers pay 15 days late?", "what if I cut costs by 15%")
        if "what if" in q or "simulate delay" in q or "agar late" in q:
            return self._what_if_reply(q)

        # 11. Payment reminder drafting ("Draft reminder for Shree Ram / Reliance")
        if "reminder" in q or "remind" in q or "draft" in q:
            return self._reminder_reply(q)

        # 12. Profit & Break-even ("How is my profit?", "What is break-even?")
        if "profit" in q or "margin" in q or "break-even" in q or "breakeven" in q:
            return self._profit_reply()

        # 13. General Overall Financial Health ("How is my money?", "Paisa kaisa hai?")
        if any(w in q for w in ["how is my money", "paisa kaisa", "overall health", "financial status", "summary"]):
            return self._health_reply()

        # 14. Greeting / Help
        if re.search(r"^(hi|hello|hey|namaste|good morning|help)\b", q):
            return self._greeting_reply()

        # Fallback to general financial overview
        return self._fallback_reply(message)

    def _greeting_reply(self) -> Dict[str, Any]:
        s = self.state
        summary = (
            f"Hello! I am your AI Finance Assistant for **{s.business.name}** ({s.business.city}).\n\n"
            f"I actively track all **{fmt_compact(s.physics_state.total_rupees_conserved)}** in conserved capital across your accounts. "
            f"Currently, your liquid bank cash is **{fmt_inr(s.physics_state.bank_cash)}**, while a non-negotiable **GST payment of {fmt_inr(s.gst_snapshot.net_gst_cash_payable)}** is due on 20 Nov.\n\n"
            f"How can I help you today? You can ask about cash flow, GST planning, loan EMIs, debtor collections, or whether you can afford new purchases."
        )
        return self._resp(
            summary,
            intent="GREETING",
            numbers=f"• Bank Cash: {fmt_inr(s.physics_state.bank_cash)}\n• GST Cash Payable (20 Nov): {fmt_inr(s.gst_snapshot.net_gst_cash_payable)}\n• Operating Runway: {s.physics_state.estimated_runway_days:.1f} Days",
            actions=[
                "Check Who Owes Me (Debtors Ledger)",
                "Review GST & Tax Planner before the 20th cut-off",
                "Simulate cash flow with customer delays"
            ],
            suggestions=["How is my money?", "What GST do I owe this month?", "Who owes me money?", "Can I afford a 5 lakh machine?"]
        )

    def _health_reply(self) -> Dict[str, Any]:
        s = self.state
        fc = run_forecast(s, self.today)["summary"]
        plan = build_gst_plan(s, self.today)
        
        status_word = "CRITICAL DEFICIT" if fc["is_deficit"] else "STABLE"
        summary = (
            f"📊 **Financial Health Overview for {s.business.name}**\n\n"
            f"• **Liquid Bank Reserves**: {fmt_inr(s.physics_state.bank_cash)}\n"
            f"• **Tax Vault Ring-Fenced**: {fmt_inr(s.physics_state.tax_vault_balance)} ({plan['vault_coverage_pct']}% covered)\n"
            f"• **Upcoming GST Due (20 Nov)**: {fmt_inr(plan['net_payable'])}\n"
            f"• **Cash Shortfall on Due Date**: {fmt_inr(plan['cash_gap'])}\n\n"
            f"⚠️ **Core Finding**: Operations are profitable, but your cash dips to **{fmt_inr(fc['lowest_balance'])}** on **{fc['lowest_date_label']}** "
            f"because statutory tax outflows precede customer settlement cycles."
        )
        
        cards = [{
            "type": "kpis",
            "items": [
                {"label": "Bank Cash", "value": fmt_compact(s.physics_state.bank_cash), "tone": "good"},
                {"label": "Tax Shortfall", "value": fmt_compact(plan['cash_gap']), "tone": "bad" if plan['cash_gap'] > 0 else "good"},
                {"label": "Lowest Projected", "value": fmt_compact(fc['lowest_balance']), "tone": "bad" if fc['is_deficit'] else "good"},
                {"label": "Runway", "value": f"{fc['estimated_runway_days']:.0f} Days", "tone": "warn"}
            ]
        }]
        
        return self._resp(
            summary,
            intent="HEALTH",
            numbers=f"• Starting Cash: {fmt_inr(fc['starting_cash'])}\n• Lowest Balance ({fc['lowest_date_label']}): {fmt_inr(fc['lowest_balance'])}\n• GSTR-3B Tax Net Due: {fmt_inr(plan['net_payable'])}\n• Tax Vault Balance: {fmt_inr(plan['in_vault'])}",
            causal="Statutory tax rules under CGST Section 39 require cash settlement before institutional collection cycles clear.",
            actions=[
                "Deploy Liquidity Bridge with 2% prompt discount to Reliance",
                "Move safe cash into Tax Vault to ring-fence taxes",
                "Defer non-essential capex until collections clear in December"
            ],
            cards=cards,
            open_tool={"tab": "cashflow"},
            suggestions=["What GST do I owe this month?", "Who owes me money?", "Can I afford a 5 lakh machine?"]
        )

    def _receivables_reply(self) -> Dict[str, Any]:
        recv = ledger.receivables_view(self.state, self.today)
        sm = recv["summary"]
        invoices = recv["invoices"]
        
        summary = (
            f"💰 **Who Owes You: Total Pending Receivables: {fmt_inr(sm['total_pending'])}** across {sm['count']} open invoices.\n\n"
            f"• **Already Overdue**: {fmt_inr(sm['overdue_amount'])}\n"
            f"• **Expected within 30 Days**: {fmt_inr(sm['expected_30_days'])}\n"
            f"• **GST Trapped Inside Unpaid Bills**: {fmt_inr(sm['gst_inside'])}\n\n"
            f"Your largest open invoice is with **{invoices[0]['customer_name']}** ({fmt_compact(invoices[0]['amount'])}), expected around {invoices[0]['expected_label']}."
        )
        
        table_rows = [
            [inv["customer_name"][:20], inv["invoice_number"], fmt_compact(inv["amount"]), f"+{inv['delay_prediction_days']}d", inv["status"]]
            for inv in invoices
        ]
        
        cards = [{
            "type": "table",
            "title": "Unsettled Customer Invoices",
            "columns": ["Customer", "Invoice #", "Amount", "Delay", "Status"],
            "rows": table_rows
        }]
        
        return self._resp(
            summary,
            intent="RECEIVABLES",
            numbers=f"• Total Unpaid: {fmt_inr(sm['total_pending'])}\n• Overdue Dues: {fmt_inr(sm['overdue_amount'])}\n• Accrued GST in Bills: {fmt_inr(sm['gst_inside'])}",
            causal="Customers hold payment for 30-45 days while GST on their bills must be remitted by the 20th in cash.",
            actions=[
                "Draft WhatsApp payment reminder for overdue invoices",
                "Offer a 2% early settlement discount to accelerate liquidity",
                "Apply Section 16 MSMED statutory interest notice for overdue debtors"
            ],
            cards=cards,
            open_tool={"tab": "debtors"},
            suggestions=["Draft reminder for Reliance", "What GST do I owe this month?", "Can I afford a 5 lakh machine?"]
        )

    def _payables_reply(self) -> Dict[str, Any]:
        pay = ledger.payables_view(self.state, self.today)
        sm = pay["summary"]
        items = pay["liabilities"]
        
        summary = (
            f"📑 **Who You Owe: Upcoming Liabilities Total {fmt_inr(sm['total_payables'])}** against bank cash of {fmt_inr(sm['bank_cash'])}.\n\n"
            f"• **Statutory GST Tax**: {fmt_inr(self.state.gst_snapshot.net_gst_cash_payable)} due 20 Nov (Non-negotiable)\n"
            f"• **Bank Loan EMIs & Rent**: {fmt_inr(sum(o['amount'] for o in items if o['priority'] == 1 and 'Tax' not in o['category']))}\n"
            f"• **Raw Material Suppliers**: {fmt_inr(sum(o['amount'] for o in items if o['category'] == 'Raw Material Supplier'))}\n\n"
            f"⚠️ **Cash Coverage Deficit**: {fmt_inr(sm['coverage_deficit'])}."
        )
        
        table_rows = [
            [it["name"][:22], fmt_compact(it["amount"]), it["due_label"], it["priority_label"]]
            for it in items
        ]
        
        cards = [{
            "type": "table",
            "title": "Upcoming Outflows & Creditors",
            "columns": ["Liability", "Amount", "Due Date", "Priority"],
            "rows": table_rows
        }]
        
        return self._resp(
            summary,
            intent="PAYABLES",
            numbers=f"• Total Liabilities: {fmt_inr(sm['total_payables'])}\n• Liquid Bank Cash: {fmt_inr(sm['bank_cash'])}\n• Cash Gap: {fmt_inr(sm['coverage_deficit'])}",
            causal="Prioritize Priority 1 bank loan EMIs and sovereign taxes to prevent loan downgrades and bank account freezing.",
            actions=[
                "Ensure ₹88,000 SBI EMI clears on Nov 18",
                "Settle GSTR-3B tax payment on Nov 20",
                "Request 15-day vendor credit extension from raw material suppliers"
            ],
            cards=cards,
            open_tool={"tab": "debtors"},
            suggestions=["What GST do I owe this month?", "Who owes me money?", "How is my money?"]
        )

    def _affordability_reply(self, query: str) -> Dict[str, Any]:
        amounts = extract_amounts(query)
        amount = amounts[0] if amounts else 500000.0
        
        s = self.state
        scen = Scenario(planned_spend=amount, spend_day=0)
        fc = run_forecast(s, self.today, scen)["summary"]
        
        is_safe = fc["lowest_balance"] >= 100000.0
        tone = "good" if is_safe else "bad"
        verdict_title = "APPROVED: Affordable" if is_safe else "CAUTION: Do Not Spend Now"

        lowest_bal = fc["lowest_balance"]
        lowest_lbl = fc["lowest_date_label"]
        if is_safe:
            liquidity_msg = "Your liquidity remains positive throughout the month."
        else:
            deficit_str = fmt_compact(abs(lowest_bal))
            liquidity_msg = f"Spending this amount immediately forces bank cash negative by {deficit_str} on {lowest_lbl}, causing loan EMIs and GST cheques to bounce!"

        summary = (
            f"🛑 **Affordability Analysis for {fmt_inr(amount)} Capex Purchase**\n\n"
            f"**Recommendation**: {verdict_title}.\n\n"
            f"• Current Bank Cash: {fmt_inr(s.physics_state.bank_cash)}\n"
            f"• Planned Immediate Outflow: {fmt_inr(amount)}\n"
            f"• Mandatory GST Tax Due (20 Nov): {fmt_inr(s.gst_snapshot.net_gst_cash_payable)}\n"
            f"• **Projected Lowest Cash Balance**: {fmt_inr(lowest_bal)} on {lowest_lbl}\n\n"
            f"{liquidity_msg}"
        )
        
        cards = [{
            "type": "verdict",
            "tone": tone,
            "title": verdict_title,
            "text": f"Lowest projected balance dips to {fmt_inr(fc['lowest_balance'])} on {fc['lowest_date_label']}."
        }]
        
        return self._resp(
            summary,
            intent="AFFORDABILITY",
            numbers=f"• Requested Spend: {fmt_inr(amount)}\n• Current Bank Cash: {fmt_inr(s.physics_state.bank_cash)}\n• Lowest Balance with Purchase: {fmt_inr(fc['lowest_balance'])}\n• Deficit: {fmt_inr(fc['max_deficit'])}",
            causal="Capital expenditure diverts required working capital before accrued statutory tax liabilities are cleared.",
            actions=[
                "Defer equipment purchase until Reliance settlement clears in December",
                f"Explore asset leasing (EMI option) of {fmt_compact(amount)} over 3-5 years",
                "Activate Liquidity Bridge to free trapped customer cash first"
            ],
            cards=cards,
            open_tool={"tab": "cashflow", "params": {"spend": amount, "spend_day": 0}},
            suggestions=[f"Calculate EMI for {fmt_compact(amount)} at 11% for 3 years", "What GST do I owe this month?", "Who owes me money?"]
        )

    def _emi_reply(self, query: str) -> Dict[str, Any]:
        amounts = extract_amounts(query)
        principal = amounts[0] if amounts else 1000000.0
        rate = extract_rate_pct(query)
        months = extract_tenure_months(query)
        
        loan = loan_summary(principal, rate, months)
        
        # Debt service check against operating profit
        defs = finance_defaults(self.state.business.archetype)
        p_data = defs["profit"]
        pm = profit_model(p_data["monthly_sales"], p_data["cogs_pct"], p_data["running_costs"], p_data["emis"])
        verdict = debt_service_verdict(p_data["emis"] + loan["emi"], pm["operating_profit"])
        
        summary = (
            f"🏦 **Loan & EMI Calculation for {fmt_inr(principal)}**\n\n"
            f"• **Monthly EMI**: **{fmt_inr(loan['emi'])}** per month\n"
            f"• **Interest Rate**: {rate:.1f}% per annum (Reducing balance)\n"
            f"• **Tenure**: {months} Months ({months // 12} Years)\n"
            f"• **Total Interest**: {fmt_inr(loan['total_interest'])} ({loan['interest_share_pct']}% of total payout)\n"
            f"• **Total Repayment**: {fmt_inr(loan['total_payment'])}\n\n"
            f"📊 **Debt Serviceability**: {verdict['text']}"
        )
        
        cards = [{
            "type": "kpis",
            "items": [
                {"label": "Monthly EMI", "value": fmt_inr(loan['emi']), "tone": "good"},
                {"label": "Total Interest", "value": fmt_compact(loan['total_interest']), "tone": "warn"},
                {"label": "Total Payment", "value": fmt_compact(loan['total_payment']), "tone": "neutral"},
                {"label": "Tenure", "value": f"{months // 12} Years", "tone": "neutral"}
            ]
        }]
        
        return self._resp(
            summary,
            intent="EMI",
            numbers=f"• Principal: {fmt_inr(principal)}\n• Monthly EMI: {fmt_inr(loan['emi'])}\n• Total Interest: {fmt_inr(loan['total_interest'])}\n• Total Outflow: {fmt_inr(loan['total_payment'])}",
            causal="Reducing-balance calculations amortize principal monthly, reducing the interest burden in later years.",
            actions=[
                f"Compare with 3-year tenure (EMI: {fmt_inr(calculate_emi(principal, rate, 36))})",
                "Ensure total monthly EMIs do not exceed 40% of operating profit",
                "Maintain 3 months of EMI reserves in liquid bank balance"
            ],
            cards=cards,
            open_tool={"tab": "profit", "params": {"principal": principal, "rate": rate, "months": months}},
            suggestions=["Can I afford a 5 lakh machine?", "How is my profit looking?", "What GST do I owe this month?"]
        )

    def _gst_reply(self, query: str) -> Dict[str, Any]:
        plan = build_gst_plan(self.state, self.today)
        
        summary = (
            f"🏛️ **GST & Tax Status for {plan['due_label']} ({plan['days_left']} Days Left)**\n\n"
            f"• **Gross Output GST on Sales**: {fmt_inr(plan['output_gst'])}\n"
            f"• **Input Tax Credit (ITC Claimed)**: -{fmt_inr(plan['itc_claimed'])}\n"
            f"• **Net Cash GST Payable**: **{fmt_inr(plan['net_payable'])}**\n"
            f"• **Secured in Tax Vault**: {fmt_inr(plan['in_vault'])} ({plan['vault_coverage_pct']}% protected)\n"
            f"• **Cash Shortfall on Due Date**: **{fmt_inr(plan['cash_gap'])}**\n\n"
            f"Crucial Note: **{plan['gst_on_unpaid_pct']}%** of this tax ({fmt_inr(plan['gst_on_unpaid'])}) is for invoices your customers have NOT yet paid. "
            f"Under CGST Section 39, tax is legally payable in cash on the 20th regardless of client payment delays."
        )
        
        cards = [{
            "type": "kpis",
            "items": [
                {"label": "Net GST Due", "value": fmt_compact(plan['net_payable']), "tone": "bad"},
                {"label": "In Tax Vault", "value": fmt_compact(plan['in_vault']), "tone": "good"},
                {"label": "Shortfall", "value": fmt_compact(plan['cash_gap']), "tone": "bad" if plan['cash_gap'] > 0 else "good"},
                {"label": "Days Left", "value": f"{plan['days_left']} Days", "tone": "warn"}
            ]
        }]
        
        return self._resp(
            summary,
            intent="GST",
            numbers=f"• Gross Sales GST: {fmt_inr(plan['output_gst'])}\n• Booked ITC: {fmt_inr(plan['itc_claimed'])}\n• Net Cash Due (20 Nov): {fmt_inr(plan['net_payable'])}\n• Cash Gap: {fmt_inr(plan['cash_gap'])}",
            causal="CGST Act mandates cash settlement on accrual; buyer collection lags do not defer sovereign tax obligations.",
            actions=[step["title"] for step in plan["steps"][:3]],
            cards=cards,
            open_tool={"tab": "gst"},
            suggestions=["Explain ITC", "What is the GST accrual trap?", "Who owes me money?"]
        )

    def _cashflow_reply(self) -> Dict[str, Any]:
        fc = run_forecast(self.state, self.today)["summary"]
        summary = (
            f"📈 **Cash-Flow Forecast & Runway Analysis**\n\n"
            f"• **Starting Bank Reserves**: {fmt_inr(fc['starting_cash'])}\n"
            f"• **Projected 45-Day Lowest Dip**: **{fmt_inr(fc['lowest_balance'])}** on **{fc['lowest_date_label']}**\n"
            f"• **Operating Runway**: {fc['estimated_runway_days']:.0f} Days until cash exhaustion\n"
            f"• **Daily Operating Burn Rate**: {fmt_inr(fc['daily_burn_rate'])} / day\n\n"
            f"{'⚠️ Warning: You enter a cash deficit on Nov 20th due to GST tax settlement.' if fc['is_deficit'] else 'Your cash balance stays solvent throughout the forecast period.'}"
        )
        
        cards = [{
            "type": "kpis",
            "items": [
                {"label": "Starting Cash", "value": fmt_compact(fc['starting_cash']), "tone": "good"},
                {"label": "Lowest Point", "value": fmt_compact(fc['lowest_balance']), "tone": "bad" if fc['is_deficit'] else "good"},
                {"label": "Lowest Date", "value": fc['lowest_date_label'], "tone": "warn"},
                {"label": "Runway", "value": f"{fc['estimated_runway_days']:.0f}d", "tone": "neutral"}
            ]
        }]
        
        return self._resp(
            summary,
            intent="CASHFLOW",
            numbers=f"• Starting: {fmt_inr(fc['starting_cash'])}\n• Lowest ({fc['lowest_date_label']}): {fmt_inr(fc['lowest_balance'])}\n• Daily Burn: {fmt_inr(fc['daily_burn_rate'])}\n• Total Inflows: {fmt_inr(fc['total_inflows'])}",
            causal="Cash trajectory reflects the timing divergence between invoice generation, tax due dates, and actual bank remittances.",
            actions=[
                "Deploy 2% prompt discount to accelerate receivables",
                "Defer discretionary equipment capex",
                "Ensure tax vault is filled to avoid late penalties"
            ],
            cards=cards,
            open_tool={"tab": "cashflow"},
            suggestions=["What if customers pay 15 days late?", "Can I afford a 5 lakh machine?", "What GST do I owe this month?"]
        )

    def _what_if_reply(self, query: str) -> Dict[str, Any]:
        days = extract_days(query)
        s = self.state
        scen = Scenario(delay_days=days)
        fc = run_forecast(s, self.today, scen)["summary"]
        
        summary = (
            f"🔮 **What-If Scenario: Customer Payments Delayed by +{days} Days**\n\n"
            f"• **Starting Bank Reserves**: {fmt_inr(fc['starting_cash'])}\n"
            f"• **Impact on Lowest Cash Dip**: Balance plunges to **{fmt_inr(fc['lowest_balance'])}** on **{fc['lowest_date_label']}**\n"
            f"• **Total Deficit**: {fmt_inr(fc['max_deficit'])}\n"
            f"• **Runway Compressed to**: {fc['estimated_runway_days']:.0f} Days\n\n"
            f"Because customer collections are deferred by {days} days while the Nov 20th tax and Nov 18th loan EMI remain fixed, "
            f"the cash deficit expands dramatically."
        )
        
        cards = [{
            "type": "kpis",
            "items": [
                {"label": "Delay Tested", "value": f"+{days} Days", "tone": "warn"},
                {"label": "New Lowest Dip", "value": fmt_compact(fc['lowest_balance']), "tone": "bad" if fc['is_deficit'] else "good"},
                {"label": "Shortfall", "value": fmt_compact(fc['max_deficit']), "tone": "bad"},
                {"label": "Runway", "value": f"{fc['estimated_runway_days']:.0f}d", "tone": "bad"}
            ]
        }]
        
        return self._resp(
            summary,
            intent="WHAT_IF",
            numbers=f"• Additional Delay: +{days} Days\n• Lowest Cash: {fmt_inr(fc['lowest_balance'])}\n• Immediate Deficit: {fmt_inr(fc['max_deficit'])}",
            causal="Delaying customer collections without delaying statutory deadlines forces bank balances into overdraft.",
            actions=[
                "Offer 2% dynamic settlement discount to prevent delays",
                "Activate Liquidity Bridge to unlock working capital",
                "Notify senior bank manager for temporary OD buffer"
            ],
            cards=cards,
            open_tool={"tab": "cashflow", "params": {"delay": days}},
            suggestions=["What if I cut costs by 15%?", "Who owes me money?", "What GST do I owe this month?"]
        )

    def _reminder_reply(self, query: str) -> Dict[str, Any]:
        recv = ledger.receivables_view(self.state, self.today)
        invoices = recv["invoices"]
        
        # Match customer if mentioned
        matched_inv = invoices[0]
        for inv in invoices:
            if inv["customer_name"].lower() in query.lower():
                matched_inv = inv
                break
                
        rem = matched_inv["reminder"]
        
        summary = (
            f"✉️ **Draft Payment Reminder Generated for {rem['customer_name']}**\n\n"
            f"• **Invoice Number**: #{rem['invoice_number']}\n"
            f"• **Outstanding Amount**: {fmt_inr(rem['amount'])}\n"
            f"• **Overdue Status**: {rem['days_overdue']} Days Overdue\n"
            f"• **Recommended Channel**: {rem['channel'].replace('_', ' ')}\n\n"
            f"Ready to copy and dispatch via WhatsApp or Email:"
        )
        
        cards = [{
            "type": "draft",
            "title": f"Payment Notice: {rem['customer_name']}",
            "subject": rem["subject"],
            "text": rem["message"]
        }]
        
        return self._resp(
            summary,
            intent="REMINDER",
            numbers=f"• Debtor: {rem['customer_name']}\n• Bill Amount: {fmt_inr(rem['amount'])}\n• Overdue Days: {rem['days_overdue']}",
            causal="Formal polite follow-ups referencing MSMED statutory interest dramatically accelerate corporate treasury releases.",
            actions=[
                f"Copy and send via WhatsApp to {rem['customer_name']} finance desk",
                "Offer a 2% prompt settlement rebate for payment within 48h",
                "Log follow-up in receivables register"
            ],
            cards=cards,
            open_tool={"tab": "debtors"},
            suggestions=["Who owes me money?", "What GST do I owe this month?", "Can I afford a 5 lakh machine?"]
        )

    def _profit_reply(self) -> Dict[str, Any]:
        defs = finance_defaults(self.state.business.archetype)
        p = defs["profit"]
        pm = profit_model(p["monthly_sales"], p["cogs_pct"], p["running_costs"], p["emis"])
        
        summary = (
            f"📊 **Monthly Profitability & Break-Even Analysis**\n\n"
            f"• **Estimated Monthly Sales**: {fmt_inr(pm['monthly_sales'])}\n"
            f"• **Cost of Goods Sold (COGS {pm['cogs_pct']:.0f}%)**: -{fmt_inr(pm['monthly_sales'] * (pm['cogs_pct'] / 100.0))}\n"
            f"• **Gross Profit**: {fmt_inr(pm['gross_profit'])}\n"
            f"• **Operating Expenses**: -{fmt_inr(pm['operating_expenses'])}\n"
            f"• **Monthly Loan EMIs**: -{fmt_inr(pm['monthly_emis'])}\n"
            f"• **Net Profit**: **{fmt_inr(pm['net_profit'])}** ({pm['net_margin_pct']:.1f}% net margin)\n\n"
            f"🎯 **Break-Even Sales Volume**: You need minimum sales of **{fmt_inr(pm['breakeven_sales'])}** per month to cover all fixed costs and EMIs."
        )
        
        cards = [{
            "type": "kpis",
            "items": [
                {"label": "Monthly Sales", "value": fmt_compact(pm['monthly_sales']), "tone": "neutral"},
                {"label": "Gross Profit", "value": fmt_compact(pm['gross_profit']), "tone": "good"},
                {"label": "Net Profit", "value": fmt_compact(pm['net_profit']), "tone": "good"},
                {"label": "Break-Even", "value": fmt_compact(pm['breakeven_sales']), "tone": "warn"}
            ]
        }]
        
        return self._resp(
            summary,
            intent="PROFIT",
            numbers=f"• Monthly Sales: {fmt_inr(pm['monthly_sales'])}\n• Gross Margin: {100 - pm['cogs_pct']:.1f}%\n• Net Profit: {fmt_inr(pm['net_profit'])}\n• Break-Even: {fmt_inr(pm['breakeven_sales'])}",
            causal="Break-even sales represent the point where contribution margins completely absorb fixed overheads and debt servicing.",
            actions=[
                "Protect minimum sales threshold of " + fmt_compact(pm['breakeven_sales']),
                "Maintain COGS discipline to preserve gross margin",
                "Keep operating expenses under " + fmt_compact(pm['operating_expenses'])
            ],
            cards=cards,
            open_tool={"tab": "profit"},
            suggestions=["Calculate EMI for 10 lakh at 11% for 5 years", "What GST do I owe this month?", "Who owes me money?"]
        )

    def _explain_topic(self, topic: Any) -> Dict[str, Any]:
        points_str = "\n".join(f"• {p}" for p in topic.key_points)
        summary = (
            f"📚 **{topic.title}**\n\n"
            f"{topic.summary}\n\n"
            f"**Key Compliance & Practical Rules**:\n"
            f"{points_str}"
        )
        return self._resp(
            summary,
            intent="EXPLAIN",
            causal=f"Understanding {topic.title} helps protect against statutory penalties, lost input credit, and cash traps.",
            actions=[
                f"Review {topic.title} in relevant tool tab",
                "Ensure company records match statutory rules"
            ],
            open_tool={"tab": topic.tool} if topic.tool else None,
            suggestions=["What GST do I owe this month?", "Who owes me money?", "Can I afford a 5 lakh machine?"]
        )

    def _fallback_reply(self, raw_message: str) -> Dict[str, Any]:
        return self._health_reply()

