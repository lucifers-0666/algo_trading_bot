# Market Data Usage, Storage & Compliance Policy

**Date:** 2026-11-04  
**Scope:** Indian Equity (NSE) Paper Trading & Quantitative Research Platform

---

## 1. Regulatory Context (NSE Data Policy)

National Stock Exchange of India (NSE) maintains strict regulations governing market data dissemination, storage, and processing:
- **Redistribution Prohibition:** Raw market data, whether tick-by-tick (Level 3), best-5 quotes (Level 2), or 1-minute/daily candles (Level 1), must never be redistributed, sub-licensed, broadcast, or published to external parties without direct vendor authorization and exchange licensing.
- **Non-Display Usage (NDU):** The use of real-time feeds inside automated calculation engines, machine learning pipelines, or algorithmic execution algorithms qualifies under exchange non-display guidelines. For commercial production systems, an exchange Non-Display License is mandatory. For personal local research and paper simulation, users operate under authorized vendor retail end-user agreements.
- **Display vs. Non-Display Boundaries:**
  - Display: Rendering charts, quotes, and tickers on the local Streamlit dashboard for human observation.
  - Non-Display: Automated feature calculation, screening filters, and simulated paper execution.

---

## 2. Platform Data Governance Rules

1. **Local-Only Boundary:** All ingested market data is retained strictly on the user's local disk inside `data/storage/` (SQLite database) or `data/sample/`. The application runs locally on `127.0.0.1` and never broadcasts or synchronizes market data over external networks.
2. **Zero Scraping Policy:** The platform strictly forbids web scraping of public portals (such as scraping `nseindia.com` or unauthorized quote endpoints) which violates terms of service and causes IP blocks. Data ingestion is restricted to:
   - Official historical CSV archives (e.g. NSE Bhavcopy files downloaded through official channels).
   - Documented, authorized vendor APIs (e.g. TrueData) using valid user credentials.
   - Built-in synthetic test-data generators.
3. **Data Integrity & Provenance:**
   - Every stored candle records its `source` (`synthetic`, `csv`, or `truedata`).
   - Timestamps are rigorously validated against the Indian market trading calendar (09:15 to 15:30 IST) and recorded in `Asia/Kolkata`.
   - Data adjustments (splits, bonuses) must maintain provenance flags to avoid corrupting historical return calculations.
4. **Stale Data Invalidation:**
   - Real-time and paper execution pipelines must continuously verify feed latency.
   - If market updates exceed `feed_freshness_threshold_seconds` (default: 300 seconds during active market hours), the data state transitions to `STALE`.
   - In `STALE` status, generation of new paper orders is immediately blocked.
