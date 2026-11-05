# Defensive Security Audit & Broker Isolation Verification — Northstar

## 1. Security Baseline & Threat Modeling

Northstar is designed from the ground up as a secure, personal quantitative research and virtual paper-trading workstation. It enforces defensive software engineering principles to guarantee that real capital and brokerage credentials can never be compromised.

---

## 2. Broker Isolation & Read-Only Boundaries

### 2.1 Complete Absence of Live Broker Routing
- **Zero Real Demat Endpoints:** The FastAPI routing table contains zero routes capable of placing, modifying, or canceling orders with live brokers (Zerodha Kite, Groww, AngelOne, Upstox, Dhan live trading).
- **Virtual Paper Broker Isolation:** All simulated executions pass through `VirtualPaperBroker` (`src/trader/paper/broker.py`), which manipulates an in-memory and SQLite-backed virtual ledger starting with ₹10,000 virtual capital.
- **DhanHQ Read-Only Compliance:** The DhanHQ adapter (`src/trader/providers/dhan_adapter.py`) uses DhanHQ's data APIs exclusively for quotes, depth, and historical candles. Live order management endpoints (`/orders`, `/positions`, `/holdings`) are not imported, declared, or implemented.

---

## 3. Network & Transport Security

### 3.1 Strict Localhost Binding
- Both the FastAPI backend and React frontend are configured to bind exclusively to `127.0.0.1` (localhost).
- The servers do not listen on `0.0.0.0` or open public gateway tunnels without explicit operator configuration.
- Local CORS policies in `app.py` are locked down to `http://127.0.0.1:5173`, `http://localhost:5173`, and local network aliases.

---

## 4. Secrets Management & Repository Hygiene

- **`.gitignore` Enforcements:**
  - `.env`, `.env.local`, and all private configuration files are strictly ignored.
  - SQLite database files (`*.db`, `*.sqlite`) are barred from repository commits.
  - Machine-specific virtual environments (`.venv/`, `env/`) and Playwright MCP caches are excluded.
- **Example Template Integrity:** `config/app.example.yaml` and `config/risk.example.yaml` contain sanitized placeholder credentials only.

---

## 5. Fail-Closed Emergency Controls

- **Hardware & Software Kill Switch (`src/trader/risk/kill_switch.py`):**
  - Maintains persistent state on disk in `config/kill_switch.state`.
  - When tripped (either manually via UI or automatically via circuit breakers), all simulated buying is immediately halted.
  - If the kill switch state file is missing or unreadable, the risk manager **fails closed** (disallowing all new trades until verified).
