"""Multi-Strategy Comparison Framework.
Executes multiple strategies against identical historical data, capital assumptions,
and statutory transaction costs, producing structured comparison tables.
"""

from typing import Dict, List, Any, Optional
from pydantic import BaseModel

from trader.domain.models import Candle
from trader.backtest.engine import BacktestEngine, BacktestResult
from trader.strategies.baseline import BaselineSwingStrategy
from trader.strategies.momentum import MomentumStrategy
from trader.strategies.breakout import DonchianBreakoutStrategy


class StrategyComparisonRow(BaseModel):
    strategy_name: str
    total_net_return_pct: float
    net_pnl_inr: float
    max_drawdown_pct: float
    sharpe_ratio: float
    sortino_ratio: float
    win_rate_pct: float
    profit_factor: float
    expectancy_inr: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    total_costs_inr: float
    average_holding_bars: float


class StrategyComparisonReport(BaseModel):
    initial_capital: float
    test_symbols: List[str]
    start_date: str
    end_date: str
    benchmark_buy_hold_return_pct: float
    comparison_table: List[StrategyComparisonRow]


def run_strategy_comparison(
    symbol_candles_map: Dict[str, List[Candle]],
    initial_capital: float = 10000.0,
    brokerage_flat: float = 20.0,
    slippage_bps: float = 10.0,
) -> StrategyComparisonReport:
    """Runs Baseline Swing, Momentum, and Breakout strategies side-by-side with identical conditions."""
    strategies = [
        ("Baseline Swing (Trend-Pullback)", BaselineSwingStrategy()),
        ("Quantitative Momentum (RS & RVOL)", MomentumStrategy()),
        ("Donchian Breakout (20d Volume)", DonchianBreakoutStrategy()),
    ]

    rows: List[StrategyComparisonRow] = []

    # Calculate Benchmark Buy & Hold return across symbols
    bnh_returns = []
    start_str = ""
    end_str = ""

    for sym, candles in symbol_candles_map.items():
        if candles:
            if not start_str:
                start_str = candles[0].timestamp.strftime("%Y-%m-%d")
                end_str = candles[-1].timestamp.strftime("%Y-%m-%d")
            p_start = candles[0].open
            p_end = candles[-1].close
            if p_start > 0:
                bnh_returns.append(((p_end - p_start) / p_start) * 100.0)

    avg_bnh_return = round(float(sum(bnh_returns) / len(bnh_returns)), 2) if bnh_returns else 0.0

    for name, strat in strategies:
        engine = BacktestEngine(
            strategy=strat,
            initial_capital=initial_capital,
            brokerage_flat=brokerage_flat,
            slippage_bps=slippage_bps,
        )
        res: BacktestResult = engine.run(symbol_candles_map)
        m = res.metrics

        # Average holding period
        holding_bars_list = [t.holding_bars for t in res.trade_records if t.is_closed]
        avg_holding = round(float(sum(holding_bars_list) / len(holding_bars_list)), 1) if holding_bars_list else 0.0

        rows.append(
            StrategyComparisonRow(
                strategy_name=name,
                total_net_return_pct=m.total_return_pct,
                net_pnl_inr=m.net_pnl_inr,
                max_drawdown_pct=m.max_drawdown_pct,
                sharpe_ratio=m.sharpe_ratio,
                sortino_ratio=0.0,
                win_rate_pct=m.win_rate_pct,
                profit_factor=m.profit_factor,
                expectancy_inr=m.expectancy_inr,
                total_trades=m.total_trades,
                winning_trades=m.winning_trades,
                losing_trades=m.losing_trades,
                total_costs_inr=m.total_costs_paid_inr,
                average_holding_bars=avg_holding,
            )
        )

    return StrategyComparisonReport(
        initial_capital=initial_capital,
        test_symbols=list(symbol_candles_map.keys()),
        start_date=start_str,
        end_date=end_str,
        benchmark_buy_hold_return_pct=avg_bnh_return,
        comparison_table=rows,
    )
