# -*- mode: python ; coding: utf-8 -*-
# macOS용 CMG-SeqViewer 빌드 설정
import sys
from pathlib import Path

# Add src to path
src_path = str(Path('.').resolve() / 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

block_cipher = None

a = Analysis(
    ['src/main.py'],
    pathex=['src'],  # Add src to Python path
    binaries=[],
    datas=[
        # Pre-loaded datasets 포함
        ('database', 'database'),
        # Include entire src package
        ('src', 'src'),
    ],
    hiddenimports=[
        # PyQt6
        'PyQt6',
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        # Core modules - explicit imports
        'gui',
        'core',
        'models',
        'presenters',
        'utils',
        'workers',
        'src.gui.main_window',
        'src.gui.filter_panel',
        'src.gui.dataset_manager',
        'src.gui.database_browser',
        'src.gui.visualization_dialog',
        'src.gui.go_clustering_dialog',
        'src.gui.go_network_dialog',
        'src.gui.go_dot_plot_dialog',
        'src.gui.go_bar_chart_dialog',
        'src.gui.go_filter_dialog',
        'src.gui.help_dialog',
        'src.gui.venn_dialog',
        'src.gui.venn_dialog_comparison',
        'src.gui.comparison_panel',
        'src.gui.column_mapper_dialog',
        'src.gui.dataset_import_dialog',
        'src.gui.dataset_edit_dialog',
        'src.gui.scientific_delegate',
        'src.gui.workers',
        'src.core',
        'src.core.fsm',
        'src.core.logger',
        'src.models',
        'src.models.data_models',
        'src.models.standard_columns',
        'src.presenters',
        'src.presenters.main_presenter',
        'src.utils',
        'src.utils.data_loader',
        'src.utils.database_manager',
        'src.utils.statistics',
        'src.utils.go_clustering',
        'src.utils.go_kegg_loader',
        'src.workers',
        'src.workers.go_workers',
        # Data processing
        'pandas',
        'numpy',
        'scipy',
        'scipy.stats',
        'scipy.cluster',
        'scipy.cluster.hierarchy',
        'scipy.spatial',
        'scipy.spatial.distance',
        'openpyxl',
        'pyarrow',
        'pyarrow.parquet',
        'sklearn',
        'sklearn.cluster',
        # Visualization
        'matplotlib',
        'matplotlib.backends.backend_qt5agg',
        'matplotlib.backends.backend_qtagg',
        'matplotlib.figure',
        'matplotlib.pyplot',
        'seaborn',
        'matplotlib_venn',
        'networkx',
        'networkx.algorithms',
        'networkx.algorithms.community',
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
    debug=False,  # Disable debug for production
    bootloader_ignore_signals=False,
    strip=True,  # Strip symbols for smaller size
    upx=False,  # Disable UPX - can cause issues on macOS
    console=False,  # GUI app - no console window
    disable_windowed_traceback=False,
    argv_emulation=True,  # Enable for macOS compatibility
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='cmg-seqviewer.icns',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=True,
    upx=False,  # Disable UPX for better compatibility
    upx_exclude=[],
    name='CMG-SeqViewer',
)

# macOS .app 번들 생성
app = BUNDLE(
    coll,
    name='CMG-SeqViewer.app',
    icon='cmg-seqviewer.icns',
    bundle_identifier='com.ibs.cmgseqviewer',
    version='1.0.8',
    info_plist={
        'NSPrincipalClass': 'NSApplication',
        'NSAppleScriptEnabled': False,
        'LSMinimumSystemVersion': '10.13.0',  # macOS 10.13 High Sierra minimum
        'NSHighResolutionCapable': True,
        'NSRequiresAquaSystemAppearance': False,
        'CFBundleShortVersionString': '1.0.8',
        'CFBundleVersion': '1.0.8',
        'CFBundleName': 'CMG-SeqViewer',
        'CFBundleDisplayName': 'CMG-SeqViewer',
        'CFBundleExecutable': 'CMG-SeqViewer',
        'CFBundlePackageType': 'APPL',
        'CFBundleSignature': '????',
        'LSApplicationCategoryType': 'public.app-category.education',
        'NSHumanReadableCopyright': 'Copyright © 2025-2026 IBS-CMG',
        'CFBundleDocumentTypes': [
            {
                'CFBundleTypeName': 'Excel Files',
                'CFBundleTypeRole': 'Viewer',
                'LSItemContentTypes': ['com.microsoft.excel.xls', 'org.openxmlformats.spreadsheetml.sheet'],
                'LSHandlerRank': 'Alternate',
            }
        ],
    },
)
