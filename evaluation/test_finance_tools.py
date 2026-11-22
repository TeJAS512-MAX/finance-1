import pytest
from backend.finance.calculators import calculate_emi, gst_split, profit_model, debt_service_verdict
from backend.finance.forecast import run_forecast, Scenario
from backend.finance.gst_plan import build_gst_plan
from backend.finance.ledger import receivables_view, payables_view, generate_reminder_draft
from backend.orchestrator.cns import CentralNervousSystem


def test_calculators():
    # Test EMI: 10 Lakhs at 12% for 3 years (36 months)
    emi = calculate_emi(1000000, 12.0, 36)
    assert 33000 <= emi <= 33500, f"Unexpected EMI: {emi}"
    
    # Test GST split: gross 118 with 18% tax -> base 100, gst 18
    split = gst_split(118.0, 18.0, is_inclusive=True)
    assert round(split["base"], 2) == 100.0
    assert round(split["gst"], 2) == 18.0

    # Test profit model
    pm = profit_model(1000000, 70.0, 150000, 30000)
    assert pm["gross_profit"] == 300000.0
    assert pm["operating_profit"] == 150000.0
    assert pm["net_profit"] == 120000.0


def test_cns_forecast_and_gst():
    cns = CentralNervousSystem()
    cns.set_archetype("STEEL_TRADER")
    
    # Check forecast
    fc = run_forecast(cns.state, cns.current_date, Scenario(delay_days=0))
    assert "daily" in fc
    assert len(fc["daily"]) >= 45
    assert fc["summary"]["starting_cash"] == cns.state.physics_state.bank_cash
    
    # Check GST plan
    gp = build_gst_plan(cns.state, cns.current_date)
    assert gp["net_payable"] > 0
    assert gp["still_to_arrange"] >= 0
    assert len(gp["steps"]) > 0


def test_ledger_and_reminders():
    cns = CentralNervousSystem()
    rec = receivables_view(cns.state, cns.current_date)
    pay = payables_view(cns.state, cns.current_date)
    assert "invoices" in rec
    assert "liabilities" in pay
    assert len(rec["invoices"]) > 0
    assert len(pay["liabilities"]) > 0

    first_inv = rec["invoices"][0]
    rem = first_inv["reminder"]
    assert rem is not None
    assert "message" in rem
    assert len(rem["message"]) > 0


def test_assistant_chat_intents():
    cns = CentralNervousSystem()
    
    # Test greetings
    res = cns.process_user_message("Hello, how are you?")
    assert "cards" in res
    
    # Test cash flow inquiry
    res = cns.process_user_message("How is my money?")
    assert "cards" in res
    assert len(res["plain_language_summary"]) > 0
    
    # Test who owes me
    res = cns.process_user_message("Who owes me money?")
    assert "receivables" in res["plain_language_summary"].lower() or "owes" in res["plain_language_summary"].lower()
    
    # Test affordability
    res = cns.process_user_message("Can I buy machinery for 500000?")
    assert "affordability" in res["plain_language_summary"].lower() or "caution" in res["plain_language_summary"].lower() or "lowest" in res["plain_language_summary"].lower()
    
    # Test EMI
    res = cns.process_user_message("Calculate EMI for 10 lakhs at 11% for 3 years")
    assert "emi" in res["plain_language_summary"].lower() or "32,739" in res["plain_language_summary"] or "32,738" in res["plain_language_summary"]


def test_user_profile_and_chat_actions():
    cns = CentralNervousSystem()
    
    # User creates profile
    cns.set_user_profile(
        company_name="Apex Logistics Ltd",
        owner_name="Vikram Patel",
        business_type="Freight & Transport",
        city="Ahmedabad, Gujarat",
        gstin="24AAACA1234M1Z8",
        bank_cash=500000.0,
        tax_vault=50000.0
    )
    assert cns.state.business.name == "Apex Logistics Ltd"
    assert cns.state.business.owner_name == "Vikram Patel"
    assert cns.state.physics_state.bank_cash == 500000.0

    # User adds invoice via natural language chat
    res = cns.process_user_message("Add invoice for Tata Steel of 300000 with 18% gst due 30 days")
    assert "invoice" in res["plain_language_summary"].lower()
    assert any(i.customer_name == "Tata Steel" for i in cns.state.invoices)

    # User adds expense via chat
    res = cns.process_user_message("Add expense monthly rent 45000")
    assert "expense" in res["plain_language_summary"].lower() or "recorded" in res["plain_language_summary"].lower()

    # User records payment received via chat
    initial_cash = cns.state.physics_state.bank_cash
    res = cns.process_user_message("Received payment 100000 from Tata Steel")
    assert "payment" in res["plain_language_summary"].lower()
    assert cns.state.physics_state.bank_cash > initial_cash

    # User updates bank balance via chat
    res = cns.process_user_message("My bank balance is 650000")
    assert "6,50,000" in res["plain_language_summary"]
    assert cns.state.physics_state.bank_cash == 650000.0

