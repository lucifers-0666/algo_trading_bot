"""Synthetic Data Provider.
In-memory and procedural generator implementing MarketDataProvider for testing and offline development.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any

from trader.domain.models import Candle, Quote, Timeframe, DataSource, IST
from trader.providers.base import MarketDataProvider
from trader.data.synthetic import generate_synthetic_candles, DEFAULT_NSE_UNIVERSE


class SyntheticDataProvider(MarketDataProvider):
    """Provides generated synthetic candles and instantaneous quotes."""

    def __init__(self, seed: int = 42, default_lookback_days: int = 150):
        self._seed = seed
        self._default_lookback_days = default_lookback_days
        self._cache: Dict[str, List[Candle]] = {}
        self._last_update = datetime.now(IST)

    @property
    def source_type(self) -> DataSource:
        return DataSource.SYNTHETIC

    def get_historical_candles(
        self,
        symbol: str,
        timeframe: Timeframe = Timeframe.DAILY,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[Candle]:
        sym = symbol.strip().upper()
        if sym not in self._cache:
            self._cache[sym] = generate_synthetic_candles(
                symbol=sym,
                num_days=self._default_lookback_days,
                seed=self._seed,
                interval=timeframe,
            )

        candles = self._cache[sym]
        if start_date:
            candles = [c for c in candles if c.timestamp >= start_date]
        if end_date:
            candles = [c for c in candles if c.timestamp <= end_date]
        return candles

    def get_latest_quote(self, symbol: str) -> Quote:
        sym = symbol.strip().upper()
        candles = self.get_historical_candles(sym)
        if not candles:
            meta = DEFAULT_NSE_UNIVERSE.get(sym, {"initial_price": 1000.0})
            ltp = meta["initial_price"]
        else:
            ltp = candles[-1].close

        self._last_update = datetime.now(IST)
        return Quote(
            exchange="NSE",
            symbol=sym,
            ltp=ltp,
            bid=round(ltp * 0.9995, 2),
            ask=round(ltp * 1.0005, 2),
            bid_qty=100.0,
            ask_qty=100.0,
            volume=candles[-1].volume if candles else 500000.0,
            timestamp=self._last_update,
            source=DataSource.SYNTHETIC,
        )

    def get_connection_status(self) -> Dict[str, Any]:
        return {
            "provider": "synthetic",
            "connected": True,
            "status": "HEALTHY",
            "latency_ms": 0.5,
            "last_update": self._last_update.isoformat(),
            "active_symbols": list(self._cache.keys()),
        }

