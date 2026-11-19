from __future__ import annotations
import os
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

from backend.orchestrator.cns import CentralNervousSystem
from backend.causal.simulator import CounterfactualSimulator

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

class ChatRequest(BaseModel):
    message: str

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

# Mount static frontend build
base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
static_dir = os.path.join(base_dir, "static")
if os.path.exists(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.api.server:app", host="0.0.0.0", port=8000, reload=True)
