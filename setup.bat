@echo off
setlocal EnableDelayedExpansion

REM =====================================================
REM Oregon Processing - Setup (Python 3.13 only)
REM =====================================================

set "VENV_DIR=venv"
set "PYTHON_VERSION=3.13"

echo =====================================================
echo      Oregon Processing - Setup
echo =====================================================
echo.

REM ==============================
REM Step 1: Locate Python launcher
REM ==============================
echo [1/3] Checking for official Python launcher...

set "PYTHON_CMD="

REM Try to find py.exe in PATH
for /f "delims=" %%i in ('where.exe py 2^>nul') do (
    set "PYTHON_CMD=%%i"
)

REM Fallback: check hardcoded user location
if not defined PYTHON_CMD (
    if exist "%LOCALAPPDATA%\Programs\Python\Launcher\py.exe" (
        set "PYTHON_CMD=%LOCALAPPDATA%\Programs\Python\Launcher\py.exe"
    )
)

if defined PYTHON_CMD (
    echo       Official Python launcher found at "!PYTHON_CMD!"
    goto FOUND_PYTHON
)

echo [ERROR] Official Python launcher (py.exe) not found.
echo Please install Python 3.13 using the official installer provided with this release.
pause
exit /b 1

:FOUND_PYTHON

REM ==============================
REM Step 2: Remove existing virtual environment
REM ==============================
if exist "%VENV_DIR%" (
    echo [2/3] Existing virtual environment detected, removing...
    rmdir /s /q "%VENV_DIR%"
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] Failed to remove existing virtual environment.
        pause
        exit /b 1
    )
    echo       Done.
) else (
    echo [2/3] No existing virtual environment found.
)
echo.

REM ==============================
REM Step 3: Create virtual environment & install package
REM ==============================
echo [3/3] Creating virtual environment in "%VENV_DIR%"...
"%PYTHON_CMD%" -%PYTHON_VERSION% -m venv "%VENV_DIR%"
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Failed to create virtual environment.
    pause
    exit /b 1
)
echo       Virtual environment created successfully.
echo.

call "%VENV_DIR%\Scripts\activate.bat"

echo       Upgrading pip...
python -m pip install --upgrade pip
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Failed to upgrade pip.
    pause
    exit /b 1
)

echo       Installing Oregon Processing package...
python -m pip install -e .
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Package installation failed.
    pause
    exit /b 1
)

echo.
echo =====================================================
echo Setup completed successfully!
echo Virtual environment: "%VENV_DIR%"
echo Python interpreter used: "!PYTHON_CMD!"
echo You can now run scripts in the "scripts" folder, which will use this virtual environment.
echo =====================================================
pause
exit /b 0
