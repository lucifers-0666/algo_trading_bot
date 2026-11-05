# Financial AI Security, Privacy & Safety Architecture

**Project:** Northstar — Indian Equity AI Quantitative Research & Paper-Trading Platform  
**Scope:** AI Inference Safety, Zero Data Egress, Quantitative Sandboxing & Prompt Guardrails  

---

## 1. Network Isolation & Zero Egress Mandate

Northstar enforces a strict local computing perimeter:

1. **Localhost Binding Only:**
   - The AI runtime listens strictly on `127.0.0.1:11434`.
   - External network interfaces (0.0.0.0) are disabled.
   - All REST requests originating from `src/trader/ai/` connect directly to loopback.
2. **Zero Cloud LLM Fallbacks:**
   - No requests, prompts, portfolio balances, or trade setups are transmitted to third-party proprietary APIs (OpenAI, Anthropic, Google Cloud).
   - If the local model is offline, the system safely falls back to local deterministic rule-based algorithms (`EventClassifier` and quantitative metrics), NEVER to an external network service.
3. **Telemetry & Log Scrubbing:**
   - Model inference logs are stored locally under `d:\Algo trading\logs\`.
   - Simulated portfolio cash (starting ₹10,000) and order logs remain strictly on local disk.

---

## 2. Quantitative Engine Supremacy & Sandboxing

A critical vulnerability in AI trading systems is giving generative models write or execution authority over orders. Northstar enforces an architectural separation:

```mermaid
flowchart LR
    subgraph AI["Qualitative AI Domain (Fin-R1)"]
        direction TB
        F1[Corporate News Analysis]
        F2[Financial Statement Logic]
        F3[Qualitative Setup Thesis]
    end

    subgraph Sandbox["Isolation Boundary"]
        Barrier["Read-Only Qualitative Gateway\n(Strict Schema Validation)"]
    end

    subgraph Quant["Quantitative Trading Engine (Deterministic Python)"]
        direction TB
        Q1[Live NSE Tick & Bar Feeds]
        Q2[Indicator Calculations (ATR, RSI, SMA)]
        Q3[Capital & Position Sizing (Fixed ₹10k Cap)]
        Q4[Stop-Loss & Target Rules]
        Q5[Virtual Paper Order Execution]
    end

    AI --> Sandbox
    Sandbox --> Quant
```

### Inviolable Rules
1. **No Direct Execution:** Fin-R1 can never submit an order, modify an order state, cancel a stop-loss, or override risk rules.
2. **Deterministic Pricing:** Trade entry prices, stop-loss calculations, and target projections are strictly calculated by Python formulas.
3. **Human In The Loop:** Paper-trade setups require human approval in the Northstar UI workstation before virtual execution.

---

## 3. Prompt Injection & Hallucination Mitigations

1. **Greedy Sampling (`temperature=0.1`):** Limits stochastic divergence and eliminates creative hallucinations.
2. **Strict System Prompt Framing:** The system prompt explicitly limits the AI's role to objective financial analysis and capital risk enumeration.
3. **Pydantic Schema Validation:** All model outputs are parsed into rigid Pydantic models (`NewsAnalysisResponse`, `SignalExplanationResponse`, `StockDossierResponse`). If the model fails to return valid JSON conforming to the schema, the client catches the error and activates the deterministic fallback.

