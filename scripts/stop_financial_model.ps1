# ==============================================================================
# Stop Local Specialist Financial Model Server (Fin-R1 / Ollama)
# ==============================================================================

Write-Host "Stopping Local Financial AI Model Server..." -ForegroundColor Yellow

$ollamaExe = "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe"
if (Test-Path $ollamaExe) {
    # Unload model from VRAM by setting keep_alive to 0
    try {
        $payload = @{
            model = "fin-r1:7b-q4_k_m"
            keep_alive = 0
        } | ConvertTo-Json
        Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/generate" -Method Post -Body $payload -ContentType "application/json" -TimeoutSec 5 -ErrorAction SilentlyContinue | Out-Null
        Write-Host "  [OK] Unloaded fin-r1 from GPU VRAM." -ForegroundColor Green
    } catch {}
}

# Stop Ollama processes if desired
Get-Process -Name "ollama*" -ErrorAction SilentlyContinue | ForEach-Object {
    Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
    Write-Host "  [OK] Stopped Ollama process PID $($_.Id)" -ForegroundColor Green
}

Write-Host "Local Financial AI Model Server stopped." -ForegroundColor Green
