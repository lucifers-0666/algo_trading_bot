"""Unit tests for Strategy Hyperparameter Optimization (Hyperopt) Runner."""

from tests.fixtures.synthetic_fixture import generate_synthetic_candles
from trader.strategies.hyperopt import StrategyHyperoptRunner, default_loss_function


def test_strategy_hyperopt_runner():
    candles_rel = generate_synthetic_candles("RELIANCE", num_days=100, seed=42)
    candles_tcs = generate_synthetic_candles("TCS", num_days=100, seed=123)
    dataset = {"RELIANCE": candles_rel, "TCS": candles_tcs}

    runner = StrategyHyperoptRunner(initial_capital=10000.0)

    # Mini grid
    param_grid = {
        "sma_fast": [20],
        "sma_slow": [50],
        "rsi_min": [40.0, 45.0],
        "stop_atr_mult": [2.0],
    }

    report = runner.optimize_baseline(dataset, param_grid=param_grid, max_trials=2)
    assert report.strategy_name == "BaselineSwingStrategy"
    assert report.trials_evaluated == 2
    assert len(report.leaderboard) == 2
    assert "total_return_pct" in report.best_metrics

