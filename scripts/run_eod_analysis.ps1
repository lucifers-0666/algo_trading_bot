param(
    [string]$ApiBase = "http://127.0.0.1:8000/api/v1",
    [string]$UniverseCsv = "data/universe/nifty500.csv",
    [string]$UniverseVersion = "nifty500-current"
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

if (-not (Test-Path $UniverseCsv)) {
    throw "Missing point-in-time NIFTY 500 CSV: $UniverseCsv. Do not substitute the curated sample universe."
}

if ($UniverseVersion -eq "nifty500-current") {
    $fileStamp = (Get-Item $UniverseCsv).LastWriteTime.ToString("yyyyMMdd")
    $UniverseVersion = "nifty500-$fileStamp"
}

$rows = Import-Csv -Path $UniverseCsv
if (-not $rows -or -not ($rows[0].PSObject.Properties.Name -contains "symbol")) {
    throw "Universe CSV must contain a 'symbol' column."
}

$symbols = @($rows | ForEach-Object { ([string]$_.symbol).Trim().ToUpperInvariant() } |
    Where-Object { $_ -match '^[A-Z0-9&-]{1,30}$' } |
    Sort-Object -Unique)

if ($symbols.Count -lt 450 -or $symbols.Count -gt 500) {
    throw "Expected 450-500 valid constituents in the point-in-time NIFTY 500 file; found $($symbols.Count)."
}

$payload = @{
    universe_symbols = $symbols
    universe_version = $UniverseVersion
    nifty_symbol = "^NSEI"
    india_vix_symbol = "^INDIAVIX"
    sector_index_symbols = @{
        "NIFTY IT" = "^CNXIT"
        "NIFTY BANK" = "^NSEBANK"
        "NIFTY AUTO" = "^CNXAUTO"
        "NIFTY PHARMA" = "^CNXPHARMA"
        "NIFTY FMCG" = "^CNXFMCG"
        "NIFTY METAL" = "^CNXMETAL"
        "NIFTY REALTY" = "^CNXREALTY"
    }
    max_candidates = 20
    generate_ollama_narratives = $true
} | ConvertTo-Json -Depth 6

$headers = @{ "Content-Type" = "application/json" }
if ($env:NORTHSTAR_API_TOKEN) {
    $headers["Authorization"] = "Bearer $($env:NORTHSTAR_API_TOKEN)"
}

Write-Host "Running EOD analysis against $($symbols.Count) supplied constituents..."
$result = Invoke-RestMethod -Method Post -Uri "$ApiBase/eod/run" -Headers $headers -Body $payload -TimeoutSec 900
Write-Host "EOD report saved for session $($result.report.session_date)"
Write-Host "Market bias: $($result.report.bias.bias)"
Write-Host "Candidates: $($result.report.candidates.Count)"
Write-Host "Execution mode: $($result.execution_mode)"
