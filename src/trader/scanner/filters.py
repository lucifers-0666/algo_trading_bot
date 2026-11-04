"""Stock Scanner Filters and Candidate Definitions.
Implements individual scanning rules for movers, relative volume, momentum,
trend strength, volatility, liquidity, and unusual activity with transparent reasoning.
"""

from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
import pandas as pd

from trader.domain.models import IST


class ScanCandidate(BaseModel):
    """Represents a screened stock candidate with transparent explanation."""
    symbol: str
    latest_price: float
    pct_change_1d: float
    volume: float
    rvol: float
    indicators: Dict[str, float] = Field(default_factory=dict)
    timestamp: datetime
    source: str
    scan_category: str
    is_qualified: bool = True
    inclusion_reasons: List[str] = Field(default_factory=list)
    exclusion_reasons: List[str] = Field(default_factory=list)


def evaluate_liquidity(
    row: pd.Series,
    min_price: float = 20.0,
    min_daily_turnover: float = 5000000.0,
) -> tuple[bool, List[str], List[str]]:
    """Checks whether a stock qualifies under fundamental liquidity constraints."""
    close = float(row.get("close", 0.0))
    turnover = float(row.get("turnover_sma_20", row.get("turnover", 0.0)))

    reasons = []
    excluded = []

    if close < min_price:
        excluded.append(f"Penny stock filter: Price ₹{close:.2f} < ₹{min_price:.2f}")
    if turnover < min_daily_turnover:
        excluded.append(f"Low liquidity: 20-day avg turnover ₹{turnover:,.0f} < ₹{min_daily_turnover:,.0f}")

    is_qualified = len(excluded) == 0
    if is_qualified:
        reasons.append(f"Liquid: Price ₹{close:.2f}, 20-day turnover ₹{turnover:,.0f}")

    return is_qualified, reasons, excluded


def scan_symbol_metrics(df_with_indicators: pd.DataFrame) -> Optional[Dict[str, Any]]:
    """Extracts the latest row and vital metrics for screening."""
    if df_with_indicators.empty:
        return None
    latest = df_with_indicators.iloc[-1]
    prev_close = df_with_indicators.iloc[-2]["close"] if len(df_with_indicators) > 1 else latest["open"]

    pct_1d = (latest["close"] - prev_close) / prev_close if prev_close > 0 else 0.0
    rvol = float(latest.get("rvol", 1.0)) if pd.notna(latest.get("rvol")) else 1.0

    return {
        "symbol": str(latest["symbol"]).upper(),
        "latest_price": round(float(latest["close"]), 2),
        "pct_change_1d": round(float(pct_1d), 4),
        "volume": float(latest["volume"]),
        "rvol": round(float(rvol), 2),
        "timestamp": latest["timestamp"],
        "source": str(latest.get("source", "synthetic")),
        "indicators": {
            "sma_20": round(float(latest.get("sma_20", 0.0)), 2) if pd.notna(latest.get("sma_20")) else 0.0,
            "sma_50": round(float(latest.get("sma_50", 0.0)), 2) if pd.notna(latest.get("sma_50")) else 0.0,
            "rsi_14": round(float(latest.get("rsi_14", 50.0)), 2) if pd.notna(latest.get("rsi_14")) else 50.0,
            "atr_14": round(float(latest.get("atr_14", 0.0)), 2) if pd.notna(latest.get("atr_14")) else 0.0,
            "atr_pct": round(float(latest.get("atr_pct", 0.0)), 4) if pd.notna(latest.get("atr_pct")) else 0.0,
        },
        "row": latest,
    }
