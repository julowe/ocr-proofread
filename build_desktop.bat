@echo off
REM Build script for creating desktop executable with PyInstaller (Windows)

echo Building OCR Proofreading Desktop Application...

REM Check if PyInstaller is installed
python -m PyInstaller --version >nul 2>&1
if %errorlevel% neq 0 (
    echo PyInstaller not found. Installing...
    pip install pyinstaller
)

REM Create executable
python -m PyInstaller ^
    --name=OCR-Proofread ^
    --windowed ^
    --onefile ^
    --add-data="config.yaml;." ^
    --hidden-import="PIL._tkinter_finder" ^
    run_desktop.py

echo Build complete! Executable is in dist\OCR-Proofread.exe
pause
