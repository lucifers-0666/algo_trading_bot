"""Canonical Domain Models for Indian Equity Paper Trading Platform.
Enforces Pydantic V2 validation, IST timezone handling, and strict type safety.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, field_validator, model_validator
import pytz

IST = pytz.timezone("Asia/Kolkata")


class DataSource(str, Enum):
    SYNTHETIC = "synthetic"
    CSV = "csv"
    TRUEDATA = "truedata"


class Timeframe(str, Enum):
    MINUTE_1 = "1m"
    MINUTE_5 = "5m"
    MINUTE_15 = "15m"
    HOUR_1 = "1h"
    DAILY = "1d"


class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"


class OrderStatus(str, Enum):
    PENDING = "PENDING"
    FILLED = "FILLED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


class Candle(BaseModel):
    """Canonical OHLCV Candlestick model."""
    exchange: str = Field(default="NSE", description="Exchange code, e.g. NSE")
    symbol: str = Field(..., description="NSE Trading symbol, e.g. RELIANCE")
    timestamp: datetime = Field(..., description="Candle start timestamp (Asia/Kolkata)")
    interval: Timeframe = Field(default=Timeframe.DAILY, description="Candle timeframe")
    open: float = Field(..., gt=0.0, description="Opening price")
    high: float = Field(..., gt=0.0, description="Highest price")
    low: float = Field(..., gt=0.0, description="Lowest price")
    close: float = Field(..., gt=0.0, description="Closing price")
    volume: float = Field(..., ge=0.0, description="Total traded volume/shares")
    turnover: Optional[float] = Field(default=None, ge=0.0, description="Total traded value in INR")
    source: DataSource = Field(default=DataSource.SYNTHETIC, description="Origin of data")
    received_at: datetime = Field(
        default_factory=lambda: datetime.now(IST),
        description="Time when system ingested this candle"
    )

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, v: str) -> str:
        clean = v.strip().upper()
        if not clean:
            raise ValueError("Symbol cannot be empty")
        return clean

    @field_validator("timestamp", mode="before")
    @classmethod
    def ensure_ist_timestamp(cls, v: Any) -> datetime:
        if isinstance(v, str):
            # Parse ISO or standard string
            dt = datetime.fromisoformat(v)
        elif isinstance(v, datetime):
            dt = v
        else:
            raise ValueError(f"Invalid timestamp format: {v}")

        if dt.tzinfo is None:
            return IST.localize(dt)
        return dt.astimezone(IST)

    @model_validator(mode="after")
    def validate_ohlc_consistency(self) -> "Candle":
        if self.high < self.low:
            raise ValueError(f"High ({self.high}) cannot be less than Low ({self.low})")
        if self.high < self.open or self.high < self.close:
            raise ValueError(
                f"High ({self.high}) must be >= Open ({self.open}) and Close ({self.close})"
            )
        if self.low > self.open or self.low > self.close:
            raise ValueError(
                f"Low ({self.low}) must be <= Open ({self.open}) and Close ({self.close})"
            )
        return self


class Quote(BaseModel):
    """Real-time market quote snapshot."""
    exchange: str = "NSE"
    symbol: str
    ltp: float = Field(..., gt=0.0, description="Last Traded Price")
    bid: Optional[float] = Field(default=None, ge=0.0)
    ask: Optional[float] = Field(default=None, ge=0.0)
    bid_qty: Optional[float] = Field(default=None, ge=0.0)
    ask_qty: Optional[float] = Field(default=None, ge=0.0)
    volume: float = Field(default=0.0, ge=0.0)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(IST))
    source: DataSource = DataSource.SYNTHETIC

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, v: str) -> str:
        return v.strip().upper()


class Instrument(BaseModel):
    """Instrument Master representation for an NSE stock."""
    symbol: str
    name: str
    series: str = "EQ"
    isin: Optional[str] = None
    tick_size: float = 0.05
    lot_size: int = 1
    is_active: bool = True
    industry: Optional[str] = None


class Order(BaseModel):
    """Simulated Paper Order."""
    order_id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: int = Field(..., gt=0, description="Integer share quantity")
    limit_price: Optional[float] = Field(default=None, gt=0.0)
    stop_price: Optional[float] = Field(default=None, gt=0.0)
    status: OrderStatus = OrderStatus.PENDING
    rejection_reason: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(IST))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(IST))


class Trade(BaseModel):
    """Executed simulated trade record."""
    trade_id: str
    order_id: str
    symbol: str
    side: OrderSide
    quantity: int = Field(..., gt=0)
    price: float = Field(..., gt=0.0, description="Execution price after slippage")
    slippage_inr: float = Field(default=0.0, ge=0.0)
    brokerage_inr: float = Field(default=0.0, ge=0.0)
    stt_inr: float = Field(default=0.0, ge=0.0)
    exchange_charges_inr: float = Field(default=0.0, ge=0.0)
    gst_inr: float = Field(default=0.0, ge=0.0)
    stamp_duty_inr: float = Field(default=0.0, ge=0.0)
    total_costs_inr: float = Field(default=0.0, ge=0.0)
    net_value_inr: float = Field(..., description="Gross trade value +/- fees")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(IST))


class Position(BaseModel):
    """Active open position holding."""
    symbol: str
    quantity: int = Field(default=0, ge=0)
    average_entry_price: float = Field(default=0.0, ge=0.0)
    current_price: float = Field(default=0.0, ge=0.0)
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    open_timestamp: datetime = Field(default_factory=lambda: datetime.now(IST))
    updated_timestamp: datetime = Field(default_factory=lambda: datetime.now(IST))

    def update_market_price(self, ltp: float) -> None:
        self.current_price = ltp
        if self.quantity > 0:
            self.unrealized_pnl = round((ltp - self.average_entry_price) * self.quantity, 2)
        else:
            self.unrealized_pnl = 0.0
        self.updated_timestamp = datetime.now(IST)


class PortfolioState(BaseModel):
    """Aggregated virtual account portfolio status."""
    starting_cash: float = 10000.0
    cash_balance: float = 10000.0
    reserved_margin: float = 0.0
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0
    total_equity: float = 10000.0
    peak_equity: float = 10000.0
    max_drawdown_pct: float = 0.0
    open_positions_count: int = 0
    updated_at: datetime = Field(default_factory=lambda: datetime.now(IST))


class AuditLog(BaseModel):
    """Immutable audit entry for risk, orders, and execution events."""
    event_id: str
    event_type: str
    symbol: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(IST))
