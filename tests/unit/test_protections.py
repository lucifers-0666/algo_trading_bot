"""Unit tests for Strategy Protections, Cooldown, and Circuit Breakers."""

from datetime import datetime, timedelta
import pytest

from trader.domain.models import IST
from trader.strategies.protections import RiskProtectionManager


def test_consecutive_loss_circuit_breaker():
    manager = RiskProtectionManager(max_consecutive_losses=3, lockout_duration_hours=24)
    now = datetime(2026, 11, 5, 10, 0, tzinfo=IST)

    # Initial state: not locked
    locked, _ = manager.is_trading_locked(now)
    assert locked is False

    # Trade 1: Loss
    manager.record_trade_result("TCS", pnl_inr=-150.0, timestamp=now)
    assert manager.is_symbol_in_cooldown("TCS") is True
    locked, _ = manager.is_trading_locked(now)
    assert locked is False

    # Trade 2: Loss
    manager.record_trade_result("INFY", pnl_inr=-200.0, timestamp=now)
    assert manager.is_symbol_in_cooldown("INFY") is True
    locked, _ = manager.is_trading_locked(now)
    assert locked is False

    # Trade 3: Loss -> Triggers consecutive loss circuit!
    manager.record_trade_result("RELIANCE", pnl_inr=-180.0, timestamp=now)
    locked, reason = manager.is_trading_locked(now)
    assert locked is True
    assert "consecutive losses" in reason.lower()

    # Step forward 25 hours -> lockout must expire
    later = now + timedelta(hours=25)
    locked_later, _ = manager.is_trading_locked(later)
    assert locked_later is False


def test_symbol_cooldown_step_bars():
    manager = RiskProtectionManager(symbol_cooldown_bars=3)
    manager.record_trade_result("SBIN", pnl_inr=-100.0)

    assert manager.is_symbol_in_cooldown("SBIN") is True

    manager.step_bar()
    assert manager.is_symbol_in_cooldown("SBIN") is True

    manager.step_bar()
    assert manager.is_symbol_in_cooldown("SBIN") is True

    manager.step_bar()
    # After 3 bars, cooldown must clear
    assert manager.is_symbol_in_cooldown("SBIN") is False


def test_winning_trade_resets_loss_counter():
    manager = RiskProtectionManager(max_consecutive_losses=3)
    manager.record_trade_result("TCS", pnl_inr=-100.0)
    manager.record_trade_result("INFY", pnl_inr=-150.0)
    assert manager._consecutive_losses == 2

    # Win resets streak to 0
    manager.record_trade_result("RELIANCE", pnl_inr=+450.0)
    assert manager._consecutive_losses == 0

