"""News-Enhanced Quantitative Swing Trading Strategy.
Synthesizes technical trend filters (SMA 20/50, RSI) with live financial intelligence sentiment scores.
Requires confirmed positive news catalysts before allowing new swing long entries.
"""

from typing import Optional, Dict, Any
import pandas as pd

from trader.strategies.baseline import StrategySignal, SignalType


class NewsSentimentStrategy:
    """Quantitative swing strategy requiring technical trend confirmation + positive news sentiment."""

    def __init__(
        self,
        min_sentiment_score: float = 0.20,
        rsi_min: float = 45.0,
        rsi_max: float = 68.0,
        stop_atr_mult: float = 2.0,
        target_atr_mult: float = 4.0,
        max_holding_candles: int = 15,
    ):
        self.min_sentiment_score = min_sentiment_score
        self.rsi_min = rsi_min
        self.rsi_max = rsi_max
        self.stop_atr_mult = stop_atr_mult
        self.target_atr_mult = target_atr_mult
        self.max_holding_candles = max_holding_candles
        self.name = "NewsSentimentStrategy"

    def evaluate_entry(
        self,
        df_ind: pd.DataFrame,
        sentiment_score: float = 0.0,
    ) -> Optional[StrategySignal]:
        """Evaluates entry condition requiring both technical confirmation and positive sentiment."""
        if len(df_ind) < 55:
            return None

        # 1. Sentiment Gate
        if sentiment_score < self.min_sentiment_score:
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

        # 2. Technical Trend Confirmation
        if not (c > s_fast and s_fast > s_slow):
            return None

        # 3. RSI Momentum Bounds
        if not (self.rsi_min <= rsi <= self.rsi_max):
            return None

        stop_loss = round(low - (atr * self.stop_atr_mult), 2)
        target = round(c + (atr * self.target_atr_mult), 2)

        return StrategySignal(
            symbol=sym,
            signal_type=SignalType.BUY,
            timestamp=ts,
            reference_close=c,
            reason=(
                f"News-Enhanced Buy: Tech uptrend (C > SMA20 > SMA50), RSI={rsi:.1f}, "
                f"Sentiment={sentiment_score:.2f} >= {self.min_sentiment_score:.2f}"
            ),
            metrics={
                "stop_loss": stop_loss,
                "target": target,
                "sentiment_score": sentiment_score,
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
        """Exit conditions based on stops, targets, or trend break."""
        if df_ind.empty:
            return None

        curr = df_ind.iloc[-1]
        c = float(curr["close"])
        low = float(curr["low"])
        high = float(curr["high"])
        s_slow = float(curr.get("sma_50", 0.0))
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

        if s_slow > 0 and c < s_slow:
            return StrategySignal(
                symbol=sym,
                signal_type=SignalType.SELL,
                timestamp=ts,
                reference_close=c,
                reason=f"Trend break exit: Close ({c:.2f}) < SMA50 ({s_slow:.2f})",
                metrics={"exit_price": c},
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

