from __future__ import annotations
from datetime import date, timedelta
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from schemas.finance import AetherPravahState
from finance.calculators import fmt_compact, fmt_inr

class Scenario(BaseModel):
    horizon: int = Field(default=45, ge=14, le=90)
    delay_days: int = Field(default=0, ge=-30, le=60)
    prompt_discount_pct: float = Field(default=0.0, ge=0.0, le=5.0)
    cost_cut_pct: float = Field(default=0.0, ge=0.0, le=60.0)
    planned_spend: float = Field(default=0.0, ge=0.0)
    spend_day: int = Field(default=0, ge=0, le=89)
    custom_running_cost: Optional[float] = None

def run_forecast(
    state: AetherPravahState,
    current_date: date,
    scenario: Optional[Scenario] = None
) -> Dict[str, Any]:
    """
    Computes a day-by-day cash trajectory over the forecast horizon.
    Strictly accounts for collections, supplier bills, statutory taxes, loan EMIs, and daily burn.
    """
    if scenario is None:
        scenario = Scenario()

    horizon = scenario.horizon
    daily_balances: List[Dict[str, Any]] = []
    events_log: List[Dict[str, Any]] = []

    # Starting liquid cash
    running_balance = float(state.physics_state.bank_cash)

    # Running daily burn baseline
    if state.business.archetype == "STEEL_TRADER":
        base_monthly_burn = 240000.0
    elif state.business.archetype == "GARMENT_MANUFACTURER":
        base_monthly_burn = 180000.0
    elif state.business.archetype == "DIGITAL_AGENCY":
        base_monthly_burn = 650000.0
    elif state.business.monthly_burn_rate and state.business.monthly_burn_rate > 0:
        base_monthly_burn = float(state.business.monthly_burn_rate)
    else:
        base_monthly_burn = 100000.0
    if scenario.custom_running_cost is not None and scenario.custom_running_cost > 0:
        base_monthly_burn = scenario.custom_running_cost

    effective_monthly_burn = base_monthly_burn * (1 - (scenario.cost_cut_pct / 100.0))
    daily_burn = effective_monthly_burn / 30.0

    # Map collections by day offset
    # Invoices: due_date + delay_prediction_days + scenario.delay_days
    # If discount offered (>0%), accelerate collection to day 2 or 3
    inflows_by_day: Dict[int, float] = {d: 0.0 for d in range(horizon + 1)}
    inflow_details: Dict[int, List[str]] = {d: [] for d in range(horizon + 1)}

    for inv in state.invoices:
        if inv.status == "PAID":
            continue
        
        expected_delay = inv.delay_prediction_days + scenario.delay_days
        raw_target_date = inv.due_date + timedelta(days=int(expected_delay))
        day_offset = (raw_target_date - current_date).days

        amount = float(inv.unpaid_cash)

        # Early payment discount acceleration
        if scenario.prompt_discount_pct > 0 and day_offset > 3:
            day_offset = 3
            discount_amount = amount * (scenario.prompt_discount_pct / 100.0)
            amount -= discount_amount
            inflow_details[day_offset].append(
                f"{inv.customer_name} ({fmt_compact(amount)} with {scenario.prompt_discount_pct}% discount)"
            )
        else:
            if day_offset < 0:
                day_offset = 1 # Overdue items collect soon
            if day_offset <= horizon:
                inflow_details[day_offset].append(f"{inv.customer_name} ({fmt_compact(amount)})")

        if 0 <= day_offset <= horizon:
            inflows_by_day[day_offset] += amount

    # Map obligations & taxes by day offset
    outflows_by_day: Dict[int, float] = {d: 0.0 for d in range(horizon + 1)}
    outflow_details: Dict[int, List[str]] = {d: [] for d in range(horizon + 1)}

    # Senior obligations (EMIs, rent, payroll)
    for obl in state.obligations:
        day_offset = (obl.due_date - current_date).days
        if 0 <= day_offset <= horizon:
            outflows_by_day[day_offset] += float(obl.amount)
            outflow_details[day_offset].append(f"{obl.name} ({fmt_compact(obl.amount)})")

    # Supplier bills
    for supp in state.suppliers:
        # Typical 30 day credit
        day_offset = 12
        if 0 <= day_offset <= horizon:
            outflows_by_day[day_offset] += float(supp.total_payable)
            outflow_details[day_offset].append(f"Supplier: {supp.name} ({fmt_compact(supp.total_payable)})")

    # Statutory GST payment on due date (Nov 20)
    gst_day_offset = (state.gst_snapshot.gstr3b_due_date - current_date).days
    tax_due = float(state.gst_snapshot.net_gst_cash_payable)
    # Deduct amount already secured in Tax Vault
    net_cash_tax_demand = max(0.0, tax_due - float(state.physics_state.tax_vault_balance))
    if 0 <= gst_day_offset <= horizon:
        outflows_by_day[gst_day_offset] += net_cash_tax_demand
        outflow_details[gst_day_offset].append(f"GSTR-3B Tax Settlement ({fmt_compact(net_cash_tax_demand)})")

    # One-off planned capital spend
    if scenario.planned_spend > 0 and 0 <= scenario.spend_day <= horizon:
        outflows_by_day[scenario.spend_day] += scenario.planned_spend
        outflow_details[scenario.spend_day].append(f"Planned Capex ({fmt_compact(scenario.planned_spend)})")

    # Daily trajectory loop
    lowest_balance = running_balance
    lowest_day = 0
    days_to_zero: Optional[int] = None

    dates_series = []
    baseline_series = []

    for d in range(horizon + 1):
        cal_date = current_date + timedelta(days=d)
        date_label = cal_date.strftime("%d %b")
        dates_series.append(date_label)

        inflow = inflows_by_day.get(d, 0.0)
        outflow = outflows_by_day.get(d, 0.0) + daily_burn

        running_balance = running_balance + inflow - outflow
        baseline_series.append(round(running_balance, 2))

        if running_balance < lowest_balance:
            lowest_balance = running_balance
            lowest_day = d

        if running_balance < 0 and days_to_zero is None:
            days_to_zero = d

        # Record landmark events
        if inflow > 0 or outflow > (daily_burn * 1.5):
            ev_in = ", ".join(inflow_details.get(d, []))
            ev_out = ", ".join(outflow_details.get(d, []))
            desc = ""
            if ev_in and ev_out:
                desc = f"In: {ev_in} | Out: {ev_out}"
            elif ev_in:
                desc = f"+{fmt_compact(inflow)} ({ev_in})"
            elif ev_out:
                desc = f"-{fmt_compact(outflow)} ({ev_out})"

            events_log.append({
                "day": d,
                "date": date_label,
                "inflow": round(inflow, 2),
                "outflow": round(outflow, 2),
                "balance": round(running_balance, 2),
                "description": desc,
                "is_negative": running_balance < 0
            })

        daily_balances.append({
            "day": d,
            "date": date_label,
            "balance": round(running_balance, 2),
            "inflow": round(inflow, 2),
            "outflow": round(outflow, 2),
            "is_negative": running_balance < 0
        })

    lowest_date = current_date + timedelta(days=lowest_day)

    summary = {
        "starting_cash": float(state.physics_state.bank_cash),
        "ending_cash": round(running_balance, 2),
        "lowest_balance": round(lowest_balance, 2),
        "lowest_date": lowest_date.isoformat(),
        "lowest_date_label": lowest_date.strftime("%d %b %Y"),
        "lowest_day_offset": lowest_day,
        "is_deficit": lowest_balance < 0,
        "max_deficit": round(abs(lowest_balance), 2) if lowest_balance < 0 else 0.0,
        "estimated_runway_days": days_to_zero if days_to_zero is not None else float(horizon),
        "daily_burn_rate": round(daily_burn, 2),
        "total_inflows": round(sum(inflows_by_day.values()), 2),
        "total_outflows": round(sum(outflows_by_day.values()) + (daily_burn * horizon), 2)
    }

    assumptions = [
        f"Daily operating burn estimated at {fmt_inr(daily_burn)} ({fmt_inr(effective_monthly_burn)}/month)",
        f"Statutory GST net payable required strictly on {state.gst_snapshot.gstr3b_due_date.strftime('%d %b')}",
        f"Customer delays modeled with +{scenario.delay_days} days shift" if scenario.delay_days != 0 else "Customer delays based on behavioral AI scores",
        f"{scenario.prompt_discount_pct}% prompt settlement discount applied" if scenario.prompt_discount_pct > 0 else "Standard payment terms without dynamic discounting"
    ]

    return {
        "dates": dates_series,
        "balances": baseline_series,
        "summary": summary,
        "events": events_log,
        "daily": daily_balances,
        "assumptions": assumptions,
        "params": scenario.model_dump()
    }
