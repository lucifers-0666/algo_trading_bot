"""Unit tests for Unified Decision Support Engine."""

from trader.domain.models import PortfolioState
from trader.strategies.baseline import StrategySignal, SignalType
from trader.strategies.regime import MarketRegime, RegimeAssessment
from trader.strategies.protections import RiskProtectionManager
from trader.decision.decision_engine import DecisionEngine


def test_decision_engine_approve_high_conviction():
    engine = DecisionEngine(min_composite_score=60.0)

    signal = StrategySignal(
        symbol="INFY",
        signal_type=SignalType.BUY,
        timestamp="2026-11-05",
        reference_close=1600.0,
        reason="Pullback bounce off SMA 20",
    )
    regime = RegimeAssessment(
        regime=MarketRegime.BULL_TRENDING,
        trade_permission="ALLOW_TRADING",
        trend_score=0.85,
        volatility_ratio=0.015,
        adx_estimate=28.5,
        summary="Bullish trending market",
        reasons=["Close > SMA 20 > SMA 50"],
    )

    dossier = engine.evaluate_candidate(
        symbol="INFY",
        price=1600.0,
        stop_loss=1560.0,
        target=1680.0,
        strategy_signal=signal,
        regime_assessment=regime,
        ml_probability=0.78,
        portfolio=PortfolioState(cash_balance=10000.0, starting_cash=10000.0),
    )

    assert dossier.symbol == "INFY"
    assert dossier.action == "APPROVE_PAPER_BUY"
    assert dossier.composite_score >= 60.0
    assert dossier.suggested_quantity > 0
    assert dossier.risk_approved is True
    assert dossier.human_confirmation_required is True


def test_decision_engine_rejects_on_bearish_regime():
    engine = DecisionEngine()

    regime = RegimeAssessment(
        regime=MarketRegime.BEAR_TRENDING,
        trade_permission="NO_TRADE",
        trend_score=-0.75,
        volatility_ratio=0.025,
        adx_estimate=32.0,
        summary="Bearish trending market",
        reasons=["Close < SMA 20 < SMA 50"],
    )

    dossier = engine.evaluate_candidate(
        symbol="TCS",
        price=3950.0,
        stop_loss=3850.0,
        regime_assessment=regime,
        portfolio=PortfolioState(cash_balance=10000.0),
    )

    assert dossier.symbol == "TCS"
    assert dossier.action == "REJECT"
    assert any("Bearish" in r for r in dossier.rejection_reasons)
