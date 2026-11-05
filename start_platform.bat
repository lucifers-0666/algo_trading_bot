@echo off
title Northstar: Indian AI Paper Trading Workstation
echo ==================================================================
echo   NORTHSTAR: INDIAN AI PAPER TRADING WORKSTATION LAUNCHER
echo   NVIDIA RTX 5060 Accelerated ^| SEBI Paper Boundary (127.0.0.1)
echo ==================================================================
echo.

cd /d "%~dp0"

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start_platform.ps1"

pause

