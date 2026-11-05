# Local AI Machine Inspection & Hardware Baseline Audit

**Project:** Northstar — Indian Equity AI Quantitative Research & Paper-Trading Platform  
**Audit Date:** 2026-11-05  
**Platform:** Windows 11 Home (HP OMEN Gaming Laptop 16-ap0xxx)  

---

## 1. Executive Hardware & Accelerator Baseline

An exhaustive hardware audit was performed using Windows Management Instrumentation (WMI/CIM) and the NVIDIA System Management Interface (`nvidia-smi`):

| Hardware Component | Detected Specification | Verification Command | Status |
| :--- | :--- | :--- | :--- |
| **Central Processor (CPU)** | AMD Ryzen 9 8940HX with Radeon Graphics (16 Cores, 32 Logical Processors) | `Get-CimInstance Win32_Processor` | **VERIFIED** |
| **System Memory (RAM)** | 24,752,529,408 bytes (~24.0 GB DDR5 RAM) | `Get-CimInstance Win32_ComputerSystem` | **VERIFIED** |
| **Dedicated Graphics (GPU)** | NVIDIA GeForce RTX 5060 Laptop GPU (WDDM Driver-Model) | `nvidia-smi` | **VERIFIED** |
| **Total Dedicated VRAM** | 8,151 MiB (~8.0 GB GDDR6 VRAM) | `nvidia-smi` | **VERIFIED** |
| **Current VRAM Usage** | 28 MiB (8,123 MiB Free Headroom) | `nvidia-smi` | **IDLE / READY** |
| **NVIDIA Display Driver** | 592.82 | `nvidia-smi` | **VERIFIED** |
| **CUDA Driver Version** | 13.1 | `nvidia-smi` | **COMPATIBLE** |

---

## 2. Storage Subsystem & Drive Free Space

All drives have been audited using PowerShell `Get-PSDrive -PSProvider FileSystem`:

| Drive | Total Used | Available Free Space | Adequacy for Fin-R1 Q4_K_M (4.7 GB) |
| :--- | :--- | :--- | :--- |
| **C:\** (System / Userprofile) | 262.8 GB | **221.2 GB Free** | **EXCELLENT** (> 40x headroom) |
| **D:\** (Repository & Projects) | 19.6 GB | **250.9 GB Free** | **EXCELLENT** (> 50x headroom) |
| **E:\** (Data Storage) | 17.2 GB | **251.1 GB Free** | **EXCELLENT** (> 50x headroom) |

> **Storage Verdict:** Storage headroom is more than sufficient across all local volumes. Downloading the 4.7 GB quantized GGUF weights requires less than 2.5% of available space on C: or D:.

---

## 3. Local Model Runtime & Process Inspection

Audited via `Get-Command ollama` and standard installation paths:

1. **Ollama CLI in PATH:** `False` (Not found in system or user PATH).
2. **Local AppData Program Directory (`%LOCALAPPDATA%\Programs\Ollama\ollama.exe`):** `False` (Not installed).
3. **System Program Files (`C:\Program Files\Ollama\ollama.exe`):** `False` (Not installed).
4. **Existing Model Directories:**
   - `$env:USERPROFILE\.ollama\models`: `Does not exist`.
   - `D:\AI-Models`: `Does not exist`.
   - `D:\Algo trading\models\ai`: `Does not exist`.
5. **Running Model-Server Processes:**
   - Port 11434 (`http://127.0.0.1:11434`): Connection refused (Service not running).
   - Port 8080 (`http://127.0.0.1:8080`): Connection refused (No llama.cpp process).
6. **Package Manager Availability:**
   - Microsoft `winget` CLI is available (`v1.29.380`).
   - Official package `Ollama.Ollama` (v0.40.14) is discoverable in the winget repository.

---

## 4. Current AI Endpoint & Fallback Configuration

- **Current Config:** Northstar's `src/trader/ai/inference_client.py` defaults to `http://127.0.0.1:11434/v1`.
- **Active Behavior:** Because the Ollama runtime is not yet running, Northstar safely fails closed to `STANDBY_HEURISTIC` mode via its `Deterministic Financial Quantitative Engine`.
- **Target Model:** `hf.co/Mungert/Fin-R1-GGUF:Q4_K_M` (Fin-R1 7B, 4-bit Medium quantization).

---

## 5. Immediate Action Plan

1. **Phase 2:** Install official Ollama runtime (via `winget install Ollama.Ollama --accept-source-agreements --accept-package-agreements` or direct official installer from `ollama.com/download`).
2. **Phase 3:** Start the Ollama background service on `127.0.0.1:11434` and verify native API (`/api/version`) and OpenAI-compatible API (`/v1/models`).
3. **Phase 4:** Pull the verified finance-specialist model checkpoint `hf.co/Mungert/Fin-R1-GGUF:Q4_K_M`.
4. **Phase 5:** Benchmark GPU allocation on the RTX 5060 Laptop GPU (verifying that all layers offload into the 8GB VRAM).
5. **Phase 6:** Integrate with Northstar's FastAPI backend and React workstation.
