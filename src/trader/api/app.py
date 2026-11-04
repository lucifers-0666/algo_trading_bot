"""Minimal local API boundary for the React dashboard.

The API deliberately exposes only safe health information at this stage. Market
provider wiring and paper-account read models must be integrated through explicit
services in later changes; this endpoint does not imply that a market feed is live.
"""

from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Indian AI Paper Trader API",
    version="0.2.0",
    docs_url="/api/docs",
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173"],
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["Accept", "Content-Type"],
)


@app.get("/api/v1/health", tags=["system"])
def health() -> dict[str, str]:
    """Return API process health and the enforced paper-only mode."""
    return {
        "status": "ok",
        "mode": "paper",
        "service": "indian-ai-paper-trader-api",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/api/v1/status", tags=["system"])
def status() -> dict[str, str | bool]:
    """Expose integration state without claiming that market data is connected."""
    return {
        "mode": "paper",
        "real_order_routing_enabled": False,
        "market_data_provider": "not_connected",
        "market_data_status": "not_configured",
        "scanner_status": "not_integrated",
        "ml_inference_status": "not_integrated",
    }
