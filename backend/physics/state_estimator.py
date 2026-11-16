from __future__ import annotations
import numpy as np
from datetime import date, timedelta
from typing import List, Dict
from backend.models.schemas import Customer, Invoice

class StateEstimator:
    """
    State Estimator (Simplified Ensemble Kalman / Bayesian Update):
    Maintains dynamic probability distributions over customer payment dates
    and updates delays based on behavioral telemetry.
    """

    @staticmethod
    def update_customer_realization(
        customer: Customer,
        invoice: Invoice,
        current_date: date,
        festival_season: bool = False
    ) -> float:
        """
        Updates predicted delay days for a specific invoice using prior behavior
        and behavioral profile priors.
        """
        # Prior delay distribution
        prior_mean = float(customer.typical_delay_days)
        
        # Profile variance adjustments
        profile_modifiers = {
            "PROMPT_PAYER": -4.0,
            "BUREAUCRATIC_ENTERPRISE": +18.0,
            "SEASONAL_SLACKER": +25.0 if festival_season else +8.0,
            "RELATIONSHIP_DEPENDENT": +5.0,
            "CHRONIC_DEFENDER": +30.0
        }
        
        adjustment = profile_modifiers.get(customer.psychological_profile, 0.0)
        
        # Age penalty: as an invoice exceeds due date, hazard rate of further delay increases
        days_past_due = max(0, (current_date - invoice.due_date).days)
        aging_drift = days_past_due * 0.35

        # Updated posterior mean delay
        posterior_delay = max(0.0, prior_mean + adjustment + aging_drift)
        return round(posterior_delay, 1)

    @classmethod
    def update_all_invoices(
        cls, 
        invoices: List[Invoice], 
        customers: Dict[str, Customer], 
        current_date: date
    ) -> List[Invoice]:
        for inv in invoices:
            cust = customers.get(inv.customer_id)
            if cust and inv.status not in ("PAID",):
                inv.delay_prediction_days = cls.update_customer_realization(cust, inv, current_date)
                # Flag critical traps
                if (current_date - inv.due_date).days > 45:
                    inv.status = "CRITICAL_TRAP"
                elif (current_date - inv.due_date).days > 0:
                    inv.status = "OVERDUE"
        return invoices
