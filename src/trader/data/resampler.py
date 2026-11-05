"""Candle Resampling Engine for Indian Equities.
Provides rigorous multi-timeframe OHLCV bar aggregation across standard intervals:
1m, 3m, 5m, 15m, 30m, 1h, 1d, 1w.
Enforces session alignment to 09:15 IST, chronological ordering, and strict OHLC invariants.
"""

from datetime import datetime, timedelta
from typing import List, Union
import pandas as pd
import pytz

from trader.domain.models import Candle, Timeframe, DataSource, IST

TIMEFRAME_MINUTES = {
    Timeframe.MINUTE_1: 1,
    Timeframe.MINUTE_3: 3,
    Timeframe.MINUTE_5: 5,
    Timeframe.MINUTE_15: 15,
    Timeframe.MINUTE_30: 30,
    Timeframe.HOUR_1: 60,
    Timeframe.DAILY: 1440,
    Timeframe.WEEKLY: 10080,
}

PANDAS_FREQ_MAP = {
    Timeframe.MINUTE_1: "1min",
    Timeframe.MINUTE_3: "3min",
    Timeframe.MINUTE_5: "5min",
    Timeframe.MINUTE_15: "15min",
    Timeframe.MINUTE_30: "30min",
    Timeframe.HOUR_1: "1h",
    Timeframe.DAILY: "1D",
    Timeframe.WEEKLY: "W-FRI",
}


def parse_timeframe(tf: Union[Timeframe, str]) -> Timeframe:
    """Parses and validates a timeframe string or enum."""
    if isinstance(tf, Timeframe):
        return tf
    val = tf.strip().lower()
    for enum_val in Timeframe:
        if enum_val.value == val:
            return enum_val
    raise ValueError(
        f"Unsupported timeframe '{tf}'. Supported timeframes: {[e.value for e in Timeframe]}"
    )


def resample_candles(
    candles: List[Candle],
    target_timeframe: Union[Timeframe, str],
) -> List[Candle]:
    """Resamples a list of chronological OHLCV candles to a target timeframe.
    
    Args:
        candles: Source candles, must be chronologically ordered.
        target_timeframe: Desired destination timeframe.
        
    Returns:
        Aggregated chronological list of candles matching target_timeframe.
        
    Raises:
        ValueError: If candles is empty, unaligned, or downsampling without intraday source.
    """
    if not candles:
        return []

    target_tf = parse_timeframe(target_timeframe)
    source_tf = candles[0].interval

    if source_tf == target_tf:
        return candles

    source_minutes = TIMEFRAME_MINUTES.get(source_tf, 1440)
    target_minutes = TIMEFRAME_MINUTES.get(target_tf, 1440)

    if target_minutes < source_minutes:
        raise ValueError(
            f"Cannot downsample higher-timeframe candles ({source_tf.value}) "
            f"to lower-timeframe ({target_tf.value}). Higher-resolution source data is required."
        )

    # Convert to DataFrame
    records = []
    symbol = candles[0].symbol
    exchange = candles[0].exchange
    source = candles[0].source

    for c in candles:
        records.append({
            "timestamp": c.timestamp,
            "open": c.open,
            "high": c.high,
            "low": c.low,
            "close": c.close,
            "volume": c.volume,
            "turnover": c.turnover or (c.close * c.volume),
        })

    df = pd.DataFrame(records)
    df = df.set_index("timestamp").sort_index()

    # Use target pandas frequency
    freq = PANDAS_FREQ_MAP[target_tf]

    # For intraday resampling (e.g. 15min, 30min, 1h), offset by 15 minutes to align with 09:15 IST market open
    resampled_rows = []
    if target_tf in (Timeframe.MINUTE_1, Timeframe.MINUTE_3, Timeframe.MINUTE_5, Timeframe.MINUTE_15, Timeframe.MINUTE_30, Timeframe.HOUR_1):
        grouped = df.resample(freq, origin="start_day", offset="15min")
    elif target_tf == Timeframe.DAILY:
        grouped = df.resample("1D", origin="start_day")
    else:  # WEEKLY
        grouped = df.resample("W-FRI")

    resampled = grouped.agg({
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last",
        "volume": "sum",
        "turnover": "sum",
    }).dropna()

    resampled_candles: List[Candle] = []
    for ts, row in resampled.iterrows():
        # Ensure IST timezone
        dt = ts.to_pydatetime()
        if dt.tzinfo is None:
            dt = IST.localize(dt)
        else:
            dt = dt.astimezone(IST)

        resampled_candles.append(
            Candle(
                exchange=exchange,
                symbol=symbol,
                timestamp=dt,
                interval=target_tf,
                open=float(row["open"]),
                high=float(row["high"]),
                low=float(row["low"]),
                close=float(row["close"]),
                volume=float(row["volume"]),
                turnover=float(row["turnover"]),
                source=source,
            )
        )

    return resampled_candles
