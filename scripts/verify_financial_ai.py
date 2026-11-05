"""Standalone Diagnostic Script for Northstar Local Financial AI Reasoning Engine."""

import sys
from trader.ai.inference_client import LocalFinancialAIClient
from trader.ai.schemas import NewsAnalysisRequest, SignalExplanationRequest

def run_diagnostics():
    client = LocalFinancialAIClient()
    health = client.check_health()

    print(f"  AI Mode Status : {health.status}")
    print(f"  Engine Provider: {health.provider}")
    print(f"  Active Model   : {health.model_name}")
    print(f"  GPU Offloading : {'Active (CUDA)' if health.gpu_acceleration else 'Standby'}")
    print(f"  Endpoint URL   : {health.endpoint}")
    print(f"  Engine Details : {health.details}")

    print("\n  [Test 1] Positive Catalyst News Analysis:")
    pos = client.analyze_news(NewsAnalysisRequest(
        headline="TCS reports net profit surges 15% and bags order win worth $1B",
        symbol="TCS",
    ))
    print(f"    Symbol: {pos.symbol} | Score: {pos.sentiment_score:.2f} ({pos.sentiment_label}) | Action: {pos.suggested_action}")
    print(f"    Key Drivers: {', '.join(pos.key_drivers[:2])}")

    print("\n  [Test 2] Regulatory Disclosure / Risk Event Analysis:")
    neg = client.analyze_news(NewsAnalysisRequest(
        headline="SEBI penalty issued on company following investigation and auditor resigns",
        symbol="INFY",
    ))
    print(f"    Symbol: {neg.symbol} | Score: {neg.sentiment_score:.2f} ({neg.sentiment_label}) | Action: {neg.suggested_action}")
    print(f"    Risk Factors: {', '.join(neg.risk_factors[:2])}")

    print("\n  [Test 3] Quantitative Trade Signal Explainer:")
    sig = client.explain_signal(SignalExplanationRequest(
        symbol="RELIANCE",
        strategy_name="baseline_swing",
        side="BUY",
        price=2850.0,
        stop_loss=2780.0,
        target=2990.0,
        indicators={"rsi_14": 58.2, "sma_20": 2820.0, "sma_50": 2750.0},
    ))
    print(f"    Symbol: {sig.symbol} | Confidence: {sig.confidence_score * 100:.0f}% | Verdict: {sig.human_verdict}")
    print(f"    Thesis: {sig.thesis}")

if __name__ == "__main__":
    run_diagnostics()

