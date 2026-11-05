# Changelog

All notable changes to the Indian AI Paper Trading Platform will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.2.0] - 2026-11-05

### Added
- **Multi-Timeframe Candle Resampling Engine (`trader/data/resampler.py`):**
  - Resamples raw minute and daily OHLCV bars into `1m`, `3m`, `5m`, `15m`, `30m`, `1h`, `1d`, `1w` timeframes.
  - Aligned strictly to Indian market open at 09:15:00 IST.
  - Guardrail preventing invalid downsampling of daily candles to intraday.
- **FastAPI Real-Time WebSocket Streaming:**
  - `/api/v1/ws/quotes/{symbol}`: Streams live quote packets and tick updates directly to subscribers.
  - `/api/v1/ws/live`: Streams portfolio equity, feed health, and open positions heartbeats every second.
- **Stock Research Live Tick Aggregation:**
  - Upgraded `StockResearchView.tsx` with dynamic timeframe selector (`1m` to `1w`) and live WebSocket connection.
  - Ticks stream in-place into the active candlestick without full page reloading.
  - Real-time connection beacon, data provenance tag, and last exchange tick timestamp.
- **Stop-Loss Execution Hardening in Paper Daemon:**
  - Resolved false stop-loss exits during active market hours by eliminating historical candle fallback.
  - Enforces actionable quote freshness before evaluating stops or profit targets; pauses safely when feed is stale.
- **Local AI Fallback Transparency:**
  - Standardized `LOCAL_AI_BASE_URL` defaulting to `http://127.0.0.1:11434/v1`.
  - Transparently indicates `STANDBY_HEURISTIC` mode when local model server is offline without fabricating AI metrics.

### Changed
- Expanded `Timeframe` enum in canonical domain models to include `3m`, `30m`, and `1w`.
- Replaced manufactured synthetic bid/ask spreads with clean `None` values.
- Expanded test suite to **129 passing tests** (100% pass rate).
- Updated comprehensive technical documentation suite across 14 documents in `docs/`.

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


## [0.3.0] - 2026-11-05

### Added
- **Bloomberg-Style Financial Intelligence System (`src/trader/intelligence/`)**
  - GDELT 2.0 Doc API ingestion client with macro/India query filtering and rate-limit backoff.
  - Corporate filings and circulars parser for NSE/BSE filings, SEBI regulatory circulars, and RBI monetary policy statements.
  - Domain-specific financial taxonomy and classifier categorizing events into `EARNINGS`, `ORDER_WIN`, `M_AND_A`, `REGULATORY`, `MACRO`, and `GEOPOLITICAL`.
  - Token Jaccard similarity and hash deduplication engine suppressing duplicate wire reports within a 24-hour sliding window.
  - Aggregated sentiment telemetry in $[-1.0, 1.0]$ per NSE instrument with negative impact dampening.
  - SQLite persistence table `financial_events` and repository layer `FinancialEventRepository`.

- **Specialist Local Financial AI Integration (`src/trader/ai/` & `scripts/`)**
  - `LocalFinancialAIClient` connecting to local OpenAI-compatible endpoints (`http://127.0.0.1:11434/v1` or `http://127.0.0.1:8000/v1`) with full acceleration on NVIDIA RTX 5060 (8GB VRAM).
  - Robust deterministic heuristic fallback mode when local LLM server is offline, ensuring 100% platform availability.
  - Pydantic V2 schemas: `NewsAnalysisRequest/Response`, `SignalExplanationRequest/Response`, `StockDossierRequest/Response`, `AIHealthResponse`.
  - Modular prompt templates: `news_prompt.txt` and `signal_prompt.txt`.
  - Operational PowerShell scripts: `setup_financial_model.ps1`, `verify_financial_model.ps1`, `start_financial_model.ps1`, `stop_financial_model.ps1`.

- **Clean-Room Freqtrade Patterns (`src/trader/strategies/`)**
  - Comprehensive architectural and licensing evaluation (`docs/FREQTRADE_INTEGRATION_ASSESSMENT.md`) documenting GPL-3.0 isolation rules and clean-room implementation boundary.
  - `LookaheadBiasDetector` conducting point-in-time incremental candle slice audits ensuring zero future data leakage.
  - `HyperoptOptimizer` searching parameter spaces optimized on Sortino, Calmar, and Profit Factor metrics.
  - `RiskProtectionManager` with consecutive-loss circuit breakers (3 losses = 48h freeze) and post-stop symbol cooldowns.
  - Multi-strategy expansion: `NewsSentimentStrategy` (trend + positive sentiment confirmation) and `RelativeStrengthStrategy` (alpha outperformance vs NIFTY 50).

- **Authoritative Indian Market Data Architecture (`src/trader/providers/`)**
  - `DhanAdapter` for SEBI-registered broker DhanHQ: streaming quotes, 5-depth order books, and daily/minute historical OHLCV with hard assertion against order placement.
  - Extended NSE calendar with Diwali Muhurat trading session handling (18:15-19:15 IST) and dynamic holiday schedule updater.
  - Comprehensive provider evaluation: `docs/INDIAN_MARKET_DATA_PROVIDER_COMPARISON.md`.

- **Institutional Decision Support Engine (`src/trader/decision/`)**
  - `DecisionEngine` synthesizing technical signals, market regimes, ML probability, news sentiment, and risk guardrails into an institutional `DecisionDossier`.

- **22-View React Workstation & Tailwind v4 Integration**
  - Integrated `@tailwindcss/vite` and unified semantic design tokens in `styles.css`.
  - `AutoTraderBotView.tsx`: Autonomous bot controller, live 3-second streaming audit tape, market hours monitor, and execution controls.
  - `OverviewView.tsx`: Embedded real-time Autonomous Bot Controller status banner.
  - `FinancialIntelligenceView.tsx`: Live news tape, sentiment meter, category filter, refresh feeds button.
  - `LocalAiResearchView.tsx`: AI GPU telemetry, news analyzer, trade signal explainer, executive stock dossier.
  - `DecisionSupportView.tsx`: Multi-model confluence score, conviction breakdowns, 1-click simulated buy with human confirmation.
  - `LookaheadAuditView.tsx`: Interactive lookahead bias detector, hyperopt search, protections status and reset.

- **Autonomous Paper Trading Daemon & Launcher Utilities**
  - `AutonomousPaperTradingDaemon` (`src/trader/paper/daemon.py`) for automated market hours monitoring, stop-loss trailing, profit target taking, and alpha paper executions.
  - Windows 1-click desktop shortcut (`create_desktop_shortcut.ps1`) and batch/powershell launchers (`start_platform.bat`, `start_platform.ps1`).

- **Expanded FastAPI REST Endpoints (36 Endpoints)**
  - Autonomous Bot: `GET /api/v1/bot/status`, `POST /api/v1/bot/start`, `POST /api/v1/bot/stop`, `POST /api/v1/bot/step`, `POST /api/v1/bot/config`.
  - Financial AI: `GET /api/v1/ai/health`, `POST /api/v1/ai/analyze-news`, `POST /api/v1/ai/explain-signal`, `POST /api/v1/ai/stock-dossier`.
  - Intelligence: `GET /api/v1/intelligence/feed`, `GET /api/v1/intelligence/sentiment/{symbol}`, `POST /api/v1/intelligence/refresh`.
  - Strategies & Audit: `POST /api/v1/strategies/audit-lookahead`, `POST /api/v1/strategies/hyperopt`, `GET /api/v1/protections/status`, `POST /api/v1/protections/reset`.
  - Decision Support: `POST /api/v1/decision/evaluate`.

### Fixed
- Fixed future candle timestamp rejection in `src/trader/data/synthetic.py::get_trading_days` by anchoring start date to the latest completed trading session when current time is before 15:30 IST.
- Fixed kill switch fail-safe to start strictly in ENGAGED mode when persistence state is missing or corrupted.
- Eliminated all mock price derivations and fabricated quotes: unavailable quotes return `None` with `DataSource.UNAVAILABLE`.
- Enforced strict feed freshness guard rejecting simulated buy orders when market feed is `STALE`, `UNAVAILABLE`, or in `ERROR`.
