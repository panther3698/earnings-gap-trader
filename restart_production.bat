@echo off
REM Clean Production Restart
REM Stops all instances and starts fresh

echo.
echo ================================================
echo   CLEAN PRODUCTION RESTART
echo ================================================
echo.

echo Stopping all Python processes...
taskkill /f /im python.exe >nul 2>&1

echo Waiting for cleanup...
timeout /t 3 >nul

echo Starting clean production instance...
start_production.bat