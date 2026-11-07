# EOD Market Intelligence and Open-Source Framework Adoption

**Status:** Deterministic EOD core added on an isolated feature branch. NSE data ingestion, production scheduling, persistent report storage, API wiring and dashboard approval workflow remain integration tasks.
**Trading boundary:** NSE cash-equity research and virtual paper execution only. Maximum planned risk per new trade is 0.5% of current virtual equity. No live broker routing.

## 1. Target EOD workflow

Run after the NSE regular session has completed and the daily candle provider has finalized the session (default operational target 16:00 IST, subject to provider publication time and exchange calendar).

1. Resolve the prior completed NSE session from the exchange calendar. Never assume the previous calendar day was a trading day.
2. Load the point-in-time NIFTY 500 constituent snapshot and at least 61 completed daily bars for NIFTY 50, India VIX, sector indices and each eligible stock.
3. Validate source, timestamps, duplicate candles, corporate-action adjustment policy, missing sessions, OHLCV consistency and feed freshness.
4. Classify the broad regime using NIFTY ADX(14), 20/50 EMA slopes, NIFTY close/EMA alignment, India VIX and sector-index breadth.
5. Screen each eligible stock for 20/50 EMA pullback, 20-session relative volume and average traded value.
6. Rank by 20/60-session relative strength versus NIFTY 50.
7. Calculate conditional breakout trigger, ATR stop, 2R/3R targets and quantity. Round to instrument tick size in production (the current pure engine uses ₹0.05 until instrument metadata is injected).
8. Persist an immutable EOD report with source and universe versions.
9. Ask local Ollama for exactly three explanatory bullets using the precomputed facts. Reject malformed output; never allow it to modify levels or quantity.
10. Display candidates for human review. At the next open, refresh prices and feed health, check gaps, stop distance, cash, exposure, kill switch and the 0.5% risk cap again before creating a paper fill.

A setup is a conditional plan, not a market-on-open instruction. If the open is beyond the trigger, below the stop, or causes risk to exceed the budget, skip it rather than widening the stop or increasing capital.

## 2. Regime rules (initial deterministic baseline)

The implementation uses the following initial rules; thresholds are configuration candidates and require walk-forward validation.

- **Risk-Off:** India VIX >= 25, or NIFTY below EMA50 with negative five-session EMA50 slope and ADX >= 18. Block new long candidates.
- **Bullish Trend:** NIFTY close > EMA20 > EMA50, both EMA slopes positive, ADX >= 18, India VIX < 22, and at least half of available sector indices above EMA20 > EMA50.
- **Mean-Reverting/Chop:** all other conditions. Candidates can be displayed, but regime-aware approval should require stricter confirmation and/or reduced portfolio exposure.

ADX must be computed from directional movement and true range, not hard-coded or approximated from trend. Sector breadth is a ratio and must report its denominator; missing sector data must not be interpreted as positive breadth.

## 3. Candidate mathematics

For a long setup, based only on the completed session:

- Relative strength: RS_n = (1 + stock_return_n) / (1 + NIFTY_return_n) - 1.
- Pullback: close is within configured tolerance (initially 1.5%) of EMA20 or EMA50 and remains above EMA50.
- Volume confirmation: current completed-session volume / 20-session average volume >= 1.20.
- Liquidity: 20-session average traded value >= configured floor (initially ₹2 crore; validate against point-in-time universe and execution capacity).
- Trigger: prior completed-session high + 0.10 * ATR(14), rounded to tick size.
- Stop: trigger - 1.50 * ATR(14), rounded to tick size.
- R = trigger - stop; Target 1 = trigger + 2R; Target 2 = trigger + 3R.
- Risk budget = current virtual equity * 0.005.
- Quantity = min(floor(risk_budget / (trigger - stop)), floor(max_capital_fraction * equity / trigger)).
- Reject zero quantity, invalid price geometry, stale/incomplete data, Risk-Off regime, and risk greater than 0.5%.

Projected target P&L is gross and excludes brokerage, statutory charges and slippage until the broker-specific round-trip cost model is applied. The final pre-trade assessment must use the actual approved quantity and adverse gap-aware execution price.

## 4. Framework evaluation and adoption policy

| Framework | Useful battle-tested patterns | Constraints | Adoption decision |
|---|---|---|---|
| Freqtrade | Strategy lifecycle, dry-run mode, backtest export, lookahead/recursive analysis, hyperopt, cooldown/protection patterns, REST API, Telegram commands and notifications | Crypto-first; CCXT/exchange assumptions and GPL-3.0 licensing. Not an NSE data or Indian statutory-cost engine. | Reimplement patterns clean-room. Do not import, vendor or copy GPL code into this project. Telegram is useful for status/alerts, but do not expose force-buy/force-exit remote controls in this paper-only app. |
| QuantConnect LEAN | Event-driven time slices, order lifecycle, fill models, stale-data checks, slippage interfaces, fee models, portfolio/risk models | Large C# engine and operational footprint; its default brokerage/data assumptions do not supply NSE-specific rules. Apache-2.0 permits reuse subject to notices and license terms. | Use as the reference model for our own FillModel and order-event contracts. Do not embed the full engine in this Python service initially. A separate LEAN research adapter may be evaluated later. |
| Jesse | Python strategy interface, candle-by-candle backtesting, comprehensive reporting, fees/order-type simulation, ML dataset generation, significance and Monte Carlo analysis, risk_to_qty/size_to_qty helpers | Crypto-oriented data/exchange abstractions. Its documented position sizing uses utility helpers (risk_to_qty / size_to_qty), not a position-sizing decorator. Current repo/docs search surfaced optimization, Monte Carlo and rule-significance testing, but did not establish a first-class walk-forward validator; implement purged walk-forward validation in our own research layer. Repository is MIT-licensed. | Borrow high-level reporting, risk-based quantity helper design and statistical-validation patterns; do not adopt its exchange/runtime layer. MIT code reuse is possible only with license and copyright notices after legal review. |

### Recommended components to implement natively

- OrderIntent / OrderEvent / FillEvent contracts and idempotent lifecycle.
- Fill model interface: market, limit, stop, gap-through-stop, partial/unfilled and circuit/volume rejection.
- Slippage model interface: fixed-bps baseline first, then calibrated volume/volatility-aware model from permitted historical data.
- Fee model interface: dated NSE/BSE cash-equity statutory charges and broker tariff configuration.
- Risk wrappers: per-trade 0.5% cap, max open risk, max exposure, daily loss, drawdown pause, symbol cooldown and persistent kill switch.
- Backtest report: equity curve, drawdown, trade distribution, exposure, turnover, fees/slippage, unfilled orders and benchmark-relative return.
- Validation: incremental lookahead audit, warmup checks, purged walk-forward splits, final holdout, block bootstrap/Monte Carlo and stressed costs.

### What not to import

Do not import Freqtrade's strategy or optimizer runtime. Do not pull in all of LEAN or Jesse just to reuse a few classes. Avoid a second order database, a second portfolio ledger, a second scheduler, or two competing indicator definitions. Keep one canonical Candle, one order lifecycle, one cost model and one paper ledger.

## 5. License and provenance controls

- Freqtrade: GPL-3.0; study public docs and architecture, but keep implementation clean-room and dependency-free.
- LEAN: Apache-2.0; if any source files are adapted, preserve required copyright, license and NOTICE material and record file-level provenance.
- Jesse: MIT; if source is reused, include the license/copyright notice and track modified files.
- Pin inspected upstream commit/tag in docs/third_party/ before any future code-level adaptation. Run dependency/license scanning in CI.
- This document is an engineering assessment, not legal advice.

## 6. API and React dashboard integration

Add endpoints under the existing localhost-only FastAPI app:

- POST /api/v1/eod/run: authenticated local operator request; accepts explicit benchmark/VIX/sector symbols and a point-in-time NIFTY 500 universe version. Runs data validation and creates a report.
- GET /api/v1/eod/latest: returns report, session date, data provenance, coverage and warnings.
- POST /api/v1/eod/candidates/{symbol}/approve: authenticated human approval. Server loads the stored candidate; never trusts client-supplied price, stop, target or quantity. Revalidates feed freshness, current market price/gap, tick size, position state, available cash, max exposure, 0.5% risk, daily loss and kill switch before a paper-only order.
- POST /api/v1/eod/kill-switch: use existing persistent risk kill switch; do not implement a second one.

React view should show the latest report and stale-data state, market regime, breadth/advance-decline if the source provides complete point-in-time constituents, portfolio equity/drawdown, candidate rows, exact risk/targets, Ollama narrative and approval/rejection audit. The emergency switch must call the existing protected endpoint. Never place broker credentials in Vite VITE_* variables or browser storage; all provider credentials remain server-side environment variables.

## 7. Automation and operational schedule

Use the existing Windows-local deployment model. Register the weekday job with powershell -ExecutionPolicy Bypass -File scripts/register_eod_task.ps1 (default 16:40 local time); it invokes scripts/run_eod_analysis.ps1. The FastAPI service and logged-in workstation session must be active. Prefer this single Windows Task Scheduler job over starting an in-process scheduler in every Uvicorn reload worker. The command must be idempotent on (session_date, universe_version, config_hash). If duplicate runs occur, return the existing report unless an explicit audited force-refresh is requested.

Do not run on weekends/holidays. Do not generate actionable output when any required benchmark/VIX/constituent data is stale, missing, mismatched or synthetic. Synthetic fixtures are for tests only.

## 8. Promotion gates

Before showing the system's picks as actionable:
- Validate 61+ completed bars, session alignment and point-in-time NIFTY 500 constituents.
- Backtest the exact EOD signal and next-session trigger execution with gaps, fees, slippage, circuits and unfilled orders.
- Use walk-forward validation and a final untouched holdout.
- Report precision@K, net expectancy, drawdown, turnover, costs and candidate coverage by regime.
- Forward paper-trade for a predeclared sample.
- Require manual approval. This upgrade does not authorize live order routing or broker API integration.


## 9. Upstream references reviewed

- Freqtrade strategy and backtest documentation: https://www.freqtrade.io/en/stable/strategy-101/ and https://www.freqtrade.io/en/stable/backtesting/
- Freqtrade Telegram controls: https://www.freqtrade.io/en/stable/telegram-usage/
- Freqtrade project license: https://github.com/freqtrade/freqtrade/blob/develop/LICENSE (GPLv3 declared in project metadata).
- LEAN fill model concepts: https://www.quantconnect.com/docs/v2/writing-algorithms/reality-modeling/trade-fills/key-concepts
- LEAN slippage models: https://www.quantconnect.com/docs/v2/writing-algorithms/reality-modeling/slippage/supported-models
- LEAN repository/license: https://github.com/QuantConnect/Lean (Apache-2.0).
- Jesse repository/license and research API: https://github.com/jesse-ai/jesse and https://docs.jesse.trade/docs/research/
- Jesse position-risk helper reference: https://github.com/jesse-ai/jesse/blob/master/jesse/mcp/resources/position_risk.md

The existence of an upstream feature does not prove it is appropriate for NSE cash equities. All fill, fee, calendar, symbol, circuit and data-right assumptions must be replaced or validated for the Indian market.
