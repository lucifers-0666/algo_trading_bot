# Quantitative Decision Engine & Alpha Generation — Northstar

## 1. Multi-Stage Decision Pipeline

The Northstar Decision Engine (`src/trader/decision/decision_engine.py`) serves as the central gatekeeper reconciling technical indicator signals, market regimes, machine learning forecasts, financial news sentiment, and risk guardrails.

```
Candidate Stock
      |
      v
[ Gate 1: Market Regime Filter ] --------> (If Bearish Trending / High Volatility -> REJECT)
      |
      v
[ Gate 2: Technical Strategy Signal ] ---> (If No Confirmed Entry Trigger -> REJECT)
      |
      v
[ Gate 3: Machine Learning Model ] ------> (If Forward Win Probability < 0.55 -> REJECT)
      |
      v
[ Gate 4: Financial AI News Sentiment ] -> (If Regulatory Penalty / Bearish Catalyst -> REJECT)
      |
      v
[ Gate 5: Quantitative Risk Manager ] ---> (Assess 0.5% Risk, Sizing, Exposure, Cash)
      |
      v
Approved Trade Proposal -> Virtual Paper Execution / Human Review
```

---

## 2. Decision Logic & Conviction Scoring

For a trade candidate to be approved for virtual execution, it must achieve a composite conviction score $\ge 0.65$:

$$\text{Conviction} = w_1 \cdot S_{tech} + w_2 \cdot P_{ml} + w_3 \cdot S_{news} + w_4 \cdot S_{regime}$$

Where:
- $w_1 = 0.35$ (Technical indicator alignment: RSI in sweet spot 45–65, SMA20 > SMA50, RVOL > 1.2)
- $w_2 = 0.25$ (Machine learning calibrated probability of positive forward return)
- $w_3 = 0.20$ (Financial disclosure sentiment: $+1.0$ for positive contract win/earnings, $-1.0$ for regulatory penalties)
- $w_4 = 0.20$ (Macro regime alignment: Bullish Trending vs Choppy Sideways)

---

## 3. Strict Pre-Trade Protections & Circuit Breakers

Located in `src/trader/strategies/protections.py` and `src/trader/risk/checks.py`:

1. **Consecutive Loss Cooldown:**
   If the portfolio experiences 2 consecutive losing trades, the system locks new entries for a configurable cooldown window (e.g. 10 bars or next trading session).
2. **Symbol Cooldown:**
   After closing a position in a given equity (whether at stop-loss or profit target), the symbol enters a mandatory cooldown period (5 bars) to prevent emotional revenge-trading or over-trading in choppy noise.
3. **Daily Loss Limit Circuit Breaker:**
   If cumulative daily unrealized + realized losses exceed 1.0% of day-starting equity, all automated new proposals are halted for the remainder of the session.
4. **Maximum Drawdown Pause:**
   If total portfolio drawdown exceeds 5.0%, all buying is disabled until an operator audits the risk parameters.
5. **Circuit-Locked Bar Protection:**
   Orders cannot execute on bars where the stock is locked in upper or lower circuit limits ($|Return| \ge 9.9\%$), mirroring real Indian equity market liquidity realities.
