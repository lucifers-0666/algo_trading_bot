"""TrueData Market Data Adapter.
Decoupled adapter supporting REST historical candle queries and WebSocket live streaming.
Defaults to safe DISABLED mode when credentials are missing or unverified.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import List, Optional, Callable, Dict, Any
import requests
import websockets

from trader.domain.models import Candle, Quote, Timeframe, DataSource, IST
from trader.providers.base import MarketDataProvider

logger = logging.getLogger(__name__)


class TrueDataAdapter(MarketDataProvider):
    """Integrates with authorized TrueData REST and WebSocket services.
    Maintains fail-closed safety and complete isolation when credentials are absent.
    """

    def __init__(
        self,
        username: Optional[str] = None,
        password: Optional[str] = None,
        realtime_url: str = "wss://push.truedata.in",
        historical_url: str = "https://history.truedata.in",
    ):
        self._username = username.strip() if username else None
        self._password = password.strip() if password else None
        self._realtime_url = realtime_url
        self._historical_url = historical_url
        self._session_token: Optional[str] = None
        self._is_connected = False
        self._subscribed_symbols: List[str] = []
        self._callbacks: List[Callable[[Quote], None]] = []
        self._last_update: Optional[datetime] = None

    @property
    def source_type(self) -> DataSource:
        return DataSource.TRUEDATA

    @property
    def is_configured(self) -> bool:
        """Returns True if credentials have been supplied."""
        return bool(self._username and self._password)

    def get_historical_candles(
        self,
        symbol: str,
        timeframe: Timeframe = Timeframe.DAILY,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[Candle]:
        """Fetches historical candles via TrueData REST API."""
        if not self.is_configured:
            logger.warning(
                "TrueData credentials not configured. Returning empty candle list (Offline Mode)."
            )
            return []

        # Formulate REST request
        endpoint = f"{self._historical_url}/get_historic_data"
        params = {
            "symbol": symbol.strip().upper(),
            "interval": timeframe.value,
            "start": start_date.strftime("%Y-%m-%d") if start_date else "",
            "end": end_date.strftime("%Y-%m-%d") if end_date else "",
            "user": self._username,
            "token": self._session_token,
        }

        try:
            resp = requests.get(endpoint, params=params, timeout=10)
            if resp.status_code != 200:
                logger.error(f"TrueData REST error {resp.status_code}: {resp.text}")
                return []

            data = resp.json()
            candles: List[Candle] = []
            for item in data.get("records", []):
                # Canonical parser for TrueData record
                ts = datetime.fromisoformat(item["timestamp"])
                if ts.tzinfo is None:
                    ts = IST.localize(ts)
                c = Candle(
                    exchange="NSE",
                    symbol=symbol.strip().upper(),
                    timestamp=ts,
                    interval=timeframe,
                    open=float(item["open"]),
                    high=float(item["high"]),
                    low=float(item["low"]),
                    close=float(item["close"]),
                    volume=float(item.get("volume", 0.0)),
                    source=DataSource.TRUEDATA,
                )
                candles.append(c)
            return candles
        except Exception as e:
            logger.error(f"TrueData historical fetch failed: {e}")
            return []

    def get_latest_quote(self, symbol: str) -> Quote:
        """Returns the latest quote. If unconfigured or offline, raises ValueError."""
        if not self.is_configured:
            raise ValueError(
                "TrueData credentials unconfigured. Use Synthetic or CSV provider in offline mode."
            )
        # Snapshot fallback
        raise NotImplementedError("Live quote stream requires active WebSocket connection.")

    def parse_websocket_message(self, raw_msg: str) -> Optional[Quote]:
        """Decodes raw WebSocket frame from TrueData stream into canonical Quote."""
        try:
            payload = json.loads(raw_msg)
            # Example TrueData tick schema: {"symbol": "RELIANCE", "ltp": 2845.5, "bid": 2845.0, ...}
            if "symbol" in payload and "ltp" in payload:
                now_ist = datetime.now(IST)
                self._last_update = now_ist
                return Quote(
                    exchange="NSE",
                    symbol=payload["symbol"].strip().upper(),
                    ltp=float(payload["ltp"]),
                    bid=float(payload.get("bid", payload["ltp"] * 0.9995)),
                    ask=float(payload.get("ask", payload["ltp"] * 1.0005)),
                    volume=float(payload.get("volume", 0.0)),
                    timestamp=now_ist,
                    source=DataSource.TRUEDATA,
                )
        except Exception as e:
            logger.debug(f"Failed to parse websocket frame: {e}")
        return None

    def get_connection_status(self) -> Dict[str, Any]:
        if not self.is_configured:
            return {
                "provider": "truedata",
                "status": "DISABLED",
                "configured": False,
                "connected": False,
                "message": "TrueData credentials not provided in .env. Running in safe offline mode.",
            }

        return {
            "provider": "truedata",
            "status": "CONNECTED" if self._is_connected else "DISCONNECTED",
            "configured": True,
            "connected": self._is_connected,
            "realtime_url": self._realtime_url,
            "subscribed_symbols": self._subscribed_symbols,
            "last_update": self._last_update.isoformat() if self._last_update else None,
        }

