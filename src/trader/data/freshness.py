"""Feed Freshness and Health Watchdog.
Monitors feed latencies against NSE trading session boundaries and enforces stale-feed trading halts.
"""

from datetime import datetime, time, timedelta
from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
import pytz

from trader.domain.models import IST
from trader.data.calendar import default_nse_calendar, NSE_MARKET_OPEN, NSE_MARKET_CLOSE


class FeedStatus(str, Enum):
    NOT_CONFIGURED = "NOT_CONFIGURED"
    CONNECTING = "CONNECTING"
    CONNECTED = "CONNECTED"
    RECEIVING_DATA = "RECEIVING_DATA"
    HEALTHY = "HEALTHY"
    STALE = "STALE"
    DISCONNECTED = "DISCONNECTED"
    ERROR = "ERROR"
    MARKET_CLOSED = "MARKET_CLOSED"
    HISTORICAL_ONLY = "HISTORICAL_ONLY"
    SYNTHETIC_ONLY = "SYNTHETIC_ONLY"


class FreshnessReport(BaseModel):
    status: FeedStatus
    is_actionable: bool = Field(..., description="Whether feed is safe for generating new trades")
    latency_seconds: float = Field(default=0.0)
    last_update_ist: Optional[datetime] = None
    is_market_open: bool = False
    message: str


def is_nse_market_open(now_dt: Optional[datetime] = None) -> bool:
    """Returns True if given IST timestamp falls within Monday-Friday 09:15-15:30 IST and is not an exchange holiday."""
    return default_nse_calendar.is_market_open(now_dt)


def evaluate_feed_freshness(
    last_update: Optional[datetime],
    freshness_threshold_seconds: float = 300.0,
    current_time: Optional[datetime] = None,
    source_type: Optional[str] = None,
    is_configured: Optional[bool] = None,
    is_connected: Optional[bool] = None,
) -> FreshnessReport:
    """Evaluates whether the market feed is current or stale, reporting exact provider status."""
    src = (source_type or "").upper()
    now_ist = current_time or datetime.now(IST)
    if now_ist.tzinfo is None:
        now_ist = IST.localize(now_ist)
    else:
        now_ist = now_ist.astimezone(IST)

    market_open = is_nse_market_open(now_ist)

    # 1. Check Explicit Synthetic / Historical Isolation
    if src == "SYNTHETIC":
        return FreshnessReport(
            status=FeedStatus.SYNTHETIC_ONLY,
            is_actionable=True,
            latency_seconds=0.0,
            last_update_ist=now_ist,
            is_market_open=market_open,
            message="Synthetic test data generation active. Zero real-time exchange ticks.",
        )
    if src in ("CSV", "HISTORICAL"):
        last_dt = None
        if last_update:
            last_dt = IST.localize(last_update) if last_update.tzinfo is None else last_update.astimezone(IST)
        return FreshnessReport(
            status=FeedStatus.HISTORICAL_ONLY,
            is_actionable=True,
            latency_seconds=0.0,
            last_update_ist=last_dt,
            is_market_open=market_open,
            message="Offline historical CSV dataset loaded. No real-time tick streaming.",
        )

    # 2. Check Provider Configuration
    if is_configured is False:
        return FreshnessReport(
            status=FeedStatus.NOT_CONFIGURED,
            is_actionable=False,
            latency_seconds=999999.0,
            is_market_open=market_open,
            message="Provider credentials unconfigured. Operating in safe standby mode.",
        )

    # 3. Missing Update Timestamps Fail Closed During Market Hours
    if last_update is None:
        if market_open:
            return FreshnessReport(
                status=FeedStatus.DISCONNECTED,
                is_actionable=False,
                latency_seconds=999999.0,
                is_market_open=market_open,
                message="Feed disconnected: No update timestamp recorded during active market session.",
            )
        else:
            return FreshnessReport(
                status=FeedStatus.MARKET_CLOSED,
                is_actionable=True,
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

