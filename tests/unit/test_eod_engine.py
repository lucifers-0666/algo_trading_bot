import numpy as np
import pandas as pd
import pytest

from trader.eod.engine import (
    EODBias,
    build_eod_report,
    classify_eod_regime,
    ollama_narrative_prompt,
)


def frame(close, volume=None, start="2026-01-01"):
    close = np.asarray(close, dtype=float)
    n = len(close)
    volume = np.asarray(volume if volume is not None else np.full(n, 100_000.0), dtype=float)
    return pd.DataFrame({
        "timestamp": pd.date_range(start, periods=n, freq="B", tz="Asia/Kolkata"),
        "open": close * 0.999,
        "high": close * 1.005,
        "low": close * 0.995,
        "close": close,
        "volume": volume,
        "turnover": close * volume,
    })


def bullish_inputs():
    n = 90
    nifty = frame(np.linspace(22000, 24500, n))
    sector = frame(np.linspace(1000, 1250, n))
    vix = frame(np.full(n, 14.0))
    # Stronger stock trend, then a final controlled pullback to the 20 EMA.
    stock_close = np.linspace(100, 145, n)
    prior_ema20 = pd.Series(stock_close[:-1]).ewm(span=20, adjust=False).mean().iloc[-1]
    stock_close[-1] = prior_ema20 * 1.005
    stock_volume = np.full(n, 200_000.0)
    stock_volume[-1] = 500_000.0
    stock = frame(stock_close, stock_volume)
    return nifty, {"NIFTY IT": sector}, vix, {"TESTCO": stock}


def test_regime_classifies_bullish_trend():
    nifty, sectors, vix, _ = bullish_inputs()
    result = classify_eod_regime(nifty, sectors, vix)
    assert result.bias == EODBias.BULLISH_TREND
    assert result.adx_14 > 18
    assert result.india_vix == 14


def test_candidate_quantity_obeys_half_percent_risk_and_capital():
    nifty, sectors, vix, stocks = bullish_inputs()
    report = build_eod_report(
        nifty, sectors, vix, stocks,
        virtual_equity_inr=10_000,
        risk_per_trade_pct=0.005,
        min_relative_strength_20d=-1.0,
        min_relative_strength_60d=-1.0,
        min_avg_turnover_inr=1,
    )
    if report.candidates:
        candidate = report.candidates[0]
        assert candidate.planned_risk_inr <= 50.0
        assert candidate.capital_required_inr <= 5_000.0
        assert candidate.target_1 == pytest.approx(candidate.trigger_price + 2 * (candidate.trigger_price-candidate.stop_loss), abs=0.06)
        assert candidate.target_2 == pytest.approx(candidate.trigger_price + 3 * (candidate.trigger_price-candidate.stop_loss), abs=0.06)
    else:
        assert "TESTCO" in report.rejected_symbols


def test_risk_off_blocks_long_candidates():
    nifty, sectors, _, stocks = bullish_inputs()
    vix = frame(np.full(90, 28.0))
    report = build_eod_report(
        nifty, sectors, vix, stocks,
        min_relative_strength_20d=-1.0,
        min_relative_strength_60d=-1.0,
        min_avg_turnover_inr=1,
    )
    assert report.bias.bias == EODBias.RISK_OFF
    assert "Risk-Off" in report.rejected_symbols.get("TESTCO", "")


def test_insufficient_history_fails_closed():
    short = frame(np.linspace(100, 110, 60))
    with pytest.raises(ValueError):
        classify_eod_regime(short, {"sector": short}, short)


def test_ollama_prompt_does_not_delegate_numeric_trade_levels():
    nifty, sectors, vix, stocks = bullish_inputs()
    report = build_eod_report(
        nifty, sectors, vix, stocks,
        min_relative_strength_20d=-1.0,
        min_relative_strength_60d=-1.0,
        min_avg_turnover_inr=1,
    )
    if report.candidates:
        prompt = ollama_narrative_prompt(report.candidates[0], report.bias)
        assert "Do not alter entry, stop, targets, quantity, or risk" in prompt
        assert "exactly three" in prompt



def test_missing_sector_confirmation_never_labels_bullish():
    nifty, _, vix, _ = bullish_inputs()
    result = classify_eod_regime(nifty, {}, vix)
    assert result.bias == EODBias.MEAN_REVERTING
    assert result.sector_count == 0


def test_vix_session_mismatch_is_rejected():
    nifty, sectors, vix, _ = bullish_inputs()
    vix["timestamp"] = vix["timestamp"] + pd.Timedelta(days=1)
    with pytest.raises(ValueError, match="session does not match"):
        classify_eod_regime(nifty, sectors, vix)


def test_risk_configuration_cannot_exceed_half_percent():
    nifty, sectors, vix, stocks = bullish_inputs()
    with pytest.raises(ValueError, match="0.5%"):
        build_eod_report(
            nifty, sectors, vix, stocks,
            risk_per_trade_pct=0.006,
            min_relative_strength_20d=-1.0,
            min_relative_strength_60d=-1.0,
            min_avg_turnover_inr=1,
        )
