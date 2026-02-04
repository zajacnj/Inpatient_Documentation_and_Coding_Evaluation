@echo off
echo ============================================================
echo LSV Schema Explorer - Inpatient Documentation Project
echo ============================================================
echo.
echo This script will connect to the LSV database and search for
echo tables related to:
echo   - Inpatient admissions and discharges (PTF)
echo   - TIU clinical notes
echo   - Vital signs
echo   - Laboratory values
echo   - ICD-10 diagnoses
echo.
echo Make sure you are connected to the VA network!
echo.
pause

echo.
echo Running schema exploration...
echo.

where py >nul 2>nul
if %errorlevel%==0 (
  py tools\explore_schema.py --apply-config
  goto :eof
)

where python >nul 2>nul
if %errorlevel%==0 (
  python tools\explore_schema.py --apply-config
  goto :eof
)

echo ERROR: Python not found on PATH.
echo Please install Python 3.9+ from https://www.python.org/downloads/
echo Ensure "Add Python to PATH" is checked during installation.
pause
exit /b 1

echo.
echo ============================================================
echo Exploration complete!
echo.
echo Results saved to: data\schema_exploration_results.json
echo.
echo Review the results and update config\database_config.json
echo with the recommended tables.
echo ============================================================
echo.
pause
