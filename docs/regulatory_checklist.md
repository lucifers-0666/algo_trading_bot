# Regulatory Boundaries & Indian Algorithmic Compliance Checklist

**Date:** 2026-11-04  
**Applicability:** Indian Equity Markets (SEBI & NSE/BSE Regulations)  
**System Status:** **RESEARCH & PAPER TRADING ONLY — LIVE ORDER ROUTING STRICTLY EXCLUDED**

---

## 1. Regulatory Context

The Securities and Exchange Board of India (SEBI) and Indian exchanges (NSE/BSE) maintain stringent regulations regarding algorithmic trading:
- **SEBI Circular SEBI/HO/MRD/DP/CIR/P/2018/62:** Prescribes guidelines on algorithmic trading, testing of algorithms, order-to-trade ratios (OTR), and risk controls.
- **Retail Algorithmic Frameworks & Exchange Empanelment:** In recent consultation papers and exchange circulars, automated strategies interacting directly with broker order APIs are classified into client-side direct APIs vs. empanelled third-party platforms. Brokers require certified algorithmic approvals for automated systems that route orders without direct human intervention per trade.
- **Paper Trading Exemption:** Standalone research systems, backtesting engines, and simulated paper-trading tools that **do not transmit electronic orders to any exchange or broker gateway** are not classified as regulated live algos. However, the boundary must be absolute and auditable.

---

## 2. Platform Compliance Controls

| Regulation / Standard | Platform Implementation | Verification Status |
| :--- | :--- | :--- |
| **No Live Order Routing** | Zero broker execution APIs (Zerodha Kite, Upstox, Angel One, Groww, etc.) are included in the codebase. All orders execute in an isolated virtual simulator. | **Enforced (100% Isolated)** |
| **No Demat Account Linkage** | System accepts no broker API keys, API secrets, or TOTP secrets for order routing. | **Enforced** |
| **Risk Control Guardrails** | Pre-trade risk controls (order size limit, max open positions, daily loss kill switch) are implemented in code at the simulation boundary. | **Enforced** |
| **Audit Trail & Idempotency** | Every simulated signal, risk evaluation, and order fill is immutably written to SQLite ledger with timestamps in `Asia/Kolkata`. | **Enforced** |
| **Order-to-Trade (OTR) Safeguards** | Even in paper trading, the engine prevents high-frequency looping, spamming, or duplicate order placement within a 60-second window. | **Enforced** |

---

## 3. Checklist for Any Future Live Execution Consideration

Should a user ever decide to transition from paper trading to live trading in a separate, dedicated project:
1. [ ] Consult legal and compliance advisors regarding current SEBI regulations.
2. [ ] Identify a broker that offers an approved client-level API (e.g., Zerodha Kite Connect, Angel SmartAPI, Upstox Developer).
3. [ ] Obtain written broker approval/algo registration if required for the specific execution model.
4. [ ] Ensure infrastructure complies with static IP, audit logging, and latency requirements.
5. [ ] Pass mandatory exchange algo conformance testing in the broker's sandbox environment.
6. [ ] Implement two-factor authentication (TOTP) and session token expiration handling according to exchange mandates.
7. [ ] Implement emergency manual square-off controls accessible at all times during trading hours.
