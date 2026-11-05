# ==============================================================================
# Start Local Specialist Financial Model Server (llama-server or Ollama)
# Offloads 33 layers to NVIDIA RTX 5060 Laptop GPU (8GB VRAM)
# ==============================================================================

param(
    [string]$ModelPath = "models/ai/fin-r1-7b-q4_k_m.gguf",
    [int]$GpuLayers = 33,
    [int]$Port = 8080,
    [int]$CtxSize = 4096
)

Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host " Starting Local Specialist Financial Model Server" -ForegroundColor Cyan
Write-Host " Target GPU: NVIDIA RTX 5060 (8GB VRAM) - Offload Layers: $GpuLayers" -ForegroundColor Cyan
Write-Host "=================================================================" -ForegroundColor Cyan

# Check if llama-server or ollama is installed
$llamaServer = Get-Command llama-server -ErrorAction SilentlyContinue
$ollama = Get-Command ollama -ErrorAction SilentlyContinue

if ($llamaServer -and (Test-Path $ModelPath)) {
    Write-Host "✓ Launching llama-server with CUDA offloading..." -ForegroundColor Green
    $args = @("-m", $ModelPath, "-ngl", $GpuLayers, "-c", $CtxSize, "--port", $Port, "--host", "127.0.0.1")
    $proc = Start-Process -FilePath "llama-server" -ArgumentList $args -PassThru -WindowStyle Minimized
    Set-Content -Path "config/ai_server.pid" -Value $proc.Id
    Write-Host "✓ Server started with PID $($proc.Id) on http://127.0.0.1:$Port" -ForegroundColor Green
} elseif ($ollama) {
    Write-Host "✓ Launching Ollama model server..." -ForegroundColor Green
    Start-Process -FilePath "ollama" -ArgumentList "serve" -WindowStyle Minimized
    Write-Host "✓ Ollama serving on http://127.0.0.1:11434" -ForegroundColor Green
} else {
    Write-Host "! Neither llama-server with GGUF weights nor Ollama was detected in PATH." -ForegroundColor Yellow
    Write-Host "  The platform will seamlessly run the built-in deterministic quantitative reasoning engine." -ForegroundColor Yellow
    Write-Host "  To enable full local LLM inference, install Ollama (https://ollama.com) or download llama.cpp." -ForegroundColor Cyan
}

