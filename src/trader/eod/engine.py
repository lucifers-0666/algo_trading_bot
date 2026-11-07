"""Deterministic EOD market analysis and next-session candidate generation.

This module is deliberately data-source agnostic. Callers must supply point-in-time,
licensed NSE daily OHLCV frames and an explicit point-in-time NIFTY 500 universe.
It never places orders and never asks an LLM to calculate prices or quantities.
"""
from __future__ import annotations

from enum import Enum
from math import floor
from typing import Dict, List, Mapping, Optional

import numpy as np
import pandas as pd
from pydantic import BaseModel, Field


class EODBias(str, Enum):
    BULLISH_TREND = "Bullish Trend"
    MEAN_REVERTING = "Mean-Reverting/Chop"
    RISK_OFF = "Risk-Off"


class RegimeSnapshot(BaseModel):
    bias: EODBias
    nifty_close: float
    adx_14: float
    sma20_slope_pct: float
    sma50_slope_pct: float
    india_vix: float
    positive_sector_count: int
    sector_count: int
    reasons: List[str] = Field(default_factory=list)


class EODCandidate(BaseModel):
    symbol: str
    session_date: str
    setup_pattern: str
    relative_strength_20d: float
    relative_strength_60d: float
    ema20: float
    ema50: float
    atr14: float
    tick_size: float
    rvol20: float
    trigger_price: float
    stop_loss: float
    target_1: float
    target_2: float
    quantity: int
    risk_budget_inr: float
    planned_risk_inr: float
    capital_required_inr: float
    projected_pnl_target_1_inr: float
    projected_pnl_target_2_inr: float
    rationale_facts: List[str] = Field(default_factory=list)
    llm_narrative: List[str] = Field(default_factory=list)
    status: str = "PENDING_REVIEW"


class EODReport(BaseModel):
    session_date: str
    next_session_plan: str
    bias: RegimeSnapshot
    universe_requested: int
    universe_covered: int
    candidates: List[EODCandidate] = Field(default_factory=list)
    rejected_symbols: Dict[str, str] = Field(default_factory=dict)
    risk_per_trade_pct: float = 0.5
    virtual_equity_inr: float
    advancers: int = 0
    decliners: int = 0
    unchanged: int = 0
    advance_decline_ratio: Optional[float] = None
    market_breadth_pct: float = 0.0
    data_warning: Optional[str] = None


def _validate_frame(frame: pd.DataFrame, name: str, min_rows: int = 61, require_volume: bool = True) -> pd.DataFrame:
    required = {"open", "high", "low", "close"}
    if require_volume:
        required.add("volume")
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"{name}: missing columns {sorted(missing)}")
    if len(frame) < min_rows:
        raise ValueError(f"{name}: requires at least {min_rows} daily bars; got {len(frame)}")
    out = frame.copy()
    if "volume" not in out.columns:
        out["volume"] = 0.0
    elif not require_volume:
        out["volume"] = out["volume"].fillna(0.0)
    if "timestamp" in out.columns:
        out["timestamp"] = pd.to_datetime(out["timestamp"], utc=True).dt.tz_convert("Asia/Kolkata")
        out = out.sort_values("timestamp")
    else:
        out = out.sort_index()
    if out[list(required)].isna().any().any():
        raise ValueError(f"{name}: OHLCV contains null values")
    if (out[["open", "high", "low", "close"]] <= 0).any().any() or (out["volume"] < 0).any():
        raise ValueError(f"{name}: invalid price or volume")
    if (out["high"] < out[["open", "close", "low"]].max(axis=1)).any():
        raise ValueError(f"{name}: invalid high")
    if (out["low"] > out[["open", "close", "high"]].min(axis=1)).any():
        raise ValueError(f"{name}: invalid low")
    return out.reset_index(drop=True)


def _indicators(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    close, high, low = out["close"], out["high"], out["low"]
    out["ema20"] = close.ewm(span=20, adjust=False, min_periods=20).mean()
    out["ema50"] = close.ewm(span=50, adjust=False, min_periods=50).mean()
    previous_close = close.shift(1)
    tr = pd.concat([(high-low), (high-previous_close).abs(), (low-previous_close).abs()], axis=1).max(axis=1)
    out["atr14"] = tr.ewm(alpha=1/14, adjust=False, min_periods=14).mean()
    up = high.diff()
    down = -low.diff()
    plus_dm = up.where((up > down) & (up > 0), 0.0)
    minus_dm = down.where((down > up) & (down > 0), 0.0)
    atr = out["atr14"].replace(0, np.nan)
    plus_di = 100 * plus_dm.ewm(alpha=1/14, adjust=False, min_periods=14).mean() / atr
    minus_di = 100 * minus_dm.ewm(alpha=1/14, adjust=False, min_periods=14).mean() / atr
    dx = 100 * (plus_di-minus_di).abs() / (plus_di+minus_di).replace(0, np.nan)
    out["adx14"] = dx.ewm(alpha=1/14, adjust=False, min_periods=14).mean()
    out["rvol20"] = out["volume"] / out["volume"].shift(1).rolling(20, min_periods=20).mean().replace(0, np.nan)
    out["turnover"] = out.get("turnover", out["close"] * out["volume"])
    out["turnover20"] = out["turnover"].shift(1).rolling(20, min_periods=20).mean()
    return out


def _slope_pct(series: pd.Series, lookback: int = 5) -> float:
    if len(series) <= lookback or pd.isna(series.iloc[-1]) or pd.isna(series.iloc[-1-lookback]):
        return 0.0
    base = float(series.iloc[-1-lookback])
    return (float(series.iloc[-1]) / base - 1.0) * 100 if base else 0.0


def classify_eod_regime(
    nifty_daily: pd.DataFrame,
    sector_indices: Mapping[str, pd.DataFrame],
    india_vix_daily: pd.DataFrame,
) -> RegimeSnapshot:
    nifty = _indicators(_validate_frame(nifty_daily, "NIFTY 50", require_volume=False))
    vix = _validate_frame(india_vix_daily, "India VIX", require_volume=False)
    row = nifty.iloc[-1]
    vix_value = float(vix.iloc[-1]["close"])
    sma20 = nifty["close"].rolling(20, min_periods=20).mean()
    sma50 = nifty["close"].rolling(50, min_periods=50).mean()
    slope20 = _slope_pct(sma20)
    slope50 = _slope_pct(sma50)
    adx = float(row["adx14"]) if pd.notna(row["adx14"]) else 0.0
    close = float(row["close"])
    sma20_last, sma50_last = float(sma20.iloc[-1]), float(sma50.iloc[-1])
    positive = 0
    valid_sector_count = 0
    for frame in sector_indices.values():
        sector = _indicators(_validate_frame(frame, "sector index", require_volume=False))
        sr = sector.iloc[-1]
        if "timestamp" in sector.columns and "timestamp" in nifty.columns and sector.iloc[-1]["timestamp"].date() != nifty.iloc[-1]["timestamp"].date():
            continue
        valid_sector_count += 1
        sector_sma20 = sector["close"].rolling(20, min_periods=20).mean().iloc[-1]
        sector_sma50 = sector["close"].rolling(50, min_periods=50).mean().iloc[-1]
        if float(sr["close"]) > float(sector_sma20) > float(sector_sma50):
            positive += 1
    total = valid_sector_count
    breadth = positive / total if total else 0.0
    vix_session = vix.iloc[-1]["timestamp"].date() if "timestamp" in vix.columns else None
    nifty_session = nifty.iloc[-1]["timestamp"].date() if "timestamp" in nifty.columns else None
    if vix_session and nifty_session and vix_session != nifty_session:
        raise ValueError("India VIX latest session does not match NIFTY 50.")
    reasons = [
        f"NIFTY close {close:.2f}; SMA20/SMA50 {sma20_last:.2f}/{sma50_last:.2f}",
        f"ADX(14) {adx:.1f}; SMA20 slope {slope20:.2f}%; SMA50 slope {slope50:.2f}%",
        f"India VIX {vix_value:.2f}; positive sectors {positive}/{total}",
    ]
    risk_off = vix_value >= 25 or (close < sma50_last and slope50 < -0.15 and adx >= 18)
    bullish = close > sma20_last > sma50_last and slope20 > 0 and slope50 > 0 and adx >= 18 and vix_value < 22 and total > 0 and breadth >= 0.5
    bias = EODBias.RISK_OFF if risk_off else EODBias.BULLISH_TREND if bullish else EODBias.MEAN_REVERTING
    return RegimeSnapshot(
        bias=bias, nifty_close=close, adx_14=round(adx, 2),
        sma20_slope_pct=round(slope20, 3), sma50_slope_pct=round(slope50, 3),
        india_vix=round(vix_value, 2), positive_sector_count=positive,
        sector_count=total, reasons=reasons,
    )


def _round_tick(value: float, tick: float = 0.05) -> float:
    return round(round(value / tick) * tick, 2)


def build_eod_report(
    nifty_daily: pd.DataFrame,
    sector_indices: Mapping[str, pd.DataFrame],
    india_vix_daily: pd.DataFrame,
    stock_daily: Mapping[str, pd.DataFrame],
    *,
    virtual_equity_inr: float = 10_000.0,
    risk_per_trade_pct: float = 0.005,
    max_capital_fraction_per_candidate: float = 0.50,
    min_relative_strength_20d: float = 0.01,
    min_relative_strength_60d: float = 0.0,
    min_rvol: float = 1.20,
    max_ema_distance_pct: float = 0.015,
    min_avg_turnover_inr: float = 20_000_000.0,
    max_candidates: int = 20,
    tick_size_by_symbol: Optional[Mapping[str, float]] = None,
) -> EODReport:
    """Create next-session conditional setups from completed daily candles only.

    A candidate quantity is a per-trade upper bound. The paper broker must re-run
    risk, cash, exposure, freshness and gap checks at approval/fill time.
    """
    if virtual_equity_inr <= 0 or not 0 < risk_per_trade_pct <= 0.005:
        raise ValueError("Equity must be positive and risk_per_trade_pct must be in (0, 0.5%].")
    if not 0 < max_capital_fraction_per_candidate <= 1:
        raise ValueError("max_capital_fraction_per_candidate must be in (0, 1].")
    nifty = _indicators(_validate_frame(nifty_daily, "NIFTY 50", require_volume=False))
    regime = classify_eod_regime(nifty_daily, sector_indices, india_vix_daily)
    benchmark = nifty["close"]
    session_date = pd.Timestamp(nifty.iloc[-1]["timestamp"]).date().isoformat() if "timestamp" in nifty.columns else "latest-session"
    risk_budget = virtual_equity_inr * risk_per_trade_pct
    candidates: List[EODCandidate] = []
    rejected: Dict[str, str] = {}
    advancers = decliners = unchanged = 0
    for raw_symbol, raw_frame in stock_daily.items():
        symbol = raw_symbol.strip().upper()
        try:
            stock = _indicators(_validate_frame(raw_frame, symbol))
            if "timestamp" in stock.columns and "timestamp" in nifty.columns:
                if stock.iloc[-1]["timestamp"].date() != nifty.iloc[-1]["timestamp"].date():
                    raise ValueError("latest candle date does not match NIFTY session")
            row = stock.iloc[-1]
            close = float(row["close"])
            session_change = close / float(stock["close"].iloc[-2]) - 1.0
            if session_change > 0.0005:
                advancers += 1
            elif session_change < -0.0005:
                decliners += 1
            else:
                unchanged += 1
            ema20, ema50, atr = float(row["ema20"]), float(row["ema50"]), float(row["atr14"])
            rvol = float(row["rvol20"]) if pd.notna(row["rvol20"]) else 0.0
            turnover = float(row["turnover20"]) if pd.notna(row["turnover20"]) else 0.0
            if not np.isfinite([ema20, ema50, atr]).all() or atr <= 0:
                raise ValueError("indicator warm-up incomplete")
            if turnover < min_avg_turnover_inr:
                raise ValueError("20-session average traded value below liquidity floor")
            if rvol < min_rvol:
                raise ValueError("no volume confirmation (RVOL below threshold)")
            if close < ema50:
                raise ValueError("close below EMA50; long setup invalid")
            dist20, dist50 = abs(close / ema20 - 1), abs(close / ema50 - 1)
            near20, near50 = dist20 <= max_ema_distance_pct, dist50 <= max_ema_distance_pct
            if not (near20 or near50):
                raise ValueError("not within pullback tolerance of EMA20/EMA50")
            stock_ret20 = close / float(stock["close"].iloc[-21]) - 1
            stock_ret60 = close / float(stock["close"].iloc[-61]) - 1
            bench_ret20 = float(benchmark.iloc[-1] / benchmark.iloc[-21] - 1)
            bench_ret60 = float(benchmark.iloc[-1] / benchmark.iloc[-61] - 1)
            rs20 = (1 + stock_ret20) / (1 + bench_ret20) - 1
            rs60 = (1 + stock_ret60) / (1 + bench_ret60) - 1
            if rs20 < min_relative_strength_20d or rs60 < min_relative_strength_60d:
                raise ValueError("relative strength versus NIFTY below threshold")
            if regime.bias == EODBias.RISK_OFF:
                raise ValueError("market regime is Risk-Off; new long candidates blocked")
            pattern = "EMA20_PULLBACK" if near20 else "EMA50_PULLBACK"
            tick_size = float((tick_size_by_symbol or {}).get(symbol, 0.05))
            if not np.isfinite(tick_size) or tick_size <= 0:
                raise ValueError("invalid instrument tick size")
            trigger = _round_tick(float(row["high"]) + 0.10 * atr, tick_size)
            stop = _round_tick(trigger - 1.50 * atr, tick_size)
            if stop <= 0 or stop >= trigger:
                raise ValueError("invalid ATR stop geometry")
            one_r = trigger - stop
            target1, target2 = _round_tick(trigger + 2 * one_r, tick_size), _round_tick(trigger + 3 * one_r, tick_size)
            qty_by_risk = floor(risk_budget / one_r)
            qty_by_capital = floor((virtual_equity_inr * max_capital_fraction_per_candidate) / trigger)
            quantity = min(qty_by_risk, qty_by_capital)
            if quantity < 1:
                raise ValueError("one share exceeds risk or capital budget")
            planned_risk = round(quantity * one_r, 2)
            if planned_risk > risk_budget + 1e-8:
                raise ValueError("planned risk exceeds 0.5% equity cap")
            candidates.append(EODCandidate(
                symbol=symbol, session_date=session_date, setup_pattern=pattern,
                relative_strength_20d=round(rs20 * 100, 2), relative_strength_60d=round(rs60 * 100, 2),
                ema20=round(ema20, 2), ema50=round(ema50, 2), atr14=round(atr, 2), tick_size=tick_size, rvol20=round(rvol, 2),
                trigger_price=trigger, stop_loss=stop, target_1=target1, target_2=target2,
                quantity=quantity, risk_budget_inr=round(risk_budget, 2),
                planned_risk_inr=planned_risk, capital_required_inr=round(quantity * trigger, 2),
                projected_pnl_target_1_inr=round(quantity * (target1-trigger), 2),
                projected_pnl_target_2_inr=round(quantity * (target2-trigger), 2),
                rationale_facts=[
                    f"{pattern.replace('_', ' ')} with close {close:.2f} near EMA support",
                    f"Relative strength vs NIFTY: 20-session {rs20*100:.2f}%, 60-session {rs60*100:.2f}%",
                    f"RVOL {rvol:.2f}x; ATR(14) {atr:.2f}; trigger requires breakout above prior high",
                ],
            ))
        except (ValueError, KeyError, IndexError, ZeroDivisionError) as exc:
            rejected[symbol] = str(exc)
    candidates.sort(key=lambda c: (c.relative_strength_20d, c.relative_strength_60d, c.rvol20), reverse=True)
    candidates = candidates[:max_candidates]
    return EODReport(
        session_date=session_date, next_session_plan="Conditional long setups for the next NSE session; revalidate gaps and risk before paper execution.",
        bias=regime, universe_requested=len(stock_daily), universe_covered=len(stock_daily),
        candidates=candidates, rejected_symbols=rejected, risk_per_trade_pct=risk_per_trade_pct*100,
        virtual_equity_inr=virtual_equity_inr,
        advancers=advancers, decliners=decliners, unchanged=unchanged,
        advance_decline_ratio=round(advancers / decliners, 3) if decliners else None,
        market_breadth_pct=round(100 * advancers / max(1, advancers + decliners + unchanged), 2),
        data_warning="Coverage is only as complete as the supplied point-in-time NIFTY 500 constituent list and licensed EOD data.",
    )


def ollama_narrative_prompt(candidate: EODCandidate, regime: RegimeSnapshot) -> str:
    """Return a constrained prompt; numeric trade levels remain engine-owned."""
    return (
        "Explain this precomputed NSE cash-equity paper-trading setup in exactly three concise bullets. "
        "Use only the supplied facts. Do not invent prices, indicators, news, probabilities, or recommendations. "
        "Do not alter entry, stop, targets, quantity, or risk. If evidence is insufficient, say so.\n"
        f"Market bias: {regime.bias.value}. Regime facts: {'; '.join(regime.reasons)}\n"
        f"Candidate facts: {candidate.model_dump_json()}\n"
        "Return JSON: {\"bullets\":[\"...\",\"...\",\"...\"]}."
    )
