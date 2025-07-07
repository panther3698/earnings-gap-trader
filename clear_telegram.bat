@echo off
REM Clear Telegram Bot Session
REM Run this if you get "bot instance already running" errors

echo.
echo ================================================
echo   TELEGRAM BOT SESSION CLEANER
echo ================================================
echo.
echo This will clear any existing Telegram bot sessions
echo to resolve "bot instance already running" conflicts.
echo.

venv\Scripts\python.exe clear_telegram.py

echo.
pause