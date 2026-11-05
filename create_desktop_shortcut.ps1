# Creates a convenient Desktop Shortcut for Northstar Trading Workstation
$WshShell = New-Object -ComObject WScript.Shell
$DesktopPath = [Environment]::GetFolderPath("Desktop")
$ShortcutPath = Join-Path $DesktopPath "Northstar AI Trading Workstation.lnk"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$TargetBat = Join-Path $ScriptDir "start_platform.bat"

$Shortcut = $WshShell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = $TargetBat
$Shortcut.WorkingDirectory = $ScriptDir
$Shortcut.Description = "Northstar: Indian AI Paper Trading & Financial Intelligence Workstation"
$Shortcut.IconLocation = "shell32.dll,243" # Trading / graph icon
$Shortcut.Save()

Write-Host "[OK] Desktop shortcut created at: $ShortcutPath" -ForegroundColor Green
