# Real-Time Streaming Implementation Guide — Northstar

## 1. Overview

Northstar provides low-latency, real-time quote streaming and candle aggregation via FastAPI WebSockets. This architecture allows the React frontend to display live price ticks, tick-by-tick candlestick updates, and system health beacons without polling REST endpoints repeatedly.

---

## 2. WebSocket Protocols & Endpoints

### 2.1 Symbol Quote Stream
- **Endpoint:** `ws://127.0.0.1:8000/api/v1/ws/quotes/{symbol}`
- **Protocol:** JSON message packets every second (or on tick arrival).
- **Packet Structure:**
  ```json
  {
    "type": "quote",
    "symbol": "RELIANCE",
    "ltp": 2854.20,
    "bid": 2853.80,
    "ask": 2854.60,
    "volume": 4512300.0,
    "timestamp": "2026-11-05T15:29:14.120000+05:30",
    "source": "DHAN"
  }
  ```
- **Error Packet:**
  ```json
  {
    "type": "error",
    "symbol": "RELIANCE",
    "message": "Market feed timeout"
  }
  ```

### 2.2 Global Heartbeat & Telemetry Stream
- **Endpoint:** `ws://127.0.0.1:8000/api/v1/ws/live`
- **Protocol:** Broadcast packet every 1.0 second.
- **Packet Structure:**
  ```json
  {
    "type": "heartbeat",
    "feed_status": "HEALTHY",
    "is_actionable": true,
    "source": "DHAN",
    "latency_seconds": 0.42,
    "portfolio_equity": 10045.50,
    "cash_balance": 8500.00,
    "open_positions": 1,
    "timestamp": "2026-11-05T15:29:15+05:30"
  }
  ```

---

## 3. Frontend Real-Time Ingestion (`StockResearchView.tsx`)

The React frontend maintains an active WebSocket subscription to the currently inspected equity symbol:

```typescript
useEffect(() => {
  let ws = new WebSocket(`ws://127.0.0.1:8000/api/v1/ws/quotes/${symbol}`);

  ws.onmessage = (event) => {
    const packet = JSON.parse(event.data);
    if (packet.type === "quote" && packet.symbol === symbol) {
      setLiveQuote(packet);

      // In-place tick streaming into the active candle
      setLiveCandles((prev) => {
        if (!prev || prev.length === 0) return prev;
        const updated = [...prev];
        const lastIdx = updated.length - 1;
        const last = updated[lastIdx];
        const currentLtp = packet.ltp;

        updated[lastIdx] = {
          ...last,
          close: currentLtp,
          high: Math.max(last.high, currentLtp),
          low: Math.min(last.low, currentLtp),
          volume: packet.volume > 0 ? packet.volume : last.volume,
        };
        return updated;
      });
    }
  };
}, [symbol]);
```

### Key UI Features:
1. **Live Connection Indicator:** Displays animated pulse for `CONNECTED`, spinner for `CONNECTING`, and gray badge for `DISCONNECTED`.
2. **Provenance Tag:** Shows explicit source badges (`DHAN`, `TRUEDATA`, `CSV`, `SYNTHETIC`).
3. **Tick Latency & Timestamp:** Formatted to Asia/Kolkata (IST) display.
4. **Dynamic Resampling:** Timeframe selector allows switching between `1m`, `3m`, `5m`, `15m`, `30m`, `1h`, `1d`, and `1w` on the fly.
