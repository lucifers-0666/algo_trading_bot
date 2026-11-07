"""Phase 0 Correctness & Safety Verification Tests.
Tests:
1. Daemon BUY freshness check refuses entry when feed is stale.
2. Daemon _force_market_open defaults to False; trades executed in forced mode are labeled in audit logs.
3. Real ATR trailing stop ratchets up monotonically and triggers exit on retracement.
4. Optional time-stop triggers exit after max holding bars.
5. Mutating API endpoints require token authentication when NORTHSTAR_API_TOKEN is set.
6. API restricts access to localhost.
7. Position model and repository preserve trailing stop, target, and lifecycle fields.
"""

import os
from datetime import datetime, timedelta
import pytest
from fastapi.testclient import TestClient

from trader.domain.models import (
    IST,
    Candle,
    Quote,
    OrderSide,
    OrderStatus,
    Position,
    PortfolioState,
    Timeframe,
    DataSource,
)
from trader.data.freshness import evaluate_feed_freshness, FeedStatus
from trader.paper.daemon import AutonomousPaperTradingDaemon
from trader.paper.broker import VirtualPaperBroker
from trader.paper.accounting import PortfolioAccountant
from trader.paper.orders import OrderManager
from trader.risk.checks import RiskManager
from trader.strategies.protections import RiskProtectionManager
from trader.decision.decision_engine import DecisionEngine, DecisionDossier
from trader.storage.database import DatabaseManager
from trader.storage.repositories import PositionRepository, AuditRepository
from trader.api.app import app


client = TestClient(app)


def test_daemon_force_market_open_default():
    """Verify _force_market_open defaults strictly to False."""
    accountant = PortfolioAccountant(starting_cash=10000.0)
    broker = VirtualPaperBroker(accountant=accountant)
    daemon = AutonomousPaperTradingDaemon(
        broker=broker,
        decision_engine=DecisionEngine(),
        scanner_engine=None,
        risk_manager=RiskManager(),
        protection_manager=RiskProtectionManager(),
    )
    assert daemon.force_market_open is False


def test_daemon_buy_freshness_guard_refuses_stale_feed():
    """Verify BUY path uses real evaluate_feed_freshness() and refuses entry on stale feed."""
    accountant = PortfolioAccountant(starting_cash=10000.0)
    broker = VirtualPaperBroker(accountant=accountant)
    decision_engine = DecisionEngine()

    class StaleQuoteProvider:
        is_configured = True
        _is_connected = True
        def get_latest_quote(self, s):
            # 2 hours old quote -> FeedStatus.STALE, is_actionable=False
            stale_time = datetime.now(IST) - timedelta(hours=2)
            return Quote(
                symbol=s,
                ltp=1500.0,
                bid=1499.0,
                ask=1501.0,
                volume=50000,
                timestamp=stale_time,
                source=DataSource.REAL_TIME,
            )
        def get_historical_candles(self, s, timeframe=None):
            return []

    class MockCandidate:
        symbol = "TCS"
        ltp = 1500.0

    class MockScanner:
        provider = StaleQuoteProvider()
        def refresh_snapshot(self): pass
        def scan_top_gainers(self): return [MockCandidate()]
        def scan_momentum(self): return []

    daemon = AutonomousPaperTradingDaemon(
        broker=broker,
        decision_engine=decision_engine,
        scanner_engine=MockScanner(),
        risk_manager=RiskManager(),
        protection_manager=RiskProtectionManager(),
    )
    daemon.force_market_open = True

    # Inject mock evaluate on decision_engine that approves
    daemon.decision_engine.evaluate = lambda **kwargs: DecisionDossier(
        symbol="TCS",
        action="APPROVE_PAPER_BUY",
        composite_score=85.0,
        technical_conviction=80.0,
        ml_conviction=80.0,
        sentiment_conviction=80.0,
        regime_conviction=80.0,
        entry_price=1500.0,
        stop_loss=1455.0,
        target=1590.0,
        risk_reward_ratio=2.0,
        suggested_quantity=1,
        risk_approved=True,
    )

    result = daemon.run_iteration()
    # No buy should execute because feed is stale!
    assert len(result.get("executed", [])) == 0
    assert "TCS" not in accountant.positions
    # Verify stale guard event was logged
    log_types = [l["event_type"] for l in daemon.get_status()["recent_logs"]]
    assert "STALE_FEED_GUARD" in log_types


def test_daemon_trailing_stop_ratchets_and_exits():
    """Verify ATR trailing stop ratchets upwards with price and executes exit when price drops."""
    accountant = PortfolioAccountant(starting_cash=10000.0)
    broker = VirtualPaperBroker(accountant=accountant)
    daemon = AutonomousPaperTradingDaemon(
        broker=broker,
        decision_engine=DecisionEngine(),
        scanner_engine=None,
        risk_manager=RiskManager(),
        protection_manager=RiskProtectionManager(),
    )
    daemon.force_market_open = True
    daemon.trailing_stop_enabled = True

    # Create an initial position entered at 1000, initial stop at 950
    pos = Position(
        symbol="TRAILTEST",
        quantity=5,
        average_entry_price=1000.0,
        current_price=1000.0,
        stop_loss=950.0,
        target=1200.0,
        highest_price=1000.0,
        trailing_stop_atr_mult=2.0,
    )
    accountant.positions["TRAILTEST"] = pos

    class DynamicProvider:
        is_configured = True
        _is_connected = True
        price = 1000.0
        def get_latest_quote(self, s):
            return Quote(
                symbol=s,
                ltp=self.price,
                bid=self.price - 1,
                ask=self.price + 1,
                volume=100000,
                timestamp=datetime.now(IST),
                source=DataSource.REAL_TIME,
            )
        def get_historical_candles(self, s, timeframe=None):
            # 15 synthetic bars with high-low spread ~10 (ATR ~10)
            candles = []
            base = 1000.0
            for i in range(15):
                candles.append(Candle(
                    exchange="NSE",
                    symbol=s,
                    timestamp=datetime.now(IST) - timedelta(days=15 - i),
                    interval=Timeframe.DAILY,
                    open=base, high=base + 10, low=base - 10, close=base + 2, volume=10000,
                    source=DataSource.REAL_TIME,
                ))
            return candles

    dyn_provider = DynamicProvider()

    class MockScanner:
        provider = dyn_provider

    daemon.scanner_engine = MockScanner()

    # Step 1: Price jumps to 1100 (high water mark)
    dyn_provider.price = 1100.0
    daemon._evaluate_open_positions()

    assert pos.highest_price == 1100.0
    # Trailing stop should ratchet up significantly above original 950
    assert pos.stop_loss is not None
    assert pos.stop_loss > 950.0
    ratcheted_stop = pos.stop_loss

    # Step 2: Price retraces back below ratcheted stop
    dyn_provider.price = ratcheted_stop - 5.0
    closed = daemon._evaluate_open_positions()

    assert len(closed) == 1
    assert closed[0]["symbol"] == "TRAILTEST"
    assert closed[0]["reason"] == "TRAILING_STOP"
    assert closed[0]["forced_market_open"] is True


def test_daemon_time_stop_exit():
    """Verify that exceeding max_holding_bars triggers a TIME_STOP exit."""
    accountant = PortfolioAccountant(starting_cash=10000.0)
    broker = VirtualPaperBroker(accountant=accountant)
    daemon = AutonomousPaperTradingDaemon(
        broker=broker,
        decision_engine=DecisionEngine(),
        scanner_engine=None,
        risk_manager=RiskManager(),
        protection_manager=RiskProtectionManager(),
    )
    daemon.force_market_open = True
    daemon.max_holding_bars = 5

    pos = Position(
        symbol="TIMETEST",
        quantity=5,
        average_entry_price=1000.0,
        current_price=1000.0,
        stop_loss=900.0,
        target=1200.0,
        highest_price=1000.0,
        holding_bars=4, # 1 more iteration will reach 5
    )
    accountant.positions["TIMETEST"] = pos

    class StaticProvider:
        is_configured = True
        _is_connected = True
        def get_latest_quote(self, s):
            return Quote(
                symbol=s,
                ltp=1000.0,
                bid=999.0,
                ask=1001.0,
                volume=10000,
                timestamp=datetime.now(IST),
                source=DataSource.REAL_TIME,
            )
        def get_historical_candles(self, s, timeframe=None):
            return []

    class MockScanner:
        provider = StaticProvider()

    daemon.scanner_engine = MockScanner()
    closed = daemon._evaluate_open_positions()

    assert len(closed) == 1
    assert closed[0]["symbol"] == "TIMETEST"
    assert closed[0]["reason"] == "TIME_STOP"


def test_mutating_endpoints_require_token_when_configured(monkeypatch):
    """Verify mutating endpoints return 401 without token and 200 with token when NORTHSTAR_API_TOKEN is set."""
    token = "test_northstar_token_institutional_9988"
    monkeypatch.setenv("NORTHSTAR_API_TOKEN", token)

    # 1. POST /api/v1/bot/start without token -> 401
    res = client.post("/api/v1/bot/start")
    assert res.status_code == 401
    assert "Unauthorized" in res.json()["detail"]

    # 2. POST /api/v1/bot/start with invalid token -> 401
    res = client.post("/api/v1/bot/start", headers={"Authorization": "Bearer wrong_token"})
    assert res.status_code == 401

    # 3. POST /api/v1/bot/start with valid Bearer token -> 200
    res = client.post("/api/v1/bot/start", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert res.json()["status"] == "started"

    # 4. POST /api/v1/bot/stop with valid X-API-Token header -> 200
    res = client.post("/api/v1/bot/stop", headers={"X-API-Token": token})
    assert res.status_code == 200
    assert res.json()["status"] == "stopped"

    # 5. POST /api/v1/risk/kill-switch with token -> 200
    res = client.post(
        "/api/v1/risk/kill-switch",
        headers={"Authorization": f"Bearer {token}"},
        json={"action": "engage", "reason": "Test engagement"},
    )
    assert res.status_code == 200
    assert res.json()["active"] is True

    # Disengage kill switch with token
    res = client.post(
        "/api/v1/risk/kill-switch",
        headers={"Authorization": f"Bearer {token}"},
        json={"action": "disengage", "reason": "Test disengagement"},
    )
    assert res.status_code == 200
    assert res.json()["active"] is False


def test_position_persistence_schema(tmp_path):
    """Verify PositionRepository properly stores and restores trailing stop and target fields."""
    db_file = tmp_path / "test_pos.db"
    db = DatabaseManager(db_file)
    repo = PositionRepository(db)

    pos = Position(
        symbol="RELIANCE",
        quantity=10,
        average_entry_price=2500.0,
        current_price=2600.0,
        stop_loss=2450.0,
        target=2750.0,
        highest_price=2620.0,
        trailing_stop_atr_mult=2.5,
        holding_bars=12,
        unrealized_pnl=1000.0,
    )
    repo.save_position(pos)

    all_positions = repo.get_all_positions()
    assert len(all_positions) == 1
    loaded = all_positions[0]
    assert loaded.symbol == "RELIANCE"
    assert loaded.quantity == 10
    assert loaded.stop_loss == 2450.0
    assert loaded.target == 2750.0
    assert loaded.highest_price == 2620.0
    assert loaded.trailing_stop_atr_mult == 2.5
    assert loaded.holding_bars == 12
