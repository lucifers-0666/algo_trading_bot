# Comprehensive Evaluation of Authoritative Indian Market Data Providers

**Document ID:** DOC-DATA-EVAL-002  
**Classification:** Financial Data Infrastructure & Regulatory Compliance  
**Date:** 2026-11-05  
**Version:** 1.0.0  
**Target Platform:** Indian AI Quantitative Trading & Financial Intelligence Platform (`algo_trading_bot`)

---

## 1. Objective and Evaluation Criteria

The platform requires dependable market data for Indian equities (National Stock Exchange - NSE cash equities segment). In accordance with our platform architecture, we prohibit unverified scraping and fabricated prices. This document evaluates three primary authoritative data sources against six key operational criteria:

1. **Licensing & Regulatory Compliance:** Legal authorization under SEBI / NSE data redistribution policies for personal quantitative research and automated paper trading.
2. **Coverage & Granularity:** Breadth of NSE equity coverage (NIFTY 50, NIFTY 500, broad universe), tick-level vs 1-minute vs daily resolution, and Level 2 market depth (5-depth / 20-depth bid/ask).
3. **Latency & Protocol Quality:** Transport protocol (WebSocket vs HTTP REST), reconnection resiliency, heartbeat/keepalive mechanisms, and latency metrics.
4. **Historical Data Archive:** Depth of completed historical OHLCV data for backtesting and machine learning model training (10+ years daily, 1–5 years intraday).
5. **Cost & Commercial Accessibility:** Initial capital requirement, recurring subscription fees, and developer onboarding friction for an individual researcher starting with ₹10,000 virtual capital.
6. **API Stability & Python SDK Quality:** Documentation clarity, official SDK support, authentication flow, and token lifetime.

---

## 2. Side-by-Side Provider Matrix

| Evaluation Dimension | **TrueData** (Authorized Data Vendor) | **DhanHQ** (Broker API - SEBI Registered) | **NSE Data & Analytics** (Official Exchange) |
| :--- | :--- | :--- | :--- |
| **Legal Status** | SEBI/NSE Authorized Real-time Vendor | SEBI Registered Broker (Dhan / Moneylicious) | 100% Owned Subsidiary of NSE India |
| **Primary Use-Case** | Institutional / Retail Pro Market Feed | Retail & Pro Algorithmic Trading | Institutional Data Feeds & Bulk Archives |
| **NSE Cash Coverage** | 100% of NSE Equities & Indices | 100% of NSE/BSE Equities & Derivatives | 100% of all NSE Segments |
| **Live Protocol** | WebSocket (Binary / JSON) + REST | WebSocket (Binary Packets) + REST | Direct Multicast / Dedicated Leased Lines |
| **Market Depth** | Best 5 Bid/Ask (Tick-by-tick available) | Best 5 Bid/Ask via WebSocket | Full 20-Depth / Tick-by-Tick Order Book |
| **Historical Data** | 10+ years Daily, 2-5 years 1-min / Tick | 5+ years Daily, 1+ year Intraday via API | 20+ years Daily & Historical Tick Archives |
| **Authentication** | Username / Password + Session Token | Client ID + Access Token (OAuth / Static) | Enterprise VPN, Digital Certificates, IP Whitelist |
| **Pricing / Month** | ₹1,500 – ₹3,500/month (Retail Pro tiers) | **₹0 (Free)** for Dhan account holders | ₹25,000 – ₹1,50,000+/month (Enterprise) |
| **Suitability for Research** | **High** (Pure data provider, no broker tie-in) | **Very High** (Free, fast API, official SDK) | **Low** (Prohibitive cost for personal research) |

---

## 3. In-Depth Provider Profiles

### 3.1 DhanHQ (Dhan Broker API) — Recommended Primary Live Adapter
- **Overview:** Dhan (Moneylicious Securities Pvt Ltd) is a modern SEBI-registered retail broker offering an open, high-performance API for trading and live market data.
- **Key Advantages:**
  - **Zero Cost for Developers:** No recurring monthly fee for live quotes, historical data, and WebSocket feeds.
  - **High Performance WebSocket:** Employs efficient binary packet unpacking for ultra-low latency real-time quote feeds (LTP, volume, best 5 bids, best 5 asks).
  - **Comprehensive Rest API:** Provides endpoints for daily historical OHLCV, intraday candles, security master, and live LTP snapshots.
  - **Zero Live Trading Risk:** By strictly consuming market data endpoints and isolating/omitting order execution endpoints, the API acts as a pure read-only institutional data provider for our virtual paper-trading engine.
- **Limitations:**
  - Access token expires after 24–30 days and requires refreshing.
  - Rate limited to 10 requests/second for REST calls (plenty for swing trading).

### 3.2 TrueData — Recommended Licensed Vendor
- **Overview:** TrueData is an official NSE-authorized dot-com vendor providing specialized market data feeds to quantitative traders, financial portals, and charting software.
- **Key Advantages:**
  - Broker-neutral: No need to open a demat or brokerage account.
  - Comprehensive historical database with corporate action adjustments (splits, bonuses, dividends).
  - High reliability and dedicated quantitative support.
- **Limitations:**
  - Recurring monthly cost (₹1,500 to ₹3,500/month), which is disproportionate for initial research with ₹10,000 starting paper capital.

### 3.3 NSE Data & Analytics (formerly DotEx)
- **Overview:** The commercial data arm of the National Stock Exchange of India.
- **Key Advantages:** The ultimate golden copy of exchange data with zero intermediary risk.
- **Limitations:** Enterprise pricing and procurement bureaucracy render it inaccessible for individual retail research.

---

## 4. Multi-Tier Data Provider Architecture

To achieve high reliability, provider independence, and zero downtime, the platform implements a three-tier fallback architecture:

```
+-----------------------------------------------------------------------+
|                       Abstract MarketDataProvider                     |
|         (get_historical_candles, get_latest_quote, get_market_depth)  |
+-----------------------------------------------------------------------+
                                    |
      +-----------------------------+-----------------------------+
      |                             |                             |
      v                             v                             v
+------------------+      +------------------+      +-------------------+
|  DhanHQ Adapter  |      | TrueData Adapter |      |   CSV / Bhavcopy  |
|  (Live Feed #1)  |      |  (Live Feed #2)  |      | (Historical/Cold) |
|  Status: ACTIVE  |      | Status: FALLBACK |      |  Status: LOCAL    |
+------------------+      +------------------+      +-------------------+
```

### 4.1 Strict Data Provenance Labels
Every price, quote, and candle ingested into the platform is stamped with a non-forgeable provenance tag:
1. `REAL_TIME`: Live, streaming WebSocket quote received < 3 seconds ago during active NSE market hours.
2. `DELAYED`: Exchange-delayed quote (typically 15-minute delay).
3. `HISTORICAL`: Completed official closing candle from Bhavcopy or historical REST endpoint.
4. `CACHED`: Locally persisted database record retrieved from cache.
5. `SYNTHETIC`: Mathematically generated test data (used strictly in test harness and simulation).
6. `STALE`: Data whose timestamp exceeds maximum allowable latency threshold (> 30 seconds for live feeds).
7. `UNAVAILABLE`: Symbol not found or quote unavailable. Fabricated fallback prices are strictly forbidden.
8. `ERROR`: Network or parsing error occurred during data acquisition.

---

## 5. Regulatory Compliance and SEBI Boundaries

Under SEBI (Stock Brokers) Regulations and circulars on algorithmic trading:
- Automated order routing directly to broker trading gateways requires formal broker approval, algorithmic certification, and risk compliance audits.
- **Personal Quantitative Research and Virtual Paper Trading** operate outside SEBI algorithmic certification requirements, provided **zero live broker orders or demat routing occur**.
- Our platform strictly adheres to this boundary: all trade proposals are virtual, executed inside our simulated ledger, and require explicit human operator confirmation.

