import pytest
from fastapi.testclient import TestClient
from trader.api.app import app, kill_switch

client = TestClient(app)


@pytest.fixture(autouse=True)
def ensure_kill_switch_reset():
    kill_switch.deactivate("Reset for API test")
    yield
    kill_switch.deactivate("Cleanup after API test")


def test_market_session_endpoint():
    res = client.get("/api/v1/market/session")
    assert res.status_code == 200
    data = res.json()
    assert "is_open" in data
    assert "regular_hours" in data
    assert "is_trading_day" in data
    assert "next_session_open" in data


def test_data_health_endpoint():
    res = client.get("/api/v1/data/health")
    assert res.status_code == 200
    data = res.json()
    assert "data_source_label" in data
    assert "feed_status" in data
    assert "latency_seconds" in data


def test_scanner_candidates_endpoint():
    res = client.get("/api/v1/scanner/candidates?category=top_gainers")
    assert res.status_code == 200
    candidates = res.json()
    assert isinstance(candidates, list)
    if candidates:
        c = candidates[0]
        assert "symbol" in c
        assert "latest_price" in c
        assert "scan_category" in c


def test_instruments_and_candles_endpoint():
    res = client.get("/api/v1/instruments")
    assert res.status_code == 200
    insts = res.json()
    assert len(insts) >= 5

    res_candles = client.get("/api/v1/instruments/INFY/candles?limit=50")
    assert res_candles.status_code == 200
    c_data = res_candles.json()
    assert c_data["symbol"] == "INFY"
    assert "candles" in c_data
    assert "regime" in c_data
    assert len(c_data["candles"]) > 0


def test_portfolio_and_positions_endpoints():
    res = client.get("/api/v1/portfolio")
    assert res.status_code == 200
    port = res.json()
    assert "starting_cash" in port
    assert "cash_balance" in port
    assert "total_equity" in port

    res_pos = client.get("/api/v1/portfolio/positions")
    assert res_pos.status_code == 200
    assert isinstance(res_pos.json(), list)


def test_paper_trading_proposal_and_execution():
    # 1. Propose order
    proposal_payload = {
        "symbol": "INFY",
        "side": "BUY",
        "price": 1600.0,
        "stop_loss": 1550.0,
    }
    res_prop = client.post("/api/v1/paper/orders", json=proposal_payload)
    assert res_prop.status_code == 200
    prop_data = res_prop.json()
    assert prop_data["symbol"] == "INFY"
    assert "approved" in prop_data

    # 2. Execute simulated paper trade
    exec_payload = {
        "symbol": "INFY",
        "side": "BUY",
        "price": 1600.0,
        "stop_loss": 1550.0,
        "quantity": 1,
    }
    res_exec = client.post("/api/v1/paper/execute", json=exec_payload)
    assert res_exec.status_code == 200
    exec_data = res_exec.json()
    assert "success" in exec_data
    assert "order" in exec_data


def test_backtest_run_and_comparison_endpoints():
    bt_payload = {
        "strategy_name": "baseline_swing",
        "symbols": ["INFY", "TCS"],
        "initial_capital": 10000.0,
    }
    res_bt = client.post("/api/v1/backtests/run", json=bt_payload)
    assert res_bt.status_code == 200
    bt_data = res_bt.json()
    assert "metrics" in bt_data
    assert "equity_curve" in bt_data

    # Comparison endpoint
    res_comp = client.get("/api/v1/backtests/comparison?symbols=INFY,TCS")
    assert res_comp.status_code == 200
    comp_data = res_comp.json()
    assert "comparison_table" in comp_data
    assert len(comp_data["comparison_table"]) == 3


def test_kill_switch_api_endpoint():
    res = client.post("/api/v1/risk/kill-switch", json={"action": "engage", "reason": "Testing API"})
    assert res.status_code == 200
    assert res.json()["active"] is True

    res2 = client.post("/api/v1/risk/kill-switch", json={"action": "disengage", "reason": "Restoring API"})
    assert res2.status_code == 200
    assert res2.json()["active"] is False
