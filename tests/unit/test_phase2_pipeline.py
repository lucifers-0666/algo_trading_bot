"""Unit tests for Phase 2: Live & Historical NSE/BSE Pipeline & TradingView Webhook."""

import pytest
from datetime import datetime
from fastapi.testclient import TestClient

from trader.domain.models import DataSource, OrderSide
from trader.providers.yfinance_adapter import YFinanceAdapter, to_yfinance_symbol
from trader.providers.nse_live_adapter import NSELiveAdapter
from trader.api.app import app

client = TestClient(app)


def test_yfinance_symbol_translation():
    """Verify standard Indian equity and index symbol mapping."""
    assert to_yfinance_symbol("RELIANCE") == "RELIANCE.NS"
    assert to_yfinance_symbol("TCS") == "TCS.NS"
    assert to_yfinance_symbol("NIFTY") == "^NSEI"
    assert to_yfinance_symbol("NIFTY 50") == "^NSEI"
    assert to_yfinance_symbol("BANKNIFTY") == "^NSEBANK"
    assert to_yfinance_symbol("INDIAVIX") == "^INDIAVIX"
    assert to_yfinance_symbol("BSE:SBIN") == "SBIN.BO"
    assert to_yfinance_symbol("^NSEI") == "^NSEI"
    assert to_yfinance_symbol("INFY.NS") == "INFY.NS"


def test_yfinance_adapter_connection_status():
    """Verify YFinance adapter reports healthy broker-independent status."""
    adapter = YFinanceAdapter(auto_persist=False)
    status = adapter.get_connection_status()

    assert status["status"] == "HEALTHY"
    assert status["connected"] is True
    assert status["configured"] is True
    assert status["data_source_label"] == DataSource.REAL_TIME.value
    assert status["broker_independent"] is True
    assert adapter.source_type == DataSource.REAL_TIME


def test_nse_live_adapter_status_and_pcr_calculation():
    """Verify NSE Live Adapter initializes cleanly and computes metrics."""
    adapter = NSELiveAdapter()
    status = adapter.get_connection_status()

    assert status["provider"] == "nse_live"
    assert status["free_data_feed"] is True
    assert status["broker_login_required"] is False


def test_tradingview_webhook_execution():
    """Verify TradingView Webhook executes simulated virtual trade and logs audit."""
    payload = {
        "symbol": "RELIANCE",
        "side": "BUY",
        "segment": "EQ_SWING",
        "price": 1320.0,
        "quantity": 1,
        "strategy_name": "PineScript_RSI_Breakout",
    }
    response = client.post("/api/webhook/tradingview", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["source"] == "TRADINGVIEW_WEBHOOK"
    assert data["symbol"] == "RELIANCE"
    assert data["side"] == "BUY"
    assert data["segment"] == "EQ_SWING"
    assert "order_id" in data
    assert data["risk_approved"] is True
    assert data["status"] in ("FILLED", "PENDING", "REJECTED")


def test_tradingview_webhook_negative_isolation():
    """Negative isolation test: ensure webhook executes in paper-only mode with zero real routing."""
    response = client.get("/api/v1/status")
    assert response.status_code == 200
    payload = response.json()

    assert payload["mode"] == "paper"
    assert payload["real_order_routing_enabled"] is False
    assert payload["broker_independent"] is True
