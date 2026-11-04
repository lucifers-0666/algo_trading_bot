# Repository Audit — 4 November 2026

Repository: [lucifers-0666/algo_trading_bot](https://github.com/lucifers-0666/algo_trading_bot)

Reviewed default branch: `main`  
Reviewed head at audit: `d072aef317af01cf966e06279cffe1493a4b3142`  
Review branch: `review/react-frontend-quant-reliability`

## Executive summary

The repository is a substantial Python research/paper-trading prototype. It is not yet a verified live-data paper-trading platform and it is not production-ready. The presence of modules and a project status claim of 55 passing tests does not establish that the actual behavior is correct. This review inspected GitHub source files and documentation; tests were not executed in this remote review environment.

The application currently uses a Streamlit dashboard, not React. The recommended UI direction is a React + TypeScript + Vite single-page application with a thin FastAPI backend. Keep all quantitative calculations, market data adapters, risk controls, backtesting and virtual accounting in Python. Do not port the trading engine to JavaScript.

## Strong existing foundations

- Python package layout under `src/trader`.
- Separation of provider abstraction, scanner, strategy, risk, backtest, ML and virtual broker.
- SQLite persistence and Pydantic domain models.
- CSV and synthetic data providers.
- A TrueData adapter placeholder, with credentials optional.
- Basic risk controls and persistent kill-switch module.
- Unit and integration test folders.
- Data-policy, provider-comparison, architecture and regulatory documentation.
- Explicit paper-only intent and no intended live order routing.

## Critical findings from source inspection

### P0 — ML evaluation is not a valid trading simulation

`src/trader/ml/evaluate.py` applies a model probability threshold to every row and compounds each row's overlapping forward return with `np.prod(1 + forward_return)`. If labels use a 5-session horizon, adjacent row returns overlap heavily. This implicitly assumes simultaneous/overlapping positions and reinvestment in a way that the code does not model. It omits position sizing, entry/exit execution, costs, risk limits, cash constraints, and portfolio accounting. The resulting value must not be described as a strategy return or profitability evidence.

**Required fix:** Use the same event-driven portfolio simulator for ML signals as for deterministic strategy signals. Define a non-overlapping or explicitly capacity-limited position policy. Include fees, slippage, order timing, stops, cash, exposure and drawdown.

### P0 — Backtest exit fill timing can be optimistic

`src/trader/backtest/engine.py` evaluates exit conditions on the current bar's OHLC/close and then adds proceeds to cash immediately on that same bar. For a trend-break exit that uses the close, the signal is only known after the close; filling at that exact close is not generally justified. Stop/target collisions and gap-through-stop behavior also need explicit conservative rules. Pending entry orders do use a later bar, but entry and exit execution conventions are inconsistent.

**Required fix:** Define an explicit event timeline: bar completes -> signal generated -> order eligible on next bar/session. Stop orders can trigger within a bar only under a documented intrabar model, conservative gap handling and adverse-price assumptions. Add hand-calculated fixtures.

### P0 — TrueData adapter is not a working live-data transport

`src/trader/providers/truedata_adapter.py` currently:
- uses a hardcoded historical URL and request parameter names without binding them to the provider's current, verified documentation;
- sends `self._session_token` while no shown code obtains/authenticates that token;
- returns empty records on HTTP failures, hiding the difference between “no data” and “provider failure”;
- has no implemented WebSocket connect/subscribe/reconnect/event loop;
- `get_latest_quote` raises `NotImplementedError` even when credentials are present;
- parses a simplified illustrative JSON payload and stamps it with local receipt time instead of preserving exchange/provider event time;
- fabricates bid/ask values when absent, which can create false market depth information.

**Required fix:** Do not activate this adapter. Verify official current provider docs and subscription permissions first. Implement using their supported SDK/protocol, preserve exchange timestamps and raw provenance, never fabricate bid/ask, expose typed provider errors, handle authentication, heartbeats, reconnects, subscriptions, rate limits and stale-feed state. Add recorded sanitized fixtures from documentation or provider-authorized test data.

### P0 — Model training/evaluation contracts are too weak

`src/trader/ml/train.py` treats any unrecognized model type as Random Forest. It computes ROC AUC fallback as 0.50 when evaluation is invalid, which can misrepresent a one-class or invalid test set as a neutral model result. The split is a single holdout despite comments and docs describing walk-forward training. Feature columns and positive-class ordering are not rigorously validated.

**Required fix:** Reject unsupported model names. Handle missing classes and invalid metric cases as unavailable/NaN with explicit reasons, not fabricated 0.50. Validate feature schema, class labels, sorted per-symbol dates, duplicate rows and class balance. Implement rolling/expanding walk-forward folds with purging based on actual label intervals; preserve final untouched holdout.

### P1 — ML label and universe design need stronger statistical controls

`src/trader/ml/labels.py` creates binary labels from close-to-close forward return only. It does not model whether a stop/target is hit during the holding period and has no neutral class. The purge gap is row-based; across multi-symbol pooled datasets this may not represent the actual calendar overlap for every symbol.

**Required fix:** Store label start/end timestamps or outcome intervals; purge overlapping intervals by time/symbol. Consider triple-barrier labels as a research option, with strictly future path data only in labels. Define realistic labels after estimated costs. Build sector/market context only with point-in-time data.

### P1 — Synthetic data generator has global random-state side effects

`src/trader/data/synthetic.py` uses `np.random.seed`, changing global NumPy RNG state. Its generated “realistic” data is synthetic and cannot support model profitability claims. Trading dates omit exchange holidays and generated prices are not market observations.

**Required fix:** Use a local `numpy.random.Generator`, explicitly label all synthetic records, seed per symbol, and never mix synthetic and real samples in the same training/evaluation claim. Use an exchange calendar for actual sessions.

### P1 — Market scanner is not scalable for a broad NSE universe

`src/trader/scanner/ranking.py` fetches historical candles and recomputes indicators separately for each symbol and for each scan method. Defaults are a hardcoded ten-stock list. This causes repeated I/O/computation and cannot efficiently scan the licensed broad universe.

**Required fix:** Build a single normalized snapshot for a scan run, cache features by symbol/timeframe/data version, fetch in provider-permitted batches, parallelize only within rate limits, and separate full-universe EOD scan from intraday subscription rotation. Add latency/throughput benchmarks.

### P1 — Dashboard architecture is not the requested React frontend

`src/trader/dashboard/app.py` is a large Streamlit script containing page routing, data construction, backend orchestration and UI in one module. There are no React package files, Vite config, TypeScript configuration, component tree, API client or frontend tests in the repository tree.

**Required fix:** Build a separate `frontend/` React + TypeScript + Vite application. Python remains authoritative for financial calculations. Expose read-only and paper-only APIs through FastAPI. Use server-sent events or WebSocket for status/quote updates, with a bounded update rate and reconnect handling. Do not let the browser calculate authoritative P&L, risk or order approval.

### P1 — Backtest accounting and metrics require reconciliation

The backtest keeps open positions in memory but the returned trade list only includes closed positions. End-of-test positions are not clearly liquidated or marked as open in the result. Metrics calculate final equity from the last recorded equity row, gross P&L from net P&L plus costs, and slippage aggregation is passed as zero in trade logs even though entry/exit slippage was calculated. Annualization uses number of observations / 252, which may not match actual elapsed trading days or irregular multi-symbol calendars.

**Required fix:** Include open positions in final valuation, provide explicit end-of-test policy (mark-to-market vs forced liquidation), reconcile ledger cash/positions/equity independently, persist costs and slippage accurately, and annualize by actual date range and valid session count. Report undefined/insufficient metrics as N/A.

### P1 — Dashboard runtime/provider wiring requires audit

The dashboard creates provider objects and service objects within Streamlit resource cache, but the source must be checked for how the configured provider is actually selected, whether a live adapter can ever become active, whether provider status is genuinely measured, and whether the dashboard's “live” page is actually based on current authorized data. Do not claim real-time status when only synthetic/cached data is active.

### P1 — Security and repository hygiene

- `src/indian_ai_paper_trader.egg-info/` is committed build output; remove it from source control and ignore it.
- `config/kill_switch.state` is committed runtime state with `active:false`. Runtime safety state should be local and ignored; the system should fail closed if the local state is absent/corrupt.
- `.gitignore` currently ignores logs, local DBs, saved models and live/cache data, which is good, but verify actual status and historical commits for accidentally committed secrets/data.
- `.env.example` has blank TrueData credentials, which is appropriate; do not accept broker execution credentials in this paper-only project.
- Requirements are not truly pinned: `>=` ranges can resolve to different builds over time. Add a lock file and reproducible install.
- The README contains hardcoded machine-specific paths and sample commands referring to files/configs not present in the tree (e.g. `nifty50_sample.csv`, `config/ml.yaml`).

## Gaps and missing capabilities

1. React frontend and FastAPI application layer.
2. Frontend component architecture, route-level lazy loading, error boundaries, loading skeletons and frontend tests.
3. Exchange calendar with holidays/special sessions and correct timezone/session boundaries.
4. TrueData (or other vendor) adapter verified against official current API docs; current code is a stub.
5. Provider health telemetry, feed event timestamps, data quality dashboard and subscription-limit-aware symbol management.
6. Point-in-time instrument universe and survivorship-bias-aware historical constituents.
7. Corporate action adjustment pipeline with adjustment provenance and unadjusted execution prices.
8. Multi-symbol chronological ML dataset construction that preserves symbol/date groups, avoids per-symbol leakage and purges actual overlapping label windows.
9. Rolling walk-forward model evaluation and model promotion gates.
10. Probability calibration, PR-AUC, precision@K, ranking metrics, confidence intervals and regime breakdown.
11. A realistic portfolio simulator for ML signals rather than overlapping forward-return compounding.
12. Robust Indian cash-market cost model with effective-dated statutory rates, provider/broker-specific brokerage assumptions and auditably sourced rates.
13. Explicit slippage/impact models and liquidity constraints.
14. Backtest event timing, stop/target ambiguity, gap fills, partial/no fills, circuits and untradeable sessions.
15. Strategy comparison framework and parameter robustness analysis; no unbounded optimizer.
16. Data/version/config/model hashes for reproducibility.
17. CI workflow running unit/integration tests, lint, type check, dependency audit and frontend build.
18. Runtime schema migrations and backup/restore.
19. Observability and performance benchmark suite.
20. Correct user-facing distinction among real-time, delayed, cached, synthetic and historical datasets.

## Quantitative methods to prioritize (not promises of better returns)

Implement in this order and evaluate on walk-forward out-of-sample data:
1. Transparent rule-based momentum/trend baseline (already present; validate correctness first).
2. Cross-sectional ranking using momentum, relative strength, liquidity, volatility-adjusted returns and volume surprise.
3. Logistic Regression as calibrated baseline; Random Forest as non-linear comparison.
4. Gradient-boosted trees (LightGBM or XGBoost) only after leakage-safe data and baseline stability.
5. Regime filter using market trend/volatility to decide when the strategy should stand aside.
6. Triple-barrier outcome labels as a research experiment, not assumed better.
7. Probability calibration and top-K selection evaluated by precision@K, net portfolio return, drawdown and turnover.
8. Portfolio allocation with volatility targeting and concentration limits.
9. Purged walk-forward and combinatorial/embargo validation where appropriate; account for multiple testing and selection bias.

Do not begin with deep neural networks, reinforcement learning, or LLM-based buy/sell decisions. They add complexity and make causal evaluation harder, especially with limited clean Indian equity data.

## Frontend recommendation

Use:
- React + TypeScript + Vite.
- Tailwind CSS for restrained design tokens and consistent spacing.
- TanStack Query for server-state caching/refetch.
- Lightweight Zustand only for client UI state.
- Lightweight Charts for financial candle/volume charts (verify current license and use terms before adopting).
- Recharts only for secondary analytics charts if needed.
- TanStack Table for large scanner tables.
- FastAPI backend with Pydantic response models.
- WebSocket or SSE for streaming status and updates.
- Vitest + React Testing Library + Playwright for frontend tests.

Design direction: clean light-first neutral palette, warm off-white background, white panels, charcoal typography, restrained emerald for positive values and muted red for negative values, subtle borders, no gradients/neon, no decorative heavy shadows. Use compact but legible tables, consistent INR formatting, clear source/latency labels and a persistent PAPER MODE indicator.

Performance requirements:
- Route-level code splitting and lazy-loaded heavy chart/model pages.
- Keep chart data aggregation and indicator computation in backend/worker, not on every React render.
- Virtualize scanner tables.
- Batch API calls, cache stable data, throttle stream updates and never update React state for every tick if the UI cannot display at that frequency.
- Profile production bundles; set measured budgets rather than making unsupported “fast” claims.
- Follow current Vite performance/build guidance.

## Verification status and honesty

This audit is based on repository source and documentation fetched from GitHub. It did not execute the repository locally, install dependencies, verify the test-count claim, or validate a live vendor subscription. Therefore:
- “55 tests passed / 81% coverage” remains an unverified repository claim.
- TrueData adapter is not verified as operational.
- No strategy is demonstrated profitable by this review.
- No real market feed is confirmed active.

## Recommended next steps

1. Fix the P0 backtest, ML evaluation, training validation and provider adapter issues.
2. Add test fixtures for next-bar exit execution, stop gaps, stop/target collision, overlapping labels, multi-symbol purge, no-data and provider-error semantics.
3. Add React frontend + FastAPI on a separate branch; keep Streamlit temporarily as a reference/fallback until React achieves feature parity.
4. Add CI and reproducible test/build instructions.
5. Obtain vendor documentation and written permission/plan details before activating live data.
6. Run walk-forward paper simulation with licensed data and realistic costs; only then assess whether any strategy has evidence of an edge.

**No live broker execution should be added.**
