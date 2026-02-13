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
REM Run cleanup script
REM ================================
echo Running cleanup script...
echo.

python dev\cleanup.py

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
