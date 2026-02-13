@echo off
setlocal EnableDelayedExpansion

REM =====================================================
REM  Oregon Processing - Automated Installer
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
    echo Environment: %ENV_NAME%
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
set ENV_NAME=oregon_env
set PYTHON_VERSION=3.11
echo =====================================================
echo      Oregon Processing - Automated Installer
echo =====================================================
echo.
echo Environment: %ENV_NAME%
echo Python: %PYTHON_VERSION%
REM ================================
REM Verify pyproject.toml exists
REM ================================
echo [1/5] Verifying project files...
IF NOT EXIST pyproject.toml (
    echo ERROR: pyproject.toml not found.
    echo Make sure you're running install.bat from the scripts folder.
    exit /b 1
)

REM ================================
REM Check if conda exists
REM ================================
echo [2/5] Checking for Conda...
where conda >nul 2>nul
IF %ERRORLEVEL% NEQ 0 (
    echo ERROR: Conda was not found in PATH.
    echo Please install Anaconda via Company Software Center.
    exit /b 1
)

REM ================================
REM Verify conda works
REM ================================
call :RUN_CONDA --version >nul 2>nul
IF %ERRORLEVEL% NEQ 0 (
    echo ERROR: Conda is installed but not initialized correctly.
    echo Try opening Anaconda Prompt once before running this installer.
    exit /b 1
)

REM ================================
REM Check if environment exists
REM ================================
echo [3/5] Checking for existing environment...
call :RUN_CONDA run -n %ENV_NAME% python --version >nul 2>nul
IF %ERRORLEVEL% EQU 0 (
    set ENV_EXISTS=0
) ELSE (
    set ENV_EXISTS=1
)

IF %ENV_EXISTS% EQU 0 (
    echo.
    echo Environment "%ENV_NAME%" already exists.
    set /p "USER_INPUT=Do you want to delete and recreate it? (y/n): "
    echo.

    IF /I "!USER_INPUT!"=="Y" (
        echo       Removing existing environment...
        call :RUN_CONDA env remove -n %ENV_NAME% -y
        IF %ERRORLEVEL% NEQ 0 (
            echo ERROR: Failed to remove environment.
            exit /b 1
        )
        echo       Done.
        goto CREATE_ENV
    ) ELSE (
        echo [4/5] Keeping existing environment.
        goto INSTALL_PACKAGE
    )
) ELSE (
    echo       No existing environment found.
)
:CREATE_ENV
echo [4/5] Creating conda environment...
call :RUN_CONDA create -y -n %ENV_NAME% python=%PYTHON_VERSION%
IF %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERROR: Failed to create environment.
    exit /b 1
)
echo.
echo       Environment created successfully.
:INSTALL_PACKAGE

REM ================================
REM Upgrade pip
REM ================================
echo [5/5] Installing oregon-processing package in editable mode...
call :RUN_CONDA run -n %ENV_NAME% python -m pip install --upgrade pip >nul
IF %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERROR: Failed to upgrade pip.
    exit /b 1
)
call :RUN_CONDA run -n %ENV_NAME% python -m pip install -e .
IF %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERROR: Package installation failed.
    exit /b 1
)
echo.
echo       Package installed successfully in editable mode.
exit /b 0

:RUN_CONDA
setlocal
set "ARGS=%*"
cmd /d /c "conda %ARGS%"
endlocal & exit /b %ERRORLEVEL%
