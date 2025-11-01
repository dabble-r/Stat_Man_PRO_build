# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for stat_man_g Windows executable build.
This creates a standalone .exe that includes Python interpreter and all dependencies.
"""

import sys
from pathlib import Path

block_cipher = None

# Base directory for resolving paths
base_dir = Path('.')

# No icon - removed to avoid build issues
app_icon = None

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
        # No other assets bundled - icons folder excluded to avoid icon processing errors
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

# Build EXE without icon (no favicon)
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
)

