from __future__ import annotations

from finance.agents.supreme_court import ConstitutionalSupremeCourt
from finance.causal.wormhole_forger import LiquidityWormholeForger
from finance.cns import CentralNervousSystem
from finance.physics.engine import MoneyPhysicsEngine


def test_money_conservation():
    cns = CentralNervousSystem()
    state = cns.state
    is_conserved, conserved_total, disc = MoneyPhysicsEngine.verify_conservation(
        state.physics_state.bank_cash,
        state.physics_state.tax_vault_balance,
        state.physics_state.pending_receivables,
        0.0,
        state.rupee_packets,
    )
    assert is_conserved, f"Rupee conservation discrepancy: {disc}"
    assert conserved_total > 0


def test_gst_accrual_singularity_detection():
    cns = CentralNervousSystem()
    singularity = cns.predict_current_singularity()
    assert singularity.is_singularity_imminent
    assert singularity.singularity_depth >= 150000.0
    assert singularity.tax_vault_deficit >= 240000.0
    assert singularity.severity == "CRITICAL"


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
        gst_snapshot=cns.state.gst_snapshot,
    )
    assert wormhole is not None
    assert wormhole.gross_liquidity_created >= singularity.singularity_depth

    sc_res = ConstitutionalSupremeCourt.verify(wormhole, cns.state.physics_state)
    assert sc_res.is_cleared
    assert sc_res.symbolic_math_valid


def test_full_conversational_workflow():
    cns = CentralNervousSystem()
    res1 = cns.process_user_message("How is my money?")
    assert "plain_language_summary" in res1
    assert "exact_numbers" in res1
    assert "causal_explanation" in res1
    assert "top_recommended_actions" in res1
    assert "what_if_ignore" in res1

    res2 = cns.process_user_message("Create invoice for Reliance 2.5 lakh")
    assert res2["singularity"]["gst_accrual_trap_component"] > 0

    res3 = cns.process_user_message("activate wormhole")
    assert res3["state"]["genome"]["overall_score"] > 60
    assert res3["state"]["physics_state"]["bank_cash"] > 250000.0
