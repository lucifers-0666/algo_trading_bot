"""Unit tests for newly added FastAPI endpoints: Intelligence, AI, Hyperopt, Protections, and Decision Engine."""

from fastapi.testclient import TestClient
from trader.api.app import app

client = TestClient(app)


def test_ai_health_and_analysis_endpoints():
    # 1. AI Health
    res_h = client.get("/api/v1/ai/health")
    assert res_h.status_code == 200
    h_data = res_h.json()
    assert "status" in h_data
    assert "provider" in h_data

    # 2. News Analysis
    res_news = client.post("/api/v1/ai/analyse-news", json={
        "headline": "Infosys secures $1.5 billion cloud transformation deal with record profit expansion",
        "symbol": "INFY"
    })
    assert res_news.status_code == 200
    n_data = res_news.json()
    assert n_data["symbol"] == "INFY"
    assert n_data["sentiment_score"] > 0.0

    # 3. Signal Explanation
    res_sig = client.post("/api/v1/ai/explain-signal", json={
        "symbol": "INFY",
        "strategy_name": "momentum_breakout",
        "side": "BUY",
        "price": 1600.0,
        "stop_loss": 1560.0,
        "target": 1680.0,
        "indicators": {"rsi_14": 62.5}
    })
    assert res_sig.status_code == 200
    sig_data = res_sig.json()
    assert "thesis" in sig_data
    assert sig_data["confidence_score"] > 0.5


def test_intelligence_endpoints():
    # 1. Record Announcement
    res_ann = client.post("/api/v1/intelligence/announcements", json={
        "symbol": "TCS",
        "headline": "TCS reports strong quarterly results with net profit surges",
        "source": "NSE_CORP"
    })
    assert res_ann.status_code == 200

    # 2. Query News
    res_news = client.get("/api/v1/intelligence/news?limit=10")
    assert res_news.status_code == 200
    assert isinstance(res_news.json(), list)

    # 3. Query Summary
    res_sum = client.get("/api/v1/intelligence/summary")
    assert res_sum.status_code == 200
    assert "overall_sentiment_score" in res_sum.json()

    # 4. Query Symbol Intelligence
    res_sym = client.get("/api/v1/intelligence/symbols/TCS")
    assert res_sym.status_code == 200
    assert res_sym.json()["symbol"] == "TCS"


def test_strategies_audit_and_protections_endpoints():
    # 1. Lookahead Audit
    res_audit = client.post("/api/v1/strategies/lookahead-audit", json={
        "symbol": "INFY",
        "strategy_name": "baseline_swing"
    })
    assert res_audit.status_code == 200
    audit_data = res_audit.json()
    assert "is_clean" in audit_data

    # 2. Protections Status
    res_prot = client.get("/api/v1/strategies/protections")
    assert res_prot.status_code == 200
    assert "is_locked" in res_prot.json()


def test_decision_evaluate_endpoint():
    res_dec = client.post("/api/v1/decision/evaluate", json={
        "symbol": "INFY",
        "price": 1600.0,
        "stop_loss": 1550.0,
        "target": 1700.0,
        "strategy_name": "baseline_swing"
    })
    assert res_dec.status_code == 200
    dec_data = res_dec.json()
    assert dec_data["symbol"] == "INFY"
    assert "action" in dec_data
    assert "composite_score" in dec_data
    assert dec_data["human_confirmation_required"] is True

