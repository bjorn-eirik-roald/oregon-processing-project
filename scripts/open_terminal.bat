@echo off
setlocal

cd /d "%~dp0.."

set VENV_DIR=venv
set VENV_PYTHON=%VENV_DIR%\Scripts\python.exe

echo Using virtual environment: %VENV_DIR%
echo.

REM --- Check if virtual environment exists ---
if not exist "%VENV_PYTHON%" (
    echo ERROR: Virtual environment not found at %VENV_DIR%.
    echo Please run setup.bat first to create the virtual environment.
    pause
    exit /b 1
)

REM --- Activate the virtual environment ---
call "%VENV_DIR%\Scripts\activate.bat"
if errorlevel 1 (
    echo ERROR: Failed to activate virtual environment.
    pause
    exit /b 1
)

REM --- Run the Python script ---
open-terminal

set ERR=%ERRORLEVEL%

if %ERR% NEQ 0 (
    echo.
    echo ERROR: The program exited with code %ERR%.
    echo Please read the messages above.
)

echo.
echo ----
echo Script finished.
pause
