@echo off
setlocal enabledelayedexpansion

cd /d "%~dp0"
set RC=0
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
chcp 65001 >nul 2>nul

if "%~1"=="" (
    set PORT=COM8
) else (
    set PORT=%~1
)

if not exist artifact\results mkdir artifact\results
set HW_LOG=artifact\results\hardware_capture_console.log
set HW_JSON=artifact\results\hardware_capture_summary.json

echo ===================================================
echo PQCFirm Hardware Capture
echo ===================================================
echo.
echo This script rebuilds and flashes the ESP32-S3 failure-reproduction firmware.
echo It captures both the 8 KB stack crash and the 96 KB stack success log.
echo.
echo Serial port: %PORT%
echo.
echo IMPORTANT: This window will stay open at the end, even on error.
echo Full hardware console output is saved to:
echo   %HW_LOG%
echo JSON summary is saved to:
echo   %HW_JSON%
echo.

echo [1/4] Checking Python...
where python >nul 2>nul
if errorlevel 1 (
    echo ERROR: Python could not be found.
    echo Please install Python 3.10 or newer and make sure "Add Python to PATH" is selected.
    set RC=1
    goto fail
)
python -c "import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)" >nul 2>nul
if errorlevel 1 (
    echo ERROR: Python 3.10 or newer is required.
    python --version
    set RC=1
    goto fail
)

echo [2/4] Creating or reusing virtual environment...
if exist "venv" if not exist "venv\Scripts\activate.bat" (
    echo Existing venv directory is incomplete; removing and recreating it.
    rmdir /s /q "venv"
)
if not exist "venv\Scripts\activate.bat" (
    python -m venv "venv"
    if errorlevel 1 (
        echo ERROR: Could not create Python virtual environment.
        echo Try deleting the venv folder manually and rerunning this script.
        set RC=1
        goto fail
    )
)
if not exist "venv\Scripts\activate.bat" (
    echo ERROR: venv\Scripts\activate.bat was not created.
    echo Please check that Python venv support is installed and that this folder is writable.
    set RC=1
    goto fail
)
call "venv\Scripts\activate.bat"
if errorlevel 1 (
    echo ERROR: Could not activate venv\Scripts\activate.bat
    set RC=1
    goto fail
)

echo [3/4] Installing missing Python and PlatformIO packages...
python -m pip install --upgrade pip setuptools wheel
if errorlevel 1 (
    echo ERROR: pip/setuptools/wheel installation failed.
    set RC=1
    goto fail
)
python -m pip install --prefer-binary -r artifact\requirements.txt
if errorlevel 1 (
    echo ERROR: Python dependency installation failed.
    set RC=1
    goto fail
)

REM Use a short PlatformIO build path to avoid Windows path-length problems.
set PLATFORMIO_BUILD_DIR=%CD%\.pb

echo [4/4] Running hardware capture...
python run_hardware_capture.py --port %PORT% --skip-paired --failure-timeout 30 > artifact\results\hardware_capture_console.log 2>&1
set CAPTURE_RC=%ERRORLEVEL%
type artifact\results\hardware_capture_console.log

if not "%CAPTURE_RC%"=="0" (
    echo.
    echo Hardware capture finished with a non-zero status: %CAPTURE_RC%
    echo Check artifact\results\hardware_capture_summary.json and artifact\results\hardware_capture_console.log
    set RC=%CAPTURE_RC%
    goto fail
)

echo.
echo Hardware capture completed successfully.
echo Main JSON summary: artifact\results\hardware_capture_summary.json
echo Failure status:    artifact\results\failure_reproduction_status.json
echo Full console log:  artifact\results\hardware_capture_console.log
goto done

:fail
echo.
echo ===================================================
echo PQCFirm hardware capture stopped with an error.
echo Exit code: %RC%
echo The window is being kept open so you can read the message.
echo ===================================================
goto done_with_code

:done
echo.
echo ===================================================
echo Finished. Press any key to close this window.
echo ===================================================
pause >nul
exit /b 0

:done_with_code
echo.
echo Press any key to close this window.
pause >nul
exit /b %RC%
