@echo off
REM Automated Setup Script for Windows - Earnings Gap Trading System
REM This script launches the Python setup wizard

echo.
echo ================================================
echo   EARNINGS GAP TRADING SYSTEM - WINDOWS SETUP
echo ================================================
echo.
echo Starting automated setup wizard...
echo.

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.9+ from https://python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation
    pause
    exit /b 1
)

REM Show Python version
echo Python version:
python --version
echo.

REM Check if setup script exists
if not exist "scripts\setup_trading_system.py" (
    echo ERROR: scripts\setup_trading_system.py not found
    echo Please ensure you're running this from the project directory
    pause
    exit /b 1
)

echo Launching setup wizard...
echo.

REM Run the setup script
python scripts\setup_trading_system.py

REM Check if setup was successful
if %errorlevel% equ 0 (
    echo.
    echo ================================================
    echo   SETUP COMPLETED SUCCESSFULLY!
    echo ================================================
    echo.
    echo Your trading system is now ready.
    echo Dashboard URL: http://localhost:8000
    echo.
    echo Press any key to open the dashboard in your browser...
    pause >nul
    start http://localhost:8000
) else (
    echo.
    echo ================================================
    echo   SETUP FAILED
    echo ================================================
    echo.
    echo Please check the error messages above and try again.
    echo For help, see QUICK_START.md or contact support.
    echo.
    pause
)

echo.
pause