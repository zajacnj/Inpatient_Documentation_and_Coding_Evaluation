@echo off
setlocal enabledelayedexpansion

REM Change to the directory where this batch file is located
REM This allows the script to work from any directory
cd /d "%~dp0"

echo.
echo Starting Inpatient Documentation and Coding Evaluation...
echo (Microsoft Edge App Mode)
echo.

REM Activate virtual environment if it exists
if exist ".venv\Scripts\activate.bat" (
    call ".venv\Scripts\activate.bat"
    echo Virtual environment activated.
) else (
    echo [WARN] .venv not found. Ensure dependencies are installed.
    echo Run: python -m venv .venv
    echo Then: .venv\Scripts\activate.bat
    echo Then: pip install -r requirements.txt
    pause
    exit /b 1
)

REM Load environment variables from Key.env
if exist "Key.env" (
    for /f "usebackq delims=" %%i in ("Key.env") do (
        set "%%i" 2>nul
    )
)

echo.
echo Starting application in Microsoft Edge app mode...
echo Close the Edge window to exit the application
echo.

python launcher_edge.py

echo.
echo Application closed.
endlocal
