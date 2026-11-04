"""Virtual Portfolio Accounting and Ledger Engine.
Maintains virtual cash balances, holdings, realized/unrealized P&L,
and drawdown telemetry for the simulated paper-trading account.
"""

from datetime import datetime
from typing import Dict, Optional
import logging

from trader.domain.models import (
    Position,
    PortfolioState,
    Trade,
    Quote,
    OrderSide,
    IST,
)
from trader.storage.repositories import PortfolioRepository, PositionRepository

logger = logging.getLogger(__name__)


class PortfolioAccountant:
    """Manages virtual funds, holdings, and P&L accounting."""

    def __init__(
        self,
        starting_cash: float = 10000.0,
        portfolio_repo: Optional[PortfolioRepository] = None,
        position_repo: Optional[PositionRepository] = None,
    ):
        self.starting_cash = starting_cash
        self.portfolio_repo = portfolio_repo
        self.position_repo = position_repo
        self.cash_balance = starting_cash
        self.reserved_margin = 0.0
        self.realized_pnl = 0.0
        self.unrealized_pnl = 0.0
        self.peak_equity = starting_cash
        self.day_starting_equity = starting_cash
        self.last_day_reset = datetime.now(IST).strftime("%Y-%m-%d")
        self.positions: Dict[str, Position] = {}
        self._last_snapshot_time = datetime.now(IST)

        # 1. Restore open positions if repository provided
        if self.position_repo:
            persisted = self.position_repo.get_all_positions()
            for pos in persisted:
                self.positions[pos.symbol] = pos
            # Recompute initial unrealized pnl from loaded positions
            self.unrealized_pnl = round(sum(p.unrealized_pnl for p in self.positions.values()), 2)

        # 2. Restore account-level snapshot
        if self.portfolio_repo:
            latest = self.portfolio_repo.get_latest_snapshot()
            if latest:
                self.starting_cash = latest.starting_cash
                self.cash_balance = latest.cash_balance
                self.reserved_margin = latest.reserved_margin
                self.realized_pnl = latest.realized_pnl
                self.peak_equity = max(latest.peak_equity, self.total_equity)

                today_str = datetime.now(IST).strftime("%Y-%m-%d")
                if latest.last_day_reset == today_str:
                    self.day_starting_equity = latest.day_starting_equity
                    self.last_day_reset = today_str
                else:
                    self.day_starting_equity = latest.total_equity
                    self.last_day_reset = today_str

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

        today_str = datetime.now(IST).strftime("%Y-%m-%d")
        if self.last_day_reset != today_str:
            self.day_starting_equity = curr_equity
            self.last_day_reset = today_str

        state = PortfolioState(
            starting_cash=self.starting_cash,
            cash_balance=round(self.cash_balance, 2),
            day_starting_equity=round(self.day_starting_equity, 2),
            last_day_reset=self.last_day_reset,
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
        """Apply a simulated fill atomically with respect to in-memory ledger checks.

        Validate the complete fill before changing cash or positions. In particular,
        an oversell must never credit proceeds to the virtual account.
        """
        if trade.quantity <= 0:
            raise ValueError("Fill quantity must be a positive integer.")
        if trade.price <= 0:
            raise ValueError("Fill price must be positive.")

        sym = trade.symbol.strip().upper()
        pos = self.positions.get(sym)

        if trade.side == OrderSide.BUY:
            if trade.net_value_inr < 0:
                raise ValueError("BUY fill net value cannot be negative.")
            if trade.net_value_inr > self.cash_balance + 1e-9:
                raise ValueError(
                    f"Insufficient virtual cash: BUY requires ₹{trade.net_value_inr:.2f}, "
                    f"available ₹{self.cash_balance:.2f}."
                )

            # All checks passed; apply the cash debit and position update.
            self.cash_balance = round(self.cash_balance - trade.net_value_inr, 2)
            if pos is None or pos.quantity == 0:
                new_pos = Position(
                    symbol=sym,
                    quantity=trade.quantity,
                    average_entry_price=trade.price,
                    current_price=trade.price,
                )
                self.positions[sym] = new_pos
                if self.position_repo:
                    self.position_repo.save_position(new_pos)
            else:
                total_qty = pos.quantity + trade.quantity
                avg_price = (
                    (pos.quantity * pos.average_entry_price) + (trade.quantity * trade.price)
                ) / total_qty
                pos.quantity = total_qty
                pos.average_entry_price = round(avg_price, 2)
                pos.current_price = trade.price
                if self.position_repo:
                    self.position_repo.save_position(pos)
        elif trade.side == OrderSide.SELL:
            # Validate inventory before crediting any sale proceeds.
            if pos is None or pos.quantity < trade.quantity:
                held = pos.quantity if pos else 0
                raise ValueError(
                    f"Cannot SELL {trade.quantity} of {sym}; only holding {held}. "
                    "Short selling is disabled in paper mode."
                )

            # All checks passed; now update proceeds and realized P&L.
            self.cash_balance = round(self.cash_balance + trade.net_value_inr, 2)
            gross_gain = (trade.price - pos.average_entry_price) * trade.quantity
            realized = round(gross_gain - trade.total_costs_inr, 2)
            self.realized_pnl = round(self.realized_pnl + realized, 2)
            pos.realized_pnl = round(pos.realized_pnl + realized, 2)
            pos.quantity -= trade.quantity
            if pos.quantity == 0:
                del self.positions[sym]
                if self.position_repo:
                    self.position_repo.delete_position(sym)
            else:
                if self.position_repo:
                    self.position_repo.save_position(pos)
        else:
            raise ValueError(f"Unsupported trade side: {trade.side!r}")

        self.get_portfolio_state()

    def update_market_prices(self, quotes: Dict[str, Quote]) -> None:
        """Marks open positions to current market prices."""
        unrealized = 0.0
        for sym, pos in self.positions.items():
            if sym in quotes:
                pos.update_market_price(quotes[sym].ltp)
                unrealized += pos.unrealized_pnl
                if self.position_repo:
                    self.position_repo.save_position(pos)
        self.unrealized_pnl = round(unrealized, 2)
        self.get_portfolio_state()

    def reset_account(self, confirmation: bool = False) -> bool:
        """Resets virtual paper account to its configured starting cash."""
        if not confirmation:
            logger.warning("Account reset rejected: Explicit confirmation flag not provided.")
            return False

        self.cash_balance = self.starting_cash
        self.day_starting_equity = self.starting_cash
        self.last_day_reset = datetime.now(IST).strftime("%Y-%m-%d")
        self.reserved_margin = 0.0
        self.realized_pnl = 0.0
        self.unrealized_pnl = 0.0
        self.peak_equity = self.starting_cash
        self.positions.clear()
        if self.position_repo:
            self.position_repo.clear_all()
        self.get_portfolio_state()
        logger.info(f"Virtual paper account successfully reset to ₹{self.starting_cash:,.2f}")
        return True
