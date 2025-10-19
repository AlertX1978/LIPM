# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for LinkedIn Post Monitor (LIPM)
Bundles all dependencies into a standalone Windows executable
"""

import sys
from pathlib import Path

block_cipher = None

# Application metadata
APP_NAME = 'LIPM'
APP_VERSION = '1.0.0'
APP_DESCRIPTION = 'LinkedIn Personal Monitor - Automated LinkedIn Post Monitoring'
APP_AUTHOR = 'Aleksey Tkachyov'

# Collect all project files
a = Analysis(
    ['linkedin_post_monitor\\main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('config.template.json', '.'),
        ('README.md', '.'),
        ('requirements.txt', '.'),
    ],
    hiddenimports=[
        'playwright',
        'playwright.async_api',
        'cryptography',
        'cryptography.fernet',
        'cryptography.hazmat.primitives.ciphers',
        'cryptography.hazmat.primitives.ciphers.aead',
        'openai',
        'openai.resources',
        'telegram',
        'telegram.ext',
        'customtkinter',
        'PIL',
        'PIL._tkinter_finder',
        'tkinter',
        '_tkinter',
        'asyncio',
        'aiohttp',
        'certifi',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'numpy',
        'pandas',
        'scipy',
        'pytest',
        'setuptools',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='LIPM',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # No console window (GUI app)
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # Add icon path here if you have one: 'resources/icon.ico'
    version_file=None,
)

# Optional: Create a COLLECT for one-folder distribution (commented out for one-file)
# coll = COLLECT(
#     exe,
#     a.binaries,
#     a.zipfiles,
#     a.datas,
#     strip=False,
#     upx=True,
#     upx_exclude=[],
#     name='LIPM',
# )
