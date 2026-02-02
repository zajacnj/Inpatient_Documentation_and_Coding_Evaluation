@echo off
echo ============================================================
echo Table Details Explorer - Inpatient Documentation Project
echo ============================================================
echo.
echo This script explores specific tables in detail, showing:
echo   - All columns with data types
echo   - Row counts
echo   - Sample data
echo   - Foreign key relationships
echo.
echo Make sure you are connected to the VA network!
echo.

if "%~1"=="" (
    echo Usage:
    echo   explore_table_details.bat Schema.TableName
    echo   explore_table_details.bat --all-recommended
    echo.
    echo Examples:
    echo   explore_table_details.bat Inpat.Inpatient
    echo   explore_table_details.bat TIU.TIUDocument
    echo   explore_table_details.bat --all-recommended
    echo.
    pause
    exit /b
)

echo Running table exploration for: %*
echo.

python tools\explore_table_details.py %*

echo.
echo ============================================================
echo Results saved to: data\table_details_results.json
echo ============================================================
echo.
pause
