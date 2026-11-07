import pytest
from datetime import datetime, timedelta
import pandas as pd

from trader.domain.models import Candle, OrderSide, IST
from trader.backtest.engine import BacktestEngine, BacktestResult
from trader.strategies.baseline import BaselineSwingStrategy, StrategySignal, SignalType


class MockStrategy(BaselineSwingStrategy):
    """Custom mock strategy for deterministic backtest execution verification."""
    def __init__(self, entry_bar_idx: int = 55, stop_loss: float = 95.0, target: float = 120.0):
        super().__init__()
        self.entry_bar_idx = entry_bar_idx
        self.stop_loss = stop_loss
        self.target = target

    def evaluate_entry(self, df_ind: pd.DataFrame) -> StrategySignal | None:
        if len(df_ind) == self.entry_bar_idx:
            close_p = float(df_ind.iloc[-1]["close"])
            dt = df_ind.iloc[-1]["timestamp"]
            return StrategySignal(
                symbol="TEST",
                signal_type=SignalType.BUY,
                timestamp=dt,
                reference_close=close_p,
                suggested_entry=close_p,
                suggested_stop_loss=self.stop_loss,
                suggested_target=self.target,
                reason="Mock trigger",
            )
        return None

    def evaluate_exit(self, df_ind: pd.DataFrame, entry_price: float, stop_loss: float, target: float | None = None, holding_candles: int = 0) -> StrategySignal | None:
        return None


def _make_candle(dt: datetime, o: float, h: float, l: float, c: float, v: float = 10000.0) -> Candle:
    return Candle(
        exchange="NSE",
        symbol="TEST",
        timestamp=dt,
        open=o,
        high=h,
        low=l,
        close=c,
        volume=v,
    )


def test_gap_through_stop_loss_execution():
    """Verify that when a session opens below the stop-loss, exit executes at open, not nominal stop."""
    base_time = datetime(2026, 1, 1, 9, 15, tzinfo=IST)
    candles = []
    # 54 warm-up bars around 100
    for i in range(54):
        t = base_time + timedelta(days=i)
        candles.append(_make_candle(t, 100.0, 101.0, 99.0, 100.0))

    # Bar 55: Signal bar. Close 100.0. Entry signal with stop 95.0, target 120.0
    candles.append(_make_candle(base_time + timedelta(days=54), 100.0, 101.0, 99.0, 100.0))

    # Bar 56: Entry executed at open 100.0
    candles.append(_make_candle(base_time + timedelta(days=55), 100.0, 103.0, 99.5, 102.0))

    # Bar 57: Gap down through stop loss! Open is 90.0 (< stop 95.0), Low 88.0, High 92.0, Close 91.0
    candles.append(_make_candle(base_time + timedelta(days=56), 90.0, 92.0, 88.0, 91.0))

    # Bar 58: Post-exit bar
    candles.append(_make_candle(base_time + timedelta(days=57), 91.0, 93.0, 90.0, 92.0))

    strat = MockStrategy(entry_bar_idx=55, stop_loss=95.0, target=120.0)
    engine = BacktestEngine(strategy=strat, slippage_bps=0.0, brokerage_flat=0.0)
    result = engine.run({"TEST": candles})

    assert len(result.trade_records) >= 1
    trade = result.trade_records[0]
    assert trade.is_closed is True
    assert "Stop-loss" in trade.exit_reason
    # CRITICAL: Exit must be executed at 90.0 (the gap open price), NOT 95.0!
    assert trade.exit_price == 90.0


def test_collision_handling_stop_loss_and_target_in_same_candle():
    """When both low <= stop and high >= target in same bar, conservative assumption executes stop first."""
    base_time = datetime(2026, 1, 1, 9, 15, tzinfo=IST)
    candles = []
    for i in range(54):
        t = base_time + timedelta(days=i)
        candles.append(_make_candle(t, 100.0, 101.0, 99.0, 100.0))

    # Bar 55: Signal bar. Close 100.0. Stop 95.0, Target 110.0
    candles.append(_make_candle(base_time + timedelta(days=54), 100.0, 101.0, 99.0, 100.0))

    # Bar 56: Entry bar at open 100.0
    candles.append(_make_candle(base_time + timedelta(days=55), 100.0, 102.0, 99.0, 101.0))

    # Bar 57: Wild candle! Open 101.0, High 115.0 (touches target 110), Low 92.0 (touches stop 95), Close 105.0
    candles.append(_make_candle(base_time + timedelta(days=56), 101.0, 115.0, 92.0, 105.0))

    strat = MockStrategy(entry_bar_idx=55, stop_loss=95.0, target=110.0)
    engine = BacktestEngine(strategy=strat, slippage_bps=0.0, brokerage_flat=0.0)
    result = engine.run({"TEST": candles})

    assert len(result.trade_records) >= 1
    trade = result.trade_records[0]
    assert trade.is_closed is True
    # Conservative execution assumption: Stop-loss executed rather than target
    assert "Stop-loss hit (Intrabar collision" in trade.exit_reason
    assert trade.exit_price == 95.0


def test_circuit_locked_bar_blocks_execution():
    """Upper/lower circuit (O=H=L=C with 0 volume) blocks entry and exit."""
    base_time = datetime(2026, 1, 1, 9, 15, tzinfo=IST)
    candles = []
    for i in range(54):
        t = base_time + timedelta(days=i)
        candles.append(_make_candle(t, 100.0, 101.0, 99.0, 100.0))

    # Bar 55: Signal bar
    candles.append(_make_candle(base_time + timedelta(days=54), 100.0, 101.0, 99.0, 100.0))

    # Bar 56: Pending entry exists, but next bar is locked at upper circuit (no volume)
    candles.append(_make_candle(base_time + timedelta(days=55), 110.0, 110.0, 110.0, 110.0, v=0.0))

    strat = MockStrategy(entry_bar_idx=55, stop_loss=95.0, target=120.0)
    engine = BacktestEngine(strategy=strat, slippage_bps=0.0, brokerage_flat=0.0)
    result = engine.run({"TEST": candles})

    # Entry should have been skipped because bar was untradeable circuit
    closed = [t for t in result.trade_records if t.is_closed]
    assert len(closed) == 0



def test_end_of_test_open_position_is_marked_without_fictitious_exit_costs():
    """Open holdings contribute to equity, but hypothetical exit costs are not booked."""
    base_time = datetime(2026, 1, 1, 9, 15, tzinfo=IST)
    candles = []
    for i in range(54):
        candles.append(_make_candle(base_time + timedelta(days=i), 100.0, 101.0, 99.0, 100.0))
    candles.append(_make_candle(base_time + timedelta(days=54), 100.0, 101.0, 99.0, 100.0))
    candles.append(_make_candle(base_time + timedelta(days=55), 100.0, 103.0, 99.5, 102.0))

    strategy = MockStrategy(entry_bar_idx=55, stop_loss=95.0, target=120.0)
    result = BacktestEngine(
        strategy=strategy,
        slippage_bps=10.0,
        brokerage_flat=0.0,
    ).run({"TEST": candles})

    assert len(result.trade_records) == 1
    open_trade = result.trade_records[0]
    assert open_trade.is_closed is False
    assert open_trade.exit_date is None
    assert open_trade.exit_price is None
    assert open_trade.exit_costs == 0.0
    assert open_trade.entry_costs > 0.0
    assert open_trade.entry_slippage > 0.0
    assert result.metrics.total_costs_paid_inr == pytest.approx(open_trade.entry_costs)
    assert result.metrics.total_slippage_inr == pytest.approx(open_trade.entry_slippage)
    assert result.metrics.gross_pnl_inr == pytest.approx(
        result.metrics.net_pnl_inr + open_trade.entry_costs + open_trade.entry_slippage
    )
    assert result.metrics.cost_drag_pct == pytest.approx(
        (open_trade.entry_costs + open_trade.entry_slippage) / 10000.0 * 100.0
    )
    assert result.equity_curve[-1]["exposure"] > 0.0
    assert result.equity_curve[-1]["equity"] == pytest.approx(
        result.equity_curve[-1]["cash"] + result.equity_curve[-1]["exposure"]
    )
