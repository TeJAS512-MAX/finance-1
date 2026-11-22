from __future__ import annotations
from typing import Dict, Any

ARCHETYPE_DEFAULTS = {
    "STEEL_TRADER": {
        "business_name": "Bharat Steel Traders Pvt Ltd",
        "archetype": "STEEL_TRADER",
        "profit": {
            "monthly_sales": 7000000.0,
            "cogs_pct": 90.0,
            "running_costs": 152000.0,
            "emis": 88000.0,
            "note": "Wholesale steel distribution margins (~10% gross margin)."
        },
        "loan": {
            "principal": 1000000.0,
            "rate_pct": 11.0,
            "months": 60,
            "example": {
                "principal": 1000000.0,
                "annual_rate_pct": 11.0,
                "months": 60,
                "emi": 21742.42,
                "total_payment": 1304545.38,
                "total_interest": 304545.38,
                "interest_share_pct": 23.3
            }
        },
        "forecast": {
            "monthly_burn": 240000.0,
            "other_running_costs": 87000.0,
            "scheduled_items": 153000.0
        }
    },
    "VASTRAKALA": {
        "business_name": "VastraKala Heritage Textiles",
        "archetype": "GARMENT_MANUFACTURER",
        "profit": {
            "monthly_sales": 3200000.0,
            "cogs_pct": 65.0,
            "running_costs": 480000.0,
            "emis": 45000.0,
            "note": "Textile and apparel manufacturing (~35% gross margin)."
        },
        "loan": {
            "principal": 800000.0,
            "rate_pct": 11.5,
            "months": 48,
            "example": {
                "principal": 800000.0,
                "annual_rate_pct": 11.5,
                "months": 48,
                "emi": 20875.0,
                "total_payment": 1002000.0,
                "total_interest": 202000.0,
                "interest_share_pct": 20.2
            }
        },
        "forecast": {
            "monthly_burn": 180000.0,
            "other_running_costs": 60000.0,
            "scheduled_items": 120000.0
        }
    },
    "NEXUS_PULSE": {
        "business_name": "NexusPulse Digital Solutions Pvt Ltd",
        "archetype": "DIGITAL_AGENCY",
        "profit": {
            "monthly_sales": 1833000.0,
            "cogs_pct": 30.0,
            "running_costs": 650000.0,
            "emis": 0.0,
            "note": "IT services & digital solutions (~70% gross margin, high payroll)."
        },
        "loan": {
            "principal": 1500000.0,
            "rate_pct": 12.0,
            "months": 36,
            "example": {
                "principal": 1500000.0,
                "annual_rate_pct": 12.0,
                "months": 36,
                "emi": 49821.0,
                "total_payment": 1793556.0,
                "total_interest": 293556.0,
                "interest_share_pct": 16.4
            }
        },
        "forecast": {
            "monthly_burn": 650000.0,
            "other_running_costs": 100000.0,
            "scheduled_items": 550000.0
        }
    }
}

def finance_defaults(archetype_key: str = "STEEL_TRADER") -> Dict[str, Any]:
    return ARCHETYPE_DEFAULTS.get(archetype_key, ARCHETYPE_DEFAULTS["STEEL_TRADER"])
