# Indian Equity AI Paper Trader

Quantitative research and paper-trading platform for Indian cash equities (initially NSE). The Python engine owns market-data processing, indicators, strategies, model inference, risk checks, backtesting and virtual-account accounting. A separate React application provides the dashboard.

> **Safety boundary:** Research, backtesting and paper trading only. No real demat account integration or live broker order routing is implemented.

## Current implementation status

This repository contains a Python research/paper-trading prototype, a React dashboard scaffold and a minimal local FastAPI health API. The React scanner, model lab, backtest and portfolio pages are not yet connected to tested backend read models. The TrueData adapter is a development placeholder and must not be treated as a verified live connection.

See:
- [Project status](PROJECT_STATUS.md)
- [Known limitations](KNOWN_LIMITATIONS.md)
- [Repository audit](docs/REPOSITORY_AUDIT_2026-11-04.md)
- [React migration plan](docs/FRONTEND_REACT_MIGRATION_PLAN.md)
- [Quantitative reliability roadmap](docs/QUANT_RELIABILITY_ROADMAP.md)
- [Provider comparison](docs/provider_comparison.md)

## Backend setup (Windows PowerShell)

Requirements: Python 3.12.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev]"
Copy-Item .env.example .env
```

Run tests:

```powershell
pytest tests/ -q
```

Run the existing CLI:

```powershell
python -m trader.cli --help
python -m trader.cli status
python -m trader.cli kill-switch status
```

Run the local API (health/status only at this stage):

```powershell
uvicorn trader.api.app:app --host 127.0.0.1 --port 8000
```

Health endpoint: `http://127.0.0.1:8000/api/v1/health`  
API documentation: `http://127.0.0.1:8000/api/docs`

## React frontend setup

Requirements: Node.js >= 22.12.0 and npm.

```powershell
cd frontend
npm install
Copy-Item .env.example .env
npm run dev
```

Open `http://127.0.0.1:5173`. The Vite development server proxies `/api` to the local FastAPI server on port 8000.

Production build and type-check:

```powershell
npm run typecheck
npm run build
```

## Data and model safety

- Synthetic data is for software tests only; never treat it as real market evidence.
- No provider credentials belong in source control or `VITE_*` frontend variables.
- The dashboard must distinguish real-time, delayed, historical, cached and synthetic datasets.
- A reachable API does not mean the market-data provider is connected.
- Strategy metrics must come from an event-driven portfolio simulation after costs and realistic execution assumptions.
- Model scores are research outputs, not certainty or guaranteed returns.

## Frontend design and architecture

React + TypeScript + Vite. The initial UI scaffold uses a light-first neutral palette with restrained emerald and muted red, minimal visual decoration and a responsive sidebar. Browser code must never be the authoritative calculator for P&L, order sizing or risk validation.

See [React migration plan](docs/FRONTEND_REACT_MIGRATION_PLAN.md) for staged API and page integration.
