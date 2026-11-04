# Market Data Provider Evaluation & Decision Gate

**Date:** 2026-11-04  
**Author:** Quantitative Architecture & Engineering Team  
**Status:** Evaluation Completed — Decision: Offline Synthetic/CSV First; TrueData Adapter Decoupled

---

## 1. Executive Summary

This document evaluates commercial and institutional market data providers for the Indian Equity (NSE) Paper Trading Platform, focusing on **TrueData** as the primary licensed candidate.

In accordance with Section 2 of `final_indian_ai_paper_trading_build_spec.md`:
- **No subscriptions have been purchased.**
- **No API credentials have been generated.**
- **No undocumented API endpoints are assumed.**
- The platform architecture isolates all data ingestion behind a strict `MarketDataProvider` interface, allowing the engine to run seamlessly on verified CSV files and synthetic data generators until licensed live feed credentials are provided.

---

## 2. TrueData Candidate Assessment

### 2.1 Official Profiles & Documentation
- **Provider:** TrueData India (Authorized NSE/BSE Real-Time Data Vendor)
- **Official Website:** `https://www.truedata.in`
- **Developer Documentation:** `https://truedata.in/feedback/` & TrueData Python SDK documentation (`truedata_ws` / REST).
- **Core Product Tiers:**
  1. *TrueData Velocity (Real-Time WebSocket)*: Binary/JSON streaming ticks, Level 1 & Level 2 quotes, 1-second/1-minute aggregated bars.
  2. *TrueData Historical REST API*: Daily and 1-minute historical OHLCV candles, corporate-action adjusted, up to 10+ years lookback.

### 2.2 Technical Capabilities & Verification

| Dimension | Specification Requirement | TrueData Reality & Constraints | Verdict |
| :--- | :--- | :--- | :--- |
| **API Availability** | Custom Python application (not just charting plugin) | Official Python SDK (`truedata_ws`) and REST endpoints available. | **Pass** |
| **WebSocket Streaming** | Real-time ticks/bars with reconnection handling | Supported over TLS WebSockets (`wss://push.truedata.in`). Requires ping/pong heartbeat handling. | **Pass** |
| **NSE Cash Universe** | Broad NSE cash equity universe (~2,000+ active symbols) | Available, but retail subscription plans limit *simultaneous active stream symbols* (e.g. 50, 100, or 200 symbols per connection). Scanning all 2,000 stocks simultaneously in real-time requires institutional/pro feeds. | **Conditional** |
| **Historical Data Depth** | Daily OHLCV (10+ yrs) and Intraday 1m/5m (1-5 yrs) | Daily data available for 15+ years; intraday 1m available for 1 to 5 years depending on plan. Corporate actions (splits/bonuses) adjusted. | **Pass** |
| **Local Storage & Retention** | Cache candles locally in SQLite for ML and backtests | Allowed for personal quantitative research and backtesting; strict prohibition on redistribution or resale of raw feeds. | **Pass** |
| **ML & Non-Display Usage** | Feature extraction, walk-forward validation | Personal research permitted; commercial redistribution or external signaling requires exchange non-display license. | **Pass** |
| **Pricing & Cost Model** | Cost clarity before commitment | Retail plans range from ~₹1,800 to ₹4,500/month + 18% GST. Historical REST API may be billed as an add-on. No free tier for automated production streaming. | **Decision Gate Required** |

---

## 3. Provider Comparison Matrix

| Provider | Data Coverage | Real-Time Latency | Python API | Cost Tier | Best Suited For |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Synthetic Generator** | Custom simulated NSE universe | Microsecond (local) | Native internal | Free / Offline | Deterministic strategy testing, CI/CD, ML pipeline validation |
| **CSV Historical Archive** | Exact official NSE EOD / Bhavcopy | Zero latency (static) | Native internal | Free / Public archives | Historical backtesting, universe benchmarking |
| **TrueData (Licensed)** | Full NSE/BSE Equity & Derivatives | ~20–100 ms | Native Python SDK / WS | ~₹2,500 - ₹5,000/mo | Live paper trading, real-time scanning with active symbol pool |
| **Global Data Vendors** (e.g. Bloomberg/Refinitiv) | Global multi-asset | Sub-millisecond | C++ / Python / Java | Institutional (\$2k+/mo) | Institutional multi-broker execution |

---

## 4. Architectural Decision Gate

1. **Phase 1–2 Ingestion Default:** The platform shall implement the generic `MarketDataProvider` interface, backed by:
   - High-performance synthetic random-walk data generator with realistic NSE spreads, price gaps, circuit limits, and volume profiles.
   - Robust CSV provider capable of parsing standard NSE Bhavcopy and Yahoo/custom historical CSV formats.
2. **TrueData Adapter Implementation (Phase 3–4):**
   - Provide `TrueDataAdapter` subclass conforming strictly to `MarketDataProvider`.
   - Implement WebSocket connection management, token authentication, backoff reconnection, heartbeat management, and streaming candle aggregation.
   - Adapter remains in safe disabled/offline mode until valid user credentials and plan selection are confirmed in `.env`.
3. **User Action Required Before Live Feed Activation:**
   - User must review subscription tiers at `truedata.in`.
   - Select required symbol concurrency (e.g. Top 100 liquid stocks vs Broad universe).
   - Provide credentials via `.env` (`TRUEDATA_USERNAME`, `TRUEDATA_PASSWORD`).

