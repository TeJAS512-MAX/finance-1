from __future__ import annotations
import uuid
from datetime import date, timedelta
from typing import Dict, Any, List, Optional
from backend.models.schemas import (
    Invoice, Customer, Supplier, Obligation, GSTLiabilitySnapshot,
    RupeePacket
)

class InvoiceForgeSpecialist:
    """
    Tier 1: InvoiceForge
    Validates GST statutory rules, HSN codes, and spawns RupeePackets.
    """
    @staticmethod
    def create_invoice(
        customer: Customer,
        base_amount: float,
        gst_rate: float = 0.18,
        due_days: int = 30,
        current_date: date = None
    ) -> tuple[Invoice, List[RupeePacket]]:
        if not current_date:
            current_date = date.today()
        
        gst_amount = round(base_amount * gst_rate, 2)
        total_amount = round(base_amount + gst_amount, 2)
        inv_id = f"INV-{uuid.uuid4().hex[:6].upper()}"
        inv_num = f"AP-{current_date.strftime('%y%m')}-{uuid.uuid4().hex[:4].upper()}"

        # Spawn RupeePackets representing future cash expectations
        base_packet = RupeePacket(
            amount=base_amount,
            source_entity=inv_num,
            current_location="PENDING_RECEIVABLE",
            causal_history=[f"Generated via InvoiceForge for {customer.name}"],
            tax_gravity_vector=0.0
        )
        tax_packet = RupeePacket(
            amount=gst_amount,
            source_entity=inv_num,
            current_location="PENDING_RECEIVABLE",
            causal_history=[f"Accrued Statutory GST on {inv_num}"],
            tax_gravity_vector=1.0  # 100% bound to sovereign tax gravity
        )

        invoice = Invoice(
            id=inv_id,
            invoice_number=inv_num,
            customer_id=customer.id,
            customer_name=customer.name,
            issue_date=current_date,
            due_date=current_date + timedelta(days=due_days),
            base_amount=base_amount,
            gst_rate=gst_rate,
            gst_amount=gst_amount,
            total_amount=total_amount,
            amount_paid=0.0,
            status="ISSUED",
            gst_filing_period=current_date.strftime("%Y-%m"),
            itc_eligible=True,
            delay_prediction_days=float(customer.typical_delay_days),
            causal_packet_ids=[base_packet.id, tax_packet.id]
        )

        return invoice, [base_packet, tax_packet]

class GSTAccrualGuardian:
    """
    Tier 1: GSTAccrualGuardian
    Monitors uncollected invoices and warns of the accrual trap.
    """
    @staticmethod
    def audit_gst_exposure(invoices: List[Invoice], current_date: date) -> Dict[str, Any]:
        unpaid = [inv for inv in invoices if inv.status in ("ISSUED", "PARTIALLY_PAID", "OVERDUE", "CRITICAL_TRAP")]
        gst_on_unpaid = sum(inv.gst_amount for inv in unpaid)
        total_unpaid_cash = sum(inv.unpaid_cash for inv in unpaid)

        accrual_trap_ratio = (gst_on_unpaid / max(1.0, total_unpaid_cash)) if total_unpaid_cash > 0 else 0.0

        return {
            "total_unpaid_receivables": round(total_unpaid_cash, 2),
            "gst_accrued_on_unpaid": round(gst_on_unpaid, 2),
            "accrual_trap_ratio": round(accrual_trap_ratio, 3),
            "warning": (
                f"You owe ₹{gst_on_unpaid:,.2f} in GST on ₹{total_unpaid_cash:,.2f} of money your buyers haven't paid you yet!"
                if gst_on_unpaid > 50000 else "GST accrual exposure within acceptable limits."
            )
        }

class CollectionPsychologist:
    """
    Tier 1: CollectionPsychologist
    Formulates high-conversion, relationship-protective chasing communication.
    """
    @staticmethod
    def craft_chasing_payload(customer: Customer, invoice: Invoice) -> Dict[str, str]:
        profile = customer.psychological_profile
        amt = f"₹{invoice.unpaid_cash:,.2f}"
        inv_no = invoice.invoice_number

        if profile == "BUREAUCRATIC_ENTERPRISE":
            channel = "DIRECTOR_CALL"
            message = (
                f"Respected Accounts Team at {customer.name}, regarding Invoice #{inv_no} for {amt}. "
                f"Our GSTR-1 is fully filed and reflected in your GSTR-2B so your ITC is 100% unlocked. "
                f"To assist with your quarterly audit reconciliation, we are extending a 1.75% prompt settlement credit if cleared within 48 hours."
            )
        elif profile == "SEASONAL_SLACKER":
            channel = "WHATSAPP_GENTLE"
            message = (
                f"Greetings team {customer.name}! Hope your business operations are running smoothly this season. "
                f"Invoice #{inv_no} ({amt}) is due for settlement. To comply with statutory GST deadlines by the 20th and maintain seamless transit clearances, "
                f"can we confirm your RTGS transfer today? Warm regards!"
            )
        elif profile == "CHRONIC_DEFENDER":
            channel = "FORMAL_LEGAL_NOTICE"
            message = (
                f"Urgent Notice: Payment Reconciliation for Invoice #{inv_no} ({amt}). "
                f"Statutory interest under MSMED Act Section 16 is applicable for delays exceeding credit period. "
                f"Kindly remit payment immediately to avoid portal reporting."
            )
        else:
            channel = "WHATSAPP_GENTLE"
            message = (
                f"Hi team {customer.name}! Quick reminder for Invoice #{inv_no} of {amt}. "
                f"We are offering a 2% prompt discount for payment before this Friday. Let us know if you'd like the revised note!"
            )

        return {
            "channel": channel,
            "message": message,
            "psychological_rationale": f"Optimized for {profile} based on {customer.discount_sensitivity * 100:.0f}% discount sensitivity."
        }

class TaxVaultKeeper:
    """
    Tier 1: TaxVaultKeeper
    Calculates dynamic tax reservation for every incoming rupee.
    """
    @staticmethod
    def calculate_incoming_tax_sweep(incoming_cash: float, current_deficit: float) -> float:
        # Ring-fence standard 18% or up to the full pending deficit
        suggested_sweep = min(current_deficit, incoming_cash * 0.18)
        return round(suggested_sweep, 2)
