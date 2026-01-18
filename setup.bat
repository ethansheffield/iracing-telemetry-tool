@echo off
title iRacing Telemetry Tool - Setup
echo.
echo  ========================================
echo   iRacing Telemetry Tool - Setup
echo  ========================================
echo.

:: Check for Python
python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python is not installed or not in PATH.
    echo.
    echo  Please install Python 3.10 or higher from:
    echo  https://www.python.org/downloads/
    echo.
    echo  IMPORTANT: Check "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)

:: Display Python version
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYVER=%%i
echo  [OK] Python %PYVER% detected
echo.

:: Create virtual environment
echo  [1/3] Creating virtual environment...
if exist venv (
    echo        Virtual environment already exists, skipping...
) else (
    python -m venv venv
    if errorlevel 1 (
        echo  [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
)
echo        Done.
echo.

:: Install dependencies
echo  [2/3] Installing dependencies...
call venv\Scripts\activate
pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo  [ERROR] Failed to install dependencies.
    pause
    exit /b 1
)
echo        Done.
echo.

:: Create launcher
echo  [3/3] Creating launcher...
(
    echo @echo off
    echo cd /d "%%~dp0"
    echo call venv\Scripts\activate
    echo pythonw gui.py
) > "Start Telemetry.bat"
echo        Done.
echo.

echo  ========================================
echo   Setup Complete!
echo  ========================================
echo.
echo  To start the tool, double-click:
echo  Start Telemetry.bat
echo.
echo  Or run from command line:
echo  venv\Scripts\activate
echo  python main.py capture
echo.
pause
