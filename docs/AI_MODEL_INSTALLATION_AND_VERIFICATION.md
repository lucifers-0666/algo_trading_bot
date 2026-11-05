# Local Financial AI Installation, GPU Configuration & Verification Guide

## 1. Hardware Architecture & Environment Specification

Northstar is optimized for local high-performance inferencing on Windows 11 hardware:

- **Host Processor:** AMD Ryzen 9 8940HX (16 Cores, 32 Threads)
- **Dedicated Graphics (GPU):** NVIDIA GeForce RTX 5060 Laptop GPU (8GB GDDR6 VRAM, CUDA 13.1, Driver 592.82)
- **System Memory:** 24 GB DDR5 RAM
- **Storage Subsystem:** High-speed NVMe SSD (200+ GB available headroom)
- **Local Runtime Target:** Ollama / llama.cpp server with OpenAI-compatible REST API

---

## 2. Model Selection & Quantization Strategy

To maximize financial reasoning while fitting comfortably within the 8GB VRAM envelope of the RTX 5060:

| Model ID | Base Architecture | Quantization | VRAM Usage | Context Window | Primary Capability |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `deepseek-r1:7b` | Qwen 2.5 7B Distill | Q4_K_M | ~4.8 GB | 8,192 tokens | Chain-of-Thought Financial Reasoning |
| `qwen2.5:7b-instruct` | Qwen 2.5 7B | Q4_K_M | ~4.6 GB | 16,384 tokens | Fast Structured JSON Extraction |
| `llama3.1:8b-instruct`| Llama 3.1 8B | Q4_K_M | ~5.1 GB | 8,192 tokens | General Financial Disclosure Analysis |
| `fingpt-7b` | Llama 2 / Mistral 7B | Q4_0 | ~4.2 GB | 4,096 tokens | Financial Sentiment Classification |

> **Recommended Production Choice:** `deepseek-r1:7b` (Q4_K_M). Fits completely in RTX 5060 VRAM, leaving ~3GB headroom for Windows desktop composition and KV cache.

---

## 3. Installation Walkthrough (Windows 11)

### Step 1: Install Ollama
Download and run the official Windows installer from:
`https://ollama.com/download/OllamaSetup.exe`

Verify installation in PowerShell:
```powershell
ollama --version
```

### Step 2: Pull the Recommended Quantized Reasoning Model
```powershell
ollama pull deepseek-r1:7b
```

### Step 3: Verify GPU Offloading
Run the model interactively and check GPU utilization using NVIDIA SMI:
```powershell
ollama run deepseek-r1:7b "Explain how a 15% increase in crude oil prices affects Asian Paints and Indian paint manufacturers."
```
In a secondary terminal:
```powershell
nvidia-smi
```
Verify that `ollama_llama_server.exe` appears in the GPU processes list and VRAM usage is ~4.8 GB.

### Step 4: Configure Environment Variables in `.env`
Update `.env` in the repository root:
```env
LOCAL_AI_BASE_URL=http://127.0.0.1:11434/v1
LOCAL_AI_MODEL=deepseek-r1:7b
```

---

## 4. Verification & Fallback Resilience Testing

Northstar provides automated end-to-end verification of the AI inference client:

1. **When Ollama is Active:**
   - Probing `/api/v1/ai/health` returns:
     ```json
     {
       "status": "ONLINE",
       "model_name": "deepseek-r1:7b",
       "provider": "Local GGUF (Ollama / llama.cpp)",
       "gpu_acceleration": true,
       "latency_ms": 142.5
     }
     ```
2. **When Ollama is Offline / Not Installed:**
   - The system automatically engages the **Deterministic Financial Quantitative Engine**.
   - Probing `/api/v1/ai/health` returns:
     ```json
     {
       "status": "STANDBY_HEURISTIC",
       "model_name": "deepseek-r1:7b (Rule-Based Fallback)",
       "provider": "Deterministic Financial Quantitative Engine",
       "gpu_acceleration": false,
       "latency_ms": 0.0
     }
     ```
   - Analysis of news and disclosures continues without interruption, utilizing keyword sentiment scoring and regex event classification.
   - **Zero Fake LLM Assertions:** The workstation UI explicitly displays `STANDBY_HEURISTIC` and never presents fabricated AI confidence metrics.
