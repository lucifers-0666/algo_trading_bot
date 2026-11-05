"""Clean-Room Strategy Protections and Circuit Breakers.
Implements cooldown periods after stop-losses, consecutive loss freezes,
and maximum portfolio drawdown trading halts.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from pydantic import BaseModel, Field

from trader.domain.models import IST

logger = logging.getLogger(__name__)


class ProtectionStatus(BaseModel):
    is_locked: bool
    lock_reason: Optional[str] = None
    unlock_at: Optional[datetime] = None
    consecutive_losses: int = 0
    symbols_in_cooldown: Dict[str, str] = Field(default_factory=dict)


class RiskProtectionManager:
    """Protects capital by locking out troubled symbols or pausing all trading during adverse streaks."""

    def __init__(
        self,
        max_consecutive_losses: int = 3,
        lockout_duration_hours: int = 48,
        symbol_cooldown_bars: int = 5,
        max_drawdown_limit_pct: float = 0.05,
    ):
        self.max_consecutive_losses = max_consecutive_losses
        self.lockout_duration = timedelta(hours=lockout_duration_hours)
        self.symbol_cooldown_bars = symbol_cooldown_bars
        self.max_drawdown_limit_pct = max_drawdown_limit_pct

        self._consecutive_losses = 0
        self._lockout_until: Optional[datetime] = None
        self._lockout_reason: Optional[str] = None
        self._symbol_cooldowns: Dict[str, int] = {} # Symbol -> cooldown bars remaining

    def is_trading_locked(self, now_dt: Optional[datetime] = None) -> Tuple[bool, Optional[str]]:
        """Returns True if global trading is locked due to consecutive loss circuit or max drawdown."""
        dt = now_dt or datetime.now(IST)
        if self._lockout_until and dt < self._lockout_until:
            return True, self._lockout_reason

        # Expired lockout
        if self._lockout_until and dt >= self._lockout_until:
            logger.info("Global trading lockout expired. Trading resumed.")
            self._lockout_until = None
            self._lockout_reason = None
            self._consecutive_losses = 0

        return False, None

    def is_symbol_in_cooldown(self, symbol: str) -> bool:
        """Returns True if a specific symbol is in cooldown following a stop-loss exit."""
        sym = symbol.strip().upper()
        return self._symbol_cooldowns.get(sym, 0) > 0

    def step_bar(self) -> None:
        """Decrements cooldown bars across all active cooldown symbols at the close of a candle."""
        for sym in list(self._symbol_cooldowns.keys()):
            self._symbol_cooldowns[sym] -= 1
            if self._symbol_cooldowns[sym] <= 0:
                del self._symbol_cooldowns[sym]
                logger.info(f"Cooldown ended for symbol {sym}.")

    def record_trade_result(
        self,
        symbol: str,
        pnl_inr: float,
        exit_reason: str = "NORMAL",
        timestamp: Optional[datetime] = None,
    ) -> None:
        """Updates consecutive loss telemetry and activates protection circuits if needed."""
        sym = symbol.strip().upper()
        now_dt = timestamp or datetime.now(IST)

        if pnl_inr < 0:
            self._consecutive_losses += 1
            # Put symbol into cooldown
            self._symbol_cooldowns[sym] = self.symbol_cooldown_bars
            logger.warning(
                f"Trade loss on {sym} (-₹{abs(pnl_inr):.2f}). "
                f"Consecutive losses: {self._consecutive_losses}. Symbol cooldown activated for {self.symbol_cooldown_bars} bars."
            )

            # Check consecutive loss circuit breaker
            if self._consecutive_losses >= self.max_consecutive_losses:
                self._lockout_until = now_dt + self.lockout_duration
                self._lockout_reason = (
                    f"Consecutive loss circuit breaker triggered ({self._consecutive_losses} consecutive losses). "
                    f"New trades locked until {self._lockout_until.strftime('%Y-%m-%d %H:%M IST')}."
                )
                logger.critical(self._lockout_reason)
        else:
            # Winning trade resets consecutive losses counter
            self._consecutive_losses = 0
            if sym in self._symbol_cooldowns:
                del self._symbol_cooldowns[sym]

    def check_drawdown_limit(self, current_drawdown_pct: float) -> bool:
        """Enforces emergency halt if portfolio drawdown exceeds threshold."""
        if current_drawdown_pct >= self.max_drawdown_limit_pct:
            self._lockout_until = datetime.now(IST) + self.lockout_duration
            self._lockout_reason = (
                f"Max portfolio drawdown limit breached ({current_drawdown_pct*100:.2f}% >= {self.max_drawdown_limit_pct*100:.1f}%). "
                "Trading halted."
            )
            return True
        return False

    def get_status(self) -> ProtectionStatus:
        """Returns comprehensive protections telemetry."""
        locked, reason = self.is_trading_locked()
        return ProtectionStatus(
            is_locked=locked,
            lock_reason=reason,
            unlock_at=self._lockout_until,
            consecutive_losses=self._consecutive_losses,
            symbols_in_cooldown={s: f"{bars} bars remaining" for s, bars in self._symbol_cooldowns.items()},
        )

    def manual_reset(self) -> None:
        """Allows manual operator reset of all active protections and cooldowns."""
        self._consecutive_losses = 0
        self._lockout_until = None
        self._lockout_reason = None
        self._symbol_cooldowns.clear()
        logger.info("Risk protections manually reset by operator.")
