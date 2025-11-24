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

# Check if Pillow is installed (required for icon processing)
echo "Checking for Pillow..."
if ! python -c "import PIL" 2>/dev/null; then
    echo "Pillow not found. Installing..."
    pip install pillow>=10.0.0
    if [ $? -ne 0 ]; then
        echo "ERROR: Failed to install Pillow. Please install manually: pip install pillow>=10.0.0"
        exit 1
    fi
    echo "Pillow installed successfully"
else
    echo "Pillow found - OK"
fi

# Verify icon file exists
echo ""
echo "Checking for icon file..."
if [ -f "assets/icons/pbl_logo_ICO.ico" ]; then
    echo "Icon file found: assets/icons/pbl_logo_ICO.ico"
    # Validate icon can be loaded by Pillow
    if python -c "from PIL import Image; img = Image.open('assets/icons/pbl_logo_ICO.ico'); print('Icon file is valid')" 2>/dev/null; then
        echo "Icon file validation passed"
    else
        echo "WARNING: Icon file exists but may be corrupted or invalid format."
        echo "Build will continue, but icon may not work correctly."
    fi
else
    echo "WARNING: Icon file not found at assets/icons/pbl_logo_ICO.ico"
    echo "Build will continue without icon."
fi

# Run PyInstaller
echo ""
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

