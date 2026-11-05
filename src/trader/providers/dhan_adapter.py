"""DhanHQ Market Data Adapter.
Integrates with SEBI-registered broker DhanHQ API for read-only market data,
depth quotes, and historical OHLCV queries for NSE cash equities.
STRICTLY ISOLATED FROM REAL ORDER PLACEMENT AND BROKER EXECUTION.
"""

import logging
from datetime import datetime
from typing import List, Optional, Callable, Dict, Any, Set
import requests

from trader.domain.models import Candle, Quote, Timeframe, DataSource, IST
from trader.providers.base import MarketDataProvider

logger = logging.getLogger(__name__)

DHAN_BASE_URL = "https://api.dhan.co"


class DhanAdapter(MarketDataProvider):
    """Read-only market data adapter for DhanHQ API.
    Provides live quotes, 5-depth order book snapshots, and historical daily/intraday candles.
    Fails closed and operates in safe unconfigured mode when credentials are absent.
    """

    def __init__(
        self,
        client_id: Optional[str] = None,
        access_token: Optional[str] = None,
        base_url: str = DHAN_BASE_URL,
        timeout: float = 8.0,
    ):
        self._client_id = client_id.strip() if client_id else None
        self._access_token = access_token.strip() if access_token else None
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._is_connected = False
        self._last_update: Optional[datetime] = None
        self._subscribed_symbols: Set[str] = set()

        # Architectural safety assertion: verify zero order execution capabilities
        self._verify_read_only_isolation()

    def _verify_read_only_isolation(self) -> None:
        """Ensures this data adapter cannot execute live financial orders."""
        assert not hasattr(self, "place_order"), "CRITICAL SAFETY: Dhan adapter must not have place_order"
        assert not hasattr(self, "modify_order"), "CRITICAL SAFETY: Dhan adapter must not have modify_order"
        assert not hasattr(self, "cancel_order"), "CRITICAL SAFETY: Dhan adapter must not have cancel_order"

    @property
    def source_type(self) -> DataSource:
        return DataSource.DHAN

    @property
    def is_configured(self) -> bool:
        """Returns True if client_id and access_token are provided."""
        return bool(self._client_id and self._access_token)

    def _get_headers(self) -> Dict[str, str]:
        return {
            "client-id": self._client_id or "",
            "access-token": self._access_token or "",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def get_connection_status(self) -> Dict[str, Any]:
        """Returns provider connectivity status and configuration telemetry."""
        return {
            "source": self.source_type.value,
            "configured": self.is_configured,
            "connected": self._is_connected,
            "last_update": self._last_update.isoformat() if self._last_update else None,
            "subscribed_symbols_count": len(self._subscribed_symbols),
            "mode": "READ_ONLY_MARKET_DATA",
            "message": "Ready" if self.is_configured else "DhanHQ credentials unconfigured (safe standby).",
        }

    def get_latest_quote(self, symbol: str) -> Quote:
        """Fetches latest quote for an NSE equity. Returns UNAVAILABLE if unconfigured or error."""
        sym = symbol.strip().upper()
        if not self.is_configured:
            raise ConnectionError(f"DhanAdapter is not configured with credentials; cannot fetch quote for {sym}.")

        url = f"{self._base_url}/marketfeed/quote"
        payload = {"symbols": [sym]}

        try:
            resp = requests.post(url, headers=self._get_headers(), json=payload, timeout=self._timeout)
            if resp.status_code == 200:
                data = resp.json()
                self._last_update = datetime.now(IST)
                self._is_connected = True
                return self.parse_quote_packet(sym, data)
            else:
                logger.warning(f"Dhan quote request failed with status {resp.status_code}: {resp.text}")
                raise ConnectionError(f"Dhan quote failed with status {resp.status_code}")
        except Exception as e:
            logger.error(f"DhanAdapter quote error for {sym}: {e}")
            raise ConnectionError(f"Dhan quote error: {e}")

    def parse_quote_packet(self, symbol: str, data: Dict[str, Any]) -> Quote:
        """Parses a Dhan marketfeed quote response packet into a canonical Quote model."""
        # Handle dictionary wrapped responses
        item = data.get(symbol) or data.get("data", {}).get(symbol) or data
        ltp = float(item.get("last_price") or item.get("ltp") or 0.0)
        volume = float(item.get("volume") or 0.0)
        bid = float(item.get("buy_price") or item.get("bid") or 0.0) or None
        ask = float(item.get("sell_price") or item.get("ask") or 0.0) or None

        raw_ts = item.get("timestamp") or item.get("last_trade_time")
        ts = datetime.now(IST)
        if raw_ts:
            try:
                parsed_ts = datetime.fromisoformat(str(raw_ts))
                ts = IST.localize(parsed_ts) if parsed_ts.tzinfo is None else parsed_ts.astimezone(IST)
            except Exception:
                pass

        return Quote(
            exchange="NSE",
            symbol=symbol.upper(),
            ltp=ltp,
            bid=bid,
            ask=ask,
            volume=volume,
            timestamp=ts,
            source=DataSource.DHAN,
        )

    def get_market_depth(self, symbol: str) -> Dict[str, Any]:
        """Fetches best 5 bid/ask market depth for an NSE equity."""
        sym = symbol.strip().upper()
        if not self.is_configured:
            return {"symbol": sym, "bids": [], "asks": [], "source": DataSource.UNAVAILABLE.value}

        url = f"{self._base_url}/marketfeed/depth"
        payload = {"symbols": [sym]}

        try:
            resp = requests.post(url, headers=self._get_headers(), json=payload, timeout=self._timeout)
            if resp.status_code == 200:
                data = resp.json()
                return self.parse_market_depth_packet(sym, data)
            return {"symbol": sym, "bids": [], "asks": [], "source": DataSource.ERROR.value}
        except Exception as e:
            logger.error(f"Dhan market depth fetch failed for {sym}: {e}")
            return {"symbol": sym, "bids": [], "asks": [], "source": DataSource.ERROR.value}

    def parse_market_depth_packet(self, symbol: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Formats 5-level market depth order book."""
        item = data.get(symbol) or data.get("data", {}).get(symbol) or {}
        bids = []
        for b in item.get("bids", [])[:5]:
            bids.append({"price": float(b.get("price", 0.0)), "quantity": int(b.get("quantity", 0)), "orders": int(b.get("orders", 0))})
        asks = []
        for a in item.get("asks", [])[:5]:
            asks.append({"price": float(a.get("price", 0.0)), "quantity": int(a.get("quantity", 0)), "orders": int(a.get("orders", 0))})

        return {
            "symbol": symbol.upper(),
            "bids": bids,
            "asks": asks,
            "total_buy_quantity": sum(b["quantity"] for b in bids),
            "total_sell_quantity": sum(a["quantity"] for a in asks),
            "source": DataSource.DHAN.value,
        }

    def get_historical_candles(
        self,
        symbol: str,
        timeframe: Timeframe = Timeframe.DAILY,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[Candle]:
        """Fetches historical candles from DhanHQ historical REST endpoint."""
        sym = symbol.strip().upper()
        if not self.is_configured:
            logger.info("DhanAdapter unconfigured. Returning empty historical candle list.")
            return []

        url = f"{self._base_url}/charts/historical"
        params = {
            "symbol": sym,
            "timeframe": timeframe.value,
            "from": start_date.strftime("%Y-%m-%d") if start_date else None,
            "to": end_date.strftime("%Y-%m-%d") if end_date else None,
        }

        try:
            resp = requests.get(url, headers=self._get_headers(), params=params, timeout=self._timeout)
            if resp.status_code == 200:
                raw_candles = resp.json().get("candles", [])
                candles = []
                for row in raw_candles:
                    # Format: [timestamp, open, high, low, close, volume]
                    dt = datetime.fromisoformat(row[0])
                    dt_ist = IST.localize(dt) if dt.tzinfo is None else dt.astimezone(IST)
                    candles.append(
                        Candle(
                            exchange="NSE",
                            symbol=sym,
                            timestamp=dt_ist,
                            interval=timeframe,
                            open=float(row[1]),
                            high=float(row[2]),
                            low=float(row[3]),
                            close=float(row[4]),
                            volume=float(row[5]),
                            source=DataSource.DHAN,
                        )
                    )
                return candles
            return []
        except Exception as e:
            logger.error(f"DhanAdapter historical candle error for {sym}: {e}")
            return []
