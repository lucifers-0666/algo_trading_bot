"""Virtual Paper Order Lifecycle Management.
Handles simulated order creation, state transitions, idempotency, and audit tracking.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import uuid4
import logging

from trader.domain.models import Order, OrderSide, OrderType, OrderStatus, IST
from trader.storage.repositories import OrderRepository

logger = logging.getLogger(__name__)


class OrderManager:
    """Manages virtual order states and persistence."""

    def __init__(self, order_repo: Optional[OrderRepository] = None):
        self.order_repo = order_repo
        self._orders: Dict[str, Order] = {}

    def create_order(
        self,
        symbol: str,
        side: OrderSide,
        quantity: int,
        order_type: OrderType = OrderType.MARKET,
        limit_price: Optional[float] = None,
        stop_price: Optional[float] = None,
    ) -> Order:
        """Creates a new simulated order in PENDING status."""
        order_id = f"ord_{uuid4().hex[:10]}"
        now_ist = datetime.now(IST)

        order = Order(
            order_id=order_id,
            symbol=symbol.strip().upper(),
            side=side,
            order_type=order_type,
            quantity=quantity,
            limit_price=limit_price,
            stop_price=stop_price,
            status=OrderStatus.PENDING,
            created_at=now_ist,
            updated_at=now_ist,
        )

        self._orders[order_id] = order
        if self.order_repo:
            self.order_repo.save_order(order)

        logger.info(f"Created simulated order {order_id}: {side.value} {quantity} {symbol}")
        return order

    def update_status(
        self,
        order_id: str,
        status: OrderStatus,
        rejection_reason: Optional[str] = None,
    ) -> Optional[Order]:
        """Transitions order status and records rejection reason if applicable."""
        order = self._orders.get(order_id)
        if not order and self.order_repo:
            order = self.order_repo.get_order(order_id)

        if not order:
            logger.error(f"Cannot update non-existent order {order_id}")
            return None

        order.status = status
        order.rejection_reason = rejection_reason
        order.updated_at = datetime.now(IST)

        self._orders[order_id] = order
        if self.order_repo:
            self.order_repo.save_order(order)

        return order

    def get_order(self, order_id: str) -> Optional[Order]:
        if order_id in self._orders:
            return self._orders[order_id]
        if self.order_repo:
            return self.order_repo.get_order(order_id)
        return None

    def get_all_orders(self) -> List[Order]:
        if self.order_repo:
            return self.order_repo.get_all_orders()
        return list(self._orders.values())
