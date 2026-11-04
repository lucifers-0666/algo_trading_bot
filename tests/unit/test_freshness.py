"""Unit tests for Feed Freshness Watchdog."""

from datetime import datetime, timedelta, time
import pytz

from trader.domain.models import IST
from trader.data.freshness import (
    evaluate_feed_freshness,
    is_nse_market_open,
    FeedStatus,
)


def test_is_nse_market_open():
    # Wednesday 11:30 AM IST -> Open
    wed_open = IST.localize(datetime(2026, 11, 4, 11, 30))
    assert is_nse_market_open(wed_open) is True

    # Wednesday 8:30 AM IST -> Closed
    wed_early = IST.localize(datetime(2026, 11, 4, 8, 30))
    assert is_nse_market_open(wed_early) is False

    # Saturday 11:30 AM IST -> Closed
    sat = IST.localize(datetime(2026, 11, 7, 11, 30))
    assert is_nse_market_open(sat) is False


def test_evaluate_feed_freshness_during_market_hours():
    now_market = IST.localize(datetime(2026, 11, 4, 11, 0))

    # Healthy: tick 30 seconds ago
    recent_tick = now_market - timedelta(seconds=30)
    rep_healthy = evaluate_feed_freshness(recent_tick, freshness_threshold_seconds=300, current_time=now_market)
    assert rep_healthy.status == FeedStatus.HEALTHY
    assert rep_healthy.is_actionable is True

    # Stale: tick 10 minutes (600s) ago
    stale_tick = now_market - timedelta(seconds=600)
    rep_stale = evaluate_feed_freshness(stale_tick, freshness_threshold_seconds=300, current_time=now_market)
    assert rep_stale.status == FeedStatus.STALE
    assert rep_stale.is_actionable is False
    assert "STALE FEED" in rep_stale.message

    # Disconnected: None
    rep_disc = evaluate_feed_freshness(None, freshness_threshold_seconds=300, current_time=now_market)
    assert rep_disc.status == FeedStatus.DISCONNECTED
    assert rep_disc.is_actionable is False

