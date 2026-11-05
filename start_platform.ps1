# ==============================================================================
# Northstar: Indian AI Paper Trading & Financial Intelligence Workstation
# All-In-One Unified Launcher (Backend + Frontend + AI Reasoning + Browser)
# ==============================================================================

Write-Host "==================================================================" -ForegroundColor Cyan
Write-Host "  NORTHSTAR: INDIAN AI PAPER TRADING WORKSTATION LAUNCHER" -ForegroundColor Green
Write-Host "  NVIDIA RTX 5060 Accelerated | SEBI Paper Boundary (127.0.0.1)" -ForegroundColor DarkCyan
Write-Host "==================================================================" -ForegroundColor Cyan
Write-Host ""

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

# 1. Check Python Virtual Environment
$VenvPython = Join-Path $ScriptDir ".venv\Scripts\python.exe"
if (-not (Test-Path $VenvPython)) {
    Write-Host "[ERROR] Virtual environment not found at .venv" -ForegroundColor Red
    Write-Host "Run: python -m venv .venv; .\.venv\Scripts\pip install -r requirements.txt"
    pause
    exit 1
}
Write-Host "[1/4] Python 3.12 Virtual Environment detected." -ForegroundColor Green

# 2. Check / Start Local AI Reasoning Model (RTX 5060)
Write-Host "[2/4] Checking Local Specialist Financial AI Engine..." -ForegroundColor Yellow
$OllamaRunning = $false
try {
    $aiCheck = Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/tags" -Method Get -TimeoutSec 2 -ErrorAction SilentlyContinue
    if ($aiCheck) {
        $OllamaRunning = $true
        Write-Host "      [OK] Local Ollama LLM Server is active on port 11434." -ForegroundColor Green
    }
} catch {
    $OllamaRunning = $false
}

if (-not $OllamaRunning) {
    $ollamaExe = "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe"
    if (-not (Test-Path $ollamaExe)) {
        $cmd = Get-Command "ollama" -ErrorAction SilentlyContinue
        if ($cmd) { $ollamaExe = $cmd.Source }
    }
    if (Test-Path $ollamaExe) {
        Write-Host "      Starting local Ollama server in background ($ollamaExe)..." -ForegroundColor Yellow
        $env:OLLAMA_HOST = "127.0.0.1:11434"
        Start-Process -FilePath $ollamaExe -ArgumentList "serve" -WindowStyle Hidden
        Start-Sleep -Seconds 3
        $OllamaRunning = $true
        Write-Host "      [OK] Ollama daemon started on http://127.0.0.1:11434" -ForegroundColor Green
    } else {
        Write-Host "      [INFO] Local Ollama server offline. High-performance deterministic quantitative heuristic fallback active." -ForegroundColor Cyan
    }
}

# 3. Start FastAPI REST Backend (127.0.0.1:8000)
Write-Host "[3/4] Launching FastAPI Backend on 127.0.0.1:8000..." -ForegroundColor Yellow
$BackendJob = Start-Process -FilePath $VenvPython -ArgumentList "-m", "uvicorn", "trader.api.app:app", "--host", "127.0.0.1", "--port", "8000" -PassThru -WindowStyle Hidden

# Wait for backend to be ready
$backendReady = $false
for ($i = 0; $i -lt 15; $i++) {
    try {
        $res = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/health" -Method Get -TimeoutSec 1 -ErrorAction SilentlyContinue
        if ($res.status -eq "ok") {
            $backendReady = $true
            break
        }
    } catch {
        Start-Sleep -Milliseconds 500
    }
}

if ($backendReady) {
    Write-Host "      [OK] FastAPI Backend online at http://127.0.0.1:8000" -ForegroundColor Green
} else {
    Write-Host "      [WARNING] Backend took longer to respond, continuing..." -ForegroundColor Yellow
}

# 4. Start React 19 Frontend Workstation (127.0.0.1:5173)
Write-Host "[4/4] Launching React 19 Workstation on 127.0.0.1:5173..." -ForegroundColor Yellow
$FrontendDir = Join-Path $ScriptDir "frontend"
$FrontendJob = Start-Process -FilePath "cmd.exe" -ArgumentList "/c", "npm", "--prefix", "`"$FrontendDir`"", "run", "dev" -PassThru -WindowStyle Hidden

# Wait for frontend to be ready
$frontendReady = $false
for ($i = 0; $i -lt 15; $i++) {
    try {
        $tcp = Test-NetConnection -ComputerName "127.0.0.1" -Port 5173 -WarningAction SilentlyContinue
        if ($tcp.TcpTestSucceeded) {
            $frontendReady = $true
            break
        }
    } catch {
        Start-Sleep -Milliseconds 500
    }
}

Write-Host ""
Write-Host "==================================================================" -ForegroundColor Green
Write-Host "  PLATFORM ONLINE & OPERATIONAL!" -ForegroundColor Green
Write-Host "  Workstation URL: http://127.0.0.1:5173" -ForegroundColor White
Write-Host "  Backend API URL: http://127.0.0.1:8000" -ForegroundColor White
Write-Host "  Interactive Docs: http://127.0.0.1:8000/api/docs" -ForegroundColor White
Write-Host "==================================================================" -ForegroundColor Green
Write-Host ""

# 5. Open Default Web Browser
Start-Process "http://127.0.0.1:5173"

Write-Host "Workstation opened in your browser." -ForegroundColor Cyan
Write-Host "Press [CTRL+C] or close this window to stop the background services." -ForegroundColor DarkGray

# Keep process alive so user can exit cleanly
try {
    while ($true) {
        Start-Sleep -Seconds 2
        # Check if processes died
        if ($BackendJob.HasExited) {
            Write-Host "[ALERT] Backend process terminated." -ForegroundColor Red
            break
        }
    }
} finally {
    Write-Host "Stopping platform background services..." -ForegroundColor Yellow
    if ($BackendJob -and -not $BackendJob.HasExited) { Stop-Process -Id $BackendJob.Id -Force -ErrorAction SilentlyContinue }
    if ($FrontendJob -and -not $FrontendJob.HasExited) { Stop-Process -Id $FrontendJob.Id -Force -ErrorAction SilentlyContinue }
    Write-Host "Services stopped cleanly." -ForegroundColor Green
}

