# Data Quality, Provenance & Lookahead Isolation — Northstar

## 1. Principles of Financial Data Integrity

In quantitative trading, low data quality and lookahead bias are the primary causes of backtest overfitting and live execution divergence. Northstar enforces an uncompromising standard of data truthfulness:

> **Engineering Mandate:** A trading system displaying honest historical or synthetic data with zero lookahead bias is vastly superior to a system fabricating artificial bid/ask spreads, synthesizing fake live timestamps, or executing stops on unverified historical candle closes.

---

## 2. Strict Provenance Hierarchy

Every candle, quote, and tick in the Northstar pipeline carries an immutable `source: DataSource` tag:

| Source Label | Description | Allowed in Paper Trading? | Allowed in Backtesting? | Real Market Data? |
| :--- | :--- | :--- | :--- | :--- |
| `DHAN` | Official DhanHQ API (REST/WebSocket) | Yes (Verified Ticks) | Yes (Historical) | **YES** |
| `TRUEDATA` | TrueData NSE real-time tick feed | Yes (Verified Ticks) | Yes (Historical) | **YES** |
| `CSV` | Local Bhavcopy or exchange archive | Monitored Paper Only | Yes (Historical) | **YES** |
| `SYNTHETIC` | Procedurally generated geometric Brownian motion | Development / Sandbox | Offline Testing Only | **NO** |
| `HISTORICAL` | Stored historical candles without live stream | Read-Only Analysis | Yes | Static |
| `STALE` | Expired tick packets (>30s during market hours) | **EXECUTION HALTED** | N/A | Degraded |
| `UNAVAILABLE` | Feed dropped or symbol unquoted | **EXECUTION HALTED** | N/A | Degraded |

---

## 3. Elimination of Manufactured Data

To maintain quantitative integrity:
1. **No Artificial Bid/Ask Spreads:**
   When using synthetic data or Bhavcopy where no live Level-2 order book exists, `bid` and `ask` fields are explicitly returned as `None` (null). The system does not fabricate artificial $\pm 0.05\%$ spreads.
2. **No Fabricated Live Timestamps:**
   Historical candles retain their exact historical timestamps (e.g. `2024-03-01 15:30:00 IST`). The system never substitutes the current system clock (`datetime.now()`) for historical data.
3. **No Mislabeled Live Feeds:**
   Synthetic and CSV data are never labeled as `REAL-TIME`. The UI displays explicit badges: `SYNTHETIC`, `CSV`, or `DHAN`.

---

## 4. Elimination of Lookahead Bias

Located in `src/trader/strategies/lookahead_detector.py`:
- All technical indicator pipelines (SMA, RSI, ATR, RVOL, Donchian Channels) calculate metrics strictly using past and current candle closes ($t \le T$).
- In machine learning pipelines (`src/trader/ml/labels.py`), forward return labels ($t+h$) are strictly barred from the feature matrix $X_t$.
- The `audit_strategy_lookahead()` endpoint evaluates strategies by comparing expanding window calculations against full dataset calculations. Any discrepancy flags forward leakage.

---

## 5. Stop-Loss Hardening & Stale Feed Protection

Located in `AutonomousPaperTradingDaemon._evaluate_open_positions()` (`src/trader/paper/daemon.py`):
- **Defect Identified & Resolved:** Previously, if a live quote lookup failed during market hours, the daemon fell back to `candles[-1].close` from historical data. This triggered false stop-loss exits during active hours.
- **Fail-Closed Policy:** During market hours, the paper trading daemon requires a fresh, actionable quote from `get_latest_quote()`.
- If the quote fails or feed latency exceeds SLA limits (`FeedStatus.STALE`), position evaluation is paused, an audit log is emitted (`STALE_FEED_GUARD`), and stop-loss execution on historical candle closes is strictly forbidden.
