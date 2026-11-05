# Quantitative Strategy Research & Specifications — Northstar

## 1. Strategy Library Overview

Northstar provides five battle-tested, modular quantitative swing-trading strategies specifically designed for Indian equities. All strategies are long-only, enforce zero lookahead bias, and calculate deterministic stop-loss and profit-target boundaries.

---

## 2. Strategy Specifications

### 2.1 Baseline Swing Strategy (`src/trader/strategies/baseline.py`)
- **Philosophy:** Trend-following pullback entry on confirmed momentum.
- **Entry Conditions:**
  1. $Close > SMA(50)$ (Macro uptrend confirmed).
  2. $SMA(20) > SMA(50)$ (Short-term momentum aligned with long-term trend).
  3. $RSI(14) \in [45, 65]$ (Pullback into sustainable swing zone; not overbought).
  4. $RVOL \ge 1.0$ (Volume pacing matches or exceeds 20-day moving average).
- **Exit Conditions:**
  - **Stop-Loss:** $\max(SwingLow, Entry - 2 \cdot ATR(14))$.
  - **Profit-Target:** $Entry + 2 \cdot (Entry - StopLoss)$ (Minimum 1:2 Risk/Reward).
  - **Time Exit:** 15 trading days maximum holding period.

---

### 2.2 Momentum Breakout Strategy (`src/trader/strategies/momentum.py`)
- **Philosophy:** High relative momentum breakout with institutional volume expansion.
- **Entry Conditions:**
  1. $Close = \max_{20}(Close)$ (20-day high close).
  2. $RVOL \ge 1.5$ (50%+ volume surge over baseline).
  3. $RSI(14) \in [55, 75]$ (Strong upward momentum without extreme divergence).
- **Exit Conditions:**
  - **Stop-Loss:** 1.5x ATR trailing stop.
  - **Profit-Target:** 3.0x ATR expansion target.

---

### 2.3 Donchian Channel Breakout (`src/trader/strategies/breakout.py`)
- **Philosophy:** Turtle-style systematic trend breakout across multi-week consolidation channels.
- **Entry Conditions:**
  1. $High \ge DonchianUpper(20)$.
  2. ADX proxy $\ge 25.0$ (Strong trending regime active).
- **Exit Conditions:**
  - Exit when price drops below $DonchianLower(10)$ (10-day channel low).

---

### 2.4 Relative Strength vs NIFTY 50 (`src/trader/strategies/relative_strength.py`)
- **Philosophy:** Mansfield relative strength ranking. Buys top-decile NSE equities outperforming the NIFTY 50 benchmark over rolling 60-day periods.
- **Entry Conditions:**
  1. $RS_{60} > 0$ and accelerating ($\Delta RS > 0$).
  2. Stock trading above its 200-day simple moving average.
- **Exit Conditions:**
  - $RS_{60}$ crosses below zero or price violates 50-day moving average.

---

### 2.5 Financial News Sentiment Strategy (`src/trader/strategies/news_sentiment_strategy.py`)
- **Philosophy:** Event-driven momentum catalyst strategy.
- **Entry Conditions:**
  1. Positive regulatory filing or major order win detected via GDELT/BSE/NSE announcements.
  2. AI sentiment score $\ge 0.60$ with confidence $\ge 0.70$.
  3. Technical regime filter permits trading (`ALLOW_TRADING`).
- **Exit Conditions:**
  - Standard 2x ATR stop or 3-day holding period post-announcement.
