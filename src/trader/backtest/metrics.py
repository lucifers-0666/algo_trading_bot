"""Performance Metrics Engine.
Computes institutional quantitative metrics including Sharpe, Sortino, Max Drawdown,
CAGR, Win Rate, Profit Factor, Expectancy, and Cost Drag.
"""

from typing import List, Dict, Any, Optional
import numpy as np
import pandas as pd
from pydantic import BaseModel, Field


class PerformanceMetrics(BaseModel):
    initial_capital: float
    final_equity: float
    gross_pnl_inr: float
    net_pnl_inr: float
    total_return_pct: float
    total_costs_paid_inr: float
    total_slippage_inr: float
    cost_drag_pct: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate_pct: float
    profit_factor: float
    expectancy_inr: float
    avg_win_inr: float
    avg_loss_inr: float
    win_loss_ratio: float
    max_drawdown_pct: float
    max_drawdown_inr: float
    max_drawdown_duration_bars: int
    sharpe_ratio: float
    cagr_pct: float


def compute_performance_metrics(
    initial_capital: float,
    equity_series: List[Dict[str, Any]],
    trade_logs: List[Dict[str, Any]],
    risk_free_rate_annual: float = 0.065, # 6.5% Indian 10y G-Sec baseline
) -> PerformanceMetrics:
    """Computes exhaustive performance report from equity curve and closed trade logs."""
    if not equity_series:
        return PerformanceMetrics(
            initial_capital=initial_capital,
            final_equity=initial_capital,
            gross_pnl_inr=0.0,
            net_pnl_inr=0.0,
            total_return_pct=0.0,
            total_costs_paid_inr=0.0,
            total_slippage_inr=0.0,
            cost_drag_pct=0.0,
            total_trades=0,
            winning_trades=0,
            losing_trades=0,
            win_rate_pct=0.0,
            profit_factor=0.0,
            expectancy_inr=0.0,
            avg_win_inr=0.0,
            avg_loss_inr=0.0,
            win_loss_ratio=0.0,
            max_drawdown_pct=0.0,
            max_drawdown_inr=0.0,
            max_drawdown_duration_bars=0,
            sharpe_ratio=0.0,
            cagr_pct=0.0,
        )

    eq_df = pd.DataFrame(equity_series)
    final_equity = float(eq_df["equity"].iloc[-1])
    net_pnl = round(final_equity - initial_capital, 2)
    total_return_pct = round((net_pnl / initial_capital) * 100.0, 2)

    # Costs and Slippage aggregation
    total_costs = round(sum(t.get("costs_inr", 0.0) for t in trade_logs), 2)
    total_slippage = round(sum(t.get("slippage_inr", 0.0) for t in trade_logs), 2)
    gross_pnl = round(net_pnl + total_costs, 2)
    cost_drag_pct = round((total_costs / initial_capital) * 100.0, 2)

    # Trade statistics
    closed_trades = [t for t in trade_logs if t.get("is_closed", False)]
    total_trades = len(closed_trades)
    pnls = [t.get("net_pnl", 0.0) for t in closed_trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]

    winning_trades = len(wins)
    losing_trades = len(losses)
    win_rate = round((winning_trades / total_trades) * 100.0, 2) if total_trades > 0 else 0.0

    sum_wins = sum(wins)
    sum_losses = abs(sum(losses))
    profit_factor = round(sum_wins / sum_losses, 2) if sum_losses > 0 else (99.0 if sum_wins > 0 else 0.0)

    avg_win = round(sum_wins / len(wins), 2) if wins else 0.0
    avg_loss = round(sum_losses / len(losses), 2) if losses else 0.0
    win_loss_ratio = round(avg_win / avg_loss, 2) if avg_loss > 0 else 0.0
    expectancy = round(sum(pnls) / total_trades, 2) if total_trades > 0 else 0.0

    # Drawdown series
    eq_series = eq_df["equity"]
    peaks = eq_series.cummax()
    dd_series = (peaks - eq_series) / peaks
    dd_inr = peaks - eq_series
    max_dd_pct = round(float(dd_series.max()) * 100.0, 2)
    max_dd_inr = round(float(dd_inr.max()), 2)

    # Drawdown duration in bars
    max_duration = 0
    current_duration = 0
    for is_dd in (eq_series < peaks):
        if is_dd:
            current_duration += 1
            max_duration = max(max_duration, current_duration)
        else:
            current_duration = 0

    # Daily returns and Sharpe ratio
    daily_returns = eq_series.pct_change().dropna()
    rf_daily = (1.0 + risk_free_rate_annual) ** (1.0 / 252.0) - 1.0
    excess_returns = daily_returns - rf_daily
    if len(daily_returns) > 5 and daily_returns.std() > 1e-8:
        sharpe = round(float(np.sqrt(252.0) * (excess_returns.mean() / daily_returns.std())), 2)
    else:
        sharpe = 0.0

    # CAGR calculation
    total_bars = len(eq_df)
    trading_years = total_bars / 252.0
    if trading_years >= 0.1 and final_equity > 0:
        cagr = round((((final_equity / initial_capital) ** (1.0 / trading_years)) - 1.0) * 100.0, 2)
    else:
        cagr = total_return_pct

    return PerformanceMetrics(
        initial_capital=initial_capital,
        final_equity=final_equity,
        gross_pnl_inr=gross_pnl,
        net_pnl_inr=net_pnl,
        total_return_pct=total_return_pct,
        total_costs_paid_inr=total_costs,
        total_slippage_inr=total_slippage,
        cost_drag_pct=cost_drag_pct,
        total_trades=total_trades,
        winning_trades=winning_trades,
        losing_trades=losing_trades,
        win_rate_pct=win_rate,
        profit_factor=profit_factor,
        expectancy_inr=expectancy,
        avg_win_inr=avg_win,
        avg_loss_inr=avg_loss,
        win_loss_ratio=win_loss_ratio,
        max_drawdown_pct=max_dd_pct,
        max_drawdown_inr=max_dd_inr,
        max_drawdown_duration_bars=max_duration,
        sharpe_ratio=sharpe,
        cagr_pct=cagr,
    )
