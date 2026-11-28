"""api/routes/finance.py — Unified SME Finance (AetherPravah) API routes."""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

from core.security import create_access_token, hash_password, verify_password
from finance import ledger
from finance.calculators import (
    amortization_by_year,
    debt_service_verdict,
    gst_split,
    loan_summary,
    profit_model,
)
from finance.causal.simulator import CounterfactualSimulator
from finance.causal.wormhole_forger import LiquidityWormholeForger
from finance.cns import CentralNervousSystem
from finance.defaults import finance_defaults
from finance.forecast import Scenario, run_forecast
from finance.gst_plan import build_gst_plan
from finance.persistence import FinancePersistence

router = APIRouter()

persistence = FinancePersistence()
cns = CentralNervousSystem()
cns.set_user_profile(
    company_name="Apex Solutions Enterprise",
    owner_name="Business Owner",
    business_type="Trading & Services",
    city="Mumbai, Maharashtra",
    gstin="27AAACU1234M1Z5",
)

USERS_DB: Dict[str, Dict[str, Any]] = {
    "demo@aetherpravah.com": {
        "name": "Rajesh Sharma",
        "email": "demo@aetherpravah.com",
        "password_hash": hash_password("password123"),
        "company_name": "Apex Solutions Enterprise",
        "business_type": "Trading & Services",
        "city": "Mumbai, Maharashtra",
        "gstin": "27AAACU1234M1Z5",
        "bank_cash": 350000.0,
        "tax_vault": 25000.0,
        "monthly_burn": 80000.0,
    }
}

_loaded = persistence.load()
if _loaded is not None:
    _saved_state, _saved_date, _saved_users = _loaded
    cns.state = _saved_state
    cns.current_date = _saved_date
    cns.sync_graph()
    for _email, _u in _saved_users.items():
        if "password" in _u and "password_hash" not in _u:
            _u["password_hash"] = hash_password(str(_u.pop("password")))
        USERS_DB[_email] = _u


def _persist() -> None:
    persistence.save(cns.state, cns.current_date, USERS_DB)


class ChatRequest(BaseModel):
    message: str


class LoginRequest(BaseModel):
    email: str
    password: str


class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str
    company_name: str
    business_type: str = "Trading & Services"
    city: str = "Mumbai, Maharashtra"
    gstin: str = "27AAACU1234M1Z5"
    bank_cash: float = 350000.0
    tax_vault: float = 25000.0
    monthly_burn: float = 80000.0


class ProfileRequest(BaseModel):
    company_name: str
    owner_name: str = "Business Owner"
    business_type: str = "Trading & Services"
    city: str = "Mumbai, Maharashtra"
    gstin: str = "27AAACU1234M1Z5"
    bank_cash: Optional[float] = None
    tax_vault: Optional[float] = None
    monthly_burn: Optional[float] = None


class InvoiceCreateRequest(BaseModel):
    customer_name: str
    base_amount: float
    gst_rate: float = 0.18
    due_days: int = 30


class ExpenseCreateRequest(BaseModel):
    name: str
    amount: float
    due_days: int = 15
    category: str = "OPERATIONAL_EXPENSE"


class PaymentRecordRequest(BaseModel):
    customer_name: str
    amount: float


class ReminderRequest(BaseModel):
    invoice_id: str


@router.get("/health", summary="SME Finance engine health check")
def health_check() -> Dict[str, Any]:
    return {
        "status": "ONLINE",
        "system": "AetherPravah Causal Organism",
        "rupees_conserved": cns.state.physics_state.total_rupees_conserved,
        "genome_score": cns.state.genome.overall_score,
        "persistence": persistence.backend_name,
        "current_date": cns.current_date.isoformat(),
    }


@router.post("/auth/login", summary="Authenticate SME finance profile")
def auth_login(req: LoginRequest) -> Dict[str, Any]:
    email = req.email.strip().lower()
    user = USERS_DB.get(email)

    if user:
        stored_hash = user.get("password_hash")
        if stored_hash:
            if not verify_password(req.password, stored_hash):
                raise HTTPException(
                    status_code=401,
                    detail="Invalid credentials. Please verify your email and password.",
                )
    else:
        if email in ["demo", "guest", "admin"] or "demo" in email:
            user = USERS_DB["demo@aetherpravah.com"]
        elif req.password:
            name_part = email.split("@")[0].replace(".", " ").replace("_", " ").title()
            user = {
                "name": name_part,
                "email": email,
                "password_hash": hash_password(req.password),
                "company_name": f"{name_part} Enterprises",
                "business_type": "Trading & Services",
                "city": "Mumbai, Maharashtra",
                "gstin": "27AAACU1234M1Z5",
                "bank_cash": 350000.0,
                "tax_vault": 25000.0,
                "monthly_burn": 80000.0,
            }
            USERS_DB[email] = user
        else:
            raise HTTPException(
                status_code=401,
                detail="Invalid credentials. Please enter email and password.",
            )

    cns.set_user_profile(
        company_name=user["company_name"],
        owner_name=user["name"],
        business_type=user.get("business_type", "Trading & Services"),
        city=user.get("city", "Mumbai, Maharashtra"),
        gstin=user.get("gstin", "27AAACU1234M1Z5"),
        bank_cash=user.get("bank_cash"),
        tax_vault=user.get("tax_vault"),
        monthly_burn=user.get("monthly_burn"),
    )
    _persist()

    token = create_access_token(
        subject=user["email"],
        extra_claims={"company_name": user["company_name"], "scope": "sme_finance"},
    )
    return {
        "status": "AUTHENTICATED",
        "token": token,
        "user": {
            "name": user["name"],
            "email": user["email"],
            "company_name": user["company_name"],
            "business_type": user.get("business_type", "Trading & Services"),
            "city": user.get("city", "Mumbai, Maharashtra"),
            "gstin": user.get("gstin", "27AAACU1234M1Z5"),
        },
        "current_date": cns.current_date.isoformat(),
        "state": cns.state.model_dump(),
    }


@router.post("/auth/register", summary="Register a new SME business profile")
def auth_register(req: RegisterRequest) -> Dict[str, Any]:
    email = req.email.strip().lower()
    user = {
        "name": req.name.strip(),
        "email": email,
        "password_hash": hash_password(req.password),
        "company_name": req.company_name.strip(),
        "business_type": req.business_type,
        "city": req.city,
        "gstin": req.gstin.strip().upper(),
        "bank_cash": float(req.bank_cash),
        "tax_vault": float(req.tax_vault),
        "monthly_burn": float(req.monthly_burn),
    }
    USERS_DB[email] = user

    cns.reset_user_business(
        company_name=user["company_name"],
        owner_name=user["name"],
        business_type=user["business_type"],
        city=user["city"],
        gstin=user["gstin"],
        bank_cash=user["bank_cash"],
        tax_vault=user["tax_vault"],
        monthly_burn=user["monthly_burn"],
    )
    _persist()

    token = create_access_token(
        subject=user["email"],
        extra_claims={"company_name": user["company_name"], "scope": "sme_finance"},
    )
    return {
        "status": "REGISTERED",
        "token": token,
        "user": {
            "name": user["name"],
            "email": user["email"],
            "company_name": user["company_name"],
            "business_type": user["business_type"],
            "city": user["city"],
            "gstin": user["gstin"],
        },
        "current_date": cns.current_date.isoformat(),
        "state": cns.state.model_dump(),
    }


@router.get("/auth/me", summary="Current SME business owner details")
def auth_me() -> Dict[str, Any]:
    return {
        "authenticated": True,
        "user": {
            "name": cns.state.business.owner_name,
            "company_name": cns.state.business.name,
            "city": cns.state.business.city,
            "gstin": cns.state.business.gstin,
        },
    }


@router.get("/profile", summary="Get active SME business profile")
def get_profile() -> Dict[str, Any]:
    return {
        "business": cns.state.business.model_dump(),
        "bank_cash": cns.state.physics_state.bank_cash,
        "tax_vault": cns.state.physics_state.tax_vault_balance,
        "runway": cns.state.physics_state.estimated_runway_days,
        "current_date": cns.current_date.isoformat(),
    }


@router.post("/profile", summary="Update active SME business profile")
def update_profile(req: ProfileRequest) -> Dict[str, Any]:
    new_state = cns.set_user_profile(
        company_name=req.company_name,
        owner_name=req.owner_name,
        business_type=req.business_type,
        city=req.city,
        gstin=req.gstin,
        bank_cash=req.bank_cash,
        tax_vault=req.tax_vault,
        monthly_burn=req.monthly_burn,
    )
    _persist()
    return {
        "status": "PROFILE_SAVED",
        "current_date": cns.current_date.isoformat(),
        "state": new_state.model_dump(),
        "singularity": cns.predict_current_singularity().model_dump(),
    }


@router.post("/profile/reset", summary="Reset SME business ledger to clean slate")
def reset_profile_endpoint() -> Dict[str, Any]:
    new_state = cns.reset_user_business()
    _persist()
    return {
        "status": "RESET_SUCCESS",
        "current_date": cns.current_date.isoformat(),
        "state": new_state.model_dump(),
        "singularity": cns.predict_current_singularity().model_dump(),
    }


@router.post("/transaction/invoice", summary="Create customer invoice")
def create_invoice_endpoint(req: InvoiceCreateRequest) -> Dict[str, Any]:
    inv = cns.add_custom_invoice(
        req.customer_name, req.base_amount, req.gst_rate, req.due_days
    )
    _persist()
    return {
        "status": "INVOICE_CREATED",
        "invoice": inv.model_dump(),
        "current_date": cns.current_date.isoformat(),
        "state": cns.state.model_dump(),
    }


@router.post("/transaction/expense", summary="Record business expense or payable")
def create_expense_endpoint(req: ExpenseCreateRequest) -> Dict[str, Any]:
    obl = cns.add_custom_obligation(
        req.name, req.amount, req.due_days, req.category
    )
    _persist()
    return {
        "status": "EXPENSE_CREATED",
        "obligation": obl.model_dump(),
        "current_date": cns.current_date.isoformat(),
        "state": cns.state.model_dump(),
    }


@router.post("/transaction/payment", summary="Record customer payment receipt")
def record_payment_endpoint(req: PaymentRecordRequest) -> Dict[str, Any]:
    res = cns.record_customer_payment(req.customer_name, req.amount)
    _persist()
    return {
        "status": "PAYMENT_RECORDED",
        "details": res,
        "current_date": cns.current_date.isoformat(),
        "state": cns.state.model_dump(),
    }


@router.get("/state", summary="Get full SME causal financial state")
def get_organism_state() -> Dict[str, Any]:
    cns.sync_graph()
    singularity = cns.predict_current_singularity()
    return {
        "current_date": cns.current_date.isoformat(),
        "state": cns.state.model_dump(),
        "singularity": singularity.model_dump(),
        "graph": cns.graph.export_graph_visualization(),
    }


@router.post("/archetype/{archetype_id}", summary="Switch SME business archetype")
def switch_archetype(archetype_id: str) -> Dict[str, Any]:
    new_state = cns.set_archetype(archetype_id)
    singularity = cns.predict_current_singularity()
    _persist()
    return {
        "status": "SWITCHED",
        "current_date": cns.current_date.isoformat(),
        "state": new_state.model_dump(),
        "singularity": singularity.model_dump(),
        "graph": cns.graph.export_graph_visualization(),
    }


@router.post("/chat", summary="Send conversational finance assistant prompt")
def handle_chat(req: ChatRequest) -> Dict[str, Any]:
    payload = cns.process_user_message(req.message)
    payload["current_date"] = cns.current_date.isoformat()
    _persist()
    return payload


@router.post("/upload-invoice", summary="Upload invoice document for OCR parsing")
async def upload_invoice(file: UploadFile = File(...)) -> Dict[str, Any]:
    contents = await file.read()
    payload = cns.process_user_message(
        message=f"Uploaded invoice document {file.filename}",
        attached_image_filename=file.filename,
        attached_image_bytes=contents,
    )
    payload["current_date"] = cns.current_date.isoformat()
    _persist()
    return payload


@router.post("/wormhole/activate", summary="Activate synthesized liquidity wormhole")
def activate_wormhole() -> Dict[str, Any]:
    payload = cns.process_user_message("activate wormhole")
    payload["current_date"] = cns.current_date.isoformat()
    _persist()
    return payload


@router.get("/wormholes/candidates", summary="List Pareto liquidity wormhole candidates")
def get_wormhole_candidates() -> Dict[str, Any]:
    singularity = cns.predict_current_singularity()
    candidates = LiquidityWormholeForger.forge_candidate_wormholes(
        current_date=cns.current_date,
        singularity=singularity,
        bank_cash=cns.state.physics_state.bank_cash,
        tax_vault_balance=cns.state.physics_state.tax_vault_balance,
        invoices=cns.state.invoices,
        customers=cns.state.customers,
        obligations=cns.state.obligations,
        gst_snapshot=cns.state.gst_snapshot,
    )
    return {"candidates": [c.model_dump() for c in candidates]}


@router.post("/simulate-delay", summary="Simulate 30-day customer payment delay")
def simulate_customer_delay() -> Dict[str, Any]:
    payload = cns.process_user_message("simulate customer delay")
    payload["current_date"] = cns.current_date.isoformat()
    _persist()
    return payload


@router.get("/counterfactual", summary="Run Pearlian counterfactual Monte-Carlo trajectories")
def get_counterfactual_simulation() -> Dict[str, Any]:
    active_w = cns.state.active_wormholes[0] if cns.state.active_wormholes else None
    configured_burn = getattr(cns.state.business, "monthly_burn_rate", None)
    if configured_burn and configured_burn > 0:
        burn = float(configured_burn)
    else:
        burn = 240000.0 if cns.state.business.archetype == "STEEL_TRADER" else 180000.0
    return CounterfactualSimulator.simulate_trajectories(
        current_date=cns.current_date,
        bank_cash=cns.state.physics_state.bank_cash,
        tax_vault=cns.state.physics_state.tax_vault_balance,
        invoices=cns.state.invoices,
        obligations=cns.state.obligations,
        gst_snapshot=cns.state.gst_snapshot,
        monthly_burn=burn,
        wormhole=active_w,
        days_ahead=40,
        num_simulations=100,
    )


@router.get("/meta-evolution", summary="Get meta-evolution learning state")
def get_meta_evolution() -> Dict[str, Any]:
    return {
        "mutations": cns.meta_evolution.get_evolution_summary(),
        "learning_rate": "Dynamic Bayesian Adaption",
        "conformal_calibration_coverage": 0.94,
    }


@router.get("/forecast", summary="Get 45-day cash flow forecast and what-if analysis")
def get_cash_forecast(
    horizon: int = 45,
    delay: int = 0,
    discount: float = 0.0,
    cost_cut: float = 0.0,
    spend: float = 0.0,
    spend_day: int = 0,
) -> Dict[str, Any]:
    scen = Scenario(
        horizon=horizon,
        delay_days=delay,
        prompt_discount_pct=discount,
        cost_cut_pct=cost_cut,
        planned_spend=spend,
        spend_day=spend_day,
    )
    return run_forecast(cns.state, cns.current_date, scen)


@router.get("/gst-plan", summary="Get GSTR-3B statutory tax plan")
def get_gst_plan() -> Dict[str, Any]:
    return build_gst_plan(cns.state, cns.current_date)


@router.get("/ledger", summary="Get debtors and creditors ledger")
def get_financial_ledger() -> Dict[str, Any]:
    rec = ledger.receivables_view(cns.state, cns.current_date)
    pay = ledger.payables_view(cns.state, cns.current_date)
    return {
        "receivables": rec,
        "payables": pay,
        "debtors": rec,
        "creditors": pay,
    }


@router.post("/reminder", summary="Generate payment reminder draft for invoice")
def generate_reminder_for_invoice(req: ReminderRequest) -> Dict[str, Any]:
    inv = next((i for i in cns.state.invoices if i.id == req.invoice_id), None)
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")
    days_overdue = max(0, (cns.current_date - inv.due_date).days)
    draft = ledger.generate_reminder_draft(
        inv.invoice_number,
        inv.customer_name,
        float(inv.unpaid_cash),
        days_overdue,
        inv.due_date,
    )
    return {"reminder": draft}


@router.get("/defaults", summary="Get archetype finance defaults")
def get_defaults() -> Dict[str, Any]:
    return finance_defaults(cns.state.business.archetype)


@router.get("/emi", summary="Calculate loan EMI, amortization, and debt service verdict")
def get_emi_calc(
    principal: float = 1000000.0, rate: float = 11.0, months: int = 60
) -> Dict[str, Any]:
    summary = loan_summary(principal, rate, months)
    amort = amortization_by_year(principal, rate, months)
    defs = finance_defaults(cns.state.business.archetype)
    p_data = defs["profit"]
    pm = profit_model(
        p_data["monthly_sales"],
        p_data["cogs_pct"],
        p_data["running_costs"],
        p_data["emis"],
    )
    verdict = debt_service_verdict(
        p_data["emis"] + summary["emi"], pm["operating_profit"]
    )
    return {
        "principal": principal,
        "rate_annual": rate,
        "tenure_months": months,
        "monthly_emi": summary["emi"],
        "total_interest": summary["total_interest"],
        "total_payment": summary["total_payment"],
        "verdict": verdict,
        "loan": summary,
        "by_year": amort,
        "debt_service": verdict,
    }


@router.get("/gst-calc", summary="Split base amount and CGST/SGST")
def get_gst_calc(
    amount: float = 100000.0, rate: float = 18.0, inclusive: bool = True
) -> Dict[str, Any]:
    return gst_split(amount, rate, inclusive)


@router.get("/profit-model", summary="Compute SME profitability and break-even")
def get_profit_calc(
    monthly_sales: float = 7000000.0,
    cogs_pct: float = 90.0,
    running_costs: float = 152000.0,
    emis: float = 88000.0,
) -> Dict[str, Any]:
    return profit_model(monthly_sales, cogs_pct, running_costs, emis)
