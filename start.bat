@echo off
echo ==============================================
echo   DEET AI Backend Starter
echo ==============================================

cd /d "%~dp0\backend"

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not added to PATH!
    pause
    exit /b
)

REM Create a virtual environment if .venv does not exist
if not exist ".venv\Scripts\activate.bat" (
    echo [INFO] Creating Python virtual environment...
    python -m venv .venv
)

echo [INFO] Activating virtual environment...
call .venv\Scripts\activate.bat

echo [INFO] Installing required dependencies...
pip install -r requirements.txt

echo.
echo [INFO] Starting the Flask server...
echo.
python app.py

pause
