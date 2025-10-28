#!/bin/bash
# Build script for creating desktop executable with PyInstaller

echo "Building OCR Proofreading Desktop Application..."

# Check if PyInstaller is installed
if ! python3 -m PyInstaller --version > /dev/null 2>&1; then
    echo "PyInstaller not found. Installing..."
    pip install pyinstaller
fi

# Create executable
python3 -m PyInstaller \
    --name="OCR-Proofread" \
    --windowed \
    --onefile \
    --add-data="config.yaml:." \
    --hidden-import="PIL._tkinter_finder" \
    run_desktop.py

echo "Build complete! Executable is in dist/OCR-Proofread"
