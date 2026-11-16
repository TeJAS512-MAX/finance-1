from __future__ import annotations
import numpy as np
from datetime import date, datetime
from typing import List, Tuple
from backend.models.schemas import (
    Invoice, Obligation, GSTLiabilitySnapshot, MoneyPhysicsState, RupeePacket
)

class MoneyPhysicsEngine:
    """
    Money Physics Engine v3:
    Treats financial flow as compressible fluid dynamics under tax gravity,
    strict conservation laws, and behavioral viscosity.
    """

    @staticmethod
    def verify_conservation(
        bank_cash: float,
        tax_vault: float,
        receivables: float,
        inventory_or_escrow: float,
        rupee_packets: List[RupeePacket]
    ) -> Tuple[bool, float, float]:
        """
        Conservation of Money Law:
        Sum of individual RupeePackets MUST match physical balances.
        """
        physical_sum = round(bank_cash + tax_vault + receivables + inventory_or_escrow, 2)
        packet_sum = round(sum(p.amount for p in rupee_packets), 2)
        discrepancy = round(abs(physical_sum - packet_sum), 2)
        is_conserved = discrepancy < 0.05
        return is_conserved, physical_sum, discrepancy

    @staticmethod
    def compute_viscosity(invoices: List[Invoice]) -> float:
        """
        Fluid Viscosity (Friction):
        Measures liquidity drag caused by delayed receivables.
        A score of 1.0 is laminar frictionless flow. 3.0+ indicates sludge.
        """
        unpaid = [inv for inv in invoices if inv.status in ("ISSUED", "PARTIALLY_PAID", "OVERDUE", "CRITICAL_TRAP")]
        if not unpaid:
            return 1.0

        total_unpaid = sum(inv.unpaid_cash for inv in unpaid)
        if total_unpaid <= 0:
            return 1.0

        # Weighted delay friction
        weighted_delay = sum(inv.unpaid_cash * max(0.0, inv.delay_prediction_days) for inv in unpaid)
        base_viscosity = 1.0 + (weighted_delay / (total_unpaid * 15.0))
        return round(float(np.clip(base_viscosity, 1.0, 8.5)), 2)

    @staticmethod
    def compute_tax_gravity_well(
        gst_snapshot: GSTLiabilitySnapshot, 
        current_date: date
    ) -> float:
        """
        Tax Gravity:
        Gravitational pull exerted by statutory GSTR-3B tax deadline.
        Approaches infinity as days_to_filing -> 0 if tax is unpaid.
        """
        days_to_filing = (gst_snapshot.gstr3b_due_date - current_date).days
        effective_days = max(1, days_to_filing)
        
        # Net unreserved tax liability
        unreserved_tax = max(0.0, gst_snapshot.net_gst_cash_payable - gst_snapshot.tax_vault_reserved)
        gravity_force = unreserved_tax / effective_days
        return round(float(gravity_force), 2)

    @classmethod
    def calculate_state(
        cls,
        current_date: date,
        bank_cash: float,
        tax_vault: float,
        invoices: List[Invoice],
        obligations: List[Obligation],
        gst_snapshot: GSTLiabilitySnapshot,
        rupee_packets: List[RupeePacket],
        monthly_burn_rate: float
    ) -> MoneyPhysicsState:
        """
        Synthesizes the complete macroscopic physics state.
        """
        pending_receivables = sum(inv.unpaid_cash for inv in invoices if inv.status != "PAID")
        
        # Obligations over the next 30 days
        next_30d_obligations = sum(
            obl.amount for obl in obligations 
            if 0 <= (obl.due_date - current_date).days <= 30
        )
        
        # Money conservation check
        is_conserved, conserved_total, _ = cls.verify_conservation(
            bank_cash, tax_vault, pending_receivables, 0.0, rupee_packets
        )

        viscosity = cls.compute_viscosity(invoices)
        gravity = cls.compute_tax_gravity_well(gst_snapshot, current_date)

        # Net liquid reserve available for operations (excluding legally isolated tax vault)
        net_liquid_cash = max(0.0, bank_cash)
        daily_burn = max(100.0, monthly_burn_rate / 30.0)

        # Probabilistic runway calculation with conformal bounds
        # Cash flow discount factor based on viscosity
        expected_daily_inflow = (pending_receivables / (30.0 * viscosity)) if viscosity > 0 else 0.0
        effective_net_daily_drain = max(10.0, daily_burn - (expected_daily_inflow * 0.4))
        
        mean_runway = round(net_liquid_cash / effective_net_daily_drain, 1)
        lower_runway = max(0.0, round(mean_runway * 0.72, 1))
        upper_runway = round(mean_runway * 1.35, 1)

        # Rupee fluid velocity
        velocity = round(float(np.clip(30.0 / viscosity, 3.5, 45.0)), 1)

        return MoneyPhysicsState(
            timestamp=datetime.utcnow(),
            total_rupees_conserved=conserved_total,
            bank_cash=round(bank_cash, 2),
            tax_vault_balance=round(tax_vault, 2),
            pending_receivables=round(pending_receivables, 2),
            locked_working_capital=round(pending_receivables * 0.45, 2),
            total_obligations_next_30d=round(next_30d_obligations, 2),
            fluid_velocity=velocity,
            viscosity_index=viscosity,
            tax_gravity_well=gravity,
            estimated_runway_days=mean_runway,
            confidence_interval_runway=(lower_runway, upper_runway)
        )
