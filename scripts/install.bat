@echo off
setlocal EnableDelayedExpansion

REM =====================================================
REM  Oregon Processing - Automated Installer
REM =====================================================

cd /d "%~dp0.."

call :MAIN
set EXIT_CODE=%ERRORLEVEL%

echo.
echo =====================================================
IF NOT "%EXIT_CODE%"=="0" (
    echo Installation FAILED with exit code %EXIT_CODE%.
) ELSE (
    echo Installation completed successfully.
)
echo =====================================================
echo.
pause
exit /b %EXIT_CODE%



:MAIN

echo [DEBUG] Entered :MAIN

REM ================================
REM Configuration
REM ================================
set ENV_NAME=oregon_env
set PYTHON_VERSION=3.11

echo [DEBUG] ENV_NAME=%ENV_NAME%
echo [DEBUG] PYTHON_VERSION=%PYTHON_VERSION%

echo.
echo =====================================================
echo      Oregon Processing Automated Installer
echo =====================================================
echo.

REM ================================
REM Verify pyproject.toml exists
REM ================================
IF NOT EXIST pyproject.toml (
    echo ERROR: pyproject.toml not found in this folder.
    echo Make sure install.bat is located in the project root.
    echo [DEBUG] Exiting: pyproject.toml missing
    exit /b 1
)

echo [DEBUG] Found pyproject.toml

REM ================================
REM Check if conda exists
REM ================================
where conda >nul 2>nul
IF %ERRORLEVEL% NEQ 0 (
    echo ERROR: Conda was not found in PATH.
    echo Please install Anaconda via Company Software Center.
    echo [DEBUG] Exiting: conda not found in PATH
    exit /b 1
)

echo Conda found.
echo [DEBUG] where conda exit code %ERRORLEVEL%

REM ================================
REM Verify conda works
REM ================================
call :RUN_CONDA --version >nul 2>nul
IF %ERRORLEVEL% NEQ 0 (
    echo ERROR: Conda is installed but not initialized correctly.
    echo Try opening Anaconda Prompt once before running this installer.
    echo [DEBUG] Exiting: conda --version failed with %ERRORLEVEL%
    exit /b 1
)

echo Conda verified.
echo [DEBUG] conda --version exit code %ERRORLEVEL%
echo.

REM ================================
REM Check if environment exists
REM ================================
call :RUN_CONDA run -n %ENV_NAME% python --version >nul 2>nul
IF %ERRORLEVEL% EQU 0 (
    set ENV_EXISTS=0
) ELSE (
    set ENV_EXISTS=1
)

echo [DEBUG] ENV_EXISTS=%ENV_EXISTS%

IF %ENV_EXISTS% EQU 0 (
    echo Environment "%ENV_NAME%" already exists.
    echo.
    set /p USER_INPUT=Do you want to delete and recreate it? ^(y/n^):

    IF /I "!USER_INPUT!"=="Y" (
        echo.
        echo Removing existing environment...
        call :RUN_CONDA env remove -n %ENV_NAME% -y
        IF %ERRORLEVEL% NEQ 0 (
            echo ERROR: Failed to remove environment.
            echo [DEBUG] Exiting: env remove failed with %ERRORLEVEL%
            exit /b 1
        )
        echo Environment removed successfully.
        echo.
        goto CREATE_ENV
    ) ELSE (
        echo Keeping existing environment.
        echo.
        goto INSTALL_PACKAGE
    )
)

:CREATE_ENV
echo Creating environment "%ENV_NAME%"...
call :RUN_CONDA create -y -n %ENV_NAME% python=%PYTHON_VERSION%
IF %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to create environment.
    echo [DEBUG] Exiting: conda create failed with %ERRORLEVEL%
    exit /b 1
)
echo Environment created successfully.
echo.

:INSTALL_PACKAGE

REM ================================
REM Upgrade pip
REM ================================
echo Upgrading pip...
call :RUN_CONDA run -n %ENV_NAME% python -m pip install --upgrade pip
IF %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to upgrade pip.
    echo [DEBUG] Exiting: pip upgrade failed with %ERRORLEVEL%
    exit /b 1
)

echo.

REM ================================
REM Install package
REM ================================
echo Installing package from current directory...
call :RUN_CONDA run -n %ENV_NAME% python -m pip install --upgrade --force-reinstall .
IF %ERRORLEVEL% NEQ 0 (
    echo ERROR: pip install failed.
    echo [DEBUG] Exiting: pip install failed with %ERRORLEVEL%
    exit /b 1
)

echo.
exit /b 0

:RUN_CONDA
setlocal
set "ARGS=%*"
echo [DEBUG] RUN_CONDA: conda %ARGS%
cmd /d /c "conda %ARGS%"
set EXIT_CODE=%ERRORLEVEL%
echo [DEBUG] RUN_CONDA exit code %EXIT_CODE%
endlocal & exit /b %EXIT_CODE%
