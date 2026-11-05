"""Unit tests for Specialist Local Financial AI Reasoning Engine."""

import pytest
from unittest.mock import patch, MagicMock

from trader.ai.schemas import (
    NewsAnalysisRequest,
    SignalExplanationRequest,
    StockDossierRequest,
)
from trader.ai.inference_client import LocalFinancialAIClient


def test_ai_client_healthcheck_fallback():
    client = LocalFinancialAIClient(base_url="http://127.0.0.1:9999/v1")
    health = client.check_health()
    assert health.status == "STANDBY_HEURISTIC"
    assert "Fallback" in health.model_name
    assert health.gpu_acceleration is False


def test_ai_client_analyze_news_positive_catalyst():
    client = LocalFinancialAIClient(base_url="http://127.0.0.1:9999/v1")
    req = NewsAnalysisRequest(
        headline="TCS reports record profit with net profit surges 15% and bags order win worth $1B",
        symbol="TCS",
    )
    res = client.analyze_news(req)
    assert res.symbol == "TCS"
    assert res.sentiment_score > 0.0
    assert res.sentiment_label == "BULLISH"
    assert res.suggested_action == "FAVORABLE_FOR_ENTRY"
    assert len(res.key_drivers) > 0


def test_ai_client_analyze_news_negative_event():
    client = LocalFinancialAIClient(base_url="http://127.0.0.1:9999/v1")
    req = NewsAnalysisRequest(
        headline="SEBI penalty issued on company following investigation and auditor resigns",
        symbol="INFY",
    )
    res = client.analyze_news(req)
    assert res.sentiment_score < 0.0
    assert res.sentiment_label == "BEARISH"
    assert res.suggested_action == "HEDGE"
    assert len(res.risk_factors) > 0


def test_ai_client_explain_signal():
    client = LocalFinancialAIClient(base_url="http://127.0.0.1:9999/v1")
    req = SignalExplanationRequest(
        symbol="INFY",
        strategy_name="momentum_breakout",
        side="BUY",
        price=1600.0,
        stop_loss=1560.0,
        target=1680.0,
        regime="BULLISH_TREND",
        indicators={"rsi_14": 62.5, "sma_20": 1580.0, "sma_50": 1540.0},
        ml_confidence=0.82,
    )
    res = client.explain_signal(req)
    assert res.symbol == "INFY"
    assert "Risk/Reward" in res.risk_reward_assessment
    assert res.confidence_score >= 0.70
    assert res.human_verdict in ("APPROVED_FOR_PAPER", "REQUIRES_MANUAL_REVIEW")


def test_ai_client_generate_dossier():
    client = LocalFinancialAIClient(base_url="http://127.0.0.1:9999/v1")
    req = StockDossierRequest(
        symbol="RELIANCE",
        current_price=2850.0,
        regime="BULLISH_TREND",
        news_headlines=["Reliance commissions new solar green energy facility"],
    )
    res = client.generate_dossier(req)
    assert res.symbol == "RELIANCE"
    assert res.trade_suitability == "SUITABLE_SWING"
    assert len(res.key_strengths) > 0
