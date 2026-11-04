# React Frontend Migration Plan

## Decision

Replace the Streamlit UI with a React + TypeScript + Vite frontend, while keeping the Python quantitative engine and paper broker authoritative. Do not rewrite trading logic in TypeScript.

Keep the existing Streamlit app available during migration until the React application reaches feature parity and passes acceptance tests.

## Target architecture

- `frontend/`: React 19-compatible setup (select and pin current stable versions at implementation time), TypeScript, Vite.
- `src/trader/api/`: FastAPI application, Pydantic response schemas, service layer.
- `src/trader/services/`: application orchestration; dashboard must not instantiate complex engines or directly mutate databases.
- Data access and financial calculations stay in Python.
- Frontend talks only to local FastAPI endpoints.
- SSE or WebSocket delivers bounded, timestamped market/status updates. Browser must not become an authoritative order system.

## Suggested frontend stack

- React + TypeScript + Vite.
- Tailwind CSS with a small token set; use CSS variables for light/dark theming.
- TanStack Query for server state, caching and invalidation.
- Zustand only for local UI state (filters, selected watchlist, layout).
- TradingView Lightweight Charts for candles/volume after checking its current license/terms; otherwise choose a compatible chart library.
- TanStack Table for scanner tables; virtualize large result sets.
- React Router for route structure.
- Zod for validating API payloads at the browser boundary (Pydantic remains backend authority).
- Vitest + React Testing Library; Playwright for browser-level flows.
- Avoid large component frameworks and multiple overlapping state/data libraries.

## Visual direction

Light-first, understated financial research workstation:
- Canvas: warm neutral `#F7F8F6`.
- Surfaces: `#FFFFFF`.
- Primary text: `#202824`.
- Secondary text: `#68736D`.
- Borders: `#E4E9E5`.
- Accent emerald: `#167A55` (positive/selected only).
- Muted red: `#C45B5B` (negative values only).
- Muted amber: `#B47A32` (warnings).
- Avoid gradients, neon colors, oversized cards and ornamental animation.
- Use accessible contrast and never convey P&L state by color alone.

## Page structure

1. Overview: system mode, market session, data provider/freshness, virtual cash/equity, daily P&L and drawdown.
2. Market scanner: top gainers/losers, relative volume, momentum, liquidity and exclusion reasons. Table must be virtualized.
3. Instrument detail: candles, volume, indicators, source and timestamp metadata.
4. Strategy lab: versioned parameters, rules, backtest run comparison.
5. ML lab: dataset dates, leakage safeguards, model metrics, top-K ranking quality and model registry.
6. Backtesting: run configuration, event assumptions, cost breakdown, trade ledger, equity/drawdown curves.
7. Paper terminal: proposed/simulated orders, fills, holdings, cash and audit timeline.
8. Risk & audit: limits, kill switch, rejected trades, data quality and errors.
9. Settings: local provider status/configuration; secrets must never be returned to frontend.

## API surface (initial read-only/status endpoints)

- `GET /api/v1/health`
- `GET /api/v1/status`
- `GET /api/v1/market/session`
- `GET /api/v1/data/health`
- `GET /api/v1/scanner/candidates?category=&limit=&cursor=`
- `GET /api/v1/instruments/{symbol}`
- `GET /api/v1/instruments/{symbol}/candles?interval=&from=&to=`
- `GET /api/v1/portfolio`
- `GET /api/v1/portfolio/positions`
- `GET /api/v1/paper/orders`
- `GET /api/v1/paper/trades`
- `GET /api/v1/models`
- `GET /api/v1/backtests/{run_id}`
- `GET /api/v1/audit`
- `GET /api/v1/stream/status` or documented SSE/WebSocket endpoint.

For state-changing paper actions use explicit paper-only endpoints with strict idempotency and server-side risk checks. Do not create real broker endpoints.

## Performance requirements

- Lazy-load charting and heavy research pages by route.
- Keep initial JS bundle small; inspect Vite bundle reports and set measured budgets.
- Use query caching, stale-time policies, request deduplication and cancellation.
- Virtualize large NSE candidate tables.
- Aggregate/throttle ticks server-side before pushing updates to the browser.
- Do not rerender the entire scanner for every market update.
- Use memoization only when profiling justifies it.
- Use skeleton/loading states and clear stale-data indicators.
- No computation-heavy Python task runs in the HTTP request thread; use a bounded background worker/job table for backtests and training.
- Browser binds to localhost and API CORS is restricted to the local frontend origin.

## Migration stages

1. Add FastAPI health/status/read-only endpoints and API contract tests.
2. Scaffold React/Vite app and design tokens.
3. Implement overview and system status.
4. Implement scanner with pagination/virtualization and explicit timestamps.
5. Implement instrument page and charts using backend-resampled data.
6. Implement ML/backtest results and audit views.
7. Implement paper account/order screens using only existing simulator services.
8. Add accessibility, performance profiling and Playwright acceptance tests.
9. Compare React pages with Streamlit; only deprecate Streamlit after parity and verified acceptance.

Do not migrate UI until API contracts and service boundaries are stable.
