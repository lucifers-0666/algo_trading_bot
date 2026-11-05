# Fin-R1 Financial Reasoning & Capabilities Evaluation Suite

**Project:** Northstar — Indian Equity AI Quantitative Research & Paper-Trading Platform  
**Model Under Test:** `fin-r1:7b-q4_k_m` (GGUF Q4_K_M, 7B parameters)  
**Host Environment:** Windows 11, NVIDIA GeForce RTX 5060 Laptop GPU (8.15 GB VRAM)  
**Inference Engine:** Ollama v0.40.14 with CUDA 13.1  

---

## 1. Evaluation Methodology

The financial reasoning evaluation suite assesses whether `Fin-R1` fulfills the institutional standards of a specialist financial AI model across 6 mission-critical domains:

1. **Test 1: Corporate Financial Statement & Capital Structure Reasoning**
   - *Prompt:* Analyze a firm with EBITDA ₹500 Cr, Total Debt ₹2,000 Cr, Cash ₹200 Cr, and Interest Expense ₹180 Cr. Calculate Net Debt, Debt-to-EBITDA leverage, and Interest Coverage Ratio. Interpret solvency risk for cyclical industries.
2. **Test 2: Corporate Earnings & Management Guidance Interpretation**
   - *Prompt:* Analyze disclosure: "Q3 Revenue grew 18% YoY to ₹4,200 Cr, but Operating Margin contracted 240 bps to 14.1% due to surging raw material input costs. FY guidance revised downward from 22% to 15%." Determine sentiment, key drivers, risk factors, and market action.
3. **Test 3: Technical Swing-Trading Setup Explanation**
   - *Prompt:* Explain a swing trade setup for INFY: Entry ₹1,620.00, Stop Loss ₹1,570.00 (Risk: ₹50.00/sh), Target ₹1,745.00 (Reward: ₹125.00/sh), RSI(14)=58.2, Price above 20 SMA (₹1,595) and 50 SMA (₹1,560). Calculate Risk/Reward ratio and assess viability.
4. **Test 4: Financial Risk Factor & Governance Guardrails**
   - *Prompt:* Identify financial distress warning signs for a mid-cap manufacturing stock with 68% promoter share pledge, negative operating cash flow for 3 consecutive quarters, and auditor resignations citing lack of disclosure.
5. **Test 5: Indian Equity Market Realities & Statutory Friction**
   - *Prompt:* Detail the execution friction for an Indian swing-trade (NSE cash equity delivery) starting with ₹10,000 capital. Include Securities Transaction Tax (STT 0.1%), exchange charges, SEBI turnover fees, stamp duty, GST, and circuit filter risks (5%/10%/20%).
6. **Test 6: Invalidation of Defective Setups (Fail-Closed Check)**
   - *Prompt:* Evaluate setup: Entry ₹850, Stop Loss ₹820 (Risk ₹30), Target ₹865 (Reward ₹15), scheduled quarterly earnings announcement tomorrow morning. What is the verdict and risk assessment?

---

## 2. Quantitative Engine vs Qualitative Reasoning Boundary Verification

| Test Dimension | Quantitative Engine Responsibility | Fin-R1 Responsibility |
| :--- | :--- | :--- |
| **Price & Levels** | Exact float values from exchange feeds | Contextual narrative on price levels |
| **Capital Allocation** | Hard limits (₹10,000 total virtual capital, max 20% position size) | Discussion of diversification principles |
| **Execution Decision** | Automated paper state machine (Pending -> Filled) | Recommendation of `APPROVED_FOR_PAPER` or `REQUIRES_MANUAL_REVIEW` |
| **Statutory Slippage** | Formulaic calculation of STT + GST + brokerage | Explanation of frictional impact on net expectancy |
