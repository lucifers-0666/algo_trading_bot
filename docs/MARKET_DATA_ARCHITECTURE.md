# Market Data Architecture & Multi-Timeframe Streaming — Northstar

## 1. Architectural Overview

Northstar implements a strictly decoupled, vendor-agnostic market data ingestion architecture engineered specifically for the Indian equity markets (National Stock Exchange - NSE). The system enforces explicit data provenance, fail-closed freshness monitoring, multi-timeframe OHLCV bar aggregation, and real-time WebSocket tick streaming.

```
+-----------------------------------------------------------------------------------+
|                           Market Data Providers                                   |
|  +-------------------+  +-------------------+  +-------------------------------+  |
|  |   DhanHQ API      |  | TrueData Feed     |  | Synthetic / CSV Bhavcopy      |  |
|  | (Official REST/WS)|  | (WebSocket Ticks) |  | (Deterministic/High-Res)      |  |
|  +---------+---------+  +---------+---------+  +---------------+---------------+  |
+------------|----------------------|----------------------------|------------------+
             |                      |                            |
             +----------------------+----------------------------+
                                    |
                                    v
                     +------------------------------+
                     | BaseMarketDataProvider (ABC) |
                     +--------------+---------------+
                                    |
            +-----------------------+-----------------------+
            |                                               |
            v                                               v
+-----------------------+                       +-----------------------+
| Candle Resampler      |                       | 11-State Health &     |
| (1m, 3m, 5m, 15m, 30m,|                       | Freshness Guard       |
|  1h, 1d, 1w)          |                       | (trader/freshness.py) |
+-----------+-----------+                       +-----------+-----------+
            |                                               |
            +-----------------------+-----------------------+
                                    |
                                    v
                  +-----------------------------------+
                  | FastAPI REST & WebSocket Endpoints|
                  | - /api/v1/instruments/{sym}/candles|
                  | - /api/v1/ws/quotes/{symbol}      |
                  | - /api/v1/ws/live                 |
                  +-----------------+-----------------+
                                    |
                                    v
                  +-----------------------------------+
                  | React Workstation Frontend        |
                  | (StockResearchView & Charts)      |
                  +-----------------------------------+
```

---

## 2. Core Components

### 2.1 Provider Abstraction (`MarketDataProvider`)
Located in `src/trader/providers/base.py`:
- `get_historical_candles(symbol, timeframe, start_date, end_date)`: Guarantees chronological ordering and returns validated `Candle` domain models.
- `get_latest_quote(symbol)`: Returns real-time or snapshot `Quote` with Last Traded Price (LTP), depth (where available), and ISO timestamp in Asia/Kolkata (IST).
- `get_connection_status()`: Telemetry on provider health, network latency, and active symbol subscriptions.

### 2.2 Supported Providers
1. **DhanHQ Adapter (`src/trader/providers/dhan_adapter.py`):**
   - Official Indian discount broker market data API.
   - Read-only data consumption: quotes, 5-level market depth, and historical intraday/daily candles.
   - Zero execution routing: does not connect to demat or live order routing endpoints.
2. **TrueData Adapter (`src/trader/providers/truedata_adapter.py`):**
   - Real-time institutional tick feed via WebSocket.
   - Handles connection lifecycle, heartbeat keep-alive, reconnect backoff, and packet parsing.
3. **CSV Data Provider (`src/trader/providers/csv_provider.py`):**
   - Ingests official NSE Bhavcopy and historical CSV data archives.
   - Enforces sequence monotonically increasing by timestamp and rejects duplicate timestamps.
4. **Synthetic Data Provider (`src/trader/providers/synthetic_provider.py`):**
   - Deterministic procedural data generator using local NumPy `default_rng`.
   - Generates realistic multi-regime daily and 1-minute intraday session bars (09:15 to 15:30 IST).
   - Provenance strictly tagged as `DataSource.SYNTHETIC` with honest `bid=None, ask=None` (no manufactured bid/ask spreads).

---

## 3. Multi-Timeframe Candle Resampling Engine

Located in `src/trader/data/resampler.py`:
- **Supported Timeframes:** `1m`, `3m`, `5m`, `15m`, `30m`, `1h`, `1d`, `1w`.
- **Session Alignment:** Intraday bars are strictly anchored to market opening at 09:15:00 IST using pandas custom offsets, preventing mismatched bar boundaries.
- **OHLC Invariants:**
  - $Open = Open_{first}$
  - $High = \max(High_i)$
  - $Low = \min(Low_i)$
  - $Close = Close_{last}$
  - $Volume = \sum Volume_i$
  - $Turnover = \sum Turnover_i$
- **Downsampling Safety Guard:** Rejects attempts to convert lower-frequency data (e.g. daily) into higher-frequency data (e.g. 1-minute) without high-resolution source ticks.

---

## 4. 11-State Feed Health & Freshness Model

Located in `src/trader/data/freshness.py`:
The data health engine transitions through 11 discrete states:
1. `NOT_CONFIGURED`: API credentials absent.
2. `CONNECTING`: Establishing socket handshake.
3. `CONNECTED`: Socket open, waiting for initial tick.
4. `RECEIVING_DATA`: Real-time packets flowing normally.
5. `HEALTHY`: Ticks within SLA latency thresholds (< 5.0 seconds).
6. `STALE`: Tick delay exceeds safety limit during active trading session (> 30.0 seconds).
7. `DISCONNECTED`: Upstream feed dropped.
8. `ERROR`: Protocol or authentication exception.
9. `MARKET_CLOSED`: Outside NSE official trading hours (Weekdays 09:15–15:30 IST) or holiday.
10. `HISTORICAL_ONLY`: Provider only supports static historical candles.
11. `SYNTHETIC_ONLY`: System running in offline procedural simulation mode.

---

## 5. Real-Time WebSocket Streaming

FastAPI WebSocket endpoints stream ticks directly to connected browser clients:
- `/api/v1/ws/quotes/{symbol}`: Streams sub-second quote packets:
  ```json
  {
    "type": "quote",
    "symbol": "INFY",
    "ltp": 1622.45,
    "bid": null,
    "ask": null,
    "volume": 5820100.0,
    "timestamp": "2026-11-05T15:29:45+05:30",
    "source": "SYNTHETIC"
  }
  ```
- `/api/v1/ws/live`: Streams portfolio equity, feed health, and open positions heartbeat every second.
- **Frontend Integration:** In `StockResearchView.tsx`, incoming ticks dynamically update the active candlestick's high, low, close, and volume without triggering full page or component re-renders.
