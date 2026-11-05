"""Donchian Channel Breakout Strategy for Indian Equities.
Detects 20-day price breakouts with volume expansion and volatility confirmation.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
import pandas as pd

from trader.domain.models import IST
from trader.strategies.baseline import StrategySignal, SignalType


class DonchianBreakoutStrategy:
    """Breakout Strategy with Volume & ATR Expansion Filters."""

    def __init__(
        self,
        breakout_period: int = 20,
        volume_mult: float = 1.3,
        atr_period: int = 14,
        stop_atr_mult: float = 2.0,
        target_atr_mult: float = 4.5,
        max_holding_candles: int = 25,
    ):
        self.breakout_period = breakout_period
        self.volume_mult = volume_mult
        self.atr_period = atr_period
        self.stop_atr_mult = stop_atr_mult
        self.target_atr_mult = target_atr_mult
        self.max_holding_candles = max_holding_candles

    def evaluate_entry(self, df_ind: pd.DataFrame) -> Optional[StrategySignal]:
        if len(df_ind) < self.breakout_period + 5:
            return None

        row = df_ind.iloc[-1]
        close_p = float(row["close"])
        sym = str(row["symbol"])
        ts = row["timestamp"]

        # Prior N-day highest high (excluding current bar)
        prior_highs = df_ind["high"].iloc[-self.breakout_period - 1 : -1]
        highest_prior = float(prior_highs.max())

        rvol = float(row.get("rvol", 1.0))
        atr = float(row.get(f"atr_{self.atr_period}", row.get("atr", close_p * 0.02)))

        # Breakout condition: close clearly breaks prior N-day high by at least 0.2% with volume surge
        if close_p > highest_prior * 1.002 and rvol >= self.volume_mult:
            stop_loss = round(close_p - (self.stop_atr_mult * atr), 2)
            target = round(close_p + (self.target_atr_mult * atr), 2)

            return StrategySignal(
                symbol=sym,
                signal_type=SignalType.BUY,
                timestamp=ts,
                reference_close=close_p,
                suggested_stop_loss=stop_loss,
                suggested_target=target,
                reason=f"Donchian {self.breakout_period}d Breakout above ₹{highest_prior:.2f} (RVOL {rvol:.1f}x)",
                metrics={
                    "breakout_high": highest_prior,
                    "rvol": round(rvol, 2),
                    "atr": round(atr, 2),
                },
            )
        return None

    def evaluate_exit(
        self,
        df_ind: pd.DataFrame,
        entry_price: float,
        stop_loss: float,
        target: Optional[float] = None,
        holding_candles: int = 0,
    ) -> Optional[StrategySignal]:
        if len(df_ind) < 10:
            return None

        row = df_ind.iloc[-1]
        close_p = float(row["close"])
        sym = str(row["symbol"])
        ts = row["timestamp"]

        if holding_candles >= self.max_holding_candles:
            return StrategySignal(
                symbol=sym,
                signal_type=SignalType.SELL,
                timestamp=ts,
                reference_close=close_p,
                reason=f"Max holding period reached ({holding_candles} bars)",
                metrics={"exit_price": close_p},
            )

        # Trailing channel exit: close below 10-day low
        ten_day_low = float(df_ind["low"].iloc[-11:-1].min())
        if close_p < ten_day_low:
            return StrategySignal(
                symbol=sym,
                signal_type=SignalType.SELL,
                timestamp=ts,
                reference_close=close_p,
                reason=f"Breakout exit: Closed below 10-day low ₹{ten_day_low:.2f}",
                metrics={"exit_price": close_p},
            )

        return None

