# Quantitative Reliability and Strategy Research Roadmap

## Objective

Improve the validity and repeatability of strategy research. There is no algorithm that guarantees a more profitable result. The objective is to reduce false discoveries, overfitting, execution optimism and measurement error.

## Research sequence

### 1. Establish trustworthy data
- Provider event time and receipt time kept separately.
- Daily and intraday candle completeness and session alignment validated.
- Point-in-time symbol universe; delisted stocks retained where possible.
- Corporate actions handled with adjustment provenance.
- Licensed source and permitted storage/computation uses recorded.
- Synthetic data is used only for software tests, never to claim strategy alpha.

### 2. Establish benchmark policies
Compare every strategy to:
- No-trade / cash baseline.
- Buy-and-hold on a suitable broad-market benchmark.
- Simple trend/momentum rule.
- Equal-weight or volatility-scaled basket baseline.

Use identical dates, universe, transaction costs, fill model and capital constraints.

### 3. Feature and signal experiments
Start with interpretable, economically motivated features:
- 1/5/10/20/60-session momentum and volatility-adjusted momentum.
- Cross-sectional relative strength vs Nifty 500 and sector index where available.
- Relative volume normalized by time-of-day for intraday signals.
- Moving-average distance/slope, RSI, ATR percentage and gap.
- Liquidity and traded-value constraints.
- Market regime: trend, realized volatility and breadth.
Do not add features merely because they increase in-sample score.

### 4. Models, in order
1. Logistic regression: calibration and robust baseline.
2. Random forest: nonlinear baseline, constrained depth/leaf size.
3. Gradient boosting (LightGBM/XGBoost): only after correct time-series CV; compare incremental out-of-sample utility.
4. Optional ranking objective: rank likely risk-adjusted future returns cross-sectionally (e.g. LightGBM ranker), validated by precision@K and net portfolio returns.
5. Regime filter: separate market-level risk-on/risk-off/sideways classifier or explicit rules.
6. Triple-barrier labels: experiment with take-profit, stop-loss and time expiry; maintain timestamped outcome interval for purging.
7. Portfolio allocation: volatility sizing and concentration constraints.

Do not start with deep learning, reinforcement learning or LLM-generated orders. They are not first-line methods for limited, noisy equity datasets.

### 5. Validation and anti-overfitting
- Expanding/rolling walk-forward folds with strict chronology.
- Purge by actual label start/end time, not merely an arbitrary row count after pooling symbols.
- Embargo where overlapping outcomes or shared information warrant.
- Final untouched holdout used once after design choices are frozen.
- Feature selection and preprocessing fitted only on each training fold.
- Evaluate multiple regimes and subperiods.
- Track all experiments and parameter trials to expose multiple-testing bias.
- Perform sensitivity analysis around parameter choices.
- Use block bootstrap or other dependence-aware uncertainty estimates where suitable.
- Do not trust accuracy alone.

### 6. Required ML/ranking metrics
- ROC-AUC and PR-AUC where class balance makes them meaningful.
- Precision, recall, F1 and confusion matrix.
- Brier score, log loss and reliability/calibration curve.
- Precision@K / hit rate among the top-ranked symbols.
- Rank correlation with subsequent risk-adjusted return.
- Coverage and abstention/no-trade rate.
- Subperiod and market-regime metrics.
State sample size and confidence intervals. If the test has one class or too few examples, metric is N/A, not a substituted constant.

### 7. Required portfolio/trading metrics
Only calculate these from an event-driven portfolio simulation:
- Net return after all estimated costs.
- CAGR based on actual elapsed period.
- Max drawdown and duration.
- Sharpe/Sortino with correct periodicity and adequate sample.
- Profit factor, win rate, expectancy, average win/loss.
- Turnover, exposure, average holding period, capacity proxy.
- Costs, slippage and missed/unfilled orders.
- Benchmark-relative return and downside.
- Results under base and stressed cost/slippage scenarios.

### 8. Execution model and market microstructure
- Next-session fills for daily-close signals.
- Gap-through-stop uses adverse opening/available executable price, not the stop price by default.
- If both stop and target lie inside one OHLC bar and tick sequence is unavailable, use the conservative outcome or mark ambiguous.
- Circuits, halts, no-trade sessions and low liquidity produce rejected/unfilled orders.
- Intraday fill simulation uses quotes/trades/timestamp granularity appropriate to the fill assumption.
- No invented bid/ask/spread information.

### 9. Strategy promotion gates
A candidate strategy/model is not promoted based on one backtest. Require:
- Positive out-of-sample net expectancy after costs.
- Bounded drawdown and concentration under predeclared risk limits.
- Sufficient trade count and stable results over multiple periods.
- No single symbol, date or regime dominates the outcome.
- Robustness to modest parameter changes and stressed costs.
- Reproducible model/data/config artifacts.
- Successful forward paper trading for a predeclared sample/time window.
- Manual review and explicit approval to promote to paper account.

These are research gates, not a guarantee that future performance will persist.
