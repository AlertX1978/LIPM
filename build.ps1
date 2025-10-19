# PowerShell Build Script for LIPM
# Creates a standalone Windows executable

Write-Host "========================================"  -ForegroundColor Cyan
Write-Host "LIPM - Build Script"  -ForegroundColor Cyan
Write-Host "========================================"  -ForegroundColor Cyan
Write-Host ""

# Check if virtual environment is activated
if (-not $env:VIRTUAL_ENV) {
    Write-Host "[ERROR] Virtual environment not activated!" -ForegroundColor Red
    Write-Host "Please run: .\venv\Scripts\Activate.ps1" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

# Install PyInstaller if not present
Write-Host "[1/4] Checking PyInstaller..." -ForegroundColor Green
$pyinstallerInstalled = pip show pyinstaller 2>$null
if (-not $pyinstallerInstalled) {
    Write-Host "Installing PyInstaller..." -ForegroundColor Yellow
    pip install pyinstaller
}

# Clean previous builds
Write-Host ""
Write-Host "[2/4] Cleaning previous builds..." -ForegroundColor Green
if (Test-Path "build") { Remove-Item -Recurse -Force "build" }
if (Test-Path "dist") { Remove-Item -Recurse -Force "dist" }
if (Test-Path "__pycache__") { Remove-Item -Recurse -Force "__pycache__" }
Write-Host "Done." -ForegroundColor Gray

# Build executable
Write-Host ""
Write-Host "[3/4] Building executable..." -ForegroundColor Green
Write-Host "This may take several minutes..." -ForegroundColor Yellow
pyinstaller LIPM.spec --clean --noconfirm

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "[ERROR] Build failed!" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# Create distribution folder
Write-Host ""
Write-Host "[4/4] Creating distribution package..." -ForegroundColor Green
if (-not (Test-Path "dist\LIPM-Package")) {
    New-Item -ItemType Directory -Path "dist\LIPM-Package" | Out-Null
}

# Copy executable and required files
Copy-Item "dist\LIPM.exe" "dist\LIPM-Package\" -Force
Copy-Item "README.md" "dist\LIPM-Package\" -Force
Copy-Item "config.template.json" "dist\LIPM-Package\config.json" -Force

# Create data and logs directories
if (-not (Test-Path "dist\LIPM-Package\data")) {
    New-Item -ItemType Directory -Path "dist\LIPM-Package\data" | Out-Null
}
if (-not (Test-Path "dist\LIPM-Package\logs")) {
    New-Item -ItemType Directory -Path "dist\LIPM-Package\logs" | Out-Null
}

# Create empty posts database
Set-Content -Path "dist\LIPM-Package\data\posts.json" -Value '{"posts": []}'

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Build completed successfully!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Executable location: dist\LIPM-Package\LIPM.exe" -ForegroundColor White
Write-Host "Package location: dist\LIPM-Package\" -ForegroundColor White
Write-Host ""
Write-Host "You can now:" -ForegroundColor Yellow
Write-Host "1. Test: cd dist\LIPM-Package; .\LIPM.exe" -ForegroundColor Gray
Write-Host "2. Distribute: Zip the LIPM-Package folder" -ForegroundColor Gray
Write-Host "3. Install: Create installer with Inno Setup" -ForegroundColor Gray
Write-Host ""
Read-Host "Press Enter to exit"
