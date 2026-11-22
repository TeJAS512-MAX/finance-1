from __future__ import annotations
import os
from datetime import datetime, date
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

from backend.orchestrator.cns import CentralNervousSystem
from backend.causal.simulator import CounterfactualSimulator
from backend.finance import ledger
from backend.finance.calculators import calculate_emi, loan_summary, amortization_by_year, debt_service_verdict, gst_split, profit_model
from backend.finance.forecast import run_forecast, Scenario
from backend.finance.gst_plan import build_gst_plan
from backend.finance.defaults import finance_defaults

app = FastAPI(
    title="AetherPravah - Causal Financial Organism",
    description="The AI that treats your money like a living organism and never lets it die.",
    version="3.8.0-CausalQuantum"
)

# Enable CORS for local dev and embedded frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Instantiate the Singleton Central Nervous System
cns = CentralNervousSystem()
# Initialize with custom user business profile
cns.set_user_profile(
    company_name="Apex Solutions Enterprise",
    owner_name="Business Owner",
    business_type="Trading & Services",
    city="Mumbai, Maharashtra",
    gstin="27AAACU1234M1Z5"
)

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

USERS_DB: Dict[str, Dict[str, Any]] = {
    "demo@aetherpravah.com": {
        "name": "Rajesh Sharma",
        "email": "demo@aetherpravah.com",
        "password": "password123",
        "company_name": "Apex Solutions Enterprise",
        "business_type": "Trading & Services",
        "city": "Mumbai, Maharashtra",
        "gstin": "27AAACU1234M1Z5",
        "bank_cash": 350000.0,
        "tax_vault": 25000.0,
        "monthly_burn": 80000.0
    }
}

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

class ArchetypeRequest(BaseModel):
    archetype: str

@app.get("/api/health")
def health_check():
    return {
        "status": "ONLINE",
        "system": "AetherPravah Causal Organism",
        "rupees_conserved": cns.state.physics_state.total_rupees_conserved,
        "genome_score": cns.state.genome.overall_score
    }

@app.post("/api/auth/login")
def auth_login(req: LoginRequest):
    email = req.email.strip().lower()
    user = USERS_DB.get(email)
    
    if not user:
        if email in ["demo", "guest", "admin"] or "demo" in email:
            user = USERS_DB["demo@aetherpravah.com"]
        elif req.password:
            name_part = email.split("@")[0].replace(".", " ").replace("_", " ").title()
            user = {
                "name": name_part,
                "email": email,
                "password": req.password,
                "company_name": f"{name_part} Enterprises",
                "business_type": "Trading & Services",
                "city": "Mumbai, Maharashtra",
                "gstin": "27AAACU1234M1Z5",
                "bank_cash": 350000.0,
                "tax_vault": 25000.0,
                "monthly_burn": 80000.0
            }
            USERS_DB[email] = user
        else:
            raise HTTPException(status_code=401, detail="Invalid credentials. Please enter email and password.")

    cns.set_user_profile(
        company_name=user["company_name"],
        owner_name=user["name"],
        business_type=user.get("business_type", "Trading & Services"),
        city=user.get("city", "Mumbai, Maharashtra"),
        gstin=user.get("gstin", "27AAACU1234M1Z5"),
        bank_cash=user.get("bank_cash"),
        tax_vault=user.get("tax_vault"),
        monthly_burn=user.get("monthly_burn")
    )

    token = f"tok_{abs(hash(email))}_{int(datetime.now().timestamp())}"
    return {
        "status": "AUTHENTICATED",
        "token": token,
        "user": {
            "name": user["name"],
            "email": user["email"],
            "company_name": user["company_name"],
            "business_type": user.get("business_type", "Trading & Services"),
            "city": user.get("city", "Mumbai, Maharashtra"),
            "gstin": user.get("gstin", "27AAACU1234M1Z5")
        },
        "state": cns.state.model_dump()
    }

@app.post("/api/auth/register")
def auth_register(req: RegisterRequest):
    email = req.email.strip().lower()
    user = {
        "name": req.name.strip(),
        "email": email,
        "password": req.password,
        "company_name": req.company_name.strip(),
        "business_type": req.business_type,
        "city": req.city,
        "gstin": req.gstin.strip().upper(),
        "bank_cash": float(req.bank_cash),
        "tax_vault": float(req.tax_vault),
        "monthly_burn": float(req.monthly_burn)
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
        monthly_burn=user["monthly_burn"]
    )

    token = f"tok_{abs(hash(email))}_{int(datetime.now().timestamp())}"
    return {
        "status": "REGISTERED",
        "token": token,
        "user": {
            "name": user["name"],
            "email": user["email"],
            "company_name": user["company_name"],
            "business_type": user["business_type"],
            "city": user["city"],
            "gstin": user["gstin"]
        },
        "state": cns.state.model_dump()
    }

@app.get("/api/auth/me")
def auth_me():
    return {
        "authenticated": True,
        "user": {
            "name": cns.state.business.owner_name,
            "company_name": cns.state.business.name,
            "city": cns.state.business.city,
            "gstin": cns.state.business.gstin
        }
    }

@app.get("/api/profile")
def get_profile():
    return {
        "business": cns.state.business.model_dump(),
        "bank_cash": cns.state.physics_state.bank_cash,
        "tax_vault": cns.state.physics_state.tax_vault_balance,
        "runway": cns.state.physics_state.estimated_runway_days
    }

@app.post("/api/profile")
def update_profile(req: ProfileRequest):
    new_state = cns.set_user_profile(
        company_name=req.company_name,
        owner_name=req.owner_name,
        business_type=req.business_type,
        city=req.city,
        gstin=req.gstin,
        bank_cash=req.bank_cash,
        tax_vault=req.tax_vault,
        monthly_burn=req.monthly_burn
    )
    return {
        "status": "PROFILE_SAVED",
        "state": new_state.model_dump(),
        "singularity": cns.predict_current_singularity().model_dump()
    }

@app.post("/api/profile/reset")
def reset_profile_endpoint():
    new_state = cns.reset_user_business()
    return {
        "status": "RESET_SUCCESS",
        "state": new_state.model_dump(),
        "singularity": cns.predict_current_singularity().model_dump()
    }

@app.post("/api/transaction/invoice")
def create_invoice_endpoint(req: InvoiceCreateRequest):
    inv = cns.add_custom_invoice(req.customer_name, req.base_amount, req.gst_rate, req.due_days)
    return {
        "status": "INVOICE_CREATED",
        "invoice": inv.model_dump(),
        "state": cns.state.model_dump()
    }

@app.post("/api/transaction/expense")
def create_expense_endpoint(req: ExpenseCreateRequest):
    obl = cns.add_custom_obligation(req.name, req.amount, req.due_days, req.category)
    return {
        "status": "EXPENSE_CREATED",
        "obligation": obl.model_dump(),
        "state": cns.state.model_dump()
    }

@app.post("/api/transaction/payment")
def record_payment_endpoint(req: PaymentRecordRequest):
    res = cns.record_customer_payment(req.customer_name, req.amount)
    return {
        "status": "PAYMENT_RECORDED",
        "details": res,
        "state": cns.state.model_dump()
    }

@app.get("/api/state")
def get_organism_state():
    cns.sync_graph()
    singularity = cns.predict_current_singularity()
    return {
        "state": cns.state.model_dump(),
        "singularity": singularity.model_dump(),
        "graph": cns.graph.export_graph_visualization()
    }

@app.post("/api/archetype/{archetype_id}")
def switch_archetype(archetype_id: str):
    new_state = cns.set_archetype(archetype_id)
    singularity = cns.predict_current_singularity()
    return {
        "status": "SWITCHED",
        "state": new_state.model_dump(),
        "singularity": singularity.model_dump(),
        "graph": cns.graph.export_graph_visualization()
    }

@app.post("/api/chat")
def handle_chat(req: ChatRequest):
    response_payload = cns.process_user_message(req.message)
    return response_payload

@app.post("/api/upload-invoice")
async def upload_invoice(file: UploadFile = File(...)):
    contents = await file.read()
    response_payload = cns.process_user_message(
        message=f"Uploaded invoice document {file.filename}",
        attached_image_filename=file.filename
    )
    return response_payload

@app.post("/api/wormhole/activate")
def activate_wormhole():
    response_payload = cns.process_user_message("activate wormhole")
    return response_payload

@app.get("/api/wormholes/candidates")
def get_wormhole_candidates():
    singularity = cns.predict_current_singularity()
    from backend.causal.wormhole_forger import LiquidityWormholeForger
    candidates = LiquidityWormholeForger.forge_candidate_wormholes(
        current_date=cns.current_date,
        singularity=singularity,
        bank_cash=cns.state.physics_state.bank_cash,
        tax_vault_balance=cns.state.physics_state.tax_vault_balance,
        invoices=cns.state.invoices,
        customers=cns.state.customers,
        obligations=cns.state.obligations,
        gst_snapshot=cns.state.gst_snapshot
    )
    return {"candidates": [c.model_dump() for c in candidates]}

@app.post("/api/simulate-delay")
def simulate_customer_delay():
    response_payload = cns.process_user_message("simulate customer delay")
    return response_payload

@app.get("/api/counterfactual")
def get_counterfactual_simulation():
    active_w = cns.state.active_wormholes[0] if cns.state.active_wormholes else None
    burn = 240000.0 if cns.state.business.archetype == "STEEL_TRADER" else 180000.0
    sim = CounterfactualSimulator.simulate_trajectories(
        current_date=cns.current_date,
        bank_cash=cns.state.physics_state.bank_cash,
        tax_vault=cns.state.physics_state.tax_vault_balance,
        invoices=cns.state.invoices,
        obligations=cns.state.obligations,
        gst_snapshot=cns.state.gst_snapshot,
        monthly_burn=burn,
        wormhole=active_w,
        days_ahead=40,
        num_simulations=100
    )
    return sim

@app.get("/api/meta-evolution")
def get_meta_evolution():
    return {
        "mutations": cns.meta_evolution.get_evolution_summary(),
        "learning_rate": "Dynamic Bayesian Adaption",
        "conformal_calibration_coverage": 0.94
    }

@app.get("/api/forecast")
def get_cash_forecast(
    horizon: int = 45,
    delay: int = 0,
    discount: float = 0.0,
    cost_cut: float = 0.0,
    spend: float = 0.0,
    spend_day: int = 0
):
    scen = Scenario(
        horizon=horizon,
        delay_days=delay,
        prompt_discount_pct=discount,
        cost_cut_pct=cost_cut,
        planned_spend=spend,
        spend_day=spend_day
    )
    return run_forecast(cns.state, cns.current_date, scen)

@app.get("/api/gst-plan")
def get_gst_plan():
    return build_gst_plan(cns.state, cns.current_date)

@app.get("/api/ledger")
def get_financial_ledger():
    return {
        "receivables": ledger.receivables_view(cns.state, cns.current_date),
        "payables": ledger.payables_view(cns.state, cns.current_date)
    }

class ReminderRequest(BaseModel):
    invoice_id: str

@app.post("/api/reminder")
def generate_reminder_for_invoice(req: ReminderRequest):
    inv = next((i for i in cns.state.invoices if i.id == req.invoice_id), None)
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")
    days_overdue = max(0, (cns.current_date - inv.due_date).days)
    draft = ledger.generate_reminder_draft(inv.invoice_number, inv.customer_name, float(inv.unpaid_cash), days_overdue, inv.due_date)
    return {"reminder": draft}

@app.get("/api/defaults")
def get_defaults():
    return finance_defaults(cns.state.business.archetype)

@app.get("/api/emi")
def get_emi_calc(principal: float = 1000000.0, rate: float = 11.0, months: int = 60):
    summary = loan_summary(principal, rate, months)
    amort = amortization_by_year(principal, rate, months)
    defs = finance_defaults(cns.state.business.archetype)
    p_data = defs["profit"]
    pm = profit_model(p_data["monthly_sales"], p_data["cogs_pct"], p_data["running_costs"], p_data["emis"])
    verdict = debt_service_verdict(p_data["emis"] + summary["emi"], pm["operating_profit"])
    return {
        "loan": summary,
        "by_year": amort,
        "debt_service": verdict
    }

@app.get("/api/gst-calc")
def get_gst_calc(amount: float = 100000.0, rate: float = 18.0, inclusive: bool = True):
    return gst_split(amount, rate, inclusive)

@app.get("/api/profit-model")
def get_profit_calc(monthly_sales: float = 7000000.0, cogs_pct: float = 90.0, running_costs: float = 152000.0, emis: float = 88000.0):
    return profit_model(monthly_sales, cogs_pct, running_costs, emis)

# Mount static frontend build
base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
static_dir = os.path.join(base_dir, "static")
if os.path.exists(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.api.server:app", host="0.0.0.0", port=8000, reload=True)
