# Indian Equity AI Paper Trading & Quantitative Research Platform

An auditable, reproducible, production-grade Python quantitative research and paper-trading platform engineered specifically for Indian Cash Equities (NSE).

> **SAFETY NOTICE:**  
> This platform is **strictly for quantitative research, backtesting, and paper trading**.  
> It does **not** connect to real demat or broker accounts and does **not** route live money orders to any exchange.

---

## 1. System Specifications & Pre-requisites

- **Operating System:** Windows 10/11 (64-bit)
- **Runtime:** Python 3.12 (Dedicated Virtual Environment `.venv`)
- **Database:** SQLite 3 (Zero external database server required)
- **Default Virtual Capital:** ₹10,000 INR
- **Market Hours:** 09:15 to 15:30 IST (`Asia/Kolkata`)

---

## 2. Fast Setup (PowerShell on Windows)

Open PowerShell in the project root (`d:\Algo trading`):

```powershell
# 1. Create Python 3.12 Virtual Environment
& "C:\Users\zaid amreliya\AppData\Local\Programs\Python\Python312\python.exe" -m venv .venv

# 2. Activate Virtual Environment
.\.venv\Scripts\Activate.ps1

# 3. Upgrade pip and install pinned dependencies
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\pip.exe install -r requirements.txt

# 4. Copy environment configuration
Copy-Item .env.example .env

# 5. Verify installation
python -c "import pandas, numpy, sklearn, streamlit; print('All systems operational!')"
```

---

## 3. Command Line Interface (CLI)

The platform provides a CLI for managing data, running backtests, training ML models, and controlling the paper broker:

```powershell
# Validate a historical CSV file
python -m trader.cli validate-data --file data/sample/nifty50_sample.csv

# Run stock screener across universe
python -m trader.cli scan --universe nse_top100

# Execute historical backtest
python -m trader.cli backtest --strategy config/strategy.example.yaml

# Train machine learning baseline model
python -m trader.cli train --config config/ml.yaml

# Evaluate model performance out-of-sample
python -m trader.cli evaluate-model --model-id latest

# Check paper trading portfolio status
python -m trader.cli status

# Manage emergency kill switch
python -m trader.cli kill-switch on
python -m trader.cli kill-switch off
```

---

## 4. Launching the Research Dashboard

Launch the Streamlit interactive trading laboratory:

```powershell
.\.venv\Scripts\streamlit.exe run src/trader/dashboard/app.py --server.port 8501 --server.address 127.0.0.1
```

Access the dashboard locally at `http://127.0.0.1:8501`.

---

## 5. Architectural Modules

- `src/trader/domain/`: Canonical Pydantic schemas (Candle, Quote, Order, Position, Ledger).
- `src/trader/providers/`: Provider abstraction (`MarketDataProvider`, `CSVProvider`, `SyntheticProvider`, `TrueDataAdapter`).
- `src/trader/data/`: Timestamp normalization (`Asia/Kolkata`), data validation, freshness monitoring.
- `src/trader/universe/`: NSE symbol and instrument master management.
- `src/trader/scanner/`: Top gainers/losers, relative volume (RVOL), momentum, volatility, and liquidity screeners.
- `src/trader/features/`: Technical indicators (SMA, RSI, ATR, VWAP, Bollinger Bands, Volume).
- `src/trader/strategies/`: Deterministic daily swing trading baseline engine.
- `src/trader/risk/`: Position sizing, 0.5% risk rule, portfolio exposure caps, persistent kill switch.
- `src/trader/backtest/`: Chronological event-driven simulation with granular Indian transaction costs.
- `src/trader/ml/`: Purged walk-forward ML pipeline, scikit-learn models, leak-free feature pipelines.
- `src/trader/paper/`: Virtual broker, order lifecycle, ledger accounting, portfolio valuation.
- `src/trader/storage/`: SQLite database schemas, connection pooling, and repositories.
- `src/trader/dashboard/`: 9-view Streamlit quantitative research suite.

---

## 6. Running Automated Tests

Run the full pytest suite with coverage:

```powershell
.\.venv\Scripts\pytest.exe -v --cov=src/trader tests/
```

---

## 7. License & Compliance

Strictly for academic, educational, and quantitative paper-trading research. No warranty of profitability is provided or implied. Consult registered financial advisors and regulatory documentation before executing real-money trades.

