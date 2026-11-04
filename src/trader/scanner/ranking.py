"""Market Scanner Engine and Ranking Logic.
Executes scans across historical/live symbol datasets and produces ranked candidate lists.
"""

from typing import List, Dict, Any, Optional
import pandas as pd

from trader.features.technical import candles_to_dataframe, compute_all_indicators
from trader.scanner.filters import (
    ScanCandidate,
    scan_symbol_metrics,
    evaluate_liquidity,
)
from trader.providers.base import MarketDataProvider


class MarketScannerEngine:
    """Orchestrates multi-strategy screening across the NSE universe."""

    def __init__(self, provider: MarketDataProvider, symbols: Optional[List[str]] = None):
        self.provider = provider
        self.symbols = symbols or ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK", "SBIN", "TATAMOTORS", "BHARTIARTL", "ITC", "KOTAKBANK"]

    def _prepare_symbol_metrics(self, symbol: str) -> Optional[Dict[str, Any]]:
        candles = self.provider.get_historical_candles(symbol)
        if len(candles) < 25:
            return None
        df = candles_to_dataframe(candles)
        df_ind = compute_all_indicators(df)
        return scan_symbol_metrics(df_ind)

    def scan_top_gainers(self, limit: int = 10) -> List[ScanCandidate]:
        candidates: List[ScanCandidate] = []
        for sym in self.symbols:
            m = self._prepare_symbol_metrics(sym)
            if not m:
                continue

            row = m["row"]
            is_liq, liq_inc, liq_exc = evaluate_liquidity(row)
            inc_reasons = list(liq_inc)
            exc_reasons = list(liq_exc)

            if m["pct_change_1d"] > 0:
                inc_reasons.append(f"Gainer: +{m['pct_change_1d']:.2%} 1-day change")
            else:
                exc_reasons.append(f"Negative/flat return: {m['pct_change_1d']:.2%}")

            cand = ScanCandidate(
                symbol=m["symbol"],
                latest_price=m["latest_price"],
                pct_change_1d=m["pct_change_1d"],
                volume=m["volume"],
                rvol=m["rvol"],
                indicators=m["indicators"],
                timestamp=m["timestamp"],
                source=m["source"],
                scan_category="Top Gainers",
                is_qualified=is_liq and (m["pct_change_1d"] > 0),
                inclusion_reasons=inc_reasons,
                exclusion_reasons=exc_reasons,
            )
            candidates.append(cand)

        # Sort descending by 1-day return
        candidates.sort(key=lambda c: c.pct_change_1d, reverse=True)
        return candidates[:limit]

    def scan_top_losers(self, limit: int = 10) -> List[ScanCandidate]:
        candidates: List[ScanCandidate] = []
        for sym in self.symbols:
            m = self._prepare_symbol_metrics(sym)
            if not m:
                continue

            row = m["row"]
            is_liq, liq_inc, liq_exc = evaluate_liquidity(row)
            inc_reasons = list(liq_inc)
            exc_reasons = list(liq_exc)

            if m["pct_change_1d"] < 0:
                inc_reasons.append(f"Loser: {m['pct_change_1d']:.2%} 1-day drop")
            else:
                exc_reasons.append(f"Positive/flat return: {m['pct_change_1d']:.2%}")

            cand = ScanCandidate(
                symbol=m["symbol"],
                latest_price=m["latest_price"],
                pct_change_1d=m["pct_change_1d"],
                volume=m["volume"],
                rvol=m["rvol"],
                indicators=m["indicators"],
                timestamp=m["timestamp"],
                source=m["source"],
                scan_category="Top Losers",
                is_qualified=is_liq and (m["pct_change_1d"] < 0),
                inclusion_reasons=inc_reasons,
                exclusion_reasons=exc_reasons,
            )
            candidates.append(cand)

        # Sort ascending by 1-day return (biggest drop first)
        candidates.sort(key=lambda c: c.pct_change_1d, reverse=False)
        return candidates[:limit]

    def scan_relative_volume(self, min_rvol: float = 1.3, limit: int = 10) -> List[ScanCandidate]:
        candidates: List[ScanCandidate] = []
        for sym in self.symbols:
            m = self._prepare_symbol_metrics(sym)
            if not m:
                continue

            row = m["row"]
            is_liq, liq_inc, liq_exc = evaluate_liquidity(row)
            inc_reasons = list(liq_inc)
            exc_reasons = list(liq_exc)

            if m["rvol"] >= min_rvol:
                inc_reasons.append(f"High Relative Volume: {m['rvol']:.2f}x of 20-day average")
            else:
                exc_reasons.append(f"Sub-threshold RVOL: {m['rvol']:.2f}x < {min_rvol}x threshold")

            cand = ScanCandidate(
                symbol=m["symbol"],
                latest_price=m["latest_price"],
                pct_change_1d=m["pct_change_1d"],
                volume=m["volume"],
                rvol=m["rvol"],
                indicators=m["indicators"],
                timestamp=m["timestamp"],
                source=m["source"],
                scan_category="Relative Volume (RVOL)",
                is_qualified=is_liq and (m["rvol"] >= min_rvol),
                inclusion_reasons=inc_reasons,
                exclusion_reasons=exc_reasons,
            )
            candidates.append(cand)

        candidates.sort(key=lambda c: c.rvol, reverse=True)
        return candidates[:limit]

    def scan_momentum(self, limit: int = 10) -> List[ScanCandidate]:
        candidates: List[ScanCandidate] = []
        for sym in self.symbols:
            m = self._prepare_symbol_metrics(sym)
            if not m:
                continue

            row = m["row"]
            is_liq, liq_inc, liq_exc = evaluate_liquidity(row)
            inc_reasons = list(liq_inc)
            exc_reasons = list(liq_exc)

            rsi = m["indicators"]["rsi_14"]
            if rsi >= 50.0:
                inc_reasons.append(f"Bullish momentum: RSI 14 = {rsi:.1f} (>= 50)")
            else:
                exc_reasons.append(f"Weak momentum: RSI 14 = {rsi:.1f} (< 50)")

            cand = ScanCandidate(
                symbol=m["symbol"],
                latest_price=m["latest_price"],
                pct_change_1d=m["pct_change_1d"],
                volume=m["volume"],
                rvol=m["rvol"],
                indicators=m["indicators"],
                timestamp=m["timestamp"],
                source=m["source"],
                scan_category="Momentum",
                is_qualified=is_liq and (rsi >= 50.0),
                inclusion_reasons=inc_reasons,
                exclusion_reasons=exc_reasons,
            )
            candidates.append(cand)

        candidates.sort(key=lambda c: c.indicators.get("rsi_14", 0.0), reverse=True)
        return candidates[:limit]

    def scan_trend_strength(self, limit: int = 10) -> List[ScanCandidate]:
        candidates: List[ScanCandidate] = []
        for sym in self.symbols:
            m = self._prepare_symbol_metrics(sym)
            if not m:
                continue

            row = m["row"]
            is_liq, liq_inc, liq_exc = evaluate_liquidity(row)
            inc_reasons = list(liq_inc)
            exc_reasons = list(liq_exc)

            p = m["latest_price"]
            s20 = m["indicators"]["sma_20"]
            s50 = m["indicators"]["sma_50"]

            is_trend = (p > s20) and (s20 > s50)
            if is_trend:
                inc_reasons.append(f"Aligned Uptrend: Price ({p}) > SMA20 ({s20}) > SMA50 ({s50})")
            else:
                exc_reasons.append(f"Non-trending: Price ({p}), SMA20 ({s20}), SMA50 ({s50}) not aligned")

            cand = ScanCandidate(
                symbol=m["symbol"],
                latest_price=m["latest_price"],
                pct_change_1d=m["pct_change_1d"],
                volume=m["volume"],
                rvol=m["rvol"],
                indicators=m["indicators"],
                timestamp=m["timestamp"],
                source=m["source"],
                scan_category="Trend Strength",
                is_qualified=is_liq and is_trend,
                inclusion_reasons=inc_reasons,
                exclusion_reasons=exc_reasons,
            )
            candidates.append(cand)

        return candidates[:limit]

    def scan_volatility(self, min_atr_pct: float = 0.02, limit: int = 10) -> List[ScanCandidate]:
        candidates: List[ScanCandidate] = []
        for sym in self.symbols:
            m = self._prepare_symbol_metrics(sym)
            if not m:
                continue

            row = m["row"]
            is_liq, liq_inc, liq_exc = evaluate_liquidity(row)
            inc_reasons = list(liq_inc)
            exc_reasons = list(liq_exc)

            atr_pct = m["indicators"]["atr_pct"]
            if atr_pct >= min_atr_pct:
                inc_reasons.append(f"Active Volatility: ATR/Price = {atr_pct:.2%} (>= {min_atr_pct:.2%})")
            else:
                exc_reasons.append(f"Low Volatility: ATR/Price = {atr_pct:.2%} (< {min_atr_pct:.2%})")

            cand = ScanCandidate(
                symbol=m["symbol"],
                latest_price=m["latest_price"],
                pct_change_1d=m["pct_change_1d"],
                volume=m["volume"],
                rvol=m["rvol"],
                indicators=m["indicators"],
                timestamp=m["timestamp"],
                source=m["source"],
                scan_category="Volatility Candidates",
                is_qualified=is_liq and (atr_pct >= min_atr_pct),
                inclusion_reasons=inc_reasons,
                exclusion_reasons=exc_reasons,
            )
            candidates.append(cand)

        candidates.sort(key=lambda c: c.indicators.get("atr_pct", 0.0), reverse=True)
        return candidates[:limit]

    def scan_unusual_movement(self, min_abs_ret: float = 0.03, min_rvol: float = 1.8, limit: int = 10) -> List[ScanCandidate]:
        candidates: List[ScanCandidate] = []
        for sym in self.symbols:
            m = self._prepare_symbol_metrics(sym)
            if not m:
                continue

            row = m["row"]
            is_liq, liq_inc, liq_exc = evaluate_liquidity(row)
            inc_reasons = list(liq_inc)
            exc_reasons = list(liq_exc)

            abs_ret = abs(m["pct_change_1d"])
            rvol = m["rvol"]
            is_unusual = (abs_ret >= min_abs_ret) and (rvol >= min_rvol)

            if is_unusual:
                inc_reasons.append(f"Unusual Activity: {m['pct_change_1d']:.2%} price jump on {rvol:.1f}x volume")
            else:
                exc_reasons.append(f"Normal Activity: Return {abs_ret:.2%}, RVOL {rvol:.1f}x")

            cand = ScanCandidate(
                symbol=m["symbol"],
                latest_price=m["latest_price"],
                pct_change_1d=m["pct_change_1d"],
                volume=m["volume"],
                rvol=m["rvol"],
                indicators=m["indicators"],
                timestamp=m["timestamp"],
                source=m["source"],
                scan_category="Unusual Price & Volume Activity",
                is_qualified=is_liq and is_unusual,
                inclusion_reasons=inc_reasons,
                exclusion_reasons=exc_reasons,
            )
            candidates.append(cand)

        candidates.sort(key=lambda c: abs(c.pct_change_1d) * c.rvol, reverse=True)
        return candidates[:limit]

    def run_full_scan(self) -> Dict[str, List[ScanCandidate]]:
        """Executes all scanners and returns structured dictionary."""
        return {
            "top_gainers": self.scan_top_gainers(),
            "top_losers": self.scan_top_losers(),
            "relative_volume": self.scan_relative_volume(),
            "momentum": self.scan_momentum(),
            "trend_strength": self.scan_trend_strength(),
            "volatility": self.scan_volatility(),
            "unusual_movement": self.scan_unusual_movement(),
        }

