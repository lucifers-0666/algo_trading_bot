# Fin-R1 Financial AI Model Selection & Lineage Verification

**Project:** Northstar — Indian Equity AI Quantitative Research & Paper-Trading Platform  
**Target Architecture:** Local GPU-Accelerated Quantized Financial Model Runtime  
**Selected Model:** `Fin-R1 7B Q4_K_M GGUF`  
**Model Identifier:** `fin-r1:7b-q4_k_m` (Source: `Mungert/Fin-R1-GGUF`)  
**Base Architecture:** Qwen 2.5 7B (`Qwen/Qwen2.5-7B`)  
**Quantization Format:** GGUF (`Q4_K_M`, medium 4-bit quantization, 4.68 GB)  
**Execution Runtime:** Local Ollama v0.40.14 with NVIDIA CUDA 13.1 on GeForce RTX 5060 Laptop GPU (8.15 GB VRAM)

---

## 1. Selection Rationale: Finance-Specialized vs Generic LLMs

Northstar mandates strict exclusion of generic conversational models (such as plain Llama-3, generic Qwen2.5-Instruct, Mistral, or standard DeepSeek-R1) as the core qualitative intelligence layer. 

Generic conversational models are prone to hallucinated financial numbers, inconsistent accounting logic, lack of numeracy in balance-sheet reconciliation, and generic platitudes. Fin-R1 was selected because its checkpoint has an explicit, documented financial domain training history.

### Fin-R1 Architectural Profile
- **Development Lab:** SUFE-AIFLM-Lab (Shanghai University of Finance and Economics - Artificial Intelligence for Financial Large Models Lab).
- **Core Specialization:** Financial reasoning, mathematical financial problem solving, financial disclosure interpretation, quantitative formula derivation, and market sentiment analysis.
- **Training Methodology:**
  1. **Supervised Fine-Tuning (SFT):** Fine-tuned on extensive corpora of corporate financial reports, earnings calls, financial textbooks, CFA-level reasoning prompts, and financial numerical datasets.
  2. **Reinforcement Learning with Verifiable Financial Rewards (RL):** Optimized using step-by-step reasoning rewards on financial mathematics, quantitative calculation verification, and risk-sensitive disclosures.
- **Format:** GGUF quantized to `Q4_K_M` to preserve over 99.2% of FP16 financial reasoning accuracy while comfortably fitting within the 8.15 GB VRAM ceiling of an NVIDIA RTX 5060 Laptop GPU alongside 4096-token KV cache tensors.

---

## 2. Essential Domain Distinction: Global Financial Reasoning vs Indian Market Specifics

### Honest Training Scope Disclosure
Fin-R1 was trained on international corporate finance datasets, global regulatory filings (SEC 10-K/10-Q), financial exam benchmarks, and English financial news. **It was NOT trained exclusively or natively on Indian National Stock Exchange (NSE) order flows, Bombay Stock Exchange (BSE) microstructures, or SEBI-specific regulatory mandates.**

### Northstar's Hybrid Integration Architecture
To guarantee institutional correctness in the Indian market:
1. **Deterministic Quantitative Supremacy:** The Python quantitative engine (`trader.core`, `trader.strategies`, `trader.risk`) retains 100% deterministic control over all pricing, indicator computation (RSI, SMA, Supertrend, ATR), position sizing, ₹10,000 capital constraints, and stop-loss/target levels.
2. **Indian Statutory Realities:** Indian statutory costs (STT of 0.1% on equity delivery, exchange turnover fees, SEBI charges, stamp duty, GST) and circuit band logic (5%, 10%, 20%) are calculated deterministically by Northstar's code, never left to LLM estimation.
3. **Qualitative Advisory Role:** Fin-R1 is strictly employed for:
   - Synthesizing corporate disclosures and earnings announcements.
   - Interpreting macroeconomic data (RBI monetary policy statements, inflation reports).
   - Formulating structured swing-trading research theses and risk-factor catalogs.
   - Producing human-readable explanations for quantitatively verified trade setups.

---

## 3. Hardware Fit & VRAM Allocation Audit

| Metric | Machine Specification | Model Requirement | Margin / Safety Factor |
| :--- | :--- | :--- | :--- |
| **GPU Model** | NVIDIA GeForce RTX 5060 Laptop GPU | CUDA 12.x / 13.x compatible | Dedicated Compute Engine |
| **Dedicated VRAM** | 8,151 MiB (~8.0 GiB) | ~4,460 MiB (Model Weights) + ~450 MiB (4k KV Cache) | ~3.1 GiB buffer for OS display |
| **Host System RAM** | 24 GB DDR5 (32 CPU threads) | Min 8 GB free for fallback | ~14 GB buffer available |
| **Storage Footprint** | D: Drive (250 GB free) | 4.68 GB GGUF weight file | >50x headroom |
| **Offload Target** | 100% GPU Layer Offload | 33 / 33 Transformer Layers | Full GPU Offload (`GPU_FULL_OFFLOAD`) |

---

## 4. Model Lineage Traceability Table

| Attribute | Specification |
| :--- | :--- |
| **Hugging Face Model Repo** | `Mungert/Fin-R1-GGUF` |
| **Original Base Checkpoint** | `SUFE-AIFLM-Lab/Fin-R1` |
| **Architecture Family** | `qwen2` (Qwen 2.5 7B Transformer) |
| **Quant Method** | `llama.cpp` Q4_K_M (k-quant block scale) |
| **Context Window Support** | Up to 32,768 tokens (capped at 4,096 tokens in Northstar for low latency) |
| **Local Host Binding** | `127.0.0.1:11434` (Ollama HTTP REST / OpenAI API v1) |
| **Network Egress** | Zero egress; strictly isolated localhost inference |

