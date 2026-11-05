"""Specialist Financial AI & Quantitative Reasoning Module.
Integrates local quantized financial models (Fin-R1 / FinGPT / Qwen-2.5)
with GPU offloading on NVIDIA RTX 5060 (8GB VRAM) and deterministic fallback heuristics.
"""

from trader.ai.schemas import (
    NewsAnalysisRequest,
    NewsAnalysisResponse,
    SignalExplanationRequest,
    SignalExplanationResponse,
    StockDossierRequest,
    StockDossierResponse,
    AIHealthResponse,
)
from trader.ai.inference_client import LocalFinancialAIClient

__all__ = [
    "NewsAnalysisRequest",
    "NewsAnalysisResponse",
    "SignalExplanationRequest",
    "SignalExplanationResponse",
    "StockDossierRequest",
    "StockDossierResponse",
    "AIHealthResponse",
    "LocalFinancialAIClient",
]

