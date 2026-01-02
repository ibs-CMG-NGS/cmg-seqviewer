# -*- mode: python ; coding: utf-8 -*-
# macOS용 CMG-SeqViewer 빌드 설정

block_cipher = None

a = Analysis(
    ['src/main.py'],
    pathex=[],
    binaries=[],
    datas=[
        # Pre-loaded datasets 포함
        ('database', 'database'),
    ],
    hiddenimports=[
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
        'seaborn',
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
    [],
    exclude_binaries=True,
    name='CMG-SeqViewer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # macOS는 GUI 앱이므로 콘솔 숨김
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='cmg-seqviewer.icns',  # macOS는 .icns 형식 필요
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='CMG-SeqViewer',
)

# macOS .app 번들 생성
app = BUNDLE(
    coll,
    name='CMG-SeqViewer.app',
    icon='cmg-seqviewer.icns',
    bundle_identifier='com.yourorg.cmgseqviewer',  # 고유 식별자로 변경 필요
    version='1.0.0',
    info_plist={
        'NSPrincipalClass': 'NSApplication',
        'NSAppleScriptEnabled': False,
        'CFBundleDocumentTypes': [
            {
                'CFBundleTypeName': 'Excel Files',
                'CFBundleTypeRole': 'Viewer',
                'LSItemContentTypes': ['com.microsoft.excel.xls', 'org.openxmlformats.spreadsheetml.sheet'],
                'LSHandlerRank': 'Alternate',
            }
        ],
        'NSHighResolutionCapable': True,
    },
)
