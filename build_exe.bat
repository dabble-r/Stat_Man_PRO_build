@echo off
REM Build script for creating Windows executable
REM This script builds the stat_man_g.exe using PyInstaller

echo Building stat_man_g.exe...
echo.

REM Try to activate virtual environment if it exists
REM Check common venv names
if exist "myenv\Scripts\activate.bat" (
    echo Activating virtual environment: myenv
    call myenv\Scripts\activate.bat
) else if exist ".myenv\Scripts\activate.bat" (
    echo Activating virtual environment: .myenv
    call .myenv\Scripts\activate.bat
) else if exist "venv\Scripts\activate.bat" (
    echo Activating virtual environment: venv
    call venv\Scripts\activate.bat
) else if exist "env\Scripts\activate.bat" (
    echo Activating virtual environment: env
    call env\Scripts\activate.bat
) else (
    echo WARNING: No virtual environment found. Using system Python.
    echo Make sure PySide6 is installed in the current Python environment.
)

REM Verify we're using the right Python
echo.
echo Using Python: 
python --version
echo Python path:
python -c "import sys; print(sys.executable)"

REM Install/upgrade required dependencies from requirements.txt
echo.
echo Installing required dependencies...
python -m pip install -q -r requirements.txt
if errorlevel 1 (
    echo Failed to install required dependencies. Please install manually:
    echo   pip install -r requirements.txt
    pause
    exit /b 1
)

REM Verify PySide6 is installed (required for application)
echo Checking for PySide6...
python -c "import PySide6; print('PySide6 version:', PySide6.__version__)" 2>nul
if errorlevel 1 (
    echo ERROR: PySide6 not found in current Python environment.
    echo Make sure you have activated your virtual environment that contains PySide6.
    echo Or install it: pip install PySide6
    pause
    exit /b 1
)
echo PySide6 found - OK

REM Verify Pillow is installed (required for icon processing)
echo Checking for Pillow...
python -c "import PIL; print('Pillow version:', PIL.__version__)" 2>nul
if errorlevel 1 (
    echo ERROR: Pillow not found. Pillow is required for icon processing.
    echo Installing Pillow...
    python -m pip install pillow>=10.0.0
    if errorlevel 1 (
        echo ERROR: Failed to install Pillow. Please install manually:
        echo   pip install pillow>=10.0.0
        pause
        exit /b 1
    )
    echo Pillow installed successfully
) else (
    echo Pillow found - OK
)

REM Verify icon file exists
echo.
echo Checking for icon file...
if exist "assets\icons\pbl_logo_ICO.ico" (
    echo Icon file found: assets\icons\pbl_logo_ICO.ico
    REM Validate icon can be loaded by Pillow
    python -c "from PIL import Image; img = Image.open('assets/icons/pbl_logo_ICO.ico'); print('Icon file is valid')" 2>nul
    if errorlevel 1 (
        echo WARNING: Icon file exists but may be corrupted or invalid format.
        echo Build will continue, but icon may not work correctly.
    ) else (
        echo Icon file validation passed
    )
) else (
    echo WARNING: Icon file not found at assets\icons\pbl_logo_ICO.ico
    echo Build will continue without icon.
)

REM Clean previous build
echo.
echo Cleaning previous build...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

REM Run PyInstaller using the active Python
echo.
echo Running PyInstaller...
python -m PyInstaller --clean stat_man_g.spec

if errorlevel 1 (
    echo.
    echo Build failed! Check the output above for errors.
    pause
    exit /b 1
)

echo.
echo Build successful!
echo Executable created at: dist\stat_man_g.exe
echo.
pause

