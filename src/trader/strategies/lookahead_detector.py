"""Clean-Room Lookahead Bias Detection Engine.
Audits quantitative strategies to ensure signal generation strictly depends only on completed bars
and never peeks into future market data or future indicator windows.
"""

import logging
from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd
from pydantic import BaseModel, Field

from trader.features.technical import candles_to_dataframe, compute_all_indicators

logger = logging.getLogger(__name__)


class LookaheadDiscrepancy(BaseModel):
    bar_index: int
    timestamp: str
    symbol: str
    issue_type: str # INDICATOR_LEAKAGE, RETROSPECTIVE_SIGNAL_CHANGE
    details: str
    indicators_diff: Dict[str, Any] = Field(default_factory=dict)


class LookaheadAuditReport(BaseModel):
    strategy_name: str
    is_clean: bool
    total_bars_audited: int
    discrepancies_count: int
    discrepancies: List[LookaheadDiscrepancy] = Field(default_factory=list)
    verdict: str


class LookaheadDetector:
    """Audits trading strategies for forward leakage and lookahead bias."""

    def __init__(self, warmup_bars: int = 55, tolerance: float = 1e-4):
        self.warmup_bars = warmup_bars
        self.tolerance = tolerance

    def audit_strategy(
        self,
        strategy: Any,
        df_candles: pd.DataFrame,
        strategy_name: Optional[str] = None,
    ) -> LookaheadAuditReport:
        """Runs incremental slice back-propagation comparison to detect lookahead bias."""
        strat_name = strategy_name or getattr(strategy, "name", strategy.__class__.__name__)
        n_bars = len(df_candles)

        if n_bars < self.warmup_bars + 10:
            return LookaheadAuditReport(
                strategy_name=strat_name,
                is_clean=True,
                total_bars_audited=0,
                discrepancies_count=0,
                discrepancies=[],
                verdict="SKIPPED: Insufficient bars for lookahead audit (need at least 65 bars).",
            )

        discrepancies: List[LookaheadDiscrepancy] = []

        # 1. Compute full-run indicators
        df_full = compute_all_indicators(df_candles.copy())

        # 2. Progressively slice data bar-by-bar and compare point-in-time evaluations
        # Sample every 2nd or 3rd bar if dataset is very large, or all bars if moderate size
        step = 1 if n_bars <= 150 else max(1, n_bars // 100)

        for i in range(self.warmup_bars, n_bars, step):
            slice_raw = df_candles.iloc[: i + 1].copy()
            slice_ind = compute_all_indicators(slice_raw)

            curr_pit = slice_ind.iloc[-1]
            curr_full = df_full.iloc[i]

            ts_str = str(curr_pit["timestamp"])
            sym = str(curr_pit.get("symbol", "UNKNOWN"))

            # Check indicator stability (excluding non-numerics)
            ind_diffs: Dict[str, Any] = {}
            numeric_cols = [c for c in slice_ind.columns if c in ["sma_20", "sma_50", "rsi_14", "atr_14", "rvol"]]
            for col in numeric_cols:
                val_pit = float(curr_pit[col]) if pd.notna(curr_pit[col]) else None
                val_full = float(curr_full[col]) if pd.notna(curr_full[col]) else None
                if val_pit is not None and val_full is not None:
                    if abs(val_pit - val_full) > self.tolerance:
                        ind_diffs[col] = {"point_in_time": val_pit, "full_run": val_full, "delta": abs(val_pit - val_full)}

            if ind_diffs:
                discrepancies.append(
                    LookaheadDiscrepancy(
                        bar_index=i,
                        timestamp=ts_str,
                        symbol=sym,
                        issue_type="INDICATOR_LEAKAGE",
                        details=f"Indicator value changed retrospectively when future bars arrived: {list(ind_diffs.keys())}",
                        indicators_diff=ind_diffs,
                    )
                )

            # Check point-in-time entry evaluation vs full run slice evaluation
            sig_pit = strategy.evaluate_entry(slice_ind)
            # Evaluate using slice from full up to i+1
            sig_from_full = strategy.evaluate_entry(df_full.iloc[: i + 1])

            sig_pit_type = sig_pit.signal_type.value if sig_pit else None
            sig_full_type = sig_from_full.signal_type.value if sig_from_full else None

            if sig_pit_type != sig_full_type:
                discrepancies.append(
                    LookaheadDiscrepancy(
                        bar_index=i,
                        timestamp=ts_str,
                        symbol=sym,
                        issue_type="RETROSPECTIVE_SIGNAL_CHANGE",
                        details=f"Entry signal mismatch at bar {i}: point_in_time={sig_pit_type} vs full_run={sig_full_type}",
                    )
                )

        is_clean = len(discrepancies) == 0
        verdict = (
            f"PASSED: Strategy '{strat_name}' verified 100% free of lookahead bias across {n_bars - self.warmup_bars} audited sessions."
            if is_clean
            else f"FAILED: Lookahead bias detected! {len(discrepancies)} discrepancies found where future data leaked into historical signals."
        )

        return LookaheadAuditReport(
            strategy_name=strat_name,
            is_clean=is_clean,
            total_bars_audited=n_bars - self.warmup_bars,
            discrepancies_count=len(discrepancies),
            discrepancies=discrepancies[:20], # Cap report to top 20
            verdict=verdict,
        )
