"""Database Connection & Schema Management for SQLite.
Configures WAL mode, indexes, busy timeouts, and table schema initialization.
"""

import sqlite3
from pathlib import Path
from typing import Optional
import os

DEFAULT_DB_PATH = Path("data/storage/paper_trader.db")

SCHEMA_SQL = """
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS candles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    exchange TEXT NOT NULL DEFAULT 'NSE',
    symbol TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    interval TEXT NOT NULL DEFAULT '1d',
    open REAL NOT NULL,
    high REAL NOT NULL,
    low REAL NOT NULL,
    close REAL NOT NULL,
    volume REAL NOT NULL DEFAULT 0.0,
    turnover REAL,
    source TEXT NOT NULL,
    received_at TEXT NOT NULL,
    UNIQUE(exchange, symbol, timestamp, interval)
);

CREATE INDEX IF NOT EXISTS idx_candles_symbol_time ON candles(symbol, timestamp);

CREATE TABLE IF NOT EXISTS instruments (
    symbol TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    series TEXT NOT NULL DEFAULT 'EQ',
    isin TEXT,
    tick_size REAL NOT NULL DEFAULT 0.05,
    lot_size INTEGER NOT NULL DEFAULT 1,
    is_active INTEGER NOT NULL DEFAULT 1,
    industry TEXT
);

CREATE TABLE IF NOT EXISTS orders (
    order_id TEXT PRIMARY KEY,
    symbol TEXT NOT NULL,
    side TEXT NOT NULL,
    order_type TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    limit_price REAL,
    stop_price REAL,
    status TEXT NOT NULL,
    rejection_reason TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_orders_symbol ON orders(symbol);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);

CREATE TABLE IF NOT EXISTS trades (
    trade_id TEXT PRIMARY KEY,
    order_id TEXT NOT NULL,
    symbol TEXT NOT NULL,
    side TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    price REAL NOT NULL,
    slippage_inr REAL NOT NULL DEFAULT 0.0,
    brokerage_inr REAL NOT NULL DEFAULT 0.0,
    stt_inr REAL NOT NULL DEFAULT 0.0,
    exchange_charges_inr REAL NOT NULL DEFAULT 0.0,
    gst_inr REAL NOT NULL DEFAULT 0.0,
    stamp_duty_inr REAL NOT NULL DEFAULT 0.0,
    total_costs_inr REAL NOT NULL DEFAULT 0.0,
    net_value_inr REAL NOT NULL,
    timestamp TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol);
CREATE INDEX IF NOT EXISTS idx_trades_timestamp ON trades(timestamp);

CREATE TABLE IF NOT EXISTS positions (
    symbol TEXT PRIMARY KEY,
    quantity INTEGER NOT NULL,
    average_entry_price REAL NOT NULL,
    current_price REAL NOT NULL,
    unrealized_pnl REAL NOT NULL DEFAULT 0.0,
    realized_pnl REAL NOT NULL DEFAULT 0.0,
    open_timestamp TEXT NOT NULL,
    updated_timestamp TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_positions_symbol ON positions(symbol);

CREATE TABLE IF NOT EXISTS portfolio_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    starting_cash REAL NOT NULL,
    cash_balance REAL NOT NULL,
    day_starting_equity REAL NOT NULL DEFAULT 10000.0,
    last_day_reset TEXT NOT NULL DEFAULT '',
    reserved_margin REAL NOT NULL DEFAULT 0.0,
    realized_pnl REAL NOT NULL DEFAULT 0.0,
    unrealized_pnl REAL NOT NULL DEFAULT 0.0,
    total_equity REAL NOT NULL,
    peak_equity REAL NOT NULL,
    max_drawdown_pct REAL NOT NULL DEFAULT 0.0,
    open_positions_count INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_logs (
    event_id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,
    symbol TEXT,
    details_json TEXT NOT NULL,
    timestamp TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_logs(timestamp);
"""


class DatabaseManager:
    """Manages SQLite connections and schema lifecycles."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = Path(db_path) if db_path else DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize_schema()

    def get_connection(self) -> sqlite3.Connection:
        """Returns a configured SQLite connection with row factory enabled."""
        conn = sqlite3.connect(
            str(self.db_path),
            timeout=10.0,
            check_same_thread=False,
            isolation_level=None, # autocommit mode by default; manual transactions with BEGIN
        )
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def initialize_schema(self) -> None:
        """Executes table and index DDL with column migrations for existing databases."""
        conn = self.get_connection()
        try:
            conn.executescript(SCHEMA_SQL)
            # Automatic schema migration for existing databases
            cursor = conn.execute("PRAGMA table_info(portfolio_snapshots);")
            cols = [r["name"] for r in cursor.fetchall()]
            if cols and "day_starting_equity" not in cols:
                conn.execute("ALTER TABLE portfolio_snapshots ADD COLUMN day_starting_equity REAL NOT NULL DEFAULT 10000.0;")
            if cols and "last_day_reset" not in cols:
                conn.execute("ALTER TABLE portfolio_snapshots ADD COLUMN last_day_reset TEXT NOT NULL DEFAULT '';")
        finally:
            conn.close()

    def reset_database(self) -> None:
        """Completely purges and reinitializes database tables."""
        conn = self.get_connection()
        try:
            conn.execute("DROP TABLE IF EXISTS candles;")
            conn.execute("DROP TABLE IF EXISTS instruments;")
            conn.execute("DROP TABLE IF EXISTS orders;")
            conn.execute("DROP TABLE IF EXISTS trades;")
            conn.execute("DROP TABLE IF EXISTS positions;")
            conn.execute("DROP TABLE IF EXISTS portfolio_snapshots;")
            conn.execute("DROP TABLE IF EXISTS audit_logs;")
            conn.executescript(SCHEMA_SQL)
        finally:
            conn.close()

