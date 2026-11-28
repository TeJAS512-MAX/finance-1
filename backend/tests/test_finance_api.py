from pathlib import Path

from fastapi.testclient import TestClient

from finance.persistence import FinancePersistence
from main import app

client = TestClient(app)


def test_unified_and_finance_health():
    core_res = client.get("/health")
    assert core_res.status_code == 200
    assert core_res.json()["status"] == "ok"

    fin_res = client.get("/api/v1/finance/health")
    assert fin_res.status_code == 200
    data = fin_res.json()
    assert data["status"] == "ONLINE"
    assert data["genome_score"] > 0


def test_finance_api_state():
    res = client.get("/api/v1/finance/state")
    assert res.status_code == 200
    data = res.json()
    assert "state" in data
    assert "singularity" in data
    assert "graph" in data


def test_finance_api_chat_and_wormhole_flow():
    client.post("/api/v1/finance/archetype/STEEL_TRADER")

    res1 = client.post("/api/v1/finance/chat", json={"message": "How is my money?"})
    assert res1.status_code == 200
    data1 = res1.json()
    assert "plain_language_summary" in data1
    assert "top_recommended_actions" in data1

    res2 = client.post(
        "/api/v1/finance/chat",
        json={"message": "Create invoice for Reliance 2.5 lakh"},
    )
    assert res2.status_code == 200
    assert "GST" in res2.json()["plain_language_summary"]

    res3 = client.post("/api/v1/finance/wormhole/activate")
    assert res3.status_code == 200
    assert res3.json()["state"]["genome"]["overall_score"] > 60


def test_finance_api_counterfactual_and_candidates():
    client.post("/api/v1/finance/archetype/STEEL_TRADER")

    res_cf = client.get("/api/v1/finance/counterfactual")
    assert res_cf.status_code == 200
    data_cf = res_cf.json()
    assert "baseline_median" in data_cf
    assert "wormhole_median" in data_cf
    assert len(data_cf["baseline_median"]) == 40

    res_cand = client.get("/api/v1/finance/wormholes/candidates")
    assert res_cand.status_code == 200
    candidates = res_cand.json()["candidates"]
    assert len(candidates) >= 3
    titles = [c["title"] for c in candidates]
    assert any("Trident" in t for t in titles)
    assert any("Velocity" in t for t in titles)
    assert any("Sovereign" in t for t in titles)


def test_finance_api_tools_and_reset():
    res_fc = client.get("/api/v1/finance/forecast")
    assert res_fc.status_code == 200
    assert len(res_fc.json()["daily"]) >= 45

    res_gst = client.get("/api/v1/finance/gst-plan")
    assert res_gst.status_code == 200
    assert "net_payable" in res_gst.json()

    res_ledger = client.get("/api/v1/finance/ledger")
    assert res_ledger.status_code == 200
    ledger_data = res_ledger.json()
    assert "debtors" in ledger_data and "creditors" in ledger_data
    assert "receivables" in ledger_data and "payables" in ledger_data

    res_emi = client.get("/api/v1/finance/emi?principal=1000000&rate=11&months=36")
    assert res_emi.status_code == 200
    emi_data = res_emi.json()
    assert emi_data["monthly_emi"] > 0
    assert emi_data["loan"]["emi"] == emi_data["monthly_emi"]

    res_reset = client.post("/api/v1/finance/profile/reset")
    assert res_reset.status_code == 200
    assert res_reset.json()["status"] == "RESET_SUCCESS"


def test_finance_auth_jwt_and_persistence(tmp_path: Path):
    reg_res = client.post(
        "/api/v1/finance/auth/register",
        json={
            "name": "Asha Mehta",
            "email": "asha@mehtasteel.in",
            "password": "StrongPassword!123",
            "company_name": "Mehta Steel Works",
            "monthly_burn": 120000.0,
        },
    )
    assert reg_res.status_code == 200
    reg_data = reg_res.json()
    assert reg_data["token"].count(".") == 2  # JWT format

    bad_login = client.post(
        "/api/v1/finance/auth/login",
        json={"email": "asha@mehtasteel.in", "password": "wrong-password"},
    )
    assert bad_login.status_code == 401

    good_login = client.post(
        "/api/v1/finance/auth/login",
        json={"email": "asha@mehtasteel.in", "password": "StrongPassword!123"},
    )
    assert good_login.status_code == 200
    assert good_login.json()["token"].count(".") == 2

    # Verify persistence round-trip with explicit file store
    state_file = tmp_path / "finance_state.json"
    store = FinancePersistence(json_path=state_file, enabled=True)
    res_state = client.get("/api/v1/finance/state").json()
    from datetime import date
    from schemas.finance import AetherPravahState

    loaded_model = AetherPravahState.model_validate(res_state["state"])
    store.save(loaded_model, date.fromisoformat(res_state["current_date"]), {"asha@mehtasteel.in": {"name": "Asha"}})
    reloaded = store.load()
    assert reloaded is not None
    assert reloaded[0].business.name == "Mehta Steel Works"


def test_finance_invoice_ocr_text_extraction():
    client.post("/api/v1/finance/profile/reset")
    sample_invoice = (
        "Tax Invoice\n"
        "Invoice No: INV-2026-889\n"
        "Customer: Bharat Forge Ltd\n"
        "Subtotal: Rs 150000\n"
        "18% GST\n"
    ).encode("utf-8")

    res = client.post(
        "/api/v1/finance/upload-invoice",
        files={"file": ("invoice.txt", sample_invoice, "text/plain")},
    )
    assert res.status_code == 200
    data = res.json()
    assert "Bharat Forge" in data["plain_language_summary"]
    assert "150,000.00" in data["exact_numbers"]
    assert "177,000.00" in data["plain_language_summary"]
