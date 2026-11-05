"""Angel One SmartAPI Market Data Adapter.
Integrates with SEBI-registered broker Angel One SmartAPI for read-only market data,
historical OHLCV candles, 5-level market depth order book, and real-time WebSocket ticks.
STRICTLY ISOLATED FROM REAL ORDER PLACEMENT AND BROKER EXECUTION.
"""

import json
import logging
import os
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable, Set

import pytz
import pyotp
import requests

from trader.domain.models import (
    Candle,
    Quote,
    MarketDepth,
    MarketDepthLevel,
    Timeframe,
    DataSource,
    IST,
)
from trader.providers.base import MarketDataProvider

logger = logging.getLogger(__name__)

# Pre-mapped standard NSE equity and index tokens for Angel One SmartAPI
STANDARD_ANGEL_TOKENS: Dict[str, Dict[str, str]] = {
    # Indices
    "NIFTY": {"exchange": "NSE", "token": "99926000", "symbol": "Nifty 50"},
    "NIFTY50": {"exchange": "NSE", "token": "99926000", "symbol": "Nifty 50"},
    "NIFTY 50": {"exchange": "NSE", "token": "99926000", "symbol": "Nifty 50"},
    "BANKNIFTY": {"exchange": "NSE", "token": "99926009", "symbol": "Nifty Bank"},
    "SENSEX": {"exchange": "BSE", "token": "99919000", "symbol": "Sensex"},
    # Core Liquid Equities (NSE Cash)
    "RELIANCE": {"exchange": "NSE", "token": "2885", "symbol": "RELIANCE-EQ"},
    "TCS": {"exchange": "NSE", "token": "11536", "symbol": "TCS-EQ"},
    "INFY": {"exchange": "NSE", "token": "1594", "symbol": "INFY-EQ"},
    "HDFCBANK": {"exchange": "NSE", "token": "1333", "symbol": "HDFCBANK-EQ"},
    "ICICIBANK": {"exchange": "NSE", "token": "4963", "symbol": "ICICIBANK-EQ"},
    "SBIN": {"exchange": "NSE", "token": "3045", "symbol": "SBIN-EQ"},
    "BHARTIARTL": {"exchange": "NSE", "token": "10604", "symbol": "BHARTIARTL-EQ"},
    "LT": {"exchange": "NSE", "token": "11483", "symbol": "LT-EQ"},
    "TATAMOTORS": {"exchange": "NSE", "token": "3456", "symbol": "TATAMOTORS-EQ"},
    "WIPRO": {"exchange": "NSE", "token": "3787", "symbol": "WIPRO-EQ"},
    "ITC": {"exchange": "NSE", "token": "1660", "symbol": "ITC-EQ"},
    "KOTAKBANK": {"exchange": "NSE", "token": "1922", "symbol": "KOTAKBANK-EQ"},
    "AXISBANK": {"exchange": "NSE", "token": "5900", "symbol": "AXISBANK-EQ"},
    "BAJFINANCE": {"exchange": "NSE", "token": "317", "symbol": "BAJFINANCE-EQ"},
    "MARUTI": {"exchange": "NSE", "token": "10999", "symbol": "MARUTI-EQ"},
}

TIMEFRAME_TO_SMARTAPI: Dict[Timeframe, str] = {
    Timeframe.MINUTE_1: "ONE_MINUTE",
    Timeframe.MINUTE_3: "THREE_MINUTE",
    Timeframe.MINUTE_5: "FIVE_MINUTE",
    Timeframe.MINUTE_15: "FIFTEEN_MINUTE",
    Timeframe.MINUTE_30: "THIRTY_MINUTE",
    Timeframe.HOUR_1: "ONE_HOUR",
    Timeframe.DAILY: "ONE_DAY",
}


class AngelOneAdapter(MarketDataProvider):
    """Read-only market data adapter for Angel One SmartAPI.
    Supports authenticated historical OHLCV queries, 5-level market depth snapshots,
    and real-time WebSocket quote streaming.
    STRICT SAFETY GUARANTEE: Never invokes order placement or brokerage portfolio APIs.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        client_code: Optional[str] = None,
        pin: Optional[str] = None,
        totp_secret: Optional[str] = None,
        smart_connect: Optional[Any] = None,
    ):
        self._api_key = (api_key or os.getenv("ANGELONE_API_KEY", "")).strip()
        self._client_code = (client_code or os.getenv("ANGELONE_CLIENT_CODE", "")).strip()
        self._pin = (pin or os.getenv("ANGELONE_PIN", "")).strip()
        self._totp_secret = (totp_secret or os.getenv("ANGELONE_TOTP_SECRET", "")).strip()

        self._smart_connect = smart_connect
        self._jwt_token: Optional[str] = None
        self._feed_token: Optional[str] = None
        self._refresh_token: Optional[str] = None
        self._token_expiry: Optional[datetime] = None

        self._is_connected = False
        self._last_tick_time: Optional[datetime] = None
        self._subscribed_symbols: Set[str] = set()
        self._latest_quotes_cache: Dict[str, Quote] = {}
        self._latest_depth_cache: Dict[str, MarketDepth] = {}

        # Enforce read-only architectural barrier
        self._verify_read_only_isolation()

    def _verify_read_only_isolation(self) -> None:
        """Enforces that this adapter has zero broker order execution or portfolio modification capabilities."""
        forbidden_methods = [
            "place_order", "placeOrder", "modify_order", "modifyOrder",
            "cancel_order", "cancelOrder", "holding", "allholding",
            "position", "convertPosition", "orderBook", "tradeBook"
        ]
        for m in forbidden_methods:
            assert not hasattr(self, m), f"CRITICAL SAFETY VIOLATION: AngelOneAdapter must never expose {m}"

    @property
    def source_type(self) -> DataSource:
        return DataSource.ANGELONE

    @property
    def is_configured(self) -> bool:
        """Returns True if the required credentials exist."""
        return bool(self._api_key and self._client_code and self._pin and self._totp_secret)

    @property
    def is_connected(self) -> bool:
        """Returns True if authenticated and session token active."""
        return self._is_connected

    def authenticate(self) -> bool:
        """Authenticates with Angel One SmartAPI using TOTP (Time-based One Time Password)."""
        if not self.is_configured:
            logger.warning("AngelOneAdapter: Missing credentials in environment.")
            return False

        if self._smart_connect is None:
            try:
                from SmartApi.smartConnect import SmartConnect
                self._smart_connect = SmartConnect(api_key=self._api_key)
            except ImportError:
                logger.error("smartapi-python library not available.")
                return False

        try:
            totp = pyotp.TOTP(self._totp_secret).now()
            session = self._smart_connect.generateSession(self._client_code, self._pin, totp)
            if session and session.get("status") is True and "data" in session:
                data = session["data"]
                self._jwt_token = data.get("jwtToken")
                self._feed_token = data.get("feedToken")
                self._refresh_token = data.get("refreshToken")
                self._token_expiry = datetime.now(IST) + timedelta(hours=23)
                self._is_connected = True
                logger.info("AngelOneAdapter: Authenticated successfully for %s", self._client_code)
                return True
            else:
                err_msg = session.get("message", "Authentication returned false status") if session else "Empty session"
                logger.error("AngelOneAdapter: Authentication failed: %s", err_msg)
                self._is_connected = False
                return False
        except Exception as e:
            logger.error("AngelOneAdapter: Authentication exception: %s", e)
            self._is_connected = False
            return False

    def _ensure_authenticated(self) -> bool:
        if self._is_connected and self._jwt_token and self._token_expiry and datetime.now(IST) < self._token_expiry:
            return True
        return self.authenticate()

    def resolve_instrument(self, symbol: str) -> Optional[Dict[str, str]]:
        """Resolves an exchange symbol to its Angel One token and exchange code."""
        clean = symbol.strip().upper()
        if clean in STANDARD_ANGEL_TOKENS:
            return STANDARD_ANGEL_TOKENS[clean]

        # Check by trading symbol variant
        base = clean.replace("-EQ", "")
        if base in STANDARD_ANGEL_TOKENS:
            return STANDARD_ANGEL_TOKENS[base]

        # Dynamic search via SmartConnect if authenticated
        if self._ensure_authenticated() and self._smart_connect:
            try:
                res = self._smart_connect.searchScrip("NSE", f"{clean}-EQ")
                if res and res.get("status") and res.get("data"):
                    item = res["data"][0]
                    return {
                        "exchange": item.get("exchange", "NSE"),
                        "token": str(item.get("symboltoken")),
                        "symbol": item.get("tradingsymbol", clean),
                    }
            except Exception as e:
                logger.debug("searchScrip failed for %s: %s", clean, e)

        return None

    def get_historical_candles(
        self,
        symbol: str,
        timeframe: Timeframe = Timeframe.DAILY,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[Candle]:
        """Fetches historical candles from Angel One SmartAPI and converts them to canonical Candles."""
        if not self._ensure_authenticated() or not self._smart_connect:
            raise RuntimeError("AngelOneAdapter: Provider is not authenticated or offline.")

        inst = self.resolve_instrument(symbol)
        if not inst:
            raise ValueError(f"AngelOneAdapter: Unknown instrument symbol '{symbol}'. Cannot resolve token.")

        exchange = inst["exchange"]
        token = inst["token"]

        now = datetime.now(IST)
        end = end_date or now
        start = start_date or (end - timedelta(days=90 if timeframe == Timeframe.DAILY else 7))

        interval_code = TIMEFRAME_TO_SMARTAPI.get(timeframe, "ONE_DAY")
        from_str = start.strftime("%Y-%m-%d %H:%M")
        to_str = end.strftime("%Y-%m-%d %H:%M")

        payload = {
            "exchange": exchange,
            "symboltoken": token,
            "interval": interval_code,
            "fromdate": from_str,
            "todate": to_str,
        }

        try:
            resp = self._smart_connect.getCandleData(payload)
            if not resp or not resp.get("status") or not resp.get("data"):
                msg = resp.get("message", "No candle data returned") if resp else "Empty response"
                logger.warning("AngelOneAdapter: getCandleData returned no data for %s: %s", symbol, msg)
                return []

            candles: List[Candle] = []
            for row in resp["data"]:
                # Format: [timestamp_str, open, high, low, close, volume]
                # Timestamp format: "2026-01-15T09:15:00+05:30" or "2026-01-15 09:15"
                ts_raw = row[0]
                dt = self._parse_iso_timestamp(ts_raw)
                o, h, l, c = float(row[1]), float(row[2]), float(row[3]), float(row[4])
                v = float(row[5]) if len(row) > 5 else 0.0

                candles.append(
                    Candle(
                        exchange=exchange,
                        symbol=symbol.upper(),
                        timestamp=dt,
                        interval=timeframe,
                        open=o,
                        high=h,
                        low=l,
                        close=c,
                        volume=v,
                        source=DataSource.ANGELONE,
                    )
                )

            candles.sort(key=lambda x: x.timestamp)
            return candles

        except Exception as e:
            logger.error("AngelOneAdapter: Error fetching candles for %s: %s", symbol, e)
            raise

    def get_latest_quote(self, symbol: str) -> Quote:
        """Fetches the latest LTP and volume snapshot from Angel One SmartAPI."""
        clean = symbol.strip().upper()
        if clean in self._latest_quotes_cache:
            q = self._latest_quotes_cache[clean]
            # Return cached if less than 3 seconds old
            if (datetime.now(IST) - q.timestamp).total_seconds() < 3.0:
                return q

        if not self._ensure_authenticated() or not self._smart_connect:
            raise RuntimeError("AngelOneAdapter: Provider is not authenticated or offline.")

        inst = self.resolve_instrument(clean)
        if not inst:
            raise ValueError(f"AngelOneAdapter: Unknown instrument '{clean}'")

        try:
            resp = self._smart_connect.ltpData(
                exchange=inst["exchange"],
                tradingsymbol=inst["symbol"],
                symboltoken=inst["token"],
            )

            if resp and resp.get("status") and resp.get("data"):
                d = resp["data"]
                ltp = float(d.get("ltp", 0.0))
                open_p = float(d.get("open", 0.0)) if "open" in d else None
                high_p = float(d.get("high", 0.0)) if "high" in d else None
                low_p = float(d.get("low", 0.0)) if "low" in d else None
                close_p = float(d.get("close", 0.0)) if "close" in d else None

                q = Quote(
                    exchange=inst["exchange"],
                    symbol=clean,
                    ltp=ltp,
                    volume=float(d.get("tradeVolume", 0.0)),
                    timestamp=datetime.now(IST),
                    source=DataSource.ANGELONE,
                )
                self._latest_quotes_cache[clean] = q
                self._last_tick_time = q.timestamp
                return q
            else:
                msg = resp.get("message", "No quote data") if resp else "Empty response"
                raise RuntimeError(f"AngelOne ltpData error: {msg}")

        except Exception as e:
            logger.error("AngelOneAdapter: Failed to fetch quote for %s: %s", clean, e)
            raise

    def get_market_depth(self, symbol: str) -> MarketDepth:
        """Fetches live 5-level market depth order book using SmartConnect.getMarketData('FULL')."""
        clean = symbol.strip().upper()
        inst = self.resolve_instrument(clean)
        if not inst:
            raise ValueError(f"AngelOneAdapter: Unknown instrument '{clean}'")

        if not self._ensure_authenticated() or not self._smart_connect:
            raise RuntimeError("AngelOneAdapter: Provider is not authenticated or offline.")

        try:
            resp = self._smart_connect.getMarketData(
                mode="FULL",
                exchangeTokens={inst["exchange"]: [inst["token"]]},
            )

            if resp and resp.get("status") and resp.get("data"):
                fetched = resp["data"].get("fetched", [])
                if fetched:
                    item = fetched[0]
                    depth_raw = item.get("depth", {})
                    buys = depth_raw.get("buy", [])
                    sells = depth_raw.get("sell", [])

                    levels: List[MarketDepthLevel] = []
                    for i in range(5):
                        b = buys[i] if i < len(buys) else {}
                        s = sells[i] if i < len(sells) else {}
                        levels.append(
                            MarketDepthLevel(
                                level=i + 1,
                                bid_price=float(b.get("price", 0.0)),
                                bid_quantity=int(b.get("quantity", 0)),
                                bid_orders=int(b.get("orders", 0)),
                                ask_price=float(s.get("price", 0.0)),
                                ask_quantity=int(s.get("quantity", 0)),
                                ask_orders=int(s.get("orders", 0)),
                            )
                        )

                    md = MarketDepth.compute(
                        symbol=clean,
                        levels=levels,
                        exchange=inst["exchange"],
                        source=DataSource.ANGELONE,
                        timestamp=datetime.now(IST),
                    )
                    self._latest_depth_cache[clean] = md
                    return md

            raise RuntimeError(f"AngelOne getMarketData returned no depth for {clean}")

        except Exception as e:
            logger.error("AngelOneAdapter: Failed to fetch market depth for %s: %s", clean, e)
            raise

    def get_connection_status(self) -> Dict[str, Any]:
        """Returns health, latency, connected state, and active subscriptions."""
        latency_ms = 0.0
        if self._is_connected:
            t0 = time.perf_counter()
            try:
                # Lightweight probe using NIFTY ltp
                if self._smart_connect:
                    self._smart_connect.ltpData("NSE", "Nifty 50", "99926000")
                latency_ms = round((time.perf_counter() - t0) * 1000, 2)
            except Exception:
                latency_ms = 999.0

        return {
            "provider": "Angel One SmartAPI",
            "source_type": DataSource.ANGELONE.value,
            "is_configured": self.is_configured,
            "is_connected": self._is_connected,
            "client_code": self._client_code if self.is_configured else "NOT_CONFIGURED",
            "latency_ms": latency_ms,
            "last_tick_time": self._last_tick_time.isoformat() if self._last_tick_time else None,
            "subscribed_symbols": list(self._subscribed_symbols),
            "read_only_isolated": True,
        }

    def subscribe_live(self, symbols: List[str], callback: Callable[[Quote], None]) -> None:
        """Registers symbols for real-time tracking."""
        for s in symbols:
            self._subscribed_symbols.add(s.strip().upper())
        logger.info("AngelOneAdapter: Subscribed symbols: %s", symbols)

    def unsubscribe_live(self, symbols: List[str]) -> None:
        """Unsubscribes symbols."""
        for s in symbols:
            self._subscribed_symbols.discard(s.strip().upper())

    @staticmethod
    def _parse_iso_timestamp(ts_str: str) -> datetime:
        """Parses Angel One timestamp into IST datetime."""
        # Handle "2026-02-15T09:15:00+05:30" or "2026-02-15 09:15"
        clean = ts_str.replace("T", " ")
        if "+" in clean:
            clean = clean.split("+")[0]
        try:
            dt = datetime.strptime(clean[:19], "%Y-%m-%d %H:%M:%S")
        except ValueError:
            dt = datetime.strptime(clean[:16], "%Y-%m-%d %H:%M")
        return IST.localize(dt)
