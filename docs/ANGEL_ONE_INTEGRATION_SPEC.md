# Angel One SmartAPI Integration Specification

## 1. Overview & Free Market Data Strategy
SEBI-registered broker Angel One provides the **SmartAPI** platform.
Unlike other brokers that levy monthly data charges (for example, Dhan charges ₹499 + GST/month for Data APIs while trading is free), **Angel One SmartAPI provides ₹0 free market data**, historical OHLCV candles, 5-level market depth order book snapshots, and real-time WebSocket ticks for all Demat account holders.

Northstar leverages Angel One SmartAPI exclusively as a **read-only market data adapter**.

---

## 2. Strict Safety & Architectural Isolation Guarantee
The `AngelOneAdapter` (`src/trader/providers/angelone_adapter.py`) enforces a hard architectural barrier between market data ingestion and trade execution:

```python
def _verify_read_only_isolation(self) -> None:
    forbidden = [
        "place_order", "placeOrder", "modify_order", "modifyOrder",
        "cancel_order", "cancelOrder", "holding", "allholding",
        "position", "convertPosition", "orderBook", "tradeBook"
    ]
    for method in forbidden:
        assert not hasattr(self, method), f"Safety violation: {method} found"
```

- **Zero Real-Money Routing:** The adapter contains zero order placement, position modification, or fund withdrawal methods.
- **Virtual Paper Trading Only:** All orders generated in Northstar route to the `VirtualPaperBroker` with ₹10,000 INR starting simulated cash.
- **Isolated Credentials:** SmartAPI credentials authenticate market data session tokens (`jwtToken`, `feedToken`) and never touch execution endpoints.

---

## 3. Authentication & TOTP Workflow
Angel One SmartAPI enforces Time-based One-Time Passwords (TOTP) for 2-Factor Authentication (2FA).
Northstar automates this via `pyotp`:

1. `SmartConnect(api_key)` is instantiated.
2. Current 6-digit TOTP is generated dynamically: `pyotp.TOTP(totp_secret).now()`.
3. `smart_connect.generateSession(client_code, pin, totp)` generates an authenticated session.
4. Tokens (`jwtToken`, `feedToken`) are cached in memory for 23 hours.

---

## 4. Market Depth Order Book & Microstructure
Angel One SmartAPI provides full 5-level market depth via `getMarketData(mode="FULL", ...)`:
- 5 levels of bids (price, quantity, order count).
- 5 levels of asks (price, quantity, order count).
- Calculated spread (INR and %).
- Top-5 Order Book Imbalance:
  $$\text{Imbalance} = \frac{\sum \text{Bid Qty} - \sum \text{Ask Qty}}{\sum \text{Bid Qty} + \sum \text{Ask Qty}}$$

---

## 5. Instrument Token Mapping
Core indices and liquid NSE equities are mapped in `STANDARD_ANGEL_TOKENS`:
- `NIFTY` / `NIFTY 50`: NSE token `99926000`
- `BANKNIFTY`: NSE token `99926009`
- `SENSEX`: BSE token `99919000`
- `RELIANCE`: NSE token `2885`
- `TCS`: NSE token `11536`
- `INFY`: NSE token `1594`
- `HDFCBANK`: NSE token `1333`
Dynamic resolution fallback uses `SmartConnect.searchScrip("NSE", symbol)`.

