@echo off
REM Run script for LinkedIn Post Monitor

echo Starting LinkedIn Post Monitor...
echo.

REM Activate virtual environment
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
) else (
    echo ERROR: Virtual environment not found
    echo Please run setup.bat first
    pause
    exit /b 1
)

REM Run the application
python -m linkedin_post_monitor.main

pause
