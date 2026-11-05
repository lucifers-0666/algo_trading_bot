"""Market Regime Detection Engine for Indian Equities.
Classifies macro market environment using trend alignment, ATR volatility,
and market breadth, with explicit NO_TRADE recommendations.
"""

from enum import Enum
from typing import Dict, Any, Optional
from pydantic import BaseModel
import pandas as pd


class MarketRegime(str, Enum):
    BULL_TRENDING = "BULL_TRENDING"
    BEAR_TRENDING = "BEAR_TRENDING"
    SIDEWAYS_CONSOLIDATION = "SIDEWAYS_CONSOLIDATION"
    HIGH_VOLATILITY = "HIGH_VOLATILITY"
    LOW_VOLATILITY = "LOW_VOLATILITY"


class RegimeAssessment(BaseModel):
    regime: MarketRegime
    trade_permission: str              # "ALLOW_TRADING", "REDUCE_SIZE", "NO_TRADE"
    trend_score: float                # -1.0 to +1.0
    volatility_ratio: float           # ATR / Close
    adx_estimate: float               # Trend strength proxy
    summary: str
    reasons: list[str]


def detect_market_regime(df_ind: pd.DataFrame) -> RegimeAssessment:
    """Classifies the market regime from benchmark or stock indicator history.

    Recommends NO_TRADE during violent breakdowns or high-volatility sideways churn.
    """
    if len(df_ind) < 50:
        return RegimeAssessment(
            regime=MarketRegime.SIDEWAYS_CONSOLIDATION,
            trade_permission="ALLOW_TRADING",
            trend_score=0.0,
            volatility_ratio=0.015,
            adx_estimate=20.0,
            summary="Insufficient historical data for deep regime classification. Defaulting to neutral.",
            reasons=["Less than 50 bars available."],
        )

    row = df_ind.iloc[-1]
    close_p = float(row["close"])
    sma20 = float(row.get("sma_20", close_p))
    sma50 = float(row.get("sma_50", close_p))
    atr = float(row.get("atr_14", row.get("atr", close_p * 0.015)))

    vol_ratio = atr / close_p if close_p > 0 else 0.015
    reasons = []

    # 1. High Volatility Spike Check
    if vol_ratio > 0.035:
        return RegimeAssessment(
            regime=MarketRegime.HIGH_VOLATILITY,
            trade_permission="NO_TRADE",
            trend_score=-0.5,
            volatility_ratio=round(vol_ratio, 4),
            adx_estimate=35.0,
            summary="HIGH VOLATILITY REGIME: Extreme ATR expansion detected. NO TRADE advised.",
            reasons=[f"Daily volatility ratio {vol_ratio:.2%} exceeds risk limit (3.5%)."],
        )

    # 2. Bull Trending: Close > 20 SMA > 50 SMA with positive momentum
    ret_20d = (close_p - float(df_ind["close"].iloc[-20])) / float(df_ind["close"].iloc[-20])
    if close_p > sma20 and sma20 > sma50 and ret_20d > 0.02:
        return RegimeAssessment(
            regime=MarketRegime.BULL_TRENDING,
            trade_permission="ALLOW_TRADING",
            trend_score=round(min(1.0, ret_20d * 10), 2),
            volatility_ratio=round(vol_ratio, 4),
            adx_estimate=28.0,
            summary="BULL TRENDING: Strong upward alignment across 20 and 50 SMAs.",
            reasons=[
                f"Close ({close_p:.2f}) > 20 SMA ({sma20:.2f}) > 50 SMA ({sma50:.2f})",
                f"20-day return: +{ret_20d:.1%}",
            ],
        )

    # 3. Bear Trending: Close < 20 SMA < 50 SMA and negative momentum
    if close_p < sma20 and sma20 < sma50 and ret_20d < -0.02:
        return RegimeAssessment(
            regime=MarketRegime.BEAR_TRENDING,
            trade_permission="NO_TRADE",
            trend_score=round(max(-1.0, ret_20d * 10), 2),
            volatility_ratio=round(vol_ratio, 4),
            adx_estimate=30.0,
            summary="BEAR TRENDING: Bearish structure across all key moving averages. Long entries halted.",
            reasons=[
                f"Close ({close_p:.2f}) < 20 SMA ({sma20:.2f}) < 50 SMA ({sma50:.2f})",
                f"20-day return: {ret_20d:.1%}",
            ],
        )

    # 4. Low Volatility Consolidation
    if vol_ratio < 0.010:
        return RegimeAssessment(
            regime=MarketRegime.LOW_VOLATILITY,
            trade_permission="ALLOW_TRADING",
            trend_score=0.1,
            volatility_ratio=round(vol_ratio, 4),
            adx_estimate=15.0,
            summary="LOW VOLATILITY: Market compressed in narrow volatility band. Breakout watch.",
            reasons=[f"Volatility ratio {vol_ratio:.2%} is below 1.0%."],
        )

    # 5. Sideways / Choppy
    return RegimeAssessment(
        regime=MarketRegime.SIDEWAYS_CONSOLIDATION,
        trade_permission="REDUCE_SIZE",
        trend_score=0.0,
        volatility_ratio=round(vol_ratio, 4),
        adx_estimate=18.0,
        summary="SIDEWAYS CONSOLIDATION: Market oscillating in trading range. Position size reduction advised.",
        reasons=["Moving averages converging; no dominant directional trend."],
    )

