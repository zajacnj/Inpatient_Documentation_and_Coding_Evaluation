@echo off
setlocal

cd /d "%~dp0"

echo Starting Inpatient Documentation and Coding Evaluation...

if exist ".venv\\Scripts\\activate.bat" (
    call ".venv\\Scripts\\activate.bat"
) else (
    echo [WARN] .venv not found. Ensure dependencies are installed.
)

if exist "Key.env" (
    for /f "usebackq delims=" %%i in ("Key.env") do set %%i
)

echo Starting server...
start /B uvicorn server:app --host 127.0.0.1 --port 8000 --reload

echo Waiting for server to be ready...
:wait_loop
timeout /t 1 /nobreak >nul
curl -s http://127.0.0.1:8000/api/health >nul 2>&1
if errorlevel 1 (
    goto wait_loop
)

echo Server is ready! Opening browser...
start "" "http://127.0.0.1:8000"

echo.
echo Application is running at http://127.0.0.1:8000
echo Press Ctrl+C to stop the server
pause >nul

endlocal
