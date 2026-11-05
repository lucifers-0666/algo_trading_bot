"""Financial Intelligence and Market Event Analysis Engine.
Ingests, deduplicates, classifies, and stores global geopolitical news,
macroeconomic data, and official Indian corporate/regulatory announcements.
"""

from trader.intelligence.classifier import EventClassifier, FinancialCategory
from trader.intelligence.deduplicator import EventDeduplicator
from trader.intelligence.gdelt_client import GDELTClient
from trader.intelligence.announcements import OfficialAnnouncementsClient
from trader.intelligence.engine import FinancialIntelligenceEngine

__all__ = [
    "EventClassifier",
    "FinancialCategory",
    "EventDeduplicator",
    "GDELTClient",
    "OfficialAnnouncementsClient",
    "FinancialIntelligenceEngine",
]
