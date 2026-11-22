from __future__ import annotations
import re
from typing import Dict, Any, Optional
from pydantic import BaseModel

class Topic(BaseModel):
    id: str
    title: str
    keywords: str
    summary: str
    key_points: list[str]
    tool: Optional[str] = None

TOPICS = [
    Topic(
        id="itc",
        title="Input Tax Credit (ITC)",
        keywords=r"\b(itc|input tax credit|input credit|tax credit|gstr-2b|gstr 2b)\b",
        summary="Input Tax Credit (ITC) allows you to reduce the GST you owe on sales by the GST you already paid to suppliers on business purchases.",
        key_points=[
            "Section 16(2)(aa) Condition: ITC can ONLY be claimed if the supplier uploads your invoice to their GSTR-1 and it appears in your GSTR-2B.",
            "If an unpaid supplier does not file GSTR-1, your credit is blocked and you must pay cash out of pocket.",
            "Payment to supplier must be made within 180 days; otherwise, claimed ITC must be reversed with 18% interest under Rule 37."
        ],
        tool="gst"
    ),
    Topic(
        id="gst_accrual",
        title="The GST Accrual Rule (Section 39)",
        keywords=r"\b(gst accrual|accrual trap|why pay gst early|unpaid gst|advance tax on bill)\b",
        summary="Under Indian GST law, tax liability triggers on the date of invoice generation (accrual basis), NOT when the customer actually transfers cash to your bank.",
        key_points=[
            "If you bill an enterprise customer ₹10 Lakhs + 18% GST (₹1.80L) on Nov 16th, that ₹1.80L GST must be remitted in cash by Nov 20th.",
            "Even if the enterprise customer takes 60 or 90 days to pay, the tax portal does not wait.",
            "This creates the classic Indian MSME cash crunch: profitable on paper, but bank account drained by statutory tax deadlines."
        ],
        tool="gst"
    ),
    Topic(
        id="gst_dates",
        title="GST Deadlines & Late Penalties",
        keywords=r"\b(gst date|deadline|gstr-1 due|gstr-3b due|late fee|gst penalty|penalties|section 50)\b",
        summary="Indian GST requires strict monthly filings: GSTR-1 by the 11th of each month, and GSTR-3B tax payment by the 20th.",
        key_points=[
            "GSTR-1 Due Date: 11th of each month (details of outward sales).",
            "GSTR-3B Due Date: 20th of each month (summary return & mandatory cash tax payment).",
            "Late Filing Fee: ₹50/day (₹20/day for nil return) under Section 47.",
            "Interest on Late Tax Payment: 18% per annum calculated daily on net cash liability under Section 50(1).",
            "Blocking of E-Way Bills: If GSTR-3B is unfiled for 2 consecutive periods, E-way bill portal blocks transport of goods under Rule 138E."
        ],
        tool="gst"
    ),
    Topic(
        id="msme_45_days",
        title="MSME 45-Day Payment Rule (Section 43B(h))",
        keywords=r"\b(45 day|45 days|msme 45|section 43b|43b\(h\)|msmed|msme payment rule)\b",
        summary="Section 43B(h) of the Income Tax Act mandates that buyers must settle dues to Micro and Small Enterprises within 45 days (or 15 days if no written agreement).",
        key_points=[
            "If a corporate buyer fails to pay a registered MSME within 45 days, the unpaid purchase cannot be deducted as an expense in that financial year.",
            "The buyer must add the full invoice amount to their taxable profit and pay 25-30% corporate income tax on it.",
            "Additionally, Section 16 of the MSMED Act awards compound interest at 3x the RBI bank rate on delayed payments."
        ],
        tool="money"
    ),
    Topic(
        id="einvoice",
        title="e-Invoicing Rules & Turnover Threshold",
        keywords=r"\b(e-invoicing|e invoicing|einvoice|irn|qr code|e invoice limit)\b",
        summary="GST e-Invoicing requires B2B invoices to be registered electronically on the Invoice Registration Portal (IRP) to generate an IRN and QR code.",
        key_points=[
            "Turnover Threshold: Mandatory for any registered business whose annual aggregate turnover exceeded ₹5 Crore in any preceding financial year since 2017-18.",
            "Invoices issued without an IRN are treated as invalid legal documents—the buyer cannot claim ITC, and goods can be detained in transit.",
            "Applicable strictly to B2B supplies, exports, and credit/debit notes."
        ],
        tool="gst"
    ),
    Topic(
        id="wormhole",
        title="Liquidity Bridge Strategy (Instant Teleportation)",
        keywords=r"\b(wormhole|liquidity bridge|cash bridge|bridge liquidity|teleport cash)\b",
        summary="A Liquidity Bridge collapses the temporal delay between invoice billing and cash settlement through simultaneous causal financial actions.",
        key_points=[
            "1. Dynamic Settlement Discount: Offer 2.0% immediate rebate to prime debtors (Reliance, L&T) to unlock 98% of cash within 36 hours.",
            "2. Intelligent Tax Vault Sweep: Immediately auto-segregate statutory tax portion (18%) to neutralize GST default.",
            "3. Supplier ITC Retention: Reconcile supplier filings to safeguard booked input tax credit."
        ],
        tool="wormhole"
    ),
    Topic(
        id="gst_basics",
        title="GST Rates & Tax Slabs in India",
        keywords=r"\b(gst rates|gst slabs|gst basic|what is gst|5%|12%|18%|28%)\b",
        summary="Goods and Services Tax (GST) is a dual destination-based tax levied by Central and State Governments on supply of goods and services.",
        key_points=[
            "Standard Rate Slabs: 0% (exempt essentials), 5% (daily staples), 12% (processed goods), 18% (standard B2B goods, steel, electronics, IT services), and 28% (automobiles, luxury/sin goods).",
            "Intra-State (within state): CGST (50%) + SGST (50%).",
            "Inter-State (across state borders): IGST (100% credited to Central Govt, shared with destination state)."
        ],
        tool="gst"
    )
]

def find_topic(query: str) -> Optional[Topic]:
    q = query.lower()
    for t in TOPICS:
        if re.search(t.keywords, q):
            return t
    return None
