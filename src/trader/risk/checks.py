"""Pre-Trade Risk Verification Engine.
Validates all incoming orders against hard regulatory and software portfolio guardrails.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field

from trader.domain.models import Order, Position, PortfolioState, OrderSide, IST
from trader.risk.kill_switch import PersistentKillSwitch
from trader.risk.sizing import calculate_position_size, SizingResult
from trader.data.freshness import FreshnessReport, FeedStatus


class RiskAssessment(BaseModel):
    approved: bool
    symbol: str
    side: OrderSide
    approved_quantity: int = 0
    rejection_reasons: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    sizing: Optional[SizingResult] = None


class RiskManager:
    """Enforces pre-trade risk controls and safety thresholds."""

    def __init__(
        self,
        kill_switch: Optional[PersistentKillSwitch] = None,
        max_open_positions: int = 2,
        max_portfolio_exposure_pct: float = 0.50,
        max_position_size_pct: float = 0.25,
        max_risk_per_trade_pct: float = 0.005,
        daily_loss_limit_pct: float = 0.01,
        max_drawdown_pause_pct: float = 0.05,
        duplicate_order_window_seconds: int = 60,
    ):
        self.kill_switch = kill_switch or PersistentKillSwitch()
        self.max_open_positions = max_open_positions
        self.max_portfolio_exposure_pct = max_portfolio_exposure_pct
        self.max_position_size_pct = max_position_size_pct
        self.max_risk_per_trade_pct = max_risk_per_trade_pct
        self.daily_loss_limit_pct = daily_loss_limit_pct
        self.max_drawdown_pause_pct = max_drawdown_pause_pct
        self.duplicate_order_window_seconds = duplicate_order_window_seconds
        self._recent_orders: Dict[str, datetime] = {}

    def assess_order(
        self,
        symbol: str,
        side: OrderSide,
        price: float,
        stop_loss: Optional[float],
        portfolio: PortfolioState,
        open_positions: List[Position],
        feed_freshness: Optional[FreshnessReport] = None,
    ) -> RiskAssessment:
        rejection_reasons: List[str] = []
        warnings: List[str] = []
        sym = symbol.strip().upper()

        # 1. Kill Switch Check
        if self.kill_switch.is_active():
            rejection_reasons.append(
                f"Emergency Kill Switch is ENGAGED: {self.kill_switch.get_reason()}"
            )
            return RiskAssessment(
                approved=False,
                symbol=sym,
                side=side,
                rejection_reasons=rejection_reasons,
            )

        # 2. Feed Freshness Guard
        if feed_freshness is not None and not feed_freshness.is_actionable:
            rejection_reasons.append(
                f"Market feed freshness guard breach: {feed_freshness.message}"
            )
            return RiskAssessment(
                approved=False,
                symbol=sym,
                side=side,
                rejection_reasons=rejection_reasons,
            )

        # 3. Duplicate Order Guard (same symbol and same side)
        now_ist = datetime.now(IST)
        order_key = f"{sym}_{side.value}"
        last_order_time = self._recent_orders.get(order_key)
        if last_order_time and (now_ist - last_order_time).total_seconds() < self.duplicate_order_window_seconds:
            rejection_reasons.append(
                f"Duplicate order rejected: Repeated {side.value} order for {sym} within {self.duplicate_order_window_seconds}s window."
            )
            return RiskAssessment(
                approved=False,
                symbol=sym,
                side=side,
                rejection_reasons=rejection_reasons,
            )

        # 4. Daily Loss Limit Check (Calculated against current trading day's starting equity)
        day_base_equity = portfolio.day_starting_equity if portfolio.day_starting_equity > 0 else portfolio.starting_cash
        daily_loss_allowed = day_base_equity * self.daily_loss_limit_pct
        current_daily_loss = day_base_equity - portfolio.total_equity
        if current_daily_loss >= daily_loss_allowed:
            rejection_reasons.append(
                f"Daily loss limit breached: Current loss ₹{current_daily_loss:.2f} >= "
                f"Limit ₹{daily_loss_allowed:.2f} ({self.daily_loss_limit_pct:.1%} of day starting equity ₹{day_base_equity:.2f})"
            )
            # Automatically activate kill switch on daily loss breach
            self.kill_switch.activate("Daily loss limit exceeded")
            return RiskAssessment(
                approved=False,
                symbol=sym,
                side=side,
                rejection_reasons=rejection_reasons,
            )

        # 5. Drawdown Pause Check
        if portfolio.max_drawdown_pct >= self.max_drawdown_pause_pct:
            rejection_reasons.append(
                f"Max portfolio drawdown breached: {portfolio.max_drawdown_pct:.1%} >= "
                f"Pause limit {self.max_drawdown_pause_pct:.1%}"
            )
            return RiskAssessment(
                approved=False,
                symbol=sym,
                side=side,
                rejection_reasons=rejection_reasons,
            )

        # SELL orders to close or reduce existing positions skip new entry caps
        if side == OrderSide.SELL:
            existing_pos = next((p for p in open_positions if p.symbol == sym), None)
            if not existing_pos or existing_pos.quantity <= 0:
                rejection_reasons.append(f"Cannot SELL {sym}: No open long position exists (Shorting forbidden).")
                return RiskAssessment(approved=False, symbol=sym, side=side, rejection_reasons=rejection_reasons)

            self._recent_orders[order_key] = now_ist
            return RiskAssessment(
                approved=True,
                symbol=sym,
                side=side,
                approved_quantity=existing_pos.quantity,
                rejection_reasons=[],
            )

        # 6. Maximum Open Positions Limit (for BUY entries)
        active_symbols = [p.symbol for p in open_positions if p.quantity > 0]
        if sym in active_symbols:
            rejection_reasons.append(f"Pyramiding rejected: Already holding open position in {sym}.")
            return RiskAssessment(approved=False, symbol=sym, side=side, rejection_reasons=rejection_reasons)

        if len(active_symbols) >= self.max_open_positions:
            rejection_reasons.append(
                f"Max open positions reached ({len(active_symbols)}/{self.max_open_positions}). New entries blocked."
            )
            return RiskAssessment(approved=False, symbol=sym, side=side, rejection_reasons=rejection_reasons)

        # 7. Position Sizing
        if stop_loss is None or stop_loss >= price:
            rejection_reasons.append(
                f"Invalid stop loss for BUY order: Stop ({stop_loss}) must be strictly below Entry ({price})."
            )
            return RiskAssessment(approved=False, symbol=sym, side=side, rejection_reasons=rejection_reasons)

        current_exposure = sum(p.quantity * p.current_price for p in open_positions)
        sizing = calculate_position_size(
            entry_price=price,
            stop_loss=stop_loss,
            total_equity=portfolio.total_equity,
            cash_balance=portfolio.cash_balance,
            max_risk_pct=self.max_risk_per_trade_pct,
            max_position_size_pct=self.max_position_size_pct,
            max_portfolio_exposure_pct=self.max_portfolio_exposure_pct,
            current_invested_capital=current_exposure,
        )

        if not sizing.approved:
            rejection_reasons.append(sizing.reason)
            return RiskAssessment(
                approved=False,
                symbol=sym,
                side=side,
                rejection_reasons=rejection_reasons,
                sizing=sizing,
            )

        self._recent_orders[order_key] = now_ist
        return RiskAssessment(
            approved=True,
            symbol=sym,
            side=side,
            approved_quantity=sizing.quantity,
            sizing=sizing,
        )
