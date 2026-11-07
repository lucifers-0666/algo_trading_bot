"""NSE Live Market Data Adapter.
Fetches real-time NSE Option Chains, Implied Volatility, PCR, and F&O Participant OI
directly from original exchange endpoints without requiring any broker login or Demat account.
"""

from datetime import datetime, timedelta
import io
import logging
from typing import Dict, Any, List, Optional
import pandas as pd

try:
    from curl_cffi import requests
except ImportError:
    import requests

from trader.domain.models import IST
from trader.data.calendar import default_nse_calendar

logger = logging.getLogger("trader.providers.nse_live")

INDICES = {"NIFTY", "BANKNIFTY", "FINNIFTY", "MIDCPNIFTY", "NIFTYNXT50"}


class NSELiveAdapter:
    """Free, direct exchange data client for NSE F&O, Option Chains, and participant positioning."""

    def __init__(self, request_timeout: int = 10):
        self._timeout = request_timeout
        self._session = None
        self._last_update: Optional[datetime] = None
        self._cached_chain: Dict[str, Any] = {}
        self._cached_chain_time: Optional[datetime] = None
        self._init_session()

    def _init_session(self) -> None:
        """Initializes a browser-impersonating HTTP session with authentic NSE cookies."""
        try:
            if hasattr(requests, "Session") and "impersonate" in requests.Session.__init__.__code__.co_varnames:
                self._session = requests.Session(impersonate="chrome120")
            else:
                self._session = requests.Session()
                self._session.headers.update(
                    {
                        "User-Agent": (
                            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                        ),
                        "Accept-Language": "en-US,en;q=0.9",
                        "Accept-Encoding": "gzip, deflate, br",
                    }
                )

            # Prime initial cookies on homepage
            self._session.get("https://www.nseindia.com", timeout=self._timeout)
            self._last_update = datetime.now(IST)
        except Exception as e:
            logger.warning(f"Failed to prime initial NSE cookies: {e}")

    def get_connection_status(self) -> Dict[str, Any]:
        """Reports live NSE feed connectivity."""
        return {
            "status": "HEALTHY" if self._session else "NOT_CONFIGURED",
            "connected": self._session is not None,
            "configured": True,
            "provider": "nse_live",
            "free_data_feed": True,
            "broker_login_required": False,
            "last_update": self._last_update.isoformat() if self._last_update else None,
        }

    def get_expiry_dates(self, symbol: str = "NIFTY") -> List[str]:
        """Fetches active Option Chain expiry dates for an index or stock."""
        sym = symbol.strip().upper()
        if not self._session:
            self._init_session()

        url = f"https://www.nseindia.com/api/option-chain-contract-info?symbol={sym}"
        headers = {"Referer": "https://www.nseindia.com/option-chain"}

        try:
            r = self._session.get(url, headers=headers, timeout=self._timeout)
            if r.status_code == 200:
                data = r.json()
                return data.get("expiryDates", [])
            elif r.status_code in (401, 403):
                # Re-prime session
                self._init_session()
                r2 = self._session.get(url, headers=headers, timeout=self._timeout)
                if r2.status_code == 200:
                    return r2.json().get("expiryDates", [])
        except Exception as exc:
            logger.error(f"Error fetching expiry dates for {sym}: {exc}")

        return []

    def get_option_chain(
        self,
        symbol: str = "NIFTY",
        expiry_date: Optional[str] = None,
        bypass_cache: bool = False,
    ) -> Dict[str, Any]:
        """Fetches real-time NSE Option Chain data (Strike, CE/PE LTP, OI, IV) without broker login."""
        sym = symbol.strip().upper()
        cache_key = f"{sym}:{expiry_date or 'default'}"
        now = datetime.now(IST)

        # 30-second cache unless forced
        if not bypass_cache and cache_key in self._cached_chain and self._cached_chain_time:
            if (now - self._cached_chain_time).total_seconds() < 30.0:
                return self._cached_chain[cache_key]

        if not self._session:
            self._init_session()

        expiries = self.get_expiry_dates(sym)
        target_expiry = expiry_date or (expiries[0] if expiries else None)

        sec_type = "Indices" if sym in INDICES else "Equity"
        url = f"https://www.nseindia.com/api/option-chain-v3?type={sec_type}&symbol={sym}"
        if target_expiry:
            url += f"&expiry={target_expiry}"

        headers = {"Referer": "https://www.nseindia.com/option-chain"}

        try:
            r = self._session.get(url, headers=headers, timeout=self._timeout)
            if r.status_code != 200:
                # Retry with refreshed session
                self._init_session()
                r = self._session.get(url, headers=headers, timeout=self._timeout)

            if r.status_code == 200:
                payload = r.json()
                records = payload.get("records", {})
                underlying_val = records.get("underlyingValue")
                raw_data = records.get("data", [])

                strikes_data: List[Dict[str, Any]] = []
                total_ce_oi = 0
                total_pe_oi = 0
                total_ce_vol = 0
                total_pe_vol = 0

                for item in raw_data:
                    strike = float(item.get("strikePrice", 0.0))
                    ce = item.get("CE")
                    pe = item.get("PE")

                    ce_info = None
                    if ce:
                        ce_oi = int(ce.get("openInterest", 0))
                        ce_vol = int(ce.get("totalTradedVolume", 0))
                        total_ce_oi += ce_oi
                        total_ce_vol += ce_vol
                        ce_info = {
                            "ltp": float(ce.get("lastPrice", 0.0)),
                            "change": float(ce.get("change", 0.0)),
                            "pChange": float(ce.get("pChange", 0.0)),
                            "oi": ce_oi,
                            "change_oi": int(ce.get("changeinOpenInterest", 0)),
                            "iv": float(ce.get("impliedVolatility", 0.0)),
                            "volume": ce_vol,
                            "bid": float(ce.get("buyPrice1", 0.0)),
                            "ask": float(ce.get("sellPrice1", 0.0)),
                        }

                    pe_info = None
                    if pe:
                        pe_oi = int(pe.get("openInterest", 0))
                        pe_vol = int(pe.get("totalTradedVolume", 0))
                        total_pe_oi += pe_oi
                        total_pe_vol += pe_vol
                        pe_info = {
                            "ltp": float(pe.get("lastPrice", 0.0)),
                            "change": float(pe.get("change", 0.0)),
                            "pChange": float(pe.get("pChange", 0.0)),
                            "oi": pe_oi,
                            "change_oi": int(pe.get("changeinOpenInterest", 0)),
                            "iv": float(pe.get("impliedVolatility", 0.0)),
                            "volume": pe_vol,
                            "bid": float(pe.get("buyPrice1", 0.0)),
                            "ask": float(pe.get("sellPrice1", 0.0)),
                        }

                    strikes_data.append(
                        {
                            "strike": strike,
                            "call": ce_info,
                            "put": pe_info,
                        }
                    )

                strikes_data.sort(key=lambda x: x["strike"])

                # Calculate Put-Call Ratio (PCR)
                pcr = round(total_pe_oi / total_ce_oi, 2) if total_ce_oi > 0 else 1.0

                # Calculate Max Pain (strike with minimum cumulative loss for option writers)
                max_pain = None
                min_loss = float("inf")
                for s_item in strikes_data:
                    k = s_item["strike"]
                    loss = 0.0
                    for other in strikes_data:
                        k_other = other["strike"]
                        if other["call"] and k > k_other:
                            loss += (k - k_other) * other["call"]["oi"]
                        if other["put"] and k < k_other:
                            loss += (k_other - k) * other["put"]["oi"]
                    if loss < min_loss:
                        min_loss = loss
                        max_pain = k

                result = {
                    "symbol": sym,
                    "underlying_value": underlying_val,
                    "expiry_date": target_expiry,
                    "available_expiries": expiries,
                    "total_call_oi": total_ce_oi,
                    "total_put_oi": total_pe_oi,
                    "pcr": pcr,
                    "max_pain": max_pain,
                    "strikes_count": len(strikes_data),
                    "strikes": strikes_data,
                    "source": "NSE_ORIGINAL_LIVE",
                    "timestamp": now.isoformat(),
                }

                self._cached_chain[cache_key] = result
                self._cached_chain_time = now
                self._last_update = now
                return result

        except Exception as exc:
            logger.error(f"Failed to fetch option chain for {sym}: {exc}")

        return {
            "symbol": sym,
            "underlying_value": None,
            "expiry_date": target_expiry,
            "available_expiries": expiries,
            "total_call_oi": 0,
            "total_put_oi": 0,
            "pcr": 1.0,
            "max_pain": None,
            "strikes_count": 0,
            "strikes": [],
            "source": "UNAVAILABLE",
            "timestamp": now.isoformat(),
        }

    def get_participant_oi(self, trade_date: Optional[datetime] = None) -> Dict[str, Any]:
        """Fetches FII, DII, Pro, and Client-wise participant Open Interest (OI) from NSE archives."""
        now_ist = trade_date or datetime.now(IST)
        # Search backwards up to 5 days for recent trading day CSV
        target = now_ist
        if not self._session:
            self._init_session()

        for _ in range(5):
            date_str = target.strftime("%d%m%Y")
            url = f"https://archives.nseindia.com/content/nsccl/fao_participant_oi_{date_str}.csv"
            try:
                r = self._session.get(url, timeout=self._timeout)
                if r.status_code == 200 and "Client Type" in r.text:
                    df = pd.read_csv(io.StringIO(r.text), skiprows=1)
                    # Standardize columns
                    df.columns = [c.strip() for c in df.columns]
                    summary = []
                    for _, row in df.iterrows():
                        client_type = str(row.get("Client Type", "")).strip()
                        if not client_type or client_type.upper() == "TOTAL":
                            continue
                        summary.append(
                            {
                                "client_type": client_type,
                                "future_index_long": int(row.get("Future Index Long", 0)),
                                "future_index_short": int(row.get("Future Index Short", 0)),
                                "future_stock_long": int(row.get("Future Stock Long", 0)),
                                "future_stock_short": int(row.get("Future Stock Short", 0)),
                                "option_index_call_long": int(row.get("Option Index Call Long", 0)),
                                "option_index_put_long": int(row.get("Option Index Put Long", 0)),
                                "option_index_call_short": int(row.get("Option Index Call Short", 0)),
                                "option_index_put_short": int(row.get("Option Index Put Short", 0)),
                            }
                        )

                    return {
                        "date": target.strftime("%Y-%m-%d"),
                        "participants": summary,
                        "status": "SUCCESS",
                        "source": "NSE_ARCHIVES_CSV",
                    }
            except Exception as e:
                logger.debug(f"Failed to fetch participant OI for {date_str}: {e}")

            target -= timedelta(days=1)

        return {"status": "NO_DATA", "participants": []}

