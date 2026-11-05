"""Official Corporate and Regulatory Announcements Ingestion.
Parses NSE/BSE corporate filings, SEBI circulars, RBI monetary policy updates,
and Government of India (PIB) economic notifications.
"""

import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from uuid import uuid4

from trader.domain.models import FinancialEvent, EventImpact, IST
from trader.intelligence.classifier import EventClassifier, FinancialCategory

logger = logging.getLogger(__name__)


class OfficialAnnouncementsClient:
    """Ingestion client for official regulatory, exchange, and corporate disclosure feeds."""

    def __init__(self, classifier: Optional[EventClassifier] = None):
        self.classifier = classifier or EventClassifier()

    def parse_corporate_announcement(
        self,
        symbol: str,
        headline: str,
        source: str = "NSE_CORP",
        summary: Optional[str] = None,
        url: Optional[str] = None,
        published_at: Optional[datetime] = None,
    ) -> FinancialEvent:
        """Parses a structured corporate disclosure into a canonical FinancialEvent."""
        pub_dt = published_at or datetime.now(IST)
        analysis = self.classifier.analyze_event(headline, summary)

        # Ensure the announced symbol is included
        sym = symbol.strip().upper()
        symbols = sorted(list(set(analysis["symbols"] + [sym])))

        return FinancialEvent(
            event_id=f"ann_{uuid4().hex[:12]}",
            source=source,
            category=analysis["category"],
            headline=headline,
            summary=summary,
            symbols=symbols,
            sentiment_score=analysis["sentiment_score"],
            impact_level=analysis["impact_level"],
            url=url,
            published_at=pub_dt,
            created_at=datetime.now(IST),
        )

    def parse_regulatory_circular(
        self,
        authority: str, # "SEBI", "RBI", "PIB"
        headline: str,
        summary: Optional[str] = None,
        url: Optional[str] = None,
        published_at: Optional[datetime] = None,
    ) -> FinancialEvent:
        """Parses an official regulatory circular or macroeconomic notification."""
        pub_dt = published_at or datetime.now(IST)
        analysis = self.classifier.analyze_event(headline, summary)

        # If authority is SEBI/RBI, override category if it wasn't already classified as regulatory or macro
        cat = analysis["category"]
        if authority.upper() == "SEBI" and cat == FinancialCategory.GENERAL.value:
            cat = FinancialCategory.REGULATORY.value
        elif authority.upper() == "RBI" and cat == FinancialCategory.GENERAL.value:
            cat = FinancialCategory.MACRO.value

        return FinancialEvent(
            event_id=f"reg_{uuid4().hex[:12]}",
            source=authority.upper(),
            category=cat,
            headline=headline,
            summary=summary,
            symbols=analysis["symbols"],
            sentiment_score=analysis["sentiment_score"],
            impact_level=analysis["impact_level"],
            url=url,
            published_at=pub_dt,
            created_at=datetime.now(IST),
        )

