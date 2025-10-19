@echo off
REM Build script for LinkedIn Post Monitor (LIPM)
REM Creates a standalone Windows executable

echo ========================================
echo LIPM - Build Script
echo ========================================
echo.

REM Check if virtual environment is activated
if not defined VIRTUAL_ENV (
    echo [ERROR] Virtual environment not activated!
    echo Please run: .\venv\Scripts\Activate.ps1
    pause
    exit /b 1
)

REM Install PyInstaller if not present
echo [1/4] Checking PyInstaller...
pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo Installing PyInstaller...
    pip install pyinstaller
)

REM Clean previous builds
echo.
echo [2/4] Cleaning previous builds...
if exist "build" rmdir /s /q build
if exist "dist" rmdir /s /q dist
if exist "__pycache__" rmdir /s /q __pycache__
echo Done.

REM Build executable
echo.
echo [3/4] Building executable...
echo This may take several minutes...
pyinstaller LIPM.spec --clean --noconfirm

if errorlevel 1 (
    echo.
    echo [ERROR] Build failed!
    pause
    exit /b 1
)

REM Create distribution folder
echo.
echo [4/4] Creating distribution package...
if not exist "dist\LIPM-Package" mkdir "dist\LIPM-Package"

REM Copy executable and required files
copy /y "dist\LIPM.exe" "dist\LIPM-Package\"
copy /y "README.md" "dist\LIPM-Package\"
copy /y "config.template.json" "dist\LIPM-Package\config.json"

REM Create data and logs directories
if not exist "dist\LIPM-Package\data" mkdir "dist\LIPM-Package\data"
if not exist "dist\LIPM-Package\logs" mkdir "dist\LIPM-Package\logs"

REM Create empty posts database
echo {"posts": []} > "dist\LIPM-Package\data\posts.json"

echo.
echo ========================================
echo Build completed successfully!
echo ========================================
echo.
echo Executable location: dist\LIPM-Package\LIPM.exe
echo Package location: dist\LIPM-Package\
echo.
echo You can now:
echo 1. Test: cd dist\LIPM-Package ^&^& LIPM.exe
echo 2. Distribute: Zip the LIPM-Package folder
echo 3. Install: Create installer with Inno Setup
echo.
pause
