"""Financial Event Taxonomy and Rule-Based Financial Sentiment Classifier.
Categorizes financial news into institutional categories and computes
calibrated financial sentiment and market impact scores.
"""

import re
from enum import Enum
from typing import List, Dict, Tuple, Optional, Set, Any
from datetime import datetime

from trader.domain.models import EventImpact, IST


class FinancialCategory(str, Enum):
    EARNINGS = "EARNINGS"
    ORDER_WIN = "ORDER_WIN"
    M_AND_A = "M_AND_A"
    REGULATORY = "REGULATORY"
    MANAGEMENT_CHANGE = "MANAGEMENT_CHANGE"
    MACRO = "MACRO"
    GEOPOLITICAL = "GEOPOLITICAL"
    GENERAL = "GENERAL"


# Curated financial lexicon with domain-specific polarity weights
FINANCIAL_POSITIVE_PHRASES = {
    "record profit": 0.85,
    "revenue jumps": 0.75,
    "net profit surges": 0.85,
    "order win": 0.70,
    "bags order": 0.70,
    "awarded contract": 0.75,
    "guidance raised": 0.80,
    "upgraded": 0.65,
    "outperforms": 0.60,
    "strong demand": 0.55,
    "margin expansion": 0.65,
    "dividend hike": 0.60,
    "buyback": 0.55,
    "expansion": 0.50,
    "commissioned": 0.50,
    "breakthrough": 0.65,
    "gains market share": 0.70,
    "rbi cuts rate": 0.80,
    "gdp grows": 0.70,
    "fii inflows": 0.65,
}

FINANCIAL_NEGATIVE_PHRASES = {
    "profit plunges": -0.85,
    "loss widens": -0.85,
    "revenue drops": -0.70,
    "sebi penalty": -0.85,
    "sebi notice": -0.70,
    "rbi penalty": -0.80,
    "fraud": -0.95,
    "investigation": -0.75,
    "ceo resigns": -0.75,
    "auditor resigns": -0.90,
    "downgraded": -0.70,
    "margin contraction": -0.65,
    "default": -0.90,
    "strike": -0.55,
    "plant shutdown": -0.65,
    "tax demand": -0.60,
    "rbi hikes rate": -0.65,
    "inflation surges": -0.70,
    "fii outflows": -0.65,
    "tariff hike": -0.70,
    "geopolitical conflict": -0.80,
    "war escalation": -0.85,
}

CATEGORY_KEYWORDS = {
    FinancialCategory.EARNINGS: [
        "q1", "q2", "q3", "q4", "fy24", "fy25", "fy26", "quarterly", "profit",
        "net profit", "revenue", "ebitda", "pat", "margin", "results", "dividend",
    ],
    FinancialCategory.ORDER_WIN: [
        "order", "contract", "awarded", "bags", "wins project", "secures deal",
        "mou", "agreement", "commissioning",
    ],
    FinancialCategory.M_AND_A: [
        "merger", "acquisition", "acquires", "stake sale", "buyout", "takeover",
        "joint venture", "amalgamation", "demerger",
    ],
    FinancialCategory.REGULATORY: [
        "sebi", "rbi", "cci", "tribunal", "nclt", "supreme court", "high court",
        "show cause", "penalty", "notice", "investigation", "sanction", "compliance",
    ],
    FinancialCategory.MANAGEMENT_CHANGE: [
        "ceo", "cfo", "md", "director", "resigns", "appointed", "promoted",
        "board member", "auditor", "executive",
    ],
    FinancialCategory.MACRO: [
        "gdp", "inflation", "cpi", "wpi", "repo rate", "monetary policy", "rbi",
        "fiscal deficit", "trade balance", "forex reserves", "budget", "crude oil",
    ],
    FinancialCategory.GEOPOLITICAL: [
        "tariff", "sanctions", "war", "conflict", "border", "bilateral", "trade deal",
        "export duty", "import duty", "opec", "geopolitical",
    ],
}

KNOWN_INDIAN_SYMBOLS = {
    "RELIANCE": ["reliance", "ril"],
    "TCS": ["tcs", "tata consultancy"],
    "INFY": ["infosys", "infy"],
    "HDFCBANK": ["hdfc bank", "hdfc"],
    "ICICIBANK": ["icici bank", "icici"],
    "SBIN": ["state bank of india", "sbi", "sbin"],
    "TATAMOTORS": ["tata motors", "tatamotors"],
    "BHARTIARTL": ["bharti airtel", "airtel"],
    "ITC": ["itc"],
    "KOTAKBANK": ["kotak mahindra", "kotak"],
    "LT": ["larsen & toubro", "l&t"],
    "WIPRO": ["wipro"],
    "AXISBANK": ["axis bank", "axis"],
    "MARUTI": ["maruti suzuki", "maruti"],
    "SUNPHARMA": ["sun pharma", "sunpharma"],
    "TITAN": ["titan"],
    "BAJFINANCE": ["bajaj finance"],
    "NTPC": ["ntpc"],
    "ONGC": ["ongc"],
    "POWERGRID": ["power grid", "powergrid"],
}


class EventClassifier:
    """Classifies financial headlines, extracts symbol linkages, and computes financial sentiment."""

    def __init__(self, symbols_map: Optional[Dict[str, List[str]]] = None):
        self.symbols_map = symbols_map or KNOWN_INDIAN_SYMBOLS

    def extract_symbols(self, text: str) -> List[str]:
        """Identifies mentioned NSE equity symbols from headline or summary text."""
        text_lower = text.lower()
        matched: List[str] = []

        for symbol, aliases in self.symbols_map.items():
            # Match symbol directly as whole word
            pattern = rf"\b{re.escape(symbol.lower())}\b"
            if re.search(pattern, text_lower):
                matched.append(symbol)
                continue
            # Match aliases
            for alias in aliases:
                alias_pattern = rf"\b{re.escape(alias.lower())}\b"
                if re.search(alias_pattern, text_lower):
                    matched.append(symbol)
                    break

        return sorted(list(set(matched)))

    def categorize(self, text: str) -> FinancialCategory:
        """Determines the primary financial event category."""
        text_lower = text.lower()
        category_scores: Dict[FinancialCategory, int] = {cat: 0 for cat in FinancialCategory}

        for cat, keywords in CATEGORY_KEYWORDS.items():
            for kw in keywords:
                if re.search(rf"\b{re.escape(kw)}\b", text_lower):
                    category_scores[cat] += 1

        top_cat, top_score = max(category_scores.items(), key=lambda x: x[1])
        if top_score > 0:
            return top_cat
        return FinancialCategory.GENERAL

    def compute_sentiment(self, text: str) -> Tuple[float, EventImpact]:
        """Calculates normalized sentiment score in [-1.0, 1.0] and assigns EventImpact."""
        text_lower = text.lower()
        score = 0.0
        matches = 0

        # Check positive phrases
        for phrase, weight in FINANCIAL_POSITIVE_PHRASES.items():
            if phrase in text_lower:
                score += weight
                matches += 1

        # Check negative phrases
        for phrase, weight in FINANCIAL_NEGATIVE_PHRASES.items():
            if phrase in text_lower:
                score += weight
                matches += 1

        # Normalize score
        if matches > 0:
            final_score = max(-1.0, min(1.0, round(score / matches, 2)))
        else:
            final_score = 0.0

        # Determine Impact
        if final_score >= 0.25:
            impact = EventImpact.POSITIVE
        elif final_score <= -0.25:
            impact = EventImpact.NEGATIVE
        elif any(w in text_lower for w in ["fraud", "resigns", "delisting", "war", "sanctions"]):
            impact = EventImpact.HIGH_VOLATILITY
        else:
            impact = EventImpact.NEUTRAL

        return final_score, impact

    def analyze_event(self, headline: str, summary: Optional[str] = None) -> Dict[str, Any]:
        """Full pipeline: extracts category, sentiment, impact, and mentioned symbols."""
        combined_text = f"{headline} {summary or ''}"
        symbols = self.extract_symbols(combined_text)
        category = self.categorize(combined_text)
        sentiment, impact = self.compute_sentiment(combined_text)

        return {
            "category": category.value,
            "symbols": symbols,
            "sentiment_score": sentiment,
            "impact_level": impact,
        }
