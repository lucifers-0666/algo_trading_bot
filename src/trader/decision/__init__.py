"""Unified Decision Support Engine.
Synthesizes technical signals, market regimes, ML predictions,
news sentiment, and risk guardrails into explainable trade dossiers.
"""

from trader.decision.decision_engine import DecisionEngine, DecisionDossier

__all__ = [
    "DecisionEngine",
    "DecisionDossier",
]
