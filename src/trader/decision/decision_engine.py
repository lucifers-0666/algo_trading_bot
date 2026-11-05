"""Unified Quantitative Decision Support Engine.
Coordinates multi-disciplinary quantitative inputs:
1. Technical Strategy Entry Signals
2. Macro / Benchmark Market Regime
3. Machine Learning Probability
4. Financial News & Regulatory Sentiment
5. Pre-Trade Portfolio Risk & Capital Protections

Outputs an institutional Decision Dossier requiring human operator confirmation.
STRICTLY VIRTUAL PAPER TRADING.
"""

import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from trader.domain.models import PortfolioState, Position, OrderSide, IST
from trader.strategies.baseline import StrategySignal, SignalType
from trader.strategies.regime import MarketRegime, RegimeAssessment
from trader.strategies.protections import RiskProtectionManager
from trader.risk.checks import RiskManager, RiskAssessment
from trader.intelligence.engine import FinancialIntelligenceEngine

logger = logging.getLogger(__name__)


class DecisionDossier(BaseModel):
    symbol: str
    action: str # "APPROVE_PAPER_BUY", "WAIT_FOR_CONFIRMATION", "REJECT"
    composite_score: float = Field(..., ge=0.0, le=100.0, description="Overall institutional conviction (0-100)")
    technical_conviction: float = Field(..., ge=0.0, le=100.0)
    ml_conviction: float = Field(..., ge=0.0, le=100.0)
    sentiment_conviction: float = Field(..., ge=0.0, le=100.0)
    regime_conviction: float = Field(..., ge=0.0, le=100.0)
    entry_price: float
    stop_loss: float
    target: float
    risk_reward_ratio: float
    suggested_quantity: int
    risk_approved: bool
    rejection_reasons: List[str] = Field(default_factory=list)
    key_catalysts: List[str] = Field(default_factory=list)
    caution_flags: List[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(IST))
    human_confirmation_required: bool = True


class DecisionEngine:
    """Evaluates multi-model confluence to produce actionable paper trading dossiers."""

    def __init__(
        self,
        risk_manager: Optional[RiskManager] = None,
        protection_manager: Optional[RiskProtectionManager] = None,
        intelligence_engine: Optional[FinancialIntelligenceEngine] = None,
        min_composite_score: float = 60.0,
    ):
        self.risk_manager = risk_manager or RiskManager()
        self.protection_manager = protection_manager or RiskProtectionManager()
        self.intelligence_engine = intelligence_engine
        self.min_composite_score = min_composite_score

    def evaluate_candidate(
        self,
        symbol: str,
        price: float,
        stop_loss: float,
        target: Optional[float] = None,
        strategy_signal: Optional[StrategySignal] = None,
        regime_assessment: Optional[RegimeAssessment] = None,
        ml_probability: Optional[float] = None,
        portfolio: Optional[PortfolioState] = None,
        open_positions: Optional[List[Position]] = None,
    ) -> DecisionDossier:
        """Synthesizes technicals, regime, ML, sentiment, and risk into a single DecisionDossier."""
        sym = symbol.strip().upper()
        rejection_reasons: List[str] = []
        caution_flags: List[str] = []
        catalysts: List[str] = []

        # 1. Protection & Cooldown Checks
        locked, lock_reason = self.protection_manager.is_trading_locked()
        if locked:
            rejection_reasons.append(f"Protection circuit active: {lock_reason}")

        if self.protection_manager.is_symbol_in_cooldown(sym):
            rejection_reasons.append(f"Symbol {sym} is in post-stop-loss cooldown.")

        # 2. Risk Evaluation
        port = portfolio or PortfolioState()
        positions = open_positions or []
        risk_eval = self.risk_manager.assess_order(
            symbol=sym,
            side=OrderSide.BUY,
            price=price,
            stop_loss=stop_loss,
            portfolio=port,
            open_positions=positions,
        )

        if not risk_eval.approved:
            rejection_reasons.extend(risk_eval.rejection_reasons)

        approved_qty = risk_eval.approved_quantity

        # 3. Component Scoring
        # Technical Score (0-100)
        tech_score = 0.0
        if strategy_signal and strategy_signal.signal_type == SignalType.BUY:
            tech_score = 80.0
            catalysts.append(f"Technical setup confirmed by {strategy_signal.reason}")
        else:
            tech_score = 40.0
            caution_flags.append("No active technical breakout signal.")

        # Regime Score (0-100)
        regime_score = 50.0
        if regime_assessment:
            if regime_assessment.regime == MarketRegime.BULL_TRENDING:
                regime_score = 90.0
                catalysts.append("Benchmark regime is strongly Bullish Trending.")
            elif regime_assessment.regime in (MarketRegime.SIDEWAYS_CONSOLIDATION, MarketRegime.LOW_VOLATILITY):
                regime_score = 50.0
                caution_flags.append("Benchmark is Sideways/Consolidating; lower win-rate expected.")
            elif regime_assessment.regime in (MarketRegime.BEAR_TRENDING, MarketRegime.HIGH_VOLATILITY):
                regime_score = 20.0
                caution_flags.append("Caution: Benchmark market is in Bearish or High-Volatility regime.")
                rejection_reasons.append("Trading counter to dominant Bearish/High-Volatility Regime.")

        # ML Score (0-100)
        ml_score = 50.0
        if ml_probability is not None:
            ml_score = round(ml_probability * 100.0, 1)
            if ml_score >= 65.0:
                catalysts.append(f"ML Model predicts {ml_score:.1f}% probability of forward upside.")
            elif ml_score < 45.0:
                caution_flags.append(f"ML Model confidence is weak ({ml_score:.1f}%).")

        # News Sentiment Score (0-100)
        sentiment_score = 50.0
        if self.intelligence_engine:
            sym_sent = self.intelligence_engine.get_symbol_sentiment(sym)
            raw_sent = sym_sent.get("sentiment_score", 0.0)
            # Map [-1.0, 1.0] to [0.0, 100.0]
            sentiment_score = round(((raw_sent + 1.0) / 2.0) * 100.0, 1)
            if raw_sent > 0.20:
                catalysts.append(f"Positive institutional news catalyst (Sentiment: +{raw_sent:.2f}).")
            elif raw_sent < -0.20:
                caution_flags.append(f"Negative news headlines detected (Sentiment: {raw_sent:.2f}).")
                if raw_sent <= -0.50:
                    rejection_reasons.append("Severe adverse news/regulatory event detected.")

        # 4. Composite Confluence Score
        # Weights: Technical 35%, ML 25%, Regime 25%, Sentiment 15%
        composite = round(
            (tech_score * 0.35)
            + (ml_score * 0.25)
            + (regime_score * 0.25)
            + (sentiment_score * 0.15),
            1,
        )

        risk_per_share = max(0.01, price - stop_loss)
        calc_target = target if target is not None else round(price + (risk_per_share * 2.0), 2)
        rr_ratio = round((calc_target - price) / risk_per_share, 2)

        # 5. Recommendation Action
        if rejection_reasons:
            action = "REJECT"
        elif composite >= self.min_composite_score and risk_eval.approved and approved_qty > 0:
            action = "APPROVE_PAPER_BUY"
        else:
            action = "WAIT_FOR_CONFIRMATION"

        return DecisionDossier(
            symbol=sym,
            action=action,
            composite_score=composite,
            technical_conviction=tech_score,
            ml_conviction=ml_score,
            sentiment_conviction=sentiment_score,
            regime_conviction=regime_score,
            entry_price=price,
            stop_loss=stop_loss,
            target=calc_target,
            risk_reward_ratio=rr_ratio,
            suggested_quantity=approved_qty,
            risk_approved=risk_eval.approved,
            rejection_reasons=rejection_reasons,
            key_catalysts=catalysts,
            caution_flags=caution_flags,
            timestamp=datetime.now(IST),
            human_confirmation_required=True,
        )
