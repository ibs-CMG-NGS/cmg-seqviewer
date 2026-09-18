# -*- mode: python ; coding: utf-8 -*-
# Single-file executable version (slower startup, easier distribution)

# GO/KEGG Enrichment Engine 번들 (plan §8/G1)
from PyInstaller.utils.hooks import collect_all, collect_submodules, collect_data_files
_datas, _binaries, _hidden = [], [], []
for _pkg in ('gseapy', 'goatools', 'mygene'):
    _d, _b, _h = collect_all(_pkg)
    _datas += _d; _binaries += _b; _hidden += _h
_datas += collect_data_files('goatools')
_hidden += collect_submodules('statsmodels')

block_cipher = None

a = Analysis(
    ['src/main.py'],
    pathex=[],
    binaries=_binaries,
    datas=[
        # Pre-loaded datasets 포함
        ('database', 'database'),
        ('src', 'src'),  # 번들 export 재현 스크립트가 render 소스를 inline 하려면 필요
        ('data/orthologs/ortholog_map.csv.gz', 'data/orthologs'),  # cross-species 메타(M2)
        ('docs/user/help', 'docs/user/help'),  # F1 markdown help (HELP_SYSTEM_OVERHAUL)
    ] + _datas,
    hiddenimports=[
        *_hidden,
        'PyQt6',
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        'pandas',
        'numpy',
        'scipy',
        'scipy.stats',
        'openpyxl',
        'pyarrow',
        'pyarrow.parquet',
        'matplotlib',
        'matplotlib.backends.backend_qt5agg',
        'matplotlib.backends.backend_agg',
        'matplotlib.backends.backend_pdf',
        'matplotlib.backends.backend_svg',
        'seaborn',
        'adjustText',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib.tests',
        'numpy.tests',
        'pandas.tests',
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
    name='CMG-SeqViewer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='cmg-seqviewer.ico',
)
