import pytest
from fastapi.testclient import TestClient
from src.api.server import app

client = TestClient(app)

def test_static_files_served():
    # Browser requests root with text/html
    r_root = client.get("/", headers={"Accept": "text/html,application/xhtml+xml"})
    assert r_root.status_code == 200
    assert "text/html" in r_root.headers.get("content-type", "")
    assert "THE FIRST 10 MINUTES" in r_root.text

    # Static assets
    r_css = client.get("/styles.css")
    assert r_css.status_code == 200
    assert "cap-alert-panel" in r_css.text

    r_api = client.get("/api.js")
    assert r_api.status_code == 200
    assert "CrisisSenseAPI" in r_api.text

    r_app = client.get("/app.js")
    assert r_app.status_code == 200
    assert "liveTimelineCache" in r_app.text

    r_login = client.get("/login.html")
    assert r_login.status_code == 200

    r_supa = client.get("/supabase-config.js")
    assert r_supa.status_code == 200

def test_scenarios_list():
    r = client.get("/scenarios")
    assert r.status_code == 200
    scenarios = r.json()
    assert len(scenarios) >= 8
    ids = [s["id"] for s in scenarios]
    assert "twin_cascade" in ids
    assert "twin_benign" in ids

def test_twin_test_divergence_via_api():
    # 1. Start Alpha (twin_cascade)
    r_alpha = client.post("/episode/start", json={"scenario": "alpha", "seed": 42})
    assert r_alpha.status_code == 200
    assert r_alpha.json()["scenario"] == "twin_cascade"

    alpha_min7 = client.get("/episode/state/7").json()
    alpha_min8 = client.get("/episode/state/8").json()

    # 2. Start Beta (twin_benign)
    r_beta = client.post("/episode/start", json={"scenario": "beta", "seed": 42})
    assert r_beta.status_code == 200
    assert r_beta.json()["scenario"] == "twin_benign"

    beta_min7 = client.get("/episode/state/7").json()
    beta_min8 = client.get("/episode/state/8").json()

    # Prefix honesty: minute 7 P(H3) must match within tolerance
    p_h3_alpha_m7 = alpha_min7["probabilities"]["H3"]
    p_h3_beta_m7 = beta_min7["probabilities"]["H3"]
    assert abs(p_h3_alpha_m7 - p_h3_beta_m7) < 0.05, f"Prefix diverged early: alpha={p_h3_alpha_m7}, beta={p_h3_beta_m7}"

    # Divergence at minute 8:
    # Alpha commits to high crisis probability
    assert alpha_min8["probabilities"]["H3"] >= 0.70
    assert alpha_min8["recommended_action"] in ("ALERT", "ESCALATE")

    # Beta relaxes
    assert beta_min8["probabilities"]["H3"] < 0.25
    assert beta_min8["recommended_action"] in ("WATCH", "PREPARE")

def test_adversity_injections():
    client.post("/episode/start", json={"scenario": "twin_cascade", "seed": 42})

    # Test gateway cutout
    r_cutout = client.post("/inject", json={"inject_type": "cutout", "target": "gw_1"})
    assert r_cutout.status_code == 200
    assert r_cutout.json()["status"] == "injected"

    # Test rumor swarm
    r_rumor = client.post("/inject", json={"inject_type": "rumor"})
    assert r_rumor.status_code == 200
    assert r_rumor.json()["status"] == "injected"

    # Test delay jitter
    r_jitter = client.post("/inject", json={"inject_type": "jitter"})
    assert r_jitter.status_code == 200
    assert r_jitter.json()["status"] == "injected"

    # Test structured lie
    r_lie = client.post("/inject", json={"inject_type": "lie"})
    assert r_lie.status_code == 200
    assert r_lie.json()["status"] == "injected"

def test_cap_alert_guarantee():
    client.post("/episode/start", json={"scenario": "twin_cascade", "seed": 42})
    # Fast forward to minute 8 where alert/escalate is triggered
    client.get("/episode/state/8")

    # JSON CAP Alert
    r_json = client.get("/cap-alert?format=json")
    assert r_json.status_code == 200
    data = r_json.json()
    assert data["format"] == "json"
    assert data["content"]["status"] == "Exercise"

    # XML CAP Alert
    r_xml = client.get("/cap-alert?format=xml")
    assert r_xml.status_code == 200
    assert r_xml.json()["format"] == "xml"
    assert "<status>Exercise</status>" in r_xml.json()["content"]
