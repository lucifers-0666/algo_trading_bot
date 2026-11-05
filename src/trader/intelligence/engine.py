"""Financial Intelligence Engine.
Orchestrates global news ingestion, official corporate filings, deduplication,
sentiment tracking, and persistent event indexing.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from trader.domain.models import FinancialEvent, EventImpact, IST
from trader.storage.repositories import FinancialEventRepository
from trader.intelligence.classifier import EventClassifier, FinancialCategory
from trader.intelligence.deduplicator import EventDeduplicator
from trader.intelligence.gdelt_client import GDELTClient
from trader.intelligence.announcements import OfficialAnnouncementsClient

logger = logging.getLogger(__name__)


class FinancialIntelligenceEngine:
    """Central manager for market intelligence, event classification, and sentiment telemetry."""

    def __init__(
        self,
        event_repo: Optional[FinancialEventRepository] = None,
        classifier: Optional[EventClassifier] = None,
        deduplicator: Optional[EventDeduplicator] = None,
        gdelt_client: Optional[GDELTClient] = None,
        announcements_client: Optional[OfficialAnnouncementsClient] = None,
    ):
        self.event_repo = event_repo
        self.classifier = classifier or EventClassifier()
        self.deduplicator = deduplicator or EventDeduplicator()
        self.gdelt_client = gdelt_client or GDELTClient(classifier=self.classifier)
        self.announcements_client = announcements_client or OfficialAnnouncementsClient(classifier=self.classifier)

    def ingest_live_feeds(self, queries: Optional[List[str]] = None) -> int:
        """Pulls latest global and Indian events, deduplicates, and saves them to storage."""
        raw_events: List[FinancialEvent] = []

        # 1. Fetch from GDELT
        search_queries = queries or [
            "India economy OR RBI OR NIFTY",
            "SEBI order OR India corporate earnings",
        ]
        for q in search_queries:
            evs = self.gdelt_client.fetch_events(query=q, max_records=20)
            raw_events.extend(evs)

        # 2. Run Deduplication
        unique_events = self.deduplicator.deduplicate(raw_events)

        # 3. Persist to repository
        saved_count = 0
        if self.event_repo and unique_events:
            saved_count = self.event_repo.save_events(unique_events)
            logger.info(f"Ingested and saved {saved_count} unique financial events.")

        return saved_count

    def record_announcement(
        self,
        symbol: str,
        headline: str,
        source: str = "NSE_CORP",
        summary: Optional[str] = None,
        url: Optional[str] = None,
    ) -> FinancialEvent:
        """Manually or programmatically records a corporate announcement."""
        event = self.announcements_client.parse_corporate_announcement(
            symbol=symbol,
            headline=headline,
            source=source,
            summary=summary,
            url=url,
        )
        if self.event_repo:
            self.event_repo.save_event(event)
        return event

    def record_regulatory_update(
        self,
        authority: str,
        headline: str,
        summary: Optional[str] = None,
        url: Optional[str] = None,
    ) -> FinancialEvent:
        """Records an official SEBI, RBI, or PIB circular."""
        event = self.announcements_client.parse_regulatory_circular(
            authority=authority,
            headline=headline,
            summary=summary,
            url=url,
        )
        if self.event_repo:
            self.event_repo.save_event(event)
        return event

    def get_recent_news(
        self,
        limit: int = 50,
        category: Optional[str] = None,
        symbol: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Returns recent news events from storage or active memory."""
        if self.event_repo:
            events = self.event_repo.get_recent_events(limit=limit, category=category, symbol=symbol)
            return [e.model_dump() for e in events]
        return []

    def get_market_sentiment_summary(self, hours: int = 48) -> Dict[str, Any]:
        """Aggregates market sentiment across recent events."""
        events = []
        if self.event_repo:
            events = self.event_repo.get_recent_events(limit=200)

        if not events:
            return {
                "overall_sentiment_score": 0.0,
                "sentiment_label": "NEUTRAL",
                "total_events_analyzed": 0,
                "positive_count": 0,
                "negative_count": 0,
                "neutral_count": 0,
                "category_breakdown": {},
            }

        scores = [e.sentiment_score for e in events]
        avg_score = round(sum(scores) / len(scores), 3) if scores else 0.0

        pos_count = sum(1 for e in events if e.impact_level == EventImpact.POSITIVE)
        neg_count = sum(1 for e in events if e.impact_level == EventImpact.NEGATIVE)
        neu_count = sum(1 for e in events if e.impact_level in (EventImpact.NEUTRAL, EventImpact.HIGH_VOLATILITY))

        category_breakdown: Dict[str, int] = {}
        for e in events:
            category_breakdown[e.category] = category_breakdown.get(e.category, 0) + 1

        label = "NEUTRAL"
        if avg_score >= 0.15:
            label = "BULLISH"
        elif avg_score <= -0.15:
            label = "BEARISH"

        return {
            "overall_sentiment_score": avg_score,
            "sentiment_label": label,
            "total_events_analyzed": len(events),
            "positive_count": pos_count,
            "negative_count": neg_count,
            "neutral_count": neu_count,
            "category_breakdown": category_breakdown,
        }

    def get_symbol_sentiment(self, symbol: str) -> Dict[str, Any]:
        """Calculates specific sentiment telemetry for a target stock symbol."""
        sym = symbol.strip().upper()
        events = []
        if self.event_repo:
            events = self.event_repo.get_recent_events(limit=50, symbol=sym)

        if not events:
            return {
                "symbol": sym,
                "sentiment_score": 0.0,
                "sentiment_label": "NEUTRAL",
                "events_count": 0,
                "recent_headlines": [],
            }

        scores = [e.sentiment_score for e in events]
        avg_score = round(sum(scores) / len(scores), 3)
        label = "NEUTRAL"
        if avg_score >= 0.20:
            label = "POSITIVE"
        elif avg_score <= -0.20:
            label = "NEGATIVE"

        return {
            "symbol": sym,
            "sentiment_score": avg_score,
            "sentiment_label": label,
            "events_count": len(events),
            "recent_headlines": [
                {
                    "headline": e.headline,
                    "published_at": e.published_at.isoformat(),
                    "category": e.category,
                    "impact": e.impact_level.value,
                    "score": e.sentiment_score,
                }
                for e in events[:5]
            ],
        }
