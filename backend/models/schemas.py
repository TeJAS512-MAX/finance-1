from __future__ import annotations
from typing import List, Dict, Optional, Any, Literal
from datetime import date, datetime
from pydantic import BaseModel, Field
import uuid

# --- CAUSAL GRAPH PRIMITIVES ---

class CausalEdge(BaseModel):
    source_id: str
    target_id: str
    relation_type: str = Field(..., description="e.g. INVOICE_GENERATES_GST, CUSTOMER_PAYS_INVOICE, GST_DRAINS_BANK")
    weight: float = Field(default=1.0, description="Causal strength or probability [0, 1]")
    viscosity_days: float = Field(default=0.0, description="Temporal transmission lag in days")
    is_counterfactual: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)

class CausalNode(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    node_type: Literal[
        "RUPEE_PACKET", "INVOICE", "CUSTOMER", "SUPPLIER", 
        "TAX_LIABILITY", "LOAN_OBLIGATION", "BANK_ACCOUNT", "TAX_VAULT"
    ]
    label: str
    value: float = 0.0
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    properties: Dict[str, Any] = Field(default_factory=dict)

# --- QUANTUM-INSPIRED RUPEEPACKET ---

class RupeePacket(BaseModel):
    id: str = Field(default_factory=lambda: f"RPK-{uuid.uuid4().hex[:8]}")
    amount: float = Field(..., description="Value in INR (₹)")
    source_entity: str = Field(..., description="Originating invoice, deposit, or loan")
    current_location: Literal["BANK_AVAILABLE", "TAX_VAULT", "PENDING_RECEIVABLE", "LOCKED_INVENTORY", "ESCROW"]
    causal_history: List[str] = Field(default_factory=list, description="Causal trace of all hops")
    tax_gravity_vector: float = Field(default=0.18, description="Portion of packet bound to sovereign GST tax gravity")
    decay_half_life_days: float = Field(default=30.0, description="Viscous inflation/opportunity decay rate")
    probability_distribution: Dict[str, float] = Field(
        default_factory=lambda: {"BANK": 0.7, "TAX_VAULT": 0.18, "VENDOR_PAYOUT": 0.12},
        description="Probability amplitude of future destination"
    )

# --- INVOICE & ACTORS ---

class Invoice(BaseModel):
    id: str = Field(default_factory=lambda: f"INV-{uuid.uuid4().hex[:6].upper()}")
    invoice_number: str
    customer_id: str
    customer_name: str
    issue_date: date
    due_date: date
    base_amount: float
    gst_rate: float = Field(default=0.18, description="0.05, 0.12, 0.18, or 0.28")
    gst_amount: float
    total_amount: float
    amount_paid: float = 0.0
    status: Literal["ISSUED", "PARTIALLY_PAID", "PAID", "OVERDUE", "CRITICAL_TRAP"] = "ISSUED"
    gst_filing_period: str = Field(..., description="e.g. 2026-11")
    itc_eligible: bool = True
    delay_prediction_days: float = 0.0
    causal_packet_ids: List[str] = Field(default_factory=list)

    @property
    def gst_outstanding(self) -> float:
        """GST is strictly accrued at invoice issue date regardless of customer payment!"""
        return self.gst_amount if self.status != "PAID" else 0.0

    @property
    def unpaid_cash(self) -> float:
        return max(0.0, self.total_amount - self.amount_paid)

class Customer(BaseModel):
    id: str = Field(default_factory=lambda: f"CUST-{uuid.uuid4().hex[:6].upper()}")
    name: str
    gstin: str
    industry: str
    payment_behavior_score: float = Field(..., ge=0.0, le=100.0, description="Historical promptness 0-100")
    psychological_profile: Literal[
        "PROMPT_PAYER", "BUREAUCRATIC_ENTERPRISE", "SEASONAL_SLACKER", 
        "RELATIONSHIP_DEPENDENT", "CHRONIC_DEFENDER"
    ]
    typical_delay_days: int = Field(default=15)
    optimal_chasing_channel: Literal["WHATSAPP_GENTLE", "DIRECTOR_CALL", "FORMAL_LEGAL_NOTICE", "EARLY_CASH_DISCOUNT"] = "WHATSAPP_GENTLE"
    discount_sensitivity: float = Field(default=0.8, description="Responsiveness to 1.5% - 2.5% cash discounts [0, 1]")
    total_outstanding: float = 0.0

class Supplier(BaseModel):
    id: str = Field(default_factory=lambda: f"SUPP-{uuid.uuid4().hex[:6].upper()}")
    name: str
    gstin: str
    itc_compliance_score: float = Field(..., ge=0.0, le=100.0, description="Reliability of supplier GSTR-1 uploading")
    credit_period_days: int = 30
    total_payable: float = 0.0
    pending_itc_lockup: float = 0.0

class Obligation(BaseModel):
    id: str = Field(default_factory=lambda: f"OBL-{uuid.uuid4().hex[:6].upper()}")
    name: str
    obligation_type: Literal["BANK_EMI", "PAYROLL", "VENDOR_PAYABLE", "STATUTORY_PF_ESI", "OFFICE_RENT"]
    amount: float
    due_date: date
    priority: int = Field(default=1, description="1=Supreme critical, 5=Flexible")
    is_negotiable: bool = False

# --- GST SINGULARITY & TAX VAULT ---

class GSTLiabilitySnapshot(BaseModel):
    period: str = Field(..., description="e.g. 2026-11 (GSTR-3B due on 20th of next month)")
    gstr3b_due_date: date
    output_gst_gross: float = Field(..., description="Total GST accrued from issued invoices")
    gst_on_unpaid_invoices: float = Field(..., description="THE DEADLY ACCRUAL TRAP: GST owed on cash not yet received")
    input_tax_credit_booked: float = Field(..., description="Valid ITC from GSTR-2B reconciled suppliers")
    itc_blocked_or_risky: float = Field(default=0.0, description="ITC blocked due to supplier non-filing")
    net_gst_cash_payable: float = Field(..., description="Output GST minus eligible ITC")
    tax_vault_reserved: float = Field(default=0.0, description="Cash physically ring-fenced in Intelligent Tax Vault")
    tax_deficit: float = Field(default=0.0, description="Shortfall between cash payable and tax vault")
    singularity_risk_score: float = Field(..., ge=0.0, le=1.0, description="Probability of working capital freeze")

# --- LIQUIDITY WORMHOLE (THE CROWN JEWEL) ---

class WormholeStep(BaseModel):
    step_number: int
    action_type: Literal[
        "ACCELERATED_DYNAMIC_DISCOUNT", 
        "REVERSE_INVOICE_FACTORING_PAPER", 
        "TAX_VAULT_AUTO_SWEEP", 
        "EMI_BALLOON_RESCHEDULING",
        "SUPPLIER_ITC_RETENTION_OFFSET"
    ]
    target_entity: str
    amount_unlocked: float
    cost_or_haircut: float
    implementation_time_hours: int
    confidence: float
    causal_mechanism: str

class LiquidityWormhole(BaseModel):
    id: str = Field(default_factory=lambda: f"WRM-{uuid.uuid4().hex[:6].upper()}")
    title: str = Field(..., description="e.g. Operation Trident Surge: 3-Way GST Liquidity Bridge")
    singularity_id: str
    steps: List[WormholeStep]
    gross_liquidity_created: float
    total_net_cost: float
    effective_apr_annualized: float
    runway_days_restored: int
    singularity_evasion_probability: float = Field(..., ge=0.0, le=1.0)
    constitutional_clearance: bool = True
    status: Literal["SYNTHESIZED", "APPROVED_BY_HUMAN", "EXECUTED", "REJECTED"] = "SYNTHESIZED"
    explanation_narrative: str
    counterfactual_inaction_damage: str

# --- MONEY PHYSICS & HEALTH GENOME ---

class MoneyPhysicsState(BaseModel):
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    total_rupees_conserved: float = Field(..., description="Strict conservation proof check")
    bank_cash: float
    tax_vault_balance: float
    pending_receivables: float
    locked_working_capital: float
    total_obligations_next_30d: float
    fluid_velocity: float = Field(..., description="Average days for 1 Rupee to complete cycle")
    viscosity_index: float = Field(..., description="Friction ratio due to customer delays [1.0 = smooth, 5.0+ = sluggish]")
    tax_gravity_well: float = Field(..., description="Accrued tax pulling cash toward 20th due date")
    estimated_runway_days: float
    confidence_interval_runway: tuple[float, float] = (0.0, 0.0)

class MoneyHealthGenome(BaseModel):
    overall_score: int = Field(..., ge=0, le=100)
    liquidity_vitality: int = Field(..., ge=0, le=100)
    gst_accrual_shield: int = Field(..., ge=0, le=100)
    customer_payment_velocity: int = Field(..., ge=0, le=100)
    debt_gravity_balance: int = Field(..., ge=0, le=100)
    trajectory: Literal["EVOLVING_THRIVING", "STABLE_BALANCED", "DECAYING_WARNING", "BLACK_HOLE_IMMINENT"]
    genome_markers: Dict[str, str] = Field(default_factory=dict)

# --- COMPLETE CAUSAL FINANCIAL ORGANISM STATE ---

class BusinessProfile(BaseModel):
    id: str
    name: str
    owner_name: str = "Business Owner"
    archetype: str = "General Business"
    tagline: str = "MSME Financial Growth"
    city: str = "Mumbai, Maharashtra"
    gstin: str = "27AAACU1234M1Z5"
    annual_turnover: float = 24000000.0
    employee_count: int = 10
    bank_name: str = "HDFC Bank / State Bank of India"
    overdraft_limit: float = 1000000.0
    monthly_burn_rate: float = 80000.0

class AetherPravahState(BaseModel):
    business: BusinessProfile
    physics_state: MoneyPhysicsState
    genome: MoneyHealthGenome
    invoices: List[Invoice]
    customers: List[Customer]
    suppliers: List[Supplier]
    obligations: List[Obligation]
    gst_snapshot: GSTLiabilitySnapshot
    active_wormholes: List[LiquidityWormhole]
    rupee_packets: List[RupeePacket]
    causal_nodes: List[CausalNode]
    causal_edges: List[CausalEdge]
    system_version: str = "3.8.0-CausalQuantum"
    last_updated: datetime = Field(default_factory=datetime.utcnow)
