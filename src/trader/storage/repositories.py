"""Data Access Repositories for SQLite Persistence.
Provides strongly-typed CRUD operations for candles, orders, trades, portfolio, and audit logs.
"""

import json
from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import uuid4

from trader.domain.models import (
    Candle,
    Instrument,
    Order,
    Trade,
    PortfolioState,
    AuditLog,
    DataSource,
    Timeframe,
    OrderSide,
    OrderType,
    OrderStatus,
    IST,
)
from trader.storage.database import DatabaseManager


class CandleRepository:
    def __init__(self, db: DatabaseManager):
        self.db = db

    def save_candles(self, candles: List[Candle]) -> int:
        if not candles:
            return 0

        conn = self.db.get_connection()
        inserted = 0
        try:
            conn.execute("BEGIN TRANSACTION;")
            query = """
            INSERT INTO candles (
                exchange, symbol, timestamp, interval, open, high, low, close, volume, turnover, source, received_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(exchange, symbol, timestamp, interval) DO UPDATE SET
                open = excluded.open,
                high = excluded.high,
                low = excluded.low,
                close = excluded.close,
                volume = excluded.volume,
                turnover = excluded.turnover,
                received_at = excluded.received_at;
            """
            params = [
                (
                    c.exchange,
                    c.symbol,
                    c.timestamp.isoformat(),
                    c.interval.value,
                    c.open,
                    c.high,
                    c.low,
                    c.close,
                    c.volume,
                    c.turnover,
                    c.source.value,
                    c.received_at.isoformat(),
                )
                for c in candles
            ]
            cursor = conn.executemany(query, params)
            conn.execute("COMMIT;")
            inserted = len(candles)
        except Exception:
            conn.execute("ROLLBACK;")
            raise
        finally:
            conn.close()
        return inserted

    def get_candles(
        self,
        symbol: str,
        timeframe: Timeframe = Timeframe.DAILY,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[Candle]:
        conn = self.db.get_connection()
        try:
            query = "SELECT * FROM candles WHERE symbol = ? AND interval = ?"
            params: List[Any] = [symbol.strip().upper(), timeframe.value]

            if start_date:
                query += " AND timestamp >= ?"
                params.append(start_date.isoformat())
            if end_date:
                query += " AND timestamp <= ?"
                params.append(end_date.isoformat())

            query += " ORDER BY timestamp ASC"
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()

            candles = []
            for r in rows:
                c = Candle(
                    exchange=r["exchange"],
                    symbol=r["symbol"],
                    timestamp=r["timestamp"],
                    interval=Timeframe(r["interval"]),
                    open=r["open"],
                    high=r["high"],
                    low=r["low"],
                    close=r["close"],
                    volume=r["volume"],
                    turnover=r["turnover"],
                    source=DataSource(r["source"]),
                    received_at=r["received_at"],
                )
                candles.append(c)
            return candles
        finally:
            conn.close()

    def get_distinct_symbols(self) -> List[str]:
        conn = self.db.get_connection()
        try:
            cursor = conn.execute("SELECT DISTINCT symbol FROM candles ORDER BY symbol ASC")
            return [r["symbol"] for r in cursor.fetchall()]
        finally:
            conn.close()


class OrderRepository:
    def __init__(self, db: DatabaseManager):
        self.db = db

    def save_order(self, order: Order) -> None:
        conn = self.db.get_connection()
        try:
            query = """
            INSERT INTO orders (
                order_id, symbol, side, order_type, quantity, limit_price, stop_price,
                status, rejection_reason, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(order_id) DO UPDATE SET
                status = excluded.status,
                rejection_reason = excluded.rejection_reason,
                updated_at = excluded.updated_at;
            """
            conn.execute(
                query,
                (
                    order.order_id,
                    order.symbol,
                    order.side.value,
                    order.order_type.value,
                    order.quantity,
                    order.limit_price,
                    order.stop_price,
                    order.status.value,
                    order.rejection_reason,
                    order.created_at.isoformat(),
                    order.updated_at.isoformat(),
                ),
            )
        finally:
            conn.close()

    def get_order(self, order_id: str) -> Optional[Order]:
        conn = self.db.get_connection()
        try:
            cursor = conn.execute("SELECT * FROM orders WHERE order_id = ?", (order_id,))
            r = cursor.fetchone()
            if not r:
                return None
            return Order(
                order_id=r["order_id"],
                symbol=r["symbol"],
                side=OrderSide(r["side"]),
                order_type=OrderType(r["order_type"]),
                quantity=r["quantity"],
                limit_price=r["limit_price"],
                stop_price=r["stop_price"],
                status=OrderStatus(r["status"]),
                rejection_reason=r["rejection_reason"],
                created_at=r["created_at"],
                updated_at=r["updated_at"],
            )
        finally:
            conn.close()

    def get_all_orders(self, limit: int = 100) -> List[Order]:
        conn = self.db.get_connection()
        try:
            cursor = conn.execute("SELECT * FROM orders ORDER BY created_at DESC LIMIT ?", (limit,))
            orders = []
            for r in cursor.fetchall():
                orders.append(
                    Order(
                        order_id=r["order_id"],
                        symbol=r["symbol"],
                        side=OrderSide(r["side"]),
                        order_type=OrderType(r["order_type"]),
                        quantity=r["quantity"],
                        limit_price=r["limit_price"],
                        stop_price=r["stop_price"],
                        status=OrderStatus(r["status"]),
                        rejection_reason=r["rejection_reason"],
                        created_at=r["created_at"],
                        updated_at=r["updated_at"],
                    )
                )
            return orders
        finally:
            conn.close()


class TradeRepository:
    def __init__(self, db: DatabaseManager):
        self.db = db

    def save_trade(self, trade: Trade) -> None:
        conn = self.db.get_connection()
        try:
            query = """
            INSERT INTO trades (
                trade_id, order_id, symbol, side, quantity, price, slippage_inr,
                brokerage_inr, stt_inr, exchange_charges_inr, gst_inr, stamp_duty_inr,
                total_costs_inr, net_value_inr, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(trade_id) DO NOTHING;
            """
            conn.execute(
                query,
                (
                    trade.trade_id,
                    trade.order_id,
                    trade.symbol,
                    trade.side.value,
                    trade.quantity,
                    trade.price,
                    trade.slippage_inr,
                    trade.brokerage_inr,
                    trade.stt_inr,
                    trade.exchange_charges_inr,
                    trade.gst_inr,
                    trade.stamp_duty_inr,
                    trade.total_costs_inr,
                    trade.net_value_inr,
                    trade.timestamp.isoformat(),
                ),
            )
        finally:
            conn.close()

    def get_trades(self, symbol: Optional[str] = None, limit: int = 100) -> List[Trade]:
        conn = self.db.get_connection()
        try:
            if symbol:
                cursor = conn.execute(
                    "SELECT * FROM trades WHERE symbol = ? ORDER BY timestamp DESC LIMIT ?",
                    (symbol.strip().upper(), limit),
                )
            else:
                cursor = conn.execute(
                    "SELECT * FROM trades ORDER BY timestamp DESC LIMIT ?", (limit,)
                )
            trades = []
            for r in cursor.fetchall():
                trades.append(
                    Trade(
                        trade_id=r["trade_id"],
                        order_id=r["order_id"],
                        symbol=r["symbol"],
                        side=OrderSide(r["side"]),
                        quantity=r["quantity"],
                        price=r["price"],
                        slippage_inr=r["slippage_inr"],
                        brokerage_inr=r["brokerage_inr"],
                        stt_inr=r["stt_inr"],
                        exchange_charges_inr=r["exchange_charges_inr"],
                        gst_inr=r["gst_inr"],
                        stamp_duty_inr=r["stamp_duty_inr"],
                        total_costs_inr=r["total_costs_inr"],
                        net_value_inr=r["net_value_inr"],
                        timestamp=r["timestamp"],
                    )
                )
            return trades
        finally:
            conn.close()


class PortfolioRepository:
    def __init__(self, db: DatabaseManager):
        self.db = db

    def save_snapshot(self, state: PortfolioState) -> None:
        conn = self.db.get_connection()
        try:
            query = """
            INSERT INTO portfolio_snapshots (
                starting_cash, cash_balance, reserved_margin, realized_pnl,
                unrealized_pnl, total_equity, peak_equity, max_drawdown_pct,
                open_positions_count, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            conn.execute(
                query,
                (
                    state.starting_cash,
                    state.cash_balance,
                    state.reserved_margin,
                    state.realized_pnl,
                    state.unrealized_pnl,
                    state.total_equity,
                    state.peak_equity,
                    state.max_drawdown_pct,
                    state.open_positions_count,
                    state.updated_at.isoformat(),
                ),
            )
        finally:
            conn.close()

    def get_latest_snapshot(self) -> Optional[PortfolioState]:
        conn = self.db.get_connection()
        try:
            cursor = conn.execute(
                "SELECT * FROM portfolio_snapshots ORDER BY id DESC LIMIT 1"
            )
            r = cursor.fetchone()
            if not r:
                return None
            return PortfolioState(
                starting_cash=r["starting_cash"],
                cash_balance=r["cash_balance"],
                reserved_margin=r["reserved_margin"],
                realized_pnl=r["realized_pnl"],
                unrealized_pnl=r["unrealized_pnl"],
                total_equity=r["total_equity"],
                peak_equity=r["peak_equity"],
                max_drawdown_pct=r["max_drawdown_pct"],
                open_positions_count=r["open_positions_count"],
                updated_at=r["updated_at"],
            )
        finally:
            conn.close()


class AuditRepository:
    def __init__(self, db: DatabaseManager):
        self.db = db

    def log_event(
        self,
        event_type: str,
        symbol: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> AuditLog:
        event = AuditLog(
            event_id=f"evt_{uuid4().hex[:12]}",
            event_type=event_type,
            symbol=symbol,
            details=details or {},
            timestamp=datetime.now(IST),
        )
        conn = self.db.get_connection()
        try:
            query = """
            INSERT INTO audit_logs (event_id, event_type, symbol, details_json, timestamp)
            VALUES (?, ?, ?, ?, ?)
            """
            conn.execute(
                query,
                (
                    event.event_id,
                    event.event_type,
                    event.symbol,
                    json.dumps(event.details),
                    event.timestamp.isoformat(),
                ),
            )
        finally:
            conn.close()
        return event

    def get_recent_logs(self, limit: int = 50) -> List[AuditLog]:
        conn = self.db.get_connection()
        try:
            cursor = conn.execute(
                "SELECT * FROM audit_logs ORDER BY timestamp DESC LIMIT ?", (limit,)
            )
            logs = []
            for r in cursor.fetchall():
                logs.append(
                    AuditLog(
                        event_id=r["event_id"],
                        event_type=r["event_type"],
                        symbol=r["symbol"],
                        details=json.loads(r["details_json"]),
                        timestamp=r["timestamp"],
                    )
                )
            return logs
        finally:
            conn.close()

