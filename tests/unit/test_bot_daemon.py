"""Unit tests for Autonomous Paper Trading Daemon."""

import pytest
from datetime import datetime
from fastapi.testclient import TestClient

from trader.domain.models import IST, OrderSide, Candle, Timeframe
from trader.data.synthetic import generate_synthetic_candles
from trader.paper.daemon import AutonomousPaperTradingDaemon
from trader.api.app import app

client = TestClient(app)


def test_bot_status_endpoint():
    res = client.get("/api/v1/bot/status")
    assert res.status_code == 200
    data = res.json()
    assert "is_running" in data
    assert "force_market_open" in data
    assert "cash_balance" in data
    assert "recent_logs" in data


def test_bot_start_stop_lifecycle():
    # Start bot
    res = client.post("/api/v1/bot/start")
    assert res.status_code == 200
    assert res.json()["status"] == "started"

    status_res = client.get("/api/v1/bot/status")
    assert status_res.json()["is_running"] is True

    # Stop bot
    stop_res = client.post("/api/v1/bot/stop")
    assert stop_res.status_code == 200
    assert stop_res.json()["status"] == "stopped"

    status_res2 = client.get("/api/v1/bot/status")
    assert status_res2.json()["is_running"] is False


def test_bot_single_step_execution():
    res = client.post("/api/v1/bot/step")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "completed"
    assert "result" in data
    assert "status" in data["result"]


def test_bot_config_update():
    res = client.post("/api/v1/bot/config", json={"force_market_open": True, "interval": 45})
    assert res.status_code == 200
    data = res.json()
    assert data["force_market_open"] is True
    assert data["scan_interval_seconds"] == 45
