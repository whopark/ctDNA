# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for ctDNA Annotation Pipeline.
Build: pyinstaller ctdna.spec
Output: dist/ctDNA.exe (single-file Windows GUI app)
"""

import os

block_cipher = None
ROOT = os.path.dirname(os.path.abspath(SPEC))

a = Analysis(
    [os.path.join(ROOT, 'ctdna_gui.py')],
    pathex=[ROOT],
    binaries=[],
    datas=[
        (os.path.join(ROOT, 'template.docx'), '.'),
        (os.path.join(ROOT, 'kb.json'), '.'),
    ],
    hiddenimports=[
        'requests',
        'docx',
        'lxml',
        'lxml.etree',
        'lxml._elementpath',
        'frozen_path',
        'annotate_vcf',
        'reformat_tiers',
        'generate_clinical_reports',
        'kb',
        'kb_update',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    name='ctDNA',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,          # GUI app — no console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
