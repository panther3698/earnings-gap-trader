@echo off
REM Production System Monitor
REM Real-time monitoring of the trading system

echo.
echo ================================================
echo   PRODUCTION SYSTEM MONITOR
echo ================================================
echo.

:monitor_loop
cls
echo ================================================
echo   EARNINGS GAP TRADING SYSTEM - MONITOR
echo ================================================
echo Time: %date% %time%
echo.

REM Check if system is running
tasklist /fi "imagename eq python.exe" /fo table | findstr "python.exe" >nul
if %errorlevel%==0 (
    echo Status: RUNNING ✓
    echo Process: Python trading system active
) else (
    echo Status: STOPPED ✗
    echo Process: No python trading system found
)

echo.
echo Dashboard: http://localhost:8000
echo.

REM Check log file if exists
if exist "logs\earnings_gap_trader_prod.log" (
    echo === RECENT LOG ENTRIES ===
    tail -n 10 "logs\earnings_gap_trader_prod.log" 2>nul || (
        powershell "Get-Content 'logs\earnings_gap_trader_prod.log' | Select-Object -Last 10"
    )
) else (
    echo Log file not found: logs\earnings_gap_trader_prod.log
)

echo.
echo ================================================
echo Press Ctrl+C to exit monitor
echo Refreshing in 30 seconds...
echo ================================================

REM Wait 30 seconds and refresh
timeout /t 30 /nobreak >nul
goto monitor_loop