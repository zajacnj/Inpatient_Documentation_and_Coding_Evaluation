@echo off
setlocal enabledelayedexpansion

REM Change to the directory where this batch file is located
cd /d "%~dp0"

echo.
echo Starting Inpatient Documentation and Coding Evaluation
echo (Desktop Mode - Full Screen Borderless Window)
echo.

REM Activate virtual environment if it exists
if exist ".venv\Scripts\activate.bat" (
    call ".venv\Scripts\activate.bat"
    echo Virtual environment activated.
) else (
    echo [ERROR] .venv not found. Cannot start application.
    echo Please run: python -m venv .venv
    echo Then run: .venv\Scripts\activate.bat
    echo Then run: pip install -r requirements.txt
    pause
    exit /b 1
)

REM Load environment variables from Key.env
if exist "Key.env" (
    for /f "usebackq delims=" %%i in ("Key.env") do (
        set "%%i" 2>nul
    )
)

echo Installing/updating pywebview if needed...
pip install pywebview^>=5.0.0 --quiet

echo.
echo Starting application in full-screen desktop mode...
echo Press F11 to toggle between fullscreen and windowed mode
echo Press Ctrl+C in this window to stop the application
echo.

python launcher.py

endlocal
