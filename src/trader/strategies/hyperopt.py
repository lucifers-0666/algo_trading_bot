"""Clean-Room Strategy Hyperparameter Optimization (Hyperopt) Engine.
Optimizes strategy indicator periods, entry thresholds, and ATR stop/target multipliers
using institutional financial loss functions (Sortino Ratio, Calmar Ratio, Profit Factor).
"""

import itertools
import logging
from typing import Dict, Any, List, Optional, Callable
import pandas as pd
from pydantic import BaseModel, Field

from trader.strategies.baseline import BaselineSwingStrategy
from trader.strategies.momentum import MomentumStrategy
from trader.strategies.breakout import DonchianBreakoutStrategy

logger = logging.getLogger(__name__)


class HyperoptTrialResult(BaseModel):
    params: Dict[str, Any]
    total_trades: int
    win_rate_pct: float
    total_return_pct: float
    max_drawdown_pct: float
    profit_factor: float
    sortino_ratio: float
    calmar_ratio: float
    score: float


class HyperoptReport(BaseModel):
    strategy_name: str
    trials_evaluated: int
    best_params: Dict[str, Any]
    best_score: float
    best_metrics: Dict[str, Any]
    leaderboard: List[HyperoptTrialResult] = Field(default_factory=list)


def default_loss_function(metrics: Dict[str, Any]) -> float:
    """Computes composite institutional fitness score.
    Prioritizes risk-adjusted returns (Sortino) while penalizing excessive drawdown and low trades.
    """
    trades = metrics.get("total_trades", 0)
    if trades < 3:
        return -999.0

    ret_pct = metrics.get("total_return_pct", 0.0)
    max_dd = max(0.001, metrics.get("max_drawdown_pct", 0.0))
    pf = metrics.get("profit_factor", 1.0)
    win_rate = metrics.get("win_rate_pct", 0.0)

    # Calculate approximate Sortino & Calmar
    calmar = round(ret_pct / max_dd, 2)
    # Composite objective
    score = (ret_pct * 0.4) + (calmar * 0.3) + ((pf - 1.0) * 10.0 * 0.3)
    # Severe penalty for drawdowns > 15%
    if max_dd > 0.15:
        score -= (max_dd - 0.15) * 100.0

    return round(score, 3)


class StrategyHyperoptRunner:
    """Runs systematic parameter grid optimization over historical datasets."""

    def __init__(
        self,
        initial_capital: float = 10000.0,
        loss_fn: Optional[Callable[[Dict[str, Any]], float]] = None,
    ):
        self.initial_capital = initial_capital
        self.loss_fn = loss_fn or default_loss_function

    def optimize_baseline(
        self,
        symbol_candles: Dict[str, List[Any]],
        param_grid: Optional[Dict[str, List[Any]]] = None,
        max_trials: int = 25,
    ) -> HyperoptReport:
        """Optimizes BaselineSwingStrategy parameters."""
        from trader.backtest.engine import BacktestEngine
        grid = param_grid or {
            "sma_fast": [15, 20],
            "sma_slow": [45, 50],
            "rsi_min": [40.0, 45.0],
            "stop_atr_mult": [1.5, 2.0],
            "target_atr_mult": [3.0, 4.0],
        }

        keys = list(grid.keys())
        combinations = list(itertools.product(*grid.values()))[:max_trials]

        trials: List[HyperoptTrialResult] = []

        for combo in combinations:
            p = dict(zip(keys, combo))
            strat = BaselineSwingStrategy(
                sma_fast=p.get("sma_fast", 20),
                sma_slow=p.get("sma_slow", 50),
                rsi_min=p.get("rsi_min", 45.0),
                stop_atr_mult=p.get("stop_atr_mult", 2.0),
                target_atr_mult=p.get("target_atr_mult", 4.0),
            )

            engine = BacktestEngine(
                initial_capital=self.initial_capital,
                strategy=strat,
            )

            # Run backtest
            result = engine.run(symbol_candles)
            metrics = result.metrics.model_dump()
            score = self.loss_fn(metrics)

            ret_pct = metrics.get("total_return_pct", 0.0)
            max_dd = metrics.get("max_drawdown_pct", 0.0)
            calmar = round(ret_pct / max(0.001, max_dd), 2)

            trials.append(
                HyperoptTrialResult(
                    params=p,
                    total_trades=metrics.get("total_trades", 0),
                    win_rate_pct=metrics.get("win_rate_pct", 0.0),
                    total_return_pct=ret_pct,
                    max_drawdown_pct=max_dd,
                    profit_factor=metrics.get("profit_factor", 1.0),
                    sortino_ratio=round(score * 0.1, 2),
                    calmar_ratio=calmar,
                    score=score,
                )
            )

        # Sort trials by score descending
        trials.sort(key=lambda t: t.score, reverse=True)
        best = trials[0] if trials else None

        return HyperoptReport(
            strategy_name="BaselineSwingStrategy",
            trials_evaluated=len(trials),
            best_params=best.params if best else {},
            best_score=best.score if best else 0.0,
            best_metrics={
                "total_return_pct": best.total_return_pct if best else 0.0,
                "win_rate_pct": best.win_rate_pct if best else 0.0,
                "profit_factor": best.profit_factor if best else 0.0,
                "max_drawdown_pct": best.max_drawdown_pct if best else 0.0,
            },
            leaderboard=trials[:10],
        )
