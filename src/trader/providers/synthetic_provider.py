"""Synthetic Data Provider.
In-memory and procedural generator implementing MarketDataProvider for testing and offline development.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any

from trader.domain.models import Candle, Quote, MarketDepth, MarketDepthLevel, Timeframe, DataSource, IST
from trader.providers.base import MarketDataProvider
from trader.data.synthetic import generate_synthetic_candles, DEFAULT_NSE_UNIVERSE


class SyntheticDataProvider(MarketDataProvider):
    """Provides generated synthetic candles and instantaneous quotes."""

    def __init__(self, seed: int = 42, default_lookback_days: int = 150):
        self._seed = seed
        self._default_lookback_days = default_lookback_days
        self._cache: Dict[tuple[str, str], List[Candle]] = {}
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
        tf = timeframe if isinstance(timeframe, Timeframe) else Timeframe(timeframe)
        cache_key = (sym, tf.value)
        if cache_key not in self._cache:
            self._cache[cache_key] = generate_synthetic_candles(
                symbol=sym,
                num_days=self._default_lookback_days,
                seed=self._seed,
                interval=tf,
            )

        candles = self._cache[cache_key]
        if start_date:
            candles = [c for c in candles if c.timestamp >= start_date]
        if end_date:
            candles = [c for c in candles if c.timestamp <= end_date]
        return candles

    def get_latest_quote(self, symbol: str) -> Quote:
        sym = symbol.strip().upper()
        candles = self.get_historical_candles(sym, timeframe=Timeframe.DAILY)
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
            bid=None,
            ask=None,
            bid_qty=None,
            ask_qty=None,
            volume=candles[-1].volume if candles else 500000.0,
            timestamp=self._last_update,
            source=DataSource.SYNTHETIC,
        )

    def get_market_depth(self, symbol: str) -> MarketDepth:
        """Procedural 5-level market depth order book for testing and simulation."""
        sym = symbol.strip().upper()
        quote = self.get_latest_quote(sym)
        ltp = quote.ltp
        tick = round(max(0.05, round(ltp * 0.0005, 2)), 2)

        levels: List[MarketDepthLevel] = []
        for i in range(1, 6):
            bid_p = round(ltp - (i * tick), 2)
            ask_p = round(ltp + (i * tick), 2)
            bid_q = int(500 * (6 - i) + (i * 37))
            ask_q = int(450 * (6 - i) + (i * 41))
            levels.append(
                MarketDepthLevel(
                    level=i,
                    bid_price=bid_p,
                    bid_quantity=bid_q,
                    bid_orders=max(1, int(bid_q / 50)),
                    ask_price=ask_p,
                    ask_quantity=ask_q,
                    ask_orders=max(1, int(ask_q / 50)),
                )
            )

        return MarketDepth.create(
            symbol=sym,
            levels=levels,
            exchange="NSE",
            source=DataSource.SYNTHETIC,
            timestamp=datetime.now(IST),
        )

    def get_connection_status(self) -> Dict[str, Any]:
        return {
            "provider": "synthetic",
            "connected": True,
            "status": "HEALTHY",
            "latency_ms": 0.5,
            "last_update": self._last_update.isoformat(),
            "active_symbols": [k[0] for k in self._cache.keys()],
        }

