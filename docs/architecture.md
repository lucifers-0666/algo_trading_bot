# Indian AI Paper Trading Platform — Architecture & Technical Design

**Version:** 0.1.0  
**Status:** Approved  
**Timezone:** `Asia/Kolkata` (IST)  
**Execution Environment:** Windows 11 / Python 3.12 (Dedicated `.venv`)

---

## 1. Architectural Philosophy

The platform is designed around strict separation of concerns, high cohesion, zero look-ahead bias, and absolute boundary isolation between simulation and real financial markets.

```
+-----------------------------------------------------------------------------------+
|                               Streamlit Dashboard                                  |
|   Overview | Scanner | Detail | Strategy | ML Lab | Paper | Risk | History | Logs   |
+-----------------------------------------------------------------------------------+
                                        |
+-----------------------------------------------------------------------------------+
|                               Application Services                                 |
|     ScannerEngine  |  StrategyEngine  |  MLPipeline  |  BacktestEngine  | PaperBroker |
+-----------------------------------------------------------------------------------+
                                        |
+-----------------------------------------------------------------------------------+
|                                 Domain Core                                       |
|      Models (Candle, Order, Position, Ledger)  |  RiskManager & KillSwitch        |
+-----------------------------------------------------------------------------------+
                                        |
+-----------------------------------------------------------------------------------+
|                               Data & Persistence                                  |
|     MarketDataProvider (Interface)   |   Validation & Freshness   | SQLite Storage |
|  [CSVProvider]  [SyntheticProvider]  [TrueDataAdapter (Decoupled)]                 |
+-----------------------------------------------------------------------------------+
```

---

## 2. Core Subsystems

### 2.1 Market Data Ingestion & Abstraction
- **`MarketDataProvider` (Abstract Interface):** Standardizes methods:
  - `get_historical_candles(symbol, timeframe, start_date, end_date) -> List[Candle]`
  - `get_latest_quote(symbol) -> Quote`
  - `subscribe_live(symbols, callback)`
  - `unsubscribe_live(symbols)`
  - `get_connection_status() -> ConnectionStatus`
- **Providers:**
  - `SyntheticDataProvider`: Generates realistic multi-regime NSE price series with authentic volume, spreads, and circuit gaps for testing.
  - `CSVDataProvider`: Ingests standard daily and intraday Bhavcopy / OHLCV files.
  - `TrueDataAdapter`: Decoupled adapter ready for TrueData WebSocket/REST API.

### 2.2 Data Normalization & Validation
- **Timezone:** All timestamps are strictly parsed, verified, and normalized to `Asia/Kolkata`.
- **Validation Rules:**
  - Prices must be positive ($P > 0$).
  - High/Low integrity: $H \ge \max(O, C)$ and $L \le \min(O, C)$.
  - Non-negative volume ($V \ge 0$).
  - Stale feed detection: Trigger warning and halt new entries if candle/quote latency exceeds 300 seconds during active NSE hours (09:15–15:30 IST).

### 2.3 Stock Discovery & Scanner
Independent rule-based screeners:
- **Top Gainers / Losers:** Ranked by 1-day percentage change with liquidity filter.
- **Relative Volume (RVOL):** Identifies institutional participation: $RVOL = \frac{V_t}{\text{SMA}_{20}(V)}$.
- **Momentum & Trend:** SMA 20/50 crossovers, RSI 14 in sweet spot (45–65), 20-day breakout scans.
- **Volatility Candidates:** ATR expansion ($ATR_{14} / \text{Price} \ge 2.5\%$).
- **Transparent Reasoning:** Every candidate outputs explicit inclusion and exclusion reasons.

### 2.4 Deterministic Strategy Engine
- **Rule Set:** Daily swing trading baseline.
- **Signal Generation:** Evaluated only upon candle close.
- **Order Execution:** Scheduled for the next eligible session open to eliminate look-ahead bias.
- **Exits:** ATR-based initial stop loss, trend-break exit ($C < SMA_{50}$), maximum holding period exit (15 candles).

### 2.5 Risk Management & Sizing
- **Risk Budget:** 0.5% of current virtual equity.
- **Integer Share Sizing:** $Qty = \lfloor \frac{\text{Risk Budget}}{\text{Entry} - \text{Stop}} \rfloor$.
- **Hard Caps:** Maximum 2 open positions, maximum 50% total exposure, maximum 25% single-stock exposure.
- **Kill Switch:** Persistent state file (`kill_switch.state`) preventing new orders upon breach of daily loss limit (1%) or manual activation.

### 2.6 Backtesting Engine
- Chronological event-driven simulator without look-ahead leakage.
- Detailed Indian transaction cost engine: Brokerage, STT, Exchange transaction charges, SEBI turnover fees, Stamp Duty, GST, and conservative slippage.
- Generates equity curves, drawdown series, Sharpe ratio, win rate, expectancy, and profit factor.

### 2.7 Machine Learning Pipeline
- Walk-forward chronological splits with purging and embargo periods to prevent label overlap leakage.
- Supervised classification (scikit-learn Random Forest, Logistic Regression) predicting 5-day / 10-day forward return quantiles.
- Rigorous benchmark comparison against rule-based strategy and buy-and-hold.

### 2.8 Virtual Paper Trading & Accounting
- In-memory & SQLite-backed virtual broker.
- Tracks cash, reserved margin, realized P&L, unrealized mark-to-market P&L.
- Implements idempotent order lifecycle: `PENDING` $\to$ `FILLED` / `REJECTED` / `CANCELLED`.
- Full audit log of all balance changes.
