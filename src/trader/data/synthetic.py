"""Synthetic Market Data Generator for Indian Equities.
Produces realistic multi-regime daily and intraday OHLCV time-series
with authentic spreads, trends, pullbacks, volume surges, and circuit boundaries.
"""

from datetime import datetime, timedelta, time
from typing import List, Dict, Optional
import numpy as np
import pytz

from trader.domain.models import Candle, DataSource, Timeframe, IST
from trader.data.calendar import default_nse_calendar
from trader.data.resampler import resample_candles

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

    # Standardize time to market close 15:30 IST
    current = end_date.replace(hour=15, minute=30, second=0, microsecond=0)
    # If the standardized 15:30 close time is in the future relative to now_ist,
    # today's daily session is not yet completed. Step back to the previous day.
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
    trend_bias: float = 0.0004, # Slight upward annual drift
    interval: Timeframe = Timeframe.DAILY,
) -> List[Candle]:
    """Generates a chronological series of synthetic OHLCV candles for an NSE stock using local RNG."""
    rng = np.random.default_rng(seed)

    meta = DEFAULT_NSE_UNIVERSE.get(
        symbol.upper(),
        {"initial_price": 1000.0, "daily_vol": 0.018, "avg_volume": 1000000},
    )

    p0 = initial_price or meta["initial_price"]
    sigma = daily_vol or meta["daily_vol"]
    base_vol = avg_volume or meta["avg_volume"]

    # If weekly timeframe requested, generate daily and resample to weekly
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

    # If intraday timeframe requested, generate 1-minute session bars and resample
    if interval in (Timeframe.MINUTE_1, Timeframe.MINUTE_3, Timeframe.MINUTE_5, Timeframe.MINUTE_15, Timeframe.MINUTE_30, Timeframe.HOUR_1):
        recent_days = get_trading_days(min(num_days, 5))
        minute_candles: List[Candle] = []
        cur_p = p0
        minute_vol = sigma / 19.36
        per_minute_base_vol = max(100.0, base_vol / 375.0)

        for day_dt in recent_days:
            # 09:15 to 15:30 IST is 375 minutes
            session_start = day_dt.replace(hour=9, minute=15, second=0, microsecond=0)
            # Overnight jump between days
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
        # Log-normal daily return using local RNG
        daily_ret = float(rng.normal(loc=trend_bias, scale=sigma))
        # Cap extreme single-day jump within +/- 10% circuit limit
        daily_ret = float(np.clip(daily_ret, -0.098, 0.098))

        # Overnight gap between previous close and open
        gap_ret = float(rng.normal(loc=0.0, scale=sigma * 0.4))
        open_price = round(current_close * (1.0 + gap_ret), 2)
        open_price = max(1.0, open_price)

        close_price = round(current_close * (1.0 + daily_ret), 2)
        close_price = max(1.0, close_price)

        # High and Low based on intraday noise
        intraday_vol = sigma * float(rng.uniform(0.6, 1.4))
        high_price = round(max(open_price, close_price) * (1.0 + abs(float(rng.normal(0, intraday_vol)))), 2)
        low_price = round(min(open_price, close_price) * (1.0 - abs(float(rng.normal(0, intraday_vol)))), 2)
        low_price = max(0.5, low_price)

        # Ensure high >= low and bounds
        high_price = max(high_price, open_price, close_price)
        low_price = min(low_price, open_price, close_price)

        # Volume modeling: higher volume on larger price moves
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
    """Generates synthetic historical candles across a basket of NSE equities."""
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

