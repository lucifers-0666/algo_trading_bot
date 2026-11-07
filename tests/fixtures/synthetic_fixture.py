"""Test Fixture: Deterministic synthetic market data and provider for offline unit testing only.
This module is isolated to tests/ and is strictly prohibited in runtime production code.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
import numpy as np

from trader.domain.models import Candle, Quote, MarketDepth, MarketDepthLevel, Timeframe, DataSource, IST
from trader.data.calendar import default_nse_calendar
from trader.data.resampler import resample_candles
from trader.providers.base import MarketDataProvider

DEFAULT_NSE_UNIVERSE = {
    "RELIANCE": {"initial_price": 2850.0, "daily_vol": 0.016, "avg_volume": 4500000},
    "TCS": {"initial_price": 3950.0, "daily_vol": 0.014, "avg_volume": 2100000},
    "INFY": {"initial_price": 1620.0, "daily_vol": 0.018, "avg_volume": 5800000},
    "HDFCBANK": {"initial_price": 1540.0, "daily_vol": 0.015, "avg_volume": 12000000},
    "ICICIBANK": {"initial_price": 1180.0, "daily_vol": 0.016, "avg_volume": 9500000},
    "SBIN": {"initial_price": 810.0, "daily_vol": 0.021, "avg_volume": 14000000},
    "TATAMOTORS": {"initial_price": 970.0, "daily_vol": 0.024, "avg_volume": 8500000},
    "BHARTIARTL": {"initial_price": 1420.0, "daily_vol": 0.017, "avg_volume": 4200000},
    "ITC": {"initial_price": 490.0, "daily_vol": 0.013, "avg_volume": 11000000},
    "KOTAKBANK": {"initial_price": 1780.0, "daily_vol": 0.015, "avg_volume": 3100000},
}


def get_trading_days(num_days: int, end_date: Optional[datetime] = None) -> List[datetime]:
    """Generates a list of valid NSE trading dates ending at end_date."""
    now_ist = datetime.now(IST)
    if end_date is None:
        end_date = now_ist
    elif end_date.tzinfo is None:
        end_date = IST.localize(end_date)
    else:
        end_date = end_date.astimezone(IST)

    current = end_date.replace(hour=15, minute=30, second=0, microsecond=0)
    while current > now_ist:
        current -= timedelta(days=1)

    days = []
    while len(days) < num_days:
        if default_nse_calendar.is_trading_day(current.date()):
            days.append(current)
        current -= timedelta(days=1)

    days.reverse()
    return days


def generate_synthetic_candles(
    symbol: str,
    num_days: int = 120,
    seed: Optional[int] = 42,
    initial_price: Optional[float] = None,
    daily_vol: Optional[float] = None,
    avg_volume: Optional[float] = None,
    trend_bias: float = 0.0004,
    interval: Timeframe = Timeframe.DAILY,
) -> List[Candle]:
    """Generates a chronological series of synthetic OHLCV candles for unit testing."""
    rng = np.random.default_rng(seed)

    meta = DEFAULT_NSE_UNIVERSE.get(
        symbol.upper(),
        {"initial_price": 1000.0, "daily_vol": 0.018, "avg_volume": 1000000},
    )

    p0 = initial_price or meta["initial_price"]
    sigma = daily_vol or meta["daily_vol"]
    base_vol = avg_volume or meta["avg_volume"]

    if interval == Timeframe.WEEKLY:
        daily_candles = generate_synthetic_candles(
            symbol=symbol,
            num_days=max(num_days * 5, 150),
            seed=seed,
            initial_price=initial_price,
            daily_vol=daily_vol,
            avg_volume=avg_volume,
            trend_bias=trend_bias,
            interval=Timeframe.DAILY,
        )
        return resample_candles(daily_candles, Timeframe.WEEKLY)

    if interval in (Timeframe.MINUTE_1, Timeframe.MINUTE_3, Timeframe.MINUTE_5, Timeframe.MINUTE_15, Timeframe.MINUTE_30, Timeframe.HOUR_1):
        recent_days = get_trading_days(min(num_days, 5))
        minute_candles: List[Candle] = []
        cur_p = p0
        minute_vol = sigma / 19.36
        per_minute_base_vol = max(100.0, base_vol / 375.0)

        for day_dt in recent_days:
            session_start = day_dt.replace(hour=9, minute=15, second=0, microsecond=0)
            cur_p = round(cur_p * (1.0 + float(rng.normal(0, sigma * 0.3))), 2)
            cur_p = max(1.0, cur_p)

            for m in range(375):
                bar_time = session_start + timedelta(minutes=m)
                ret = float(rng.normal(loc=0.0, scale=minute_vol))
                o = cur_p
                c = round(max(0.5, o * (1.0 + ret)), 2)
                h = round(max(o, c) * (1.0 + abs(float(rng.normal(0, minute_vol * 0.5)))), 2)
                l = round(min(o, c) * (1.0 - abs(float(rng.normal(0, minute_vol * 0.5)))), 2)
                l = max(0.2, l)
                h = max(h, o, c)
                l = min(l, o, c)
                v = float(round(per_minute_base_vol * float(rng.lognormal(0.0, 0.4))))
                minute_candles.append(
                    Candle(
                        exchange="NSE",
                        symbol=symbol.upper(),
                        timestamp=bar_time,
                        interval=Timeframe.MINUTE_1,
                        open=o,
                        high=h,
                        low=l,
                        close=c,
                        volume=v,
                        turnover=round(c * v, 2),
                        source=DataSource.SYNTHETIC,
                    )
                )
                cur_p = c

        if interval == Timeframe.MINUTE_1:
            return minute_candles
        return resample_candles(minute_candles, interval)

    dates = get_trading_days(num_days)
    candles: List[Candle] = []
    current_close = p0

    for dt in dates:
        daily_ret = float(rng.normal(loc=trend_bias, scale=sigma))
        daily_ret = float(np.clip(daily_ret, -0.098, 0.098))

        gap_ret = float(rng.normal(loc=0.0, scale=sigma * 0.4))
        open_price = round(current_close * (1.0 + gap_ret), 2)
        open_price = max(1.0, open_price)

        close_price = round(current_close * (1.0 + daily_ret), 2)
        close_price = max(1.0, close_price)

        intraday_vol = sigma * float(rng.uniform(0.6, 1.4))
        high_price = round(max(open_price, close_price) * (1.0 + abs(float(rng.normal(0, intraday_vol)))), 2)
        low_price = round(min(open_price, close_price) * (1.0 - abs(float(rng.normal(0, intraday_vol)))), 2)
        low_price = max(0.5, low_price)

        high_price = max(high_price, open_price, close_price)
        low_price = min(low_price, open_price, close_price)

        move_magnitude = abs(daily_ret) / sigma
        vol_multiplier = float(rng.lognormal(mean=0.0, sigma=0.35)) * (1.0 + 0.5 * move_magnitude)
        volume = float(round(base_vol * vol_multiplier))
        turnover = round(close_price * volume, 2)

        candle = Candle(
            exchange="NSE",
            symbol=symbol.upper(),
            timestamp=dt,
            interval=interval,
            open=open_price,
            high=high_price,
            low=low_price,
            close=close_price,
            volume=volume,
            turnover=turnover,
            source=DataSource.SYNTHETIC,
        )
        candles.append(candle)
        current_close = close_price

    return candles


def generate_universe_dataset(
    symbols: Optional[List[str]] = None,
    num_days: int = 150,
    base_seed: int = 100,
) -> Dict[str, List[Candle]]:
    """Generates synthetic historical candles across a basket of NSE equities for unit tests."""
    if symbols is None:
        symbols = list(DEFAULT_NSE_UNIVERSE.keys())

    dataset = {}
    for i, sym in enumerate(symbols):
        candles = generate_synthetic_candles(
            symbol=sym,
            num_days=num_days,
            seed=base_seed + i,
        )
        dataset[sym] = candles
    return dataset


class SyntheticDataProvider(MarketDataProvider):
    """Provides generated synthetic candles and instantaneous quotes for testing."""

    def __init__(self, seed: int = 42, default_lookback_days: int = 150):
        self._seed = seed
        self._default_lookback_days = default_lookback_days
        self._cache: Dict[tuple[str, str], List[Candle]] = {}
        self._last_update = datetime.now(IST)

    @property
    def source_type(self) -> DataSource:
        return DataSource.SYNTHETIC

    def get_connection_status(self) -> Dict[str, Any]:
        return {
            "status": "HEALTHY",
            "connected": True,
            "configured": True,
            "data_source_label": self.source_type.value,
            "latency_seconds": 0.0,
            "last_update": self._last_update.isoformat(),
        }

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
            bids=levels,
            asks=levels,
            timestamp=self._last_update,
        )

