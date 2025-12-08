@echo off
REM ============================================================
REM  SEMPTIFY WINDOWS INSTALLER BUILDER
REM  Version 5.0.0 - Windows 10/11/22 Compatible
REM ============================================================
REM
REM  Usage: build_installer.bat [options]
REM  
REM  Options:
REM    clean     - Remove previous build before building
REM    onefile   - Create single EXE (slower startup)
REM    debug     - Enable debug output
REM
REM ============================================================

echo.
echo ============================================================
echo   SEMPTIFY WINDOWS INSTALLER BUILDER
echo   Version 5.0.0 - Windows 10/11/22 Compatible
echo ============================================================
echo.

cd /d "%~dp0\.."

REM Check Python venv
if not exist ".venv\Scripts\python.exe" (
    echo ERROR: Virtual environment not found!
    echo Run: python -m venv .venv
    echo Then: .venv\Scripts\activate
    echo Then: pip install -r requirements.txt
    pause
    exit /b 1
)

echo [1/5] Checking PyInstaller...
.venv\Scripts\python.exe -m pip install pyinstaller --quiet

echo [2/5] Building Semptify installer...
echo.

REM Parse arguments
set CLEAN_ARG=
set ONEFILE_ARG=
set DEBUG_ARG=

:parse_args
if "%1"=="" goto build
if /i "%1"=="clean" set CLEAN_ARG=--clean
if /i "%1"=="onefile" set ONEFILE_ARG=--onefile
if /i "%1"=="debug" set DEBUG_ARG=--debug=all
shift
goto parse_args

:build

REM Default to onedir (folder mode)
if "%ONEFILE_ARG%"=="" (
    set BUILD_MODE=--onedir
) else (
    set BUILD_MODE=%ONEFILE_ARG%
)

.venv\Scripts\python.exe -m PyInstaller ^
    %CLEAN_ARG% ^
    --noconfirm ^
    --console ^
    %BUILD_MODE% ^
    %DEBUG_ARG% ^
    installer\semptify.spec

if errorlevel 1 (
    echo.
    echo ERROR: Build failed!
    pause
    exit /b 1
)

echo.
echo [3/5] Build complete!

REM Check if onefile or folder mode
if "%ONEFILE_ARG%"=="" (
    set EXE_PATH=dist\Semptify\Semptify.exe
) else (
    set EXE_PATH=dist\Semptify.exe
)

if exist "%EXE_PATH%" (
    echo   Executable: %EXE_PATH%
) else (
    echo   WARNING: Could not find executable
)

echo.
echo ============================================================
echo   BUILD SUCCESSFUL!
echo ============================================================
echo.
echo To run: %EXE_PATH%
echo.
pause
