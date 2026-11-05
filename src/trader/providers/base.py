"""Market Data Provider Base Interface.
All live, CSV, and synthetic market data sources must conform strictly to this abstraction.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional, Callable, Dict, Any

from trader.domain.models import Candle, Quote, MarketDepth, Timeframe, DataSource


class MarketDataProvider(ABC):
    """Abstract interface decoupling consumers from specific market data vendors."""

    @property
    @abstractmethod
    def source_type(self) -> DataSource:
        """Identifies the underlying data source."""
        pass

    @abstractmethod
    def get_historical_candles(
        self,
        symbol: str,
        timeframe: Timeframe = Timeframe.DAILY,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[Candle]:
        """Fetches chronological historical OHLCV candles."""
        pass

    @abstractmethod
    def get_latest_quote(self, symbol: str) -> Quote:
        """Fetches latest real-time or snapshot quote."""
        pass

    @abstractmethod
    def get_connection_status(self) -> Dict[str, Any]:
        """Returns health, latency, connected state, and last update timestamp."""
        pass

    def get_market_depth(self, symbol: str) -> MarketDepth:
        """Fetches 5-level market depth order book. Fallback raises NotImplementedError."""
        raise NotImplementedError(f"Market depth is not supported by {self.source_type.value}")

    def subscribe_live(self, symbols: List[str], callback: Callable[[Quote], None]) -> None:
        """Subscribes to real-time quote/tick streaming (optional for offline sources)."""
        pass

    def unsubscribe_live(self, symbols: List[str]) -> None:
        """Unsubscribes from streaming feeds."""
        pass

