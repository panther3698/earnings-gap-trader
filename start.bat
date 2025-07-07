@echo off
REM Earnings Gap Trading System - Quick Start
REM This script activates the virtual environment and starts the system

echo.
echo ================================================
echo   EARNINGS GAP TRADING SYSTEM - QUICK START
echo ================================================
echo.

REM Check if virtual environment exists
if not exist "venv\Scripts\python.exe" (
    echo ERROR: Virtual environment not found
    echo Please run setup.bat first to install the system
    pause
    exit /b 1
)

REM Check if main.py exists
if not exist "main.py" (
    echo ERROR: main.py not found
    echo Please ensure you're running this from the project directory
    pause
    exit /b 1
)

echo Starting Earnings Gap Trading System...
echo.
echo Dashboard will be available at: http://localhost:8000
echo Press Ctrl+C to stop the system
echo.

REM Start the system using virtual environment python
venv\Scripts\python.exe main.py

REM If we get here, the system has stopped
echo.
echo ================================================
echo   TRADING SYSTEM STOPPED
echo ================================================
echo.
pause