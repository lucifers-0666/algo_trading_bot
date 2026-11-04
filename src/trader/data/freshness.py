"""Feed Freshness and Health Watchdog.
Monitors feed latencies against NSE trading session boundaries and enforces stale-feed trading halts.
"""

from datetime import datetime, time, timedelta
from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
import pytz

from trader.domain.models import IST

NSE_MARKET_OPEN = time(9, 15)
NSE_MARKET_CLOSE = time(15, 30)


class FeedStatus(str, Enum):
    HEALTHY = "HEALTHY"
    STALE = "STALE"
    DISCONNECTED = "DISCONNECTED"
    MARKET_CLOSED = "MARKET_CLOSED"


class FreshnessReport(BaseModel):
    status: FeedStatus
    is_actionable: bool = Field(..., description="Whether feed is safe for generating new trades")
    latency_seconds: float = Field(default=0.0)
    last_update_ist: Optional[datetime] = None
    is_market_open: bool = False
    message: str


def is_nse_market_open(now_dt: Optional[datetime] = None) -> bool:
    """Returns True if given IST timestamp falls within Monday-Friday 09:15-15:30 IST."""
    if now_dt is None:
        now_dt = datetime.now(IST)
    elif now_dt.tzinfo is None:
        now_dt = IST.localize(now_dt)
    else:
        now_dt = now_dt.astimezone(IST)

    # Monday=0, Sunday=6
    if now_dt.weekday() >= 5:
        return False

    current_time = now_dt.time()
    return NSE_MARKET_OPEN <= current_time <= NSE_MARKET_CLOSE


def evaluate_feed_freshness(
    last_update: Optional[datetime],
    freshness_threshold_seconds: float = 300.0,
    current_time: Optional[datetime] = None,
) -> FreshnessReport:
    """Evaluates whether the market feed is current or stale."""
    now_ist = current_time or datetime.now(IST)
    if now_ist.tzinfo is None:
        now_ist = IST.localize(now_ist)
    else:
        now_ist = now_ist.astimezone(IST)

    market_open = is_nse_market_open(now_ist)

    if last_update is None:
        if market_open:
            return FreshnessReport(
                status=FeedStatus.DISCONNECTED,
                is_actionable=False,
                latency_seconds=999999.0,
                is_market_open=market_open,
                message="Feed disconnected: No update timestamp recorded during market session.",
            )
        else:
            return FreshnessReport(
                status=FeedStatus.MARKET_CLOSED,
                is_actionable=True, # Off-market analysis permitted
                latency_seconds=0.0,
                is_market_open=market_open,
                message="Market closed. EOD/offline analysis permitted.",
            )

    if last_update.tzinfo is None:
        last_update_ist = IST.localize(last_update)
    else:
        last_update_ist = last_update.astimezone(IST)

    latency = max(0.0, (now_ist - last_update_ist).total_seconds())

    if market_open:
        if latency > freshness_threshold_seconds:
            return FreshnessReport(
                status=FeedStatus.STALE,
                is_actionable=False,
                latency_seconds=latency,
                last_update_ist=last_update_ist,
                is_market_open=market_open,
                message=f"STALE FEED: Last tick was {latency:.1f}s ago (> {freshness_threshold_seconds}s limit). Trading halted.",
            )
        return FreshnessReport(
            status=FeedStatus.HEALTHY,
            is_actionable=True,
            latency_seconds=latency,
            last_update_ist=last_update_ist,
            is_market_open=market_open,
            message=f"Feed healthy. Latency: {latency:.1f}s.",
        )
    else:
        return FreshnessReport(
            status=FeedStatus.MARKET_CLOSED,
            is_actionable=True,
            latency_seconds=latency,
            last_update_ist=last_update_ist,
            is_market_open=market_open,
            message="Market currently closed. Off-hours research & backtesting active.",
        )
