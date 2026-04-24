@echo off
REM Semptify GUI Test Runner (Windows)
REM This script runs the Playwright GUI test bot

echo ============================================
echo Semptify GUI Test Bot
echo ============================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Please install Python 3.11+
    exit /b 1
)

REM Check if virtual environment exists and activate it
if exist "..\.venv\Scripts\activate.bat" (
    echo Activating virtual environment...
    call "..\.venv\Scripts\activate.bat"
) else if exist "..\venv311\Scripts\activate.bat" (
    echo Activating virtual environment (venv311)...
    call "..\venv311\Scripts\activate.bat"
)

REM Check if playwright is installed
python -c "import playwright" >nul 2>&1
if errorlevel 1 (
    echo Installing Playwright...
    pip install playwright
    playwright install chromium
)

REM Parse arguments
set HEADED=
set SLOW=
set ROLE=all

:parse_args
if "%~1"=="" goto run_tests
if /I "%~1"=="--headed" set HEADED=--headed
if /I "%~1"=="--slow" set SLOW=--slow 500
if /I "%~1"=="--role" (
    shift
    set ROLE=%~1
)
shift
goto parse_args

:run_tests
echo.
echo Running GUI tests with role: %ROLE%
if not "%HEADED%"=="" echo Mode: HEADED (visible browser)
if not "%SLOW%"=="" echo Slow motion: 500ms

python "%~dp0\gui_test_bot.py" %HEADED% %SLOW% --role %ROLE%

if errorlevel 1 (
    echo.
    echo ============================================
    echo Tests completed with failures
    echo ============================================
    exit /b 1
) else (
    echo.
    echo ============================================
    echo All tests passed!
    echo ============================================
)
