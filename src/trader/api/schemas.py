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

