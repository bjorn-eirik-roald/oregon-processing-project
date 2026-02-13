@echo off
setlocal

set ENV_NAME=oregon_env
echo Using conda environment: %ENV_NAME%
echo.

REM --- Check if conda exists ---
where conda >nul 2>nul
if errorlevel 1 (
    echo ERROR: Conda not found.
    echo Please install Anaconda or Miniconda and try again.
    pause
    exit /b 1
)

REM --- Check if the environment exists ---
conda env list | findstr /i "%ENV_NAME%" >nul
if errorlevel 1 (
    echo ERROR: Conda environment "%ENV_NAME%" not found.
    echo Make sure the environment is created with the proper name and packages installed. Then try again.
    pause
    exit /b 1
)

REM --- Activate the environment ---
call conda activate %ENV_NAME%
if errorlevel 1 (
    echo ERROR: Failed to activate environment "%ENV_NAME%".
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
