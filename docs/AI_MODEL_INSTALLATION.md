# Specialist Financial AI Installation & Verification Guide

**Project:** Northstar — Indian Equity AI Quantitative Research & Paper-Trading Platform  
**Target Platform:** Windows 11 (x64) with NVIDIA GeForce RTX 5060 Laptop GPU  
**Model Runtime:** Ollama v0.40.14 + CUDA 13.1 Compute Engine  
**Model Checkpoint:** Fin-R1 7B Q4_K_M GGUF  

---

## 1. Prerequisites Verification

Before starting, verify machine readiness using the hardware probe:
```powershell
nvidia-smi
```
Expected output:
- **GPU:** NVIDIA GeForce RTX 5060 Laptop GPU
- **Driver:** >= 550.0 (Installed: 592.82)
- **CUDA Version:** >= 12.0 (Detected: 13.1)
- **VRAM:** 8,151 MiB

---

## 2. Step-by-Step Installation Procedure

### Step 1: Install Local Inference Runtime (Ollama)
If Ollama is not already present:
```powershell
# Download official installer from Ollama GitHub releases
curl.exe -L -o "D:\OllamaSetup.exe" "https://github.com/ollama/ollama/releases/download/v0.40.14/OllamaSetup.exe"
# Execute silent installation
& "D:\OllamaSetup.exe" /SILENT
```
Ollama installs to:
`%LOCALAPPDATA%\Programs\Ollama\ollama.exe`

### Step 2: Start Background Service
```powershell
$env:OLLAMA_HOST = "127.0.0.1:11434"
& "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe" serve
```
Verify endpoint connectivity:
```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/version"
```

### Step 3: Fetch Fin-R1 GGUF Checkpoint
Download the finance-specialized GGUF directly from Hugging Face:
```powershell
curl.exe -L -C - -o "D:\Algo trading\models\saved\Fin-R1-q4_k_m.gguf" "https://huggingface.co/Mungert/Fin-R1-GGUF/resolve/main/Fin-R1-q4_k_m.gguf"
```

### Step 4: Register Model in Ollama via Modelfile
Run:
```powershell
& "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe" create fin-r1:7b-q4_k_m -f "D:\Algo trading\models\Modelfile.fin-r1"
```

### Step 5: Verify Model GPU Offload
Execute a quick financial test inference:
```powershell
& "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe" run fin-r1:7b-q4_k_m "Explain how debt-to-equity ratio affects financial leverage for capital goods companies."
```
While running, check GPU status:
```powershell
nvidia-smi
& "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe" ps
```
The output confirms `100% GPU offload` (`33/33 layers on CUDA0`), allocating ~4.8 GB VRAM.

---

## 3. Automated Lifecycle Scripts

Northstar provides turnkey scripts under `scripts/`:
- `scripts\start_financial_model.ps1`: Starts Ollama background daemon and pre-warms Fin-R1.
- `scripts\stop_financial_model.ps1`: Gracefully stops the Ollama process and unloads VRAM.
- `scripts\setup_financial_model.ps1`: Automated end-to-end download and setup script.
- `scripts\verify_financial_model.ps1`: Comprehensive 6-test financial reasoning and GPU offload verification suite.
