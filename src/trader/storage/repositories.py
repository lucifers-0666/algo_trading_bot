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
    Position,
    PortfolioState,
    AuditLog,
    FinancialEvent,
    EventImpact,
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
                starting_cash, cash_balance, day_starting_equity, last_day_reset,
                reserved_margin, realized_pnl,
                unrealized_pnl, total_equity, peak_equity, max_drawdown_pct,
                open_positions_count, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            conn.execute(
                query,
                (
                    state.starting_cash,
                    state.cash_balance,
                    state.day_starting_equity,
                    state.last_day_reset,
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
            keys = r.keys()
            day_starting = r["day_starting_equity"] if "day_starting_equity" in keys else r["starting_cash"]
            last_reset = r["last_day_reset"] if "last_day_reset" in keys else ""
            return PortfolioState(
                starting_cash=r["starting_cash"],
                cash_balance=r["cash_balance"],
                day_starting_equity=day_starting,
                last_day_reset=last_reset,
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


class PositionRepository:
    """Manages persistent active equity holdings across application restarts."""

    def __init__(self, db: DatabaseManager):
        self.db = db

    def _ensure_position_schema(self, conn) -> None:
        """Ensures positions table exists and migrates columns if absent."""
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS positions (
                    symbol TEXT PRIMARY KEY,
                    quantity INTEGER NOT NULL,
                    average_entry_price REAL NOT NULL,
                    current_price REAL NOT NULL,
                    stop_loss REAL,
                    target REAL,
                    highest_price REAL DEFAULT 0.0,
                    trailing_stop_atr_mult REAL,
                    trailing_stop_pct REAL,
                    holding_bars INTEGER DEFAULT 0,
                    unrealized_pnl REAL NOT NULL DEFAULT 0.0,
                    realized_pnl REAL NOT NULL DEFAULT 0.0,
                    open_timestamp TEXT NOT NULL,
                    updated_timestamp TEXT NOT NULL
                );
                """
            )
            cursor = conn.execute("PRAGMA table_info(positions);")
            cols = {r["name"] for r in cursor.fetchall()}
            if "stop_loss" not in cols:
                conn.execute("ALTER TABLE positions ADD COLUMN stop_loss REAL;")
            if "target" not in cols:
                conn.execute("ALTER TABLE positions ADD COLUMN target REAL;")
            if "highest_price" not in cols:
                conn.execute("ALTER TABLE positions ADD COLUMN highest_price REAL DEFAULT 0.0;")
            if "trailing_stop_atr_mult" not in cols:
                conn.execute("ALTER TABLE positions ADD COLUMN trailing_stop_atr_mult REAL;")
            if "trailing_stop_pct" not in cols:
                conn.execute("ALTER TABLE positions ADD COLUMN trailing_stop_pct REAL;")
            if "holding_bars" not in cols:
                conn.execute("ALTER TABLE positions ADD COLUMN holding_bars INTEGER DEFAULT 0;")
        except Exception:
            pass

    def save_position(self, pos: Position) -> None:
        conn = self.db.get_connection()
        try:
            self._ensure_position_schema(conn)
            query = """
            INSERT INTO positions (
                symbol, quantity, average_entry_price, current_price,
                stop_loss, target, highest_price, trailing_stop_atr_mult,
                trailing_stop_pct, holding_bars,
                unrealized_pnl, realized_pnl, open_timestamp, updated_timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(symbol) DO UPDATE SET
                quantity = excluded.quantity,
                average_entry_price = excluded.average_entry_price,
                current_price = excluded.current_price,
                stop_loss = excluded.stop_loss,
                target = excluded.target,
                highest_price = excluded.highest_price,
                trailing_stop_atr_mult = excluded.trailing_stop_atr_mult,
                trailing_stop_pct = excluded.trailing_stop_pct,
                holding_bars = excluded.holding_bars,
                unrealized_pnl = excluded.unrealized_pnl,
                realized_pnl = excluded.realized_pnl,
                updated_timestamp = excluded.updated_timestamp;
            """
            conn.execute(
                query,
                (
                    pos.symbol.strip().upper(),
                    pos.quantity,
                    pos.average_entry_price,
                    pos.current_price,
                    pos.stop_loss,
                    pos.target,
                    pos.highest_price,
                    pos.trailing_stop_atr_mult,
                    pos.trailing_stop_pct,
                    pos.holding_bars,
                    pos.unrealized_pnl,
                    pos.realized_pnl,
                    pos.open_timestamp.isoformat(),
                    pos.updated_timestamp.isoformat(),
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def delete_position(self, symbol: str) -> None:
        conn = self.db.get_connection()
        try:
            conn.execute("DELETE FROM positions WHERE symbol = ?", (symbol.strip().upper(),))
            conn.commit()
        finally:
            conn.close()

    def get_all_positions(self) -> List[Position]:
        conn = self.db.get_connection()
        try:
            self._ensure_position_schema(conn)
            cursor = conn.execute("SELECT * FROM positions WHERE quantity > 0")
            positions = []
            for r in cursor.fetchall():
                keys = r.keys()
                positions.append(
                    Position(
                        symbol=r["symbol"],
                        quantity=r["quantity"],
                        average_entry_price=r["average_entry_price"],
                        current_price=r["current_price"],
                        stop_loss=r["stop_loss"] if "stop_loss" in keys else None,
                        target=r["target"] if "target" in keys else None,
                        highest_price=r["highest_price"] if "highest_price" in keys else 0.0,
                        trailing_stop_atr_mult=r["trailing_stop_atr_mult"] if "trailing_stop_atr_mult" in keys else None,
                        trailing_stop_pct=r["trailing_stop_pct"] if "trailing_stop_pct" in keys else None,
                        holding_bars=r["holding_bars"] if "holding_bars" in keys else 0,
                        unrealized_pnl=r["unrealized_pnl"],
                        realized_pnl=r["realized_pnl"],
                        open_timestamp=r["open_timestamp"],
                        updated_timestamp=r["updated_timestamp"],
                    )
                )
            return positions
        finally:
            conn.close()

    def clear_all(self) -> None:
        conn = self.db.get_connection()
        try:
            conn.execute("DELETE FROM positions")
            conn.commit()
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


class FinancialEventRepository:
    """Persistence repository for structured financial news and geopolitical events."""

    def __init__(self, db: DatabaseManager):
        self.db = db

    def save_event(self, event: FinancialEvent) -> None:
        conn = self.db.get_connection()
        try:
            query = """
            INSERT INTO financial_events (
                event_id, source, category, headline, summary, symbols,
                sentiment_score, impact_level, url, published_at, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(event_id) DO UPDATE SET
                headline = excluded.headline,
                summary = excluded.summary,
                symbols = excluded.symbols,
                sentiment_score = excluded.sentiment_score,
                impact_level = excluded.impact_level;
            """
            conn.execute(
                query,
                (
                    event.event_id,
                    event.source,
                    event.category,
                    event.headline,
                    event.summary,
                    json.dumps(event.symbols),
                    event.sentiment_score,
                    event.impact_level.value,
                    event.url,
                    event.published_at.isoformat(),
                    event.created_at.isoformat(),
                ),
            )
        finally:
            conn.close()

    def save_events(self, events: List[FinancialEvent]) -> int:
        if not events:
            return 0
        conn = self.db.get_connection()
        inserted = 0
        try:
            conn.execute("BEGIN TRANSACTION;")
            query = """
            INSERT INTO financial_events (
                event_id, source, category, headline, summary, symbols,
                sentiment_score, impact_level, url, published_at, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(event_id) DO NOTHING;
            """
            for ev in events:
                conn.execute(
                    query,
                    (
                        ev.event_id,
                        ev.source,
                        ev.category,
                        ev.headline,
                        ev.summary,
                        json.dumps(ev.symbols),
                        ev.sentiment_score,
                        ev.impact_level.value,
                        ev.url,
                        ev.published_at.isoformat(),
                        ev.created_at.isoformat(),
                    ),
                )
                inserted += 1
            conn.execute("COMMIT;")
            return inserted
        except Exception:
            conn.execute("ROLLBACK;")
            raise
        finally:
            conn.close()

    def get_recent_events(
        self, limit: int = 50, category: Optional[str] = None, symbol: Optional[str] = None
    ) -> List[FinancialEvent]:
        conn = self.db.get_connection()
        try:
            sql = "SELECT * FROM financial_events WHERE 1=1"
            params: List[Any] = []
            if category:
                sql += " AND category = ?"
                params.append(category.upper())
            if symbol:
                sql += " AND symbols LIKE ?"
                params.append(f"%{symbol.upper()}%")
            sql += " ORDER BY published_at DESC LIMIT ?"
            params.append(limit)

            cursor = conn.execute(sql, params)
            events = []
            for r in cursor.fetchall():
                symbols_list = []
                try:
                    symbols_list = json.loads(r["symbols"]) if r["symbols"] else []
                except Exception:
                    symbols_list = [r["symbols"]] if r["symbols"] else []

                events.append(
                    FinancialEvent(
                        event_id=r["event_id"],
                        source=r["source"],
                        category=r["category"],
                        headline=r["headline"],
                        summary=r["summary"],
                        symbols=symbols_list,
                        sentiment_score=float(r["sentiment_score"]),
                        impact_level=EventImpact(r["impact_level"]),
                        url=r["url"],
                        published_at=datetime.fromisoformat(r["published_at"]),
                        created_at=datetime.fromisoformat(r["created_at"]),
                    )
                )
            return events
        finally:
            conn.close()


