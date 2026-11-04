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
