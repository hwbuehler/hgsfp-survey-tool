# Build script for HGSFP Survey Tool (PowerShell version)
# This script creates a single executable file for distribution

Write-Host ""
Write-Host "============================================"
Write-Host "HGSFP Survey Tool - PyInstaller Build Script"
Write-Host "============================================"
Write-Host ""

# Check if virtual environment is activated
if (-not $env:VIRTUAL_ENV) {
    Write-Host "Error: Virtual environment not activated." -ForegroundColor Red
    Write-Host "Please run: .\Scripts\Activate.ps1"
    exit 1
}

# Activate virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Cyan
& ".\Scripts\Activate.ps1"

Write-Host ""
Write-Host "Checking for PyInstaller..." -ForegroundColor Cyan
$pyinstallerCheck = pip show pyinstaller 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "Installing PyInstaller..." -ForegroundColor Yellow
    pip install pyinstaller
}

Write-Host ""
Write-Host "Building executable from gui.spec..." -ForegroundColor Cyan
Write-Host "This may take several minutes on first run (large model file)..."
Write-Host ""

pyinstaller gui.spec --distpath dist --buildpath build

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "ERROR: Build failed!" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "============================================"
Write-Host "Build completed successfully!" -ForegroundColor Green
Write-Host "============================================"
Write-Host ""
Write-Host "Your executable is located at:"
Write-Host "  dist\HGSFP-Survey-Tool.exe" -ForegroundColor Yellow
Write-Host ""
Write-Host "You can now distribute this executable to your coworkers."
Write-Host ""
