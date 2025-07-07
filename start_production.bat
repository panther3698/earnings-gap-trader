@echo off
REM Earnings Gap Trading System - Production Mode
REM This script starts the system in production configuration

echo.
echo ================================================
echo   EARNINGS GAP TRADING SYSTEM - PRODUCTION
echo ================================================
echo.
echo WARNING: Starting in PRODUCTION mode with LIVE TRADING
echo Make sure you have:
echo   1. Valid API credentials configured
echo   2. Sufficient account balance
echo   3. Risk parameters properly set
echo.
set /p confirm="Continue with PRODUCTION mode? (y/n): "
if /i not "%confirm%"=="y" (
    echo Production startup cancelled.
    pause
    exit /b 0
)

echo.
echo Starting Production Trading System...
echo.

REM Check if virtual environment exists
if not exist "venv\Scripts\python.exe" (
    echo ERROR: Virtual environment not found
    echo Please run setup.bat first to install the system
    pause
    exit /b 1
)

REM Copy production environment
if exist ".env.production" (
    copy ".env.production" ".env" >nul
    echo Production environment loaded
) else (
    echo WARNING: .env.production not found, using current .env
)

REM Create production logs directory
if not exist "logs" mkdir logs

echo.
echo ================================================
echo   PRODUCTION SYSTEM ACTIVE
echo ================================================
echo Dashboard: http://localhost:8001
echo Mode: LIVE TRADING ENABLED
echo Logs: logs/earnings_gap_trader_prod.log
echo.
echo Press Ctrl+C to stop the system
echo.

REM Start with production main script
venv\Scripts\python.exe main_production.py

echo.
echo ================================================
echo   PRODUCTION SYSTEM STOPPED
echo ================================================
echo.
pause