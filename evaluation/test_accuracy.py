from __future__ import annotations
import pytest
from datetime import date
from backend.orchestrator.cns import CentralNervousSystem
from backend.physics.engine import MoneyPhysicsEngine
from backend.physics.singularity import GSTSingularityPredictor
from backend.causal.wormhole_forger import LiquidityWormholeForger
from backend.agents.supreme_court import ConstitutionalSupremeCourt

def test_money_conservation():
    cns = CentralNervousSystem()
    state = cns.state
    # Check conservation
    is_conserved, conserved_total, disc = MoneyPhysicsEngine.verify_conservation(
        state.physics_state.bank_cash,
        state.physics_state.tax_vault_balance,
        state.physics_state.pending_receivables,
        0.0,
        state.rupee_packets
    )
    assert is_conserved, f"Rupee conservation discrepancy: {disc}"
    print(f"✅ Money Conservation verified: Total ₹{conserved_total:,.2f} conserved with zero leakage.")

def test_gst_accrual_singularity_detection():
    cns = CentralNervousSystem()
    singularity = cns.predict_current_singularity()
    assert singularity.is_singularity_imminent, "Bharat Steel should have an imminent singularity on Nov 20!"
    assert singularity.singularity_depth >= 150000.0, f"Expected >= ₹1.5L deficit, got {singularity.singularity_depth}"
    assert singularity.tax_vault_deficit >= 240000.0, f"Expected >= ₹2.4L tax deficit, got {singularity.tax_vault_deficit}"
    assert singularity.severity == "CRITICAL"
    print(f"✅ GST Singularity detected: Event Horizon {singularity.event_horizon_date}, Depth: ₹{singularity.singularity_depth:,.2f}")

def test_wormhole_synthesis_and_execution():
    cns = CentralNervousSystem()
    singularity = cns.predict_current_singularity()
    wormhole = LiquidityWormholeForger.forge_wormhole(
        current_date=cns.current_date,
        singularity=singularity,
        bank_cash=cns.state.physics_state.bank_cash,
        tax_vault_balance=cns.state.physics_state.tax_vault_balance,
        invoices=cns.state.invoices,
        customers=cns.state.customers,
        obligations=cns.state.obligations,
        gst_snapshot=cns.state.gst_snapshot
    )
    assert wormhole is not None, "Wormhole should be synthesized!"
    assert wormhole.gross_liquidity_created >= singularity.singularity_depth
    print(f"✅ Wormhole Synthesized: {wormhole.title}, Cash Liberated: ₹{wormhole.gross_liquidity_created:,.2f}")

    # Supreme court clearance
    sc_res = ConstitutionalSupremeCourt.verify(wormhole, cns.state.physics_state)
    assert sc_res.is_cleared
    assert sc_res.symbolic_math_valid
    print(f"✅ Supreme Court formally verified: {sc_res.constitutional_verdict}")

def test_full_conversational_workflow():
    cns = CentralNervousSystem()
    # 1. Health check
    res1 = cns.process_user_message("How is my money?")
    assert "plain_language_summary" in res1
    assert "exact_numbers" in res1
    assert "causal_explanation" in res1
    assert "top_recommended_actions" in res1
    assert "what_if_ignore" in res1
    print("✅ Chat 5-element format verified for 'How is my money?'")

    # 2. Create invoice
    res2 = cns.process_user_message("Create invoice for Reliance 2.5 lakh")
    assert res2["singularity"]["gst_accrual_trap_component"] > 0
    print("✅ InvoiceForge parsed and deepened GST Accrual Singularity as expected.")

    # 3. Activate wormhole
    res3 = cns.process_user_message("activate wormhole")
    assert res3["state"]["genome"]["overall_score"] > 60
    assert res3["state"]["physics_state"]["bank_cash"] > 250000.0
    print(f"✅ Wormhole executed: New Genome Score {res3['state']['genome']['overall_score']}/100, Bank cash ₹{res3['state']['physics_state']['bank_cash']:,.2f}")

if __name__ == "__main__":
    test_money_conservation()
    test_gst_accrual_singularity_detection()
    test_wormhole_synthesis_and_execution()
    test_full_conversational_workflow()
    print("\n🎉 ALL MATHEMATICAL & CAUSAL ARCHITECTURE TESTS PASSED WITH 100% ACCURACY!")
