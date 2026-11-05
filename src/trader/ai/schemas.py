"""Typed Schemas for Local Specialist Financial AI Reasoning.
Enforces Pydantic V2 validation on structured LLM prompts and inference responses.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class AIHealthResponse(BaseModel):
    status: str # "ONLINE" or "STANDBY_HEURISTIC"
    model_name: str
    provider: str
    gpu_acceleration: bool
    endpoint: str
    latency_ms: float
    details: str


class NewsAnalysisRequest(BaseModel):
    headline: str = Field(..., min_length=5, description="Financial news headline or wire")
    content: Optional[str] = Field(default=None, description="Detailed article body or regulatory text")
    symbol: Optional[str] = Field(default=None, description="Optional target NSE stock symbol")


class NewsAnalysisResponse(BaseModel):
    symbol: Optional[str] = None
    sentiment_score: float = Field(..., ge=-1.0, le=1.0)
    sentiment_label: str # BULLISH, BEARISH, NEUTRAL
    impact_level: str # HIGH, MODERATE, LOW
    key_drivers: List[str] = Field(default_factory=list)
    risk_factors: List[str] = Field(default_factory=list)
    suggested_action: str # MONITOR, NO_IMPACT, HEDGE, FAVORABLE_FOR_ENTRY
    reasoning: str


class SignalExplanationRequest(BaseModel):
    symbol: str
    strategy_name: str
    side: str = "BUY"
    price: float = Field(..., gt=0.0)
    stop_loss: float = Field(..., gt=0.0)
    target: Optional[float] = None
    regime: Optional[str] = None
    indicators: Dict[str, Any] = Field(default_factory=dict)
    ml_confidence: Optional[float] = None


class SignalExplanationResponse(BaseModel):
    symbol: str
    strategy_name: str
    thesis: str
    technical_rationale: List[str] = Field(default_factory=list)
    risk_reward_assessment: str
    caution_flags: List[str] = Field(default_factory=list)
    confidence_score: float = Field(default=0.70, ge=0.0, le=1.0)
    human_verdict: str # APPROVED_FOR_PAPER, REQUIRES_MANUAL_REVIEW, REJECT


class StockDossierRequest(BaseModel):
    symbol: str
    current_price: Optional[float] = None
    regime: Optional[str] = None
    technicals: Dict[str, Any] = Field(default_factory=dict)
    news_headlines: List[str] = Field(default_factory=list)


class StockDossierResponse(BaseModel):
    symbol: str
    executive_summary: str
    trend_verdict: str # STRONG_UPTREND, WEAK_UPTREND, CONSOLIDATING, DOWNTREND
    sentiment_verdict: str # POSITIVE, NEUTRAL, CAUTIOUS
    key_strengths: List[str] = Field(default_factory=list)
    key_risks: List[str] = Field(default_factory=list)
    trade_suitability: str # SUITABLE_SWING, MONITOR_ONLY, AVOID
    generated_at: str
    ai_provider: str
