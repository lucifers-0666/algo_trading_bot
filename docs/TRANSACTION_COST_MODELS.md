# Multi-Broker Transaction Cost & Statutory Tax Models

## 1. Statutory Taxes & Regulatory Levies (SEBI / NSE / State)
Trading Indian equities incurs mandatory sovereign taxes and exchange levies that differ significantly between Delivery (CNC) and Intraday (MIS) trades:

| Levy | Delivery (CNC) | Intraday (MIS) | Notes |
| :--- | :--- | :--- | :--- |
| **Securities Transaction Tax (STT)** | 0.10% on BUY and SELL | 0.025% on SELL only | Sovereign direct tax |
| **Exchange Transaction Charges** | 0.00297% (NSE Cash) | 0.00297% (NSE Cash) | NSE circular effective Oct 2024 |
| **SEBI Turnover Fee** | ₹10 / crore (0.0001%) | ₹10 / crore (0.0001%) | Regulatory oversight fee |
| **Stamp Duty** | 0.0015% on BUY only | 0.003% on BUY only | Indian Stamp Act (State revenue) |
| **GST** | 18% on Services | 18% on Services | 18% on (Brokerage + Txn + SEBI) |

---

## 2. Broker Commission Profiles & Depository (DP) Charges
Northstar models verified Indian broker schedules:

### 1. Angel One (SmartAPI / iTrade Prime)
- **Delivery Brokerage:** ₹0 (Zero brokerage on equity delivery).
- **Intraday Brokerage:** ₹20 or 0.25% (whichever lower).
- **DP Charges:** ₹20 + 18% GST = **₹23.60** (levied on SELL delivery only).

### 2. Zerodha (Kite)
- **Delivery Brokerage:** ₹0 (Zero brokerage on equity delivery).
- **Intraday Brokerage:** ₹20 or 0.03% (whichever lower).
- **DP Charges:** ₹13.50 + 18% GST = **₹15.93** (levied on SELL delivery only).

### 3. Dhan
- **Delivery Brokerage:** ₹0 (Zero brokerage on equity delivery).
- **Intraday Brokerage:** ₹20 or 0.03% (whichever lower).
- **DP Charges:** ₹12.50 + 18% GST = **₹14.75** (levied on SELL delivery only).

### 4. Fyers
- **Delivery Brokerage:** ₹0 (Zero brokerage on equity delivery).
- **Intraday Brokerage:** ₹20 or 0.03% (whichever lower).
- **DP Charges:** ₹12.50 + 18% GST = **₹14.75** (levied on SELL delivery only).

### 5. Flat Zero
- Pure statutory baseline without broker commission or DP charges.

---

## 3. Breakeven Exit Formula
Because delivery sell trades incur both variable taxes (STT 0.10%, NSE txn 0.00297%, SEBI 0.0001%, GST) and fixed charges (DP fee + brokerage), the breakeven exit price is calculated as:

$$\text{Breakeven Price} = \frac{\text{Net Buy Inflow} + \text{Fixed Sell Costs}}{Q \times (1 - \text{Variable Sell Tax Rate})}$$

This formula guarantees that simulated strategies only trigger exits when net after-tax profits are positive.
