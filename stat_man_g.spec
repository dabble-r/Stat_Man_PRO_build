# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for stat_man_g Windows executable build.
This creates a standalone .exe that includes Python interpreter and all dependencies.
"""

import sys
import os
from pathlib import Path

block_cipher = None

# Base directory for resolving paths - use spec file's directory
# This ensures paths work regardless of where PyInstaller is run from
spec_file_dir = Path(__file__).parent if '__file__' in globals() else Path(os.getcwd())
base_dir = spec_file_dir

# Application icon configuration
icon_path = base_dir / 'assets' / 'icons' / 'pbl_logo_ICO.ico'
icon_path_abs = icon_path.resolve()

if icon_path.exists() or icon_path_abs.exists():
    # Use the absolute path that exists
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
    app_icon = None
    print(f"✗ WARNING: Icon file not found")
    print(f"  Tried: {icon_path}")
    print(f"  Tried: {icon_path_abs}")
    print(f"  Current working directory: {os.getcwd()}")
    print(f"  Spec file directory: {spec_file_dir}")
    print("  Building without icon.")

# Collect PySide6 binaries and plugins
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

try:
    import PySide6
    # Collect PySide6 data files and DLLs
    pyside6_datas = collect_data_files('PySide6')
    pyside6_binaries = collect_dynamic_libs('PySide6')
except ImportError:
    print("WARNING: PySide6 not found. Make sure PySide6 is installed in your build environment.")
    pyside6_datas = []
    pyside6_binaries = []

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=pyside6_binaries,
    datas=pyside6_datas + [
        # Icon file is handled separately via app_icon parameter
    ],
    hiddenimports=[
        'PySide6',
        'PySide6.QtCore',
        'PySide6.QtWidgets',
        'PySide6.QtGui',
        'PySide6.QtCharts',  # Used in stat_dialog_ui
        'PySide6.QtOpenGL',  # Often needed for Qt apps
        'sqlite3',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'numpy',
        'pandas',
        'scipy',
        'IPython',
        'jupyter',
        'pytest',
        'setuptools',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
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
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # No console window for GUI app
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=app_icon,  # Application icon (None if file not found)
)

