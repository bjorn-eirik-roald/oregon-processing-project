@echo off
setlocal

REM =====================================================
REM  Oregon Processing - Cleanup Script
REM =====================================================

cd /d "%~dp0.."

echo.
echo =====================================================
echo      Oregon Processing - Cleanup
echo =====================================================
echo.

REM ================================
REM Verify cleanup.py exists
REM ================================
IF NOT EXIST tools\cleanup.py (
    echo ERROR: cleanup.py not found in tools folder.
    echo Make sure the tools folder exists with cleanup.py.
    echo.
    pause
    exit /b 1
)

REM ================================
REM Check if virtual environment exists
REM ================================
IF EXIST venv\Scripts\python.exe (
    echo Using Python from virtual environment.
    echo.
    echo Running cleanup script...
    echo.
    venv\Scripts\python.exe tools\cleanup.py
) ELSE (
    echo Virtual environment not found, using system Python.
    echo.
    echo Running cleanup script...
    echo.
    python tools\cleanup.py
)

set ERR=%ERRORLEVEL%

echo.
echo =====================================================
IF %ERR% NEQ 0 (
    echo Cleanup FAILED with exit code %ERR%.
    echo Please read the messages above.
) ELSE (
    echo Cleanup completed successfully.
)
echo =====================================================
echo.

pause
exit /b %ERR%
