from __future__ import annotations
import math
import re
from typing import Dict, Any, List

def calculate_emi(principal: float, annual_rate_pct: float, months: int) -> float:
    """Standard reducing-balance EMI formula."""
    if principal <= 0 or months <= 0:
        return 0.0
    if annual_rate_pct <= 0:
        return round(principal / months, 2)
    
    monthly_rate = (annual_rate_pct / 100.0) / 12.0
    emi = (principal * monthly_rate * math.pow(1 + monthly_rate, months)) / (math.pow(1 + monthly_rate, months) - 1)
    return round(emi, 2)

def loan_summary(principal: float, annual_rate_pct: float, months: int) -> Dict[str, Any]:
    """Generates complete loan repayment numbers and interest shares."""
    emi = calculate_emi(principal, annual_rate_pct, months)
    total_payment = round(emi * months, 2)
    total_interest = round(total_payment - principal, 2)
    interest_share_pct = round((total_interest / total_payment * 100.0) if total_payment > 0 else 0.0, 1)
    
    return {
        "principal": round(principal, 2),
        "annual_rate_pct": annual_rate_pct,
        "months": months,
        "emi": emi,
        "total_payment": total_payment,
        "total_interest": total_interest,
        "interest_share_pct": interest_share_pct
    }

def amortization_by_year(principal: float, annual_rate_pct: float, months: int) -> List[Dict[str, Any]]:
    """Year-by-year amortization schedule."""
    if principal <= 0 or months <= 0:
        return []
    
    monthly_rate = (annual_rate_pct / 100.0) / 12.0
    emi = calculate_emi(principal, annual_rate_pct, months)
    balance = principal
    schedule = []
    
    years = math.ceil(months / 12.0)
    current_month = 0
    
    for yr in range(1, years + 1):
        yr_principal = 0.0
        yr_interest = 0.0
        
        for _ in range(12):
            if current_month >= months or balance <= 0:
                break
            interest = balance * monthly_rate
            principal_paid = emi - interest
            if principal_paid > balance:
                principal_paid = balance
                balance = 0.0
            else:
                balance -= principal_paid
            
            yr_interest += interest
            yr_principal += principal_paid
            current_month += 1
            
        schedule.append({
            "year": yr,
            "principal_paid": round(yr_principal, 2),
            "interest_paid": round(yr_interest, 2),
            "closing_balance": round(max(0.0, balance), 2)
        })
        
    return schedule

def debt_service_verdict(total_emis: float, operating_profit_before_emi: float) -> Dict[str, Any]:
    """
    Checks what share of monthly operating profit goes to EMIs.
    <=40% comfortable, <=60% stretched, >60% heavy.
    """
    if operating_profit_before_emi <= 0:
        return {
            "ratio_pct": None,
            "verdict": "heavy",
            "text": "Your business is currently operating at a cash deficit, so any new EMI would increase insolvency risk."
        }
    
    ratio = (total_emis / operating_profit_before_emi) * 100.0
    if ratio <= 40.0:
        verdict = "comfortable"
        text = f"Comfortable: Monthly EMIs consume {ratio:.1f}% of operating profit (safely under 40%)."
    elif ratio <= 60.0:
        verdict = "stretched"
        text = f"Stretched: Monthly EMIs consume {ratio:.1f}% of operating profit (leaves little safety cushion)."
    else:
        verdict = "heavy"
        text = f"Heavy / High Risk: Monthly EMIs consume {ratio:.1f}% of operating profit (>60% threshold)."
        
    return {
        "ratio_pct": round(ratio, 1),
        "verdict": verdict,
        "text": text
    }

def gst_split(amount: float, rate_pct: float = 18.0, is_inclusive: bool = True) -> Dict[str, float]:
    """Calculates Base Amount, CGST, SGST, IGST, and Total."""
    if is_inclusive:
        base = amount / (1 + (rate_pct / 100.0))
        gst = amount - base
        total = amount
    else:
        base = amount
        gst = amount * (rate_pct / 100.0)
        total = base + gst
        
    return {
        "base": round(base, 2),
        "gst": round(gst, 2),
        "cgst": round(gst / 2.0, 2),
        "sgst": round(gst / 2.0, 2),
        "total": round(total, 2),
        "rate_pct": rate_pct
    }

def profit_model(monthly_sales: float, cogs_pct: float, running_costs: float, emis: float) -> Dict[str, Any]:
    """Calculates monthly gross profit, operating profit, net profit, and break-even sales."""
    gross_profit = monthly_sales * (1 - (cogs_pct / 100.0))
    operating_profit = gross_profit - running_costs
    net_profit = operating_profit - emis
    
    margin = 1 - (cogs_pct / 100.0)
    fixed_costs = running_costs + emis
    breakeven_sales = (fixed_costs / margin) if margin > 0 else float("inf")
    
    return {
        "monthly_sales": round(monthly_sales, 2),
        "cogs_pct": cogs_pct,
        "gross_profit": round(gross_profit, 2),
        "operating_expenses": round(running_costs, 2),
        "operating_profit": round(operating_profit, 2),
        "monthly_emis": round(emis, 2),
        "net_profit": round(net_profit, 2),
        "net_margin_pct": round((net_profit / monthly_sales * 100.0) if monthly_sales > 0 else 0.0, 1),
        "breakeven_sales": round(breakeven_sales, 2)
    }

def fmt_inr(amount: float) -> str:
    """Formats a number in Indian rupee formatting: ₹1,52,915.00"""
    is_neg = amount < 0
    val = abs(round(amount, 2))
    s = f"{val:.2f}"
    parts = s.split(".")
    integer_part = parts[0]
    decimal_part = parts[1]
    
    if len(integer_part) > 3:
        last3 = integer_part[-3:]
        rest = integer_part[:-3]
        groups = []
        while len(rest) > 2:
            groups.insert(0, rest[-2:])
            rest = rest[:-2]
        if rest:
            groups.insert(0, rest)
        formatted_int = ",".join(groups) + "," + last3
    else:
        formatted_int = integer_part
        
    return f"{'-' if is_neg else ''}₹{formatted_int}.{decimal_part}"

def fmt_compact(amount: float) -> str:
    """Formats in compact Indian terms: ₹1.53 L, ₹35k, ₹2.40 Cr"""
    abs_amt = abs(amount)
    sign = "-" if amount < 0 else ""
    if abs_amt >= 10000000:
        return f"{sign}₹{abs_amt / 10000000:.2f} Cr"
    elif abs_amt >= 100000:
        return f"{sign}₹{abs_amt / 100000:.2f} L"
    elif abs_amt >= 1000:
        return f"{sign}₹{abs_amt / 1000:.0f}k"
    else:
        return f"{sign}₹{abs_amt:.0f}"

def extract_amounts(text: str) -> List[float]:
    """Finds money amounts mentioned in user queries."""
    results = []
    # e.g., 5 lakh, 2.5 L, 50k, 100000, 1.2 cr
    pattern = r"(?:₹|rs\.?|inr)?\s*(\d+(?:\.\d+)?)\s*(lakh|lac|l|cr|crore|k|thousand)?"
    matches = re.finditer(pattern, text, re.IGNORECASE)
    for m in matches:
        num_str = m.group(1)
        unit = (m.group(2) or "").lower()
        if not num_str:
            continue
        val = float(num_str)
        if unit in ("lakh", "lac", "l"):
            results.append(val * 100000.0)
        elif unit in ("cr", "crore"):
            results.append(val * 10000000.0)
        elif unit in ("k", "thousand"):
            results.append(val * 1000.0)
        elif val >= 500:
            results.append(val)
    return results

def extract_days(text: str) -> int:
    m = re.search(r"(\d+)\s*(?:day|days|din)", text, re.IGNORECASE)
    return int(m.group(1)) if m else 15

def extract_rate_pct(text: str) -> float:
    m = re.search(r"(\d+(?:\.\d+)?)\s*%", text)
    return float(m.group(1)) if m else 11.0

def extract_tenure_months(text: str) -> int:
    m_yr = re.search(r"(\d+(?:\.\d+)?)\s*(?:year|years|saal|yr|yrs)", text, re.IGNORECASE)
    if m_yr:
        return int(float(m_yr.group(1)) * 12)
    m_mo = re.search(r"(\d+)\s*(?:month|months|mahine|mo)", text, re.IGNORECASE)
    if m_mo:
        return int(m_mo.group(1))
    return 60
