"""Cross-Sectional Momentum & Relative Strength Strategy.
Selects leading Indian equities based on 20-day, 50-day momentum,
volatility-adjusted strength, and relative volume confirmation.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
import pandas as pd
import numpy as np

from trader.domain.models import IST
from trader.strategies.baseline import StrategySignal, SignalType


class MomentumStrategy:
    """Quantitative Momentum and Trend Persistence Strategy."""

    def __init__(
        self,
        lookback_momentum: int = 20,
        min_momentum_pct: float = 0.03,  # Minimum 3% 20d return
        rvol_min: float = 1.1,
        rsi_min: float = 50.0,
        rsi_max: float = 75.0,
        atr_period: int = 14,
        stop_atr_mult: float = 2.0,
        target_atr_mult: float = 4.0,
        max_holding_candles: int = 20,
    ):
        self.lookback_momentum = lookback_momentum
        self.min_momentum_pct = min_momentum_pct
        self.rvol_min = rvol_min
        self.rsi_min = rsi_min
        self.rsi_max = rsi_max
        self.atr_period = atr_period
        self.stop_atr_mult = stop_atr_mult
        self.target_atr_mult = target_atr_mult
        self.max_holding_candles = max_holding_candles

    def evaluate_entry(self, df_ind: pd.DataFrame) -> Optional[StrategySignal]:
        """Evaluates entry signal on candle close."""
        if len(df_ind) < max(self.lookback_momentum + 5, 50):
            return None

        row = df_ind.iloc[-1]
        close_p = float(row["close"])
        sym = str(row["symbol"])
        ts = row["timestamp"]

        # Calculate momentum: price change over lookback period
        past_close = float(df_ind["close"].iloc[-self.lookback_momentum])
        momentum_pct = (close_p - past_close) / past_close

        # Volatility-adjusted momentum (Sharpe-like metric)
        atr = float(row.get(f"atr_{self.atr_period}", row.get("atr", close_p * 0.02)))
        vol_adj_mom = momentum_pct / (atr / close_p) if atr > 0 else 0.0

        rvol = float(row.get("rvol", 1.0))
        rsi = float(row.get(f"rsi_{self.atr_period}", row.get("rsi", 55.0)))
        sma20 = float(row.get("sma_20", close_p))
        sma50 = float(row.get("sma_50", close_p))

        # Core quantitative momentum conditions:
        # 1. 20-day return >= min_momentum_pct
        # 2. Trend alignment: close > sma20 >= sma50
        # 3. Healthy RSI (not overbought or collapsing)
        # 4. Relative volume confirmation
        if (
            momentum_pct >= self.min_momentum_pct
            and close_p > sma20
            and sma20 >= sma50
            and self.rsi_min <= rsi <= self.rsi_max
            and rvol >= self.rvol_min
        ):
            stop_loss = round(close_p - (self.stop_atr_mult * atr), 2)
            target = round(close_p + (self.target_atr_mult * atr), 2)

            return StrategySignal(
                symbol=sym,
                signal_type=SignalType.BUY,
                timestamp=ts,
                reference_close=close_p,
                suggested_stop_loss=stop_loss,
                suggested_target=target,
                reason=f"Strong Momentum: 20d +{momentum_pct:.1%}, VolAdjMom {vol_adj_mom:.2f}, RVOL {rvol:.1f}x",
                metrics={
                    "momentum_pct": round(momentum_pct, 4),
                    "vol_adj_mom": round(vol_adj_mom, 2),
                    "rvol": round(rvol, 2),
                    "rsi": round(rsi, 2),
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
        """Evaluates technical exit conditions on candle close."""
        if len(df_ind) == 0:
            return None

        row = df_ind.iloc[-1]
        close_p = float(row["close"])
        sym = str(row["symbol"])
        ts = row["timestamp"]
        sma20 = float(row.get("sma_20", close_p))

        # 1. Time-based exit
        if holding_candles >= self.max_holding_candles:
            return StrategySignal(
                symbol=sym,
                signal_type=SignalType.SELL,
                timestamp=ts,
                reference_close=close_p,
                reason=f"Max holding period reached ({holding_candles} bars)",
                metrics={"exit_price": close_p},
            )

        # 2. Trend trailing exit: close falls below 20-day SMA
        if close_p < sma20:
            return StrategySignal(
                symbol=sym,
                signal_type=SignalType.SELL,
                timestamp=ts,
                reference_close=close_p,
                reason=f"Trend breakdown: close ({close_p}) < 20 SMA ({sma20})",
                metrics={"exit_price": close_p},
            )

        return None

