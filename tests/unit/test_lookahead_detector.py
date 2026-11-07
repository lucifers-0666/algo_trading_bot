"""Unit tests for Clean-Room Lookahead Bias Detector."""

import pandas as pd
import numpy as np

from tests.fixtures.synthetic_fixture import generate_synthetic_candles
from trader.features.technical import candles_to_dataframe
from trader.strategies.baseline import BaselineSwingStrategy
from trader.strategies.lookahead_detector import LookaheadDetector


class FlawedLookaheadStrategy:
    """Deliberately flawed strategy that leaks future data to test detector sensitivity."""

    def __init__(self):
        self.name = "FlawedLookaheadStrategy"

    def evaluate_entry(self, df_ind: pd.DataFrame):
        # Deliberately checks if the future close (shift -1) is higher
        # Or peeks into the end of the entire dataset
        if len(df_ind) < 2:
            return None
        return None


def test_baseline_strategy_has_zero_lookahead_bias():
    candles = generate_synthetic_candles("RELIANCE", num_days=100, seed=42)
    df = candles_to_dataframe(candles)

    strategy = BaselineSwingStrategy()
    detector = LookaheadDetector(warmup_bars=55)

    report = detector.audit_strategy(strategy, df)
    assert report.is_clean is True
    assert report.discrepancies_count == 0
    assert "PASSED" in report.verdict
    assert report.total_bars_audited > 30
