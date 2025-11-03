#!/bin/bash
# Build script for creating Windows executable (for WSL/Linux environments)
# This script builds the stat_man_g.exe using PyInstaller

echo "Building stat_man_g.exe..."
echo ""

# Track actions for summary
VENV_ACTION=""
DEPS_INSTALLED=""
CLEANED_BUILD=false
BUILD_RESULT=""

# Function to check if a virtual environment is active
is_venv_active() {
    [ -n "$VIRTUAL_ENV" ]
}

# Function to check if a venv directory exists
venv_exists() {
    local venv_name=$1
    [ -d "$venv_name" ] && [ -f "$venv_name/bin/activate" ]
}

# Step 1: Check for and create/activate virtual environment
echo "=== Step 1: Checking virtual environment ==="
VENV_NAME=""
VENV_CREATED=false

# Check common venv names
if venv_exists "myenv"; then
    VENV_NAME="myenv"
    echo "Found existing virtual environment: myenv"
elif venv_exists ".myenv"; then
    VENV_NAME=".myenv"
    echo "Found existing virtual environment: .myenv"
elif venv_exists "venv"; then
    VENV_NAME="venv"
    echo "Found existing virtual environment: venv"
elif venv_exists "env"; then
    VENV_NAME="env"
    echo "Found existing virtual environment: env"
fi

if [ -n "$VENV_NAME" ]; then
    echo "Activating virtual environment: $VENV_NAME"
    source "$VENV_NAME/bin/activate"
    VENV_ACTION="Activated existing venv: $VENV_NAME"
else
    echo "No virtual environment found. Creating new venv: myenv"
    python3 -m venv myenv
    if [ $? -ne 0 ]; then
        echo "ERROR: Failed to create virtual environment."
        echo "Make sure python3-venv is installed: sudo apt-get install python3-venv"
        exit 1
    fi
    source myenv/bin/activate
    VENV_NAME="myenv"
    VENV_CREATED=true
    VENV_ACTION="Created and activated new venv: myenv"
fi

# Verify activation
if ! is_venv_active; then
    echo "ERROR: Virtual environment activation failed."
    exit 1
fi

echo "Using Python: $(python --version)"
echo "Python path: $(python -c 'import sys; print(sys.executable)')"
echo ""

# Step 2: Check for missing dependencies
echo "=== Step 2: Checking dependencies ==="
MISSING_DEPS=()

# Check if requirements.txt exists
if [ ! -f "requirements.txt" ]; then
    echo "WARNING: requirements.txt not found. Skipping dependency checks."
else
    # Read requirements.txt and check each package
    while IFS= read -r line || [ -n "$line" ]; do
        # Skip comments and empty lines
        [[ "$line" =~ ^#.*$ ]] && continue
        [[ -z "$line" ]] && continue
        
        # Extract package name (before >=, ==, etc.)
        pkg_name=$(echo "$line" | sed -E 's/([^>=<]+).*/\1/' | tr -d ' ')
        
        if [ -n "$pkg_name" ]; then
            if ! python -c "import $pkg_name" 2>/dev/null; then
                # Handle special case: PySide6 imports as PySide6
                if [ "$pkg_name" = "PySide6" ]; then
                    if ! python -c "import PySide6" 2>/dev/null; then
                        MISSING_DEPS+=("$line")
                        echo "  Missing: $line"
                    fi
                # Handle special case: pillow imports as PIL
                elif [ "$pkg_name" = "pillow" ] || [ "$pkg_name" = "Pillow" ]; then
                    if ! python -c "import PIL" 2>/dev/null; then
                        MISSING_DEPS+=("$line")
                        echo "  Missing: $line"
                    fi
                # Handle special case: pyinstaller
                elif [ "$pkg_name" = "pyinstaller" ] || [ "$pkg_name" = "PyInstaller" ]; then
                    if ! python -c "import PyInstaller" 2>/dev/null; then
                        MISSING_DEPS+=("$line")
                        echo "  Missing: $line"
                    fi
                else
                    MISSING_DEPS+=("$line")
                    echo "  Missing: $line"
                fi
            fi
        fi
    done < requirements.txt
fi

# Step 3: Install missing dependencies
if [ ${#MISSING_DEPS[@]} -eq 0 ]; then
    echo "All required dependencies are already installed."
    DEPS_INSTALLED="All dependencies already present"
else
    echo ""
    echo "=== Step 3: Installing missing dependencies ==="
    echo "Installing dependencies from requirements.txt..."
    
    python -m pip install --upgrade pip
    python -m pip install -r requirements.txt
    
    if [ $? -ne 0 ]; then
        echo "ERROR: Failed to install required dependencies."
        echo "Please install manually: pip install -r requirements.txt"
        exit 1
    fi
    
    DEPS_INSTALLED="Installed ${#MISSING_DEPS[@]} missing package(s)"
fi

# Step 4: Verify critical dependencies
echo ""
echo "=== Step 4: Verifying critical dependencies ==="
if python -c "import PySide6; print('PySide6 version:', PySide6.__version__)" 2>/dev/null; then
    echo "✓ PySide6 found"
else
    echo "ERROR: PySide6 not found after installation."
    exit 1
fi

if python -c "import PyInstaller" 2>/dev/null; then
    echo "✓ PyInstaller found"
else
    echo "ERROR: PyInstaller not found after installation."
    exit 1
fi

# Step 5: Clean previous build
echo ""
echo "=== Step 5: Cleaning previous build ==="
if [ -d "build" ]; then
    rm -rf build
    echo "Removed build/ directory"
    CLEANED_BUILD=true
fi

if [ -d "dist" ]; then
    rm -rf dist
    echo "Removed dist/ directory"
    CLEANED_BUILD=true
fi

if [ "$CLEANED_BUILD" = false ]; then
    echo "No previous build artifacts to clean"
fi

# Step 6: Run PyInstaller
echo ""
echo "=== Step 6: Running PyInstaller ==="
python -m PyInstaller --clean stat_man_g.spec

if [ $? -ne 0 ]; then
    echo ""
    echo "Build failed! Check the output above for errors."
    BUILD_RESULT="FAILED"
else
    BUILD_RESULT="SUCCESS"
fi

# Step 7: Summary
echo ""
echo "========================================="
echo "           BUILD SUMMARY"
echo "========================================="
echo "Virtual Environment: $VENV_ACTION"
echo "Dependencies: $DEPS_INSTALLED"
if [ "$CLEANED_BUILD" = true ]; then
    echo "Build Cleanup: Removed previous build artifacts"
else
    echo "Build Cleanup: No cleanup needed"
fi
echo "Build Result: $BUILD_RESULT"
if [ "$BUILD_RESULT" = "SUCCESS" ]; then
    echo "Executable Location: dist/stat_man_g.exe"
fi
echo "========================================="
echo ""

if [ "$BUILD_RESULT" = "FAILED" ]; then
    exit 1
fi