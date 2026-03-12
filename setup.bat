@echo off
setlocal EnableDelayedExpansion



set "VENV_DIR=.venv"
set "PYTHON_VERSION=3.13"
set "PACKAGE_NAME=OREGON-PROCESSING"


REM STARTING SETUP
goto START_SETUP




REM ==============================
:START_SETUP

echo =====================================================
echo      %PACKAGE_NAME% - Setup
echo =====================================================
echo.

goto DETECT_LAUNCHER
REM ==============================

REM ==============================
:DETECT_LAUNCHER

echo.
echo =====================================================
echo Stage 1/4: Detecting Python launcher...
echo =====================================================
echo.

set "PYTHON_CMD="
for /f "delims=" %%i in ('where.exe py 2^>nul') do (
    set "PYTHON_CMD=%%i"
)

if not defined PYTHON_CMD (
    if exist "%LOCALAPPDATA%\Programs\Python\Launcher\py.exe" (
        set "PYTHON_CMD=%LOCALAPPDATA%\Programs\Python\Launcher\py.exe"
    )
)

if defined PYTHON_CMD ( goto FOUND_PYTHON )
goto NO_LAUNCHER_ERROR
REM ==============================

REM ==============================
:FOUND_PYTHON
REM Launcher found, proceed to verification
echo [INFO] Official Python launcher found at "!PYTHON_CMD!"
goto VERIFY_PYTHON
REM ==============================

REM ==============================
:VERIFY_PYTHON
echo.
echo =====================================================
echo Stage 2/4: Verifying Python %PYTHON_VERSION% is installed...
echo =====================================================
echo.

"%PYTHON_CMD%" -%PYTHON_VERSION% --version >nul 2>&1
    if %ERRORLEVEL% neq 0 goto INSTALL_PYTHON
    goto PYTHON_VERIFIED
REM ==============================

REM ==============================
:PYTHON_VERIFIED
echo [INFO] Python %PYTHON_VERSION% verified.
echo.

goto CHECK_VENV
REM ==============================

REM ==============================
:INSTALL_PYTHON
echo.
echo [INFO] Python %PYTHON_VERSION% is not installed. Attempting to install using Python Install Manager...
"%PYTHON_CMD%" install %PYTHON_VERSION%

goto POST_INSTALL_CHECK
REM ==============================

:POST_INSTALL_CHECK

echo [INFO] Re-checking for Python %PYTHON_VERSION% after install...
"%PYTHON_CMD%" -%PYTHON_VERSION% --version >nul 2>&1
    if %ERRORLEVEL% neq 0 goto PYTHON_RECHECK_ERROR
    goto PYTHON_VERIFIED
REM ==============================

REM ==============================
:CHECK_VENV

echo.
echo =====================================================
echo Stage 3/4: Setting up virtual environment...
echo =====================================================
echo.
if exist "%VENV_DIR%" (
    echo [INFO] Existing virtual environment detected
    goto REMOVE_VENV

) else (
    echo [INFO] No existing virtual environment found.
    goto CREATE_VENV
)
echo.
REM ==============================

REM ==============================
:REMOVE_VENV

echo [INFO] Removing existing virtual environment...
    rmdir /s /q "%VENV_DIR%"
    if %ERRORLEVEL% neq 0 (
        goto REMOVE_VENV_ERROR
    )
echo [INFO] Existing virtual environment removed.
goto CREATE_VENV

:CREATE_VENV

echo [INFO] Creating virtual environment in "%VENV_DIR%"...
"%PYTHON_CMD%" -%PYTHON_VERSION% -m venv "%VENV_DIR%"
if %ERRORLEVEL% neq 0 (
    goto CREATE_VENV_ERROR
)

echo [INFO] Virtual environment created successfully.
goto INSTALL_PACKAGE
REM ==============================

REM ==============================
:INSTALL_PACKAGE

echo.
echo =====================================================
echo Stage 4/4: Installing %PACKAGE_NAME% Package
echo =====================================================
echo.

call "%VENV_DIR%\Scripts\activate.bat"

echo [INFO] Upgrading pip...
python -m pip install --upgrade pip
if %ERRORLEVEL% neq 0 (
    goto PIP_UPGRADE_ERROR
)
echo [INFO] PIP upgraded successfully.

echo [INFO] Installing %PACKAGE_NAME% package...
python -m pip install -e .
if %ERRORLEVEL% neq 0 (
    goto INSTALL_PACKAGE_ERROR
)

echo [INFO] %PACKAGE_NAME% package installed successfully.
goto POST_INSTALL_SUCCESS
REM ==============================

REM ==============================
:POST_INSTALL_SUCCESS
echo.
echo.
echo =====================================================
echo Setup completed successfully!
echo Virtual environment: "%VENV_DIR%"
echo Python interpreter used: "!PYTHON_CMD!"
echo %PACKAGE_NAME% is now installed in the virtual environment.
echo You can now run scripts in the "bin" folder, which will use this virtual environment.
echo =====================================================
echo.
echo.
pause
exit /b 0
REM ==============================





REM ==============================
:PYTHON_INSTALL_ERROR
echo [ERROR] Python Install Manager (python.exe) failed to install Python 3.13. Please check your internet connection and try again.
pause
exit /b 1
REM ==============================

REM ==============================
:PYTHON_RECHECK_ERROR
echo [ERROR] After completing install of Python 3.13 without error, Python Install Manager (python.exe) failed to detect Python 3.13..
pause
exit /b 1
REM ==============================

REM ==============================
:PY_INSTALL_ERROR
echo [ERROR] Python Install Manager (py.exe) failed to install Python 3.13. Please ensure Python Install Manager is installed from the Windows Store and try again.
echo If you just installed it, try restarting your terminal or logging out and back in.
pause
exit /b 1
REM ==============================

REM ==============================
:NO_LAUNCHER_ERROR
echo [ERROR] Official Python launcher (py.exe) not found.
echo Please install Python 3.13 using the official installer provided with this release.
pause
exit /b 1
REM ==============================

REM ==============================
:REMOVE_VENV_ERROR
echo [ERROR] Failed to remove existing virtual environment.
pause
exit /b 1
REM ==============================

REM ==============================
:CREATE_VENV_ERROR
echo [ERROR] Failed to create virtual environment.
pause
exit /b 1
REM ==============================

REM ==============================
:PIP_UPGRADE_ERROR
echo [ERROR] Failed to upgrade PIP.
pause
exit /b 1
REM ==============================

REM ==============================
:INSTALL_PACKAGE_ERROR
echo [ERROR] Failed to install %PACKAGE_NAME% package.
pause
exit /b 1
REM ==============================






