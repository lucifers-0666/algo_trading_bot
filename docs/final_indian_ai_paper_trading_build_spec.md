# Final Build Specification: Indian AI Live-Data Paper-Trading Platform

**Status:** Research + paper trading only. No real broker order
submission. **Market:** NSE cash equities, broad universe subject to
provider coverage and license. **Initial capital:** ₹10,000 virtual
cash. **Data:** Daily historical candles plus live intraday updates.
**First provider candidate:** TrueData, pending verification of plan,
API access, historical coverage, full-universe symbols, storage rights,
and personal-use terms. **Platform:** Local Windows application; Python
3.12, SQLite, scikit-learn, Streamlit. **Goal:** A fast, auditable,
reproducible platform to research stock screens and ML strategies---not
a promise of profit.

## 1. Product requirements

Build a local dashboard and research engine that: 1. Ingests daily
historical OHLCV candles and live intraday market updates from a
documented, authorized source. 2. Covers the broad NSE cash-equity
universe only to the extent allowed by the selected subscription and
instrument master. 3. Shows top movers, relative volume, liquidity,
trend and volatility candidates with transparent reasons. 4. Builds
timestamp-correct features and trains/evaluates ML models without future
leakage. 5. Simulates trading using ₹10,000 virtual cash, simulated
order fills, fees, slippage, holdings, P&L and audit logs. 6. Reports
backtests and paper results, including drawdown and cost sensitivity. 7.
Fails safely when the feed is stale, invalid, disconnected or not
licensed/configured. 8. Never accesses or submits orders to a real
demat/broker account in this phase.

## 2. Provider decision gate: TrueData candidate

The coding agent must inspect current official TrueData documentation
and contact/provider plan information where necessary before
implementing its adapter. Verify and document: - API availability for
custom Python applications (not just a charting plugin). - WebSocket
support, subscription limits, authentication and reconnection
behavior. - Daily and intraday historical candle availability, lookback
depth, adjustments and corrections. - Coverage of all requested NSE
cash-equity symbols and symbol/instrument master. - Whether the intended
personal research, local storage, feature calculation and ML use are
permitted. - Exact subscription price, taxes, trial terms and rate
limits. - Whether historical and live data are included in the same plan
or charged separately. - Rules about display, non-display computation,
retention, and redistribution.

Official pages to start from: - TrueData:
https://www.truedata.in/Home/Index - NSE real-time data:
https://www.nseindia.com/static/market-data/real-time-data-subscription -
NSE historical/EOD data:
https://www.nseindia.com/static/market-data/eod-historical-data-subscription -
NSE data sharing/usage policy:
https://www.nseindia.com/static/market-data/nse-data-policy - NSE retail
algo guidance:
https://www.nseindia.com/static/trade/empanelled-algo-providers-exchange

TrueData advertises real-time and historical market-data products,
including WebSocket/API offerings; this does not establish that every
product, universe, storage right, API feature or use case is included in
a particular plan. Do not assume a free API or choose a paid plan
without explicit user approval. If the provider cannot satisfy
requirements, implement the provider interface and CSV/synthetic modes
and ask the user before selecting an alternative.

Do not scrape websites, use unauthorized endpoints, bypass rate limits,
or redistribute provider data. Record source URLs, verification date,
pricing quote/plan, permitted use, and unresolved questions in
`docs/provider_comparison.md` and `docs/data_policy.md`.

## 3. Current regulatory boundary

The app is paper-only, so it must not submit live orders. Nevertheless,
document the current Indian requirements before any future
live-execution phase. Review current official SEBI and NSE/BSE
circulars, broker policies, client API requirements, order tagging/rate
thresholds, static-IP/network rules where applicable, and any relevant
registration or empanelment conditions. Requirements may depend on the
exact execution route and can change. Do not provide legal conclusions
from assumptions; list unresolved questions for the user and broker.

For a future live phase, require a separate explicit user request,
chosen broker, updated compliance review and new safety testing. Do not
include a dormant real-order function in the paper-only build.

## 4. Technology and structure

Use Python 3.12 in a `.venv`, `pandas`, `numpy`, `scikit-learn`,
`pytest`, `pydantic`, SQLite, structured logging and Streamlit. Add
dependencies only when needed and pin compatible versions.

Suggested layout:

    indian-ai-paper-trader/
      README.md
      pyproject.toml
      .env.example
      .gitignore
      config/
        app.example.yaml
        strategy.example.yaml
        risk.example.yaml
      docs/
        architecture.md
        provider_comparison.md
        data_policy.md
        strategy_spec.md
        ml_validation.md
        risk_controls.md
        regulatory_checklist.md
        testing_and_operations.md
      src/trader/
        cli.py
        config.py
        logging_config.py
        domain/models.py
        providers/base.py
        providers/csv_provider.py
        providers/truedata_adapter.py
        data/normalizer.py
        data/validation.py
        data/candles.py
        data/freshness.py
        data/store.py
        universe/instruments.py
        scanner/filters.py
        scanner/ranking.py
        features/technical.py
        strategies/baseline.py
        ml/dataset.py
        ml/labels.py
        ml/train.py
        ml/evaluate.py
        ml/inference.py
        risk/sizing.py
        risk/checks.py
        risk/kill_switch.py
        backtest/engine.py
        backtest/fills.py
        backtest/costs.py
        backtest/metrics.py
        paper/broker.py
        paper/accounting.py
        paper/orders.py
        storage/database.py
        storage/repositories.py
        dashboard/app.py
        ai/explainer.py
      tests/
        unit/
        integration/
        fixtures/
      data/.gitkeep
      reports/.gitkeep
      models/.gitkeep

Adjust the layout if a simpler structure is justified. Avoid empty
placeholder modules.

## 5. Data flow and market data

Create a `MarketDataProvider` interface. Implement CSV/synthetic sources
first. Implement `TrueDataAdapter` only after official documentation,
API access and terms are verified. All provider-specific code must stay
behind the interface.

Canonical candle fields: - exchange, symbol, instrument ID where
available - timestamp in `Asia/Kolkata` or a clearly normalized UTC
timestamp with explicit conversion - interval, open, high, low, close,
volume - provider/source, received timestamp, data status and
corporate-action fields where available

Live ingestion: - Prefer documented WebSocket streaming when available
and appropriate. - Handle reconnects, heartbeat/timeouts, authentication
expiry, throttling, duplicate/out-of-order messages and subscription
limits. - Build 1-minute/5-minute candles only from timestamps and
trades/updates supplied by the provider; do not imply a quote feed
contains every trade unless documentation confirms that. - Keep daily
candles as the main strategy input. Use intraday updates for monitoring,
candidate ranking and optional intraday features. - Distinguish
last-traded price, quote, snapshot, partial candle and completed
candle. - Show provider, last-update timestamp, feed latency where
measurable, delay/real-time status, connected/disconnected state, and
stale-data warnings. - When feed freshness breaches a configured
threshold, stop creating new paper entries. Never display stale data as
current. - Do not silently fill missing prices, invent ticks or backdate
updates.

Validation: - positive prices, nonnegative volume, high/low
consistency - duplicate/out-of-order timestamps, missing sessions and
stale data - symbol mapping, market calendar and time zone -
split/bonus/dividend adjustment provenance where available - gaps and
abnormal jumps flagged for review - log every rejected or suspicious
record with a reason

## 6. Broad NSE universe and scanner

Use the licensed provider's supported instrument master. The term "broad
NSE universe" means all eligible symbols the selected data subscription
permits; do not promise full coverage before verifying the plan. Keep
universe snapshots/versioning and historical membership when available.

Build transparent scanner views: - top percentage gainers and losers -
relative-volume candidates - momentum candidates over defined
lookbacks - trend candidates - volatility candidates -
liquidity-qualified candidates - excluded symbols with reasons

Every row must include calculation time, interval, source, and criteria.
Do not equate "top mover" with a buy signal. Filter low-liquidity,
stale, suspended/circuit-affected or insufficient-history symbols where
relevant data exists.

## 7. Deterministic baseline before ML

Implement one explainable daily swing-trading baseline first: - SMA 20,
SMA 50, RSI 14, ATR 14 - 20-day average volume/traded-value liquidity -
fully defined trend/pullback entry conditions - explicit exit rules:
ATR-based initial stop, trend-break exit, optional target and maximum
holding period - signals only after candle completion - fills no earlier
than the next eligible price/session unless an explicitly documented
realistic fill model is used - long-only, no leverage, no derivatives,
no shorting, no averaging down/pyramiding

Keep all parameters in config. Document the hypothesis and formulas. Do
not claim this strategy is profitable.

## 8. Machine learning

Use a supervised scikit-learn baseline only after deterministic
backtesting works. Candidate models may include logistic regression and
random forest; compare against the rule-based baseline. Use more complex
models only if they demonstrate robust out-of-sample improvement.

Possible features: - multi-period returns/momentum - SMA distances and
slopes - RSI, ATR and realized volatility - relative volume, traded
value, price gaps - market/index and sector-relative features only when
timestamped, licensed and reliable

Define the prediction horizon and labels before training (e.g. next 5 or
10 trading sessions). Labels must reflect only future outcomes; features
must use only information available at prediction time. Include
neutral/no-trade outcomes and costs where appropriate.

Validation requirements: - chronological train/validation/test splits
and walk-forward testing - no random shuffle for final time-series
evaluation - fit preprocessing only on training folds - prevent
overlapping-horizon leakage with a gap/embargo where needed - record
dataset version, feature schema, labels, split dates, config, seed,
package versions and model hash - do not tune repeatedly against the
final holdout - compare ML with a no-trade baseline and deterministic
strategy - reject stale or mismatched inference feature schemas - show
probability calibration and uncertainty; scores are not certainty

Track net P&L, drawdown, trade count, costs, expectancy, exposure,
turnover, robustness by period/regime and sensitivity to slippage. A
high classification accuracy does not prove profitability. No model is
promoted to paper mode solely because training metrics are good.

## 9. Virtual trading engine

Starting virtual cash: ₹10,000, configurable. Implement: - cash,
positions, reserved cash, average price and realized/unrealized P&L -
simulated order lifecycle, duplicate-order prevention and idempotency -
conservative configurable slippage and verified/timestamped
transaction-cost assumptions - simulated fills only when a valid market
observation would have been available - explicit behavior for gaps,
stop/target collision, unfilled/expired orders and market closures -
persistent ledger and audit log - user-visible PAPER mode banner - no
real broker client, real credentials, actual account balance or live
order endpoint

Paper mode must be isolated so an error cannot fall through to real
execution.

## 10. Risk defaults

Configurable simulation defaults: - virtual starting cash ₹10,000 -
planned risk per trade 0.5% of paper equity - max two open positions -
maximum invested exposure 50% of paper equity - daily-loss stop at 1% of
start-of-day paper equity - configurable max drawdown pause with manual
reset - no leverage/margin/derivatives/shorting

These are software test defaults, not guarantees of safety or
suitability. With ₹10,000, transaction costs and minimum share
quantities can make a trade impractical; skip trades that exceed the
risk budget.

Compute quantity from risk budget and stop distance, then cap by cash,
exposure, liquidity and costs. If data is stale, limits are breached,
configuration is invalid, or ledger state cannot be reconciled, reject
new trades. Persist a kill switch; missing/corrupt state means no new
entries.

## 11. Backtesting and reporting

Implement chronological event-driven backtesting with no look-ahead
bias. Model transaction costs, slippage, next-eligible-price fills,
cash, holdings, corporate actions where possible, stop gaps and unfilled
orders.

Report: - gross and net returns - CAGR only for suitable intervals - max
drawdown and duration - win rate, average win/loss, expectancy and
profit factor - number of trades, holding period, exposure and
turnover - total costs and cost sensitivity - equity/drawdown curves and
benchmark comparison if valid data exists - data source/date range,
universe version, config hash and model version

Mark low trade counts, unstable results, and weak out-of-sample results
as inconclusive.

## 12. Dashboard

Views: 1. Overview: market status, data freshness, mode, virtual
equity/cash, daily P&L, drawdown and system warnings. 2. Scanner:
movers, relative volume, trend, liquidity, rule-by-rule explanation and
timestamps. 3. Symbol detail: candles, volume, indicators and signals.
4. Strategy lab: config, backtest runs and comparison. 5. ML lab:
dataset coverage, chronological splits, metrics, model versions and
baseline. 6. Paper terminal: virtual orders, fills, positions and
ledger. 7. Performance: equity curve, drawdown, costs, monthly returns
and benchmark. 8. Risk/audit: active limits, kill switch, rejected
trades and errors. 9. Settings: provider configuration without exposing
secrets.

Keep it local-only, responsive and measured. Use background jobs for
scans/training/backtests, throttle dashboard updates, paginate large
symbol lists, and show cached data only with a stale warning. Do not
claim low latency until measured.

## 13. Security

-   `.env.example` contains placeholders only.
-   Never commit `.env`, credentials, tokens, model/data files or local
    databases.
-   Redact secrets from logs.
-   Bind dashboard to localhost by default.
-   Do not require administrator privileges.
-   Avoid unsafe deserialization and arbitrary remote code.
-   Do not auto-start ingestion or trading on Windows startup.
-   Provide safe database backup/reset steps.

## 14. Testing

Offline tests using clearly labeled synthetic fixtures: - OHLCV schema
and validation - time zones, session boundaries and candle building -
stale feed, duplicates, out-of-order messages and reconnect behavior -
indicators and warm-up periods - no look-ahead leakage and chronological
ML splits - label generation and preprocessing isolation - risk sizing,
costs, cash/exposure, daily loss and drawdown stops - kill switch and
corrupt config fail-closed behavior - paper ledger, order lifecycle,
idempotency and restart reconciliation - proof that paper mode cannot
call a real broker order endpoint - secret redaction and dashboard/CLI
smoke tests - end-to-end ingestion → scanner → signal → risk → virtual
fill → report

Report only tests actually run. Include a test deliberately attempting
to bypass risk controls and prove rejection.

## 15. CLI

Implement commands similar to: -
`python -m trader.cli validate-data --file data/sample.csv` -
`python -m trader.cli scan` -
`python -m trader.cli backtest --strategy config/strategy.yaml` -
`python -m trader.cli train` -
`python -m trader.cli evaluate-model --model-id <id>` -
`python -m trader.cli paper --start-cash 10000` -
`python -m trader.cli report --run-id <id>` -
`python -m trader.cli status` - `python -m trader.cli kill-switch on` -
`python -m trader.cli kill-switch off`

Adjust command syntax as needed. Kill-switch state persists across
restarts.

## 16. Implementation phases

Phase 1: inspect repository/runtime, verify provider docs and
requirements, produce architecture and a provider-cost/coverage
decision. Do not buy a plan or assume a provider feature.

Phase 2: skeleton, configuration, logs, CSV/synthetic ingestion,
validation, SQLite persistence and unit tests.

Phase 3: implement one provider adapter only after verification and user
approval of the selected plan. If credentials or terms are not
confirmed, leave the adapter disabled and continue in offline mode.

Phase 4: universe management, indicators, movers/relative-volume scanner
and deterministic baseline.

Phase 5: risk manager, kill switch, virtual ledger and order simulator.

Phase 6: backtesting, costs, reports and regression tests.

Phase 7: ML labels, chronological evaluation, model registry and
baseline comparison.

Phase 8: dashboard, background jobs, feed health and measured
performance.

Phase 9: full integration/security review, Windows setup instructions,
test results and known limitations.

At each phase, list changed files, design decisions, assumptions, tests
actually run, unresolved questions and next steps. Preserve existing
user work. Start by inspecting the repository and implementing Phase 1
and Phase 2. Do not stop after generating a plan. Do not add real order
execution.
