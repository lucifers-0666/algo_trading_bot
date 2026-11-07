param(
    [string]$TaskName = "Northstar EOD Market Analysis",
    [string]$StartTime = "16:40"
)

$ErrorActionPreference = "Stop"
$runner = Join-Path $PSScriptRoot "run_eod_analysis.ps1"
if (-not (Test-Path $runner)) { throw "EOD runner not found: $runner" }

$quote = [char]34
$taskCommand = "powershell.exe -NoProfile -ExecutionPolicy Bypass -File $quote$runner$quote"
& schtasks.exe /Create /SC WEEKLY /D MON,TUE,WED,THU,FRI /TN $TaskName /TR $taskCommand /ST $StartTime /RU $env:USERNAME /IT /F
if ($LASTEXITCODE -ne 0) {
    throw "Task Scheduler registration failed with exit code $LASTEXITCODE."
}

Write-Host "Registered '$TaskName' for weekdays at $StartTime local time."
Write-Host "The user session and FastAPI service must be running; data finalization is validated by the API."
Write-Host "To remove: schtasks.exe /Delete /TN $TaskName /F"
