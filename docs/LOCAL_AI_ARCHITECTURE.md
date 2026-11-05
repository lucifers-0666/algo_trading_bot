# Local Financial AI Architecture & Prompt Engineering — Northstar

## 1. Architectural Pipeline

The Northstar Local AI reasoning engine (`src/trader/ai/inference_client.py`) is engineered to process unstructured financial disclosures, corporate announcements, and regulatory filings locally without sending proprietary data to third-party cloud APIs.

```
+-----------------------------------------------------------------------------------+
|                            Incoming Unstructured Data                             |
|  - NSE Corporate Announcements (BSE/NSE XBRL filings)                             |
|  - Financial News Wires (GDELT / RSS Feeds)                                       |
|  - Strategy Signal Context (Technical Indicators, Regime, Risk Parameters)        |
+------------------------------------------+----------------------------------------+
                                           |
                                           v
                       +---------------------------------------+
                       | Event Classifier & Entity Extractor   |
                       | (src/trader/intelligence/classifier.py|
                       +-------------------+-------------------+
                                           |
                                           v
                       +---------------------------------------+
                       | Local Financial AI Client             |
                       | (src/trader/ai/inference_client.py)   |
                       +-------------------+-------------------+
                                           |
                    +----------------------+----------------------+
                    |                                             |
           (If LLM Server Online)                      (If LLM Server Offline)
                    v                                             v
  +-----------------------------------+         +-----------------------------------+
  | Local GGUF Model                  |         | Deterministic Quantitative Engine |
  | (deepseek-r1:7b on RTX 5060)      |         | - Heuristic Sentiment Scoring     |
  | - Structured JSON Prompting       |         | - Regulatory Clause Regex Engine  |
  | - Few-Shot Financial Priming      |         | - Rule-Based Signal Explainer     |
  +-----------------+-----------------+         +-----------------+-----------------+
                    |                                             |
                    +----------------------+----------------------+
                                           |
                                           v
                       +---------------------------------------+
                       | Structured Pydantic Response Validation|
                       | - NewsAnalysisResponse                |
                       | - SignalExplanationResponse           |
                       | - StockDossierResponse                |
                       +-------------------+-------------------+
                                           |
                                           v
                       +---------------------------------------+
                       | Decision Support Engine Gatekeeper    |
                       | (src/trader/decision/decision_engine) |
                       +---------------------------------------+
```

---

## 2. Structured Prompt Templates

The client enforces strict JSON schema completion using system instructions tailored to Indian financial terminology (SEBI, RBI, EBITDA, Capex, PAT, Q-o-Q, Y-o-Y, Promoters, FII/DII):

### 2.1 News & Disclosure Prompt Template
```
You are a senior Indian equity research analyst and forensic accountant.
Analyze the following market headline/disclosure for {symbol}:
"{headline}"

Evaluate the catalyst impact on the company's fundamentals and stock price.
Respond strictly with valid JSON conforming to this schema:
{
  "sentiment_score": float between -1.0 (extremely bearish) and 1.0 (extremely bullish),
  "sentiment_label": "BULLISH" | "BEARISH" | "NEUTRAL",
  "confidence": float between 0.0 and 1.0,
  "suggested_action": "FAVORABLE_FOR_ENTRY" | "AVOID" | "HEDGE" | "NEUTRAL_WATCH",
  "key_drivers": [string],
  "risk_factors": [string],
  "reasoning": string
}
```

### 2.2 Explainable Signal Dossier Template
```
Explain this quantitative swing trade setup for {symbol}:
- Strategy: {strategy_name}
- Signal Action: {side} at INR {price}
- Stop Loss: INR {stop_loss}
- Target: INR {target}
- Market Regime: {regime}
- RSI(14): {rsi} | SMA20: {sma20} | SMA50: {sma50}

Explain the quantitative rationale, primary catalysts, invalidate conditions, and key risks.
Return valid JSON.
```

---

## 3. Privacy, Security & Data Sovereignty

1. **Zero External Data Egress:** All inferencing occurs on `127.0.0.1:11434` or `127.0.0.1:8080`. Portfolio positions, cash balance, and trade execution intentions never leave the local machine.
2. **Deterministic Fallback Guarantee:** If the local model server is killed or runs out of memory, the system seamlessly transitions to deterministic rule-based analysis without raising unhandled exceptions or stalling trading operations.
3. **Pydantic Validation Guard:** Every response generated by the local LLM is parsed and validated by strict Pydantic V2 models (`NewsAnalysisResponse`, `SignalExplanationResponse`). Any ill-formed response triggers immediate deterministic fallback.
