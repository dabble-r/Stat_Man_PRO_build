#!/bin/bash
# Build script for creating Windows executable (for WSL/Linux environments)
# This script builds the stat_man_g.exe using PyInstaller

echo "Building stat_man_g.exe..."
echo ""

# Check if PyInstaller is installed
if ! python -c "import PyInstaller" 2>/dev/null; then
    echo "PyInstaller not found. Installing..."
    pip install pyinstaller>=6.0.0
    if [ $? -ne 0 ]; then
        echo "Failed to install PyInstaller. Please install manually: pip install pyinstaller"
        exit 1
    fi
fi

# Run PyInstaller
echo "Running PyInstaller..."
pyinstaller stat_man_g.spec

if [ $? -ne 0 ]; then
    echo ""
    echo "Build failed! Check the output above for errors."
    exit 1
fi

echo ""
echo "Build successful!"
echo "Executable created at: dist/stat_man_g.exe"
echo ""

