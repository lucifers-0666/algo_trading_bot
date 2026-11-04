# Northstar: Indian Equity AI Paper Trading Workstation

[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![React 19](https://img.shields.io/badge/react-19-cyan.svg)](https://react.dev/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.135-green.svg)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Tests: 91 Passing](https://img.shields.io/badge/tests-91%20passing-brightgreen.svg)]()
[![Coverage: 82%](https://img.shields.io/badge/coverage-82%25-brightgreen.svg)]()

A quantitative research and paper-trading platform designed specifically for Indian cash equity markets (NSE). The Python backend provides data ingestion, technical indicators, machine-learning pipelines, multiple strategies, event-driven backtesting, and strict risk guardrails. A modern, high-density React 19 workstation provides 17 views for screening, charting, strategy comparison, and simulated order execution.

> **Safety boundary:** Strictly virtual research and simulated paper trading. No demat account integration or live broker order routing is implemented. Zero real-money exposure.

---

## 1. Workstation Architecture (17 Views)

The workstation operates across 5 functional areas:

- **Workspace:**
  1. `Overview`: Unified executive telemetry, virtual capital mark-to-market, today's P&L, feed latency, active positions gauge, scanner opportunities, and recent orders.
  2. `Market Scanner`: Multi-factor screening across 6 categories (Gainers, Losers, Momentum, Breakouts, RVOL, All), liquid-only filtering, transparent inclusion/exclusion reasoning, and direct navigation to Research Chart or Trading Terminal.
  3. `Instrument Master`: Curated NSE cash equity universe browser, ISIN numbers, lot sizes, tick sizes, sector classification, and market depth snapshots.
  4. `Stock Research`: Interactive multi-pane SVG candlestick chart with SMA 20/50 overlays, volume bars, RSI(14) oscillator, and real-time Market Regime banner (`ALLOW_TRADING`, `REDUCE_SIZE`, `NO_TRADE`).
- **Quant Research & ML:**
  5. `Strategy Lab`: Interactive parameter tuner (SMA fast/slow, RSI pullback range, ATR stop distance) with rule explainability and execution timeline documentation.
  6. `ML Research Lab`: Chronological model trainer (Random Forest, Gradient Boosting, Logistic Regression) with purge gaps, Brier score calibration, Precision@K, and feature importance analysis.
  7. `Backtests`: Chronological event simulation, executive metrics grid (Sharpe, Sortino, Drawdown, Profit Factor, Expectancy), SVG equity curve, official Indian statutory cost audit (STT, NSE Txn, Stamp Duty, GST), and trade-by-trade ledger.
  8. `Strategy Comparison`: Side-by-side comparative matrix evaluating Baseline Swing vs Quantitative Momentum vs Donchian Breakout vs Buy & Hold Benchmark under identical conditions.
  9. `Model Registry`: Versioned catalog of trained ML artifacts with out-of-sample test metrics.
- **Simulated Paper Trading:**
  10. `Trading Terminal`: Simulated paper order entry, pre-trade risk verification, 2% risk budget sizing preview, and one-click execution.
  11. `Portfolio & Holdings`: Active open equity holdings table with live mark-to-market P&L, allocation progress bar, and position close actions.
  12. `Order History`: Filterable audit ledger of all simulated paper orders (PENDING, FILLED, REJECTED) with rejection rationales.
  13. `Performance Analytics`: Cumulative returns, peak drawdown, trade win/loss counts, fee attribution, and equity curve trajectory.
- **Risk & Compliance:**
  14. `Risk Management`: Emergency fail-closed Kill Switch controller (Engage / Disengage) and portfolio risk guardrail gauges.
  15. `Audit Logs`: Cryptographically sequenced immutable event stream table with JSON payload inspector.
- **System & Data:**
  16. `Market Data & Feeds`: Data provenance tracking (`REAL-TIME`, `HISTORICAL`, `SYNTHETIC`, `UNAVAILABLE`), feed latency watchdog, market session status, and TrueData credentials configuration.
  17. `System Settings`: Localhost binding verification (`127.0.0.1`), SQLite WAL mode status, and Virtual Paper Account Reset with explicit confirmation modal.

---

## 2. Quick Start Guide

### Prerequisites
- Python 3.12 (in dedicated virtual environment `.venv`)
- Node.js >= 22.12.0 and npm

### Backend Setup & Launch (Windows PowerShell)

```powershell
# 1. Activate Python virtual environment
.\.venv\Scripts\Activate.ps1

# 2. Run automated tests (91 unit & integration tests)
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

## 3. Financial & Execution Correctness Highlights

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

## 4. Documentation Links

- [Project Status](PROJECT_STATUS.md)
- [Known Limitations](KNOWN_LIMITATIONS.md)
- [Changelog](CHANGELOG.md)
- [System Architecture](docs/architecture.md)
- [Provider Comparison](docs/provider_comparison.md)
- [Data Policy](docs/data_policy.md)
- [Regulatory Checklist](docs/regulatory_checklist.md)
