# Institutional Backtesting & Execution Realism — Northstar

## 1. Backtesting Engine Architecture

Located in `src/trader/backtest/engine.py` and `src/trader/backtest/costs.py`.

Unlike generic backtesters that simulate perfect fills at candle close prices, Northstar simulates institutional execution realities tailored to Indian equity cash markets:

1. **Next-Bar Open Execution:** Signals generated at candle $t$ close can only execute on candle $t+1$ open.
2. **Gap-Through Stop-Loss Modeling:**
   If a stock opens below the planned stop-loss level (e.g. overnight gap down), the order fills at the lower opening price—never at the theoretical stop price.
3. **Same-Bar Collision Handling:**
   If a candle touches both the stop-loss price and profit-target price, the backtester conservatively assumes the stop-loss was triggered first.
4. **Circuit-Locked Bar Rejection:**
   If a stock hits upper or lower circuit limits ($\pm 10\%$), execution is blocked due to liquidity freeze.

---

## 2. Indian Equity Statutory Transaction Costs

Located in `src/trader/backtest/costs.py`:

Every trade deducts statutory taxes and fees mandated by the Government of India, SEBI, and the stock exchanges:

| Cost Component | Statutory Rate | Applied On | Description |
| :--- | :--- | :--- | :--- |
| **Brokerage** | ₹20.00 / order | Buy & Sell | Discount broker flat fee (Zerodha/Groww model) |
| **Securities Transaction Tax (STT)**| 0.10% (0.001) | Buy & Sell | Delivery trades on NSE |
| **NSE Transaction Charge** | 0.00325% | Buy & Sell | Exchange turnover levy |
| **SEBI Turnover Charge** | ₹10 / Crore (0.000001) | Buy & Sell | Regulatory oversight fee |
| **State Stamp Duty** | 0.015% (0.00015) | **Buy Only** | Indian Stamp Act 2019 schedule |
| **Goods & Services Tax (GST)** | 18.0% | Both | 18% on (Brokerage + Exchange + SEBI fees) |
| **Slippage Model** | 10 basis points (0.10%) | Both | Market impact on execution |

---

## 3. Walk-Forward Validation & Purge Gaps

Located in `src/trader/ml/dataset.py` and `src/trader/ml/train.py`:

To prevent data snooping and chronological leakage:
1. **Strictly Chronological Splits:** Data is ordered by timestamp; future data is never used for training.
2. **Purge Gaps ($Gap = \text{Horizon}$):** An embargo window equal to the forward label horizon is inserted between training and test sets to eliminate overlapping forward return correlations.
3. **Out-of-Sample Calibration:** Model probabilities are evaluated using Brier Score, Log Loss, and ROC-AUC on unseen forward test folds.
