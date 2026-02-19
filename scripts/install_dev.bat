@echo off
setlocal EnableDelayedExpansion

REM =====================================================
REM  Oregon Processing - Development Installer
REM =====================================================

cd /d "%~dp0.."

call :MAIN
set EXIT_CODE=%ERRORLEVEL%
echo ===========================================================================
IF NOT "%EXIT_CODE%"=="0" (
    echo Installation FAILED with exit code %EXIT_CODE%.
    echo Please review the error messages above.
) ELSE (
    echo Installation completed successfully!
    echo Virtual Environment: %VENV_DIR%
    echo Python version: %PYTHON_VERSION%
    echo You can now run the following scripts:
    echo   - scripts\open_terminal.bat  ^(Open interactive terminal^)
    echo   - scripts\start_export.bat   ^(Export data from device^)
)
echo ===========================================================================
pause
exit /b %EXIT_CODE%



:MAIN

REM ================================
REM Configuration
REM ================================
set VENV_DIR=venv
set PYTHON_DIR=python
set PYTHON_VERSION=3.13
echo =====================================================
echo      Oregon Processing - Development Installer
echo =====================================================
echo.
echo Virtual Environment: %VENV_DIR%
echo Python: %PYTHON_VERSION%
echo.

REM ================================
REM Verify pyproject.toml exists
REM ================================
echo [1/5] Verifying project files...
IF NOT EXIST pyproject.toml (
    echo ERROR: pyproject.toml not found.
    echo Make sure you're running install_dev.bat from the scripts folder.
    exit /b 1
)

REM ================================
REM Check if embedded Python exists
REM ================================
echo [2/5] Checking for embedded Python...
IF NOT EXIST %PYTHON_DIR%\python.exe (
    echo ERROR: Embedded Python not found in %PYTHON_DIR% folder.
    echo Make sure you have placed the embedded Python distribution in the %PYTHON_DIR% folder.
    exit /b 1
)
echo       Embedded Python found.

REM ================================
REM Check if venv already exists
REM ================================
echo [3/5] Checking for existing virtual environment...
IF EXIST %VENV_DIR% (
    echo.
    echo Virtual environment "%VENV_DIR%" already exists.
    set /p "USER_INPUT=Do you want to delete and recreate it? (y/n): "
    echo.

    IF /I "!USER_INPUT!"=="Y" (
        echo       Removing existing virtual environment...
        rmdir /s /q %VENV_DIR%
        IF %ERRORLEVEL% NEQ 0 (
            echo ERROR: Failed to remove virtual environment.
            exit /b 1
        )
        echo       Done.
        goto CREATE_VENV
    ) ELSE (
        echo [4/5] Keeping existing virtual environment.
        goto INSTALL_PACKAGE
    )
) ELSE (
    echo       No existing virtual environment found.
)

:CREATE_VENV
echo [4/5] Creating virtual environment...
%PYTHON_DIR%\python.exe -m venv %VENV_DIR%
IF %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERROR: Failed to create virtual environment.
    exit /b 1
)
echo       Virtual environment created successfully.

:INSTALL_PACKAGE
REM ================================
REM Upgrade pip and install package with dev dependencies
REM ================================
echo [5/5] Installing oregon-processing package with dev dependencies...
call %VENV_DIR%\Scripts\python.exe -m pip install --upgrade pip >nul
IF %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERROR: Failed to upgrade pip.
    exit /b 1
)
call %VENV_DIR%\Scripts\pip.exe install -e ".[test]"
IF %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERROR: Package installation failed.
    exit /b 1
)
echo       Package installed successfully with development tools.
exit /b 0
