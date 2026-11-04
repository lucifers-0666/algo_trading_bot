# Known Limitations & Operating Boundaries

**Date:** 2026-11-04  
**Project:** Indian AI Live-Data Paper Trading Platform (Version 0.2.0)

---

## 1. Capital & Sizing Realities
- **Virtual Starting Capital:** ₹10,000 INR.
- **Risk per Trade (2.0%):** ₹200 risk budget per trade on initial capital.
- **Whole Share Constraints:** NSE cash equities require integer shares (fractional shares do not exist in Indian markets). High-priced stocks (e.g. MRF at ₹1,30,000, Honeywell Automation at ₹45,000, or TCS at ₹3,800) cannot be traded within a 2.0% risk budget or 25% max position allocation on ₹10,000 capital. The risk engine will automatically reject candidate signals where even a 1-share position exceeds the risk budget or cash ceiling.
- **Transaction Cost Drag:** Flat broker fees (e.g. ₹20/order) plus statutory taxes (STT 0.1%, Stamp Duty 0.0015%, GST 18%, Exchange charges 0.00297%) represent a high percentage on very small trade sizes (~₹2,000 position with ₹20 buy + ₹20 sell = 2% cost drag immediately). Small-account swing trading faces significant structural friction unless zero-brokerage delivery models are selected.

## 2. Market Data & Universe Boundaries
- **Provider Status:** TrueData adapter is decoupled and defaults safely to `DISABLED` mode until valid user subscription credentials are supplied. The platform operates out of the box using offline CSV archives and realistic synthetic geometric Brownian motion market data generators.
- **Broad Universe Scanning:** Scanning all ~2,000+ NSE listed stocks simultaneously in real-time requires high-bandwidth multi-symbol WebSocket streaming packages. The platform provides a curated universe of the most liquid large-cap and mid-cap NSE equities for fast local screening.
- **Corporate Action Adjustments:** EOD data includes splits and bonus adjustments; intraday tick feeds reflect unadjusted live market prices. Historical backtests must account for adjustment provenance.

## 3. Regulatory & Execution Boundaries
- **Strictly Paper Trading:** The platform does NOT connect to real demat accounts or real broker order routing APIs. All order fills, slippage, and portfolio ledger updates are purely simulated.
- **Execution Assumption:** Signals are evaluated on completed daily candles ($t$). Fills are simulated at the next session open ($t+1$) or eligible bar price. Fills are not permitted in low-liquidity stocks or stocks locked in upper/lower circuit limits.
- **Security & Network:** All server endpoints and dashboards are bound strictly to `127.0.0.1` (localhost) with zero public internet exposure.
