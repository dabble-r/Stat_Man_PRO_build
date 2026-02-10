# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for stat_man_g executable build.
This creates a standalone executable that includes Python interpreter and all dependencies.
Works on both Windows (.exe) and Linux (ELF binary).
"""

import sys
import os
from pathlib import Path

block_cipher = None

# Detect platform
is_windows = sys.platform.startswith('win')
is_linux = sys.platform.startswith('linux')
is_macos = sys.platform.startswith('darwin')

# Helper function to check if UPX is available
def _check_upx_available():
    """Check if UPX compression tool is available."""
    import shutil
    upx_available = shutil.which('upx') is not None
    if upx_available:
        print("✓ UPX compression available - will compress executable")
    else:
        print("ℹ UPX not found - building without compression")
        print("  Install UPX for smaller executables: sudo apt-get install upx-ucl (Ubuntu/Debian)")
    return upx_available

# Helper function to get console setting (allows debugging)
def _get_console_setting():
    """Get console setting from environment variable or default to False."""
    # Allow enabling console for debugging via STATMANG_CONSOLE=1
    console_env = os.environ.get('STATMANG_CONSOLE', '').lower()
    if console_env in ('1', 'true', 'yes', 'on'):
        print("ℹ Console mode enabled (STATMANG_CONSOLE=1) - useful for debugging")
        return True
    return False  # Default: no console for GUI app

# Base directory for resolving paths - use spec file's directory
# This ensures paths work regardless of where PyInstaller is run from
spec_file_dir = Path(__file__).parent if '__file__' in globals() else Path(os.getcwd())
base_dir = spec_file_dir

# Application icon configuration (Windows uses .ico, Linux can use .png or skip)
app_icon = None
if is_windows:
    # Windows: use .ico file
    icon_path = base_dir / 'assets' / 'icons' / 'pbl_logo_ICO.ico'
    icon_path_abs = icon_path.resolve()
    
    if icon_path.exists() or icon_path_abs.exists():
        final_icon_path = icon_path_abs if icon_path_abs.exists() else icon_path
        app_icon = str(final_icon_path)
        
        # Verify icon can be processed (if Pillow is available)
        try:
            from PIL import Image
            test_img = Image.open(str(final_icon_path))
            print(f"✓ Using application icon: {app_icon}")
            print(f"  Icon format: {test_img.format}, Size: {test_img.size}")
        except ImportError:
            print(f"⚠ Using application icon: {app_icon}")
            print("  Warning: Pillow not available, cannot validate icon format")
        except Exception as e:
            print(f"⚠ Using application icon: {app_icon}")
            print(f"  Warning: Could not validate icon: {e}")
    else:
        print(f"✗ WARNING: Icon file not found")
        print(f"  Tried: {icon_path}")
        print(f"  Tried: {icon_path_abs}")
        print("  Building without icon.")
elif is_linux:
    # Linux: prefer .png for icons, but .ico can work too
    # Icons are optional on Linux and can be set at runtime
    icon_path_png = base_dir / 'assets' / 'icons' / 'pbl_logo.png'
    icon_path_ico = base_dir / 'assets' / 'icons' / 'pbl_logo_ICO.ico'
    
    if icon_path_png.exists():
        app_icon = str(icon_path_png.resolve())
        print(f"✓ Using application icon (PNG): {app_icon}")
    elif icon_path_ico.exists():
        app_icon = str(icon_path_ico.resolve())
        print(f"✓ Using application icon (ICO): {app_icon}")
        print("  Note: .ico format works but .png is preferred for Linux")
    else:
        app_icon = None
        print("ℹ Building Linux executable without embedded icon")
        print("  Icons can be set at runtime via QApplication.setWindowIcon()")
else:
    print(f"ℹ Platform {sys.platform} detected, building without icon")

# Collect PySide6 binaries and plugins
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

try:
    import PySide6
    # Collect PySide6 data files and dynamic libraries
    pyside6_datas = collect_data_files('PySide6')
    pyside6_binaries = collect_dynamic_libs('PySide6')
    
    # On Linux, explicitly collect Qt plugins directory (critical for GUI)
    # PyInstaller's collect_data_files should handle this, but we verify
    if is_linux:
        try:
            import PySide6
            pyside6_dir = Path(PySide6.__file__).parent
            
            # Check if plugins directory exists
            plugins_dir = pyside6_dir / 'Qt6' / 'plugins'
            if plugins_dir.exists():
                # collect_data_files('PySide6') should already include plugins
                # But we verify and add explicit plugin collection if needed
                print(f"✓ Qt plugins directory found at: {plugins_dir}")
                print(f"  Plugins should be included via collect_data_files('PySide6')")
            else:
                # Try alternative location
                plugins_dir_alt = pyside6_dir / 'plugins'
                if plugins_dir_alt.exists():
                    print(f"✓ Qt plugins directory found at: {plugins_dir_alt}")
                else:
                    print(f"⚠ Qt plugins directory not found (tried: {plugins_dir}, {plugins_dir_alt})")
                    print("  This may cause 'Qt platform plugin' errors at runtime")
        except Exception as e:
            print(f"⚠ Warning: Could not verify Qt plugins: {e}")
            print("  collect_data_files('PySide6') should include plugins automatically")
except ImportError:
    print("WARNING: PySide6 not found. Make sure PySide6 is installed in your build environment.")
    pyside6_datas = []
    pyside6_binaries = []

# Bundle assets folder so icon and other assets are available at runtime
# PyInstaller's tuple format (source, destination) bundles entire directory tree
assets_path = base_dir / 'assets'
assets_data = []
if assets_path.exists():
    # Tuple format: (source_path, destination_in_bundle)
    # This bundles the entire directory tree preserving structure
    assets_data = [(str(assets_path), 'assets')]
    print(f"✓ Bundling assets folder: {assets_path}")
    print(f"  Assets will be available at runtime in: assets/")
else:
    print(f"⚠ WARNING: Assets folder not found at {assets_path}")

# Bundle nl_sql directory so server scripts exist at runtime (FastAPI/MCP servers)
# When frozen, NLServerManager runs these via system Python; scripts must be on disk
nl_sql_path = base_dir / 'nl_sql'
nl_sql_data = []
if nl_sql_path.exists():
    nl_sql_data = [(str(nl_sql_path), 'nl_sql')]
    print(f"✓ Bundling nl_sql folder: {nl_sql_path}")
    print(f"  nl_sql will be available at runtime in: nl_sql/")
else:
    print(f"⚠ WARNING: nl_sql folder not found at {nl_sql_path}")

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=pyside6_binaries,
    datas=pyside6_datas + assets_data + nl_sql_data,
    hiddenimports=[
        'PySide6',
        'PySide6.QtCore',
        'PySide6.QtWidgets',
        'PySide6.QtGui',
        'PySide6.QtCharts',  # Used in stat_dialog_ui
        'PySide6.QtOpenGL',  # Often needed for Qt apps
        'sqlite3',
        # Natural Language Query dialog (lazy-imported from search_dialog)
        'pandas',
        'numpy',
        'matplotlib',
        'src.ui.dialogs.nl_query_dialog',
        # pkg_resources runtime hook (pyi_rth_pkgres) needs setuptools deps
        'pkg_resources',
        'jaraco',
        'jaraco.text',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'scipy',
        'IPython',
        'jupyter',
        'pytest',
    ],
    win_no_prefer_redirects=False,  # Ignored on non-Windows platforms
    win_private_assemblies=False,   # Ignored on non-Windows platforms
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# Build EXE with icon (if available)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='stat_man_g',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=_check_upx_available() if is_linux else False,  # UPX compression (only if available)
    upx_exclude=[],
    runtime_tmpdir=None,
    console=_get_console_setting(),  # Console window (configurable via env var)
    disable_windowed_traceback=False,
    argv_emulation=False if is_macos else None,  # macOS-specific
    target_arch=None,  # Auto-detect
    codesign_identity=None if is_macos else None,  # macOS-specific
    entitlements_file=None if is_macos else None,  # macOS-specific
    icon=app_icon,  # Application icon (None if file not found)
)

