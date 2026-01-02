# -*- mode: python ; coding: utf-8 -*-
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
        ('database', 'database'),  # database 폴더 전체를 배포판에 포함
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
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # GUI 프로그램이므로 콘솔 창 숨김
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='cmg-seqviewer.ico',
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
