from trader.backtest.costs import BrokerProfile
"""Pydantic Request and Response Schemas for the FastAPI REST API."""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from trader.domain.models import OrderSide, OrderType, OrderStatus, Timeframe


class OrderProposalRequest(BaseModel):
    symbol: str
    side: OrderSide
    price: float = Field(..., gt=0.0)
    stop_loss: Optional[float] = None
    quantity: Optional[int] = Field(default=None, gt=0)
    order_type: OrderType = OrderType.MARKET


class OrderExecuteRequest(BaseModel):
    symbol: str
    side: OrderSide
    price: float = Field(..., gt=0.0)
    stop_loss: Optional[float] = None
    quantity: Optional[int] = Field(default=None, gt=0)
    order_type: OrderType = OrderType.MARKET


class ResetAccountRequest(BaseModel):
    confirmation: bool = True


class KillSwitchRequest(BaseModel):
    action: str = Field(..., description="'engage' or 'disengage'")
    reason: str = Field(default="Manual operator action")


class BacktestRunRequest(BaseModel):
    strategy_name: str = Field(default="baseline_swing")
    symbols: List[str] = Field(default_factory=lambda: ["INFY", "RELIANCE", "TCS"])
    initial_capital: float = 10000.0
    brokerage_flat: float = 20.0
    slippage_bps: float = 10.0


class ModelTrainRequest(BaseModel):
    symbol: str = "INFY"
    model_type: str = "random_forest"
    horizon_bars: int = 5


class LookaheadAuditRequest(BaseModel):
    symbol: str = "INFY"
    strategy_name: str = "baseline_swing"


class HyperoptRequest(BaseModel):
    symbols: List[str] = Field(default_factory=lambda: ["INFY", "TCS"])
    param_grid: Optional[Dict[str, List[Any]]] = None
    max_trials: int = 10


class AnnouncementCreateRequest(BaseModel):
    symbol: str
    headline: str
    source: str = "NSE_CORP"
    summary: Optional[str] = None
    url: Optional[str] = None


class DecisionEvaluateRequest(BaseModel):
    symbol: str
    price: float = Field(..., gt=0.0)
    stop_loss: float = Field(..., gt=0.0)
    target: Optional[float] = None
    strategy_name: Optional[str] = "baseline_swing"


class AngelOneConfigureRequest(BaseModel):
    api_key: str
    client_code: str
    pin: str
    totp_secret: str
    test_connection: bool = True


class ProviderSelectRequest(BaseModel):
    provider: str = Field(..., description="'angelone', 'dhan', 'truedata', 'csv', or 'synthetic'")


class CostSimulateRequest(BaseModel):
    symbol: str = "INFY"
    buy_price: float = Field(..., gt=0.0)
    sell_price: float = Field(..., gt=0.0)
    quantity: int = Field(default=10, gt=0)
    broker: str = "ANGEL_ONE"
    trade_type: str = "DELIVERY"
    slippage_bps: float = 5.0


class ForecastEvaluateRequest(BaseModel):
    symbols: Optional[List[str]] = None


class TradingViewWebhookPayload(BaseModel):
    symbol: str
    side: str = Field(..., description="'BUY' or 'SELL'")
    segment: Optional[str] = Field(default="EQ_SWING", description="'EQ_INTRADAY', 'EQ_SWING', 'FUTURES', 'OPTIONS'")
    price: Optional[float] = Field(default=None, description="Trigger/signal price")
    stop_loss: Optional[float] = Field(default=None, description="Stop loss price level")
    target: Optional[float] = Field(default=None, description="Profit target price level")
    quantity: Optional[int] = Field(default=None, gt=0, description="Optional target order quantity")
    strategy_name: Optional[str] = Field(default="TradingView_PineScript", description="PineScript strategy or alert identifier")
    token: Optional[str] = Field(default=None, description="Optional security token")






class EODRunRequest(BaseModel):
    """Explicit point-in-time NSE universe and index symbols for an EOD run."""
    universe_symbols: List[str] = Field(..., min_length=1, max_length=500)
    universe_version: str = Field(..., min_length=1, max_length=100)
    nifty_symbol: str = "^NSEI"
    india_vix_symbol: str = "^INDIAVIX"
    sector_index_symbols: Dict[str, str] = Field(default_factory=dict)
    tick_size_by_symbol: Dict[str, float] = Field(default_factory=dict)
    broker_profile: BrokerProfile = BrokerProfile.ANGEL_ONE
    max_candidates: int = Field(default=20, ge=1, le=100)
    generate_ollama_narratives: bool = False
