# Changelog

All notable changes to the Indian AI Paper Trading Platform will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-11-04

### Added
- **Phase 1: Environment & Scaffolding**
  - Git repository initialization on `main` branch.
  - Dedicated virtual environment configured with Python 3.12.10.
  - Pinned `pyproject.toml` and `requirements.txt` with pandas, numpy, scikit-learn, pydantic, streamlit, plotly, pytest, websockets.
  - Application configuration templates: `config/app.example.yaml`, `config/strategy.example.yaml`, `config/risk.example.yaml`.
  - Security artifacts: `.gitignore`, `.env.example`.
  - Documentation: `docs/provider_comparison.md`, `docs/data_policy.md`, `docs/regulatory_checklist.md`, `docs/final_indian_ai_paper_trading_build_spec.md`.

- **Phase 2: Data Architecture & Historical CSV Ingestion**
  - Canonical Pydantic V2 domain models: `Candle`, `Quote`, `Instrument`, `Order`, `Trade`, `Position`, `PortfolioState`, `AuditLog`.
  - `Asia/Kolkata` explicit timezone enforcement across all timestamp parsing.
  - Robust OHLCV validation: price positivity, high/low geometry, non-negative volume, future timestamp rejection, abnormal return circuit detection.
  - Multi-schema date and column normalizer supporting NSE Bhavcopy and Yahoo format variants.
  - Synthetic market data generator modeling geometric Brownian motion, volatility regimes, volume surges, and realistic NSE stocks.
  - `MarketDataProvider` abstract interface and concrete `SyntheticDataProvider` & `CSVDataProvider`.
  - Stale feed watchdog enforcing 300s latency limits during NSE market hours (09:15-15:30 IST).
  - High-performance SQLite database schema with WAL mode and repositories for candles, orders, trades, portfolio snapshots, and audit logs.

- **Phase 3 & 4: Live Data Decoupled Adapter & Universe Management**
  - `TrueDataAdapter` providing REST historical queries and WebSocket client skeleton. Defaults safely to `DISABLED` mode without credentials.
  - `UniverseManager` managing NSE cash equity instruments, sector classifications, and circuit limit filters.

- **Phase 5: Stock Scanner & Technical Indicators**
  - Vectorized indicator functions: SMA 20/50/200, RSI 14 (Wilder's smoothing), ATR 14, RVOL, Volume SMA.
  - Transparent stock discovery engine (`MarketScannerEngine`) with 8 independent scanners: Top Gainers, Top Losers, Relative Volume, Momentum, Trend Strength, Volatility, Liquidity, and Unusual Activity.

- **Phase 6: Deterministic Strategy Engine**
  - `BaselineSwingStrategy`: Trend-pullback swing trading baseline with ATR stop-loss, profit target, trend-break exit, and max holding period exit.
  - No look-ahead bias: signals evaluated on bar close ($t$), executed at next bar open ($t+1$).

- **Phase 7: Risk Management & Persistent Kill Switch**
  - Position sizing engine enforcing 0.5% risk budget, integer shares, 25% single-stock cap, and 50% exposure cap.
  - Hard pre-trade checks: max 2 open positions, 1% daily loss limit pause, duplicate order protection.
  - Persistent disk-backed kill switch with fail-closed safety.

- **Phase 8: Chronological Backtesting & Indian Transaction Costs**
  - Event-driven chronological backtest engine (`BacktestEngine`).
  - Exact Indian cash equity delivery transaction cost calculator: Brokerage, STT (0.1%), Exchange fees (0.00325%), SEBI charges (0.0001%), Stamp duty (0.0015% buy), and GST (18%).
  - Exhaustive institutional performance metrics: CAGR, Sharpe, Drawdown, Profit Factor, Expectancy, and Cost Drag.

- **Phase 9: Machine Learning Pipeline**
  - Leak-free feature extraction from past bar data only.
  - Future return labeler with strict purge/embargo gap to prevent time-series overlap leakage.
  - Walk-forward chronological training for Random Forest and Logistic Regression.
  - Out-of-sample evaluation, probability calibration, and candidate ranking.

- **Phase 10: Virtual Paper Trading Engine**
  - `VirtualPaperBroker` simulating order execution with realistic slippage and statutory costs.
  - `PortfolioAccountant` tracking virtual cash balance (₹10,000 initial), positions, realized/unrealized P&L, and account reset.
  - Order state machine (`OrderManager`) managing `PENDING`, `FILLED`, `REJECTED`, `CANCELLED` lifecycles.

- **Phase 11: Interactive Dashboard, CLI & System Verification**
  - Full-featured 14-view Streamlit quantitative dashboard (`app.py`) with permanent PAPER TRADING banner and feed health indicator.
  - Rich CLI tool (`cli.py`) supporting `validate-data`, `scan`, `backtest`, `train`, `status`, and `kill-switch`.
  - Comprehensive unit, integration, and negative security isolation test suite (55 tests, 81% code coverage, 100% pass rate).

## [0.2.0] - 2026-11-04

### Added
- **17-View Quantitative Research Workstation (React 19 + TypeScript + Vite)**
  - Overview Dashboard: Unified executive telemetry, virtual capital mark-to-market, today's P&L, feed latency, active positions gauge, scanner opportunities, and recent orders.
  - Market Scanner: Multi-factor screening across 6 categories (Gainers, Losers, Momentum, Breakouts, RVOL, All), liquid-only filtering, transparent reasoning, and direct navigation to Research Chart or Trading Terminal.
  - Instrument Master: NSE cash equity universe browser, ISIN numbers, lot sizes, tick sizes, sector classification, and market depth snapshots.
  - Stock Research: Interactive multi-pane SVG candlestick chart with SMA 20/50 overlays, volume bars, RSI(14) oscillator, and real-time Market Regime banner (`ALLOW_TRADING`, `REDUCE_SIZE`, `NO_TRADE`).
  - Strategy Laboratory: Interactive parameter tuner (SMA fast/slow, RSI pullback range, ATR stop distance) with rule explainability and execution timeline documentation.
  - ML Research Laboratory: Chronological model trainer (Random Forest, Gradient Boosting, Logistic Regression) with purge gaps, Brier score calibration, Precision@K, and feature importance analysis.
  - Backtesting Laboratory: Chronological event simulation, executive metrics grid (Sharpe, Sortino, Drawdown, Profit Factor, Expectancy), SVG equity curve, official Indian statutory cost audit (STT, NSE Txn, Stamp Duty, GST), and trade-by-trade ledger.
  - Strategy Comparison: Side-by-side comparative matrix evaluating Baseline Swing vs Quantitative Momentum vs Donchian Breakout vs Buy & Hold Benchmark under identical conditions.
  - Model Registry: Versioned catalog of trained ML artifacts with out-of-sample test metrics.
  - Trading Terminal: Simulated paper order entry, pre-trade risk verification, 2% risk budget sizing preview, and one-click execution.
  - Portfolio & Holdings: Active open equity holdings table with live mark-to-market P&L, allocation progress bar, and position close actions.
  - Order History: Filterable audit ledger of all simulated paper orders (PENDING, FILLED, REJECTED) with rejection rationales.
  - Performance Analytics: Cumulative returns, peak drawdown, trade win/loss counts, fee attribution, and equity curve trajectory.
  - Risk Management: Emergency fail-closed Kill Switch controller (Engage / Disengage) and portfolio risk guardrail gauges.
  - Audit Logs: Cryptographically sequenced immutable event stream table with JSON payload inspector.
  - Market Data & Feeds: Data provenance tracking (`REAL-TIME`, `HISTORICAL`, `SYNTHETIC`, `UNAVAILABLE`), feed latency watchdog, market session status, and TrueData credentials configuration.
  - System Settings: Localhost binding verification (`127.0.0.1`), SQLite WAL mode status, and Virtual Paper Account Reset with explicit confirmation modal.

- **FastAPI Typed REST Backend (22 Endpoints)**
  - System: `GET /api/v1/health`, `GET /api/v1/status`.
  - Market & Data: `GET /api/v1/market/session`, `GET /api/v1/data/health`.
  - Scanner: `GET /api/v1/scanner/candidates`.
  - Universe & Candles: `GET /api/v1/instruments`, `GET /api/v1/instruments/{symbol}`, `GET /api/v1/instruments/{symbol}/candles`.
  - Portfolio & Paper Trading: `GET /api/v1/portfolio`, `GET /api/v1/portfolio/positions`, `GET /api/v1/paper/orders`, `POST /api/v1/paper/orders`, `POST /api/v1/paper/execute`, `POST /api/v1/paper/reset`, `GET /api/v1/paper/trades`.
  - Strategies & Backtesting: `GET /api/v1/strategies`, `POST /api/v1/backtests/run`, `GET /api/v1/backtests/comparison`.
  - ML & Models: `GET /api/v1/models`, `POST /api/v1/models/train`.
  - Risk & Audit: `GET /api/v1/audit`, `POST /api/v1/risk/kill-switch`.

- **Quantitative & Execution Correctness**
  - Relational `positions` table in SQLite with restart recovery and atomic order fill persistence.
  - Pre-fill atomic revalidation ensuring no race conditions can bypass portfolio risk limits.
  - Intrabar stop-loss checking, gap-through-stop handling, conservative stop-vs-target collision handling, circuit lock blocking, and explicit end-of-test MTM valuation in backtesting.
  - Revised transaction charges adhering to official NSE Circular NSE/MEM/63897 (0.00297%), STT (0.1%), Stamp duty (0.0015%), GST (18%), and SEBI fees.
  - NSE statutory calendar (09:15-15:30 IST) with statutory holiday schedules for 2024-2026.
  - Vectorized Market Regime Classifier (`detect_market_regime`) recommending `NO_TRADE` during turbulent consolidations.
  - Multi-Strategy Comparison Framework (`run_strategy_comparison`).
  - Purged walk-forward validation for financial ML with calibration curves, Brier score, and Precision@K.

### Fixed
- Daily loss limit now correctly tracks today's starting equity (`day_starting_equity`) rather than the initial ₹10,000 capital, preventing false halts on profitable trading days.
- Isolated local `np.random.default_rng` in synthetic data generator to eliminate global state mutation.
- Resolved NaN feature rejection in Gradient Boosting models by embedding `SimpleImputer(strategy="median")`.
