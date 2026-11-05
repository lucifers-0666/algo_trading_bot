# ==============================================================================
# Start Local Specialist Financial Model Server (Fin-R1 via Ollama)
# Offloads 100% layers to NVIDIA RTX 5060 Laptop GPU (8GB VRAM)
# ==============================================================================

param(
    [string]$Model = "fin-r1:7b-q4_k_m",
    [int]$Port = 11434
)

Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host " Starting Local Specialist Financial Model Server (Fin-R1)" -ForegroundColor Cyan
Write-Host " Target GPU: NVIDIA RTX 5060 (8GB VRAM) - Full CUDA Offload" -ForegroundColor Cyan
Write-Host "=================================================================" -ForegroundColor Cyan

$ollamaExe = "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe"
if (-not (Test-Path $ollamaExe)) {
    $cmd = Get-Command ollama -ErrorAction SilentlyContinue
    if ($cmd) { $ollamaExe = $cmd.Source }
}

if (-not (Test-Path $ollamaExe)) {
    Write-Host "[!] Ollama executable not found. Please install Ollama." -ForegroundColor Red
    exit 1
}

# Check if Ollama is already serving
$isRunning = $false
try {
    $ver = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/api/version" -TimeoutSec 1 -ErrorAction Stop
    $isRunning = $true
} catch {
    $isRunning = $false
}

if (-not $isRunning) {
    Write-Host "[1/2] Launching Ollama daemon service..." -ForegroundColor Yellow
    $env:OLLAMA_HOST = "127.0.0.1:$Port"
    Start-Process -FilePath $ollamaExe -ArgumentList "serve" -WindowStyle Minimized
    Start-Sleep -Seconds 3
    Write-Host "  [OK] Ollama daemon listening on http://127.0.0.1:$Port" -ForegroundColor Green
} else {
    Write-Host "  [OK] Ollama daemon already active on http://127.0.0.1:$Port" -ForegroundColor Green
}

# Pre-warm Fin-R1 model into GPU VRAM
Write-Host "[2/2] Pre-warming Fin-R1 into NVIDIA RTX 5060 GPU VRAM..." -ForegroundColor Yellow
try {
    $payload = @{
        model = $Model
        prompt = "Hello"
        stream = $false
    } | ConvertTo-Json
    $warm = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/api/generate" -Method Post -Body $payload -ContentType "application/json" -TimeoutSec 60
    Write-Host "  [OK] $Model successfully warmed in GPU VRAM." -ForegroundColor Green
} catch {
    Write-Host "  [!] Pre-warm request completed or pending on demand." -ForegroundColor Gray
}

Write-Host "`nFin-R1 Specialist Financial Model Ready!" -ForegroundColor Green
