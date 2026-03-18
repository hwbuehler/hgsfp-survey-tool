@echo off
REM Build script for HGSFP Survey Tool
REM This script creates a single executable file for distribution

echo.
echo ============================================
echo HGSFP Survey Tool - PyInstaller Build Script
echo ============================================
echo.

REM Check if virtual environment is activated
if not defined VIRTUAL_ENV (
    echo Error: Virtual environment not activated.
    echo Please run: .\Scripts\Activate.bat
    exit /b 1
)

echo Activating virtual environment...
call Scripts\Activate.bat

echo.
echo Checking for PyInstaller...
pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo Installing PyInstaller...
    pip install pyinstaller
)

echo.
echo Building executable from gui.spec...
echo This may take several minutes on first run (large model file)...
echo.

pyinstaller gui.spec --distpath dist --buildpath build

if errorlevel 1 (
    echo.
    echo ERROR: Build failed!
    exit /b 1
)

echo.
echo ============================================
echo Build completed successfully!
echo ============================================
echo.
echo Your executable is located at:
echo   dist\HGSFP-Survey-Tool.exe
echo.
echo You can now distribute this executable to your coworkers.
echo.
pause
