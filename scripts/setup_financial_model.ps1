# ==============================================================================
# Setup Financial AI Reasoning Model (NVIDIA RTX 5060 Laptop GPU / 8GB VRAM)
# Target Models: Fin-R1 / FinGPT / Qwen-2.5-7B Quantized GGUF (Q4_K_M)
# ==============================================================================

Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host " Indian AI Platform - Specialist Local Financial Model Setup" -ForegroundColor Cyan
Write-Host "=================================================================" -ForegroundColor Cyan

# 1. Hardware & System Inspection
Write-Host "`n[1/5] Inspecting Hardware and GPU acceleration..." -ForegroundColor Yellow
$gpuInfo = Get-Command nvidia-smi -ErrorAction SilentlyContinue
if ($gpuInfo) {
    Write-Host "✓ NVIDIA GPU driver detected." -ForegroundColor Green
    & nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader
} else {
    Write-Host "! nvidia-smi not in PATH. CPU inference fallback will be used if GPU is unavailable." -ForegroundColor Yellow
}

$ram = (Get-CimInstance Win32_PhysicalMemory | Measure-Object -Property Capacity -Sum).Sum / 1GB
Write-Host "✓ Total System RAM: $([math]::Round($ram, 1)) GB" -ForegroundColor Green

# 2. Disk Space Inspection
Write-Host "`n[2/5] Checking Disk Space for GGUF weights..." -ForegroundColor Yellow
$drive = Get-PSDrive -Name D -ErrorAction SilentlyContinue
if (-not $drive) { $drive = Get-PSDrive -Name C }
Write-Host "✓ Drive $($drive.Name): $([math]::Round($drive.Free / 1GB, 2)) GB free space available." -ForegroundColor Green

# 3. Directory Configuration
Write-Host "`n[3/5] Setting up model directories..." -ForegroundColor Yellow
$modelDir = "models/ai"
if (-not (Test-Path $modelDir)) {
    New-Item -ItemType Directory -Path $modelDir -Force | Out-Null
    Write-Host "✓ Created model directory: $modelDir" -ForegroundColor Green
} else {
    Write-Host "✓ Model directory exists: $modelDir" -ForegroundColor Green
}

# 4. Local Model Configuration JSON
$aiConfigFile = "config/ai_config.json"
$configContent = @"
{
  "provider": "llama.cpp_server",
  "base_url": "http://127.0.0.1:8080/v1",
  "model_name": "fin-r1-7b-q4_k_m.gguf",
  "model_path": "models/ai/fin-r1-7b-q4_k_m.gguf",
  "gpu_layers": 33,
  "context_size": 4096,
  "threads": 8,
  "vram_limit_mb": 6000
}
"@
if (-not (Test-Path "config")) { New-Item -ItemType Directory -Path "config" -Force | Out-Null }
Set-Content -Path $aiConfigFile -Value $configContent -Encoding UTF8
Write-Host "✓ Wrote local AI configuration to $aiConfigFile" -ForegroundColor Green

# 5. Instructions for Serving
Write-Host "`n[4/5] Model Execution Options:" -ForegroundColor Yellow
Write-Host "Option A (Ollama - Recommended for Windows):" -ForegroundColor White
Write-Host "  1. Install Ollama: https://ollama.com/download"
Write-Host "  2. Pull model:     ollama run qwen2.5:7b (or fin-r1)"
Write-Host "  3. Ollama runs at: http://127.0.0.1:11434/v1"

Write-Host "`nOption B (llama-server standalone with CUDA offload):" -ForegroundColor White
Write-Host "  Run: .\scripts\start_financial_model.ps1"

Write-Host "`n[5/5] Verification:" -ForegroundColor Yellow
Write-Host "  Run: .\scripts\verify_financial_model.ps1" -ForegroundColor Cyan
Write-Host "`nSetup complete!" -ForegroundColor Green
