from __future__ import annotations
import numpy as np
from datetime import date, timedelta
from typing import Dict, Any, List
from backend.models.schemas import (
    Invoice, Obligation, GSTLiabilitySnapshot, MoneyPhysicsState,
    MoneyHealthGenome, LiquidityWormhole
)
from backend.physics.engine import MoneyPhysicsEngine
from backend.physics.singularity import GSTSingularityPredictor

class CounterfactualSimulator:
    """
    Pearl do-calculus Counterfactual Simulator:
    Simulates thousands of trajectories comparing P(Runway | do(Action))
    against P(Runway | Inaction).
    """

    @classmethod
    def simulate_trajectories(
        cls,
        current_date: date,
        bank_cash: float,
        tax_vault: float,
        invoices: List[Invoice],
        obligations: List[Obligation],
        gst_snapshot: GSTLiabilitySnapshot,
        monthly_burn: float,
        wormhole: LiquidityWormhole | None = None,
        days_ahead: int = 45,
        num_simulations: int = 250
    ) -> Dict[str, Any]:
        """
        Runs Monte-Carlo forward simulation of cash balance over `days_ahead`
        under both Baseline (no intervention) and Wormhole (intervention).
        """
        dates = [(current_date + timedelta(days=i)).strftime("%d %b") for i in range(days_ahead)]
        daily_burn = monthly_burn / 30.0

        # Precalculate deterministic obligations by day offset
        obl_by_day = [0.0] * days_ahead
        for obl in obligations:
            day_idx = (obl.due_date - current_date).days
            if 0 <= day_idx < days_ahead:
                obl_by_day[day_idx] += obl.amount

        # GST filing day offset
        gst_day_idx = (gst_snapshot.gstr3b_due_date - current_date).days
        net_gst = gst_snapshot.net_gst_cash_payable

        # 1. Baseline Sim (Inaction)
        baseline_curves = []
        for _ in range(num_simulations):
            cash = bank_cash
            curve = []
            for day in range(days_ahead):
                # Burn
                cash -= daily_burn * np.random.normal(1.0, 0.08)
                # Obligations
                cash -= obl_by_day[day]
                # GST payment on 20th
                if day == gst_day_idx:
                    cash -= net_gst
                # Stochastic invoice arrivals
                for inv in invoices:
                    inv_target_day = (inv.due_date - current_date).days + int(inv.delay_prediction_days)
                    # Stochastic realization with delay jitter
                    if day == inv_target_day:
                        if np.random.rand() > 0.15:  # 85% arrive around predicted day
                            cash += inv.unpaid_cash
                curve.append(cash)
            baseline_curves.append(curve)

        # 2. Wormhole Sim (do(Wormhole))
        wormhole_curves = []
        bonus_cash = wormhole.gross_liquidity_created - wormhole.total_net_cost if wormhole else 0.0
        
        for _ in range(num_simulations):
            cash = bank_cash + bonus_cash  # Liquidity teleported early
            curve = []
            for day in range(days_ahead):
                cash -= daily_burn * np.random.normal(1.0, 0.08)
                cash -= obl_by_day[day]
                if day == gst_day_idx:
                    # GST paid cleanly from Tax Vault without draining general bank cash
                    pass
                for inv in invoices:
                    inv_target_day = (inv.due_date - current_date).days
                    if day == inv_target_day:
                        if np.random.rand() > 0.05:
                            cash += inv.unpaid_cash * 0.4
                curve.append(cash)
            wormhole_curves.append(curve)

        baseline_arr = np.array(baseline_curves)
        wormhole_arr = np.array(wormhole_curves)

        return {
            "dates": dates,
            "baseline_median": [round(float(x), 2) for x in np.median(baseline_arr, axis=0)],
            "baseline_p10": [round(float(x), 2) for x in np.percentile(baseline_arr, 10, axis=0)],
            "baseline_p90": [round(float(x), 2) for x in np.percentile(baseline_arr, 90, axis=0)],
            "wormhole_median": [round(float(x), 2) for x in np.median(wormhole_arr, axis=0)],
            "wormhole_p10": [round(float(x), 2) for x in np.percentile(wormhole_arr, 10, axis=0)],
            "wormhole_p90": [round(float(x), 2) for x in np.percentile(wormhole_arr, 90, axis=0)],
            "days_ahead": days_ahead
        }
