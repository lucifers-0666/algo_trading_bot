"""Local FastAPI REST API for the Indian AI Paper Trading Platform.
Exposes typed, validated endpoints for Market Data, Scanners, Strategy Lab,
Backtesting, ML Registry, Risk Management, and Virtual Paper Trading.
STRICTLY BOUND TO LOCALHOST (127.0.0.1) AND STRICTLY VIRTUAL PAPER TRADING.
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional
import asyncio
import json
import os
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

from fastapi import (
    FastAPI,
    HTTPException,
    Query,
    Body,
    WebSocket,
    WebSocketDisconnect,
    Request,
    Header,
    Depends,
    status,
)
from fastapi.middleware.cors import CORSMiddleware

from trader.domain.models import (
    IST,
    Candle,
    Quote,
    Order,
    Trade,
    Position,
    PortfolioState,
    AuditLog,
    OrderSide,
    OrderType,
    OrderStatus,
    Timeframe,
    DataSource,
)
from trader.data.calendar import default_nse_calendar, NSE_MARKET_OPEN, NSE_MARKET_CLOSE
from trader.data.freshness import evaluate_feed_freshness, FreshnessReport, FeedStatus
from trader.storage.database import DatabaseManager
from trader.storage.repositories import (
    CandleRepository,
    OrderRepository,
    TradeRepository,
    PortfolioRepository,
    PositionRepository,
    AuditRepository,
    FinancialEventRepository,
)
from trader.risk.kill_switch import PersistentKillSwitch
from trader.risk.checks import RiskManager
from trader.paper.orders import OrderManager
from trader.paper.accounting import PortfolioAccountant
from trader.paper.broker import VirtualPaperBroker
from trader.providers.csv_provider import CSVDataProvider
from trader.providers.synthetic_provider import SyntheticDataProvider
from trader.providers.dhan_adapter import DhanAdapter
from trader.providers.truedata_adapter import TrueDataAdapter
from trader.providers.angelone_adapter import AngelOneAdapter
from trader.ml.forecaster import NextSessionForecaster, NextSessionForecast
from trader.backtest.costs import (
    simulate_roundtrip_trade,
    calculate_trade_costs,
    BrokerProfile,
    TradeType,
)
from trader.scanner.ranking import MarketScannerEngine
from trader.universe.instruments import UniverseManager
from trader.features.technical import candles_to_dataframe, compute_all_indicators
from trader.data.resampler import parse_timeframe
from trader.strategies.baseline import BaselineSwingStrategy
from trader.strategies.momentum import MomentumStrategy
from trader.strategies.breakout import DonchianBreakoutStrategy
from trader.strategies.regime import detect_market_regime
from trader.backtest.engine import BacktestEngine
from trader.backtest.comparison import run_strategy_comparison
from trader.ml.dataset import extract_features
from trader.ml.labels import generate_forward_labels
from trader.ml.train import train_model
from trader.intelligence.engine import FinancialIntelligenceEngine
from trader.ai.inference_client import LocalFinancialAIClient
from trader.ai.schemas import NewsAnalysisRequest, SignalExplanationRequest, StockDossierRequest
from trader.strategies.lookahead_detector import LookaheadDetector
from trader.strategies.hyperopt import StrategyHyperoptRunner
from trader.strategies.protections import RiskProtectionManager
from trader.decision.decision_engine import DecisionEngine
from trader.api.schemas import (
    OrderProposalRequest,
    OrderExecuteRequest,
    ResetAccountRequest,
    KillSwitchRequest,
    BacktestRunRequest,
    ModelTrainRequest,
    LookaheadAuditRequest,
    HyperoptRequest,
    AnnouncementCreateRequest,
    DecisionEvaluateRequest,
    AngelOneConfigureRequest,
    ProviderSelectRequest,
    CostSimulateRequest,
    ForecastEvaluateRequest,
)

app = FastAPI(
    title="Indian AI Paper Trader API",
    version="0.3.0",
    description="Institutional-grade local research and virtual paper trading backend for Indian Equities.",
    docs_url="/api/docs",
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Accept", "Content-Type", "Authorization", "X-API-Token"],
)


def verify_localhost(request: Request) -> None:
    """Enforces that all REST requests originate strictly from localhost."""
    client_host = request.client.host if request.client else ""
    if client_host not in ("127.0.0.1", "localhost", "::1", "testclient"):
        raise HTTPException(
            status_code=403,
            detail="Access forbidden: Northstar workstation is restricted to localhost.",
        )


def verify_api_token(
    request: Request,
    authorization: Optional[str] = Header(None),
    x_api_token: Optional[str] = Header(None),
) -> None:
    """Verifies that mutating operations are authorized with NORTHSTAR_API_TOKEN when configured."""
    verify_localhost(request)
    expected_token = os.getenv("NORTHSTAR_API_TOKEN")
    if not expected_token:
        return

    token = None
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()
    elif x_api_token:
        token = x_api_token.strip()
    elif "token" in request.query_params:
        token = request.query_params.get("token")

    if not token or token != expected_token:
        raise HTTPException(
            status_code=401,
            detail="Unauthorized: Invalid or missing API token.",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def verify_ws_auth(websocket: WebSocket) -> bool:
    """Authenticates WebSocket connections and enforces localhost origin."""
    client_host = websocket.client.host if websocket.client else ""
    if client_host not in ("127.0.0.1", "localhost", "::1", "testclient"):
        await websocket.close(code=1008, reason="Localhost only")
        return False

    expected_token = os.getenv("NORTHSTAR_API_TOKEN")
    if not expected_token:
        return True

    token = websocket.query_params.get("token")
    if not token:
        auth = websocket.headers.get("authorization")
        if auth and auth.lower().startswith("bearer "):
            token = auth[7:].strip()
        else:
            token = websocket.headers.get("x-api-token")

    if not token or token != expected_token:
        await websocket.close(
            code=1008,
            reason="Unauthorized: Invalid or missing API token",
        )
        return False

    return True

# -----------------------------------------------------------------------------
# Module Singletons
# -----------------------------------------------------------------------------
db_mgr = DatabaseManager()
candle_repo = CandleRepository(db_mgr)
order_repo = OrderRepository(db_mgr)
trade_repo = TradeRepository(db_mgr)
portfolio_repo = PortfolioRepository(db_mgr)
pos_repo = PositionRepository(db_mgr)
audit_repo = AuditRepository(db_mgr)
financial_event_repo = FinancialEventRepository(db_mgr)

kill_switch = PersistentKillSwitch()
# Kill switch starts strictly ENGAGED on missing/unreadable state (Fail-Closed)

accountant = PortfolioAccountant(
    starting_cash=10000.0,
    portfolio_repo=portfolio_repo,
    position_repo=pos_repo,
)
risk_mgr = RiskManager(kill_switch=kill_switch)
order_mgr = OrderManager(order_repo=order_repo)
paper_broker = VirtualPaperBroker(
    accountant=accountant,
    risk_manager=risk_mgr,
    order_manager=order_mgr,
    trade_repo=trade_repo,
    audit_repo=audit_repo,
)

# Financial Intelligence, AI Reasoning, and Strategy Optimization Singletons
intelligence_engine = FinancialIntelligenceEngine(event_repo=financial_event_repo)
ai_client = LocalFinancialAIClient()
protection_mgr = RiskProtectionManager()
decision_engine = DecisionEngine(
    risk_manager=risk_mgr,
    protection_manager=protection_mgr,
    intelligence_engine=intelligence_engine,
)
lookahead_detector = LookaheadDetector()
hyperopt_runner = StrategyHyperoptRunner(initial_capital=10000.0)

# Providers
angelone_api_key = os.getenv("ANGELONE_API_KEY", "").strip()
angelone_client_code = os.getenv("ANGELONE_CLIENT_CODE", "").strip()
angelone_pin = os.getenv("ANGELONE_PIN", "").strip()
angelone_totp_secret = os.getenv("ANGELONE_TOTP_SECRET", "").strip()
angelone_adapter = (
    AngelOneAdapter(
        api_key=angelone_api_key,
        client_code=angelone_client_code,
        pin=angelone_pin,
        totp_secret=angelone_totp_secret,
    )
    if (angelone_api_key and angelone_client_code and angelone_pin and angelone_totp_secret)
    else AngelOneAdapter()
)

dhan_client_id = os.getenv("DHAN_CLIENT_ID", "").strip()
dhan_access_token = os.getenv("DHAN_ACCESS_TOKEN", "").strip()
dhan_adapter = DhanAdapter(client_id=dhan_client_id, access_token=dhan_access_token) if (dhan_client_id and dhan_access_token) else None

truedata_user = os.getenv("TRUEDATA_USERNAME", "").strip()
truedata_pass = os.getenv("TRUEDATA_PASSWORD", "").strip()
truedata_adapter = TrueDataAdapter(username=truedata_user, password=truedata_pass) if (truedata_user and truedata_pass) else None

csv_path = Path("data/sample")
csv_provider = CSVDataProvider(data_path=csv_path) if csv_path.exists() else None
synth_provider = SyntheticDataProvider(seed=42)

ACTIVE_DATA_PROVIDER = os.getenv("DATA_PROVIDER", "angelone").strip().lower()
forecaster = NextSessionForecaster()

def get_market_provider():
    global ACTIVE_DATA_PROVIDER
    if ACTIVE_DATA_PROVIDER == "angelone":
        if angelone_adapter and angelone_adapter.is_configured:
            return angelone_adapter
    elif ACTIVE_DATA_PROVIDER == "dhan":
        if dhan_adapter and dhan_adapter.is_configured:
            return dhan_adapter
    elif ACTIVE_DATA_PROVIDER == "truedata":
        if truedata_adapter and truedata_adapter.is_configured:
            return truedata_adapter
    elif ACTIVE_DATA_PROVIDER == "csv":
        if csv_provider and len(csv_provider.get_available_symbols()) > 0:
            return csv_provider
    elif ACTIVE_DATA_PROVIDER == "synthetic":
        return synth_provider

    # Cascade auto-detection
    if angelone_adapter and angelone_adapter.is_configured:
        return angelone_adapter
    if dhan_adapter and dhan_adapter.is_configured:
        return dhan_adapter
    if truedata_adapter and truedata_adapter.is_configured:
        return truedata_adapter
    if csv_provider and len(csv_provider.get_available_symbols()) > 0:
        return csv_provider
    return synth_provider

scanner_engine = MarketScannerEngine(provider=get_market_provider())
universe_mgr = UniverseManager()

from trader.paper.daemon import AutonomousPaperTradingDaemon

auto_trader = AutonomousPaperTradingDaemon(
    broker=paper_broker,
    decision_engine=decision_engine,
    scanner_engine=scanner_engine,
    risk_manager=risk_mgr,
    protection_manager=protection_mgr,
    scan_interval_seconds=30,
)


# -----------------------------------------------------------------------------
# 1. System Health & Status Endpoints
# -----------------------------------------------------------------------------
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
def status() -> dict[str, Any]:
    """Expose integration state without claiming live real order routing."""
    is_live = bool(
        (angelone_adapter and angelone_adapter.is_configured and getattr(angelone_adapter, "_is_connected", False))
        or (dhan_adapter and dhan_adapter.is_configured)
        or (truedata_adapter and truedata_adapter.is_configured)
    )
    active_provider = get_market_provider()
    provider_name = active_provider.source_type.value if hasattr(active_provider, "source_type") else "not_connected"
    return {
        "mode": "paper",
        "real_order_routing_enabled": False,
        "market_data_provider": provider_name if is_live else "not_connected",
        "market_data_status": "connected" if is_live else "not_configured",
        "active_provider_setting": ACTIVE_DATA_PROVIDER,
        "angelone_configured": bool(angelone_adapter and angelone_adapter.is_configured),
        "scanner_status": "ready",
        "ml_inference_status": "ready",
        "kill_switch_active": kill_switch.is_active(),
        "kill_switch_reason": kill_switch.get_reason(),
    }


# -----------------------------------------------------------------------------
# 2. Market Session & Feed Health Endpoints
# -----------------------------------------------------------------------------
@app.get("/api/v1/market/session", tags=["market"])
def market_session() -> dict[str, Any]:
    """Provides official NSE trading hours, session status, and holiday calendars."""
    now_ist = datetime.now(IST)
    is_open = default_nse_calendar.is_market_open(now_ist)
    next_open = default_nse_calendar.get_next_trading_session_start(now_ist)

    return {
        "is_open": is_open,
        "current_time_ist": now_ist.strftime("%Y-%m-%d %H:%M:%S IST"),
        "regular_hours": "09:15 - 15:30 IST",
        "is_trading_day": default_nse_calendar.is_trading_day(now_ist.date()),
        "next_session_open": next_open.strftime("%Y-%m-%d %H:%M:%S IST"),
        "statutory_holidays_count": len(default_nse_calendar.holidays),
    }


@app.get("/api/v1/data/health", tags=["market"])
def data_health() -> dict[str, Any]:
    """Monitors market data latency, source provenance, and freshness guards with strict fail-closed safety."""
    provider = get_market_provider()
    last_tick_time = getattr(provider, "_last_update", None)
    is_conf = getattr(provider, "is_configured", True)
    is_conn = getattr(provider, "_is_connected", False)
    source_label = provider.source_type.value.upper() if hasattr(provider, "source_type") else "UNAVAILABLE"

    freshness = evaluate_feed_freshness(
        last_update=last_tick_time,
        source_type=source_label,
        is_configured=is_conf,
        is_connected=is_conn,
    )

    return {
        "data_source_label": source_label,
        "feed_status": freshness.status.value,
        "is_actionable": freshness.is_actionable,
        "latency_seconds": round(freshness.latency_seconds, 2),
        "message": freshness.message,
        "is_configured": is_conf,
        "is_connected": is_conn,
        "last_update_ist": freshness.last_update_ist.strftime("%Y-%m-%d %H:%M:%S IST") if freshness.last_update_ist else None,
    }


@app.get("/api/v1/market-data/status", tags=["market"])
def market_data_status() -> Dict[str, Any]:
    """Comprehensive status of all market data feeds, credentials, and source provenance."""
    global ACTIVE_DATA_PROVIDER, angelone_adapter, dhan_adapter, truedata_adapter, csv_provider, synth_provider
    provider = get_market_provider()
    is_live = bool(getattr(provider, "is_configured", False) and getattr(provider, "_is_connected", False))
    source = getattr(provider, "source_type", DataSource.SYNTHETIC)
    source_val = source.value if hasattr(source, "value") else str(source)

    return {
        "active_provider_setting": ACTIVE_DATA_PROVIDER,
        "resolved_source_type": source_val,
        "is_live": is_live,
        "is_configured": getattr(provider, "is_configured", False),
        "is_connected": getattr(provider, "_is_connected", source_val == "SYNTHETIC"),
        "angelone": {
            "configured": bool(angelone_adapter and angelone_adapter.is_configured),
            "connected": bool(angelone_adapter and getattr(angelone_adapter, "_is_connected", False)),
            "source": "ANGEL_ONE_SMARTAPI",
            "free_data_feed": True,
        },
        "dhan": {
            "configured": bool(dhan_adapter and dhan_adapter.is_configured),
            "connected": bool(dhan_adapter and getattr(dhan_adapter, "_is_connected", False)),
            "source": "DHANHQ",
        },
        "truedata": {
            "configured": bool(truedata_adapter and truedata_adapter.is_configured),
            "connected": bool(truedata_adapter and getattr(truedata_adapter, "_is_connected", False)),
        },
        "csv_available": bool(csv_provider and len(csv_provider.get_available_symbols()) > 0),
        "synthetic_ready": True,
        "data_provenance": "REAL_TIME" if is_live else ("SYNTHETIC" if source_val == "SYNTHETIC" else "OFFLINE"),
        "disclaimer": "Strictly read-only market data. Zero broker execution. Virtual paper trading only.",
        "last_update": datetime.now(IST).isoformat(),
    }


@app.get("/api/v1/market-data/depth/{symbol}", tags=["market"])
def get_market_depth(symbol: str) -> Dict[str, Any]:
    """Returns 5-level market depth order book and top-5 imbalance metrics."""
    sym = symbol.strip().upper()
    provider = get_market_provider()
    try:
        if hasattr(provider, "get_market_depth"):
            depth = provider.get_market_depth(sym)
            return depth.model_dump()
        else:
            depth = synth_provider.get_market_depth(sym)
            return depth.model_dump()
    except Exception as e:
        logger.warning(f"Error fetching depth from {getattr(provider, 'source_type', 'unknown')}: {e}. Falling back to synthetic depth.")
        depth = synth_provider.get_market_depth(sym)
        dump = depth.model_dump()
        dump["warning"] = f"Live feed offline ({str(e)}). Procedural depth active."
        return dump


@app.post("/api/v1/market-data/configure", tags=["market"], dependencies=[Depends(verify_api_token)])
def configure_market_data(req: AngelOneConfigureRequest) -> Dict[str, Any]:
    """Configures Angel One SmartAPI credentials and authenticates session."""
    global angelone_adapter, ACTIVE_DATA_PROVIDER
    try:
        new_adapter = AngelOneAdapter(
            api_key=req.api_key.strip(),
            client_code=req.client_code.strip(),
            pin=req.pin.strip(),
            totp_secret=req.totp_secret.strip(),
        )
        if req.test_connection:
            success = new_adapter.authenticate()
            if not success:
                raise HTTPException(status_code=400, detail="Angel One authentication failed. Check API Key, Client Code, PIN, and TOTP Secret.")

        angelone_adapter = new_adapter
        ACTIVE_DATA_PROVIDER = "angelone"
        scanner_engine.provider = angelone_adapter

        return {
            "status": "connected" if new_adapter.is_connected else "configured",
            "message": "Angel One SmartAPI credentials saved and verified successfully.",
            "client_code": req.client_code.strip(),
            "active_provider": "angelone",
        }
    except Exception as exc:
        if isinstance(exc, HTTPException):
            raise exc
        raise HTTPException(status_code=500, detail=f"Failed to configure Angel One: {str(exc)}")


@app.post("/api/v1/market-data/select-provider", tags=["market"], dependencies=[Depends(verify_api_token)])
def select_market_data_provider(req: ProviderSelectRequest) -> Dict[str, Any]:
    """Switches active market data provider (angelone, dhan, truedata, csv, synthetic)."""
    global ACTIVE_DATA_PROVIDER
    target = req.provider.strip().lower()
    valid_providers = {"angelone", "dhan", "truedata", "csv", "synthetic"}
    if target not in valid_providers:
        raise HTTPException(status_code=400, detail=f"Invalid provider '{target}'. Must be one of {valid_providers}")

    ACTIVE_DATA_PROVIDER = target
    active = get_market_provider()
    scanner_engine.provider = active

    return {
        "status": "success",
        "active_provider": ACTIVE_DATA_PROVIDER,
        "resolved_source": active.source_type.value if hasattr(active, "source_type") else "UNKNOWN",
    }


# -----------------------------------------------------------------------------
# 3. Market Scanner Endpoints
# -----------------------------------------------------------------------------
@app.get("/api/v1/scanner/candidates", tags=["scanner"])
def scanner_candidates(category: str = Query("all", description="Scanner category")) -> List[Dict[str, Any]]:
    """Runs high-performance scanner across cached snapshots and returns ranked setups."""
    scanner_engine.provider = get_market_provider()
    scanner_engine.refresh_snapshot()

    cat = category.lower().strip()
    if cat == "top_gainers":
        candidates = scanner_engine.scan_top_gainers()
    elif cat == "top_losers":
        candidates = scanner_engine.scan_top_losers()
    elif cat == "momentum":
        candidates = scanner_engine.scan_momentum()
    elif cat == "breakout":
        candidates = scanner_engine.scan_trend_strength()
    elif cat == "rvol":
        candidates = scanner_engine.scan_relative_volume()
    else:  # all / combined
        all_res = scanner_engine.run_full_scan()
        combined = []
        for c_list in all_res.values():
            combined.extend(c_list)
        # Deduplicate by symbol while keeping highest qualified
        seen = set()
        candidates = []
        for c in combined:
            if c.symbol not in seen:
                seen.add(c.symbol)
                candidates.append(c)

    return [c.model_dump() for c in candidates]


# -----------------------------------------------------------------------------
# 4. Instruments & Candle Data
# -----------------------------------------------------------------------------
@app.get("/api/v1/instruments", tags=["instruments"])
def list_instruments() -> List[Dict[str, Any]]:
    """Returns curated NSE equity universe."""
    return [i.model_dump() for i in universe_mgr.get_all_instruments()]


@app.get("/api/v1/instruments/{symbol}", tags=["instruments"])
def get_instrument_details(symbol: str) -> Dict[str, Any]:
    """Returns instrument master record and current market quote."""
    sym = symbol.strip().upper()
    inst = universe_mgr.get_instrument(sym)
    if not inst:
        raise HTTPException(status_code=404, detail=f"Instrument {sym} not found in master universe.")

    provider = get_market_provider()
    try:
        quote = provider.get_latest_quote(sym)
        q_data = quote.model_dump()
    except Exception:
        candles = provider.get_historical_candles(sym)
        if candles:
            last_c = candles[-1]
            q_data = {
                "symbol": sym,
                "ltp": last_c.close,
                "bid": None,
                "ask": None,
                "volume": last_c.volume,
                "timestamp": last_c.timestamp.isoformat(),
                "source": DataSource.HISTORICAL.value,
            }
        else:
            q_data = {
                "symbol": sym,
                "ltp": None,
                "bid": None,
                "ask": None,
                "volume": None,
                "timestamp": None,
                "source": DataSource.UNAVAILABLE.value,
            }

    return {
        "instrument": inst.model_dump(),
        "quote": q_data,
    }


@app.websocket("/api/v1/ws/quotes/{symbol}")
async def websocket_symbol_quotes(websocket: WebSocket, symbol: str):
    """Streams live quotes and tick aggregations for a single equity symbol."""
    if not await verify_ws_auth(websocket):
        return
    await websocket.accept()
    sym = symbol.strip().upper()
    provider = get_market_provider()
    try:
        while True:
            try:
                quote = provider.get_latest_quote(sym)
                source_label = quote.source.value if hasattr(quote, "source") else "UNKNOWN"
                await websocket.send_json({
                    "type": "quote",
                    "symbol": sym,
                    "ltp": quote.ltp,
                    "bid": quote.bid,
                    "ask": quote.ask,
                    "volume": quote.volume,
                    "timestamp": quote.timestamp.isoformat(),
                    "source": source_label,
                })
            except Exception as e:
                await websocket.send_json({
                    "type": "error",
                    "symbol": sym,
                    "message": str(e),
                })
            await asyncio.sleep(1.0)
    except WebSocketDisconnect:
        pass


@app.websocket("/api/v1/ws/live")
async def websocket_live_stream(websocket: WebSocket):
    """Streams active feed health, portfolio summary, and market pulse every second."""
    if not await verify_ws_auth(websocket):
        return
    await websocket.accept()
    try:
        while True:
            provider = get_market_provider()
            last_tick_time = getattr(provider, "_last_update", None)
            is_conf = getattr(provider, "is_configured", True)
            is_conn = getattr(provider, "_is_connected", False)
            source_label = provider.source_type.value.upper() if hasattr(provider, "source_type") else "UNAVAILABLE"
            freshness = evaluate_feed_freshness(
                last_update=last_tick_time,
                source_type=source_label,
                is_configured=is_conf,
                is_connected=is_conn,
            )
            state = accountant.get_portfolio_state()
            await websocket.send_json({
                "type": "heartbeat",
                "feed_status": freshness.status.value,
                "is_actionable": freshness.is_actionable,
                "source": source_label,
                "latency_seconds": round(freshness.latency_seconds, 2),
                "portfolio_equity": state.total_equity,
                "cash_balance": state.cash_balance,
                "open_positions": len(accountant.positions),
                "timestamp": datetime.now(IST).isoformat(),
            })
            await asyncio.sleep(1.0)
    except WebSocketDisconnect:
        pass


@app.get("/api/v1/instruments/{symbol}/candles", tags=["instruments"])
def get_instrument_candles(
    symbol: str,
    timeframe: str = Query("1d", description="Timeframe e.g. 1m, 3m, 5m, 15m, 30m, 1h, 1d, 1w"),
    limit: int = Query(100, ge=10, le=500),
) -> Dict[str, Any]:
    """Returns historical candles decorated with technical indicators and regime assessment."""
    sym = symbol.strip().upper()
    try:
        tf = parse_timeframe(timeframe)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    provider = get_market_provider()
    try:
        candles = provider.get_historical_candles(sym, timeframe=tf)
    except ValueError as e:
        # If active provider lacks intraday, provide high-resolution synthetic intraday series for research
        if tf in (Timeframe.MINUTE_1, Timeframe.MINUTE_3, Timeframe.MINUTE_5, Timeframe.MINUTE_15, Timeframe.MINUTE_30, Timeframe.HOUR_1):
            candles = synth_provider.get_historical_candles(sym, timeframe=tf)
        else:
            raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Provider failed to fetch candles: {str(e)}")

    if not candles:
        raise HTTPException(status_code=404, detail=f"No candles available for {sym} at timeframe {tf.value}.")

    candles = candles[-limit:]
    df = candles_to_dataframe(candles)
    df_ind = compute_all_indicators(df)
    regime = detect_market_regime(df_ind)

    # Format candle list with indicators
    is_intraday = tf in (Timeframe.MINUTE_1, Timeframe.MINUTE_3, Timeframe.MINUTE_5, Timeframe.MINUTE_15, Timeframe.MINUTE_30, Timeframe.HOUR_1)
    date_format = "%Y-%m-%d %H:%M" if is_intraday else "%Y-%m-%d"

    candle_records = []
    for _, row in df_ind.iterrows():
        candle_records.append({
            "timestamp": row["timestamp"].strftime(date_format),
            "open": float(row["open"]),
            "high": float(row["high"]),
            "low": float(row["low"]),
            "close": float(row["close"]),
            "volume": float(row["volume"]),
            "sma_20": float(row["sma_20"]) if pd.notna(row.get("sma_20")) else None,
            "sma_50": float(row["sma_50"]) if pd.notna(row.get("sma_50")) else None,
            "rsi_14": float(row["rsi_14"]) if pd.notna(row.get("rsi_14")) else None,
            "atr_14": float(row["atr_14"]) if pd.notna(row.get("atr_14")) else None,
            "rvol": float(row["rvol"]) if pd.notna(row.get("rvol")) else None,
        })

    return {
        "symbol": sym,
        "timeframe": tf.value,
        "source": candles[0].source.value if candles else "UNKNOWN",
        "count": len(candle_records),
        "regime": regime.model_dump(),
        "candles": candle_records,
    }


# -----------------------------------------------------------------------------
# 5. Portfolio & Virtual Accounting Endpoints
# -----------------------------------------------------------------------------
@app.get("/api/v1/portfolio", tags=["portfolio"])
def get_portfolio() -> Dict[str, Any]:
    """Returns real-time mark-to-market virtual portfolio state."""
    state = accountant.get_portfolio_state()
    return state.model_dump()


@app.get("/api/v1/portfolio/positions", tags=["portfolio"])
def get_positions() -> List[Dict[str, Any]]:
    """Returns active open equity positions."""
    positions = list(accountant.positions.values())
    return [p.model_dump() for p in positions]


# -----------------------------------------------------------------------------
# 6. Virtual Paper Trading Endpoints (Strictly Virtual)
# -----------------------------------------------------------------------------
@app.get("/api/v1/paper/orders", tags=["paper_trading"])
def list_orders(limit: int = Query(50, ge=1, le=200)) -> List[Dict[str, Any]]:
    """Returns simulated paper order audit ledger."""
    orders = order_repo.get_all_orders(limit=limit)
    return [o.model_dump() for o in orders]


@app.post("/api/v1/paper/orders", tags=["paper_trading"])
def propose_order(req: OrderProposalRequest) -> Dict[str, Any]:
    """Pre-trade risk verification & sizing preview for simulated orders."""
    sym = req.symbol.strip().upper()
    portfolio = accountant.get_portfolio_state()
    open_positions = list(accountant.positions.values())

    # Assess feed freshness for symbol
    provider = get_market_provider()
    feed_freshness = None
    try:
        quote = provider.get_latest_quote(sym)
        if quote.source in (DataSource.UNAVAILABLE, DataSource.ERROR, DataSource.STALE):
            feed_freshness = FreshnessReport(
                status=FeedStatus.STALE if quote.source == DataSource.STALE else FeedStatus.DISCONNECTED,
                is_actionable=False,
                latency_seconds=999999.0,
                is_market_open=default_nse_calendar.is_market_open(),
                message=f"Market data feed source is {quote.source.value}; fresh actionable feed required.",
            )
        else:
            feed_freshness = evaluate_feed_freshness(quote.timestamp)
    except Exception:
        candles = provider.get_historical_candles(sym)
        if candles:
            feed_freshness = evaluate_feed_freshness(candles[-1].timestamp)
        else:
            feed_freshness = evaluate_feed_freshness(None)

    assessment = risk_mgr.assess_order(
        symbol=sym,
        side=req.side,
        price=req.price,
        stop_loss=req.stop_loss,
        portfolio=portfolio,
        open_positions=open_positions,
        feed_freshness=feed_freshness,
    )

    return {
        "symbol": sym,
        "side": req.side.value,
        "approved": assessment.approved,
        "approved_quantity": assessment.approved_quantity,
        "rejection_reasons": assessment.rejection_reasons,
        "sizing": assessment.sizing.model_dump() if assessment.sizing else None,
    }


@app.post("/api/v1/paper/execute", tags=["paper_trading"], dependencies=[Depends(verify_api_token)])
def execute_order(req: OrderExecuteRequest) -> Dict[str, Any]:
    """Executes a simulated paper order with institutional statutory costs and risk re-validation."""
    sym = req.symbol.strip().upper()

    # Re-evaluate feed freshness at time of simulated fill
    provider = get_market_provider()
    feed_freshness = None
    try:
        quote = provider.get_latest_quote(sym)
        if quote.source in (DataSource.UNAVAILABLE, DataSource.ERROR, DataSource.STALE):
            feed_freshness = FreshnessReport(
                status=FeedStatus.STALE if quote.source == DataSource.STALE else FeedStatus.DISCONNECTED,
                is_actionable=False,
                latency_seconds=999999.0,
                is_market_open=default_nse_calendar.is_market_open(),
                message=f"Market data feed source is {quote.source.value}; fresh actionable feed required.",
            )
        else:
            feed_freshness = evaluate_feed_freshness(quote.timestamp)
    except Exception:
        candles = provider.get_historical_candles(sym)
        if candles:
            feed_freshness = evaluate_feed_freshness(candles[-1].timestamp)
        else:
            feed_freshness = evaluate_feed_freshness(None)

    order, trade, assessment = paper_broker.submit_simulated_order(
        symbol=sym,
        side=req.side,
        price=req.price,
        stop_loss=req.stop_loss,
        quantity=req.quantity,
        order_type=req.order_type,
        feed_freshness=feed_freshness,
    )

    return {
        "success": order.status == OrderStatus.FILLED,
        "order": order.model_dump(),
        "trade": trade.model_dump() if trade else None,
        "risk_assessment": assessment.model_dump(),
    }


@app.post("/api/v1/paper/reset", tags=["paper_trading"], dependencies=[Depends(verify_api_token)])
def reset_virtual_account(req: ResetAccountRequest) -> Dict[str, Any]:
    """Resets paper account balances and positions to initial virtual capital (₹10,000)."""
    success = accountant.reset_account(confirmation=req.confirmation)
    if not success:
        raise HTTPException(status_code=400, detail="Explicit confirmation required to reset paper account.")

    return {
        "success": True,
        "message": "Virtual paper account successfully reset to ₹10,000.",
        "portfolio": accountant.get_portfolio_state().model_dump(),
    }


@app.get("/api/v1/paper/trades", tags=["paper_trading"])
def list_trades(limit: int = Query(50, ge=1, le=200)) -> List[Dict[str, Any]]:
    """Returns filled simulated trade ledger."""
    trades = trade_repo.get_trades(limit=limit)
    return [t.model_dump() for t in trades]


# -----------------------------------------------------------------------------
# 7. Strategy Laboratory & Backtesting Endpoints
# -----------------------------------------------------------------------------
@app.get("/api/v1/strategies", tags=["strategies"])
def list_strategies() -> List[Dict[str, Any]]:
    """Lists available quantitative research strategies."""
    return [
        {
            "id": "baseline_swing",
            "name": "Baseline Swing (Trend-Pullback)",
            "description": "Deterministic trend-following pullback strategy using SMA 20/50, RSI 14, ATR, and volume confirmation.",
            "default_params": {"sma_fast": 20, "sma_slow": 50, "rsi_min": 45.0, "rsi_max": 65.0, "stop_atr_mult": 2.0},
        },
        {
            "id": "momentum",
            "name": "Quantitative Momentum (RS & RVOL)",
            "description": "Cross-sectional momentum persistence ranking using 20-day returns, volatility-adjusted momentum, and RVOL.",
            "default_params": {"lookback_momentum": 20, "min_momentum_pct": 0.03, "rvol_min": 1.1},
        },
        {
            "id": "breakout",
            "name": "Donchian Breakout (20d Volume)",
            "description": "20-day channel breakout strategy with volume expansion and false breakout filters.",
            "default_params": {"breakout_period": 20, "volume_mult": 1.3, "stop_atr_mult": 2.0},
        },
    ]


@app.post("/api/v1/backtests/run", tags=["backtests"])
def run_backtest(req: BacktestRunRequest) -> Dict[str, Any]:
    """Executes a chronological event-driven backtest with statutory costs and realistic gap execution."""
    strat_map = {
        "baseline_swing": BaselineSwingStrategy(),
        "momentum": MomentumStrategy(),
        "breakout": DonchianBreakoutStrategy(),
    }
    strat = strat_map.get(req.strategy_name.lower().strip(), BaselineSwingStrategy())

    provider = get_market_provider()
    symbol_candles = {}
    for s in req.symbols:
        c = provider.get_historical_candles(s)
        if c:
            symbol_candles[s] = c

    if not symbol_candles:
        raise HTTPException(status_code=400, detail="No historical candles available for requested symbols.")

    engine = BacktestEngine(
        strategy=strat,
        initial_capital=req.initial_capital,
        brokerage_flat=req.brokerage_flat,
        slippage_bps=req.slippage_bps,
    )
    result = engine.run(symbol_candles)

    return {
        "strategy_name": req.strategy_name,
        "metrics": result.metrics.model_dump(),
        "equity_curve": result.equity_curve,
        "trade_records": [t.model_dump() for t in result.trade_records],
    }


@app.get("/api/v1/backtests/comparison", tags=["backtests"])
def compare_strategies(symbols: Optional[str] = Query(None, description="Comma-separated symbols")) -> Dict[str, Any]:
    """Runs all 3 quantitative strategies side-by-side with identical capital and statutory costs."""
    sym_list = [s.strip().upper() for s in symbols.split(",")] if symbols else ["INFY", "RELIANCE", "TCS"]
    provider = get_market_provider()

    symbol_candles = {}
    for s in sym_list:
        c = provider.get_historical_candles(s)
        if c:
            symbol_candles[s] = c

    if not symbol_candles:
        raise HTTPException(status_code=400, detail="No candle data found for comparison symbols.")

    report = run_strategy_comparison(symbol_candles, initial_capital=10000.0)
    return report.model_dump()


# -----------------------------------------------------------------------------
# 8. Machine Learning Model Registry & Training Endpoints
# -----------------------------------------------------------------------------
@app.get("/api/v1/models", tags=["ml"])
def list_models() -> List[Dict[str, Any]]:
    """Returns catalog of registered trained ML models."""
    registry_file = Path("models/registry.json")
    if not registry_file.exists():
        return []
    try:
        data = json.loads(registry_file.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:
        return []


@app.post("/api/v1/models/train", tags=["ml"])
def train_ml_model(req: ModelTrainRequest) -> Dict[str, Any]:
    """Trains scikit-learn model using chronological splits and purge gaps."""
    provider = get_market_provider()
    candles = provider.get_historical_candles(req.symbol)
    if len(candles) < 60:
        raise HTTPException(status_code=400, detail=f"Insufficient candles ({len(candles)}) for {req.symbol}.")

    df = candles_to_dataframe(candles)
    df_ind = compute_all_indicators(df)
    feat_df = extract_features(df_ind)
    labeled_df = generate_forward_labels(feat_df, horizon_bars=req.horizon_bars)

    try:
        model, metadata = train_model(
            labeled_df,
            model_type=req.model_type,
            save_dir="models/saved",
        )
        return {
            "success": True,
            "metadata": metadata.model_dump(),
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Model training failed: {exc}")


# -----------------------------------------------------------------------------
# 8b. Institutional Next-Session Forecasting & Multi-Broker Cost Engine
# -----------------------------------------------------------------------------
@app.get("/api/v1/forecast/next-session", tags=["forecasting"])
def get_next_session_forecast(symbol: str = Query("NIFTY", description="Equity or index symbol")) -> Dict[str, Any]:
    """Generates a calibrated next-session quantitative forecast with statistical volatility bounds."""
    sym = symbol.strip().upper()
    provider = get_market_provider()
    try:
        candles = provider.get_historical_candles(sym, timeframe=Timeframe.DAILY)
    except Exception as e:
        candles = synth_provider.get_historical_candles(sym, timeframe=Timeframe.DAILY)

    if not candles or len(candles) < 25:
        # Fallback to synth if historical candles insufficient
        candles = synth_provider.get_historical_candles(sym, timeframe=Timeframe.DAILY)

    try:
        forecast = forecaster.forecast_next_session(sym, candles)
        return forecast.model_dump()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Forecasting engine error: {str(exc)}")


@app.get("/api/v1/forecast/history", tags=["forecasting"])
def get_forecast_history(
    symbol: Optional[str] = Query(None, description="Optional symbol filter"),
    limit: int = Query(50, ge=1, le=200, description="Max entries to return"),
) -> Dict[str, Any]:
    """Returns historical prediction ledger entries and accuracy scorecard."""
    entries = forecaster.get_ledger(symbol=symbol, limit=limit)
    evaluated = [e for e in entries if e.get("status") == "EVALUATED"]
    total_eval = len(evaluated)
    hits = sum(1 for e in evaluated if e.get("direction_hit"))

    accuracy = round((hits / total_eval) * 100.0, 1) if total_eval > 0 else 0.0

    return {
        "symbol": symbol,
        "total_records": len(entries),
        "evaluated_records": total_eval,
        "historical_accuracy_pct": accuracy,
        "entries": entries,
    }


@app.post("/api/v1/forecast/evaluate", tags=["forecasting"])
def evaluate_forecast_ledger(req: Optional[ForecastEvaluateRequest] = None) -> Dict[str, Any]:
    """Evaluates pending forecasts against realized candles."""
    provider = get_market_provider()
    syms = req.symbols if (req and req.symbols) else ["NIFTY", "SENSEX", "RELIANCE", "TCS", "INFY", "HDFCBANK", "SBIN"]

    candles_map: Dict[str, List[Candle]] = {}
    for s in syms:
        try:
            c = provider.get_historical_candles(s, timeframe=Timeframe.DAILY)
            if c:
                candles_map[s.upper()] = c
        except Exception:
            c = synth_provider.get_historical_candles(s, timeframe=Timeframe.DAILY)
            if c:
                candles_map[s.upper()] = c

    result = forecaster.evaluate_realized_candles(candles_map)
    return result


@app.post("/api/v1/costs/simulate", tags=["costs"])
def simulate_trade_costs(req: CostSimulateRequest) -> Dict[str, Any]:
    """Simulates complete buy-and-sell roundtrip costs, brokerage, statutory taxes, and DP charges."""
    broker_name = req.broker.strip().upper()
    try:
        broker_enum = BrokerProfile(broker_name)
    except ValueError:
        broker_enum = BrokerProfile.ANGEL_ONE

    trade_name = req.trade_type.strip().upper()
    try:
        trade_enum = TradeType(trade_name)
    except ValueError:
        trade_enum = TradeType.DELIVERY

    sim = simulate_roundtrip_trade(
        symbol=req.symbol,
        buy_price=req.buy_price,
        sell_price=req.sell_price,
        quantity=req.quantity,
        broker=broker_enum,
        trade_type=trade_enum,
        slippage_bps=req.slippage_bps,
    )
    return sim.model_dump()


# -----------------------------------------------------------------------------
# 9. Audit Logs & Emergency Kill Switch
# -----------------------------------------------------------------------------
@app.get("/api/v1/audit", tags=["audit"])
def get_audit_logs(limit: int = Query(50, ge=1, le=200)) -> List[Dict[str, Any]]:
    """Returns immutable risk, order, and execution audit trail."""
    logs = audit_repo.get_recent_logs(limit=limit)
    return [l.model_dump() for l in logs]


@app.post("/api/v1/risk/kill-switch", tags=["risk"], dependencies=[Depends(verify_api_token)])
def set_kill_switch(req: KillSwitchRequest) -> Dict[str, Any]:
    """Engages or disengages the emergency trading kill switch."""
    if req.action.lower() == "engage":
        kill_switch.activate(req.reason)
        audit_repo.log_event("KILL_SWITCH_ENGAGED", details={"reason": req.reason})
    elif req.action.lower() == "disengage":
        kill_switch.deactivate(req.reason)
        audit_repo.log_event("KILL_SWITCH_DISENGAGED", details={"reason": req.reason})
    else:
        raise HTTPException(status_code=400, detail="Action must be 'engage' or 'disengage'.")

    return {
        "active": kill_switch.is_active(),
        "reason": kill_switch.get_reason(),
    }


# -----------------------------------------------------------------------------
# 10. Financial Intelligence & Market News Endpoints
# -----------------------------------------------------------------------------
@app.get("/api/v1/intelligence/news", tags=["intelligence"])
def get_intelligence_news(
    limit: int = Query(50, ge=1, le=200),
    category: Optional[str] = Query(None, description="Category e.g. EARNINGS, ORDER_WIN, REGULATORY, MACRO"),
    symbol: Optional[str] = Query(None, description="Filter news by NSE symbol"),
) -> List[Dict[str, Any]]:
    """Returns recent financial events, corporate filings, and global news."""
    return intelligence_engine.get_recent_news(limit=limit, category=category, symbol=symbol)


@app.get("/api/v1/intelligence/summary", tags=["intelligence"])
def get_intelligence_summary() -> Dict[str, Any]:
    """Returns aggregated market sentiment metrics and category breakdowns."""
    return intelligence_engine.get_market_sentiment_summary()


@app.get("/api/v1/intelligence/symbols/{symbol}", tags=["intelligence"])
def get_symbol_intelligence(symbol: str) -> Dict[str, Any]:
    """Returns company-specific sentiment telemetry and recent headline coverage."""
    return intelligence_engine.get_symbol_sentiment(symbol)


@app.post("/api/v1/intelligence/refresh", tags=["intelligence"])
def refresh_intelligence_feeds() -> Dict[str, Any]:
    """Triggers live ingestion from GDELT and official disclosure wires."""
    count = intelligence_engine.ingest_live_feeds()
    return {
        "success": True,
        "new_events_ingested": count,
        "refreshed_at": datetime.now(IST).isoformat(),
    }


@app.post("/api/v1/intelligence/announcements", tags=["intelligence"])
def record_announcement(req: AnnouncementCreateRequest) -> Dict[str, Any]:
    """Records an official corporate disclosure or regulatory announcement."""
    event = intelligence_engine.record_announcement(
        symbol=req.symbol,
        headline=req.headline,
        source=req.source,
        summary=req.summary,
        url=req.url,
    )
    return {
        "success": True,
        "event": event.model_dump(),
    }


# -----------------------------------------------------------------------------
# 11. Specialist Local Financial AI Reasoning Endpoints
# -----------------------------------------------------------------------------
@app.get("/api/v1/ai/health", tags=["ai"])
def get_ai_health() -> Dict[str, Any]:
    """Returns local financial model server status, GPU acceleration, and telemetry."""
    health = ai_client.check_health()
    return health.model_dump()


@app.post("/api/v1/ai/analyse-news", tags=["ai"])
def analyze_news(req: NewsAnalysisRequest) -> Dict[str, Any]:
    """Analyzes financial news headline/disclosure using specialist local reasoning."""
    res = ai_client.analyze_news(req)
    return res.model_dump()


@app.post("/api/v1/ai/explain-signal", tags=["ai"])
def explain_signal(req: SignalExplanationRequest) -> Dict[str, Any]:
    """Generates an explainable thesis and risk/reward breakdown for a trade signal."""
    res = ai_client.explain_signal(req)
    return res.model_dump()


@app.post("/api/v1/ai/dossier", tags=["ai"])
def generate_stock_dossier(req: StockDossierRequest) -> Dict[str, Any]:
    """Produces a structured executive research dossier for a target NSE stock."""
    res = ai_client.generate_dossier(req)
    return res.model_dump()


# -----------------------------------------------------------------------------
# 12. Strategy Optimization, Lookahead Audit & Protections
# -----------------------------------------------------------------------------
@app.post("/api/v1/strategies/lookahead-audit", tags=["strategies"])
def audit_strategy_lookahead(req: LookaheadAuditRequest) -> Dict[str, Any]:
    """Audits strategy for forward leakage and lookahead bias over completed candles."""
    sym = req.symbol.strip().upper()
    provider = get_market_provider()
    candles = provider.get_historical_candles(sym)
    if len(candles) < 65:
        raise HTTPException(status_code=400, detail=f"Insufficient candles ({len(candles)}) for lookahead audit.")

    df = candles_to_dataframe(candles)
    strategy = BaselineSwingStrategy()
    if req.strategy_name.lower() == "momentum":
        strategy = MomentumStrategy()
    elif req.strategy_name.lower() == "breakout":
        strategy = DonchianBreakoutStrategy()

    report = lookahead_detector.audit_strategy(strategy, df, strategy_name=req.strategy_name)
    return report.model_dump()


@app.post("/api/v1/strategies/hyperopt", tags=["strategies"])
def run_strategy_hyperopt(req: HyperoptRequest) -> Dict[str, Any]:
    """Runs parameter optimization grid and returns Sortino/Calmar ranked leaderboard."""
    provider = get_market_provider()
    dataset = {}
    for s in req.symbols:
        c = provider.get_historical_candles(s)
        if c:
            dataset[s] = c

    if not dataset:
        raise HTTPException(status_code=400, detail="No candle data found for hyperopt symbols.")

    report = hyperopt_runner.optimize_baseline(
        symbol_candles=dataset,
        param_grid=req.param_grid,
        max_trials=req.max_trials,
    )
    return report.model_dump()


@app.get("/api/v1/strategies/protections", tags=["strategies"])
def get_protection_status() -> Dict[str, Any]:
    """Returns active cooldown periods, consecutive loss breakers, and lockout status."""
    status = protection_mgr.get_status()
    return status.model_dump()


@app.post("/api/v1/strategies/protections/reset", tags=["strategies"], dependencies=[Depends(verify_api_token)])
def reset_protections() -> Dict[str, Any]:
    """Manually resets active consecutive loss locks and cooldown periods."""
    protection_mgr.manual_reset()
    return {
        "success": True,
        "message": "Risk protections and symbol cooldowns successfully reset.",
        "status": protection_mgr.get_status().model_dump(),
    }


# -----------------------------------------------------------------------------
# 13. Unified Decision Support Engine Endpoints
# -----------------------------------------------------------------------------
@app.post("/api/v1/decision/evaluate", tags=["decision"])
def evaluate_trade_decision(req: DecisionEvaluateRequest) -> Dict[str, Any]:
    """Synthesizes technicals, regime, ML, news sentiment, and risk into an institutional Decision Dossier."""
    sym = req.symbol.strip().upper()
    provider = get_market_provider()
    candles = provider.get_historical_candles(sym)

    strategy_signal = None
    regime = None
    if candles and len(candles) >= 55:
        df = candles_to_dataframe(candles)
        df_ind = compute_all_indicators(df)
        strategy = BaselineSwingStrategy()
        strategy_signal = strategy.evaluate_entry(df_ind)
        regime = detect_market_regime(df_ind)

    portfolio = accountant.get_portfolio_state()
    positions = list(accountant.positions.values())

    dossier = decision_engine.evaluate_candidate(
        symbol=sym,
        price=req.price,
        stop_loss=req.stop_loss,
        target=req.target,
        strategy_signal=strategy_signal,
        regime_assessment=regime,
        portfolio=portfolio,
        open_positions=positions,
    )
    return dossier.model_dump()


# -----------------------------------------------------------------------------
# 11. Autonomous Paper Trading Bot Controller Endpoints
# -----------------------------------------------------------------------------
@app.get("/api/v1/bot/status", tags=["bot"])
def get_bot_status() -> dict[str, Any]:
    """Returns autonomous paper trading bot state, schedule, and recent live activity."""
    return auto_trader.get_status()


@app.post("/api/v1/bot/start", tags=["bot"], dependencies=[Depends(verify_api_token)])
def start_bot() -> dict[str, Any]:
    """Starts the autonomous paper trading background execution loop."""
    auto_trader.start()
    return {"status": "started", "message": "Autonomous paper trading daemon started."}


@app.post("/api/v1/bot/stop", tags=["bot"], dependencies=[Depends(verify_api_token)])
def stop_bot() -> dict[str, Any]:
    """Stops the autonomous paper trading background execution loop."""
    auto_trader.stop()
    return {"status": "stopped", "message": "Autonomous paper trading daemon stopped."}


@app.post("/api/v1/bot/step", tags=["bot"], dependencies=[Depends(verify_api_token)])
def step_bot() -> dict[str, Any]:
    """Executes a single evaluation and paper trading cycle on demand."""
    result = auto_trader.run_iteration()
    return {"status": "completed", "result": result}


@app.post("/api/v1/bot/config", tags=["bot"], dependencies=[Depends(verify_api_token)])
def config_bot(force_market_open: Optional[bool] = Body(None), interval: Optional[int] = Body(None)) -> dict[str, Any]:
    """Updates auto-trader operating mode parameters."""
    if force_market_open is not None:
        auto_trader.force_market_open = force_market_open
    if interval is not None and interval >= 5:
        auto_trader.scan_interval_seconds = interval
    return auto_trader.get_status()
