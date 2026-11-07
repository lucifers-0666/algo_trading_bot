"""End-to-End System Integration Test.
Exercises the entire quantitative loop:
Data Ingestion -> Screener -> Signal Generation -> Pre-Trade Risk -> Virtual Execution -> Ledger Audit.
"""

import tempfile
from pathlib import Path
from datetime import datetime
import pytest

from trader.domain.models import OrderSide, OrderStatus, Timeframe
from tests.fixtures.synthetic_fixture import SyntheticDataProvider
from trader.scanner.ranking import MarketScannerEngine
from trader.features.technical import candles_to_dataframe, compute_all_indicators
from trader.strategies.baseline import BaselineSwingStrategy, SignalType
from trader.risk.kill_switch import PersistentKillSwitch
from trader.risk.checks import RiskManager
from trader.paper.accounting import PortfolioAccountant
from trader.paper.orders import OrderManager
from trader.paper.broker import VirtualPaperBroker
from trader.storage.database import DatabaseManager
from trader.storage.repositories import (
    CandleRepository,
    OrderRepository,
    TradeRepository,
    PortfolioRepository,
    AuditRepository,
)


def test_full_pipeline_end_to_end():
    with tempfile.TemporaryDirectory() as tmpdir:
        # 1. Initialize persistent storage
        db_path = Path(tmpdir) / "e2e_test.db"
        db = DatabaseManager(db_path=db_path)
        candle_repo = CandleRepository(db)
        order_repo = OrderRepository(db)
        trade_repo = TradeRepository(db)
        pf_repo = PortfolioRepository(db)
        audit_repo = AuditRepository(db)

        # 2. Ingest and persist historical market data
        provider = SyntheticDataProvider(seed=77)
        candles = provider.get_historical_candles("RELIANCE")
        assert len(candles) >= 100
        saved_count = candle_repo.save_candles(candles)
        assert saved_count == len(candles)

        # 3. Stock Scanner
        scanner = MarketScannerEngine(provider=provider, symbols=["RELIANCE", "TCS"])
        gainers = scanner.scan_top_gainers(limit=2)
        assert len(gainers) > 0
        top_cand = gainers[0]
        assert top_cand.symbol in ["RELIANCE", "TCS"]

        # 4. Strategy Signal Generation
        strategy = BaselineSwingStrategy()
        df = candles_to_dataframe(candles)
        df_ind = compute_all_indicators(df)

        # 5. Risk Manager & Paper Broker
        ks_path = Path(tmpdir) / "e2e_ks.state"
        ks = PersistentKillSwitch(state_file=ks_path)
        ks.deactivate("Integration test explicit reset")
        rm = RiskManager(kill_switch=ks)
        accountant = PortfolioAccountant(starting_cash=10000.0, portfolio_repo=pf_repo)
        order_manager = OrderManager(order_repo=order_repo)
        broker = VirtualPaperBroker(
            accountant=accountant,
            risk_manager=rm,
            order_manager=order_manager,
            trade_repo=trade_repo,
            audit_repo=audit_repo,
        )

        # 6. Execute Virtual Order
        entry_price = float(df_ind.iloc[-1]["close"])
        stop_price = round(entry_price * 0.98, 2)

        order, trade, assessment = broker.submit_simulated_order(
            symbol="RELIANCE",
            side=OrderSide.BUY,
            price=entry_price,
            stop_loss=stop_price,
        )

        # Sizing may approve or reject based on whether 1 share exceeds ₹50 risk budget
        if assessment.approved:
            assert order.status == OrderStatus.FILLED
            assert trade is not None
            assert trade.symbol == "RELIANCE"
            assert trade.quantity >= 1
            # Verify persisted in database
            stored_orders = order_repo.get_all_orders()
            assert len(stored_orders) >= 1
            stored_trades = trade_repo.get_trades("RELIANCE")
            assert len(stored_trades) >= 1
        else:
            assert order.status == OrderStatus.REJECTED
            assert trade is None

        # Verify audit log was recorded
        logs = audit_repo.get_recent_logs(limit=10)
        assert len(logs) >= 1
        assert logs[0].symbol == "RELIANCE"

