"""Market Data Normalizer for Indian Equity OHLCV data.
Handles date/timestamp parsing, timezone conversion to Asia/Kolkata,
and column schema normalization across standard NSE Bhavcopy and generic feeds.
"""

from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
import pandas as pd
import pytz
from dateutil import parser as date_parser

from trader.domain.models import Candle, DataSource, Timeframe, IST

# Known column mappings across CSV formats
COLUMN_ALIASES = {
    "symbol": ["symbol", "ticker", "instrument", "sec_name"],
    "timestamp": ["timestamp", "date", "datetime", "time", "trade_date"],
    "open": ["open", "open_price", "op_prc"],
    "high": ["high", "high_price", "hi_prc"],
    "low": ["low", "low_price", "lo_prc"],
    "close": ["close", "close_price", "cl_prc", "last_price", "last"],
    "volume": ["volume", "tottrdqty", "traded_qty", "vol", "shares_traded"],
    "turnover": ["turnover", "tottrdval", "traded_val", "val_inr"],
}


def parse_timestamp_to_ist(val: Any) -> datetime:
    """Parses any date, string, or timestamp object into an explicit Asia/Kolkata localized datetime."""
    if isinstance(val, datetime):
        dt = val
    elif isinstance(val, (int, float)):
        # Check if milliseconds or seconds
        if val > 1e11:
            dt = datetime.fromtimestamp(val / 1000.0, tz=timezone.utc)
        else:
            dt = datetime.fromtimestamp(val, tz=timezone.utc)
    elif isinstance(val, str):
        # Support common formats e.g. '04-NOV-2026', '2026-11-04', '2026-11-04 09:15:00'
        clean_str = val.strip()
        dt = date_parser.parse(clean_str)
    elif isinstance(val, pd.Timestamp):
        dt = val.to_pydatetime()
    else:
        raise ValueError(f"Cannot parse timestamp from type {type(val)}: {val}")

    if dt.tzinfo is None:
        # Assume IST if naive, which is the local trading exchange standard
        return IST.localize(dt)
    return dt.astimezone(IST)


def resolve_canonical_columns(df_columns: List[str]) -> Dict[str, str]:
    """Finds best matching canonical fields from provided dataframe columns."""
    mapping = {}
    lower_cols = {str(c).strip().lower(): c for c in df_columns}

    for canonical, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            if alias in lower_cols:
                mapping[canonical] = lower_cols[alias]
                break
    return mapping


def normalize_row_to_candle(
    row: Dict[str, Any],
    default_symbol: Optional[str] = None,
    interval: Timeframe = Timeframe.DAILY,
    source: DataSource = DataSource.CSV,
) -> Candle:
    """Converts a raw dictionary or DataFrame row into a canonical Candle."""
    norm_dict = {}
    lower_row = {str(k).strip().lower(): v for k, v in row.items()}

    for canonical, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            if alias in lower_row and lower_row[alias] is not None:
                norm_dict[canonical] = lower_row[alias]
                break

    symbol = norm_dict.get("symbol") or default_symbol
    if not symbol:
        raise ValueError("Missing symbol in row and no default_symbol provided")

    raw_ts = norm_dict.get("timestamp")
    if raw_ts is None:
        raise ValueError("Missing timestamp in row")
    ts = parse_timestamp_to_ist(raw_ts)

    open_p = float(norm_dict["open"])
    high_p = float(norm_dict["high"])
    low_p = float(norm_dict["low"])
    close_p = float(norm_dict["close"])
    volume = float(norm_dict.get("volume", 0.0))
    turnover = float(norm_dict["turnover"]) if "turnover" in norm_dict and norm_dict["turnover"] is not None else None

    return Candle(
        exchange="NSE",
        symbol=str(symbol).strip().upper(),
        timestamp=ts,
        interval=interval,
        open=open_p,
        high=high_p,
        low=low_p,
        close=close_p,
        volume=volume,
        turnover=turnover,
        source=source,
    )
