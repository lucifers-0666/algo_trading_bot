from fastapi.testclient import TestClient

from trader.api.app import app

client = TestClient(app)


def test_health_endpoint_is_paper_only():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["mode"] == "paper"
    assert payload["service"] == "indian-ai-paper-trader-api"
    assert "timestamp" in payload


def test_status_does_not_claim_live_data_or_order_routing():
    response = client.get("/api/v1/status")
    assert response.status_code == 200
    payload = response.json()
    assert payload["mode"] == "paper"
    assert payload["real_order_routing_enabled"] is False
    assert payload["market_data_status"] == "not_configured"
