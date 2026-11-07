# Quantitative Next-Session Forecasting Methodology

## 1. Objective & Scope
Northstar's Next-Session Forecasting Engine (`src/trader/ml/forecaster.py`) produces calibrated direction probabilities, expected mean returns, and volatility range cones for NIFTY 50, SENSEX, and top liquid NSE equities for the upcoming trading session.

---

## 2. Separation of Quantitative ML and Qualitative LLM
A core engineering principle of Northstar is the strict separation of numerical prediction from qualitative reasoning:
- **Quantitative ML / Statistical Models:** Handle all numerical forecasts (direction probability, expected % drift, volatility bands, and baseline comparisons).
- **Specialist Financial LLM (Fin-R1 7B on NVIDIA RTX 5060 GPU):** Handles qualitative analysis (corporate disclosures, earnings transcripts, macroeconomic event catalysts, and strategic takeaways). The LLM is never prompted to guess stock prices.

---

## 3. Feature Engineering Pipeline
Given chronological daily candles ($t \ge 25$ bars):
1. **Multi-Horizon Momentum:**
   - 1-day return: $(C_t - C_{t-1}) / C_{t-1}$
   - 3-day return: $(C_t - C_{t-3}) / C_{t-3}$
   - 5-day return: $(C_t - C_{t-5}) / C_{t-5}$
2. **Mean Reversion & Oscillators:**
   - 14-period RSI (Relative Strength Index)
3. **Trend Alignment:**
   - 20-day SMA distance: $(C_t - \text{SMA}_{20}) / \text{SMA}_{20} \times 100$
4. **Volatility & Dispersion:**
   - 14-period Average True Range (ATR) as % of Close
   - 20-period annualized historical volatility: $\sigma_{20} \times \sqrt{252} \times 100$
5. **Volume Expansion:**
   - Relative Volume (RVOL): Volume / 20-day Volume SMA

---

## 4. Direction & Volatility Range Formulation
- **Probability Calibration:**
  Composite technical signal $S$ is transformed into an upward probability via logistic sigmoid:
  $$P(\text{Up}) = \frac{1}{1 + e^{-2.2 \times S}}$$
  Clipped to $[0.15, 0.85]$.
- **Expected Daily Drift:**
  $$E[R] = (P(\text{Up}) - 0.50) \times \frac{\sigma_{20}}{\sqrt{252}} \times 1.5$$
- **Expected Trading Range (1.1x ATR Band):**
  $$\text{Range High} = C_t + 1.10 \times \text{ATR}_{14}$$
  $$\text{Range Low} = C_t - 1.10 \times \text{ATR}_{14}$$

---

## 5. Non-ML Financial Baselines
To prevent spurious quantitative claims, every forecast is benchmarked against 3 naive non-ML financial models:
1. **Zero-Return Martingale:** Assumes market is an efficient random walk ($E[R] = 0\%$, Neutral).
2. **Persistence / Momentum:** Predicts next session follows previous day's direction sign.
3. **20-day SMA Trend Following:** Bullish if $C_t > \text{SMA}_{20}$, else Bearish.

---

## 6. Immutable Prediction Ledger & Realized Evaluation
Every prediction is timestamped and persisted to `data/forecasts/forecast_ledger.json` with status `PENDING`.
Once the target trading session occurs, `evaluate_realized_candles()` computes:
- Realized return: $(C_{\text{realized}} - C_{\text{forecast}}) / C_{\text{forecast}} \times 100$.
- Direction Hit: True if predicted direction matched realized price movement.
- Range Containment: True if realized High/Low stayed within forecast bands.
- Mean Absolute Error (MAE) and historical hit-rate scorecard.

