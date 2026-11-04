# Known Limitations & Operating Boundaries

**Date:** 2026-11-04  
**Project:** Indian AI Live-Data Paper Trading Platform

---

## 1. Capital & Sizing Realities
- **Virtual Starting Capital:** ₹10,000 INR.
- **Risk per Trade (0.5%):** ₹50 risk budget per trade.
- **Whole Share Constraints:** NSE cash equities require integer shares (fractional shares do not exist in Indian markets). High-priced stocks (e.g. MRF at ₹1,30,000, Honeywell Automation at ₹45,000, or TCS at ₹3,800) cannot be traded within a 0.5% risk budget or 25% max position allocation on ₹10,000 capital. The risk engine will automatically reject candidate signals where even a 1-share position exceeds the risk budget or cash ceiling.
- **Transaction Cost Drag:** Flat broker fees (e.g. ₹20/order) plus statutory taxes (STT, Stamp Duty, GST, Exchange charges) represent a high percentage on very small trade sizes (~₹2,000 position with ₹20 buy + ₹20 sell = 2% cost drag immediately). Users must recognize that small-account trading faces significant structural friction.

## 2. Market Data & Universe Boundaries
- **Provider Status:** TrueData adapter is decoupled and disabled by default until user confirms subscription credentials. The platform operates primarily on offline CSV Bhavcopy archives and synthetic market data engines during development.
- **Broad Universe Scanning:** Scanning all ~2,000+ NSE listed stocks simultaneously in real-time requires high-bandwidth multi-symbol WebSocket streaming packages. Standard retail subscriptions often cap concurrent active streaming symbols (e.g., 50–200 symbols).
- **Corporate Action Adjustments:** EOD data includes splits and bonus adjustments; intraday tick feeds reflect unadjusted live market prices. Historical backtests must account for adjustment provenance.

## 3. Regulatory & Execution Boundaries
- **Strictly Paper Trading:** The platform does NOT connect to real demat accounts or real broker order routing APIs. All order fills, slippage, and portfolio ledger updates are purely simulated.
- **Execution Assumption:** Signals are evaluated on completed daily candles. Fills are simulated at the next session open or eligible bar price. Fills are not guaranteed in low-liquidity stocks or stocks locked in upper/lower circuits.

