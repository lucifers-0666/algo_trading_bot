# Northstar: Indian Equity AI Paper Trading & Financial Intelligence Workstation

[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![React 19](https://img.shields.io/badge/react-19-cyan.svg)](https://react.dev/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.135-green.svg)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Tests: 129 Passing](https://img.shields.io/badge/tests-129%20passing-brightgreen.svg)]()
[![Coverage: 81%](https://img.shields.io/badge/coverage-81%25-brightgreen.svg)]()
[![Hardware: NVIDIA RTX 5060](https://img.shields.io/badge/GPU-RTX%205060%20(8GB)-76B900.svg)]()

An institutional-grade quantitative research, financial intelligence, and paper-trading workstation designed specifically for Indian cash equity markets (NSE). The Python backend provides data ingestion, technical indicators, machine-learning pipelines, multiple strategies, event-driven backtesting, financial news intelligence, local specialist AI reasoning, an autonomous background paper-trading daemon, and strict risk guardrails. A modern, high-density React 19 workstation provides **22 dedicated quantitative views** for screening, charting, strategy comparison, lookahead audit, intelligence feeds, AI dossiers, and automated simulated order execution.

> **Safety boundary:** Strictly virtual research and simulated paper trading. No demat account integration or live broker order routing is implemented. Zero real-money exposure. All server endpoints are bound exclusively to `127.0.0.1`.

---

## 1. Workstation Architecture (22 Views)

The workstation operates across 5 functional areas:

- **Workspace:**
  1. `Overview`: Unified executive telemetry, virtual capital mark-to-market, today's P&L, feed latency, active positions gauge, scanner opportunities, autonomous bot controller banner, and recent orders.
  2. `Market Scanner`: Multi-factor screening across 6 categories (Gainers, Losers, Momentum, Breakouts, RVOL, All), liquid-only filtering, transparent inclusion/exclusion reasoning, and direct navigation to Research Chart or Trading Terminal.
  3. `Instrument Master`: Curated NSE cash equity universe browser, ISIN numbers, lot sizes, tick sizes, sector classification, and market depth snapshots.
  4. `Stock Research`: Interactive multi-pane SVG candlestick chart with SMA 20/50 overlays, volume bars, RSI(14) oscillator, and real-time Market Regime banner (`ALLOW_TRADING`, `REDUCE_SIZE`, `NO_TRADE`).
  5. `Financial Intelligence`: Bloomberg-style live financial news tape, sector sentiment telemetry, deduplication engine, and category filtering (EARNINGS, ORDER_WIN, M&A, REGULATORY, MACRO, GEOPOLITICAL).
  6. `AI Research Lab`: Local specialist financial AI interface running quantized LLMs on NVIDIA RTX 5060 (8GB VRAM) with GPU telemetry, trade signal explainer, and executive stock dossier generator (with deterministic fallback).
  7. `Decision Support`: Institutional confluence matrix uniting technical signals, market regime, ML confidence, news sentiment, and risk guardrails into a single trade conviction dossier with one-click paper order execution.
- **Quant Research & ML:**
  8. `Strategy Lab`: Interactive parameter tuner (SMA fast/slow, RSI pullback range, ATR stop distance) with rule explainability and execution timeline documentation.
  9. `Lookahead & Hyperopt`: Clean-room point-in-time lookahead bias detector, Bayesian parameter optimizer (Sortino, Calmar, Profit Factor), and Freqtrade-style protection circuit breakers.
  10. `ML Research Lab`: Chronological model trainer (Random Forest, Gradient Boosting, Logistic Regression) with purge gaps, Brier score calibration, Precision@K, and feature importance analysis.
  11. `Backtests`: Chronological event simulation, executive metrics grid (Sharpe, Sortino, Drawdown, Profit Factor, Expectancy), SVG equity curve, official Indian statutory cost audit (STT, NSE Txn, Stamp Duty, GST), and trade-by-trade ledger.
  12. `Strategy Comparison`: Side-by-side comparative matrix evaluating Baseline Swing vs Quantitative Momentum vs Donchian Breakout vs Relative Strength vs News Sentiment vs Buy & Hold Benchmark under identical conditions.
  13. `Model Registry`: Versioned catalog of trained ML artifacts with out-of-sample test metrics.
- **Simulated Paper Trading:**
  14. `Trading Terminal`: Simulated paper order entry, pre-trade risk verification, 2% risk budget sizing preview, and one-click execution.
  15. `Auto-trading Bot`: Autonomous paper trading daemon monitoring the Indian market, scanning alpha setups, managing trailing stops, and executing simulated paper orders.
  16. `Portfolio & Holdings`: Active open equity holdings table with live mark-to-market P&L, allocation progress bar, and position close actions.
  17. `Order History`: Filterable audit ledger of all simulated paper orders (PENDING, FILLED, REJECTED) with rejection rationales.
  18. `Performance Analytics`: Cumulative returns, peak drawdown, trade win/loss counts, fee attribution, and equity curve trajectory.
- **Risk & Compliance:**
  19. `Risk Management`: Emergency fail-closed Kill Switch controller (Engage / Disengage) and portfolio risk guardrail gauges.
  20. `Audit Logs`: Cryptographically sequenced immutable event stream table with JSON payload inspector.
- **System & Data:**
  21. `Market Data & Feeds`: Data provenance tracking (`REAL-TIME`, `HISTORICAL`, `SYNTHETIC`, `UNAVAILABLE`), feed latency watchdog, market session status, and TrueData / DhanHQ credentials configuration.
  22. `System Settings`: Localhost binding verification (`127.0.0.1`), SQLite WAL mode status, and Virtual Paper Account Reset with explicit confirmation modal.

---

## 2. Advanced Intelligence & Quantitative Capabilities

### A. Bloomberg-Style Financial Intelligence System (`src/trader/intelligence/`)
- **GDELT 2.0 Ingestion:** Macroeconomic and geopolitical news crawler filtered for Indian capital markets and Indian corporate entities.
- **Corporate Filings & Circulars:** Structured parser for official exchange announcements (NSE/BSE), SEBI regulatory circulars, and RBI monetary policy decisions.
- **NLP Event Classification:** Domain-specific financial taxonomy tagging events as `EARNINGS`, `ORDER_WIN`, `M_AND_A`, `REGULATORY`, `MACRO`, or `GEOPOLITICAL`.
- **Deduplication Engine:** Token Jaccard similarity and hash clustering suppressing duplicated wire reports within a 24-hour sliding window.
- **Calibrated Sentiment:** Domain-aware sentiment score in $[-1.0, 1.0]$ aggregated per NSE symbol.

### B. Local Specialist Financial AI (`src/trader/ai/` & `scripts/`)
- **Target Hardware:** Optimized for NVIDIA GeForce RTX 5060 Laptop GPU (8GB VRAM) and 24GB system RAM.
- **Model Architecture:** Compatible with quantized financial reasoning models (e.g. DeepSeek-R1-Distill-Qwen-7B, Llama-3-8B-Instruct GGUF Q4_K_M) via local OpenAI-compatible endpoints (`http://127.0.0.1:11434/v1` or `http://127.0.0.1:8000/v1`).
- **Deterministic Heuristic Fallback:** When the local LLM server is offline, the client seamlessly falls back to rigorous quantitative rule-based sentiment scoring and trade explanation, guaranteeing 100% platform uptime.
- **Management Scripts:**
  - `scripts/setup_financial_model.ps1`: Guides local Ollama setup and model pulling.
  - `scripts/verify_financial_model.ps1`: Inspects GPU VRAM and queries test prompts.
  - `scripts/start_financial_model.ps1` & `scripts/stop_financial_model.ps1`: Orchestrates local server processes.

### C. Clean-Room Freqtrade Patterns (`src/trader/strategies/`)
- **Zero Copyleft Contamination:** Independent, clean-room implementation of valuable quantitative concepts without importing or copying GPL-3.0 code (documented in `docs/FREQTRADE_INTEGRATION_ASSESSMENT.md`).
- **Lookahead Bias Detector (`lookahead_detector.py`):** Point-in-time incremental candle slice simulation asserting that signals generated at bar $t$ are mathematically invariant to future data bars $t+1 \dots T$.
- **Hyperopt Parameter Optimizer (`hyperopt.py`):** Exhaustive and random search optimizer tuning indicators across Sortino ratio, Calmar ratio, and Profit Factor metrics.
- **Protection Circuit Breakers (`protections.py`):**
  - `ConsecutiveLossesProtection`: Automatically freezes new buy signals for 48 hours after 3 consecutive realized losses.
  - `SymbolCooldownProtection`: Enforces a mandatory cooldown period (e.g., 5 trading bars) on a specific symbol following a stop-loss exit.

### D. Authoritative Indian Market Data Architecture (`src/trader/providers/`)
- **DhanHQ Adapter (`dhan_adapter.py`):** Certified integration with SEBI-registered broker DhanHQ for live quote streaming, 5-depth market order books, and daily/minute historical OHLCV. Strictly isolated from trade execution.
- **TrueData Adapter (`truedata_adapter.py`):** Real-time WebSocket and historical REST feed client for authorized TrueData equity subscribers.
- **NSE Trading Calendar (`calendar.py`):** Complete holiday schedules, Muhurat trading session handling (Diwali 18:15-19:15 IST), and dynamic calendar updates.

---

## 3. Quick Start Guide

### Prerequisites
- Python 3.12 (in dedicated virtual environment `.venv`)
- Node.js >= 22.12.0 and npm
- Windows 11 with PowerShell 5.1 / 7+
- (Optional for AI) NVIDIA RTX GPU with CUDA 12+ and Ollama

### Backend Setup & Launch (Windows PowerShell)

```powershell
# 1. Activate Python virtual environment
.\.venv\Scripts\Activate.ps1

# 2. Run automated tests (118 unit & integration tests)
pytest tests/ -v

# 3. Launch FastAPI backend on localhost
uvicorn trader.api.app:app --host 127.0.0.1 --port 8000
```

- API Base URL: `http://127.0.0.1:8000`
- Interactive OpenAPI Docs: `http://127.0.0.1:8000/api/docs`
- Health check: `http://127.0.0.1:8000/api/v1/health`

### Frontend Workstation Launch

In a separate terminal:

```powershell
# 1. Navigate to frontend directory
cd frontend

# 2. Install dependencies (if not already installed)
npm install

# 3. Build & verify production bundle
npm run build

# 4. Start local development server (proxies /api to 127.0.0.1:8000)
npm run dev
```

- Workstation URL: `http://127.0.0.1:5173`

---

## 4. Financial & Execution Correctness Highlights

- **Statutory Delivery Taxes:** Implements official rates per SEBI & NSE circulars:
  - Securities Transaction Tax (STT): 0.1% on Buy and Sell turnover.
  - NSE Transaction Charges: 0.00297% (revised Oct 2024).
  - SEBI Turnover Charges: ₹10 per crore (0.0001%).
  - Stamp Duty: 0.0015% on Buy turnover.
  - GST: 18% on (Brokerage + Exchange charges).
- **Execution Timeline:** Signals evaluated strictly on bar close ($t$), orders executed at next session open ($t+1$).
- **Realistic Backtesting:** Intrabar stop-loss execution (`low <= stop`), gap-through-stop fills at market open, conservative collision handling (assumes stop hit first when both touched), and circuit lock blocking.
- **Relational Persistence:** SQLite `positions` table with ACID transaction recovery and pre-fill atomic revalidation.
- **Machine Learning Integrity:** Chronological walk-forward splits with purge gaps between train and test windows to prevent overlapping return leakage.

---

## 5. Documentation Links

- [Project Status](PROJECT_STATUS.md)
- [Known Limitations](KNOWN_LIMITATIONS.md)
- [Changelog](CHANGELOG.md)
- [Freqtrade Architecture & Clean-Room Assessment](docs/FREQTRADE_INTEGRATION_ASSESSMENT.md)
- [Indian Market Data Provider Comparison](docs/INDIAN_MARKET_DATA_PROVIDER_COMPARISON.md)
- [System Architecture](docs/architecture.md)
- [Data Policy](docs/data_policy.md)
- [Regulatory Checklist](docs/regulatory_checklist.md)
