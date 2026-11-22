from __future__ import annotations
from datetime import date, timedelta
from typing import Dict, Any, List
from backend.models.schemas import (
    BusinessProfile, Invoice, Customer, Supplier, Obligation,
    GSTLiabilitySnapshot, MoneyPhysicsState, MoneyHealthGenome,
    RupeePacket, AetherPravahState
)
from backend.physics.engine import MoneyPhysicsEngine
from backend.physics.singularity import GSTSingularityPredictor

def create_user_custom_business(
    company_name: str = "My Business Enterprise",
    owner_name: str = "Business Owner",
    business_type: str = "Trading & Services",
    city: str = "Mumbai, Maharashtra",
    gstin: str = "27AAACU1234M1Z5",
    bank_cash: float = 300000.0,
    tax_vault: float = 25000.0,
    monthly_burn: float = 80000.0,
    today: date = date(2026, 11, 16)
) -> AetherPravahState:
    """Creates a custom, dynamic business state for any user."""
    biz = BusinessProfile(
        id="BIZ-USER-CUSTOM",
        name=company_name,
        owner_name=owner_name,
        archetype=business_type,
        tagline=f"{business_type} Operations",
        city=city,
        gstin=gstin,
        annual_turnover=max(1200000.0, bank_cash * 12.0),
        employee_count=8,
        bank_name="Primary Bank Current Account",
        overdraft_limit=max(500000.0, bank_cash * 0.5)
    )

    invoices: List[Invoice] = []
    customers: List[Customer] = []
    suppliers: List[Supplier] = []
    obligations: List[Obligation] = []

    gst_snapshot = GSTLiabilitySnapshot(
        period="2026-11",
        gstr3b_due_date=date(2026, 11, 20),
        output_gst_gross=0.0,
        gst_on_unpaid_invoices=0.0,
        input_tax_credit_booked=0.0,
        itc_blocked_or_risky=0.0,
        net_gst_cash_payable=0.0,
        tax_vault_reserved=tax_vault,
        tax_deficit=0.0,
        singularity_risk_score=0.1
    )

    packets = [
        RupeePacket(
            amount=bank_cash,
            source_entity="BANK_OPENING_BALANCE",
            current_location="BANK_AVAILABLE"
        ),
        RupeePacket(
            amount=tax_vault,
            source_entity="TAX_VAULT_RESERVE",
            current_location="TAX_VAULT"
        )
    ]

    physics = MoneyPhysicsEngine.calculate_state(
        current_date=today,
        bank_cash=bank_cash,
        tax_vault=tax_vault,
        invoices=invoices,
        obligations=obligations,
        gst_snapshot=gst_snapshot,
        rupee_packets=packets,
        monthly_burn_rate=monthly_burn
    )

    genome = MoneyHealthGenome(
        overall_score=82,
        liquidity_vitality=85,
        gst_accrual_shield=80,
        customer_payment_velocity=82,
        debt_gravity_balance=80,
        trajectory="STABLE_BALANCED",
        genome_markers={"status": "CUSTOM_PROFILE_ACTIVE"}
    )

    return AetherPravahState(
        business=biz,
        physics_state=physics,
        genome=genome,
        invoices=invoices,
        customers=customers,
        suppliers=suppliers,
        obligations=obligations,
        gst_snapshot=gst_snapshot,
        active_wormholes=[],
        rupee_packets=packets,
        causal_nodes=[],
        causal_edges=[]
    )

def generate_bharat_steel_data(today: date = date(2026, 11, 16)) -> AetherPravahState:
    """
    Archetype 1: Bharat Steel Traders
    Wholesale B2B Steel Trader (Raipur & Navi Mumbai).
    Razor-thin margins, high volume, heavy reliance on 60-90 day enterprise credit.
    Currently facing an acute GST Accrual Singularity on Nov 20!
    """
    biz = BusinessProfile(
        id="BIZ-BHARAT-STEEL",
        name="Bharat Steel Traders Pvt Ltd",
        archetype="STEEL_TRADER",
        tagline="Heavy Steels, TMT Bars & Structural Sections",
        city="Navi Mumbai, Maharashtra",
        gstin="27AABCB1234F1Z8",
        annual_turnover=84000000.0,  # ₹8.4 Cr
        employee_count=14,
        bank_name="State Bank of India (MSME SME Branch)",
        overdraft_limit=1500000.0
    )

    customers = [
        Customer(
            id="CUST-RELIANCE-INFRA",
            name="Reliance Infra Projects Ltd",
            gstin="27AAACR1234M1Z2",
            industry="Infrastructure & Construction",
            payment_behavior_score=68.0,
            psychological_profile="BUREAUCRATIC_ENTERPRISE",
            typical_delay_days=35,
            optimal_chasing_channel="DIRECTOR_CALL",
            discount_sensitivity=0.85,
            total_outstanding=1475000.0
        ),
        Customer(
            id="CUST-LNT-BUILDERS",
            name="Larsen & Toubro Heavy Fab",
            gstin="27AAACL5678P1Z9",
            industry="Engineering",
            payment_behavior_score=78.0,
            psychological_profile="BUREAUCRATIC_ENTERPRISE",
            typical_delay_days=28,
            optimal_chasing_channel="WHATSAPP_GENTLE",
            discount_sensitivity=0.75,
            total_outstanding=950000.0
        ),
        Customer(
            id="CUST-SHREE-FAB",
            name="Shree Ram Fabrication Works",
            gstin="27AAACS9988D1Z4",
            industry="SME Fabrication",
            payment_behavior_score=45.0,
            psychological_profile="CHRONIC_DEFENDER",
            typical_delay_days=50,
            optimal_chasing_channel="FORMAL_LEGAL_NOTICE",
            discount_sensitivity=0.40,
            total_outstanding=420000.0
        )
    ]

    invoices = [
        # Invoice 1: Accrued GST trap! Unpaid large invoice to Reliance
        Invoice(
            id="INV-BST-2610-01",
            invoice_number="BST/2026/1042",
            customer_id="CUST-RELIANCE-INFRA",
            customer_name="Reliance Infra Projects Ltd",
            issue_date=today - timedelta(days=25),
            due_date=today + timedelta(days=5),
            base_amount=1250000.0,
            gst_rate=0.18,
            gst_amount=225000.0,
            total_amount=1475000.0,
            amount_paid=0.0,
            status="ISSUED",
            gst_filing_period="2026-11",
            itc_eligible=True,
            delay_prediction_days=35.0
        ),
        # Invoice 2: L&T heavy steel delivery
        Invoice(
            id="INV-BST-2610-02",
            invoice_number="BST/2026/1043",
            customer_id="CUST-LNT-BUILDERS",
            customer_name="Larsen & Toubro Heavy Fab",
            issue_date=today - timedelta(days=20),
            due_date=today + timedelta(days=10),
            base_amount=805085.0,
            gst_rate=0.18,
            gst_amount=144915.0,
            total_amount=950000.0,
            amount_paid=0.0,
            status="ISSUED",
            gst_filing_period="2026-11",
            itc_eligible=True,
            delay_prediction_days=28.0
        ),
        # Invoice 3: Shree Ram fabrication (Overdue)
        Invoice(
            id="INV-BST-2609-08",
            invoice_number="BST/2026/0991",
            customer_id="CUST-SHREE-FAB",
            customer_name="Shree Ram Fabrication Works",
            issue_date=today - timedelta(days=55),
            due_date=today - timedelta(days=25),
            base_amount=355932.0,
            gst_rate=0.18,
            gst_amount=64068.0,
            total_amount=420000.0,
            amount_paid=0.0,
            status="OVERDUE",
            gst_filing_period="2026-10",
            itc_eligible=True,
            delay_prediction_days=50.0
        )
    ]

    suppliers = [
        Supplier(
            id="SUPP-JINDAL-STEEL",
            name="Jindal Steel & Power Ltd",
            gstin="22AAACJ4321Q1Z1",
            itc_compliance_score=98.0,
            credit_period_days=21,
            total_payable=680000.0,
            pending_itc_lockup=0.0
        )
    ]

    obligations = [
        Obligation(
            id="OBL-SBI-OD-INTEREST",
            name="SBI MSME Term Loan & OD Interest",
            obligation_type="BANK_EMI",
            amount=88000.0,
            due_date=today + timedelta(days=2),  # Due Nov 18
            priority=1,
            is_negotiable=False
        ),
        Obligation(
            id="OBL-WAREHOUSE-RENT",
            name="Navi Mumbai Stockyard Lease",
            obligation_type="OFFICE_RENT",
            amount=65000.0,
            due_date=today + timedelta(days=6),  # Due Nov 22
            priority=3,
            is_negotiable=True
        )
    ]

    # Gross GST owed for period: Reliance (225k) + L&T (144.9k) = 369.9k
    # Valid ITC available: ~85k
    # Net GST Cash Payable on 20th: 284,915.0
    gst_snapshot = GSTLiabilitySnapshot(
        period="2026-11",
        gstr3b_due_date=today + timedelta(days=4),  # Nov 20!
        output_gst_gross=369915.0,
        gst_on_unpaid_invoices=369915.0,  # 100% of GST is on unpaid invoices!
        input_tax_credit_booked=85000.0,
        itc_blocked_or_risky=12000.0,
        net_gst_cash_payable=284915.0,
        tax_vault_reserved=35000.0,  # Only 35k reserved!
        tax_deficit=249915.0,
        singularity_risk_score=0.94
    )

    bank_cash = 185000.0  # Liquid cash in SBI
    tax_vault = 35000.0

    # Build RupeePackets
    rupee_packets = []
    # Bank packets
    rupee_packets.append(RupeePacket(
        amount=bank_cash,
        source_entity="SBI-OD-ACCOUNT",
        current_location="BANK_AVAILABLE",
        causal_history=["Retained working capital"],
        tax_gravity_vector=0.0
    ))
    rupee_packets.append(RupeePacket(
        amount=tax_vault,
        source_entity="TAX-VAULT-RESERVE",
        current_location="TAX_VAULT",
        causal_history=["Auto-swept GST reserve"],
        tax_gravity_vector=1.0
    ))
    # Receivable packets
    for inv in invoices:
        rupee_packets.append(RupeePacket(
            amount=inv.unpaid_cash,
            source_entity=inv.invoice_number,
            current_location="PENDING_RECEIVABLE",
            causal_history=[f"Receivable from {inv.customer_name}"],
            tax_gravity_vector=inv.gst_amount / max(1.0, inv.total_amount)
        ))

    physics = MoneyPhysicsEngine.calculate_state(
        current_date=today,
        bank_cash=bank_cash,
        tax_vault=tax_vault,
        invoices=invoices,
        obligations=obligations,
        gst_snapshot=gst_snapshot,
        rupee_packets=rupee_packets,
        monthly_burn_rate=240000.0
    )

    genome = MoneyHealthGenome(
        overall_score=38,
        liquidity_vitality=28,
        gst_accrual_shield=19,
        customer_payment_velocity=41,
        debt_gravity_balance=62,
        trajectory="BLACK_HOLE_IMMINENT",
        genome_markers={
            "PRIMARY_RISK": "GST Accrual Singularity on Nov 20",
            "DEFICIT": "₹2,49,915.00 shortfall against statutory GSTR-3B",
            "VISCOSITY": "3.85 (High friction from Enterprise 30-day payment lag)"
        }
    )

    return AetherPravahState(
        business=biz,
        physics_state=physics,
        genome=genome,
        invoices=invoices,
        customers=customers,
        suppliers=suppliers,
        obligations=obligations,
        gst_snapshot=gst_snapshot,
        active_wormholes=[],
        rupee_packets=rupee_packets,
        causal_nodes=[],
        causal_edges=[]
    )

def generate_vastrakala_data(today: date = date(2026, 11, 16)) -> AetherPravahState:
    """
    Archetype 2: VastraKala Apparels
    Garment Manufacturer & Exporter (Surat & Tirupur).
    Diwali peak inventory lockup, supplier ITC unfiled trap.
    """
    biz = BusinessProfile(
        id="BIZ-VASTRAKALA",
        name="VastraKala Textiles LLP",
        archetype="GARMENT_MANUFACTURER",
        tagline="Ethnic Wear, Cotton Apparels & Export Fabrics",
        city="Surat, Gujarat",
        gstin="24AACCV4567K1Z3",
        annual_turnover=36000000.0,
        employee_count=26,
        bank_name="HDFC Bank (Commercial Banking)",
        overdraft_limit=800000.0
    )

    customers = [
        Customer(
            id="CUST-FABINDIA-RETAIL",
            name="FabStyle Retail Chains",
            gstin="24AAACF1122J1Z5",
            industry="Apparel Retail",
            payment_behavior_score=72.0,
            psychological_profile="SEASONAL_SLACKER",
            typical_delay_days=25,
            optimal_chasing_channel="WHATSAPP_GENTLE",
            discount_sensitivity=0.80,
            total_outstanding=820000.0
        )
    ]

    invoices = [
        Invoice(
            id="INV-VT-2610-14",
            invoice_number="VT/26/110",
            customer_id="CUST-FABINDIA-RETAIL",
            customer_name="FabStyle Retail Chains",
            issue_date=today - timedelta(days=18),
            due_date=today + timedelta(days=12),
            base_amount=694915.0,
            gst_rate=0.18,
            gst_amount=125085.0,
            total_amount=820000.0,
            amount_paid=0.0,
            status="ISSUED",
            gst_filing_period="2026-11",
            itc_eligible=True,
            delay_prediction_days=25.0
        )
    ]

    suppliers = [
        Supplier(
            id="SUPP-SURAT-DYEING",
            name="Surat Silk & Dyeing Mills",
            gstin="24AAACS7766R1Z9",
            itc_compliance_score=42.0,  # Unreliable GSTR-1 filer!
            credit_period_days=30,
            total_payable=340000.0,
            pending_itc_lockup=61200.0  # ITC blocked from supplier non-filing
        )
    ]

    obligations = [
        Obligation(
            id="OBL-KNITTING-EMI",
            name="Automatic Knitting Machinery EMI",
            obligation_type="BANK_EMI",
            amount=55000.0,
            due_date=today + timedelta(days=8),
            priority=1,
            is_negotiable=False
        )
    ]

    gst_snapshot = GSTLiabilitySnapshot(
        period="2026-11",
        gstr3b_due_date=today + timedelta(days=4),
        output_gst_gross=125085.0,
        gst_on_unpaid_invoices=125085.0,
        input_tax_credit_booked=32000.0,
        itc_blocked_or_risky=61200.0,
        net_gst_cash_payable=93085.0,
        tax_vault_reserved=40000.0,
        tax_deficit=53085.0,
        singularity_risk_score=0.68
    )

    bank_cash = 210000.0
    tax_vault = 40000.0

    rupee_packets = [
        RupeePacket(amount=bank_cash, source_entity="HDFC-CURRENT", current_location="BANK_AVAILABLE"),
        RupeePacket(amount=tax_vault, source_entity="TAX-VAULT", current_location="TAX_VAULT"),
        RupeePacket(amount=820000.0, source_entity="VT/26/110", current_location="PENDING_RECEIVABLE")
    ]

    physics = MoneyPhysicsEngine.calculate_state(
        current_date=today,
        bank_cash=bank_cash,
        tax_vault=tax_vault,
        invoices=invoices,
        obligations=obligations,
        gst_snapshot=gst_snapshot,
        rupee_packets=rupee_packets,
        monthly_burn_rate=180000.0
    )

    genome = MoneyHealthGenome(
        overall_score=54,
        liquidity_vitality=51,
        gst_accrual_shield=44,
        customer_payment_velocity=58,
        debt_gravity_balance=65,
        trajectory="DECAYING_WARNING",
        genome_markers={
            "SUPPLIER_RISK": "₹61,200 ITC blocked due to Surat Dyeing non-filing",
            "SEASONAL_DRAG": "Festival inventory hold"
        }
    )

    return AetherPravahState(
        business=biz,
        physics_state=physics,
        genome=genome,
        invoices=invoices,
        customers=customers,
        suppliers=suppliers,
        obligations=obligations,
        gst_snapshot=gst_snapshot,
        active_wormholes=[],
        rupee_packets=rupee_packets,
        causal_nodes=[],
        causal_edges=[]
    )

def generate_nexus_pulse_data(today: date = date(2026, 11, 16)) -> AetherPravahState:
    """
    Archetype 3: NexusPulse Media
    Digital Agency & Software Dev (Bengaluru).
    High 18% service GST on retainers, massive payroll due on 1st of each month.
    """
    biz = BusinessProfile(
        id="BIZ-NEXUS-PULSE",
        name="NexusPulse Digital Solutions Pvt Ltd",
        archetype="DIGITAL_AGENCY",
        tagline="Performance Marketing & SaaS Engineering",
        city="Bengaluru, Karnataka",
        gstin="29AABCN8899M1Z7",
        annual_turnover=22000000.0,
        employee_count=18,
        bank_name="ICICI Bank (Tech Corporate Branch)",
        overdraft_limit=500000.0
    )

    customers = [
        Customer(
            id="CUST-GROW-FINTECH",
            name="GrowFast Fintech India",
            gstin="29AAACG4433P1Z2",
            industry="Fintech SaaS",
            payment_behavior_score=85.0,
            psychological_profile="PROMPT_PAYER",
            typical_delay_days=10,
            optimal_chasing_channel="WHATSAPP_GENTLE",
            discount_sensitivity=0.60,
            total_outstanding=590000.0
        )
    ]

    invoices = [
        Invoice(
            id="INV-NP-2611-04",
            invoice_number="NP/26/401",
            customer_id="CUST-GROW-FINTECH",
            customer_name="GrowFast Fintech India",
            issue_date=today - timedelta(days=10),
            due_date=today + timedelta(days=10),
            base_amount=500000.0,
            gst_rate=0.18,
            gst_amount=90000.0,
            total_amount=590000.0,
            amount_paid=0.0,
            status="ISSUED",
            gst_filing_period="2026-11",
            itc_eligible=True,
            delay_prediction_days=10.0
        )
    ]

    suppliers = [
        Supplier(
            id="SUPP-AWS-CLOUD",
            name="Amazon Web Services India",
            gstin="29AAACA1122C1Z4",
            itc_compliance_score=99.0,
            credit_period_days=15,
            total_payable=85000.0,
            pending_itc_lockup=0.0
        )
    ]

    obligations = [
        Obligation(
            id="OBL-DEV-PAYROLL",
            name="18 Engineers & Marketers Payroll",
            obligation_type="PAYROLL",
            amount=550000.0,
            due_date=today + timedelta(days=14),  # Dec 1
            priority=1,
            is_negotiable=False
        )
    ]

    gst_snapshot = GSTLiabilitySnapshot(
        period="2026-11",
        gstr3b_due_date=today + timedelta(days=4),
        output_gst_gross=90000.0,
        gst_on_unpaid_invoices=90000.0,
        input_tax_credit_booked=22000.0,
        itc_blocked_or_risky=0.0,
        net_gst_cash_payable=68000.0,
        tax_vault_reserved=50000.0,
        tax_deficit=18000.0,
        singularity_risk_score=0.25
    )

    bank_cash = 480000.0
    tax_vault = 50000.0

    rupee_packets = [
        RupeePacket(amount=bank_cash, source_entity="ICICI-MAIN", current_location="BANK_AVAILABLE"),
        RupeePacket(amount=tax_vault, source_entity="TAX-VAULT", current_location="TAX_VAULT"),
        RupeePacket(amount=590000.0, source_entity="NP/26/401", current_location="PENDING_RECEIVABLE")
    ]

    physics = MoneyPhysicsEngine.calculate_state(
        current_date=today,
        bank_cash=bank_cash,
        tax_vault=tax_vault,
        invoices=invoices,
        obligations=obligations,
        gst_snapshot=gst_snapshot,
        rupee_packets=rupee_packets,
        monthly_burn_rate=650000.0
    )

    genome = MoneyHealthGenome(
        overall_score=78,
        liquidity_vitality=76,
        gst_accrual_shield=84,
        customer_payment_velocity=82,
        debt_gravity_balance=71,
        trajectory="STABLE_BALANCED",
        genome_markers={
            "HEALTH": "Strong recurring retainers",
            "WATCH": "Dec 1st Payroll alignment"
        }
    )

    return AetherPravahState(
        business=biz,
        physics_state=physics,
        genome=genome,
        invoices=invoices,
        customers=customers,
        suppliers=suppliers,
        obligations=obligations,
        gst_snapshot=gst_snapshot,
        active_wormholes=[],
        rupee_packets=rupee_packets,
        causal_nodes=[],
        causal_edges=[]
    )
