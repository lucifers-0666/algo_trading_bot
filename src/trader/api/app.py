"""Local FastAPI REST API for the Indian AI Paper Trading Platform.
Exposes typed, validated endpoints for Market Data, Scanners, Strategy Lab,
Backtesting, ML Registry, Risk Management, and Virtual Paper Trading.
STRICTLY BOUND TO LOCALHOST (127.0.0.1) AND STRICTLY VIRTUAL PAPER TRADING.
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional
import json
import pandas as pd

from fastapi import FastAPI, HTTPException, Query, Body
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
from trader.scanner.ranking import MarketScannerEngine
from trader.universe.instruments import UniverseManager
from trader.features.technical import candles_to_dataframe, compute_all_indicators
from trader.strategies.baseline import BaselineSwingStrategy
from trader.strategies.momentum import MomentumStrategy
from trader.strategies.breakout import DonchianBreakoutStrategy
from trader.strategies.regime import detect_market_regime
from trader.backtest.engine import BacktestEngine
from trader.backtest.comparison import run_strategy_comparison
from trader.ml.dataset import extract_features
from trader.ml.labels import generate_forward_labels
from trader.ml.train import train_model
from trader.api.schemas import (
    OrderProposalRequest,
    OrderExecuteRequest,
    ResetAccountRequest,
    KillSwitchRequest,
    BacktestRunRequest,
    ModelTrainRequest,
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
    allow_headers=["Accept", "Content-Type"],
)

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

# Providers
csv_path = Path("data/sample")
csv_provider = CSVDataProvider(data_path=csv_path) if csv_path.exists() else None
synth_provider = SyntheticDataProvider(seed=42)

def get_market_provider():
    if csv_provider and len(csv_provider.get_available_symbols()) > 0:
        return csv_provider
    return synth_provider

scanner_engine = MarketScannerEngine(provider=get_market_provider())
universe_mgr = UniverseManager()


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
    return {
        "mode": "paper",
        "real_order_routing_enabled": False,
        "market_data_provider": "not_connected",
        "market_data_status": "not_configured",
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
    """Monitors market data latency, source provenance, and freshness guards."""
    provider = get_market_provider()
    last_tick_time = getattr(provider, "_last_update", datetime.now(IST))
    freshness = evaluate_feed_freshness(last_tick_time)

    return {
        "data_source_label": provider.source_type.value.upper(),
        "feed_status": freshness.status.value,
        "is_actionable": freshness.is_actionable,
        "latency_seconds": round(freshness.latency_seconds, 2),
        "message": freshness.message,
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


@app.get("/api/v1/instruments/{symbol}/candles", tags=["instruments"])
def get_instrument_candles(
    symbol: str,
    timeframe: str = Query("1d", description="Timeframe e.g. 1d"),
    limit: int = Query(100, ge=10, le=500),
) -> Dict[str, Any]:
    """Returns historical candles decorated with technical indicators and regime assessment."""
    sym = symbol.strip().upper()
    provider = get_market_provider()
    candles = provider.get_historical_candles(sym)

    if not candles:
        raise HTTPException(status_code=404, detail=f"No historical candles available for {sym}.")

    candles = candles[-limit:]
    df = candles_to_dataframe(candles)
    df_ind = compute_all_indicators(df)
    regime = detect_market_regime(df_ind)

    # Format candle list with indicators
    candle_records = []
    for _, row in df_ind.iterrows():
        candle_records.append({
            "timestamp": row["timestamp"].strftime("%Y-%m-%d"),
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


@app.post("/api/v1/paper/execute", tags=["paper_trading"])
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


@app.post("/api/v1/paper/reset", tags=["paper_trading"])
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
# 9. Audit Logs & Emergency Kill Switch
# -----------------------------------------------------------------------------
@app.get("/api/v1/audit", tags=["audit"])
def get_audit_logs(limit: int = Query(50, ge=1, le=200)) -> List[Dict[str, Any]]:
    """Returns immutable risk, order, and execution audit trail."""
    logs = audit_repo.get_recent_logs(limit=limit)
    return [l.model_dump() for l in logs]


@app.post("/api/v1/risk/kill-switch", tags=["risk"])
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
