# ==============================================================================
# Stop Local Specialist Financial Model Server
# ==============================================================================

Write-Host "Stopping Local Financial AI Model Server..." -ForegroundColor Yellow

$pidFile = "config/ai_server.pid"
if (Test-Path $pidFile) {
    $procId = Get-Content $pidFile
    try {
        Stop-Process -Id $procId -Force -ErrorAction Stop
        Write-Host "✓ Stopped process PID $procId" -ForegroundColor Green
    } catch {
        Write-Host "- Process PID $procId was not active." -ForegroundColor DarkGray
    }
    Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
}

# Also terminate any running llama-server instances if present
$llamaProcs = Get-Process -Name "llama-server" -ErrorAction SilentlyContinue
if ($llamaProcs) {
    $llamaProcs | Stop-Process -Force
    Write-Host "✓ Terminated active llama-server process." -ForegroundColor Green
}

Write-Host "Local Financial AI Model Server stopped." -ForegroundColor Green
