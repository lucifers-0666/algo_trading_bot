"""NSE Instrument Master and Universe Management.
Manages stock master lists, sector classifications, circuit bands, and universe filtering.
"""

from typing import List, Dict, Optional, Any
from trader.domain.models import Instrument

# Curated benchmark universe of prominent liquid NSE Equities
CURATED_NSE_STOCKS: List[Dict[str, Any]] = [
    {"symbol": "RELIANCE", "name": "Reliance Industries Ltd.", "industry": "Oil & Gas", "isin": "INE002A01018", "circuit_pct": 0.10},
    {"symbol": "TCS", "name": "Tata Consultancy Services Ltd.", "industry": "IT - Software", "isin": "INE467B01029", "circuit_pct": 0.10},
    {"symbol": "HDFCBANK", "name": "HDFC Bank Ltd.", "industry": "Banking - Private", "isin": "INE040A01034", "circuit_pct": 0.10},
    {"symbol": "INFY", "name": "Infosys Ltd.", "industry": "IT - Software", "isin": "INE009A01021", "circuit_pct": 0.10},
    {"symbol": "ICICIBANK", "name": "ICICI Bank Ltd.", "industry": "Banking - Private", "isin": "INE090A01021", "circuit_pct": 0.10},
    {"symbol": "BHARTIARTL", "name": "Bharti Airtel Ltd.", "industry": "Telecom", "isin": "INE397D01024", "circuit_pct": 0.10},
    {"symbol": "SBIN", "name": "State Bank of India", "industry": "Banking - Public", "isin": "INE062A01020", "circuit_pct": 0.10},
    {"symbol": "ITC", "name": "ITC Ltd.", "industry": "FMCG", "isin": "INE154A01025", "circuit_pct": 0.10},
    {"symbol": "TATAMOTORS", "name": "Tata Motors Ltd.", "industry": "Automobile", "isin": "INE155A01022", "circuit_pct": 0.10},
    {"symbol": "KOTAKBANK", "name": "Kotak Mahindra Bank Ltd.", "industry": "Banking - Private", "isin": "INE237A01028", "circuit_pct": 0.10},
    {"symbol": "LT", "name": "Larsen & Toubro Ltd.", "industry": "Engineering & Construction", "isin": "INE018A01030", "circuit_pct": 0.10},
    {"symbol": "HINDUNILVR", "name": "Hindustan Unilever Ltd.", "industry": "FMCG", "isin": "INE030A01027", "circuit_pct": 0.10},
    {"symbol": "AXISBANK", "name": "Axis Bank Ltd.", "industry": "Banking - Private", "isin": "INE238A01034", "circuit_pct": 0.10},
    {"symbol": "SUNPHARMA", "name": "Sun Pharmaceutical Industries Ltd.", "industry": "Pharmaceuticals", "isin": "INE044A01036", "circuit_pct": 0.10},
    {"symbol": "MARUTI", "name": "Maruti Suzuki India Ltd.", "industry": "Automobile", "isin": "INE585B01010", "circuit_pct": 0.10},
    {"symbol": "BAJFINANCE", "name": "Bajaj Finance Ltd.", "industry": "NBFC", "isin": "INE296A01024", "circuit_pct": 0.10},
    {"symbol": "ASIANPAINT", "name": "Asian Paints Ltd.", "industry": "Consumer Durables", "isin": "INE021A01026", "circuit_pct": 0.10},
    {"symbol": "TITAN", "name": "Titan Company Ltd.", "industry": "Consumer Durables", "isin": "INE280A01028", "circuit_pct": 0.10},
    {"symbol": "HCLTECH", "name": "HCL Technologies Ltd.", "industry": "IT - Software", "isin": "INE860A01027", "circuit_pct": 0.10},
    {"symbol": "WIPRO", "name": "Wipro Ltd.", "industry": "IT - Software", "isin": "INE075A01022", "circuit_pct": 0.10},
]


class UniverseManager:
    """Manages the universe of active trading instruments."""

    def __init__(self, initial_catalog: Optional[List[Dict[str, Any]]] = None):
        catalog = initial_catalog or CURATED_NSE_STOCKS
        self._instruments: Dict[str, Instrument] = {}
        self._metadata: Dict[str, Dict[str, Any]] = {}

        for item in catalog:
            sym = item["symbol"].strip().upper()
            inst = Instrument(
                symbol=sym,
                name=item.get("name", sym),
                series="EQ",
                isin=item.get("isin"),
                tick_size=0.05,
                lot_size=1,
                is_active=True,
                industry=item.get("industry"),
            )
            self._instruments[sym] = inst
            self._metadata[sym] = item

    def get_instrument(self, symbol: str) -> Optional[Instrument]:
        return self._instruments.get(symbol.strip().upper())

    def get_all_symbols(self) -> List[str]:
        return sorted(list(self._instruments.keys()))

    def get_all_instruments(self) -> List[Instrument]:
        return list(self._instruments.values())

    def get_symbols_by_industry(self, industry: str) -> List[str]:
        return [
            inst.symbol
            for inst in self._instruments.values()
            if inst.industry and industry.lower() in inst.industry.lower()
        ]

    def get_circuit_pct(self, symbol: str) -> float:
        meta = self._metadata.get(symbol.strip().upper(), {})
        return meta.get("circuit_pct", 0.10)
