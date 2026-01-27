@echo off
setlocal
cd /d "%~dp0"

REM --- Read environment name from config.env ---
for /f "delims=" %%A in (config.env) do set %%A

echo Using conda environment: %OREGON_ENV%
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
conda env list | findstr /i "%OREGON_ENV%" >nul
if errorlevel 1 (
    echo ERROR: Conda environment "%OREGON_ENV%" not found.
    echo Make sure the environment is created with the proper name and packages installed. Then try again.
    pause
    exit /b 1
)

REM --- Activate the environment ---
call conda activate %OREGON_ENV%
if errorlevel 1 (
    echo ERROR: Failed to activate environment "%OREGON_ENV%".
    pause
    exit /b 1
)

REM --- Run the Python script ---
run-export

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
