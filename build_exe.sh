#!/bin/bash
# Build script for creating Linux executable
# This script builds the stat_man_g executable using PyInstaller
# On Linux, this creates an ELF binary (not .exe)

echo "Building stat_man_g executable for Linux..."
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

# Check for UPX (optional compression tool)
echo ""
echo "Checking for UPX (compression tool)..."
if command -v upx >/dev/null 2>&1; then
    UPX_VERSION=$(upx --version 2>/dev/null | head -1 || echo "unknown")
    echo "✓ UPX found: $UPX_VERSION"
    echo "  Executable will be compressed (smaller file size)"
else
    echo "ℹ UPX not found - building without compression"
    echo "  Install UPX for smaller executables: sudo apt-get install upx-ucl"
fi

# Run PyInstaller with clean build
echo ""
echo "Running PyInstaller..."
python -m PyInstaller --clean --noconfirm stat_man_g.spec

if [ $? -ne 0 ]; then
    echo ""
    echo "Build failed! Check the output above for errors."
    exit 1
fi

# Ensure executable permissions are set (important for Linux/WSL)
if [ -f "dist/stat_man_g" ]; then
    # Set explicit permissions: rwxr-xr-x (755)
    # This ensures the file is readable and executable by owner and group
    chmod 755 dist/stat_man_g
    echo "Executable permissions set on dist/stat_man_g (755)"
    
    # Verify file type
    file_type=$(file -b dist/stat_man_g)
    echo "File type: $file_type"
    
    # Verify permissions
    file_perms=$(stat -c "%a" dist/stat_man_g 2>/dev/null || stat -f "%OLp" dist/stat_man_g 2>/dev/null || echo "unknown")
    echo "File permissions: $file_perms"
    
    # Verify it's readable and executable
    if [ -r "dist/stat_man_g" ] && [ -x "dist/stat_man_g" ]; then
        echo "✓ File is readable and executable"
    else
        echo "⚠ WARNING: File permissions may be incorrect"
        echo "  Readable: $([ -r dist/stat_man_g ] && echo 'YES' || echo 'NO')"
        echo "  Executable: $([ -x dist/stat_man_g ] && echo 'YES' || echo 'NO')"
        # Try to fix again with more explicit permissions
        chmod u+rwx,go+rx dist/stat_man_g
        echo "  Attempted to fix permissions again"
    fi
else
    echo "⚠ WARNING: Expected executable not found at dist/stat_man_g"
fi

echo ""
echo "Build successful!"
echo "Executable created at: dist/stat_man_g"
echo ""

# Verify the executable
if [ -f "dist/stat_man_g" ]; then
    # Check file type
    file_info=$(file -b dist/stat_man_g 2>/dev/null)
    echo "File verification:"
    echo "  Type: $file_info"
    
    # Check if it's a valid ELF executable
    if echo "$file_info" | grep -q "ELF.*executable"; then
        echo "  ✓ Valid ELF executable"
    else
        echo "  ⚠ WARNING: File may not be a valid executable"
    fi
    
    # Check size
    file_size=$(du -h dist/stat_man_g | cut -f1)
    echo "  Size: $file_size"
    
    echo ""
    echo "Debugging tips:"
    echo "  To enable console output for debugging, set:"
    echo "    export STATMANG_CONSOLE=1"
    echo "    ./build_exe.sh"
    echo ""
fi

echo "IMPORTANT - Copying the executable:"
echo "  When copying to another Linux directory, use:"
echo "    cp -p dist/stat_man_g /destination/path/"
echo "    # Then verify permissions: chmod 755 /destination/path/stat_man_g"
echo ""
echo "  When copying to Windows filesystem (e.g., /mnt/c/), permissions will be lost."
echo "  After copying, you may need to:"
echo "    chmod 755 /mnt/c/path/to/stat_man_g"
echo ""
echo "  For IDE access issues (if IDE can't read/execute):"
echo "    - Ensure you're accessing via WSL filesystem (not Windows mount)"
echo "    - Try: chmod 644 dist/stat_man_g && chmod +x dist/stat_man_g"
echo "    - Or set explicit: chmod 755 dist/stat_man_g"
echo ""

