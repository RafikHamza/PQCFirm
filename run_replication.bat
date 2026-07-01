@echo off
setlocal enabledelayedexpansion

cd /d "%~dp0"
set RC=0
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
chcp 65001 >nul 2>nul

if not exist artifact\results mkdir artifact\results
set RUN_LOG=artifact\results\run_replication_console.log
set SUMMARY_JSON=artifact\results\run_replication_summary.json

echo =================================================
echo PQCFirm Artifact Replication and Verification
echo =================================================
echo.
echo This script creates a local Python environment, installs required packages,
echo prepares optional Mbed TLS source context, and runs the verification harness.
echo.
echo IMPORTANT: This window will stay open at the end, even on error.
echo Full verification output is saved to:
echo   %RUN_LOG%
echo JSON summary is saved to:
echo   %SUMMARY_JSON%
echo.

echo [1/5] Checking Python...
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

echo [2/5] Creating or reusing virtual environment...
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

echo [3/5] Installing missing Python packages...
python -m pip install --upgrade pip setuptools wheel
if errorlevel 1 (
    echo ERROR: pip/setuptools/wheel installation failed.
    set RC=1
    goto fail
)
python -m pip install --prefer-binary -r artifact\requirements.txt
if errorlevel 1 (
    echo ERROR: Python dependency installation failed.
    echo Please check your internet connection and rerun this script.
    set RC=1
    goto fail
)

echo [4/5] Preparing optional Mbed TLS source context...
python artifact\scripts\ensure_mbedtls.py
if errorlevel 1 (
    echo WARNING: Mbed TLS source could not be downloaded automatically.
    echo The artifact will continue using cached Mbed TLS findings.
)

echo [5/5] Running verification harness...
cd artifact
python verify_all.py > results\run_replication_console.log 2>&1
set VERIFY_RC=%ERRORLEVEL%
type results\run_replication_console.log
python scripts\write_run_summary.py --mode replication --exit-code %VERIFY_RC%
set SUMMARY_RC=%ERRORLEVEL%
cd ..

if not "%VERIFY_RC%"=="0" (
    echo.
    echo ERROR: verification failed with exit code %VERIFY_RC%.
    echo Please check artifact\results\run_replication_console.log
    echo A summary was written to artifact\results\run_replication_summary.json when possible.
    set RC=%VERIFY_RC%
    goto fail
)

if not "%SUMMARY_RC%"=="0" (
    echo.
    echo ERROR: summary writing failed with exit code %SUMMARY_RC%.
    set RC=%SUMMARY_RC%
    goto fail
)

echo.
echo Replication completed successfully.
echo Main JSON summary: artifact\results\run_replication_summary.json
echo Claim matrix:      artifact\results\claim_matrix.json
echo Full console log:  artifact\results\run_replication_console.log
echo Human notes:       artifact\CLAIMS_SUPPORTED.md
goto done

:fail
echo.
echo =================================================
echo PQCFirm replication stopped with an error.
echo Exit code: %RC%
echo The window is being kept open so you can read the message.
echo =================================================
goto done_with_code

:done
echo.
echo =================================================
echo Finished. Press any key to close this window.
echo =================================================
pause >nul
exit /b 0

:done_with_code
echo.
echo Press any key to close this window.
pause >nul
exit /b %RC%
