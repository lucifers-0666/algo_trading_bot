# Project Status: Indian Equity AI Paper Trading Platform

**Last Updated:** 2026-11-04  
**Current Phase:** Production-Ready Research & Paper-Trading Workstation (Phase 1 through Phase 10 Complete)  
**System State:** **FULLY FUNCTIONAL LOCAL WORKSTATION — STRICTLY PAPER TRADING ONLY**

---

## 1. System Overview

| Metric / Attribute | Value |
| :--- | :--- |
| **Operating System** | Windows 11 Home (64-bit), Build 10.0.26300 |
| **CPU / Hardware** | AMD Ryzen 9 8940HX (16 Cores, 32 Threads), 24GB RAM |
| **GPU / Acceleration** | NVIDIA GeForce RTX 5060 Laptop GPU (8GB VRAM, CUDA 13.1) |
| **Python Runtime** | Python 3.12.10 in dedicated `.venv` (`d:\Algo trading\.venv`) |
| **Execution Mode** | **STRICTLY VIRTUAL PAPER TRADING** (Real demat order routing excluded) |
| **Virtual Starting Capital** | ₹10,000 INR |
| **Database** | SQLite 3 (`data/storage/paper_trader.db`) with WAL Mode & ACID Persistence |
| **Frontend Workstation** | React 19 + TypeScript + Vite across 17 dedicated quantitative views |
| **Backend REST API** | FastAPI running on loopback (`127.0.0.1:8000`) across 22 typed endpoints |
| **Automated Test Suite** | **91 passed / 0 failed / 82% code coverage** |

---

## 2. Phase-by-Phase Progress Tracker

- [x] **Phase 1: Environment Inspection, Project Scaffolding & Provider Evaluation**
  - Inspected Windows environment, Python 3.12, CUDA, disk space, and Git.
  - Comprehensive provider evaluation documented in `docs/provider_comparison.md`.
  - Regulatory boundary documented in `docs/regulatory_checklist.md`, data policy in `docs/data_policy.md`.
  - Config templates: `config/app.example.yaml`, `config/strategy.example.yaml`, `config/risk.example.yaml`.

- [x] **Phase 2: Data Architecture & Historical CSV Ingestion**
  - Canonical Pydantic V2 domain models with `Asia/Kolkata` timezone enforcement.
  - Data validation engine with granular reject reasons.
  - OHLCV normalizer for Bhavcopy & Yahoo schemas.
  - Realistic synthetic market data generator with isolated local `np.random.default_rng(seed)`.
  - Historical CSV provider & `MarketDataProvider` base interface.
  - Feed freshness monitor checking latency limits during NSE market hours (09:15-15:30 IST).
  - SQLite persistence store with WAL mode and dedicated `positions` table with restart recovery.

- [x] **Phase 3 & 4: TrueData Decoupled Adapter & Universe Management**
  - `TrueDataAdapter` providing REST historical queries and WebSocket client.
  - Explicit data provenance labels: `REAL-TIME`, `HISTORICAL`, `SYNTHETIC`, `UNAVAILABLE`.
  - `UniverseManager` managing NSE cash equity instruments, sector classifications, and circuit limit filters.

- [x] **Phase 5: Stock Scanner & Technical Indicators**
  - Vectorized indicator functions: SMA 20/50/200, RSI 14 (Wilder's smoothing), ATR 14, RVOL, Volume SMA.
  - Transparent stock discovery engine (`MarketScannerEngine`) with pre-scan snapshot caching.
  - 8 independent scanners: Top Gainers, Losers, RVOL, Momentum, Trend Strength, Volatility, Liquidity, and Unusual Activity.

- [x] **Phase 6: Deterministic Strategy Engine & Market Regime Detection**
  - `BaselineSwingStrategy`: Trend-pullback swing trading baseline with ATR stop-loss, target, and trend exits.
  - `MomentumStrategy`: Cross-sectional 20-day momentum ranking with RVOL qualification.
  - `DonchianBreakoutStrategy`: 20-day channel breakout with volume expansion filters.
  - `detect_market_regime`: Macro market regime classifier recommending `NO_TRADE` during turbulent consolidations.
  - No look-ahead bias: signals evaluated on bar close ($t$), executed at next bar open ($t+1$).

- [x] **Phase 7: Risk Management & Persistent Kill Switch**
  - Position sizing engine enforcing 2.0% risk budget, integer shares, 25% single-stock cap, and cash limits.
  - Hard pre-trade checks: max 5 open positions, 3.0% daily loss limit calculated from today's starting equity (`day_starting_equity`).
  - Pre-fill atomic revalidation in `VirtualPaperBroker` preventing race conditions.
  - Persistent disk-backed kill switch with fail-closed safety.

- [x] **Phase 8: Chronological Backtesting & Indian Transaction Costs**
  - Event-driven chronological backtest engine with intrabar stop-loss checks, gap-through-stop handling, stop-vs-target collision conservatism, circuit-limit blocks, and explicit end-of-test MTM valuation.
  - Official Indian cash equity delivery statutory cost model: STT (0.1%), NSE Txn (0.00297%), SEBI fee, Stamp duty (0.0015% buy), and GST (18%).
  - Multi-Strategy Comparison Framework (`run_strategy_comparison`) evaluating all strategies side-by-side.

- [x] **Phase 9: Machine Learning Pipeline**
  - Leak-free feature extraction from past bar data only.
  - Future return labeler with strict purge gaps between training and testing windows.
  - Chronological walk-forward splits for Random Forest, Gradient Boosting, and Logistic Regression with `SimpleImputer`.
  - Out-of-sample evaluation: Accuracy, Precision, Recall, F1, ROC-AUC, Brier score, and Precision@K.

- [x] **Phase 10: Virtual Paper Trading & 17-View React Workstation**
  - High-performance, anti-slop React 19 + TypeScript + Vite workstation covering all 17 specification views.
  - Real-time mark-to-market portfolio accounting, simulated order proposals, and one-click execution.
  - Backed by 22 typed FastAPI REST endpoints bound exclusively to `127.0.0.1`.
