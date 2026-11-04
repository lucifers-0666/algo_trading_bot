"""Data Validation Engine for Indian Equity Market Data.
Validates individual candles and time-series sequences against exchange trading rules,
OHLC consistency, chronological ordering, and abnormal volatility jumps.
"""

from datetime import datetime, timedelta
from typing import List, Optional, Tuple, Dict, Any
from pydantic import BaseModel, Field
import pytz

from trader.domain.models import Candle, IST


class ValidationResult(BaseModel):
    """Encapsulates validation outcome for a candle or dataset."""
    is_valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    rejected_count: int = 0
    accepted_count: int = 0


def validate_single_candle(
    candle: Candle,
    max_future_tolerance_minutes: int = 5,
    abnormal_return_threshold: float = 0.20,
) -> ValidationResult:
    """Performs deep sanity checks on a single Candle."""
    errors = []
    warnings = []

    # 1. Price Positivity
    if candle.open <= 0 or candle.high <= 0 or candle.low <= 0 or candle.close <= 0:
        errors.append(
            f"Non-positive price detected: O={candle.open}, H={candle.high}, L={candle.low}, C={candle.close}"
        )

    # 2. OHLC Structural Geometry
    if candle.high < candle.low:
        errors.append(f"High ({candle.high}) is lower than Low ({candle.low})")
    if candle.high < candle.open or candle.high < candle.close:
        errors.append(
            f"High ({candle.high}) must be >= Open ({candle.open}) and Close ({candle.close})"
        )
    if candle.low > candle.open or candle.low > candle.close:
        errors.append(
            f"Low ({candle.low}) must be <= Open ({candle.open}) and Close ({candle.close})"
        )

    # 3. Volume Non-negativity
    if candle.volume < 0:
        errors.append(f"Negative volume detected: {candle.volume}")

    # 4. Timestamp Sanity (No future timestamps)
    now_ist = datetime.now(IST)
    if candle.timestamp > now_ist + timedelta(minutes=max_future_tolerance_minutes):
        errors.append(
            f"Timestamp is in the future: {candle.timestamp.isoformat()} > current {now_ist.isoformat()}"
        )

    # 5. Volatility / Circuit Warnings
    intraday_range_pct = (candle.high - candle.low) / candle.low if candle.low > 0 else 0
    if intraday_range_pct > abnormal_return_threshold:
        warnings.append(
            f"Abnormal intraday spread of {intraday_range_pct:.1%}: High={candle.high}, Low={candle.low}"
        )

    is_valid = len(errors) == 0
    return ValidationResult(
        is_valid=is_valid,
        errors=errors,
        warnings=warnings,
        rejected_count=0 if is_valid else 1,
        accepted_count=1 if is_valid else 0,
    )


def validate_candle_sequence(
    candles: List[Candle],
    require_monotonic: bool = True,
    reject_duplicates: bool = True,
) -> Tuple[List[Candle], ValidationResult]:
    """Validates an entire sequence of candles for a symbol, ensuring chronological consistency."""
    if not candles:
        return [], ValidationResult(is_valid=True)

    valid_candles: List[Candle] = []
    all_errors: List[str] = []
    all_warnings: List[str] = []
    seen_timestamps = set()
    last_timestamp = None

    for idx, c in enumerate(candles):
        res = validate_single_candle(c)
        if not res.is_valid:
            for err in res.errors:
                all_errors.append(f"Row {idx} ({c.symbol} @ {c.timestamp}): {err}")
            continue

        # Check duplicate timestamps
        ts_key = c.timestamp
        if reject_duplicates and ts_key in seen_timestamps:
            all_errors.append(f"Row {idx} ({c.symbol}): Duplicate timestamp {ts_key}")
            continue

        # Check monotonic ordering
        if require_monotonic and last_timestamp is not None:
            if c.timestamp < last_timestamp:
                all_errors.append(
                    f"Row {idx} ({c.symbol}): Out-of-order timestamp {c.timestamp} < previous {last_timestamp}"
                )
                continue

        seen_timestamps.add(ts_key)
        last_timestamp = c.timestamp
        valid_candles.append(c)
        all_warnings.extend(res.warnings)

    is_valid = len(all_errors) == 0
    result = ValidationResult(
        is_valid=is_valid,
        errors=all_errors,
        warnings=all_warnings,
        rejected_count=len(candles) - len(valid_candles),
        accepted_count=len(valid_candles),
    )
    return valid_candles, result
