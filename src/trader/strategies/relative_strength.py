"""Sector and Benchmark Relative Strength (RS) Strategy.
Evaluates equity price performance relative to the NIFTY 50 benchmark index.
Filters trades to only select equities showing clear alpha outperformance.
"""

from typing import Optional, Dict, Any
import pandas as pd

from trader.strategies.baseline import StrategySignal, SignalType


class SectorRelativeStrengthStrategy:
    """Relative Strength Momentum Strategy.
    Buys stocks with alpha > min_alpha relative to benchmark, confirmed by 20/50 SMA trend.
    """

    def __init__(
        self,
        lookback_bars: int = 20,
        min_alpha: float = 0.02, # 2% outperformance over lookback
        stop_atr_mult: float = 2.0,
        target_atr_mult: float = 4.0,
        max_holding_candles: int = 20,
    ):
        self.lookback_bars = lookback_bars
        self.min_alpha = min_alpha
        self.stop_atr_mult = stop_atr_mult
        self.target_atr_mult = target_atr_mult
        self.max_holding_candles = max_holding_candles
        self.name = "SectorRelativeStrengthStrategy"

    def compute_relative_strength(
        self,
        stock_df: pd.DataFrame,
        benchmark_df: Optional[pd.DataFrame] = None,
    ) -> float:
        """Computes stock return minus benchmark return over lookback_bars."""
        if len(stock_df) < self.lookback_bars + 1:
            return 0.0

        p_curr = float(stock_df["close"].iloc[-1])
        p_prev = float(stock_df["close"].iloc[-1 - self.lookback_bars])
        stock_ret = (p_curr - p_prev) / p_prev

        bm_ret = 0.0
        if benchmark_df is not None and len(benchmark_df) >= self.lookback_bars + 1:
            bm_curr = float(benchmark_df["close"].iloc[-1])
            bm_prev = float(benchmark_df["close"].iloc[-1 - self.lookback_bars])
            bm_ret = (bm_curr - bm_prev) / bm_prev

        return round(stock_ret - bm_ret, 4)

    def evaluate_entry(
        self,
        df_ind: pd.DataFrame,
        benchmark_df: Optional[pd.DataFrame] = None,
    ) -> Optional[StrategySignal]:
        """Evaluates entry based on Relative Strength Alpha + Technical Trend."""
        if len(df_ind) < 55:
            return None

        alpha = self.compute_relative_strength(df_ind, benchmark_df)
        if alpha < self.min_alpha:
            return None

        curr = df_ind.iloc[-1]
        c = float(curr["close"])
        low = float(curr["low"])
        ts = curr["timestamp"]
        sym = str(curr.get("symbol", "UNKNOWN")).upper()

        s_fast = float(curr.get("sma_20", 0.0))
        s_slow = float(curr.get("sma_50", 0.0))
        rsi = float(curr.get("rsi_14", 50.0))
        atr = float(curr.get("atr_14", 10.0))

        # Technical Trend Confirmation
        if not (c > s_fast and s_fast > s_slow):
            return None

        stop_loss = round(low - (atr * self.stop_atr_mult), 2)
        target = round(c + (atr * self.target_atr_mult), 2)

        return StrategySignal(
            symbol=sym,
            signal_type=SignalType.BUY,
            timestamp=ts,
            reference_close=c,
            reason=(
                f"Relative Strength Buy: Alpha={alpha*100:.2f}% vs Benchmark "
                f"(>= {self.min_alpha*100:.1f}%), Close > SMA20 > SMA50, RSI={rsi:.1f}"
            ),
            metrics={
                "alpha": alpha,
                "stop_loss": stop_loss,
                "target": target,
                "atr": atr,
                "rsi": rsi,
            },
        )

    def evaluate_exit(
        self,
        df_ind: pd.DataFrame,
        entry_price: float,
        stop_loss: float,
        target: Optional[float],
        holding_candles: int,
    ) -> Optional[StrategySignal]:
        """Exits on stop loss, target, or holding period."""
        if df_ind.empty:
            return None

        curr = df_ind.iloc[-1]
        c = float(curr["close"])
        low = float(curr["low"])
        high = float(curr["high"])
        ts = curr["timestamp"]
        sym = str(curr.get("symbol", "UNKNOWN")).upper()

        if low <= stop_loss:
            return StrategySignal(
                symbol=sym,
                signal_type=SignalType.SELL,
                timestamp=ts,
                reference_close=c,
                reason=f"Stop loss triggered: Low ({low:.2f}) <= Stop ({stop_loss:.2f})",
                metrics={"exit_price": stop_loss},
            )

        if target is not None and high >= target:
            return StrategySignal(
                symbol=sym,
                signal_type=SignalType.SELL,
                timestamp=ts,
                reference_close=c,
                reason=f"Profit target triggered: High ({high:.2f}) >= Target ({target:.2f})",
                metrics={"exit_price": target},
            )

        if holding_candles >= self.max_holding_candles:
            return StrategySignal(
                symbol=sym,
                signal_type=SignalType.SELL,
                timestamp=ts,
                reference_close=c,
                reason=f"Time exit: Max holding period ({self.max_holding_candles} bars) reached",
                metrics={"exit_price": c},
            )

        return None
