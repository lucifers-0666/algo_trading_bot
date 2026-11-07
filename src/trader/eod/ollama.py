"""Optional Ollama narrative generation for deterministic EOD candidates.

The quantitative engine owns every numeric field. This client can only attach
three explanatory bullets and degrades safely when Ollama is unavailable.
"""
from __future__ import annotations

import json
import os
from typing import List

import requests

from trader.eod.engine import EODCandidate, RegimeSnapshot, ollama_narrative_prompt


def explain_candidate(
    candidate: EODCandidate,
    regime: RegimeSnapshot,
    *,
    base_url: str | None = None,
    model: str | None = None,
    timeout_seconds: float = 20.0,
) -> List[str]:
    url = (base_url or os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")).rstrip("/")
    model_name = model or os.getenv("OLLAMA_MODEL", "qwen2.5:7b-instruct")
    response = requests.post(
        f"{url}/api/generate",
        json={
            "model": model_name,
            "prompt": ollama_narrative_prompt(candidate, regime),
            "stream": False,
            "format": "json",
            "options": {"temperature": 0.1, "num_predict": 220},
        },
        timeout=timeout_seconds,
    )
    response.raise_for_status()
    payload = response.json()
    generated = payload.get("response", "")
    parsed = json.loads(generated)
    bullets = parsed.get("bullets")
    if not isinstance(bullets, list) or len(bullets) != 3:
        raise ValueError("Ollama response must contain exactly three bullets.")
    if not all(isinstance(item, str) and item.strip() for item in bullets):
        raise ValueError("Ollama bullets must be non-empty strings.")
    return [item.strip()[:400] for item in bullets]
