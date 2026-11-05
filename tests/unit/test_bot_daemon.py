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


def test_stale_or_missing_quote_refuses_stop_loss_execution():
    from trader.api.app import auto_trader, accountant
    from trader.domain.models import Position, Quote, DataSource
    import pytz

    # Manually insert an open position with stop loss at 1000
    pos = Position(
        symbol="STALETEST",
        quantity=10,
        average_price=1100.0,
        current_price=1100.0,
        stop_loss=1000.0,
        target=1200.0,
        entry_time=datetime.now(IST),
    )
    accountant.positions["STALETEST"] = pos

    # Create mock provider where get_latest_quote raises error or returns stale quote
    class FailingProvider:
        is_configured = True
        _is_connected = True
        def get_latest_quote(self, s):
            raise RuntimeError("Live connection timeout")
        def get_historical_candles(self, s, timeframe=None):
            # Old candle close was 950 (which would have triggered stop loss if fallen back to!)
            return [Candle(
                exchange="NSE",
                symbol="STALETEST",
                timestamp=datetime(2025, 1, 1, 15, 30, tzinfo=IST),
                interval=Timeframe.DAILY,
                open=960, high=970, low=940, close=950, volume=100000,
                source=DataSource.HISTORICAL
            )]

    orig_provider = auto_trader.scanner_engine.provider
    try:
        auto_trader.scanner_engine.provider = FailingProvider()
        closed = auto_trader._evaluate_open_positions()
        # Verify NO position was closed on historical fallback
        assert len(closed) == 0
        assert "STALETEST" in accountant.positions
    finally:
        auto_trader.scanner_engine.provider = orig_provider
        accountant.positions.pop("STALETEST", None)


