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
IF NOT EXIST dev\cleanup.py (
    echo ERROR: cleanup.py not found in dev folder.
    echo Make sure the dev folder exists with cleanup.py.
    echo.
    pause
    exit /b 1
)

REM ================================
REM Check if embedded Python exists
REM ================================
IF NOT EXIST python\python.exe (
    echo ERROR: Embedded Python not found in python folder.
    echo Using system Python instead.
    echo.
    echo Running cleanup script...
    echo.
    python dev\cleanup.py
) ELSE (
    echo Using embedded Python from python folder.
    echo.
    echo Running cleanup script...
    echo.
    python\python.exe dev\cleanup.py
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
