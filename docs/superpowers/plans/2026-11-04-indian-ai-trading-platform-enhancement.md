# Indian Equity AI Algorithmic Trading Platform Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform the Indian equity AI paper-trading platform into an institutional-grade, statistically defensible swing-trading research and paper-trading workstation with strict execution timing, persistent positions, verifiable statutory costs, multi-strategy backtesting, walk-forward ML, a typed FastAPI backend, and a modern 17-view React dashboard.

**Architecture:** A layered Python backend featuring event-driven backtesting, transactional SQLite persistence, deterministic quantitative indicators, and walk-forward ML with label purging, exposed via a typed, localhost-bound FastAPI service to a high-density, tabbed React + TypeScript + Vite workstation.

**Tech Stack:** Python 3.12, FastAPI, Pydantic v2, SQLite (WAL mode), scikit-learn, pandas, numpy, React 19, TypeScript 5.9, Vite 8, TanStack Query, Lucide React, Pytest.

**Spec:** `docs/final_indian_ai_paper_trading_build_spec.md` & Master Engineering Prompt.

## Global Constraints

- Execution mode: **Strictly Paper Trading**. No real broker order routing, demat integration, or real money.
- Initial virtual capital: ₹10,000 INR.
- Localhost binding only: `127.0.0.1` (FastAPI and Vite).
- Fail-closed security: Emergency kill switch, missing market data, or invalid risk state defaults to blocking new orders.
- No look-ahead bias: Signal generated strictly at candle $t$ close; execution occurs at $t+1$ open or subsequent eligible tick.
- No overlapping label leakage: Walk-forward splits must include purge gaps and embargo periods.
- Design tokens: Background `#F7F8F6`, Surface `#FFFFFF`, Primary text `#202824`, Borders `#E4E9E5`, Emerald `#167A55`, Negative `#C45B5B`, Warning `#B47A32`.
- Git rules: Continue on `review/react-frontend-quant-reliability`, small logical commits, no force-push, do not overwrite `main`.

## Review Focus

1. **Intrabar stop-loss collision:** When both stop-loss and target are touched in a single bar, execution must conservatively assume stop-loss was hit first.
2. **Gap-through-stop execution:** When a session opens below the nominal stop-loss, the exit price must be the open price, not the unachievable stop price.
3. **Daily loss calculation basis:** Daily loss limit must calculate drawdown relative to today's starting equity (`day_starting_equity`), not original starting capital.
4. **Position restart persistence:** Open positions must be saved in a relational `positions` table and restored atomically across application restarts.
5. **Double-counting slippage:** Cost models and performance ledgers must track slippage transparently without subtracting it twice from gross P&L.

---

## Tasks

### Task 1: Persistent Positions & Transactional Accounting (Phase 1)
- [ ] Add `positions` table DDL to `src/trader/storage/database.py`.
- [ ] Create `PositionRepository` in `src/trader/storage/repositories.py` with CRUD, transaction handling, and reconciliation.
- [ ] Update `PortfolioAccountant` in `src/trader/paper/accounting.py` to restore open positions on initialization and persist them upon fill/reset.
- [ ] Update `PortfolioState` in `src/trader/domain/models.py` to include `day_starting_equity` and `last_day_reset`.
- [ ] Write unit and integration tests in `tests/unit/test_position_persistence.py` verifying restart survival, oversell rejection, and cash balance reconciliation.
- [ ] Run pytest, verify all tests pass, and commit.

### Task 2: Risk Management Refinements & Fail-Closed Guardrails (Phase 1)
- [ ] Fix daily loss limit in `src/trader/risk/checks.py` to compare against `portfolio.day_starting_equity`.
- [ ] Add pre-fill revalidation in `src/trader/paper/broker.py` to ensure risk checks are re-verified right before simulated trade fill.
- [ ] Ensure user-supplied quantity can only reduce approved size, never exceed it.
- [ ] Add test cases in `tests/unit/test_risk_management.py` verifying daily loss with varied starting equities.
- [ ] Run pytest, verify all tests pass, and commit.

### Task 3: Realistic Backtesting Execution & Intrabar Gap Handling (Phase 1)
- [ ] Enhance `BacktestEngine` in `src/trader/backtest/engine.py`:
  - Intrabar stop-loss check (`low <= stop_loss`).
  - Gap-through-stop execution: `if open < stop_loss: exit_price = open`.
  - Collision handling: if both stop and target touched in the same bar, execute stop-loss first.
  - Circuit limit handling (untradeable bar when high == low == close or zero volume).
  - Explicit end-of-test mark-to-market open position accounting.
- [ ] Add unit tests in `tests/unit/test_backtest_execution.py` covering gap-down exits, collision conservatism, and circuit limit blocking.
- [ ] Run pytest, verify all tests pass, and commit.

### Task 4: Complete Indian Equity Delivery Cost Model (Phase 1)
- [ ] Update `src/trader/backtest/costs.py`:
  - Configurable broker fee models: Flat ₹20 (default), Zero-brokerage delivery, Percentage fee.
  - Statutory rates: STT 0.1%, NSE Txn charges 0.00297%, SEBI turnover 0.0001%, Stamp duty 0.0015% (BUY only), GST 18%.
  - Separate statutory costs from broker fees in `TradeCostBreakdown`.
  - Ensure slippage is reported cleanly without double-counting against effective prices.
- [ ] Add tests in `tests/unit/test_transaction_costs_indian_equities.py` for ₹500, ₹1,000, ₹2,000, ₹5,000, and ₹50,000 transactions.
- [ ] Run pytest, verify all tests pass, and commit.

### Task 5: Market Data Infrastructure & NSE Trading Calendar (Phase 2)
- [ ] Implement `src/trader/data/calendar.py` with NSE trading hours (09:15-15:30 IST), public holidays, and weekend detection.
- [ ] Update `src/trader/data/freshness.py` to use `NSETradingCalendar`.
- [ ] Update `src/trader/data/synthetic.py` to use deterministic local NumPy random generators (`np.random.default_rng(seed)`).
- [ ] Harden `TrueDataLiveAdapter` in `src/trader/providers/truedata_adapter.py`: documented endpoints, explicit session lifecycle, heartbeat, backoff reconnection, latency monitoring, and strict `DataSource` labels (`REAL-TIME`, `DELAYED`, `HISTORICAL`, `CACHED`, `SYNTHETIC`, `UNAVAILABLE`).
- [ ] Add tests in `tests/unit/test_calendar_and_providers.py`.
- [ ] Run pytest, verify all tests pass, and commit.

### Task 6: Multi-Strategy Quantitative Engine & Feature Snapshot Cache (Phase 3)
- [ ] Implement snapshot caching in `src/trader/scanner/engine.py` to eliminate redundant indicator calculations across scans.
- [ ] Implement Strategy 2: Momentum & Relative Strength (`src/trader/strategies/momentum.py`).
- [ ] Implement Strategy 3: Donchian Breakout (`src/trader/strategies/breakout.py`).
- [ ] Implement Strategy 4: Market Regime Filter (`src/trader/strategies/regime.py`) with support for NO TRADE signals.
- [ ] Implement Strategy Comparison Engine (`src/trader/backtest/comparison.py`) running identical datasets and costs across all strategies and benchmarks.
- [ ] Add tests in `tests/unit/test_multi_strategies.py`.
- [ ] Run pytest, verify all tests pass, and commit.

### Task 7: Machine Learning Walk-Forward Validation & Model Registry (Phase 3)
- [ ] Update `src/trader/ml/labels.py` with chronological expanding/rolling walk-forward splits, purge gaps, and embargo periods.
- [ ] Update `src/trader/ml/train.py` to support Logistic Regression, Random Forest, and Gradient Boosting, rejecting unknown models.
- [ ] Update `src/trader/ml/evaluate.py` to compute Precision@K, PR-AUC, calibration error, and show explicit N/A reasons instead of arbitrary defaults.
- [ ] Ensure ML-assisted strategy routes signals into the event-driven backtesting engine with realistic costs.
- [ ] Add tests in `tests/unit/test_ml_walk_forward.py`.
- [ ] Run pytest, verify all tests pass, and commit.

### Task 8: Comprehensive FastAPI REST API Backend (Phase 4)
- [ ] Implement structured schemas in `src/trader/schemas/` for all market, scanner, portfolio, backtest, and ML models.
- [ ] Expand `src/trader/api/app.py` with typed endpoints:
  - `GET /api/v1/health`, `GET /api/v1/status`
  - `GET /api/v1/market/session`, `GET /api/v1/data/health`
  - `GET /api/v1/scanner/candidates`
  - `GET /api/v1/instruments`, `GET /api/v1/instruments/{symbol}`
  - `GET /api/v1/instruments/{symbol}/candles`
  - `GET /api/v1/portfolio`, `GET /api/v1/portfolio/positions`
  - `GET /api/v1/paper/orders`, `POST /api/v1/paper/orders` (simulated order proposal)
  - `POST /api/v1/paper/execute` (simulated order execution)
  - `POST /api/v1/paper/reset` (virtual reset with confirmation)
  - `GET /api/v1/paper/trades`
  - `GET /api/v1/strategies`, `POST /api/v1/backtests/run`, `GET /api/v1/backtests`
  - `GET /api/v1/models`, `POST /api/v1/models/train`
  - `GET /api/v1/audit`
  - `POST /api/v1/risk/kill-switch` (engage / disengage)
- [ ] Add API integration tests in `tests/unit/test_api_endpoints.py`.
- [ ] Run pytest, verify all tests pass, and commit.

### Task 9: Professional 17-View React Quantitative Workstation (Phase 4)
- [ ] Set up clean routing/tabbed navigation for the 17 workstation views in `frontend/src/`:
  1. Overview Dashboard
  2. Market Scanner
  3. Instrument Details
  4. Stock Research
  5. Strategy Laboratory
  6. ML Research Laboratory
  7. Backtesting Laboratory
  8. Strategy Comparison
  9. Paper Trading Terminal
  10. Portfolio and Holdings
  11. Order History
  12. Performance Analytics
  13. Risk Management
  14. Audit Logs
  15. Market Data & Provider Settings
  16. Model Registry
  17. System Configuration
- [ ] Incorporate high-density, light-first institutional aesthetic using defined design tokens (`#F7F8F6`, `#FFFFFF`, `#202824`, `#167A55`, `#C45B5B`, `#B47A32`).
- [ ] Implement responsive data tables with tabular numerals, status badges, and interactive controls for simulated paper orders.
- [ ] Implement lightweight canvas/SVG candlestick and indicator charting in Stock Research and Backtesting views.
- [ ] Verify `npm run build` and `tsc -b` pass cleanly.
- [ ] Commit frontend updates.

### Task 10: Full Regression Testing, Security Verification & Documentation (Phase 5)
- [ ] Run complete Python pytest suite with coverage (`pytest --cov=trader`).
- [ ] Verify negative broker isolation tests (confirm zero live demat endpoints).
- [ ] Verify frontend build and run frontend component/unit checks.
- [ ] Update `README.md`, `PROJECT_STATUS.md`, `KNOWN_LIMITATIONS.md`, `CHANGELOG.md`, and `docs/architecture.md`.
- [ ] Commit and push all changes to `origin/review/react-frontend-quant-reliability`.

