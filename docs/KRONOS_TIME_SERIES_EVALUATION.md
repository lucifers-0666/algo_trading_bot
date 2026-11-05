# Kronos-Base Time-Series Foundation Model Evaluation

**Project:** Northstar — Indian Equity AI Quantitative Research & Paper-Trading Platform  
**Target Architecture:** Financial Time-Series Forecasting vs Financial Language Reasoning  
**Model Under Review:** `NeoQuasar/Kronos-base` (102.3M Parameters)  
**Evaluator:** Senior Quantitative Systems Architect & Financial Machine-Learning Engineer  

---

## 1. Executive Summary

While **Fin-R1** serves as Northstar's primary financial language and qualitative reasoning model (7 Billion parameters, specializing in disclosures, corporate balance sheets, and trade thesis synthesis), the Northstar architecture was also directed to evaluate **`NeoQuasar/Kronos-base`** (102.3 Million parameters) on Hugging Face.

Kronos-base is a specialized time-series foundation model designed for sequential numerical market data rather than natural language reasoning.

---

## 2. Model Profile & Architectural Classification

| Attribute | Fin-R1 (Primary LLM) | Kronos-base (Evaluated Time-Series Model) |
| :--- | :--- | :--- |
| **Model Repository** | `Mungert/Fin-R1-GGUF` | `NeoQuasar/Kronos-base` |
| **Parameter Count** | 7,615,616,512 (~7.6B) | 102,300,000 (~102.3M) |
| **Model Modality** | Autoregressive Natural Language Transformer | Numerical Time-Series Encoder/Decoder Foundation Model |
| **Input Format** | Financial text tokens, news strings, JSON payloads | Fixed-length continuous numerical feature tensors (OHLCV vectors) |
| **Output Format** | Structured JSON, research theses, risk factor lists | Continuous forecast vectors (future expected returns, variance) |
| **Compute Engine** | Ollama / `llama.cpp` CUDA GGUF Runtime | PyTorch / Hugging Face Transformers (`transformers`, `torch`) |
| **Hardware Footprint** | ~4.68 GB VRAM | ~420 MB VRAM |

---

## 3. Comparative Evaluation & Suitability Analysis

### Strengths of Kronos-Base
1. **Lightweight Footprint:** At 102.3M parameters, Kronos-base can execute high-frequency sequential inference in under 15ms on an NVIDIA RTX 5060 GPU.
2. **Pure Numerical Focus:** Unlike language models which struggle with high-precision floating-point arithmetic across multi-step sequences, Kronos-base operates directly on standardized returns, volume deltas, and volatility tensors.
3. **Complementary Modality:** Kronos-base does not compete with Fin-R1; it operates at a completely different tier of the trading pipeline (numerical price prediction vs qualitative fundamental reasoning).

### Critical Limitations & Risks for Indian Cash Equities
1. **Lack of Explainability:** Kronos-base outputs latent vector predictions or forecasted price distributions without explanatory reasoning. In contrast, Northstar's core mandate requires explainable setups with clear rationale.
2. **Indian Market Regime Shifts:** Foundation time-series models trained on US equities or cryptocurrency tick data frequently exhibit catastrophic distribution shift when applied to Indian equity market regimes (e.g., quarterly settlement cycles, circuit band halts, RBI interest-rate shifts).
3. **Deployment Complexity:** Kronos-base requires a separate PyTorch CUDA runtime environment with specific version pins (`torch>=2.2.0`, `transformers>=4.38.0`), increasing operational surface area compared to the standardized Ollama GGUF runtime.

---

## 4. Architectural Verdict & Roadmap

1. **Current Production Baseline (Fin-R1):**
   - Fin-R1 remains the sole primary AI model for Northstar. It handles corporate disclosure sentiment, swing-trading setup explanations, risk factor analysis, and research briefings.
2. **Deterministic Quant Baseline:**
   - Numerical indicators (RSI, ATR, SMA, Supertrend) and machine learning ranking (scikit-learn / LightGBM) continue to provide the primary quantitative signals with 100% reproducibility.
3. **Future Kronos-Base Research Integration:**
   - Kronos-base is documented and staged as an optional secondary plugin in `src/trader/ml/timeseries/kronos.py` for offline research and backtesting, requiring explicit activation when PyTorch CUDA is initialized.

