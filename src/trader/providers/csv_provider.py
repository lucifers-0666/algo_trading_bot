"""Historical CSV Market Data Provider.
Parses, normalizes, validates, and indexes local CSV Bhavcopy or OHLCV datasets.
"""

from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any, Union
import pandas as pd

from trader.domain.models import Candle, Quote, Timeframe, DataSource, IST
from trader.providers.base import MarketDataProvider
from trader.data.normalizer import normalize_row_to_candle
from trader.data.validation import validate_candle_sequence
from trader.data.resampler import resample_candles


class CSVDataProvider(MarketDataProvider):
    """Loads and serves OHLCV candles from local CSV archives."""

    def __init__(self, data_path: Optional[Union[str, Path]] = None):
        self._data_path = Path(data_path) if data_path else Path("data/sample")
        self._cache: Dict[str, List[Candle]] = {}
        self._last_update = datetime.now(IST)

        if self._data_path.exists():
            if self._data_path.is_file() and self._data_path.suffix.lower() == ".csv":
                self.load_file(self._data_path)
            elif self._data_path.is_dir():
                self.load_directory(self._data_path)

    @property
    def source_type(self) -> DataSource:
        return DataSource.CSV

    def load_file(self, file_path: Union[str, Path], default_symbol: Optional[str] = None) -> int:
        """Parses an individual CSV file, validates candles, and populates cache."""
        p = Path(file_path)
        if not p.exists():
            raise FileNotFoundError(f"CSV file not found: {p}")

        df = pd.read_csv(p)
        if df.empty:
            return 0

        # If symbol is not in columns, infer from filename (e.g., RELIANCE.csv)
        inferred_symbol = default_symbol or p.stem.upper()
        raw_candles = []

        for _, row in df.iterrows():
            try:
                c = normalize_row_to_candle(
                    row.to_dict(),
                    default_symbol=inferred_symbol,
                    source=DataSource.CSV,
                )
                raw_candles.append(c)
            except Exception:
                continue

        # Validate sequence
        valid_candles, _ = validate_candle_sequence(raw_candles, require_monotonic=True)
        if not valid_candles:
            return 0

        sym = valid_candles[0].symbol
        self._cache[sym] = valid_candles
        self._last_update = datetime.now(IST)
        return len(valid_candles)

    def load_directory(self, dir_path: Union[str, Path]) -> Dict[str, int]:
        """Scans directory and loads all .csv files."""
        d = Path(dir_path)
        results = {}
        for csv_file in d.glob("*.csv"):
            count = self.load_file(csv_file)
            results[csv_file.stem.upper()] = count
        return results

    def get_historical_candles(
        self,
        symbol: str,
        timeframe: Timeframe = Timeframe.DAILY,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[Candle]:
        sym = symbol.strip().upper()
        candles = self._cache.get(sym, [])

        if start_date:
            candles = [c for c in candles if c.timestamp >= start_date]
        if end_date:
            candles = [c for c in candles if c.timestamp <= end_date]

        if not candles:
            return []

        tf = timeframe if isinstance(timeframe, Timeframe) else Timeframe(timeframe)
        if tf == Timeframe.WEEKLY:
            return resample_candles(candles, Timeframe.WEEKLY)
        elif tf != Timeframe.DAILY:
            # If base CSV data is daily, refuse to falsely label daily bars as intraday
            if candles[0].interval == Timeframe.DAILY:
                raise ValueError(
                    f"CSV archive for {sym} is daily (1d) resolution. Intraday timeframe '{tf.value}' cannot be derived from daily Bhavcopy."
                )
            return resample_candles(candles, tf)

        return candles

    def get_latest_quote(self, symbol: str) -> Quote:
        sym = symbol.strip().upper()
        candles = self.get_historical_candles(sym)
        if not candles:
            raise ValueError(f"No historical data loaded for symbol: {sym}")

        last_c = candles[-1]
        self._last_update = datetime.now(IST)
        return Quote(
            exchange="NSE",
            symbol=sym,
            ltp=last_c.close,
            bid=round(last_c.close * 0.9995, 2),
            ask=round(last_c.close * 1.0005, 2),
            bid_qty=100.0,
            ask_qty=100.0,
            volume=last_c.volume,
            timestamp=last_c.timestamp,
            source=DataSource.CSV,
        )

    def get_available_symbols(self) -> List[str]:
        """Returns list of currently cached symbols."""
        return list(self._cache.keys())

    def get_connection_status(self) -> Dict[str, Any]:
        return {
            "provider": "csv",
            "connected": len(self._cache) > 0,
            "status": "HEALTHY" if len(self._cache) > 0 else "NO_DATA",
            "loaded_symbols_count": len(self._cache),
            "loaded_symbols": list(self._cache.keys()),
            "last_update": self._last_update.isoformat(),
        }

