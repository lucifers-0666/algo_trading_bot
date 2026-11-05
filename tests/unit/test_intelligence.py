"""Unit tests for Bloomberg-style Financial Intelligence System."""

from datetime import datetime
import pytest

from trader.domain.models import FinancialEvent, EventImpact, IST
from trader.intelligence.classifier import EventClassifier, FinancialCategory
from trader.intelligence.deduplicator import EventDeduplicator, token_jaccard_similarity
from trader.intelligence.announcements import OfficialAnnouncementsClient
from trader.intelligence.engine import FinancialIntelligenceEngine
from trader.storage.database import DatabaseManager
from trader.storage.repositories import FinancialEventRepository


def test_classifier_symbol_extraction():
    classifier = EventClassifier()
    text = "Infosys reports strong quarterly performance while Reliance expands green energy"
    symbols = classifier.extract_symbols(text)
    assert "INFY" in symbols
    assert "RELIANCE" in symbols


def test_classifier_category_and_sentiment():
    classifier = EventClassifier()

    # 1. Earnings (Positive)
    earnings_text = "TCS net profit surges 14% to record high driven by strong cloud demand"
    analysis1 = classifier.analyze_event(earnings_text)
    assert analysis1["category"] == FinancialCategory.EARNINGS.value
    assert analysis1["sentiment_score"] > 0.3
    assert analysis1["impact_level"] == EventImpact.POSITIVE

    # 2. Regulatory (Negative)
    reg_text = "SEBI issues show cause notice and penalty on broker following investigation"
    analysis2 = classifier.analyze_event(reg_text)
    assert analysis2["category"] == FinancialCategory.REGULATORY.value
    assert analysis2["sentiment_score"] < -0.3
    assert analysis2["impact_level"] == EventImpact.NEGATIVE

    # 3. Order win
    order_text = "Larsen & Toubro bags mega order worth Rs 5000 crore in Middle East"
    analysis3 = classifier.analyze_event(order_text)
    assert analysis3["category"] == FinancialCategory.ORDER_WIN.value


def test_deduplicator_jaccard_and_near_duplicates():
    h1 = "Infosys reports 12% rise in Q3 net profit to Rs 6586 crore"
    h2 = "Infosys Q3 net profit jumps 12% to Rs 6586 crore"
    h3 = "Tata Motors reports vehicle sales surge in domestic commercial market"

    sim1_2 = token_jaccard_similarity(h1, h2)
    assert sim1_2 >= 0.50

    sim1_3 = token_jaccard_similarity(h1, h3)
    assert sim1_3 < 0.20

    dedup = EventDeduplicator(similarity_threshold=0.50)
    ev1 = FinancialEvent(
        event_id="e1",
        source="FEED1",
        category="EARNINGS",
        headline=h1,
        symbols=["INFY"],
        published_at=datetime.now(IST),
    )
    ev2 = FinancialEvent(
        event_id="e2",
        source="FEED2",
        category="EARNINGS",
        headline=h2,
        symbols=["INFY"],
        published_at=datetime.now(IST),
    )
    ev3 = FinancialEvent(
        event_id="e3",
        source="FEED3",
        category="ORDER_WIN",
        headline=h3,
        symbols=["TATAMOTORS"],
        published_at=datetime.now(IST),
    )

    filtered = dedup.deduplicate([ev1, ev2, ev3])
    assert len(filtered) == 2
    assert filtered[0].event_id == "e1"
    assert filtered[1].event_id == "e3"


def test_intelligence_engine_record_and_sentiment_aggregation(tmp_path):
    db_path = tmp_path / "test_intel.db"
    db_mgr = DatabaseManager(db_path=db_path)
    repo = FinancialEventRepository(db_mgr)
    engine = FinancialIntelligenceEngine(event_repo=repo)

    # Record announcements
    ev1 = engine.record_announcement(
        symbol="INFY",
        headline="Infosys net profit surges with record profit in Q3",
        source="NSE_CORP",
    )
    assert "INFY" in ev1.symbols
    assert ev1.sentiment_score > 0.0

    ev2 = engine.record_regulatory_update(
        authority="SEBI",
        headline="SEBI notice regarding market compliance disclosures",
    )
    assert ev2.category == "REGULATORY"

    # Query recent news
    news = engine.get_recent_news(limit=10)
    assert len(news) == 2

    # Query market sentiment summary
    summary = engine.get_market_sentiment_summary()
    assert summary["total_events_analyzed"] == 2
    assert "category_breakdown" in summary

    # Query specific symbol sentiment
    infy_sentiment = engine.get_symbol_sentiment("INFY")
    assert infy_sentiment["symbol"] == "INFY"
    assert infy_sentiment["events_count"] == 1
    assert infy_sentiment["sentiment_score"] > 0.0
