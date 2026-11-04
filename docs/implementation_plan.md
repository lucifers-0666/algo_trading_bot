# Technical Implementation Plan: Indian AI Paper Trading Platform

**Spec:** `docs/final_indian_ai_paper_trading_build_spec.md`  
**Execution Environment:** Windows 11 64-bit | Python 3.12 (`.venv`) | SQLite 3 | Streamlit  
**Timezone:** `Asia/Kolkata` (IST)  
**Safety Boundary:** Research & Paper Trading Only — Real Demat Order Routing Prohibited

---

## 1. Global Constraints

- **Python Runtime:** Python 3.12.10 in dedicated `.venv`.
- **Database:** Local SQLite (`data/storage/paper_trader.db`).
- **Initial Capital:** ₹10,000 INR virtual cash.
- **Risk per Trade:** 0.5% (₹50 on ₹10k).
- **Position Limits:** Max 2 simultaneous open positions; max 50% total portfolio exposure; max 25% single-stock exposure.
- **Whole Share Rule:** Integer shares only. If minimum 1 share violates risk or cash constraints, trade must be rejected with logged rationale.
- **Timezone:** All timestamps strictly converted/stored in `Asia/Kolkata`.
- **No Look-Ahead Bias:** Signals evaluated strictly on completed candles ($t$); fills simulated on next open ($t+1$).
- **Fail-Closed:** Missing data, stale feed (>300s), corrupt state, or active kill switch blocks all new entries.

---

## 2. Review Focus & Edge Cases

1. **High-Value Stocks vs Small Capital:** A ₹3,000 stock with 2% stop distance requires ₹60 risk per share (exceeding ₹50 risk budget) and ₹3,000 capital (30% of portfolio, exceeding 25% single-position cap). Sizing engine must cleanly reject without crashing.
2. **Indian Transaction Costs on Small Equity:** Statutory taxes (STT 0.1%, GST 18%, Stamp Duty 0.0015%, Exchange fees) plus flat brokerage (₹20) create significant drag. Backtest must calculate exact net P&L after costs.
3. **Data Gaps & Circuit Halts:** NSE stocks hitting upper/lower circuits (5%, 10%, 20%) cannot be entered or exited at nominal prices. Scanner and backtest must flag circuit states.
4. **Time-Series ML Leakage:** Standard k-fold shuffle leaks future information into past predictions. Train/val/test splits must be strictly chronological with a purge/embargo window.
5. **Kill Switch Persistence:** Kill switch must persist in SQLite/disk file across application restarts and fail closed if unreadable.

---

## 3. Phased Task Breakdown

### Phase 1: Environment Inspection, Project Initialization & Provider Evaluation (COMPLETED)
- Inspect Windows, Python 3.12, GPU/CUDA, CPU, RAM, Git.
- Initialize Git, create `.venv`, install pinned dependencies, configure `.gitignore` and `.env.example`.
- Evaluate TrueData candidate in `docs/provider_comparison.md`.
- Document data policy in `docs/data_policy.md` and regulatory boundaries in `docs/regulatory_checklist.md`.
- Establish project architecture in `docs/architecture.md` and `README.md`.

### Phase 2: Data Architecture & Historical CSV Ingestion (NEXT)
- `src/trader/domain/models.py`: Pydantic models for `Candle`, `Quote`, `Trade`, `Order`, `Position`, `PortfolioState`, `AuditLog`.
- `src/trader/data/normalizer.py`: Normalize various CSV Bhavcopy schemas and date formats to canonical ISO `Asia/Kolkata`.
- `src/trader/data/validation.py`: Validate prices ($P>0$), $H \ge \max(O,C)$, $L \le \min(O,C)$, $V \ge 0$, and timestamp sequence.
- `src/trader/data/synthetic.py`: Synthetic generator producing realistic multi-stock NSE OHLCV series.
- `src/trader/providers/base.py`: Abstract `MarketDataProvider`.
- `src/trader/providers/csv_provider.py`: CSV historical data provider.
- `src/trader/data/freshness.py`: Feed latency and staleness watchdog.
- `src/trader/storage/database.py` & `repositories.py`: SQLite schema and data access layers.
- Tests: `tests/unit/test_data_validation.py`, `tests/unit/test_csv_provider.py`, `tests/unit/test_storage.py`.

### Phase 3: Database & Provider Interface (TrueData Decoupled)
- Decoupled `TrueDataAdapter` in `src/trader/providers/truedata_adapter.py`.
- WebSocket connection skeleton, authentication token refresh, heartbeat ping/pong, and candle aggregator.
- Safe disabled mode when credentials are missing.
- Tests: `tests/unit/test_truedata_adapter.py`.

### Phase 4: Stock Universe & Discovery Engine
- `src/trader/universe/instruments.py`: NSE instrument master and symbol metadata.
- `src/trader/scanner/filters.py` & `ranking.py`: Top gainers/losers, relative volume (RVOL), momentum, volatility, and liquidity filters with explicit rationale output.
- Tests: `tests/unit/test_scanner.py`.

### Phase 5: Technical Indicators & Deterministic Strategy Engine
- `src/trader/features/technical.py`: Vectorized SMA, RSI 14, ATR 14, Bollinger Bands, Volume SMA.
- `src/trader/strategies/baseline.py`: Explainable daily swing trading strategy.
- Tests: `tests/unit/test_indicators.py`, `tests/unit/test_strategy.py`.

### Phase 6: Risk Management & Persistent Kill Switch
- `src/trader/risk/sizing.py`: Position sizing with integer share rounding, cash limits, and risk budget cap.
- `src/trader/risk/checks.py`: Pre-trade checks (max positions, exposure, daily loss, stale data).
- `src/trader/risk/kill_switch.py`: Persistent disk-backed kill switch.
- Tests: `tests/unit/test_risk_management.py`.

### Phase 7: Event-Driven Backtesting Engine
- `src/trader/backtest/engine.py`: Chronological event-driven simulator without look-ahead bias.
- `src/trader/backtest/costs.py`: Indian statutory taxes (STT, GST, Stamp Duty, Exchange fees) and brokerage.
- `src/trader/backtest/metrics.py`: CAGR, Sharpe ratio, Max Drawdown, Win Rate, Profit Factor, Expectancy.
- Tests: `tests/unit/test_backtest.py`.

### Phase 8: Machine Learning Pipeline
- `src/trader/ml/dataset.py`: Leak-free feature extraction.
- `src/trader/ml/labels.py`: Forward return quantiles / binary labels with purging/embargo.
- `src/trader/ml/train.py`: Chronological walk-forward train/val/test splits, Random Forest & Logistic Regression.
- `src/trader/ml/evaluate.py`: Model comparison vs deterministic baseline.
- Tests: `tests/unit/test_ml_pipeline.py`.

### Phase 9: Virtual Paper Trading Engine
- `src/trader/paper/broker.py`: Virtual broker executing orders with simulated fills and slippage.
- `src/trader/paper/accounting.py`: Cash, equity, unrealized/realized P&L, ledger tracking.
- `src/trader/paper/orders.py`: Order state machine (`PENDING`, `FILLED`, `REJECTED`, `CANCELLED`).
- Tests: `tests/unit/test_paper_broker.py`, `tests/unit/test_negative_broker_isolation.py` (proves real broker calls are impossible).

### Phase 10: Interactive Dashboard & Background Jobs
- `src/trader/dashboard/app.py`: Streamlit multi-view laboratory.
- Views: Overview, Scanner, Stock Detail, Strategy Lab, ML Lab, Paper Trading, Performance Analytics, Risk/Audit, Settings.
- Permanent PAPER TRADING banner and freshness indicator.

### Phase 11: Integration Testing, Security Audit & Documentation
- End-to-end integration test (`tests/integration/test_full_system.py`).
- Security audit verifying credential redaction and localhost binding.
- Final documentation and operational runbook.
