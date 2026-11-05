"""Financial News Deduplication Engine.
Removes echo-chamber duplicate headlines across global wires and RSS feeds
using token n-gram Jaccard similarity and semantic clustering.
"""

import hashlib
import re
from typing import List, Set, Dict, Any, Optional
from datetime import datetime, timedelta

from trader.domain.models import FinancialEvent


def clean_headline(text: str) -> str:
    """Normalizes headline text by removing punctuation, extra whitespace, and common noise."""
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    tokens = text.split()
    # Filter stopwords that add no discriminative value
    stopwords = {"a", "an", "the", "in", "on", "at", "for", "to", "of", "and", "is", "by", "with", "from"}
    meaningful_tokens = [t for t in tokens if t not in stopwords and len(t) > 1]
    return " ".join(meaningful_tokens)


def token_jaccard_similarity(text1: str, text2: str) -> float:
    """Computes Jaccard similarity over word tokens."""
    tokens1 = set(clean_headline(text1).split())
    tokens2 = set(clean_headline(text2).split())
    if not tokens1 or not tokens2:
        return 0.0
    intersection = tokens1.intersection(tokens2)
    union = tokens1.union(tokens2)
    return len(intersection) / len(union)


class EventDeduplicator:
    """Detects and suppresses duplicate or near-duplicate financial headlines."""

    def __init__(self, similarity_threshold: float = 0.65, time_window_hours: int = 24):
        self.similarity_threshold = similarity_threshold
        self.time_window = timedelta(hours=time_window_hours)
        self._seen_hashes: Set[str] = set()
        self._history: List[FinancialEvent] = []

    def compute_hash(self, headline: str) -> str:
        """Computes deterministic hash from cleaned headline."""
        cleaned = clean_headline(headline)
        return hashlib.sha256(cleaned.encode("utf-8")).hexdigest()

    def is_duplicate(self, candidate: FinancialEvent) -> bool:
        """Returns True if candidate event is an exact or near duplicate of a recently ingested event."""
        h = self.compute_hash(candidate.headline)
        if h in self._seen_hashes:
            return True

        # Check against recent events within the time window
        cutoff = candidate.published_at - self.time_window
        for existing in reversed(self._history):
            if existing.published_at < cutoff:
                break

            # If both mention specific symbols and they have zero overlap, not duplicates
            if candidate.symbols and existing.symbols:
                if not set(candidate.symbols).intersection(set(existing.symbols)):
                    continue

            sim = token_jaccard_similarity(candidate.headline, existing.headline)
            if sim >= self.similarity_threshold:
                return True

        return False

    def deduplicate(self, events: List[FinancialEvent]) -> List[FinancialEvent]:
        """Filters a list of financial events, discarding duplicates."""
        unique_events: List[FinancialEvent] = []
        # Sort chronologically
        sorted_events = sorted(events, key=lambda e: e.published_at)

        for event in sorted_events:
            if not self.is_duplicate(event):
                h = self.compute_hash(event.headline)
                self._seen_hashes.add(h)
                self._history.append(event)
                unique_events.append(event)

        return unique_events

    def reset(self) -> None:
        """Clears in-memory deduplication cache."""
        self._seen_hashes.clear()
        self._history.clear()
