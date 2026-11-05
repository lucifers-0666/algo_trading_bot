"""GDELT Global Financial & Geopolitical Intelligence Client.
Queries the official GDELT 2.0 Doc API for global macro events,
trade policy, commodity shocks, and Indian economic news.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from uuid import uuid4
import requests

from trader.domain.models import FinancialEvent, EventImpact, IST
from trader.intelligence.classifier import EventClassifier, FinancialCategory

logger = logging.getLogger(__name__)

GDELT_DOC_API = "https://api.gdeltproject.org/api/v2/doc/doc"

DEFAULT_QUERIES = [
    "India economy OR Reserve Bank of India OR NSE NIFTY",
    "India trade tariffs OR crude oil import India",
    "SEBI regulatory order OR corporate India earnings",
]


class GDELTClient:
    """Client for GDELT 2.0 API specializing in Indian macroeconomic and geopolitical intelligence."""

    def __init__(
        self,
        api_url: str = GDELT_DOC_API,
        classifier: Optional[EventClassifier] = None,
        timeout: float = 6.0,
    ):
        self.api_url = api_url
        self.classifier = classifier or EventClassifier()
        self.timeout = timeout

    def fetch_events(
        self,
        query: Optional[str] = None,
        max_records: int = 25,
        timespan: str = "24h",
    ) -> List[FinancialEvent]:
        """Queries GDELT API and converts articles into canonical FinancialEvent records."""
        q = query or "India economy OR RBI OR NSE OR SEBI"
        params = {
            "query": q,
            "mode": "artlist",
            "maxrecords": str(min(max_records, 50)),
            "format": "json",
            "timespan": timespan,
            "sort": "DateDesc",
        }

        try:
            resp = requests.get(self.api_url, params=params, timeout=self.timeout)
            if resp.status_code != 200:
                logger.warning(f"GDELT API returned status {resp.status_code}")
                return []

            data = resp.json()
            articles = data.get("articles", [])
            events: List[FinancialEvent] = []

            for art in articles:
                headline = art.get("title", "").strip()
                if not headline:
                    continue

                url = art.get("url")
                seendate_str = art.get("seendate")
                # Parse GDELT timestamp: e.g. '20261105T053000Z'
                pub_dt = datetime.now(IST)
                if seendate_str:
                    try:
                        clean_dt = datetime.strptime(seendate_str[:15], "%Y%m%dT%H%M%S")
                        pub_dt = IST.localize(clean_dt)
                    except Exception:
                        pass

                # Classify event
                analysis = self.classifier.analyze_event(headline)

                events.append(
                    FinancialEvent(
                        event_id=f"gdelt_{uuid4().hex[:12]}",
                        source="GDELT",
                        category=analysis["category"],
                        headline=headline,
                        summary=art.get("domain", ""),
                        symbols=analysis["symbols"],
                        sentiment_score=analysis["sentiment_score"],
                        impact_level=analysis["impact_level"],
                        url=url,
                        published_at=pub_dt,
                        created_at=datetime.now(IST),
                    )
                )

            logger.info(f"GDELT fetched {len(events)} events for query: {q[:30]}...")
            return events

        except Exception as e:
            logger.warning(f"GDELT network request failed: {e}. Operating in graceful offline mode.")
            return []

