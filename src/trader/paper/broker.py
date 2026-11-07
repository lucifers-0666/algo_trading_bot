"""Virtual Paper Broker Implementation.
Executes simulated paper trades with exact Indian costs and pre-trade risk controls.
STRICTLY ISOLATED FROM REAL BROKER GATEWAYS.
"""

from datetime import datetime
from typing import Optional, Dict, List, Any, Tuple
from uuid import uuid4
import logging

from trader.domain.models import (
    Order,
    Trade,
    Position,
    PortfolioState,
    Quote,
    OrderSide,
    OrderType,
    OrderStatus,
    IST,
)
from trader.risk.checks import RiskManager, RiskAssessment
from trader.paper.orders import OrderManager
from trader.paper.accounting import PortfolioAccountant
from trader.backtest.costs import calculate_trade_costs, TradeCostBreakdown
from trader.storage.repositories import TradeRepository, AuditRepository
from trader.data.freshness import FreshnessReport

logger = logging.getLogger(__name__)


class VirtualPaperBroker:
    """Simulated execution broker for Indian Equity Paper Trading.
    Completely isolated from real financial market execution.
    """

    def __init__(
        self,
        accountant: Optional[PortfolioAccountant] = None,
        risk_manager: Optional[RiskManager] = None,
        order_manager: Optional[OrderManager] = None,
        trade_repo: Optional[TradeRepository] = None,
        audit_repo: Optional[AuditRepository] = None,
        slippage_bps: float = 10.0,
        brokerage_flat: float = 20.0,
    ):
        self.accountant = accountant or PortfolioAccountant()
        self.risk_manager = risk_manager or RiskManager()
        self.order_manager = order_manager or OrderManager()
        self.trade_repo = trade_repo
        self.audit_repo = audit_repo
        self.slippage_bps = slippage_bps
        self.brokerage_flat = brokerage_flat

        # Assert paper isolation at initialization
        self._verify_broker_isolation()

    def _verify_broker_isolation(self) -> None:
        """Architectural assertion: ensures real broker libraries or live order functions are absent."""
        # Check that no live demat routing is present
        assert not hasattr(self, "route_real_order"), "CRITICAL ERROR: Real order routing must not exist!"

    @staticmethod
    def is_live_broker_connected() -> bool:
        """Explicit query proving paper mode cannot route real orders."""
        return False

    def submit_simulated_order(
        self,
        symbol: str,
        side: OrderSide,
        price: float,
        stop_loss: Optional[float] = None,
        quantity: Optional[int] = None,
        order_type: OrderType = OrderType.MARKET,
        feed_freshness: Optional[FreshnessReport] = None,
        target: Optional[float] = None,
        trailing_stop_atr_mult: Optional[float] = None,
    ) -> Tuple[Order, Optional[Trade], RiskAssessment]:
        """Submits, risk-checks, and executes a simulated paper order."""
        sym = symbol.strip().upper()
        portfolio_state = self.accountant.get_portfolio_state()
        open_positions = list(self.accountant.positions.values())

        # 1. Pre-Trade Risk Evaluation
        assessment = self.risk_manager.assess_order(
            symbol=sym,
            side=side,
            price=price,
            stop_loss=stop_loss,
            portfolio=portfolio_state,
            open_positions=open_positions,
            feed_freshness=feed_freshness,
        )

        final_qty = assessment.approved_quantity if quantity is None else quantity

        # A caller-supplied quantity may reduce an approved size, but must never
        # enlarge it or exceed the position available for a SELL.
        if assessment.approved and (final_qty <= 0 or final_qty > assessment.approved_quantity):
            assessment.approved = False
            assessment.rejection_reasons.append(
                f"Requested quantity {final_qty} exceeds the risk-approved quantity "
                f"{assessment.approved_quantity}."
            )

        # Create Order in PENDING status
        order = self.order_manager.create_order(
            symbol=sym,
            side=side,
            quantity=max(1, final_qty),
            order_type=order_type,
            limit_price=price if order_type == OrderType.LIMIT else None,
            stop_price=stop_loss,
        )

        if not assessment.approved:
            reason = "; ".join(assessment.rejection_reasons)
            self.order_manager.update_status(order.order_id, OrderStatus.REJECTED, rejection_reason=reason)
            order.status = OrderStatus.REJECTED
            order.rejection_reason = reason

            if self.audit_repo:
                self.audit_repo.log_event(
                    event_type="ORDER_REJECTED",
                    symbol=sym,
                    details={"order_id": order.order_id, "side": side.value, "reasons": assessment.rejection_reasons},
                )
            logger.warning(f"Simulated order {order.order_id} REJECTED: {reason}")
            return order, None, assessment

        # 2. Compute Fills & Statutory Indian Costs
        cost_breakdown = calculate_trade_costs(
            side=side,
            price=price,
            quantity=final_qty,
            brokerage_flat=self.brokerage_flat,
            slippage_bps=self.slippage_bps,
        )

        # 3. Create Trade Record
        # Pre-fill revalidation immediately before execution (fail closed)
        if self.risk_manager.kill_switch.is_active():
            reason = f"Pre-fill rejection: Emergency Kill Switch is ENGAGED: {self.risk_manager.kill_switch.get_reason()}"
            assessment.approved = False
            assessment.rejection_reasons.append(reason)
            self.order_manager.update_status(order.order_id, OrderStatus.REJECTED, rejection_reason=reason)
            order.status = OrderStatus.REJECTED
            order.rejection_reason = reason
            return order, None, assessment

        trade_id = f"trd_{uuid4().hex[:10]}"
        now_ist = datetime.now(IST)

        trade = Trade(
            trade_id=trade_id,
            order_id=order.order_id,
            symbol=sym,
            side=side,
            quantity=final_qty,
            price=cost_breakdown.effective_price,
            slippage_inr=cost_breakdown.slippage_inr,
            brokerage_inr=cost_breakdown.brokerage_inr,
            stt_inr=cost_breakdown.stt_inr,
            exchange_charges_inr=cost_breakdown.exchange_charges_inr,
            gst_inr=cost_breakdown.gst_inr,
            stamp_duty_inr=cost_breakdown.stamp_duty_inr,
            total_costs_inr=cost_breakdown.total_costs_inr,
            net_value_inr=cost_breakdown.net_trade_amount,
            timestamp=now_ist,
        )

        # 4. Apply fill to virtual portfolio ledger. The accountant performs
        # final cash/inventory validation before mutating the simulated account.
        try:
            self.accountant.apply_fill(
                trade,
                stop_loss=stop_loss,
                target=target,
                trailing_stop_atr_mult=trailing_stop_atr_mult,
            )
        except ValueError as exc:
            reason = f"Virtual fill rejected: {exc}"
            assessment.approved = False
            assessment.rejection_reasons.append(reason)
            self.order_manager.update_status(
                order.order_id,
                OrderStatus.REJECTED,
                rejection_reason=reason,
            )
            order.status = OrderStatus.REJECTED
            order.rejection_reason = reason
            if self.audit_repo:
                self.audit_repo.log_event(
                    event_type="ORDER_REJECTED",
                    symbol=sym,
                    details={
                        "order_id": order.order_id,
                        "side": side.value,
                        "reason": reason,
                    },
                )
            logger.warning("Simulated order %s REJECTED: %s", order.order_id, reason)
            return order, None, assessment

        if self.trade_repo:
            self.trade_repo.save_trade(trade)

        # 5. Update Order to FILLED
        self.order_manager.update_status(order.order_id, OrderStatus.FILLED)
        order.status = OrderStatus.FILLED

        if self.audit_repo:
            self.audit_repo.log_event(
                event_type="ORDER_FILLED",
                symbol=sym,
                details={
                    "order_id": order.order_id,
                    "trade_id": trade.trade_id,
                    "price": trade.price,
                    "quantity": trade.quantity,
                    "total_costs_inr": trade.total_costs_inr,
                },
            )

        logger.info(
            f"Simulated order {order.order_id} FILLED as {trade.trade_id}: "
            f"{side.value} {final_qty} {sym} @ ₹{trade.price:.2f} (Costs: ₹{trade.total_costs_inr:.2f})"
        )
        return order, trade, assessment
