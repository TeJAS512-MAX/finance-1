import pytest
from fastapi.testclient import TestClient
from backend.api.server import app

client = TestClient(app)

def test_api_health():
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ONLINE"
    assert data["genome_score"] > 0
    print(f"✅ /api/health passed: Genome score = {data['genome_score']}")

def test_api_state():
    res = client.get("/api/state")
    assert res.status_code == 200
    data = res.json()
    assert "state" in data
    assert "singularity" in data
    assert "graph" in data
    print(f"✅ /api/state passed: {len(data['state']['invoices'])} invoices, {len(data['graph']['nodes'])} causal nodes")

def test_api_chat_flow():
    # 1. Health inquiry
    res1 = client.post("/api/chat", json={"message": "How is my money?"})
    assert res1.status_code == 200
    data1 = res1.json()
    assert "plain_language_summary" in data1
    assert "top_recommended_actions" in data1
    print("✅ /api/chat 'How is my money?' passed")

    # 2. Create invoice
    res2 = client.post("/api/chat", json={"message": "Create invoice for Reliance 2.5 lakh"})
    assert res2.status_code == 200
    data2 = res2.json()
    assert "GST" in data2["plain_language_summary"]
    print("✅ /api/chat 'Create invoice for Reliance' passed")

    # 3. Wormhole activation
    res3 = client.post("/api/wormhole/activate")
    assert res3.status_code == 200
    data3 = res3.json()
    assert data3["state"]["genome"]["overall_score"] > 60
    print(f"✅ /api/wormhole/activate passed: Genome score boosted to {data3['state']['genome']['overall_score']}")

def test_api_counterfactual():
    res = client.get("/api/counterfactual")
    assert res.status_code == 200
    data = res.json()
    assert "baseline_median" in data
    assert "wormhole_median" in data
    assert len(data["baseline_median"]) == 40
    print(f"✅ /api/counterfactual passed: 40 simulated future days generated")

def test_api_wormhole_candidates():
    # Reset to baseline archetype to test candidate generation in pre-execution singularity state
    client.post("/api/archetype/STEEL_TRADER")
    res = client.get("/api/wormholes/candidates")
    assert res.status_code == 200
    data = res.json()
    assert "candidates" in data
    assert len(data["candidates"]) >= 3
    titles = [c["title"] for c in data["candidates"]]
    assert any("Trident" in t for t in titles)
    assert any("Velocity" in t for t in titles)
    assert any("Sovereign" in t for t in titles)
    print(f"✅ /api/wormholes/candidates passed: {len(data['candidates'])} Pareto strategies generated ({', '.join(titles)})")

def test_static_frontend_mount():
    res = client.get("/")
    assert res.status_code == 200
    assert "AetherPravah" in res.text
    print("✅ Static Frontend mounted and served at '/' successfully")

if __name__ == "__main__":
    test_api_health()
    test_api_state()
    test_api_chat_flow()
    test_api_wormhole_candidates()
    test_api_counterfactual()
    test_static_frontend_mount()
    print("\n🎉 ALL API ENDPOINTS & FRONTEND TESTS PASSED PERFECTLY!")
