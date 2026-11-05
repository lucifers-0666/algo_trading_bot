from trader.strategies.baseline import BaselineSwingStrategy, StrategySignal, SignalType
from trader.strategies.momentum import MomentumStrategy
from trader.strategies.breakout import DonchianBreakoutStrategy
from trader.strategies.regime import MarketRegime, RegimeAssessment, detect_market_regime
from trader.strategies.lookahead_detector import LookaheadDetector, LookaheadAuditReport
from trader.strategies.hyperopt import StrategyHyperoptRunner, HyperoptReport
from trader.strategies.protections import RiskProtectionManager, ProtectionStatus
from trader.strategies.news_sentiment_strategy import NewsSentimentStrategy
from trader.strategies.relative_strength import SectorRelativeStrengthStrategy

__all__ = [
    "BaselineSwingStrategy",
    "StrategySignal",
    "SignalType",
    "MomentumStrategy",
    "DonchianBreakoutStrategy",
    "MarketRegime",
    "RegimeAssessment",
    "detect_market_regime",
    "LookaheadDetector",
    "LookaheadAuditReport",
    "StrategyHyperoptRunner",
    "HyperoptReport",
    "RiskProtectionManager",
    "ProtectionStatus",
    "NewsSentimentStrategy",
    "SectorRelativeStrengthStrategy",
]
