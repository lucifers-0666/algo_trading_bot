"""Virtual Portfolio Accounting and Ledger Engine.
Maintains exact virtual cash balances, holdings, realized/unrealized P&L,
and drawdown telemetry for the simulated ₹10,000 paper trading account.
"""

from datetime import datetime
from typing import Dict, List, Optional
import logging

from trader.domain.models import (
    Position,
    PortfolioState,
    Trade,
    Quote,
    OrderSide,
    IST,
)
from trader.storage.repositories import PortfolioRepository

logger = logging.getLogger(__name__)


class PortfolioAccountant:
    """Manages virtual funds, holdings, and P&L accounting."""

    def __init__(
        self,
        starting_cash: float = 10000.0,
        portfolio_repo: Optional[PortfolioRepository] = None,
    ):
        self.starting_cash = starting_cash
        self.portfolio_repo = portfolio_repo
        self.cash_balance = starting_cash
        self.reserved_margin = 0.0
        self.realized_pnl = 0.0
        self.unrealized_pnl = 0.0
        self.peak_equity = starting_cash
        self.positions: Dict[str, Position] = {}
        self._last_snapshot_time = datetime.now(IST)

        # Restore from database if snapshot exists
        if self.portfolio_repo:
            latest = self.portfolio_repo.get_latest_snapshot()
            if latest:
                self.starting_cash = latest.starting_cash
                self.cash_balance = latest.cash_balance
                self.reserved_margin = latest.reserved_margin
                self.realized_pnl = latest.realized_pnl
                self.peak_equity = latest.peak_equity

    @property
    def total_equity(self) -> float:
        market_val = sum(p.quantity * p.current_price for p in self.positions.values())
        return round(self.cash_balance + market_val, 2)

    @property
    def max_drawdown_pct(self) -> float:
        curr_eq = self.total_equity
        if self.peak_equity <= 0:
            return 0.0
        dd = (self.peak_equity - curr_eq) / self.peak_equity
        return max(0.0, round(float(dd), 4))

    def get_portfolio_state(self) -> PortfolioState:
        curr_equity = self.total_equity
        if curr_equity > self.peak_equity:
            self.peak_equity = curr_equity

        state = PortfolioState(
            starting_cash=self.starting_cash,
            cash_balance=round(self.cash_balance, 2),
            reserved_margin=round(self.reserved_margin, 2),
            realized_pnl=round(self.realized_pnl, 2),
            unrealized_pnl=round(self.unrealized_pnl, 2),
            total_equity=curr_equity,
            peak_equity=self.peak_equity,
            max_drawdown_pct=self.max_drawdown_pct,
            open_positions_count=len([p for p in self.positions.values() if p.quantity > 0]),
            updated_at=datetime.now(IST),
        )

        if self.portfolio_repo:
            self.portfolio_repo.save_snapshot(state)
        return state

    def apply_fill(self, trade: Trade) -> None:
        """Updates virtual cash and positions following trade execution."""
        sym = trade.symbol
        pos = self.positions.get(sym)

        if trade.side == OrderSide.BUY:
            # Outflow: Net trade amount (Trade value + Brokerage + Taxes)
            self.cash_balance -= trade.net_value_inr

            if pos is None or pos.quantity == 0:
                self.positions[sym] = Position(
                    symbol=sym,
                    quantity=trade.quantity,
                    average_entry_price=trade.price,
                    current_price=trade.price,
                )
            else:
                total_qty = pos.quantity + trade.quantity
                avg_price = (
                    (pos.quantity * pos.average_entry_price) + (trade.quantity * trade.price)
                ) / total_qty
                pos.quantity = total_qty
                pos.average_entry_price = round(avg_price, 2)
                pos.current_price = trade.price
        else: # SELL
            # Inflow: Net trade amount (Trade value - Brokerage - Taxes)
            self.cash_balance += trade.net_value_inr

            if pos and pos.quantity >= trade.quantity:
                gross_gain = (trade.price - pos.average_entry_price) * trade.quantity
                # Realized net P&L incorporates total costs
                realized = round(gross_gain - trade.total_costs_inr, 2)
                self.realized_pnl += realized
                pos.realized_pnl += realized

                pos.quantity -= trade.quantity
                if pos.quantity == 0:
                    del self.positions[sym]
            else:
                logger.error(f"Cannot sell {trade.quantity} of {sym}; only holding {pos.quantity if pos else 0}")

        self.get_portfolio_state()

    def update_market_prices(self, quotes: Dict[str, Quote]) -> None:
        """Marks open positions to current market prices."""
        unrealized = 0.0
        for sym, pos in self.positions.items():
            if sym in quotes:
                pos.update_market_price(quotes[sym].ltp)
                unrealized += pos.unrealized_pnl
        self.unrealized_pnl = round(unrealized, 2)
        self.get_portfolio_state()

    def reset_account(self, confirmation: bool = False) -> bool:
        """Resets virtual paper account to ₹10,000 upon explicit confirmation."""
        if not confirmation:
            logger.warning("Account reset rejected: Explicit confirmation flag not provided.")
            return False

        self.cash_balance = self.starting_cash
        self.reserved_margin = 0.0
        self.realized_pnl = 0.0
        self.unrealized_pnl = 0.0
        self.peak_equity = self.starting_cash
        self.positions.clear()
        self.get_portfolio_state()
        logger.info(f"Virtual paper account successfully reset to ₹{self.starting_cash:,.2f}")
        return True
