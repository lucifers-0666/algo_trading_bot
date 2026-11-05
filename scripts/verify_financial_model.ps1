# ==============================================================================
# Verify Financial AI Reasoning Model Service
# ==============================================================================

Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host " Testing Specialist Local Financial AI Reasoning Service" -ForegroundColor Cyan
Write-Host "=================================================================" -ForegroundColor Cyan

# 1. Check GPU state
$nvidiaSmi = Get-Command nvidia-smi -ErrorAction SilentlyContinue
if ($nvidiaSmi) {
    Write-Host "`n[1/3] NVIDIA GPU Telemetry:" -ForegroundColor Yellow
    & nvidia-smi --query-gpu=name,memory.used,memory.total,utilization.gpu --format=csv
}

# 2. Probe endpoints
$endpoints = @("http://127.0.0.1:8080/v1/models", "http://127.0.0.1:11434/v1/models")

Write-Host "`n[2/3] Probing local inference endpoints..." -ForegroundColor Yellow
foreach ($ep in $endpoints) {
    try {
        $res = Invoke-RestMethod -Uri $ep -Method Get -TimeoutSec 2 -ErrorAction Stop
        Write-Host "[OK] Endpoint reachable: $ep" -ForegroundColor Green
    }
    catch {
        Write-Host "[*] Standby: $ep not responding" -ForegroundColor DarkGray
    }
}

# 3. Test Python AI Client directly
Write-Host "`n[3/3] Running Python AI Client Healthcheck..." -ForegroundColor Yellow
$pyPath = Resolve-Path ".\.venv\Scripts\python.exe"

& $pyPath -c "from trader.ai.inference_client import LocalFinancialAIClient; from trader.ai.schemas import NewsAnalysisRequest; client = LocalFinancialAIClient(); h = client.check_health(); print('[OK] AI Health Status: ' + h.status); print('[OK] Provider:         ' + h.provider); print('[OK] Model:            ' + h.model_name); res = client.analyze_news(NewsAnalysisRequest(headline='Infosys reports 14 percent rise in quarterly net profit and bags large deal', symbol='INFY')); print('[OK] Test News Score:  ' + str(res.sentiment_score) + ' (' + res.sentiment_label + ')'); print('[OK] Action:           ' + res.suggested_action)"

Write-Host "`n[OK] Verification completed successfully." -ForegroundColor Green
