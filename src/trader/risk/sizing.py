"""Position Sizing Engine for Indian Equities.
Calculates strict whole-share integer quantities respecting 0.5% risk limits,
capital allocation caps, and cash constraints.
"""

import math
from typing import Optional
from pydantic import BaseModel


class SizingResult(BaseModel):
    """Encapsulates position sizing decision."""
    approved: bool
    quantity: int = 0
    entry_price: float
    stop_loss: float
    risk_budget_inr: float
    calculated_risk_inr: float = 0.0
    allocated_capital_inr: float = 0.0
    reason: str


def calculate_position_size(
    entry_price: float,
    stop_loss: float,
    total_equity: float,
    cash_balance: float,
    max_risk_pct: float = 0.005, # 0.5%
    max_position_size_pct: float = 0.25, # 25% single-stock cap
    max_portfolio_exposure_pct: float = 0.50, # 50% total exposure cap
    current_invested_capital: float = 0.0,
) -> SizingResult:
    """Calculates integer share quantity enforcing all risk and capital constraints."""
    if entry_price <= 0 or stop_loss <= 0 or total_equity <= 0:
        return SizingResult(
            approved=False,
            entry_price=entry_price,
            stop_loss=stop_loss,
            risk_budget_inr=0.0,
            reason="Invalid inputs: entry price, stop loss, and equity must be strictly positive",
        )

    stop_distance = entry_price - stop_loss
    if stop_distance <= 0:
        return SizingResult(
            approved=False,
            entry_price=entry_price,
            stop_loss=stop_loss,
            risk_budget_inr=0.0,
            reason=f"Invalid stop loss: Stop (₹{stop_loss:.2f}) must be strictly below Entry (₹{entry_price:.2f})",
        )

    # 1. Planned Risk Budget (e.g. ₹50 on ₹10,000 equity)
    risk_budget = total_equity * max_risk_pct
    raw_qty_by_risk = risk_budget / stop_distance
    qty_by_risk = math.floor(raw_qty_by_risk)

    if qty_by_risk < 1:
        single_share_risk = stop_distance
        return SizingResult(
            approved=False,
            entry_price=entry_price,
            stop_loss=stop_loss,
            risk_budget_inr=risk_budget,
            reason=(
                f"Risk budget breach: Even 1 share risks ₹{single_share_risk:.2f}, "
                f"which exceeds the ₹{risk_budget:.2f} risk budget ({max_risk_pct:.1%} of ₹{total_equity:,.0f})."
            ),
        )

    # 2. Capital Allocation Caps
    max_single_stock_capital = total_equity * max_position_size_pct
    remaining_portfolio_capital = max(0.0, (total_equity * max_portfolio_exposure_pct) - current_invested_capital)
    available_capital = min(cash_balance, max_single_stock_capital, remaining_portfolio_capital)

    qty_by_capital = math.floor(available_capital / entry_price)
    final_qty = min(qty_by_risk, qty_by_capital)

    if final_qty < 1:
        return SizingResult(
            approved=False,
            entry_price=entry_price,
            stop_loss=stop_loss,
            risk_budget_inr=risk_budget,
            reason=(
                f"Capital cap breach: 1 share of ₹{entry_price:.2f} exceeds available capital "
                f"ceiling of ₹{available_capital:.2f} (Cash: ₹{cash_balance:.2f}, "
                f"Max Pos Cap: ₹{max_single_stock_capital:.2f}, Exposure Cap: ₹{remaining_portfolio_capital:.2f})."
            ),
        )

    allocated_capital = round(final_qty * entry_price, 2)
    calculated_risk = round(final_qty * stop_distance, 2)

    return SizingResult(
        approved=True,
        quantity=final_qty,
        entry_price=entry_price,
        stop_loss=stop_loss,
        risk_budget_inr=risk_budget,
        calculated_risk_inr=calculated_risk,
        allocated_capital_inr=allocated_capital,
        reason=(
            f"Approved: Sized to {final_qty} shares (Allocated: ₹{allocated_capital:.2f}, "
            f"Risk: ₹{calculated_risk:.2f} <= Budget ₹{risk_budget:.2f})"
        ),
    )
