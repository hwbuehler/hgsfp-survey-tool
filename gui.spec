# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for HGSFP Survey Tool GUI
Builds a single executable with all dependencies bundled
"""

from PyInstaller.utils.hooks import collect_submodules, collect_data_files
import os

# Collect all data files from dependencies
matplotlib_datas = collect_data_files('matplotlib')
sentence_transformers_datas = collect_data_files('sentence_transformers')

# Define all data files to include (use relative paths from current working directory)
datas = [
    # Include models directory
    ('models', 'models'),
    # Include fonts directory
    ('fonts', 'fonts'),
]

# Add external dependency data files
datas.extend(matplotlib_datas)
datas.extend(sentence_transformers_datas)

# Hidden imports for packages that may not be discovered automatically
hiddenimports = [
    'customtkinter',
    'CTkMessagebox',
    'sentence_transformers',
    'sklearn.cluster',
    'fpdf',
    'pypdf',
    'matplotlib.backends.backend_tkagg',
    'PIL',
]

a = Analysis(
    ['gui.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludedimports=[],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='HGSFP Survey Tool',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
