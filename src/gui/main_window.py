"""
Main Window for RNA-Seq Data Analysis Program

Excel 스타일의 메인 윈도우를 구현합니다.
"""

from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                            QSplitter, QTabWidget, QTableWidget, QTableWidgetItem,
                            QTextEdit, QMenuBar, QMenu, QToolBar, QStatusBar,
                            QLabel, QPushButton, QFileDialog, QMessageBox,
                            QProgressBar, QInputDialog, QLineEdit, QHeaderView,
                            QSizePolicy, QDialog, QToolButton, QFrame,
                            QDockWidget, QScrollArea)
from PyQt6.QtCore import Qt, pyqtSignal, QThread
from PyQt6.QtGui import QAction, QIcon, QFont, QActionGroup, QPixmap
import logging
import math
from pathlib import Path
from typing import Optional, List, Dict
import pandas as pd

from core.fsm import FSM, State, Event
from core.logger import QtLogHandler, LogBuffer, get_audit_logger
from gui.filter_panel import FilterPanel
from gui.dataset_tree_panel import DatasetTreePanel
from gui.comparison_panel import ComparisonPanel
from gui.visualization_dialog import VolcanoPlotWidget, VolcanoPlotDialog, HeatmapWidget, HeatmapDialog, PadjHistogramDialog, DotPlotDialog
from gui.pca_dialog import PCADialog
from gui.venn_dialog import VennDiagramDialog
from gui.venn_dialog_comparison import VennDiagramFromComparisonDialog
from gui.upset_plot_dialog import UpsetPlotDialog
from gui.help_dialog import HelpDialog
from gui.multi_omics_panel import MultiOmicsPanel
from models.data_models import FilterMode, DatasetType
from presenters.main_presenter import MainPresenter


class NumericTableWidgetItem(QTableWidgetItem):
    """숫자 정렬을 지원하는 QTableWidgetItem"""

    def __init__(self, value, display_text):
        super().__init__(display_text)
        self.numeric_value = value

    def __lt__(self, other):
        """정렬을 위한 비교 연산자.

        NaN은 IEEE754 규칙상 모든 비교(<, >)가 항상 False라서, 정렬 알고리즘이
        요구하는 전순서(total order)가 깨진다. NaN을 항상 "가장 큰 값"으로
        취급해 일관되게 비교해야 NaN과 무관한 다른 행들의 순서도 깨지지 않는다
        (pandas의 na_position='last'와 동일한 관례).
        """
        if isinstance(other, NumericTableWidgetItem):
            a, b = self.numeric_value, other.numeric_value
            a_nan = isinstance(a, float) and math.isnan(a)
            b_nan = isinstance(b, float) and math.isnan(b)
            if a_nan or b_nan:
                return False if a_nan else True
            return a < b
        return super().__lt__(other)


class MainWindow(QMainWindow):
    """
    메인 윈도우 (Parent Window)
    
    Excel과 유사한 구조를 가진 GUI를 제공합니다.
    - 좌측: 필터 패널 및 유전자 입력
    - 우측: 데이터 뷰 (탭 형태)
    - 하단: 로그 터미널
    """
    
    def __init__(self):
        super().__init__()
        
        self.logger = logging.getLogger(__name__)
        self.audit_logger = get_audit_logger()
        
        # QSettings 초기화 (UI 설정 저장/복원용)
        from PyQt6.QtCore import QSettings
        self.settings = QSettings("RNASeqDataView", "MainWindow")
        
        # Presenter 초기화 (MVP 패턴)
        self.presenter = MainPresenter(self)
        
        # Presenter 시그널 연결
        self.presenter.filter_completed.connect(self._on_filter_completed)
        self.presenter.error_occurred.connect(self._on_presenter_error)
        self.presenter.progress_updated.connect(self._on_progress_updated)
        
        # 설정 값
        self.column_display_level = "basic"  # "basic", "de", "full" - 기본값: basic
        self.decimal_precision = 3
        
        # 각 탭의 원본 데이터 저장 (탭 인덱스 -> (DataFrame, Dataset))
        self.tab_data: Dict[int, dict] = {}
        
        # 최근 파일 히스토리 (최대 10개)
        self.recent_files = []
        self.max_recent_files = 10
        self._load_recent_files()

        # 최근 프로젝트 히스토리
        self.recent_projects: list = []
        self._load_recent_projects()
        
        # Database Manager 초기화
        from utils.database_manager import DatabaseManager
        self.db_manager = DatabaseManager()
        
        # FSM 상태 변경 리스너 등록
        self.presenter.fsm.add_state_change_listener(self._on_state_changed)
        
        # GUI 초기화
        self._init_ui()
        self._create_menu_bar()
        # self._create_tool_bar()  # 툴바 제거 (세로 공간 절약)
        self._create_status_bar()
        
        # UI 설정 복원
        self._restore_ui_settings()
        
        # 로그 핸들러 연결
        self._setup_logging()
        
        # 메뉴는 항상 활성화 상태 유지
        
        self.logger.info("Main window initialized")
        self.audit_logger.log_action("Application Started")
    
    def _init_ui(self):
        """UI 구성 요소 초기화"""
        self.setWindowTitle("CMG-SeqViewer")
        self.setGeometry(100, 100, 1400, 900)
        self.setMinimumSize(1280, 720)  # 최소 창 크기 설정
        
        # Window Icon 설정
        self._set_window_icon()
        
        # 중앙 위젯
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 메인 레이아웃
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)

        # ── 3-way horizontal splitter ──────────────────────────────────
        # [트리 패널] | [기능 패널] | [데이터 탭]
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.main_splitter.setChildrenCollapsible(False)  # 드래그로 완전 접힘 방지

        # ── 패널 0: Dataset Tree ───────────────────────────────────────
        tree_container = QWidget()
        tree_container.setMinimumWidth(140)
        tree_container.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        tree_container_layout = QVBoxLayout(tree_container)
        tree_container_layout.setContentsMargins(0, 0, 0, 0)
        tree_container_layout.setSpacing(0)

        # 트리 헤더 (제목)
        tree_header = QWidget()
        tree_header.setStyleSheet("background:#f5f5f5; border-bottom:1px solid #ddd;")
        tree_header_layout = QHBoxLayout(tree_header)
        tree_header_layout.setContentsMargins(6, 3, 3, 3)
        tree_title = QLabel("Datasets")
        tree_title.setStyleSheet("font-weight:bold; font-size:11px;")
        tree_header_layout.addWidget(tree_title)
        tree_container_layout.addWidget(tree_header)

        self.dataset_manager = DatasetTreePanel()
        self.dataset_manager.dataset_selected.connect(self._on_dataset_selected)
        self.dataset_manager.add_requested.connect(self._on_add_dataset)
        self.dataset_manager.dataset_removed.connect(self._on_dataset_removed)
        self.dataset_manager.rename_requested.connect(self._on_dataset_renamed)
        self.dataset_manager.sheet_rename_requested.connect(self._on_sheet_renamed)
        self.dataset_manager.file_dropped.connect(self._on_file_dropped)
        self.dataset_manager.sheet_selected.connect(self._on_tree_sheet_selected)
        self.dataset_manager.dataset_added.connect(self._on_dataset_tree_root_added)
        tree_container_layout.addWidget(self.dataset_manager)
        self.tree_container = tree_container
        self.main_splitter.addWidget(tree_container)

        # ── 패널 1: 기능 패널 (필터 + 비교) ───────────────────────────
        func_container = QWidget()
        func_container.setMinimumWidth(200)
        func_container.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        func_container_layout = QVBoxLayout(func_container)
        func_container_layout.setContentsMargins(0, 0, 0, 0)
        func_container_layout.setSpacing(0)

        # 기능 패널 헤더 (제목)
        func_header = QWidget()
        func_header.setStyleSheet("background:#f5f5f5; border-bottom:1px solid #ddd;")
        func_header_layout = QHBoxLayout(func_header)
        func_header_layout.setContentsMargins(6, 3, 3, 3)
        func_title = QLabel("Filter / Compare")
        func_title.setStyleSheet("font-weight:bold; font-size:11px;")
        func_header_layout.addWidget(func_title)
        func_container_layout.addWidget(func_header)

        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 4, 0, 0)
        left_layout.setSpacing(5)

        self.filter_panel = FilterPanel()
        self.filter_panel.filter_requested.connect(self._on_filter_requested)
        self.filter_panel.analysis_requested.connect(self._on_analysis_requested)
        left_layout.addWidget(self.filter_panel)

        self.comparison_panel = ComparisonPanel()
        self.comparison_panel.compare_requested.connect(self._on_comparison_requested)
        left_layout.addWidget(self.comparison_panel)

        self.multi_omics_panel = MultiOmicsPanel()
        self.multi_omics_panel.integrate_requested.connect(self._on_integrate_requested)
        self.filter_panel.add_multi_omics_tab(self.multi_omics_panel)

        # 버튼 행을 QWidget으로 감싸서 show/hide 가능하게 함
        self.action_buttons_widget = QWidget()
        button_layout = QHBoxLayout(self.action_buttons_widget)
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setSpacing(5)
        button_layout.addWidget(self.filter_panel.apply_filter_btn)
        button_layout.addWidget(self.comparison_panel.compare_btn)
        left_layout.addWidget(self.action_buttons_widget)

        # RNA+ATAC 탭 전환 시 ComparisonPanel / 버튼 행 자동 show/hide
        self.filter_panel.filter_tabs.currentChanged.connect(self._on_filter_tab_changed)

        func_container_layout.addWidget(left_widget)
        self.func_container = func_container
        self.main_splitter.addWidget(func_container)

        # ── 패널 2: 데이터 탭 ─────────────────────────────────────────
        self.data_tabs = QTabWidget()
        self.data_tabs.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.data_tabs.setTabsClosable(True)
        self.data_tabs.tabCloseRequested.connect(self._on_tab_close_requested)
        self.data_tabs.currentChanged.connect(self._on_tab_changed)
        self.data_tabs.setAcceptDrops(True)
        self.data_tabs.dragEnterEvent = self._data_tabs_drag_enter
        self.data_tabs.dropEvent = self._data_tabs_drop
        self.main_splitter.addWidget(self.data_tabs)

        # splitter 스트레치 / collapsible 설정
        self.main_splitter.setStretchFactor(0, 0)
        self.main_splitter.setStretchFactor(1, 0)
        self.main_splitter.setStretchFactor(2, 1)
        self.main_splitter.setCollapsible(0, False)
        self.main_splitter.setCollapsible(1, False)
        self.main_splitter.setCollapsible(2, False)

        # ── Plot Settings Dock (우측) ─────────────────────────────────
        self.plot_settings_dock = QDockWidget("Plot Settings", self)
        self.plot_settings_dock.setObjectName("PlotSettingsDock")
        self.plot_settings_dock.setAllowedAreas(
            Qt.DockWidgetArea.RightDockWidgetArea | Qt.DockWidgetArea.LeftDockWidgetArea
        )
        self.plot_settings_dock.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable |
            QDockWidget.DockWidgetFeature.DockWidgetFloatable |
            QDockWidget.DockWidgetFeature.DockWidgetClosable
        )
        self.plot_settings_dock.setMinimumWidth(300)
        # 빈 placeholder 위젯으로 초기화
        _dock_placeholder = QLabel("No plot settings")
        _dock_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        _dock_placeholder.setStyleSheet("color: grey; font-size: 11px;")
        self.plot_settings_dock.setWidget(_dock_placeholder)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.plot_settings_dock)
        self.plot_settings_dock.hide()
        self._current_settings_widget: QWidget | None = None  # 현재 도크에 들어있는 설정 패널

        # 패널 크기 저장용 (숨기기/복원)
        self._tree_panel_width: int = 200
        self._func_panel_width: int = 260
        self._split_view_active: bool = False

        # 초기 상태: 트리 숨김, 필터 표시
        self.tree_container.setVisible(False)
        self.main_splitter.setSizes([0, 260, 940])

        # 초기 탭 생성
        self._create_data_tab("Whole Dataset")

        # Activity Bar + Main Splitter 래이아웃
        content_widget = QWidget()
        content_layout = QHBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        content_layout.addWidget(self._build_activity_bar())
        content_layout.addWidget(self.main_splitter)
        main_layout.addWidget(content_widget, stretch=100)
        
        # 하단: 로그 터미널 (폰트 8pt 기준 5줄 표시)
        self.log_terminal = QTextEdit()
        self.log_terminal.setReadOnly(True)
        self.log_terminal.setMinimumHeight(90)   # 5줄 최소 높이
        self.log_terminal.setMaximumHeight(110)  # 5줄 최대 높이
        self.log_terminal.setSizePolicy(
            QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        )
        self.log_terminal.setFont(QFont("Consolas", 9))  # 폰트 크기 9pt
        self.log_terminal.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #3e3e3e;
            }
        """)
        main_layout.addWidget(self.log_terminal)
        
        # 로그 버퍼
        self.log_buffer = LogBuffer()
    
    def _create_menu_bar(self):
        """메뉴바 생성"""
        menubar = self.menuBar()
        
        # 메뉴바 폰트 크기 설정
        menubar.setStyleSheet("""
            QMenuBar {
                font-size: 10pt;
            }
            QMenuBar::item {
                padding: 4px 8px;
            }
            QMenu {
                font-size: 10pt;
            }
            QMenu::item {
                padding: 4px 20px;
            }
        """)
        
        # File 메뉴
        file_menu = menubar.addMenu("&File")
        
        self.open_action = QAction("&Open Dataset...", self)
        self.open_action.setShortcut("Ctrl+O")
        self.open_action.triggered.connect(self._on_open_dataset)
        file_menu.addAction(self.open_action)
        
        self.open_genes_action = QAction("Open Gene List...", self)
        self.open_genes_action.triggered.connect(self._on_open_gene_list)
        file_menu.addAction(self.open_genes_action)
        
        # GO/KEGG 결과 로딩
        self.open_go_kegg_action = QAction("Open GO/KEGG Results...", self)
        self.open_go_kegg_action.setShortcut("Ctrl+G")
        self.open_go_kegg_action.triggered.connect(self._on_open_go_kegg_results)
        file_menu.addAction(self.open_go_kegg_action)

        self.open_atac_action = QAction("Open ATAC-seq Dataset...", self)
        self.open_atac_action.setShortcut("Ctrl+A")
        self.open_atac_action.triggered.connect(self._on_open_atac_dataset)
        file_menu.addAction(self.open_atac_action)

        self.open_motif_action = QAction("Open TF Motif Results...", self)
        self.open_motif_action.triggered.connect(self._on_open_motif_results)
        file_menu.addAction(self.open_motif_action)

        self.open_footprint_action = QAction("Open TF Footprint Results...", self)
        self.open_footprint_action.triggered.connect(self._on_open_footprint_results)
        file_menu.addAction(self.open_footprint_action)

        self.open_chromvar_action = QAction("Open chromVAR Results...", self)
        self.open_chromvar_action.triggered.connect(self._on_open_chromvar_results)
        file_menu.addAction(self.open_chromvar_action)

        file_menu.addSeparator()
        
        # Database 서브메뉴
        database_menu = file_menu.addMenu("📚 Database")
        
        self.db_browser_action = QAction("Browse Pre-loaded Datasets...", self)
        self.db_browser_action.setShortcut("Ctrl+B")
        self.db_browser_action.triggered.connect(self._on_open_database_browser)
        database_menu.addAction(self.db_browser_action)
        
        self.db_import_action = QAction("Import Current Dataset to Database...", self)
        self.db_import_action.setShortcut("Ctrl+I")
        self.db_import_action.triggered.connect(self._on_import_to_database)
        database_menu.addAction(self.db_import_action)
        
        file_menu.addSeparator()

        # 프로젝트 저장/불러오기
        self.save_project_action = QAction("Save Project...", self)
        self.save_project_action.setShortcut("Ctrl+Shift+S")
        self.save_project_action.triggered.connect(self._on_save_project)
        file_menu.addAction(self.save_project_action)

        self.open_project_action = QAction("Open Project...", self)
        self.open_project_action.setShortcut("Ctrl+Shift+O")
        self.open_project_action.triggered.connect(self._on_open_project)
        file_menu.addAction(self.open_project_action)

        file_menu.addSeparator()

        # 최근 파일 메뉴
        self.recent_menu = file_menu.addMenu("Recent Files")
        self._update_recent_files_menu()

        # 최근 프로젝트 메뉴
        self.recent_projects_menu = file_menu.addMenu("Recent Projects")
        self._update_recent_projects_menu()

        file_menu.addSeparator()
        
        self.export_action = QAction("&Export Current Tab...", self)
        self.export_action.setShortcut("Ctrl+E")
        self.export_action.triggered.connect(self._on_export_data)
        # 항상 활성화
        file_menu.addAction(self.export_action)

        self.export_multi_omics_action = QAction("Export Multi-Omics Results (Excel)...", self)
        self.export_multi_omics_action.triggered.connect(self._on_export_multi_omics)
        file_menu.addAction(self.export_multi_omics_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("E&xit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Analysis 메뉴
        analysis_menu = menubar.addMenu("&Analysis")
        
        self.filter_action = QAction("Apply &Filter", self)
        self.filter_action.setShortcut("Ctrl+F")
        self.filter_action.triggered.connect(self._on_filter_requested)
        # 항상 활성화
        analysis_menu.addAction(self.filter_action)
        
        self.fisher_action = QAction("Fisher's Exact Test", self)
        self.fisher_action.triggered.connect(lambda: self._on_analysis_requested("fisher"))
        # 항상 활성화
        analysis_menu.addAction(self.fisher_action)
        
        self.gsea_action = QAction("GSEA Lite", self)
        self.gsea_action.triggered.connect(lambda: self._on_analysis_requested("gsea"))
        # 항상 활성화
        analysis_menu.addAction(self.gsea_action)
        
        analysis_menu.addSeparator()
        
        self.compare_action = QAction("Compare Datasets...", self)
        self.compare_action.triggered.connect(self._on_compare_datasets)
        # 항상 활성화
        analysis_menu.addAction(self.compare_action)
        
        analysis_menu.addSeparator()
        
        # GO/KEGG 분석 메뉴 (서브메뉴 없이 직접 추가)
        self.cluster_go_action = QAction("🧬 Cluster GO Terms...", self)
        self.cluster_go_action.triggered.connect(self._on_cluster_go_terms)
        analysis_menu.addAction(self.cluster_go_action)
        
        self.filter_go_action = QAction("🧬 Filter GO/KEGG Results...", self)
        self.filter_go_action.triggered.connect(self._on_filter_go_results)
        analysis_menu.addAction(self.filter_go_action)

        analysis_menu.addSeparator()

        # Multi-Group 분석
        self.multi_heatmap_action = QAction("🌡️ Multi-Group Heatmap...", self)
        self.multi_heatmap_action.triggered.connect(self._on_multi_group_heatmap)
        analysis_menu.addAction(self.multi_heatmap_action)

        analysis_menu.addSeparator()

        # Multi-Omics 통합 분석
        self.integrate_action = QAction("🔗 Integrate RNA + ATAC...", self)
        self.integrate_action.triggered.connect(self._on_show_multi_omics_panel)
        analysis_menu.addAction(self.integrate_action)

        # View 메뉴
        view_menu = menubar.addMenu("&View")

        # ── Panels 서브메뉴 ──────────────────────────────────────────
        panels_menu = view_menu.addMenu("Panels")

        self._menu_datasets_action = QAction("Datasets", self, checkable=True)
        self._menu_datasets_action.setChecked(False)
        self._menu_datasets_action.setShortcut("Ctrl+1")
        self._menu_datasets_action.triggered.connect(self._on_menu_datasets_toggled)
        panels_menu.addAction(self._menu_datasets_action)

        self._menu_filter_action = QAction("Filter / Compare", self, checkable=True)
        self._menu_filter_action.setChecked(True)
        self._menu_filter_action.setShortcut("Ctrl+2")
        self._menu_filter_action.triggered.connect(self._on_menu_filter_toggled)
        panels_menu.addAction(self._menu_filter_action)

        panels_menu.addSeparator()

        self._menu_split_action = QAction("Split View", self, checkable=True)
        self._menu_split_action.setChecked(False)
        self._menu_split_action.setShortcut("Ctrl+\\")
        self._menu_split_action.triggered.connect(self._on_menu_split_toggled)
        panels_menu.addAction(self._menu_split_action)

        view_menu.addSeparator()

        # 컬럼 표시 레벨 서브메뉴
        column_level_menu = view_menu.addMenu("📊 Column Display Level")
        
        self.column_level_group = QActionGroup(self)
        self.column_level_group.setExclusive(True)
        
        basic_action = QAction("Basic", self, checkable=True)
        basic_action.setData("basic")
        basic_action.setChecked(True)  # 기본값: Basic
        basic_action.triggered.connect(lambda: self._on_column_level_changed("basic"))
        self.column_level_group.addAction(basic_action)
        column_level_menu.addAction(basic_action)

        de_action = QAction("Stat", self, checkable=True)
        de_action.setData("de")
        de_action.triggered.connect(lambda: self._on_column_level_changed("de"))
        self.column_level_group.addAction(de_action)
        column_level_menu.addAction(de_action)

        full_action = QAction("Full", self, checkable=True)
        full_action.setData("full")
        full_action.triggered.connect(lambda: self._on_column_level_changed("full"))
        self.column_level_group.addAction(full_action)
        column_level_menu.addAction(full_action)
        
        view_menu.addSeparator()
        
        # 유효숫자 설정
        precision_menu = view_menu.addMenu("🔢 Decimal Precision")
        
        self.precision_group = QActionGroup(self)
        self.precision_group.setExclusive(True)
        
        for precision in [2, 3, 4, 5, 6]:
            action = QAction(f"{precision} decimal places", self, checkable=True)
            action.setData(precision)
            action.triggered.connect(lambda checked, p=precision: self._on_precision_changed(p))
            if precision == 3:  # 기본값
                action.setChecked(True)
            self.precision_group.addAction(action)
            precision_menu.addAction(action)
        
        view_menu.addSeparator()
        
        clear_log_action = QAction("Clear Log", self)
        clear_log_action.triggered.connect(self._on_clear_log)
        view_menu.addAction(clear_log_action)

        view_menu.addSeparator()
        igv_settings_action = QAction("🔬 IGV Settings...", self)
        igv_settings_action.triggered.connect(self._on_igv_settings)
        view_menu.addAction(igv_settings_action)

        # Visualization 메뉴
        viz_menu = menubar.addMenu("&Visualization")
        
        self.volcano_action = QAction("📊 Volcano Plot", self)
        self.volcano_action.setShortcut("Ctrl+V")
        self.volcano_action.triggered.connect(lambda: self._on_visualization_requested("volcano"))
        # 항상 활성화
        viz_menu.addAction(self.volcano_action)
        
        self.histogram_action = QAction("📈 P-adj Histogram", self)
        self.histogram_action.triggered.connect(lambda: self._on_visualization_requested("histogram"))
        # 항상 활성화
        viz_menu.addAction(self.histogram_action)
        
        self.heatmap_action = QAction("🔥 Heatmap", self)
        self.heatmap_action.triggered.connect(lambda: self._on_visualization_requested("heatmap"))
        # 항상 활성화
        viz_menu.addAction(self.heatmap_action)
        
        self.pca_action = QAction("🔵 PCA Plot", self)
        self.pca_action.setShortcut("Ctrl+P")
        self.pca_action.triggered.connect(lambda: self._on_visualization_requested("pca"))
        viz_menu.addAction(self.pca_action)

        self.expr_bar_action = QAction("📊 Gene Expression Bar+Scatter (Grouped)", self)
        self.expr_bar_action.triggered.connect(self._on_gene_expression_bar)
        viz_menu.addAction(self.expr_bar_action)

        viz_menu.addSeparator()
        
        # 비교 데이터 시각화
        self.dotplot_action = QAction("⚫ Dot Plot (Comparison)", self)
        self.dotplot_action.triggered.connect(self._on_dotplot_requested)
        # 항상 활성화
        viz_menu.addAction(self.dotplot_action)
        
        self.venn_action = QAction("⭕ Venn Diagram (Comparison)", self)
        self.venn_action.triggered.connect(self._on_venn_diagram)
        # 항상 활성화
        viz_menu.addAction(self.venn_action)
        
        viz_menu.addSeparator()
        
        # GO/KEGG 시각화 메뉴 (서브메뉴 없이 직접 추가)
        self.go_dotplot_action = QAction("🧬 Dot Plot (GO/KEGG)", self)
        self.go_dotplot_action.triggered.connect(lambda: self._on_go_visualization("dotplot"))
        viz_menu.addAction(self.go_dotplot_action)
        
        self.go_barplot_action = QAction("🧬 Bar Chart (GO/KEGG)", self)
        self.go_barplot_action.triggered.connect(lambda: self._on_go_visualization("barplot"))
        viz_menu.addAction(self.go_barplot_action)
        
        self.go_network_action = QAction("🧬 Network Chart (GO/KEGG)", self)
        self.go_network_action.triggered.connect(lambda: self._on_go_visualization("network"))
        viz_menu.addAction(self.go_network_action)

        viz_menu.addSeparator()

        # ATAC-seq 전용 시각화 (ATAC 탭 활성 시에만 활성화)
        self.genomic_dist_action = QAction("🧬 Genomic Distribution Plot (ATAC-seq)", self)
        self.genomic_dist_action.triggered.connect(lambda: self._on_atac_visualization("genomic_distribution"))
        self.genomic_dist_action.setEnabled(False)
        viz_menu.addAction(self.genomic_dist_action)

        self.tss_distance_action = QAction("📏 TSS Distance Plot (ATAC-seq)", self)
        self.tss_distance_action.triggered.connect(lambda: self._on_atac_visualization("tss_distance"))
        self.tss_distance_action.setEnabled(False)
        viz_menu.addAction(self.tss_distance_action)

        self.ma_plot_action = QAction("📈 MA Plot (ATAC-seq)", self)
        self.ma_plot_action.triggered.connect(lambda: self._on_atac_visualization("ma_plot"))
        self.ma_plot_action.setEnabled(False)
        viz_menu.addAction(self.ma_plot_action)

        self.motif_enrichment_action = QAction("🔡 TF Motif Enrichment Plot", self)
        self.motif_enrichment_action.triggered.connect(self._on_motif_enrichment_requested)
        self.motif_enrichment_action.setEnabled(False)
        viz_menu.addAction(self.motif_enrichment_action)

        self.tf_footprint_action = QAction("👣 TF Activity Plot (Footprint)", self)
        self.tf_footprint_action.triggered.connect(self._on_tf_footprint_requested)
        self.tf_footprint_action.setEnabled(False)
        viz_menu.addAction(self.tf_footprint_action)

        self.chromvar_action = QAction("🧬 chromVAR TF Activity Plot", self)
        self.chromvar_action.triggered.connect(self._on_chromvar_requested)
        self.chromvar_action.setEnabled(False)
        viz_menu.addAction(self.chromvar_action)

        self.da_peak_overlap_action = QAction("🔗 DA Peak Overlap (ATAC-seq)...", self)
        self.da_peak_overlap_action.triggered.connect(self._on_da_peak_overlap)
        # 항상 활성화 — 로드된 ATAC_SEQ 데이터셋 개수는 핸들러 내부에서 확인
        viz_menu.addAction(self.da_peak_overlap_action)

        viz_menu.addSeparator()

        # Multi-Omics 전용 시각화 (MULTI_OMICS 탭 활성 시에만 활성화)
        self.quadrant_plot_action = QAction("◈ Quadrant Plot (Multi-Omics)", self)
        self.quadrant_plot_action.triggered.connect(
            lambda: self._on_multi_omics_visualization("quadrant")
        )
        self.quadrant_plot_action.setEnabled(False)
        viz_menu.addAction(self.quadrant_plot_action)

        self.concordance_heatmap_action = QAction("🔥 Concordance Heatmap (Multi-Omics)", self)
        self.concordance_heatmap_action.triggered.connect(
            lambda: self._on_multi_omics_visualization("heatmap")
        )
        self.concordance_heatmap_action.setEnabled(False)
        viz_menu.addAction(self.concordance_heatmap_action)

        self.concordance_summary_action = QAction("📊 Concordance Bar Chart (Multi-Omics)", self)
        self.concordance_summary_action.triggered.connect(
            lambda: self._on_multi_omics_visualization("summary")
        )
        self.concordance_summary_action.setEnabled(False)
        viz_menu.addAction(self.concordance_summary_action)

        self.integrated_volcano_action = QAction("🌋 Integrated Volcano Plot (Multi-Omics)", self)
        self.integrated_volcano_action.triggered.connect(
            lambda: self._on_multi_omics_visualization("integrated_volcano")
        )
        self.integrated_volcano_action.setEnabled(False)
        viz_menu.addAction(self.integrated_volcano_action)

        # Help 메뉴
        help_menu = menubar.addMenu("&Help")
        
        help_doc_action = QAction("📖 &Documentation", self)
        help_doc_action.setShortcut("F1")
        help_doc_action.triggered.connect(self._on_help_documentation)
        help_menu.addAction(help_doc_action)
        
        help_menu.addSeparator()
        
        about_action = QAction("&About", self)
        about_action.triggered.connect(self._on_about)
        help_menu.addAction(about_action)
    
    def _create_tool_bar(self):
        """툴바 생성"""
        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        
        # Open 버튼
        open_btn = QAction("📂 Open", self)
        open_btn.triggered.connect(self._on_open_dataset)
        toolbar.addAction(open_btn)
        
        toolbar.addSeparator()
        
        # Filter 버튼
        filter_btn = QAction("🔍 Filter", self)
        filter_btn.triggered.connect(self._on_filter_requested)
        toolbar.addAction(filter_btn)
        
        # Analysis 버튼
        analysis_btn = QAction("📊 Analysis", self)
        analysis_btn.triggered.connect(lambda: self._on_analysis_requested("fisher"))
        toolbar.addAction(analysis_btn)
        
        toolbar.addSeparator()
        
        # Export 버튼
        export_btn = QAction("💾 Export", self)
        export_btn.triggered.connect(self._on_export_data)
        toolbar.addAction(export_btn)
    
    def _create_status_bar(self):
        """상태바 생성"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # 상태 라벨
        self.status_label = QLabel("Ready")
        self.status_bar.addWidget(self.status_label)
        
        # Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(200)
        self.progress_bar.hide()
        self.status_bar.addPermanentWidget(self.progress_bar)
        
        # FSM 상태 라벨
        self.fsm_state_label = QLabel(f"State: {self.presenter.fsm.current_state.name}")
        self.status_bar.addPermanentWidget(self.fsm_state_label)
    
    def _setup_logging(self):
        """로그 핸들러 설정"""
        self.qt_log_handler = QtLogHandler()
        self.qt_log_handler.log_signal.connect(self._on_log_message)
        
        # 루트 로거에 핸들러 추가
        root_logger = logging.getLogger()
        root_logger.addHandler(self.qt_log_handler)
    
    def _create_data_tab(self, tab_name: str, sheet_type: str = 'whole',
                         parent_dataset: str = None) -> QTableWidget:
        """새 데이터 탭 생성"""
        table = QTableWidget()
        table.setAlternatingRowColors(True)
        # 셀 단위 선택으로 변경 (기존: SelectRows)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectItems)
        table.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)  # 다중 선택 가능
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)  # 편집 불가 (read-only)
        table.setSortingEnabled(False)  # 데이터 채우기 전까지 비활성 (populate_table에서 활성화)
        
        # 선택 색상을 연한 파란색으로 설정
        table.setStyleSheet("""
            QTableWidget::item:selected {
                background-color: #ADD8E6;  /* 연한 파란색 */
                color: black;
            }
        """)
        
        # 키보드 이벤트 핸들러 연결 (Ctrl+C/Ctrl+V)
        table.keyPressEvent = lambda event: self._handle_table_key_press(event, table)
        
        # 컨텍스트 메뉴 활성화
        table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        table.customContextMenuRequested.connect(lambda pos: self._show_table_context_menu(table, pos))
        
        # 헤더 클릭으로 정렬 가능하도록 설정
        table.horizontalHeader().setSectionsClickable(True)
        table.horizontalHeader().sectionClicked.connect(
            lambda col, t=table: self._sort_table_by_column(t, col)
        )
        table.horizontalHeader().setStyleSheet("""
            QHeaderView::section {
                background-color: #f0f0f0;
                padding: 4px;
                border: 1px solid #d0d0d0;
                font-weight: bold;
            }
            QHeaderView::section:hover {
                background-color: #e0e0e0;
            }
        """)
        
        self.data_tabs.addTab(table, tab_name)

        # tab_data 사전 등록 (아직 없을 때만)
        new_idx = self.data_tabs.indexOf(table)
        if new_idx >= 0 and new_idx not in self.tab_data:
            self.tab_data[new_idx] = {
                'dataframe': None,
                'dataset': None,
                'parent_dataset': parent_dataset,
                'sheet_type': sheet_type,
                'sheet_label': tab_name,
                'filter_params': None,
                'comparison_params': None,
            }
        # 비-whole 시트는 parent_dataset이 있으면 즉시 트리에 등록
        if parent_dataset and sheet_type != 'whole':
            self.dataset_manager.add_sheet(parent_dataset, new_idx, tab_name, sheet_type)

        return table

    def populate_table(self, table: QTableWidget, dataframe: pd.DataFrame, dataset=None):
        """
        테이블에 데이터 채우기 (컬럼 레벨 및 정밀도 적용)
        
        Args:
            table: QTableWidget
            dataframe: 표시할 DataFrame
            dataset: Dataset 객체 (컬럼 매핑 정보 포함, optional)
        """
        if dataframe is None or dataframe.empty:
            return
        
        # 탭 인덱스 찾기 및 원본 데이터 저장 (시각화를 위해 항상 전체 데이터 저장)
        tab_index = self.data_tabs.indexOf(table)
        if tab_index >= 0:
            if tab_index in self.tab_data:
                self.tab_data[tab_index]['dataframe'] = dataframe
                self.tab_data[tab_index]['dataset'] = dataset
                # 'whole' 시트: parent_dataset이 아직 None이면 dataset.name으로 채움
                if (dataset is not None
                        and self.tab_data[tab_index].get('parent_dataset') is None
                        and self.tab_data[tab_index].get('sheet_type') == 'whole'):
                    self.tab_data[tab_index]['parent_dataset'] = dataset.name
            else:
                self.tab_data[tab_index] = {
                    'dataframe': dataframe,
                    'dataset': dataset,
                    'parent_dataset': dataset.name if dataset else None,
                    'sheet_type': 'whole',
                    'sheet_label': '',
                    'filter_params': None,
                    'comparison_params': None,
                }
        
        # 컬럼 필터링 (테이블 표시용 - dataset이 있으면 필터링)
        if dataset:
            # Dataset 객체가 있으면 column_display_level에 따라 필터링
            columns = self._filter_columns(dataframe.columns.tolist(), dataset)
            filtered_df = dataframe[columns]
        else:
            # Comparison 결과 등 dataset이 None인 경우만 그대로 사용
            columns = dataframe.columns.tolist()
            filtered_df = dataframe
        
        # 테이블 설정
        table.setRowCount(len(filtered_df))
        table.setColumnCount(len(columns))
        table.setHorizontalHeaderLabels(columns)
        
        # 정렬 기능 활성화
        table.setSortingEnabled(False)  # 데이터 입력 중에는 비활성화
        
        # FDR, adj-pvalue 등 scientific notation 필요한 컬럼 인덱스 확인
        from models.standard_columns import StandardColumns
        scientific_columns = {
            StandardColumns.FDR, StandardColumns.ADJ_PVALUE, 
            StandardColumns.PVALUE, StandardColumns.PVALUE_GO,
            StandardColumns.QVALUE
        }
        scientific_col_indices = {i for i, col in enumerate(columns) if col in scientific_columns}
        
        # 데이터 채우기
        for i, row in enumerate(filtered_df.values):
            for j, value in enumerate(row):
                # Scientific notation이 필요한 컬럼인지 확인
                needs_scientific = j in scientific_col_indices
                
                # 유효숫자 적용
                if isinstance(value, float):
                    if needs_scientific:
                        # Scientific notation 적용
                        abs_value = abs(value)
                        if abs_value == 0:
                            formatted_value = "0"
                        elif abs_value >= 1.0:
                            formatted_value = f"{value:.2f}"
                        elif abs_value >= 0.01:
                            formatted_value = f"{value:.3f}"
                        elif abs_value >= 0.0001:
                            formatted_value = f"{value:.4f}"
                        else:
                            formatted_value = f"{value:.2e}"
                    else:
                        formatted_value = f"{value:.{self.decimal_precision}f}"
                    # 숫자형 아이템 사용 (정렬 지원)
                    item = NumericTableWidgetItem(value, formatted_value)
                elif isinstance(value, int):
                    formatted_value = str(value)
                    item = NumericTableWidgetItem(value, formatted_value)
                else:
                    formatted_value = str(value)
                    item = QTableWidgetItem(formatted_value)
                
                item.setData(Qt.ItemDataRole.UserRole, i)
                table.setItem(i, j, item)

        # setSortingEnabled(True)를 사용하지 않음:
        # Qt가 활성화 시 자동으로 sortItems(0, Asc)를 호출하여 입력 순서를 깨뜨림.
        # 대신 sectionClicked 시그널에 _sort_table_by_column을 연결하여 수동 정렬.
        
        # 정렬 인디케이터 초기화 (화살표 없음)
        table.horizontalHeader().setSortIndicator(-1, Qt.SortOrder.AscendingOrder)

        # 저장된 컬럼 너비 복원
        self._restore_table_column_widths(table)
        
        # 컬럼 크기 자동 조정
        table.resizeColumnsToContents()
        
        # gene_symbols 열 너비 제한 (너무 넓지 않게)
        for i, col in enumerate(columns):
            if col == StandardColumns.GENE_SYMBOLS or col.lower() == 'gene_symbols':
                table.setColumnWidth(i, 150)  # 초기 너비를 150px로 제한
                break
    
    def _sort_table_by_column(self, table: QTableWidget, col: int):
        """헤더 클릭 시 수동 정렬 (setSortingEnabled 미사용)

        QHeaderView.setSectionsClickable(True)를 켜면 setSortingEnabled 여부와
        무관하게 Qt가 sectionClicked를 emit하기 *전에* 내부적으로 sort indicator를
        이미 올바른 방향으로 토글해 둔다(Qt 자체 동작). 여기서 또 토글하면 클릭마다
        두 번 토글되어 항상 같은 방향(Descending)에 고정되는 문제가 있었다.
        Qt가 이미 정해 둔 현재 indicator 값을 그대로 사용해 실제 행 정렬만 적용한다.
        """
        header = table.horizontalHeader()
        table.sortItems(header.sortIndicatorSection(), header.sortIndicatorOrder())
    
    def _filter_columns(self, all_columns: List[str], dataset=None) -> List[str]:
        """
        컬럼 표시 레벨에 따라 표시할 컬럼 필터링
        
        Args:
            all_columns: 전체 컬럼 리스트 (표준 컬럼명 사용)
            dataset: Dataset 객체 (데이터셋 타입 확인용)
            
        Returns:
            필터링된 컬럼 리스트
        """
        from models.standard_columns import StandardColumns
        from models.data_models import DatasetType
        
        # 항상 제거할 내부 처리용 컬럼
        # gene_set은 GO 필터링에 필요하므로 유지, direction은 제거
        internal_columns = {'_gene_set', 'Value', StandardColumns.DIRECTION}
        
        # GO/KEGG 데이터인 경우 - 지정된 순서로 표시
        if dataset and dataset.dataset_type == DatasetType.GO_ANALYSIS:
            # 고정 앞부분: ID / 설명
            prefix_order = [
                StandardColumns.ONTOLOGY,
                StandardColumns.GENE_SET,
                StandardColumns.TERM_ID,
                StandardColumns.DESCRIPTION,
            ]
            # 고정 통계 순서 (gene_count 제외 - gene_ratio 분자와 중복)
            stat_order = [
                StandardColumns.GENE_RATIO,
                StandardColumns.BG_RATIO,
                StandardColumns.FOLD_ENRICHMENT,
                StandardColumns.PVALUE_GO,
                StandardColumns.FDR,
                StandardColumns.QVALUE,
                StandardColumns.GENE_SYMBOLS,
            ]
            # 위 순서에 포함되지 않은 나머지 컬럼 (예상 외 컬럼 보존)
            ordered = []
            seen = set()
            for col in prefix_order + stat_order:
                if col in all_columns and col not in internal_columns and col not in seen:
                    ordered.append(col)
                    seen.add(col)
            # 나머지 컬럼 뒤에 추가 (gene_count 포함 중복 컬럼은 제외)
            skip_cols = internal_columns | {StandardColumns.GENE_COUNT}
            for col in all_columns:
                if col not in seen and col not in skip_cols:
                    ordered.append(col)
                    seen.add(col)
            return ordered
        
        # ATAC-seq 데이터인 경우
        if dataset and dataset.dataset_type == DatasetType.ATAC_SEQ:
            if self.column_display_level == "full":
                level_cols = StandardColumns.get_atac_all()
            elif self.column_display_level == "de":   # 'de' 레벨 → ATAC의 stat 수준
                level_cols = StandardColumns.get_atac_stat()
            else:  # "basic"
                level_cols = StandardColumns.get_atac_basic()

            # 정의된 순서 우선, 나머지 컬럼은 full에만 추가
            ordered = []
            seen = set()
            for col in level_cols:
                if col in all_columns and col not in internal_columns:
                    ordered.append(col)
                    seen.add(col)
            if self.column_display_level == "full":
                for col in all_columns:
                    if col not in seen and col not in internal_columns:
                        ordered.append(col)
            return ordered if ordered else [col for col in all_columns if col not in internal_columns]

        # DE 데이터인 경우 (기존 로직)
        if self.column_display_level == "full":
            return [col for col in all_columns if col not in internal_columns]

        columns_to_show = []

        # Basic 레벨: gene_id + symbol + base_mean + 샘플 count 컬럼만
        if self.column_display_level == "basic":
            # 1. 기본 컬럼 추가 (gene_id, symbol, base_mean)
            for col in StandardColumns.get_de_basic():
                if col in all_columns:
                    columns_to_show.append(col)
            
            # 2. 샘플 카운트 컬럼 추가 (표준 DE 컬럼이 아닌 것들)
            standard_de_cols = set(StandardColumns.get_de_all())
            for col in all_columns:
                if col not in standard_de_cols and col not in columns_to_show and col not in internal_columns:
                    columns_to_show.append(col)
            
            return columns_to_show if columns_to_show else [col for col in all_columns if col not in internal_columns]
        
        # DE 레벨: gene_id, base_mean + 모든 DE 통계 컬럼
        if self.column_display_level == "de":
            # 기본 컬럼 (gene_id, base_mean)
            for col in StandardColumns.get_de_basic():
                if col in all_columns:
                    columns_to_show.append(col)
            
            # DE 통계 컬럼 (log2fc, lfcse, stat, pvalue, adj_pvalue)
            for col in StandardColumns.get_de_statistics():
                if col in all_columns:
                    columns_to_show.append(col)
            
            return columns_to_show if columns_to_show else [col for col in all_columns if col not in internal_columns]
        
        return [col for col in all_columns if col not in internal_columns]
    
    def _on_state_changed(self, old_state: State, new_state: State):
        """FSM 상태 변경 시 UI 업데이트"""
        self.fsm_state_label.setText(f"State: {new_state.name}")
        
        # 상태에 따른 UI 활성화/비활성화
        if new_state in [State.LOADING_DATA, State.FILTERING, State.ANALYZING]:
            self.progress_bar.show()
            self.status_label.setText(f"{new_state.name}...")
        else:
            self.progress_bar.hide()
            self.status_label.setText("Ready")
        
        # 메뉴 항목 활성화/비활성화
        self._update_menu_states(new_state)
    
    def _update_menu_states(self, state: State):
        """FSM 상태에 따라 메뉴 항목 enable/disable - 모두 활성화 상태 유지"""
        # 모든 메뉴를 항상 활성화 상태로 유지
        # 잘못된 상황에서 클릭 시 각 기능에서 에러 메시지 표시
        pass
    
    def _on_log_message(self, message: str, level: int):
        """로그 메시지 표시"""
        # 로그 버퍼에 추가
        self.log_buffer.add(message, level)
        
        # 터미널에 표시
        color = self._get_log_color(level)
        html_message = f'<span style="color: {color};">{message}</span>'
        self.log_terminal.append(html_message)
        
        # 자동 스크롤
        scrollbar = self.log_terminal.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def _get_log_color(self, level: int) -> str:
        """로그 레벨에 따른 색상 반환"""
        if level >= logging.ERROR:
            return "#f48771"  # 빨강
        elif level >= logging.WARNING:
            return "#dcdcaa"  # 노랑
        elif level >= logging.INFO:
            return "#4ec9b0"  # 청록
        else:
            return "#d4d4d4"  # 회색
    
    # Slot 메서드들
    def _on_open_dataset(self):
        """데이터셋 열기"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Dataset", "", "Excel Files (*.xlsx *.xls);;All Files (*)"
        )
        
        if file_path:
            # 기본 파일명 추출
            default_name = Path(file_path).stem
            
            # 사용자에게 별명 입력 요청
            dataset_name, ok = QInputDialog.getText(
                self, 
                "Dataset Name", 
                "Enter a name for this dataset:",
                QLineEdit.EchoMode.Normal,
                default_name
            )
            
            if ok and dataset_name:
                # 별명과 함께 데이터셋 로드
                self.presenter.load_dataset(Path(file_path), custom_name=dataset_name.strip())
                # 최근 파일에 추가
                self._add_recent_file(file_path)
            elif ok:
                # 빈 이름인 경우 기본 이름 사용
                self.presenter.load_dataset(Path(file_path))
                # 최근 파일에 추가
                self._add_recent_file(file_path)
            # Cancel 버튼 누르면 아무것도 안함
    
    def _on_open_atac_dataset(self):
        """ATAC-seq DA 데이터셋 열기"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open ATAC-seq Dataset", "",
            "ATAC-seq Files (*.xlsx *.xls *.parquet);;Excel Files (*.xlsx *.xls);;Parquet Files (*.parquet);;All Files (*)"
        )
        if not file_path:
            return

        default_name = Path(file_path).stem
        dataset_name, ok = QInputDialog.getText(
            self, "Dataset Name", "Enter a name for this ATAC-seq dataset:",
            QLineEdit.EchoMode.Normal, default_name
        )
        if not ok:
            return

        name = dataset_name.strip() or default_name
        self._add_recent_file(file_path)
        self.presenter.load_dataset(Path(file_path), custom_name=name)

    def _on_open_motif_results(self):
        """HOMER knownResults.txt 또는 MEME AME ame.tsv 열기."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open TF Motif Results", "",
            "Motif Files (*.txt *.tsv);;HOMER knownResults (knownResults.txt);;AME results (ame.tsv);;All Files (*)"
        )
        if not file_path:
            return

        default_name = Path(file_path).stem
        dataset_name, ok = QInputDialog.getText(
            self, "Dataset Name", "Enter a name for this motif dataset:",
            QLineEdit.EchoMode.Normal, default_name
        )
        if not ok:
            return

        name = dataset_name.strip() or default_name
        self._add_recent_file(file_path)
        self.presenter.load_dataset(Path(file_path), custom_name=name)

    def _on_open_footprint_results(self):
        """TOBIAS bindetect_results.txt 열기."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open TF Footprint Results", "",
            "BINDetect Results (bindetect_results.txt *.txt);;All Files (*)"
        )
        if not file_path:
            return

        default_name = Path(file_path).stem
        dataset_name, ok = QInputDialog.getText(
            self, "Dataset Name", "Enter a name for this footprint dataset:",
            QLineEdit.EchoMode.Normal, default_name
        )
        if not ok:
            return

        name = dataset_name.strip() or default_name
        self._add_recent_file(file_path)
        self.presenter.load_dataset(Path(file_path), custom_name=name)

    def _on_add_dataset(self):
        """추가 데이터셋 로드"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Add Dataset", "", 
            "Excel Files (*.xlsx *.xls);;CSV Files (*.csv);;All Files (*)"
        )
        
        if file_path:
            self._load_dataset_with_name(file_path)
    
    def _data_tabs_drag_enter(self, event):
        """Data tabs 드래그 진입 이벤트"""
        from PyQt6.QtGui import QDragEnterEvent
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if urls:
                file_path = urls[0].toLocalFile()
                if file_path.lower().endswith(('.xlsx', '.xls', '.csv', '.tsv')):
                    event.accept()
                    return
        event.ignore()
    
    def _data_tabs_drop(self, event):
        """Data tabs 드롭 이벤트"""
        from PyQt6.QtGui import QDropEvent
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if urls:
                file_path = urls[0].toLocalFile()
                if file_path.lower().endswith(('.xlsx', '.xls', '.csv', '.tsv')):
                    self._load_dataset_with_name(file_path)
                    event.accept()
                    return
        event.ignore()
    
    def _load_dataset_with_name(self, file_path: str):
        """파일 경로로 데이터셋 로드 (이름 입력 포함)"""
        # 기본 파일명 추출
        default_name = Path(file_path).stem
        
        # 사용자에게 별명 입력 요청
        dataset_name, ok = QInputDialog.getText(
            self, 
            "Dataset Name", 
            "Enter a name for this dataset:",
            QLineEdit.EchoMode.Normal,
            default_name
        )
        
        if ok and dataset_name:
            # 별명과 함께 데이터셋 로드
            self.presenter.load_dataset(Path(file_path), custom_name=dataset_name.strip())
            # 최근 파일에 추가
            self._add_recent_file(file_path)
        elif ok:
            # 빈 이름인 경우 기본 이름 사용
            self.presenter.load_dataset(Path(file_path))
            # 최근 파일에 추가
            self._add_recent_file(file_path)
        # Cancel 버튼 누르면 아무것도 안함
    
    def _on_open_gene_list(self):
        """유전자 리스트 파일 열기"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Gene List", "", "Text Files (*.txt);;All Files (*)"
        )
        
        if file_path:
            self.presenter.load_gene_list(Path(file_path))
    
    def _on_dataset_selected(self, dataset_name: str):
        """데이터셋 선택 → 해당 데이터로 전환하고 공유 'Whole Dataset' 탭으로 이동.

        'Whole Dataset' 탭은 데이터셋마다 따로 있지 않고 하나를 공유한다
        (switch_dataset → _update_view_with_dataset가 현재 데이터로 다시 채움).
        루트 클릭 시 그 공유 탭으로 활성 탭을 전환해 데이터를 바로 보여준다.
        """
        self.presenter.switch_dataset(dataset_name)
        for i in range(self.data_tabs.count()):
            if self.data_tabs.tabText(i) == "Whole Dataset":
                self.data_tabs.setCurrentIndex(i)
                break
    
    def _on_dataset_removed(self, dataset_name: str):
        """데이터셋 제거"""
        if dataset_name in self.presenter.datasets:
            del self.presenter.datasets[dataset_name]
            self.logger.info(f"Dataset removed: {dataset_name}")
            
            # 현재 데이터셋이 제거되었다면 다른 데이터셋으로 전환
            if self.presenter.current_dataset and self.presenter.current_dataset.name == dataset_name:
                remaining = self.dataset_manager.get_all_datasets()
                if remaining:
                    self.presenter.switch_dataset(remaining[0])
                else:
                    self.presenter.current_dataset = None
    
    def _on_dataset_renamed(self, old_name: str, new_name: str):
        """데이터셋 이름 변경"""
        if old_name in self.presenter.datasets:
            # Dataset 객체의 이름 변경
            dataset = self.presenter.datasets[old_name]
            dataset.name = new_name
            
            # 딕셔너리 키 변경
            self.presenter.datasets[new_name] = self.presenter.datasets.pop(old_name)
            
            # 현재 데이터셋이 변경된 경우 업데이트
            if self.presenter.current_dataset and self.presenter.current_dataset.name == old_name:
                self.presenter.current_dataset.name = new_name
            
            # 탭 이름 업데이트
            for i in range(self.data_tabs.count()):
                tab_name = self.data_tabs.tabText(i)
                if tab_name == f"Whole Dataset: {old_name}":
                    self.data_tabs.setTabText(i, f"Whole Dataset: {new_name}")
                elif tab_name.startswith(f"Filtered: {old_name}"):
                    # Filtered 탭은 "Filtered: dataset_name (criteria)" 형식
                    new_tab_name = tab_name.replace(f"Filtered: {old_name}", f"Filtered: {new_name}")
                    self.data_tabs.setTabText(i, new_tab_name)
            
            # Comparison Panel의 dataset 리스트 업데이트
            all_datasets = self.dataset_manager.get_all_datasets()
            self.comparison_panel.update_dataset_list(all_datasets)

            self.logger.info(f"Dataset renamed: {old_name} -> {new_name}")

    def _on_sheet_renamed(self, tab_index: int, new_label: str):
        """child 시트(필터/비교/클러스터 탭) 이름 변경을 탭/데이터에 반영"""
        if not (0 <= tab_index < self.data_tabs.count()):
            return
        # 탭 텍스트 변경
        self.data_tabs.setTabText(tab_index, new_label)
        # tab_data의 라벨과 Dataset 객체 이름 동기화
        entry = self.tab_data.get(tab_index)
        if entry is not None:
            entry['sheet_label'] = new_label
            ds = entry.get('dataset')
            if ds is not None:
                ds.name = new_label
        self.logger.info(f"Sheet renamed: tab {tab_index} -> {new_label}")

    def _on_filter_requested(self):
        """필터링 요청"""
        criteria = self.filter_panel.get_filter_criteria()
        
        # 현재 dataset type 확인 및 로깅
        dataset_type = self.presenter.current_dataset.dataset_type if self.presenter.current_dataset else None
        self.logger.info(f"Filter requested: dataset_type={dataset_type}, criteria={criteria.to_dict()}")
        
        # 현재 활성화된 탭 확인
        current_tab_name = self.data_tabs.tabText(self.data_tabs.currentIndex())
        current_table = self.data_tabs.currentWidget()
        
        from models.data_models import FilterMode, DatasetType
        import re

        # Gene List 필터는 항상 원본 데이터셋(presenter)에서 필터링
        if criteria.mode == FilterMode.GENE_LIST:
            # GO_ANALYSIS + Gene Symbol 모드인데 입력이 GO/KEGG ID 패턴이면 경고
            if (dataset_type == DatasetType.GO_ANALYSIS
                    and criteria.gene_list
                    and not criteria.term_id_list):
                term_id_pattern = re.compile(
                    r'^GO:\d+$|^R-[A-Z]+-\d+$|^[a-z]{3}\d+$|^path:[a-z]{3}\d+$',
                    re.IGNORECASE
                )
                matches = sum(1 for g in criteria.gene_list if term_id_pattern.match(g.strip()))
                if matches >= max(1, len(criteria.gene_list) // 2):
                    QMessageBox.warning(
                        self,
                        "GO Term ID Detected",
                        "입력값이 GO/KEGG Term ID 패턴(GO:XXXXXXX)으로 보입니다.\n\n"
                        "Gene Symbol 모드에서는 GO term의 gene_symbols 컬럼을 검색합니다.\n\n"
                        "GO Term ID로 검색하려면:\n"
                        "  ● Gene Symbol → ○ GO Term ID 를 선택하고 다시 Apply Filter를 눌러주세요."
                    )
                    return

            self.presenter.apply_filter(criteria)
            return
        
        # Statistical 필터: 현재 탭이 Filtered 또는 Comparison 탭이면 해당 데이터를 필터링
        if current_tab_name.startswith("Filtered:") or current_tab_name.startswith("Comparison:"):
            self._filter_current_tab(criteria, current_tab_name, current_table)
        else:
            # Whole Dataset 탭인 경우 기존 방식 사용
            self.presenter.apply_filter(criteria)
    
    def _filter_current_tab(self, criteria, tab_name, table):
        """현재 탭의 데이터를 필터링"""
        try:
            row_count = table.rowCount()
            if row_count == 0:
                QMessageBox.warning(self, "No Data", "Current tab is empty.")
                return

            # tab_data에서 전체 DataFrame 사용 (column display level과 무관하게 모든 컬럼 접근 가능)
            current_index = self.data_tabs.currentIndex()
            _entry = self.tab_data.get(current_index)
            stored_df = _entry['dataframe'] if _entry else None
            tab_dataset = _entry['dataset'] if _entry else None

            if stored_df is not None and not stored_df.empty:
                df = stored_df.copy()
            else:
                # fallback: 테이블 위젯에서 읽기
                col_count = table.columnCount()
                headers = []
                for col in range(col_count):
                    header_item = table.horizontalHeaderItem(col)
                    if header_item:
                        headers.append(header_item.text())
                data = []
                for row in range(row_count):
                    row_data = {}
                    for col in range(col_count):
                        item = table.item(row, col)
                        if item:
                            value = item.text()
                            try:
                                value = float(value)
                            except:
                                pass
                            row_data[headers[col]] = value
                        else:
                            row_data[headers[col]] = None
                    data.append(row_data)
                df = pd.DataFrame(data)
                tab_dataset = None
            
            # 필터 적용
            if criteria.mode == FilterMode.GENE_LIST:
                # Gene list 필터
                if not criteria.gene_list:
                    QMessageBox.warning(self, "Empty Gene List", "Please enter genes to filter.")
                    return

                tab_dataset_type = tab_dataset.dataset_type if tab_dataset else None

                if tab_dataset_type == DatasetType.GO_ANALYSIS:
                    # GO 데이터: gene_symbols 컬럼에서 부분 포함 검색
                    import re
                    from models.standard_columns import StandardColumns
                    gs_col = StandardColumns.GENE_SYMBOLS
                    if gs_col not in df.columns:
                        QMessageBox.warning(self, "No gene_symbols Column",
                                            "This GO dataset has no 'gene_symbols' column.")
                        return

                    query_set = {g.strip().upper() for g in criteria.gene_list if g.strip()}

                    def _count_hits(cell):
                        if not isinstance(cell, str) or not cell.strip():
                            return 0
                        syms = {s.strip().upper() for s in re.split(r'[,;/\s]+', cell) if s.strip()}
                        return len(syms & query_set)

                    hit_counts = df[gs_col].apply(_count_hits)
                    filtered_df = df[hit_counts > 0].copy()
                    filtered_df['_hit'] = hit_counts[hit_counts > 0]
                    filtered_df = filtered_df.sort_values('_hit', ascending=False).drop(columns='_hit')
                    new_tab_name = f"Filtered: {tab_name} - Gene Symbols ({len(criteria.gene_list)} genes)"

                else:
                    # DE 데이터: gene_id 또는 symbol 컬럼 완전 일치 검색
                    gene_col = None
                    if 'symbol' in df.columns:
                        gene_col = 'symbol'
                    elif 'gene_id' in df.columns:
                        gene_col = 'gene_id'
                    else:
                        QMessageBox.warning(self, "No Gene Column", "No gene identifier column found.")
                        return

                    # 필터링 (gene list 입력 순서 유지)
                    gene_order = {g.upper(): i for i, g in enumerate(criteria.gene_list)}
                    mask = df[gene_col].astype(str).str.upper().isin(gene_order)
                    filtered_df = (
                        df[mask]
                        .assign(_sort_key=df.loc[mask, gene_col].astype(str).str.upper().map(gene_order))
                        .sort_values('_sort_key')
                        .drop(columns='_sort_key')
                    )
                    new_tab_name = f"Filtered: {tab_name} - Gene List ({len(criteria.gene_list)} genes)"
                
            else:  # Statistical filter
                dataset_type = tab_dataset.dataset_type if tab_dataset else None
                filtered_df = df.copy()
                
                if dataset_type == DatasetType.DIFFERENTIAL_EXPRESSION:
                    # DE 데이터 필터링
                    regulation_direction = getattr(criteria, 'regulation_direction', 'both')
                    
                    # log2FC 필터
                    fc_cols = [col for col in df.columns if 'log2FC' in col or 'log2FoldChange' in col or 'log2fc' in col]
                    if fc_cols:
                        fc_mask = pd.Series([False] * len(filtered_df), index=filtered_df.index)
                        for fc_col in fc_cols:
                            fc_values = filtered_df[fc_col].astype(float, errors='ignore')
                            
                            if regulation_direction == "up":
                                fc_mask |= fc_values >= criteria.log2fc_min
                            elif regulation_direction == "down":
                                fc_mask |= fc_values <= -criteria.log2fc_min
                            else:  # both
                                fc_mask |= abs(fc_values) >= criteria.log2fc_min
                        
                        filtered_df = filtered_df[fc_mask]
                    
                    # padj 필터
                    padj_cols = [col for col in df.columns if 'padj' in col or 'Padj' in col or 'adj_pvalue' in col]
                    if padj_cols:
                        padj_mask = pd.Series([False] * len(filtered_df), index=filtered_df.index)
                        for padj_col in padj_cols:
                            padj_mask |= filtered_df[padj_col].astype(float, errors='ignore') <= criteria.adj_pvalue_max
                        filtered_df = filtered_df[padj_mask]
                    
                    direction_str = ""
                    if regulation_direction == "up":
                        direction_str = " (Up)"
                    elif regulation_direction == "down":
                        direction_str = " (Down)"
                    
                    new_tab_name = f"Filtered: {tab_name} - p≤{criteria.adj_pvalue_max}, |FC|≥{criteria.log2fc_min}{direction_str}"
                
                elif dataset_type == DatasetType.GO_ANALYSIS:
                    # GO 데이터 필터링
                    from models.standard_columns import StandardColumns
                    
                    # FDR 필터
                    if StandardColumns.FDR in filtered_df.columns:
                        fdr_values = pd.to_numeric(filtered_df[StandardColumns.FDR], errors='coerce')
                        filtered_df = filtered_df[fdr_values <= criteria.fdr_max]
                    
                    # Fold Enrichment 필터
                    fe_min = getattr(criteria, 'fold_enrichment_min', 0.0)
                    if fe_min > 0 and StandardColumns.FOLD_ENRICHMENT in filtered_df.columns:
                        fe_values = pd.to_numeric(filtered_df[StandardColumns.FOLD_ENRICHMENT], errors='coerce')
                        filtered_df = filtered_df[fe_values >= fe_min]
                    
                    # Ontology 필터
                    if criteria.ontology != "All" and StandardColumns.ONTOLOGY in filtered_df.columns:
                        filtered_df = filtered_df[filtered_df[StandardColumns.ONTOLOGY] == criteria.ontology]
                    
                    # Gene Set 필터 (UP/DOWN/TOTAL DEG로 분석한 결과)
                    # gene_set 컬럼 우선, 없으면 direction 컬럼으로 fallback
                    if criteria.go_direction != "All":
                        if StandardColumns.GENE_SET in filtered_df.columns:
                            filtered_df = filtered_df[
                                filtered_df[StandardColumns.GENE_SET].str.upper() == criteria.go_direction.upper()
                            ]
                        elif StandardColumns.DIRECTION in filtered_df.columns:
                            filtered_df = filtered_df[
                                filtered_df[StandardColumns.DIRECTION].str.upper() == criteria.go_direction.upper()
                            ]
                    
                    # 탭 이름 생성
                    filters = []
                    if criteria.fdr_max < 0.001:
                        filters.append(f"FDR≤{criteria.fdr_max:.1e}")
                    else:
                        filters.append(f"FDR≤{criteria.fdr_max:.3f}")
                    fe_min = getattr(criteria, 'fold_enrichment_min', 0.0)
                    if fe_min > 0:
                        filters.append(f"FE≥{fe_min:.1f}")
                    if criteria.ontology != "All":
                        filters.append(criteria.ontology)
                    if criteria.go_direction != "All":
                        filters.append(criteria.go_direction)
                    
                    new_tab_name = f"Filtered: {tab_name} - {', '.join(filters)}"
                
                else:
                    # Unknown dataset type - 일반 필터링 시도
                    regulation_direction = getattr(criteria, 'regulation_direction', 'both')
                    
                    # log2FC 필터 (여러 데이터셋 컬럼 지원)
                    fc_cols = [col for col in df.columns if 'log2FC' in col or 'log2FoldChange' in col]
                    if fc_cols:
                        # 모든 log2FC 컬럼 중 하나라도 조건을 만족하면 포함
                        fc_mask = pd.Series([False] * len(filtered_df), index=filtered_df.index)
                        for fc_col in fc_cols:
                            fc_values = filtered_df[fc_col].astype(float, errors='ignore')
                            
                            # Regulation direction 적용
                            if regulation_direction == "up":
                                # Up-regulated: log2FC >= log2fc_min (양수)
                                fc_mask |= fc_values >= criteria.log2fc_min
                            elif regulation_direction == "down":
                                # Down-regulated: log2FC <= -log2fc_min (음수)
                                fc_mask |= fc_values <= -criteria.log2fc_min
                            else:  # both
                                # Both: |log2FC| >= log2fc_min
                                fc_mask |= abs(fc_values) >= criteria.log2fc_min
                        
                        filtered_df = filtered_df[fc_mask]
                    
                    # padj 필터
                    padj_cols = [col for col in df.columns if 'padj' in col or 'Padj' in col]
                    if padj_cols:
                        # 모든 padj 컬럼 중 하나라도 조건을 만족하면 포함
                        padj_mask = pd.Series([False] * len(filtered_df), index=filtered_df.index)
                        for padj_col in padj_cols:
                            padj_mask |= filtered_df[padj_col].astype(float, errors='ignore') <= criteria.adj_pvalue_max
                        filtered_df = filtered_df[padj_mask]
                    
                    # Tab 이름에 regulation direction 표시
                    direction_str = ""
                    if regulation_direction == "up":
                        direction_str = " (Up)"
                    elif regulation_direction == "down":
                        direction_str = " (Down)"
                    
                    new_tab_name = f"Filtered: {tab_name} - p≤{criteria.adj_pvalue_max}, |FC|≥{criteria.log2fc_min}{direction_str}"
            
            if filtered_df.empty:
                QMessageBox.information(self, "No Results", "No data matches the filter criteria.")
                return
            
            # 현재 탭의 dataset 정보 가져오기 (GO visualization 등에서 dataset type 필요)
            current_index = self.data_tabs.currentIndex()
            _entry = self.tab_data.get(current_index)
            current_dataset = _entry['dataset'] if _entry else None
            
            # 필터링된 데이터로 Dataset 객체 생성
            from models.data_models import Dataset
            if current_dataset is not None:
                filtered_dataset = Dataset(
                    name=new_tab_name,
                    dataset_type=current_dataset.dataset_type,
                    dataframe=filtered_df,
                    original_columns=current_dataset.original_columns,
                    metadata=current_dataset.metadata.copy() if current_dataset.metadata else {}
                )
            else:
                filtered_dataset = None
            
            # 새 탭 생성
            _cur_entry = self.tab_data.get(self.data_tabs.currentIndex())
            parent_root = (_cur_entry.get('parent_dataset') if _cur_entry else None) \
                or (current_dataset.name if current_dataset else None)
            new_table = self._create_data_tab(new_tab_name,
                                              sheet_type='filtered',
                                              parent_dataset=parent_root)
            self.populate_table(new_table, filtered_df, filtered_dataset)
            self.logger.info(f"Filtered current tab: {len(filtered_df)} rows from {row_count} rows")
            
        except Exception as e:
            self.logger.error(f"Filter current tab failed: {e}", exc_info=True)
            QMessageBox.critical(self, "Filter Error", f"Failed to filter current tab:\n{str(e)}")

    
    def _on_comparison_requested(self, dataset_names: List[str], comparison_type: str):
        """
        데이터셋 비교 요청
        
        Args:
            dataset_names: 비교할 데이터셋 이름 리스트
            comparison_type: 비교 타입 ("gene_list", "statistics", "venn", "scatter", "heatmap", "correlation")
        """
        self.logger.info(f"Comparison requested: {comparison_type} for {len(dataset_names)} datasets")
        
        # 직접 비교 수행 (Presenter는 단일 데이터셋 처리만 담당)
        self._perform_basic_comparison(dataset_names, comparison_type)
    
    def _perform_basic_comparison(self, dataset_names: List[str], comparison_type: str):
        """
        기본 비교 구현 (Presenter에 메서드가 없을 때)
        
        Args:
            dataset_names: 비교할 데이터셋 이름 리스트
            comparison_type: 비교 타입
        """
        try:
            # 데이터셋 가져오기
            datasets = []
            for name in dataset_names:
                if name in self.presenter.datasets:
                    datasets.append(self.presenter.datasets[name])
                else:
                    self.logger.warning(f"Dataset not found: {name}")
            
            if len(datasets) < 2:
                QMessageBox.warning(self, "Comparison Error", 
                                  "At least 2 valid datasets are required for comparison.")
                return
            
            # 비교 타입별 처리
            if comparison_type == "gene_list":
                self._compare_gene_list(datasets)
            elif comparison_type == "statistics":
                self._compare_statistics(datasets)
            elif comparison_type == "go_term":
                self._compare_go_terms(datasets)
            else:
                QMessageBox.information(self, "Feature Moved", 
                                      "Visualization features (Venn, Scatter, Heatmap, Correlation) "
                                      "have been moved to the Visualization menu.")
        
        except Exception as e:
            self.logger.error(f"Comparison failed: {e}")
            QMessageBox.critical(self, "Comparison Error", f"Failed to compare datasets:\n{str(e)}")
    
    def _compare_gene_list(self, datasets):
        """Gene List 필터링 비교 - Wide format"""
        criteria = self.filter_panel.get_filter_criteria()
        gene_list = criteria.gene_list  # FilterCriteria 객체의 속성 사용
        
        if not gene_list:
            QMessageBox.information(self, "Gene List Required", 
                                  "Please enter a gene list in the filter panel first.")
            return
        
        self.logger.info(f"Comparing {len(datasets)} datasets with {len(gene_list)} genes")
        self.logger.info(f"Gene list: {gene_list[:5]}..." if len(gene_list) > 5 else f"Gene list: {gene_list}")
        
        # 각 데이터셋에서 필터링된 데이터 수집
        dataset_dfs = {}
        for dataset in datasets:
            df = dataset.dataframe.copy()
            
            self.logger.info(f"Dataset '{dataset.name}' columns: {df.columns.tolist()}")
            
            # gene_id 컬럼 찾기 (symbol이 먼저)
            gene_id_col = None
            if 'symbol' in df.columns:
                gene_id_col = 'symbol'
                self.logger.info(f"Using 'symbol' column as gene identifier")
            elif 'gene_id' in df.columns:
                gene_id_col = 'gene_id'
                self.logger.info(f"Using 'gene_id' column as gene identifier")
            else:
                self.logger.warning(f"No gene identifier column found in dataset: {dataset.name}")
                continue
            
            # 디버깅: 첫 5개 gene 값 출력
            self.logger.info(f"First 5 genes in dataset: {df[gene_id_col].head().tolist()}")
            
            # 필터링 (gene list 입력 순서 유지)
            gene_order = {g.upper(): i for i, g in enumerate(gene_list)}
            mask = df[gene_id_col].isin(gene_list)
            
            if not mask.any():
                self.logger.warning(f"No matching genes found in dataset: {dataset.name}")
                # 대소문자 구분 없이 재시도
                mask = df[gene_id_col].str.upper().isin(gene_order)
                if not mask.any():
                    continue
                else:
                    self.logger.debug(f"Found {mask.sum()} genes after case-insensitive matching")
            else:
                self.logger.debug(f"Found {mask.sum()} matching genes in dataset: {dataset.name}")

            filtered_df = (
                df[mask].copy()
                .assign(_sort_key=df.loc[mask, gene_id_col].astype(str).str.upper().map(gene_order))
                .sort_values('_sort_key')
                .drop(columns='_sort_key')
            )
            
            # 필요한 컬럼만 선택
            result_df = pd.DataFrame()
            
            # gene_id와 symbol 구분해서 추출
            if 'gene_id' in filtered_df.columns and 'symbol' in filtered_df.columns:
                # 둘 다 있으면 각각 저장
                result_df['gene_id'] = filtered_df['gene_id']
                result_df['symbol'] = filtered_df['symbol']
            elif 'symbol' in filtered_df.columns:
                # symbol만 있는 경우: ENSMUSG 패턴이면 gene_id로, 아니면 symbol로
                first_value = str(filtered_df['symbol'].iloc[0]) if not filtered_df.empty else ''
                if first_value.startswith('ENSMUSG') or first_value.startswith('ENSG'):
                    # Ensembl ID 패턴이면 gene_id로 취급
                    result_df['gene_id'] = filtered_df['symbol']
                    result_df['symbol'] = ''  # symbol은 비움
                else:
                    # 일반 gene symbol이면 symbol로 취급
                    result_df['gene_id'] = ''
                    result_df['symbol'] = filtered_df['symbol']
            elif 'gene_id' in filtered_df.columns:
                # gene_id만 있으면 gene_id로 사용
                result_df['gene_id'] = filtered_df['gene_id']
                result_df['symbol'] = ''
            
            if 'log2FC' in filtered_df.columns:
                result_df['log2FC'] = filtered_df['log2FC']
            elif 'log2fc' in filtered_df.columns:
                result_df['log2FC'] = filtered_df['log2fc']
            elif 'log2FoldChange' in filtered_df.columns:
                result_df['log2FC'] = filtered_df['log2FoldChange']
            elif 'Log2FoldChange' in filtered_df.columns:
                result_df['log2FC'] = filtered_df['Log2FoldChange']
            
            if 'padj' in filtered_df.columns:
                result_df['padj'] = filtered_df['padj']
            elif 'adj_pvalue' in filtered_df.columns:
                result_df['padj'] = filtered_df['adj_pvalue']
            elif 'Padj' in filtered_df.columns:
                result_df['padj'] = filtered_df['Padj']
            
            if 'regulation' in filtered_df.columns:
                result_df['regulation'] = filtered_df['regulation']
            
            dataset_dfs[dataset.name] = result_df
        
        if not dataset_dfs:
            QMessageBox.warning(self, "No Results", 
                              "No matching genes found in selected datasets.")
            return
        
        # Wide format으로 병합
        # 1. 모든 유전자의 gene_id와 symbol 매핑 수집
        gene_mapping = {}  # {identifier: {'gene_id': ..., 'symbol': ...}}
        
        for dataset_name, df in dataset_dfs.items():
            for idx, row in df.iterrows():
                gene_id = row.get('gene_id', '')
                symbol = row.get('symbol', '')
                
                # 실제로 값이 있는 것을 기준으로 식별자 결정
                identifier = symbol if symbol else gene_id
                
                if identifier and identifier not in gene_mapping:
                    gene_mapping[identifier] = {
                        'gene_id': gene_id if gene_id else '',
                        'symbol': symbol if symbol else ''
                    }
        
        # 2. 결과 DataFrame 생성 (gene_list 입력 순서 기준으로 정렬)
        result_rows = []
        # gene_list 입력 순서대로 identifier를 순회
        ordered_identifiers = []
        seen_ids = set()
        for g in gene_list:
            g_upper = g.strip().upper()
            for identifier in gene_mapping:
                if str(identifier).upper() == g_upper and identifier not in seen_ids:
                    ordered_identifiers.append(identifier)
                    seen_ids.add(identifier)
                    break
        # gene_list에 없던 항목은 뒤에 추가 (안전 처리)
        for identifier in gene_mapping:
            if identifier not in seen_ids:
                ordered_identifiers.append(identifier)

        for identifier in ordered_identifiers:
            row = {}
            
            # gene_id와 symbol 설정
            row['gene_id'] = gene_mapping[identifier]['gene_id']
            row['symbol'] = gene_mapping[identifier]['symbol']
            
            # 각 데이터셋의 log2FC, padj 추가
            for dataset_name, df in dataset_dfs.items():
                # identifier로 해당 행 찾기
                gene_data = pd.DataFrame()
                
                if gene_mapping[identifier]['symbol']:
                    gene_data = df[df['symbol'] == gene_mapping[identifier]['symbol']]
                elif gene_mapping[identifier]['gene_id']:
                    gene_data = df[df['gene_id'] == gene_mapping[identifier]['gene_id']]
                
                if not gene_data.empty:
                    if 'log2FC' in gene_data.columns:
                        row[f'{dataset_name}_log2FC'] = gene_data['log2FC'].iloc[0]
                    if 'padj' in gene_data.columns:
                        row[f'{dataset_name}_padj'] = gene_data['padj'].iloc[0]
                    if 'regulation' in gene_data.columns:
                        row[f'{dataset_name}_regulation'] = gene_data['regulation'].iloc[0]
                else:
                    row[f'{dataset_name}_log2FC'] = None
                    row[f'{dataset_name}_padj'] = None
            
            result_rows.append(row)
        
        result_df = pd.DataFrame(result_rows)
        
        # 컬럼 순서 정렬: gene_id, symbol, D1_log2FC, D1_padj, D2_log2FC, D2_padj, ...
        ordered_columns = ['gene_id', 'symbol']
        dataset_names = list(dataset_dfs.keys())
        for dataset_name in dataset_names:
            ordered_columns.append(f'{dataset_name}_log2FC')
            ordered_columns.append(f'{dataset_name}_padj')
            if f'{dataset_name}_regulation' in result_df.columns:
                ordered_columns.append(f'{dataset_name}_regulation')
        
        # 존재하는 컬럼만 선택
        ordered_columns = [col for col in ordered_columns if col in result_df.columns]
        result_df = result_df[ordered_columns]
        
        # 탭 생성
        comparison_tab_name = f"Comparison: Gene List ({len(datasets)} datasets)"
        table = self._create_data_tab(comparison_tab_name, sheet_type='comparison')
        self.populate_table(table, result_df)
        self.logger.info(f"Gene list comparison completed: {len(result_df)} genes across {len(datasets)} datasets")

    def _compare_go_terms(self, datasets):
        """GO Term Comparison — Union 방식으로 여러 GO 데이터셋 비교"""
        from models.data_models import DatasetType, Dataset
        from models.standard_columns import StandardColumns

        # 모든 dataset이 GO_ANALYSIS 타입인지 확인
        non_go = [d.name for d in datasets if d.dataset_type != DatasetType.GO_ANALYSIS]
        if non_go:
            QMessageBox.warning(
                self,
                "Invalid Dataset Type",
                "GO Term Comparison requires all selected datasets to be GO/KEGG type.\n\n"
                f"Non-GO datasets selected:\n" + "\n".join(f"  • {n}" for n in non_go)
            )
            return

        tid_col  = StandardColumns.TERM_ID        # 'term_id'
        desc_col = StandardColumns.DESCRIPTION    # 'description'
        fe_col   = StandardColumns.FOLD_ENRICHMENT
        fdr_col  = StandardColumns.FDR
        gc_col   = StandardColumns.GENE_COUNT
        ont_col  = StandardColumns.ONTOLOGY

        # dataset 이름 → safe column prefix (공백 → '_', 중복 시 suffix)
        def _make_safe_names(names):
            seen = {}
            result = []
            for name in names:
                safe = name.replace(' ', '_').replace('-', '_')
                # 중복 처리
                if safe in seen:
                    seen[safe] += 1
                    safe = f"{safe}_{seen[safe]}"  
                else:
                    seen[safe] = 0
                result.append(safe)
            return result

        dataset_names = [d.name for d in datasets]
        safe_names    = _make_safe_names(dataset_names)

        # ── 필터 패널에서 GO Term ID 목록 읽기 ────────────────────────────
        criteria = self.filter_panel.get_filter_criteria()
        requested_ids = None

        if criteria.term_id_list:
            # GO Term ID 모드로 입력된 ID 목록
            requested_ids = [t.strip().upper() for t in criteria.term_id_list if t.strip()]
        elif criteria.gene_list:
            # Gene Symbol 모드이지만 GO ID 패턴일 수 있음 — 그대로 사용
            import re
            term_pattern = re.compile(
                r'^GO:\d+$|^R-[A-Z]+-\d+$|^[a-z]{3}\d+$|^path:[a-z]{3}\d+$',
                re.IGNORECASE
            )
            go_ids = [g.strip() for g in criteria.gene_list
                      if term_pattern.match(g.strip())]
            if go_ids:
                requested_ids = [g.upper() for g in go_ids]

        if not requested_ids:
            QMessageBox.information(
                self,
                "GO Term ID List Required",
                "Please enter GO/KEGG Term IDs in the Gene List tab (GO Term ID mode) "
                "before running GO Term Comparison.\n\n"
                "Example IDs: GO:0006955, hsa04110, R-HSA-168928"
            )
            return

        # Union: 전체 term_id 수집, description/ontology는 첫 발견 기준
        # requested_ids 목록에 있는 term_id만 포함
        term_meta = {}  # term_id → {'description': ..., 'ontology': ...}
        for ds in datasets:
            df = ds.dataframe
            if df is None or tid_col not in df.columns:
                continue
            for _, row in df.iterrows():
                tid = str(row[tid_col]).strip()
                if not tid or tid == 'nan':
                    continue
                # requested_ids 필터 적용
                if tid.upper() not in requested_ids:
                    continue
                if tid not in term_meta:
                    term_meta[tid] = {
                        'description': str(row[desc_col]) if desc_col in df.columns else tid,
                        'ontology':    str(row[ont_col])  if ont_col  in df.columns else ''
                    }

        if not term_meta:
            found_any = False
            for ds in datasets:
                df = ds.dataframe
                if df is not None and tid_col in df.columns:
                    tids_in_ds = set(df[tid_col].astype(str).str.strip().str.upper())
                    if any(r in tids_in_ds for r in requested_ids):
                        found_any = True
                        break
            if not found_any:
                QMessageBox.warning(
                    self, "No Matching Terms",
                    f"None of the {len(requested_ids)} requested term IDs were found "
                    "in any of the selected datasets.\n\n"
                    "Check that the term IDs match the format in your datasets."
                )
            else:
                QMessageBox.warning(self, "No Terms",
                                    "No GO/KEGG terms found in selected datasets.")
            return

        # Wide-format DataFrame 조립
        rows = []
        for tid, meta in term_meta.items():
            row = {'term_id': tid, 'description': meta['description'],
                   'ontology': meta['ontology']}
            for ds, safe in zip(datasets, safe_names):
                df = ds.dataframe
                if df is None or tid_col not in df.columns:
                    row[f"{safe}_fe"]         = None
                    row[f"{safe}_fdr"]        = None
                    row[f"{safe}_gene_count"] = None
                    continue
                match = df[df[tid_col].astype(str).str.strip() == tid]
                if match.empty:
                    row[f"{safe}_fe"]         = None
                    row[f"{safe}_fdr"]        = None
                    row[f"{safe}_gene_count"] = None
                else:
                    first = match.iloc[0]
                    row[f"{safe}_fe"]         = first[fe_col]  if fe_col  in df.columns else None
                    row[f"{safe}_fdr"]        = first[fdr_col] if fdr_col in df.columns else None
                    row[f"{safe}_gene_count"] = first[gc_col]  if gc_col  in df.columns else None
            rows.append(row)

        result_df = pd.DataFrame(rows)

        # 컬럼 순서 정렬
        base_cols = ['term_id', 'description', 'ontology']
        ds_cols   = []
        for safe in safe_names:
            ds_cols += [f"{safe}_fe", f"{safe}_fdr", f"{safe}_gene_count"]
        result_df = result_df[[c for c in base_cols + ds_cols if c in result_df.columns]]

        # Dataset 객체 생성 (is_go_comparison 플래그)
        tab_name = f"Comparison: GO Terms ({len(datasets)} datasets)"
        comp_dataset = Dataset(
            name=tab_name,
            dataset_type=DatasetType.GO_ANALYSIS,
            dataframe=result_df,
            original_columns={},
            metadata={
                'is_go_comparison': True,
                'dataset_names':    dataset_names,
                'safe_names':       safe_names,
                'n_terms_total':    len(result_df)
            }
        )

        table = self._create_data_tab(tab_name, sheet_type='comparison')
        self.populate_table(table, result_df, comp_dataset)

        # 비교 탭으로 자동 이동
        new_tab_index = self.data_tabs.indexOf(table)
        if new_tab_index >= 0:
            self.data_tabs.setCurrentIndex(new_tab_index)

        self.logger.info(
            f"GO term comparison: {len(result_df)} terms across {len(datasets)} datasets"
        )

    def _compare_statistics(self, datasets):
        """Statistics 필터링 비교 - Common/Unique 표시"""
        criteria = self.filter_panel.get_filter_criteria()
        
        self.logger.info(f"Statistics comparison: log2FC >= {criteria.log2fc_min}, padj <= {criteria.adj_pvalue_max}")
        
        # 각 데이터셋에 통계 필터 적용
        dataset_dfs = {}
        dataset_genes = {}
        
        for dataset in datasets:
            df = dataset.dataframe.copy()
            
            # 통계 필터 적용
            if 'log2FC' in df.columns:
                df = df[abs(df['log2FC']) >= criteria.log2fc_min]
            elif 'log2fc' in df.columns:
                df = df[abs(df['log2fc']) >= criteria.log2fc_min]
            elif 'log2FoldChange' in df.columns:
                df = df[abs(df['log2FoldChange']) >= criteria.log2fc_min]
            elif 'Log2FoldChange' in df.columns:
                df = df[abs(df['Log2FoldChange']) >= criteria.log2fc_min]
            
            if 'padj' in df.columns:
                df = df[df['padj'] <= criteria.adj_pvalue_max]
            elif 'adj_pvalue' in df.columns:
                df = df[df['adj_pvalue'] <= criteria.adj_pvalue_max]
            elif 'Padj' in df.columns:
                df = df[df['Padj'] <= criteria.adj_pvalue_max]
            
            if df.empty:
                self.logger.warning(f"No genes passed statistical criteria in dataset: {dataset.name}")
                continue
            
            self.logger.info(f"Found {len(df)} DEGs in dataset: {dataset.name}")
            
            # 표준 컬럼명으로 통일
            if 'log2fc' in df.columns and 'log2FC' not in df.columns:
                df = df.rename(columns={'log2fc': 'log2FC'})
            if 'log2FoldChange' in df.columns and 'log2FC' not in df.columns:
                df = df.rename(columns={'log2FoldChange': 'log2FC'})
            if 'Log2FoldChange' in df.columns and 'log2FC' not in df.columns:
                df = df.rename(columns={'Log2FoldChange': 'log2FC'})
            if 'adj_pvalue' in df.columns and 'padj' not in df.columns:
                df = df.rename(columns={'adj_pvalue': 'padj'})
            if 'Padj' in df.columns and 'padj' not in df.columns:
                df = df.rename(columns={'Padj': 'padj'})
            
            # 필요한 컬럼만 선택
            result_df = pd.DataFrame()
            
            # gene_id와 symbol 구분해서 추출
            if 'gene_id' in df.columns and 'symbol' in df.columns:
                # 둘 다 있으면 각각 저장
                result_df['gene_id'] = df['gene_id']
                result_df['symbol'] = df['symbol']
                # symbol을 사용해서 유전자 세트 생성
                dataset_genes[dataset.name] = set(df['symbol'].dropna().unique())
            elif 'symbol' in df.columns:
                # symbol만 있는 경우: ENSMUSG 패턴이면 gene_id로, 아니면 symbol로
                first_value = str(df['symbol'].iloc[0]) if not df.empty else ''
                if first_value.startswith('ENSMUSG') or first_value.startswith('ENSG'):
                    # Ensembl ID 패턴이면 gene_id로 취급
                    result_df['gene_id'] = df['symbol']
                    result_df['symbol'] = ''
                    dataset_genes[dataset.name] = set(df['symbol'].dropna().unique())
                else:
                    # 일반 gene symbol이면 symbol로 취급
                    result_df['gene_id'] = ''
                    result_df['symbol'] = df['symbol']
                    dataset_genes[dataset.name] = set(df['symbol'].dropna().unique())
            elif 'gene_id' in df.columns:
                # gene_id만 있으면 gene_id로 사용
                result_df['gene_id'] = df['gene_id']
                result_df['symbol'] = ''
                dataset_genes[dataset.name] = set(df['gene_id'].dropna().unique())
            else:
                self.logger.warning(f"No gene identifier found in dataset: {dataset.name}")
                continue
            
            self.logger.info(f"Extracted {len(dataset_genes[dataset.name])} unique genes from {dataset.name}")
            
            if 'log2FC' in df.columns:
                result_df['log2FC'] = df['log2FC']
            elif 'log2fc' in df.columns:
                result_df['log2FC'] = df['log2fc']
            elif 'log2FoldChange' in df.columns:
                result_df['log2FC'] = df['log2FoldChange']
            elif 'Log2FoldChange' in df.columns:
                result_df['log2FC'] = df['Log2FoldChange']
            
            if 'padj' in df.columns:
                result_df['padj'] = df['padj']
            elif 'adj_pvalue' in df.columns:
                result_df['padj'] = df['adj_pvalue']
            elif 'Padj' in df.columns:
                result_df['padj'] = df['Padj']
            
            if 'regulation' in df.columns:
                result_df['regulation'] = df['regulation']
            
            dataset_dfs[dataset.name] = result_df
        
        if not dataset_dfs:
            QMessageBox.warning(self, "No Results", 
                              "No data matched the statistical criteria.")
            return
        
        # 공통 유전자와 unique 유전자 계산
        all_genes = set()
        for genes in dataset_genes.values():
            all_genes.update(genes)
        
        common_genes = set.intersection(*dataset_genes.values()) if len(dataset_genes) > 1 else all_genes
        
        # Comparison Panel 옵션 적용
        common_genes_only = self.comparison_panel.common_genes_only.isChecked()
        include_unique = self.comparison_panel.include_unique.isChecked()
        
        # 유전자 필터링 로직
        if common_genes_only:
            # 공통 유전자만 표시
            genes_to_show = common_genes
        elif not include_unique:
            # Unique 제외 (교집합만)
            genes_to_show = common_genes
        else:
            # 전체 유전자 (기본)
            genes_to_show = all_genes
        
        # Wide format으로 병합
        # 1. 모든 유전자의 gene_id와 symbol 매핑 수집
        gene_mapping = {}  # {identifier: {'gene_id': ..., 'symbol': ...}}
        
        for dataset_name, df in dataset_dfs.items():
            for idx, row in df.iterrows():
                gene_id = row.get('gene_id', '')
                symbol = row.get('symbol', '')
                
                # 실제로 값이 있는 것을 기준으로 식별자 결정
                identifier = symbol if symbol else gene_id
                
                if identifier and identifier not in gene_mapping:
                    gene_mapping[identifier] = {
                        'gene_id': gene_id if gene_id else '',
                        'symbol': symbol if symbol else ''
                    }
        
        # 2. 결과 DataFrame 생성
        result_rows = []
        # 타입 혼합 문제 방지를 위해 문자열로 변환 후 정렬
        for identifier in sorted(gene_mapping.keys(), key=str):
            # 필터링 옵션에 따라 유전자 포함 여부 결정
            if identifier not in genes_to_show:
                continue
            
            row = {}
            
            # gene_id와 symbol 설정
            row['gene_id'] = gene_mapping[identifier]['gene_id']
            row['symbol'] = gene_mapping[identifier]['symbol']
            
            # 공통/Unique 표시
            is_common = identifier in common_genes
            datasets_with_gene = [name for name, genes in dataset_genes.items() if identifier in genes]
            
            # 공통/Unique 상태
            if is_common:
                row['Status'] = 'Common'
            else:
                row['Status'] = f"Unique ({', '.join(datasets_with_gene)})"
            
            row['Found_in'] = f"{len(datasets_with_gene)}/{len(datasets)}"
            
            # 각 데이터셋의 log2FC, padj 추가
            for dataset_name, df in dataset_dfs.items():
                # identifier로 해당 행 찾기
                gene_data = pd.DataFrame()
                
                if gene_mapping[identifier]['symbol']:
                    gene_data = df[df['symbol'] == gene_mapping[identifier]['symbol']]
                elif gene_mapping[identifier]['gene_id']:
                    gene_data = df[df['gene_id'] == gene_mapping[identifier]['gene_id']]
                
                if not gene_data.empty:
                    if 'log2FC' in gene_data.columns:
                        row[f'{dataset_name}_log2FC'] = gene_data['log2FC'].iloc[0]
                    if 'padj' in gene_data.columns:
                        row[f'{dataset_name}_padj'] = gene_data['padj'].iloc[0]
                    if 'regulation' in gene_data.columns:
                        row[f'{dataset_name}_regulation'] = gene_data['regulation'].iloc[0]
                else:
                    row[f'{dataset_name}_log2FC'] = None
                    row[f'{dataset_name}_padj'] = None
            
            result_rows.append(row)
        
        result_df = pd.DataFrame(result_rows)
        
        # 컬럼 순서 정렬: gene_id, symbol, Status, Found_in, D1_log2FC, D1_padj, ...
        ordered_columns = ['gene_id', 'symbol', 'Status', 'Found_in']
        dataset_names = list(dataset_dfs.keys())
        for dataset_name in dataset_names:
            ordered_columns.append(f'{dataset_name}_log2FC')
            ordered_columns.append(f'{dataset_name}_padj')
            if f'{dataset_name}_regulation' in result_df.columns:
                ordered_columns.append(f'{dataset_name}_regulation')
        
        # 존재하는 컬럼만 선택
        ordered_columns = [col for col in ordered_columns if col in result_df.columns]
        result_df = result_df[ordered_columns]
        
        # 탭 생성
        comparison_tab_name = f"Comparison: Statistics ({len(datasets)} datasets)"
        table = self._create_data_tab(comparison_tab_name, sheet_type='comparison')
        self.populate_table(table, result_df)

        # 통계 정보 로그
        self.logger.info(f"Statistics comparison completed:")
        self.logger.info(f"  - Total unique genes: {len(all_genes)}")
        self.logger.info(f"  - Common genes (in all datasets): {len(common_genes)}")
        for name, genes in dataset_genes.items():
            unique_to_dataset = genes - set.union(*(g for n, g in dataset_genes.items() if n != name))
            self.logger.info(f"  - Unique to {name}: {len(unique_to_dataset)}")
    
    def _update_comparison_panel_datasets(self):
        """비교 패널의 데이터셋 리스트 업데이트, Multi-Omics 패널 콤보박스도 갱신"""
        dataset_names = self.dataset_manager.get_all_datasets()
        self.comparison_panel.update_dataset_list(dataset_names)
        # Multi-Omics 패널이 표시 중이면 콤보박스도 갱신
        if hasattr(self, 'multi_omics_panel') and self.multi_omics_panel.isVisible():
            self.multi_omics_panel.refresh_dataset_list(self.presenter.datasets)


    
    def _on_analysis_requested(self, analysis_type: str):
        """분석 요청"""
        # GO Advanced Filter 요청인 경우
        if analysis_type == "go_advanced_filter":
            self._on_filter_go_results()
            return
        
        # Comparison 요청인 경우
        if analysis_type == "comparison":
            self._on_compare_datasets()
            return
        
        # 기존 분석 요청 (fisher, gsea 등)
        gene_list = self.filter_panel.get_gene_list()
        
        # Statistical filter 설정값 가져오기
        adj_pvalue_cutoff = self.filter_panel.adj_pvalue_input.value()
        log2fc_cutoff = self.filter_panel.log2fc_input.value()
        
        self.presenter.run_analysis(analysis_type, gene_list, adj_pvalue_cutoff, log2fc_cutoff)
    
    def _on_compare_datasets(self):
        """데이터셋 비교"""
        selected_datasets = self.dataset_manager.get_selected_datasets()
        if len(selected_datasets) < 2:
            QMessageBox.warning(self, "Warning", "Please select at least 2 datasets to compare.")
            return
        
        self.presenter.compare_datasets(selected_datasets)
    
    def _on_export_data(self):
        """데이터 내보내기"""
        file_path, file_filter = QFileDialog.getSaveFileName(
            self, "Export Data", "", 
            "Excel Files (*.xlsx);;CSV Files (*.csv);;TSV Files (*.tsv)"
        )
        
        if file_path:
            current_tab = self.data_tabs.currentWidget()
            if isinstance(current_tab, QTableWidget):
                self.presenter.export_data(Path(file_path), current_tab)
    
    def _remove_tab_safely(self, index: int):
        """
        탭 제거 + tab_data 인덱스 재정렬.

        removeTab()이 currentChanged를 동기적으로 발화하기 때문에,
        tab_data를 먼저 정리한 뒤 실제 탭을 제거해야 _on_tab_changed가
        올바른 데이터를 읽을 수 있다.
        """
        # 1. 트리: 닫히는 시트 노드 제거
        self.dataset_manager.remove_sheet(index)
        # 트리: index보다 큰 child 노드의 tab_index를 1씩 당김
        for key in sorted(self.tab_data.keys()):
            if key > index:
                self.dataset_manager.update_sheet_tab_index(key, key - 1)

        # 2. tab_data: 제거 대상 삭제
        if index in self.tab_data:
            del self.tab_data[index]

        # 3. index보다 큰 키를 1씩 당김 (removeTab 후 탭 shift 반영)
        shifted: dict = {}
        for key, value in self.tab_data.items():
            shifted[key - 1 if key > index else key] = value
        self.tab_data = shifted

        # 4. 실제 탭 제거 (currentChanged 신호 발화)
        self.data_tabs.removeTab(index)

    def _pin_plot_to_tab(self, widget, label: str, plot_type: str,
                          plot_params: dict, parent_dataset: str = None):
        """Plot widget을 새 탭으로 고정"""
        tab_index = self.data_tabs.addTab(widget, f"📈 {label}")
        # tab_data를 setCurrentIndex 전에 설정해야 _on_tab_changed에서 dock을 바로 업데이트할 수 있음
        self.tab_data[tab_index] = {
            'dataframe': None,
            'dataset': None,
            'parent_dataset': parent_dataset,
            'sheet_type': 'plot',
            'sheet_label': label,
            'filter_params': None,
            'comparison_params': None,
            'plot_type': plot_type,
            'plot_params': plot_params,
            'plot_widget': widget,
        }
        self.data_tabs.setCurrentIndex(tab_index)
        if parent_dataset and hasattr(self, 'dataset_manager'):
            self.dataset_manager.add_sheet(parent_dataset, tab_index, label, 'plot')
        self.logger.info(f"Plot pinned to tab: {label} (type={plot_type})")

    def _on_tab_close_requested(self, index: int):
        """탭 닫기 요청"""
        if index > 0:  # 첫 번째 탭(Whole Dataset)은 닫지 않음
            self._remove_tab_safely(index)
            self._update_menu_states(self.presenter.fsm.current_state)
    
    def _on_tab_changed(self, index: int):
        """탭 변경 시 메뉴 상태 및 current_dataset 업데이트"""
        # 메뉴가 생성되었는지 확인
        if not hasattr(self, 'export_action'):
            return
        
        if index >= 0:
            self._update_menu_states(self.presenter.fsm.current_state)
            
            # 탭에 저장된 dataset으로 current_dataset 업데이트
            if index in self.tab_data:
                dataset = self.tab_data[index]['dataset']
                if dataset is not None:
                    self.presenter.current_dataset = dataset
                    self.logger.info(f"Tab changed to index {index}: current_dataset updated to '{dataset.name}'")

            # GO_ANALYSIS 데이터일 때만 Gene List 탭에 모드 토글 표시
            self._update_filter_panel_go_mode(index)

            # ATAC-seq 필터 섹션 및 전용 시각화 메뉴 업데이트
            self._update_atac_ui(index)

            # 트리 선택 동기화
            self.dataset_manager.sync_selection(index)

            # ── Plot Settings Dock 업데이트 ────────────────────────────
            self._update_plot_settings_dock(index)

    def _update_plot_settings_dock(self, index: int):
        """현재 탭이 plot 탭이면 우측 Settings Dock에 해당 위젯의 설정 패널을 표시"""
        if not hasattr(self, 'plot_settings_dock'):
            return

        entry = self.tab_data.get(index, {})
        if entry.get('sheet_type') == 'plot':
            plot_widget = entry.get('plot_widget')
            if plot_widget and hasattr(plot_widget, 'get_settings_panel'):
                new_panel = plot_widget.get_settings_panel()
                if new_panel is not None and new_panel is not self._current_settings_widget:
                    self.plot_settings_dock.setWidget(new_panel)
                    self._current_settings_widget = new_panel
                    # dock 제목을 plot 타입에 맞게 업데이트
                    plot_type = entry.get('plot_type', 'Plot')
                    self.plot_settings_dock.setWindowTitle(
                        f"{plot_type.capitalize()} Settings" if plot_type else "Plot Settings"
                    )
                if not self.plot_settings_dock.isVisible():
                    self.plot_settings_dock.show()
                return
        # 비-plot 탭 → dock 숨김
        self.plot_settings_dock.hide()
        self._current_settings_widget = None

    # ── Activity Bar ─────────────────────────────────────────────────

    def _build_activity_bar(self) -> QWidget:
        """Activity Bar 위젯 생성 (좌측 세로 아이콘 바)"""
        bar = QWidget()
        bar.setObjectName("ActivityBar")
        bar.setFixedWidth(44)
        bar.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        bar.setStyleSheet("""
            QWidget#ActivityBar {
                background: #ebebeb;
                border-right: 1px solid #ccc;
            }
            QToolButton {
                background: transparent;
                border: none;
                color: #555;
                font-size: 18px;
                border-radius: 4px;
                padding: 6px 4px;
            }
            QToolButton:hover {
                background: #d6d6d6;
                color: #222;
            }
            QToolButton:checked {
                background: #cde4f5;
                color: #005a9e;
                border-left: 2px solid #0078d4;
            }
        """)
        bar_layout = QVBoxLayout(bar)
        bar_layout.setContentsMargins(2, 6, 2, 6)
        bar_layout.setSpacing(4)

        self._act_dataset_btn = QToolButton()
        self._act_dataset_btn.setText("≡")
        self._act_dataset_btn.setToolTip("Datasets")
        self._act_dataset_btn.setFixedSize(40, 40)
        self._act_dataset_btn.setCheckable(True)
        self._act_dataset_btn.setChecked(False)
        self._act_dataset_btn.clicked.connect(self._on_act_dataset_clicked)
        bar_layout.addWidget(self._act_dataset_btn)

        self._act_filter_btn = QToolButton()
        self._act_filter_btn.setText("⊟")
        self._act_filter_btn.setToolTip("Filter / Compare")
        self._act_filter_btn.setFixedSize(40, 40)
        self._act_filter_btn.setCheckable(True)
        self._act_filter_btn.setChecked(True)
        self._act_filter_btn.clicked.connect(self._on_act_filter_clicked)
        bar_layout.addWidget(self._act_filter_btn)

        bar_layout.addStretch()

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #ccc;")
        bar_layout.addWidget(sep)

        self._act_split_btn = QToolButton()
        self._act_split_btn.setText("∥")
        self._act_split_btn.setToolTip("Split View — show both panels")
        self._act_split_btn.setFixedSize(40, 40)
        self._act_split_btn.setCheckable(True)
        self._act_split_btn.setChecked(False)
        self._act_split_btn.clicked.connect(self._on_act_split_toggled)
        bar_layout.addWidget(self._act_split_btn)

        return bar

    def _on_act_dataset_clicked(self, checked: bool):
        """Datasets 패널 토글 (비분할 모드에서는 Filter와 상호 배타)"""
        if checked and not self._split_view_active:
            self._set_panel_visible(self.func_container, False, is_func=True)
            self._act_filter_btn.setChecked(False)
            self._menu_filter_action.setChecked(False)
        self._set_panel_visible(self.tree_container, checked, is_func=False)
        self._menu_datasets_action.setChecked(checked)

    def _on_act_filter_clicked(self, checked: bool):
        """Filter/Compare 패널 토글 (비분할 모드에서는 Datasets와 상호 배타)"""
        if checked and not self._split_view_active:
            self._set_panel_visible(self.tree_container, False, is_func=False)
            self._act_dataset_btn.setChecked(False)
            self._menu_datasets_action.setChecked(False)
        self._set_panel_visible(self.func_container, checked, is_func=True)
        self._menu_filter_action.setChecked(checked)

    def _on_act_split_toggled(self, checked: bool):
        """Split View 토글: 두 패널 동시 표시 ↔ 단일 패널"""
        self._split_view_active = checked
        self._menu_split_action.setChecked(checked)
        if checked:
            self._set_panel_visible(self.tree_container, True, is_func=False)
            self._set_panel_visible(self.func_container, True, is_func=True)
            self._act_dataset_btn.setChecked(True)
            self._act_filter_btn.setChecked(True)
            self._menu_datasets_action.setChecked(True)
            self._menu_filter_action.setChecked(True)
        else:
            # Filter만 유지, 트리 숨김
            self._set_panel_visible(self.tree_container, False, is_func=False)
            self._act_dataset_btn.setChecked(False)
            self._menu_datasets_action.setChecked(False)

    # ── View 메뉴 핸들러 ───────────────────────────────────────

    def _on_menu_datasets_toggled(self, checked: bool):
        """View > Panels > Datasets 메뉴 → activity bar로 위임"""
        self._act_dataset_btn.setChecked(checked)
        self._on_act_dataset_clicked(checked)

    def _on_menu_filter_toggled(self, checked: bool):
        """View > Panels > Filter/Compare 메뉴 → activity bar로 위임"""
        self._act_filter_btn.setChecked(checked)
        self._on_act_filter_clicked(checked)

    def _on_menu_split_toggled(self, checked: bool):
        """View > Panels > Split View 메뉴 → activity bar로 위임"""
        self._act_split_btn.setChecked(checked)
        self._on_act_split_toggled(checked)

    def _set_panel_visible(self, panel: QWidget, visible: bool, *, is_func: bool):
        """패널 표시/숨김 + splitter 크기 복원"""
        if visible == panel.isVisible():
            return
        if visible:
            sizes = self.main_splitter.sizes()
            panel.setVisible(True)
            width = (self._func_panel_width if is_func else self._tree_panel_width) or (260 if is_func else 200)
            idx = 1 if is_func else 0
            new_sizes = list(sizes)
            new_sizes[idx] = width
            new_sizes[2] = max(new_sizes[2] - width, 300)
            self.main_splitter.setSizes(new_sizes)
        else:
            sizes = self.main_splitter.sizes()
            idx = 1 if is_func else 0
            if sizes[idx] > 0:
                if is_func:
                    self._func_panel_width = sizes[idx]
                else:
                    self._tree_panel_width = sizes[idx]
            panel.setVisible(False)

    def _toggle_tree_panel(self):
        """레거시 호환 — activity bar로 위임"""
        checked = not self.tree_container.isVisible()
        self._act_dataset_btn.setChecked(checked)
        self._on_act_dataset_clicked(checked)

    def _toggle_func_panel(self):
        """레거시 호환 — activity bar로 위임"""
        checked = not self.func_container.isVisible()
        self._act_filter_btn.setChecked(checked)
        self._on_act_filter_clicked(checked)

    def _on_tree_sheet_selected(self, tab_index: int):
        """트리에서 시트 클릭 → 탭 활성화"""
        if 0 <= tab_index < self.data_tabs.count():
            self.data_tabs.setCurrentIndex(tab_index)

    def _on_file_dropped(self, file_path: str):
        """DatasetTreePanel 드롭 → 파일 로드"""
        self._load_dataset_with_name(file_path)

    def _on_dataset_tree_root_added(self, dataset_name: str):
        """루트 노드 추가 후 해당 dataset의 whole 시트를 트리에 등록"""
        for tab_index, entry in self.tab_data.items():
            if (entry.get('sheet_type') == 'whole'
                    and entry.get('parent_dataset') == dataset_name
                    and self.dataset_manager._find_child_by_tab(tab_index) is None):
                sheet_label = self.data_tabs.tabText(tab_index)
                self.dataset_manager.add_sheet(dataset_name, tab_index, sheet_label, 'whole')

    def _update_filter_panel_go_mode(self, tab_index: int):
        """
        현재 탭의 dataset type이 GO_ANALYSIS이면 FilterPanel Gene List 탭에
        GO Term ID 모드 토글을 표시하고, 그 외에는 숨긴다.
        Gene Symbol 모드로 초기화하지 않아 사용자의 선택을 유지한다.
        """
        from models.data_models import DatasetType
        is_go = False
        if tab_index in self.tab_data:
            dataset = self.tab_data[tab_index]['dataset']
            if dataset is not None and dataset.dataset_type == DatasetType.GO_ANALYSIS:
                is_go = True

        if hasattr(self.filter_panel, 'go_mode_widget'):
            self.filter_panel.go_mode_widget.setVisible(is_go)
            # GO 탭이 아니면 항상 Gene Symbol 모드로 복귀
            if not is_go and hasattr(self.filter_panel, 'gene_symbol_radio'):
                self.filter_panel.gene_symbol_radio.setChecked(True)

    def _update_atac_ui(self, tab_index: int):
        """
        현재 탭이 ATAC_SEQ 데이터셋이면:
          - FilterPanel의 ATAC 섹션 표시 및 annotation 드롭다운 갱신
          - Visualization 메뉴의 ATAC 전용 항목 활성화
        그 외에는 ATAC 섹션을 숨기고 메뉴 비활성화.
        """
        from models.data_models import DatasetType
        dataset = None
        if tab_index in self.tab_data:
            dataset = self.tab_data[tab_index]['dataset']

        is_atac = (dataset is not None and
                   dataset.dataset_type == DatasetType.ATAC_SEQ)
        is_multi_omics = (dataset is not None and
                          dataset.dataset_type == DatasetType.MULTI_OMICS)
        is_motif = (dataset is not None and
                    dataset.dataset_type == DatasetType.MOTIF_ENRICHMENT)
        is_footprint = (dataset is not None and
                        dataset.dataset_type == DatasetType.TF_FOOTPRINT)
        is_chromvar = (dataset is not None and
                       dataset.dataset_type == DatasetType.CHROMVAR_DIFF_TF)

        # FilterPanel 갱신
        if hasattr(self.filter_panel, 'update_for_dataset'):
            self.filter_panel.update_for_dataset(dataset if is_atac else None)

        # ATAC 전용 Visualization 메뉴 활성화
        if hasattr(self, 'genomic_dist_action'):
            self.genomic_dist_action.setEnabled(is_atac)
        if hasattr(self, 'tss_distance_action'):
            self.tss_distance_action.setEnabled(is_atac)
        if hasattr(self, 'ma_plot_action'):
            self.ma_plot_action.setEnabled(is_atac)
        if hasattr(self, 'motif_enrichment_action'):
            self.motif_enrichment_action.setEnabled(is_motif)
        if hasattr(self, 'tf_footprint_action'):
            self.tf_footprint_action.setEnabled(is_footprint)
        if hasattr(self, 'chromvar_action'):
            self.chromvar_action.setEnabled(is_chromvar)

        # Multi-Omics 전용 Visualization 메뉴 활성화
        for action_name in ('quadrant_plot_action', 'concordance_heatmap_action',
                            'concordance_summary_action', 'integrated_volcano_action'):
            if hasattr(self, action_name):
                getattr(self, action_name).setEnabled(is_multi_omics)

    def _on_clear_log(self):
        """로그 지우기"""
        self.log_terminal.clear()
        self.log_buffer.clear()
    
    def _on_column_level_changed(self, level: str):
        """컬럼 표시 레벨 변경 - 모든 탭에 즉시 적용 (Comparison 탭 제외)"""
        self.column_display_level = level
        self.logger.info(f"Column display level changed to: {level}")
        
        # 모든 탭의 데이터를 다시 표시
        for tab_index in range(self.data_tabs.count()):
            # Comparison 탭은 건너뛰기
            tab_name = self.data_tabs.tabText(tab_index)
            if tab_name.startswith("Comparison:"):
                continue
            
            if tab_index in self.tab_data:
                dataframe = self.tab_data[tab_index]['dataframe']
                dataset = self.tab_data[tab_index]['dataset']
                table = self.data_tabs.widget(tab_index)
                if isinstance(table, QTableWidget):
                    # 테이블 재구성
                    self._refresh_table(table, dataframe, dataset)
        
        self.status_label.setText(f"Column level: {level}")
    
    def _on_precision_changed(self, precision: int):
        """유효숫자 변경 - 모든 탭에 즉시 적용"""
        self.decimal_precision = precision
        self.logger.info(f"Decimal precision changed to: {precision}")
        
        # 모든 탭의 데이터를 다시 표시
        for tab_index in range(self.data_tabs.count()):
            if tab_index in self.tab_data:
                dataframe = self.tab_data[tab_index]['dataframe']
                dataset = self.tab_data[tab_index]['dataset']
                table = self.data_tabs.widget(tab_index)
                if isinstance(table, QTableWidget):
                    # 테이블 재구성
                    self._refresh_table(table, dataframe, dataset)
        
        self.status_label.setText(f"Precision: {precision} decimals")
    
    def _refresh_table(self, table: QTableWidget, dataframe: pd.DataFrame, dataset=None):
        """
        테이블 새로고침 (컬럼 레벨 및 정밀도 재적용)
        
        Args:
            table: QTableWidget
            dataframe: 원본 DataFrame
            dataset: Dataset 객체
        """
        if dataframe is None or dataframe.empty:
            return
        
        # 컬럼 필터링
        columns = self._filter_columns(dataframe.columns.tolist(), dataset)
        filtered_df = dataframe[columns]
        
        # 테이블 설정
        table.clearContents()
        table.setRowCount(len(filtered_df))
        table.setColumnCount(len(columns))
        table.setHorizontalHeaderLabels(columns)
        
        # 데이터 채우기
        for i, row in enumerate(filtered_df.values):
            for j, value in enumerate(row):
                # 유효숫자 적용
                if isinstance(value, float):
                    formatted_value = f"{value:.{self.decimal_precision}f}"
                else:
                    formatted_value = str(value)
                
                item = QTableWidgetItem(formatted_value)
                table.setItem(i, j, item)
        
        # 컬럼 크기 자동 조정
        table.resizeColumnsToContents()
    
    def _on_about(self):
        """About 다이얼로그"""
        dlg = QDialog(self)
        dlg.setWindowTitle("About CMG-SeqViewer")
        dlg.setFixedWidth(520)

        root = QVBoxLayout(dlg)
        root.setContentsMargins(24, 24, 24, 16)
        root.setSpacing(12)

        # --- logo + title row ---
        top_row = QHBoxLayout()
        top_row.setSpacing(16)

        logo_label = QLabel()
        logo_path = Path(__file__).parent.parent.parent / "CMG.png"
        if logo_path.exists():
            pm = QPixmap(str(logo_path)).scaledToHeight(
                90, Qt.TransformationMode.SmoothTransformation
            )
            logo_label.setPixmap(pm)
        logo_label.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignHCenter)
        top_row.addWidget(logo_label)

        title_label = QLabel(
            "<h2 style='margin:0;'>CMG-SeqViewer</h2>"
            "<p style='margin:2px 0;'><b>Version 1.2.1</b></p>"
            "<p style='margin:2px 0; color:#555;'>RNA-Seq Data Analysis &amp; Visualization</p>"
        )
        title_label.setWordWrap(True)
        title_label.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        top_row.addWidget(title_label, 1)
        root.addLayout(top_row)

        # --- feature text ---
        from PyQt6.QtWidgets import QTextBrowser
        body = QTextBrowser()
        body.setOpenExternalLinks(True)
        body.setReadOnly(True)
        body.setMaximumHeight(320)
        body.setHtml(
            "<p><b>Key Features:</b></p>"
            "<ul>"
            "<li><b>Data Management:</b> Multi-dataset loading, Parquet database, Import Folder</li>"
            "<li><b>Filtering:</b> Gene list and statistical filtering with active tab support</li>"
            "<li><b>Statistical Analysis:</b> Fisher's Exact Test, GSEA Lite</li>"
            "<li><b>Visualizations:</b> Volcano plots, Heatmaps, PCA Plot, P-adj Histograms</li>"
            "<li><b>Comparison Tools:</b> Venn diagrams (2-3 datasets), Dataset statistics comparison</li>"
            "<li><b>🌡️ Multi-Group Heatmap:</b> LRT omnibus result → Z-score clustermap with "
            "group colour bars, gene cluster cutting, and CSV/Parquet export</li>"
            "</ul>"
            "<p><b>Advanced Features:</b></p>"
            "<ul>"
            "<li>Multi-Group: auto-detected from LRT CSV; gene-list filtering creates child sheets "
            "passable directly into the heatmap dialog</li>"
            "<li>PCA Plot — sample-level expression PCA (Ctrl+P)</li>"
            "<li>Import Folder — one-click pipeline output merging</li>"
            "<li>merge_db.py — CLI batch-merge tool</li>"
            "<li>Sig. Genes: padj &lt; 0.05 AND |log2FC| &gt; 1</li>"
            "<li>GO Clustering — grid-cell layout for readability</li>"
            "<li>Interactive tooltips with boundary detection</li>"
            "<li>Cell-level selection and clipboard support (Ctrl+C/V)</li>"
            "<li>Column display levels (Basic, DE Analysis, Full)</li>"
            "</ul>"
            "<p><b>Developed with:</b> Python, PyQt6, Pandas, Matplotlib, Seaborn, SciPy, NumPy</p>"
            "<p style='color:#777;'>&copy; 2025 ibs CMG NGS core</p>"
        )
        root.addWidget(body)

        # --- close button ---
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        close_btn = QPushButton("Close")
        close_btn.setFixedWidth(80)
        close_btn.clicked.connect(dlg.accept)
        btn_row.addWidget(close_btn)
        root.addLayout(btn_row)

        dlg.exec()
    
    def _on_help_documentation(self):
        """Help documentation dialog"""
        dialog = HelpDialog(self)
        dialog.exec()
    
    def _on_visualization_requested(self, viz_type: str):
        """시각화 요청 처리"""
        try:
            # 현재 탭 확인
            current_index = self.data_tabs.currentIndex()
            if current_index < 0:
                QMessageBox.warning(self, "No Data", 
                                  "Please load a dataset first.")
                return
            
            # 현재 탭의 데이터 가져오기
            if current_index not in self.tab_data:
                QMessageBox.warning(self, "No Data", 
                                  "No data available in current tab.")
                return
            
            dataframe = self.tab_data[current_index]['dataframe']
            dataset = self.tab_data[current_index]['dataset']
            
            # Comparison 결과인지 확인 (dataset이 None인 경우)
            if dataset is None:
                QMessageBox.warning(self, "Invalid Data", 
                                  "Visualization is not available for comparison results.\n"
                                  "Please select a single dataset tab.")
                return
            
            # 필요한 컬럼 확인
            if viz_type == "volcano":
                required_cols = ['log2FC', 'padj']
            elif viz_type == "histogram":
                required_cols = ['padj']
            elif viz_type == "heatmap":
                required_cols = []  # Heatmap은 샘플 발현 데이터 자동 탐지
            elif viz_type == "pca":
                # PCA: DE 데이터셋만 허용, 컬럼 검사는 다이얼로그 내부에서 수행
                if dataset.dataset_type.value != "DE":
                    from models.data_models import DatasetType as _DT
                    if dataset.dataset_type != _DT.DIFFERENTIAL_EXPRESSION:
                        QMessageBox.warning(
                            self, "PCA — DE Dataset Required",
                            "PCA Plot is only available for Differential Expression datasets.\n"
                            "Please select a DE dataset tab."
                        )
                        return
                dataset_name = dataset.name if hasattr(dataset, 'name') else ""
                dialog = PCADialog(dataframe, dataset_name=dataset_name, parent=self)
                dialog.exec()
                self.logger.info("Visualization opened: pca")
                return
            else:
                QMessageBox.warning(self, "Unknown Visualization", 
                                  f"Unknown visualization type: {viz_type}")
                return
            
            # DataFrame은 이미 표준 컬럼명을 사용하고 있음
            # 시각화 다이얼로그용으로 일부 컬럼명만 변경
            from models.standard_columns import StandardColumns
            
            df = dataframe.copy()
            rename_map = {
                StandardColumns.LOG2FC: 'log2FC',
                StandardColumns.ADJ_PVALUE: 'padj',
                StandardColumns.PVALUE: 'pvalue',
            }
            
            # 표준 컬럼명을 시각화용 이름으로 변경
            df = df.rename(columns=rename_map)
            
            # 필수 컬럼 확인 (heatmap 제외)
            if required_cols:
                missing_cols = [col for col in required_cols if col not in df.columns]
                if missing_cols:
                    # 디버깅: 사용 가능한 컬럼 표시
                    available = ', '.join(df.columns.tolist()[:10])  # 처음 10개만
                    QMessageBox.warning(self, "Missing Columns", 
                                      f"Required columns not found: {', '.join(missing_cols)}\n\n"
                                      f"Available columns: {available}...\n\n"
                                      "This dataset may not support this visualization.")
                    return
            
            # 시각화 다이얼로그 열기
            if viz_type == "volcano":
                dialog = VolcanoPlotDialog(df, self)
                _parent_ds = self.tab_data.get(self.data_tabs.currentIndex(), {}).get('parent_dataset')
                dialog.plot_pinned.connect(
                    lambda w, lbl, pt, pp, _pd=_parent_ds: self._pin_plot_to_tab(w, lbl, pt, pp, _pd)
                )
                dialog.exec()
            elif viz_type == "histogram":
                dialog = PadjHistogramDialog(df, self)
                dialog.exec()
            elif viz_type == "heatmap":
                dialog = HeatmapDialog(df, self)
                _parent_ds = self.tab_data.get(self.data_tabs.currentIndex(), {}).get('parent_dataset')
                dialog.plot_pinned.connect(
                    lambda w, lbl, pt, pp, _pd=_parent_ds: self._pin_plot_to_tab(w, lbl, pt, pp, _pd)
                )
                dialog.exec()
            
            self.logger.info(f"Visualization opened: {viz_type}")
            
        except Exception as e:
            self.logger.error(f"Visualization failed: {e}")
            QMessageBox.critical(self, "Visualization Error", 
                               f"Failed to create visualization:\n{str(e)}")
    
    def _on_multi_group_heatmap(self):
        """Multi-Group Heatmap 다이얼로그 열기"""
        try:
            current_index = self.data_tabs.currentIndex()
            if current_index < 0 or current_index not in self.tab_data:
                QMessageBox.warning(self, "No Data", "Please load a dataset first.")
                return
            dataset = self.tab_data[current_index]['dataset']
            from models.data_models import DatasetType as _DT
            if dataset is None or dataset.dataset_type != _DT.MULTI_GROUP:
                QMessageBox.warning(
                    self, "Multi-Group Dataset Required",
                    "Multi-Group Heatmap is only available for Multi-Group datasets.\n"
                    "Load a multi_group_result.csv (LRT omnibus result) file first."
                )
                return
            from gui.multi_group_heatmap_dialog import MultiGroupHeatmapDialog
            dialog = MultiGroupHeatmapDialog(dataset, parent=self)
            dialog.exec()
            self.logger.info("Visualization opened: multi_heatmap")
        except Exception as e:
            self.logger.error(f"Multi-Group Heatmap failed: {e}")
            QMessageBox.critical(self, "Error", f"Failed to open Multi-Group Heatmap:\n{str(e)}")

    def _on_gene_expression_bar(self):
        """Gene Expression Bar+Scatter (Grouped) 다이얼로그 열기.

        현재 탭의 데이터셋에 샘플별 발현 컬럼이 있어야 한다. filtered DE 시트에서
        소수 유전자를 그룹별 막대(mean)+개별 점으로 비교하는 데 가장 유용하다.
        """
        try:
            current_index = self.data_tabs.currentIndex()
            if current_index < 0 or current_index not in self.tab_data:
                QMessageBox.warning(self, "No Data", "Please open a dataset tab first.")
                return
            dataset = self.tab_data[current_index]['dataset']
            if dataset is None or dataset.dataframe is None or dataset.dataframe.empty:
                QMessageBox.warning(self, "No Data", "The current tab has no data.")
                return

            from gui.gene_expression_bar_dialog import GeneExpressionBarDialog
            # 부모 데이터셋 이름("CTX200A vs CTX0A DE")을 그룹 라벨 시드 힌트로 전달
            # (filtered 시트는 자기 이름에 그룹 정보가 없으므로 부모 이름이 핵심 단서)
            name_hint = self.tab_data[current_index].get('parent_dataset') or dataset.name
            dialog = GeneExpressionBarDialog(dataset, parent=self, name_hint=name_hint)
            if not dialog.has_data:
                QMessageBox.warning(
                    self, "No Sample Columns",
                    "This plot needs per-sample expression columns "
                    "(e.g. Ctrl_1, Ctrl_2, Treat_1 ...).\n\n"
                    "The current dataset has none that could be detected. "
                    "Open a DE dataset (or its Filtered sheet) that keeps sample-level counts."
                )
                return
            dialog.exec()
            self.logger.info("Visualization opened: gene_expression_bar")
        except Exception as e:
            self.logger.error(f"Gene Expression Bar failed: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Failed to open Gene Expression Bar plot:\n{str(e)}")

    def _on_dotplot_requested(self):
        """Dot Plot 시각화 (Comparison Data)"""
        # 현재 탭이 Comparison sheet인지 확인
        current_index = self.data_tabs.currentIndex()
        current_tab_name = self.data_tabs.tabText(current_index)

        # GO Term Comparison 탭이면 GO/KEGG Dot Plot으로 안내
        if current_tab_name.startswith("Comparison: GO Terms"):
            QMessageBox.information(
                self,
                "Use GO/KEGG Dot Plot",
                "This tab contains GO Term Comparison data.\n\n"
                "Please use:  Visualization → 🧬 GO/KEGG Dot Plot"
            )
            return
        
        if not (current_tab_name.startswith("Comparison: Statistics") or 
                current_tab_name.startswith("Comparison: Gene List")):
            QMessageBox.warning(self, "Invalid Tab", 
                              "Please open a Comparison sheet (Statistics or Gene List) to create a Dot Plot.")
            return
        
        # 현재 탭에서 DataFrame 가져오기
        try:
            current_table = self.data_tabs.widget(current_index)
            if not isinstance(current_table, QTableWidget):
                return
            
            # QTableWidget에서 DataFrame으로 변환
            row_count = current_table.rowCount()
            col_count = current_table.columnCount()
            
            # 헤더 가져오기
            headers = []
            for col in range(col_count):
                header_item = current_table.horizontalHeaderItem(col)
                if header_item:
                    headers.append(header_item.text())
            
            # 데이터 가져오기
            data = []
            for row in range(row_count):
                row_data = []
                for col in range(col_count):
                    item = current_table.item(row, col)
                    if item:
                        text = item.text()
                        # 숫자 변환 시도
                        try:
                            if text.lower() == 'nan' or text == '':
                                row_data.append(None)
                            else:
                                row_data.append(float(text))
                        except ValueError:
                            row_data.append(text)
                    else:
                        row_data.append(None)
                data.append(row_data)
            
            # DataFrame 생성
            comparison_df = pd.DataFrame(data, columns=headers)
            
            # Dot Plot dialog 생성
            dialog = DotPlotDialog(comparison_df, self)
            dialog.exec()
            
        except Exception as e:
            self.logger.error(f"Failed to create Dot Plot: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", 
                               f"Failed to create Dot Plot:\n{str(e)}")
    
    def _on_venn_diagram(self):
        """Venn Diagram 시각화"""
        # 현재 탭 이름 확인
        current_tab_name = self.data_tabs.tabText(self.data_tabs.currentIndex())
        
        # Comparison sheet인 경우
        if current_tab_name.startswith("Comparison: Statistics"):
            self._create_venn_from_comparison_sheet()
            return
        
        # 일반적인 경우: 2-3개 데이터셋 선택
        all_datasets = list(self.presenter.datasets.values())
        
        if len(all_datasets) < 2:
            QMessageBox.warning(self, "Insufficient Datasets", 
                              "Please load at least 2 datasets to create a Venn diagram.")
            return
        
        if len(all_datasets) > 3:
            # 사용자에게 선택하도록 요청
            from PyQt6.QtWidgets import QDialog, QVBoxLayout, QListWidget, QDialogButtonBox
            
            dialog = QDialog(self)
            dialog.setWindowTitle("Select Datasets for Venn Diagram")
            dialog.setMinimumWidth(400)
            
            layout = QVBoxLayout(dialog)
            layout.addWidget(QLabel("Select 2 or 3 datasets to compare:"))
            
            list_widget = QListWidget()
            list_widget.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
            for ds in all_datasets:
                list_widget.addItem(ds.name)
            layout.addWidget(list_widget)
            
            buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
            buttons.accepted.connect(dialog.accept)
            buttons.rejected.connect(dialog.reject)
            layout.addWidget(buttons)
            
            if dialog.exec() == QDialog.DialogCode.Accepted:
                selected_indices = [list_widget.row(item) for item in list_widget.selectedItems()]
                
                if len(selected_indices) < 2 or len(selected_indices) > 3:
                    QMessageBox.warning(self, "Invalid Selection", 
                                      "Please select 2 or 3 datasets.")
                    return
                
                selected_datasets = [all_datasets[i] for i in selected_indices]
            else:
                return
        else:
            selected_datasets = all_datasets[:3] if len(all_datasets) == 3 else all_datasets
        
        try:
            dialog = VennDiagramDialog(selected_datasets, self)
            dialog.exec()
        except Exception as e:
            self.logger.error(f"Failed to create Venn diagram: {e}")
            QMessageBox.critical(self, "Venn Diagram Error",
                               f"Failed to create Venn diagram:\n{str(e)}")

    def _on_da_peak_overlap(self):
        """ATAC-seq DA 데이터셋 간 peak_id(좌표) 기반 overlap 분석.

        2-3개 → Venn Diagram(peak_id 키), 4개 이상 → UpSet Plot.
        전제: 비교 대상 데이터셋들이 같은 consensus peak set에서 나와야 유효함.
        """
        atac_datasets = [
            ds for ds in self.presenter.datasets.values()
            if ds.dataset_type == DatasetType.ATAC_SEQ
        ]

        if len(atac_datasets) < 2:
            QMessageBox.warning(
                self, "Insufficient Datasets",
                "DA Peak Overlap 분석에는 ATAC-seq 데이터셋이 2개 이상 필요합니다.\n"
                "(현재 로드된 ATAC-seq 데이터셋: "
                f"{len(atac_datasets)}개)"
            )
            return

        from PyQt6.QtWidgets import QDialog, QListWidget, QDialogButtonBox

        select_dialog = QDialog(self)
        select_dialog.setWindowTitle("Select ATAC-seq Datasets for Peak Overlap")
        select_dialog.setMinimumWidth(420)

        layout = QVBoxLayout(select_dialog)
        layout.addWidget(QLabel(
            "비교할 ATAC-seq 데이터셋을 2개 이상 선택하세요.\n"
            "(같은 peak set/consensus peak에서 나온 결과여야 비교가 유효합니다)"
        ))

        list_widget = QListWidget()
        list_widget.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        for ds in atac_datasets:
            list_widget.addItem(ds.name)
        for i in range(list_widget.count()):
            list_widget.item(i).setSelected(True)
        layout.addWidget(list_widget)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(select_dialog.accept)
        buttons.rejected.connect(select_dialog.reject)
        layout.addWidget(buttons)

        if select_dialog.exec() != QDialog.DialogCode.Accepted:
            return

        selected_indices = [list_widget.row(item) for item in list_widget.selectedItems()]
        if len(selected_indices) < 2:
            QMessageBox.warning(self, "Invalid Selection", "2개 이상의 데이터셋을 선택하세요.")
            return

        selected_datasets = [atac_datasets[i] for i in selected_indices]

        try:
            if len(selected_datasets) <= 3:
                dialog = VennDiagramDialog(selected_datasets, self)
            else:
                dialog = UpsetPlotDialog(selected_datasets, self)
            dialog.exec()
        except Exception as e:
            self.logger.error(f"Failed to create DA peak overlap plot: {e}")
            QMessageBox.critical(self, "DA Peak Overlap Error",
                               f"Failed to create overlap plot:\n{str(e)}")

    def _create_venn_from_comparison_sheet(self):
        """Comparison sheet에서 Venn diagram 생성"""
        try:
            # 현재 테이블에서 데이터 가져오기
            current_table = self.data_tabs.currentWidget()
            if not current_table:
                QMessageBox.warning(self, "No Data", "No comparison data available.")
                return
            
            # 테이블 데이터를 DataFrame으로 변환
            row_count = current_table.rowCount()
            col_count = current_table.columnCount()
            
            if row_count == 0:
                QMessageBox.warning(self, "No Data", "Comparison sheet is empty.")
                return
            
            # 헤더 읽기
            headers = []
            for col in range(col_count):
                header_item = current_table.horizontalHeaderItem(col)
                if header_item:
                    headers.append(header_item.text())
                else:
                    headers.append(f"Column_{col}")
            
            # 데이터 읽기
            data = []
            for row in range(row_count):
                row_data = []
                for col in range(col_count):
                    item = current_table.item(row, col)
                    if item:
                        text = item.text()
                        # 숫자 변환 시도
                        try:
                            # nan 체크
                            if text.lower() == 'nan' or text == '':
                                row_data.append(None)
                            else:
                                row_data.append(float(text))
                        except ValueError:
                            row_data.append(text)
                    else:
                        row_data.append(None)
                data.append(row_data)
            
            # DataFrame 생성
            comparison_df = pd.DataFrame(data, columns=headers)
            
            # Venn dialog 생성
            dialog = VennDiagramFromComparisonDialog(comparison_df, self)
            dialog.exec()
            
        except Exception as e:
            self.logger.error(f"Failed to create Venn diagram from comparison sheet: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", 
                               f"Failed to create Venn diagram:\n{str(e)}")
    
    def _handle_table_key_press(self, event, table):
        """테이블에서 Ctrl+C (복사) 및 Ctrl+V (붙여넣기) 처리"""
        from PyQt6.QtGui import QKeyEvent, QClipboard
        from PyQt6.QtCore import Qt
        
        # Ctrl+C: 복사
        if event.key() == Qt.Key.Key_C and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            self._copy_selection(table)
        # Ctrl+V: 붙여넣기
        elif event.key() == Qt.Key.Key_V and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            self._paste_selection(table)
        else:
            # 기본 동작 수행
            QTableWidget.keyPressEvent(table, event)
    
    def _copy_selection(self, table):
        """선택된 셀들을 클립보드에 복사 (Excel 형식)"""
        selection = table.selectedRanges()
        if not selection:
            return
        
        # 선택된 영역의 모든 셀 데이터 수집
        copied_data = []
        for sel_range in selection:
            for row in range(sel_range.topRow(), sel_range.bottomRow() + 1):
                row_data = []
                for col in range(sel_range.leftColumn(), sel_range.rightColumn() + 1):
                    item = table.item(row, col)
                    row_data.append(item.text() if item else "")
                copied_data.append("\t".join(row_data))
        
        # 클립보드에 복사 (탭으로 열 구분, 줄바꿈으로 행 구분)
        clipboard_text = "\n".join(copied_data)
        from PyQt6.QtWidgets import QApplication
        QApplication.clipboard().setText(clipboard_text)
        
        self.logger.info(f"Copied {len(copied_data)} rows to clipboard")
    
    def _paste_selection(self, table):
        """클립보드 내용을 gene list 입력란에 붙여넣기"""
        from PyQt6.QtWidgets import QApplication
        
        clipboard_text = QApplication.clipboard().text()
        if not clipboard_text:
            return
        
        # Gene list로 추정되는 경우 filter panel의 gene list에 추가
        # 줄바꿈 또는 탭으로 구분된 텍스트
        genes = []
        for line in clipboard_text.split('\n'):
            # 탭으로 구분된 경우 첫 번째 열만 사용 (gene_id 또는 symbol)
            parts = line.strip().split('\t')
            if parts and parts[0]:
                genes.append(parts[0])
        
        if genes:
            # FilterPanel의 gene list에 추가
            current_text = self.filter_panel.gene_input.toPlainText()
            if current_text:
                new_text = current_text + '\n' + '\n'.join(genes)
            else:
                new_text = '\n'.join(genes)
            
            self.filter_panel.gene_input.setPlainText(new_text)
            self.logger.info(f"Pasted {len(genes)} genes to filter panel")
            QMessageBox.information(self, "Paste Complete", 
                                  f"{len(genes)} genes pasted to Gene List input")
    
    def _load_recent_files(self):
        """최근 파일 히스토리 로드"""
        try:
            import json
            import os
            config_path = os.path.join(os.path.expanduser("~"), ".rna_seq_viewer_recent.json")
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    self.recent_files = json.load(f)
                    # 최대 개수 제한
                    self.recent_files = self.recent_files[:self.max_recent_files]
        except Exception as e:
            self.logger.warning(f"Failed to load recent files: {e}")
            self.recent_files = []
    
    def _save_recent_files(self):
        """최근 파일 히스토리 저장"""
        try:
            import json
            import os
            config_path = os.path.join(os.path.expanduser("~"), ".rna_seq_viewer_recent.json")
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(self.recent_files, f, indent=2)
        except Exception as e:
            self.logger.warning(f"Failed to save recent files: {e}")
    
    def _add_recent_file(self, file_path):
        """최근 파일에 추가"""
        import os
        # 절대 경로로 변환
        file_path = os.path.abspath(file_path)
        
        # 이미 있으면 제거
        if file_path in self.recent_files:
            self.recent_files.remove(file_path)
        
        # 맨 앞에 추가
        self.recent_files.insert(0, file_path)
        
        # 최대 개수 제한
        self.recent_files = self.recent_files[:self.max_recent_files]
        
        # 저장 및 메뉴 업데이트
        self._save_recent_files()
        self._update_recent_files_menu()
    
    def _update_recent_files_menu(self):
        """최근 파일 메뉴 업데이트"""
        self.recent_menu.clear()
        
        if not self.recent_files:
            action = QAction("(No recent files)", self)
            action.setEnabled(False)
            self.recent_menu.addAction(action)
        else:
            import os
            for i, file_path in enumerate(self.recent_files):
                # 경로의 마지막 2-3 레벨 표시
                path_parts = file_path.replace('\\', '/').split('/')
                if len(path_parts) >= 3:
                    # 마지막 3개 레벨 표시: parent_dir/sub_dir/filename.xlsx
                    display_name = '/'.join(path_parts[-3:])
                elif len(path_parts) >= 2:
                    # 마지막 2개 레벨 표시: dir/filename.xlsx
                    display_name = '/'.join(path_parts[-2:])
                else:
                    # 파일명만
                    display_name = os.path.basename(file_path)
                
                action = QAction(f"{i+1}. {display_name}", self)
                action.setToolTip(file_path)  # 전체 경로는 툴팁으로
                action.triggered.connect(lambda checked, path=file_path: self._open_recent_file(path))
                self.recent_menu.addAction(action)
            
            # Clear 옵션 추가
            self.recent_menu.addSeparator()
            clear_action = QAction("Clear Recent Files", self)
            clear_action.triggered.connect(self._clear_recent_files)
            self.recent_menu.addAction(clear_action)
    
    def _open_recent_file(self, file_path):
        """최근 파일 열기"""
        import os
        if not os.path.exists(file_path):
            QMessageBox.warning(self, "File Not Found", 
                              f"The file no longer exists:\n{file_path}")
            # 목록에서 제거
            self.recent_files.remove(file_path)
            self._save_recent_files()
            self._update_recent_files_menu()
            return
        
        # 파일 열기 (이름 지정 과정 포함)
        self._load_dataset_with_name(file_path)
    
    def _clear_recent_files(self):
        """최근 파일 히스토리 지우기"""
        reply = QMessageBox.question(self, "Clear Recent Files", 
                                     "Are you sure you want to clear the recent files list?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.recent_files = []
            self._save_recent_files()
            self._update_recent_files_menu()

    # ── Project Save / Load ──────────────────────────────────────────

    def _load_recent_projects(self):
        """최근 프로젝트 히스토리 로드"""
        try:
            import json
            import os
            config_path = os.path.join(os.path.expanduser("~"), ".rna_seq_viewer_recent_projects.json")
            if os.path.exists(config_path):
                with open(config_path, "r", encoding="utf-8") as f:
                    self.recent_projects = json.load(f)
                    self.recent_projects = self.recent_projects[:self.max_recent_files]
        except Exception as e:
            self.logger.warning(f"Failed to load recent projects: {e}")
            self.recent_projects = []

    def _save_recent_projects(self):
        """최근 프로젝트 히스토리 저장"""
        try:
            import json
            import os
            config_path = os.path.join(os.path.expanduser("~"), ".rna_seq_viewer_recent_projects.json")
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(self.recent_projects, f, indent=2)
        except Exception as e:
            self.logger.warning(f"Failed to save recent projects: {e}")

    def _add_recent_project(self, project_path: str):
        """최근 프로젝트 목록에 추가"""
        import os
        project_path = os.path.abspath(project_path)
        if project_path in self.recent_projects:
            self.recent_projects.remove(project_path)
        self.recent_projects.insert(0, project_path)
        self.recent_projects = self.recent_projects[:self.max_recent_files]
        self._save_recent_projects()
        self._update_recent_projects_menu()

    def _update_recent_projects_menu(self):
        """최근 프로젝트 메뉴 업데이트"""
        import os
        self.recent_projects_menu.clear()
        if not self.recent_projects:
            action = QAction("(No recent projects)", self)
            action.setEnabled(False)
            self.recent_projects_menu.addAction(action)
        else:
            for i, proj_path in enumerate(self.recent_projects):
                display = os.path.basename(proj_path)
                action = QAction(f"{i+1}. {display}", self)
                action.setToolTip(proj_path)
                action.triggered.connect(lambda checked, p=proj_path: self._open_project_path(p))
                self.recent_projects_menu.addAction(action)
            self.recent_projects_menu.addSeparator()
            clear_action = QAction("Clear Recent Projects", self)
            clear_action.triggered.connect(lambda: self._clear_recent_projects())
            self.recent_projects_menu.addAction(clear_action)

    def _clear_recent_projects(self):
        """최근 프로젝트 목록 지우기"""
        reply = QMessageBox.question(
            self, "Clear Recent Projects",
            "Are you sure you want to clear the recent projects list?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.recent_projects = []
            self._save_recent_projects()
            self._update_recent_projects_menu()

    def _on_save_project(self):
        """현재 분석 세션을 .seqproj 파일로 저장"""
        import os
        from utils.project_io import ProjectIO

        # 저장할 탭이 없으면 알림
        if not self.tab_data:
            QMessageBox.information(self, "Save Project", "There are no datasets to save.")
            return

        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Project",
            os.path.expanduser("~"),
            "SeqViewer Project (*.seqproj);;All Files (*)",
        )
        if not path:
            return
        if not path.endswith(".seqproj"):
            path += ".seqproj"

        try:
            # 데이터셋 파일 경로 / 타입 맵 구성
            dataset_file_map: dict = {}
            dataset_type_map: dict = {}
            dataset_source_map: dict = {}  # "file" or "database"
            dataset_db_id_map: dict = {}   # db_dataset_id (database source 전용)
            for name, ds in self.presenter.datasets.items():
                fp = getattr(ds, "file_path", None) or ""
                dataset_file_map[name] = str(fp)
                dt = getattr(ds, "dataset_type", None)
                dataset_type_map[name] = dt.value if dt else ""
                db_id = ds.metadata.get("db_dataset_id", "") if hasattr(ds, "metadata") else ""
                if db_id:
                    dataset_source_map[name] = "database"
                    dataset_db_id_map[name] = db_id
                else:
                    dataset_source_map[name] = "file"

            # 트리에서 펼쳐진 루트 항목 수집
            tree_expanded: list = []
            if hasattr(self, "dataset_manager"):
                root = self.dataset_manager.dataset_tree.invisibleRootItem()
                for i in range(root.childCount()):
                    item = root.child(i)
                    if item.isExpanded():
                        tree_expanded.append(item.text(0))

            spec = ProjectIO.build_spec(
                tab_data=self.tab_data,
                dataset_file_map=dataset_file_map,
                dataset_type_map=dataset_type_map,
                active_tab_index=self.data_tabs.currentIndex(),
                tree_expanded=tree_expanded,
                project_path=None,
            )
            # source / db_dataset_id 주입 + 파일 경로 상대화
            from pathlib import Path as _Path
            project_dir = _Path(path).parent
            for ds_spec in spec.get("datasets", []):
                ds_name = ds_spec.get("name", "")
                source = dataset_source_map.get(ds_name, "file")
                ds_spec["source"] = source
                if source == "database":
                    ds_spec["db_dataset_id"] = dataset_db_id_map.get(ds_name, "")
                    ds_spec["file_path"] = ""  # 파일 경로 불필요
                else:
                    fp = ds_spec.get("file_path", "")
                    if fp and os.path.isabs(fp):
                        try:
                            ds_spec["file_path"] = os.path.relpath(fp, start=project_dir)
                        except ValueError:
                            pass

            ProjectIO.save(path, spec)
            self._add_recent_project(path)
            self.logger.info(f"Project saved: {path}")
            QMessageBox.information(self, "Save Project", f"Project saved successfully:\n{path}")

        except Exception as e:
            self.logger.error(f"Failed to save project: {e}", exc_info=True)
            QMessageBox.critical(self, "Save Project Failed", f"Could not save project:\n{e}")

    def _on_open_project(self):
        """파일 대화상자로 .seqproj 프로젝트 열기"""
        import os
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Project",
            os.path.expanduser("~"),
            "SeqViewer Project (*.seqproj);;All Files (*)",
        )
        if path:
            self._open_project_path(path)

    def _open_project_path(self, path: str):
        """지정된 .seqproj 경로의 프로젝트 복원"""
        import os
        from utils.project_io import ProjectIO
        from models.data_models import FilterCriteria, FilterMode

        if not os.path.exists(path):
            QMessageBox.warning(self, "File Not Found", f"Project file not found:\n{path}")
            if path in self.recent_projects:
                self.recent_projects.remove(path)
                self._save_recent_projects()
                self._update_recent_projects_menu()
            return

        try:
            spec = ProjectIO.load(path)
        except Exception as e:
            QMessageBox.critical(self, "Open Project Failed", f"Could not read project file:\n{e}")
            return

        missing_files: list = []
        loaded_count = 0

        for ds_spec in spec.get("datasets", []):
            ds_name = ds_spec.get("name", "")
            ds_file = ds_spec.get("file_path", "")
            ds_type = ds_spec.get("type", "")
            source = ds_spec.get("source", "file")
            sheets = ds_spec.get("sheets", [])
            loaded_ds_name = ds_name  # 실제 presenter.datasets 키 (unique_name 적용 시 갱신)

            # ── 데이터베이스 소스 ──
            if source == "database":
                db_id = ds_spec.get("db_dataset_id", "")
                try:
                    dataset = self.db_manager.load_dataset(db_id or ds_name)
                    if dataset is None:
                        raise ValueError(f"Not found in database: {db_id or ds_name}")
                    unique_name = self.dataset_manager._generate_unique_name(ds_name)
                    dataset.name = unique_name
                    dataset.metadata['db_dataset_id'] = db_id
                    self.presenter.datasets[unique_name] = dataset
                    meta = {
                        'file_path': 'database',
                        'dataset_type': dataset.dataset_type.value,
                        'row_count': len(dataset.dataframe),
                        'column_count': len(dataset.dataframe.columns),
                    }
                    self.dataset_manager.add_dataset(unique_name, metadata=meta)
                    self.presenter.current_dataset = dataset
                    self.presenter._update_view_with_dataset(dataset, add_to_manager=False)
                    self._update_comparison_panel_datasets()
                    loaded_ds_name = unique_name  # DB는 unique_name으로 저장됨
                    loaded_count += 1
                except Exception as e:
                    self.logger.warning(f"Failed to load DB dataset '{ds_name}': {e}")
                    missing_files.append(ds_name)
                    continue

            # ── 파일 소스 ──
            else:
                # 파일 경로가 없거나 존재하지 않으면 DB에서 이름으로 fallback 시도
                if not ds_file or not os.path.exists(ds_file):
                    db_meta = next(
                        (m for m in self.db_manager.get_all_metadata() if m.alias == ds_name),
                        None,
                    )
                    if db_meta:
                        # DB fallback 성공 → database 소스로 처리
                        try:
                            dataset = self.db_manager.load_dataset(db_meta.dataset_id)
                            if dataset is None:
                                raise ValueError(f"DB load returned None for {db_meta.dataset_id}")
                            unique_name = self.dataset_manager._generate_unique_name(ds_name)
                            dataset.name = unique_name
                            dataset.metadata['db_dataset_id'] = db_meta.dataset_id
                            self.presenter.datasets[unique_name] = dataset
                            meta = {
                                'file_path': 'database',
                                'dataset_type': dataset.dataset_type.value,
                                'row_count': len(dataset.dataframe),
                                'column_count': len(dataset.dataframe.columns),
                            }
                            self.dataset_manager.add_dataset(unique_name, metadata=meta)
                            self.presenter.current_dataset = dataset
                            self.presenter._update_view_with_dataset(dataset, add_to_manager=False)
                            self._update_comparison_panel_datasets()
                            loaded_ds_name = unique_name  # DB fallback도 unique_name 사용
                            loaded_count += 1
                        except Exception as e:
                            self.logger.warning(f"DB fallback failed for '{ds_name}': {e}")
                            missing_files.append(ds_name)
                            continue
                    else:
                        missing_files.append(ds_file or ds_name)
                        continue
                else:
                    try:
                        self.presenter.load_dataset(
                            Path(ds_file),
                            custom_name=ds_name if ds_name else None,
                        )
                        loaded_count += 1
                    except Exception as e:
                        self.logger.warning(f"Failed to load dataset '{ds_name}': {e}")
                        missing_files.append(ds_file)
                        continue

            # sheets 재현 (filtered + plot)
            for sheet in sheets:
                stype = sheet.get("type")

                if stype == "filtered":
                    fp_dict = sheet.get("filter_params")
                    if not fp_dict:
                        continue
                    try:
                        criteria = FilterCriteria.from_dict(fp_dict)
                        self.presenter.switch_dataset(loaded_ds_name)
                        self.presenter.apply_filter(criteria)
                    except Exception as e:
                        self.logger.warning(f"Failed to replay filter for sheet '{sheet.get('label')}': {e}")

                elif stype == "plot":
                    plot_type = sheet.get("plot_type", "")
                    plot_params = sheet.get("plot_params") or {}
                    label_str = sheet.get("label", "Plot")
                    try:
                        target_ds = self.presenter.datasets.get(loaded_ds_name)
                        if target_ds is None:
                            raise ValueError(f"Dataset '{loaded_ds_name}' not found")
                        df = target_ds.dataframe
                        # Rename standardized columns to visualization names
                        from models.standard_columns import StandardColumns
                        _rename_map = {
                            StandardColumns.LOG2FC: 'log2FC',
                            StandardColumns.ADJ_PVALUE: 'padj',
                            StandardColumns.PVALUE: 'pvalue',
                        }
                        df = df.rename(columns=_rename_map)
                        if plot_type == "volcano":
                            widget = VolcanoPlotWidget(
                                df, plot_params=plot_params,
                                show_pin_button=False, embed_settings=False
                            )
                            self._pin_plot_to_tab(widget, label_str, "volcano", plot_params, loaded_ds_name)
                        elif plot_type == "heatmap":
                            widget = HeatmapWidget(
                                df, plot_params=plot_params,
                                show_pin_button=False, embed_settings=False
                            )
                            self._pin_plot_to_tab(widget, label_str, "heatmap", plot_params, loaded_ds_name)
                    except Exception as e:
                        self.logger.warning(f"Failed to restore plot '{label_str}': {e}")

        # 마지막 활성 탭 복원
        ui_state = spec.get("ui_state", {})
        active_idx = ui_state.get("active_tab_index", 0)
        if 0 <= active_idx < self.data_tabs.count():
            self.data_tabs.setCurrentIndex(active_idx)

        self._add_recent_project(path)

        # 누락 파일 경고
        if missing_files:
            files_list = "\n".join(missing_files[:10])
            QMessageBox.warning(
                self,
                "Missing Files",
                f"The following files could not be found and were skipped:\n{files_list}",
            )

        msg = f"Project opened: {loaded_count} dataset(s) loaded."
        if missing_files:
            msg += f" {len(missing_files)} file(s) skipped."
        self.logger.info(msg)

    def _set_window_icon(self):
        """윈도우 아이콘 설정"""
        from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QFont
        from PyQt6.QtCore import Qt, QRect
        
        # 프로그래밍 방식으로 아이콘 생성 (DNA 이중나선 이미지)
        pixmap = QPixmap(64, 64)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 배경 원
        painter.setBrush(QColor(70, 130, 180))  # Steel Blue
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(2, 2, 60, 60)
        
        # DNA 심볼 그리기 (간단한 텍스트)
        painter.setPen(QColor(255, 255, 255))
        font = QFont("Arial", 28, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(QRect(0, 0, 64, 64), Qt.AlignmentFlag.AlignCenter, "🧬")
        
        painter.end()
        
        icon = QIcon(pixmap)
        self.setWindowIcon(icon)
    
    def closeEvent(self, event):
        """창 닫기 이벤트"""
        # 종료 확인 메시지
        reply = QMessageBox.question(
            self,
            "Confirm Exit",
            "Are you sure you want to exit?\n\nAll unsaved work will be lost.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No  # 기본값: No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            event.ignore()  # 종료 취소
            return
        
        # UI 설정 저장
        self._save_ui_settings()
        
        # Qt 로그 핸들러 제거 전에 마지막 로그 기록
        self.audit_logger.log_action("Application Closed")
        
        # Qt 로그 핸들러 제거 (atexit 에러 방지)
        try:
            root_logger = logging.getLogger()
            if self.qt_log_handler in root_logger.handlers:
                root_logger.removeHandler(self.qt_log_handler)
            self.qt_log_handler.close()
        except Exception:
            pass  # 이미 삭제된 경우 무시
        
        event.accept()
    
    # ==================== Database 기능 ====================
    
    def _on_open_database_browser(self):
        """Database Browser 열기"""
        from gui.database_browser import DatabaseBrowserDialog
        
        dialog = DatabaseBrowserDialog(self.db_manager, self)
        dialog.datasets_selected.connect(self._on_database_datasets_selected)
        dialog.exec()
    
    def _on_database_datasets_selected(self, dataset_ids: List[str]):
        """Database에서 선택된 데이터셋 로드"""
        if not dataset_ids:
            return
        
        try:
            # 다중 선택 시 확인 메시지
            if len(dataset_ids) > 1:
                reply = QMessageBox.question(
                    self,
                    "Load Multiple Datasets",
                    f"Load {len(dataset_ids)} datasets?\n\n"
                    "They will be added to the dataset manager.",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.Yes
                )
                
                if reply != QMessageBox.StandardButton.Yes:
                    return
            
            # 데이터셋 로드
            first_dataset = None
            for dataset_id in dataset_ids:
                dataset = self.db_manager.load_dataset(dataset_id)
                if dataset and dataset.dataframe is not None:
                    # 고유 이름 생성 및 추가
                    unique_name = self.dataset_manager._generate_unique_name(dataset.name)
                    dataset.name = unique_name
                    
                    # Presenter에 추가
                    self.presenter.datasets[unique_name] = dataset
                    dataset.metadata['db_dataset_id'] = dataset_id  # 프로젝트 저장/복원용
                    
                    # Dataset Manager에 추가 (metadata와 함께)
                    metadata = {
                        'file_path': 'database',
                        'dataset_type': dataset.dataset_type.value,
                        'row_count': len(dataset.dataframe),
                        'column_count': len(dataset.dataframe.columns)
                    }
                    self.dataset_manager.add_dataset(unique_name, metadata=metadata)
                    
                    # 첫 번째 데이터셋 기억
                    if first_dataset is None:
                        first_dataset = dataset
                    
                    self.logger.info(f"Loaded dataset from database: {dataset.name}")
            
            # 첫 번째 데이터셋을 현재 데이터셋으로 설정하고 GUI 업데이트
            if first_dataset:
                self.presenter.current_dataset = first_dataset
                
                # FSM 상태 전환 (현재 상태에 따라)
                current_state = self.presenter.fsm.current_state
                if current_state == State.IDLE:
                    # IDLE → LOADING_DATA → DATA_LOADED
                    self.presenter.fsm.trigger(Event.LOAD_DATA)
                    self.presenter.fsm.trigger(Event.DATA_LOAD_SUCCESS)
                elif current_state in [State.ERROR, State.FILTER_COMPLETE, State.ANALYSIS_COMPLETE]:
                    # ERROR/COMPLETE → IDLE → LOADING_DATA → DATA_LOADED
                    self.presenter.fsm.trigger(Event.RESET)
                    self.presenter.fsm.trigger(Event.LOAD_DATA)
                    self.presenter.fsm.trigger(Event.DATA_LOAD_SUCCESS)
                # DATA_LOADED 상태면 그대로 유지
                
                # 첫 번째 데이터셋의 basic 정보를 Whole Dataset에 표시 (add_to_manager=False로 중복 방지)
                self.presenter._update_view_with_dataset(first_dataset, add_to_manager=False)
                
                # Comparison panel 업데이트 (모든 데이터셋 표시)
                self._update_comparison_panel_datasets()
                
                # 시그널 발생
                self.presenter.dataset_loaded.emit(first_dataset.name, first_dataset)
            
            QMessageBox.information(
                self,
                "Load Complete",
                f"Successfully loaded {len(dataset_ids)} dataset(s) from database."
            )
            
        except Exception as e:
            self.logger.error(f"Failed to load datasets from database: {e}")
            QMessageBox.critical(
                self,
                "Load Error",
                f"Failed to load datasets from database:\n\n{str(e)}"
            )
    
    def _on_import_to_database(self):
        """현재 데이터셋을 데이터베이스로 임포트"""
        if not self.presenter.current_dataset:
            QMessageBox.warning(
                self,
                "No Dataset",
                "Please load a dataset first before importing to database."
            )
            return
        
        from gui.dataset_import_dialog import DatasetImportDialog
        
        dialog = DatasetImportDialog(
            self.presenter.current_dataset,
            self.db_manager,
            self
        )
        dialog.import_completed.connect(self._on_dataset_imported)
        dialog.exec()
    
    def _on_dataset_imported(self, dataset_id: str):
        """데이터셋 임포트 완료"""
        self.logger.info(f"Dataset imported to database: {dataset_id}")
        
        # 필요 시 추가 작업 수행
    
    # ========== GO/KEGG Analysis Handlers ==========
    
    def _on_open_go_kegg_results(self):
        """GO/KEGG 결과 파일 열기"""
        from PyQt6.QtWidgets import QFileDialog, QMessageBox, QInputDialog
        from pathlib import Path
        
        # 파일 형식 선택
        file_type, ok = QInputDialog.getItem(
            self,
            "Select File Type",
            "Select GO/KEGG file format:",
            ["Excel file (single file with multiple sheets)", 
             "CSV files (multiple files)"],
            0,
            False
        )
        
        if not ok:
            return
        
        is_excel = "Excel" in file_type
        
        if is_excel:
            # Excel 파일 선택
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "Open GO/KEGG Results (Excel)",
                "",
                "Excel Files (*.xlsx *.xls);;All Files (*)"
            )
            
            if not file_path:
                return
            
            file_paths = [Path(file_path)]
            default_name = Path(file_path).stem
            
        else:
            # 여러 CSV 파일 선택
            file_paths_str, _ = QFileDialog.getOpenFileNames(
                self,
                "Open GO/KEGG Results (CSV files)",
                "",
                "CSV Files (*.csv);;All Files (*)"
            )
            
            if not file_paths_str:
                return
            
            file_paths = [Path(fp) for fp in file_paths_str]
            default_name = "GO/KEGG Analysis"
        
        # 데이터셋 이름 입력
        dataset_name, ok = QInputDialog.getText(
            self,
            "Dataset Name",
            "Enter a name for this GO/KEGG dataset:",
            QLineEdit.EchoMode.Normal,
            default_name
        )
        
        if not ok or not dataset_name.strip():
            dataset_name = default_name
        
        try:
            # Presenter를 통해 로딩
            self.presenter.load_go_kegg_data(
                file_paths=file_paths,
                is_excel=is_excel,
                dataset_name=dataset_name.strip()
            )
            
            self.logger.info(f"GO/KEGG data loading initiated: {len(file_paths)} file(s)")
            
        except Exception as e:
            self.logger.error(f"Failed to load GO/KEGG data: {e}", exc_info=True)
            QMessageBox.critical(
                self,
                "Load Error",
                f"Failed to load GO/KEGG data:\n{str(e)}"
            )
    
    def _on_cluster_go_terms(self):
        """GO Term 클러스터링 다이얼로그 열기 (Filtered 탭에서만 가능)"""
        from PyQt6.QtWidgets import QMessageBox
        from models.data_models import DatasetType
        
        # 현재 데이터셋 확인
        if self.presenter.current_dataset is None:
            QMessageBox.warning(
                self,
                "No Dataset",
                "Please load a GO/KEGG dataset first."
            )
            return
        
        if self.presenter.current_dataset.dataset_type != DatasetType.GO_ANALYSIS:
            QMessageBox.warning(
                self,
                "Invalid Dataset",
                "Clustering is only available for GO/KEGG datasets.\n"
                "Please load GO/KEGG results first."
            )
            return
        
        # 현재 선택된 탭 확인 - Filtered 탭만 허용
        current_tab_index = self.data_tabs.currentIndex()
        current_tab_name = self.data_tabs.tabText(current_tab_index)
        
        if not current_tab_name.startswith("Filtered:"):
            QMessageBox.information(
                self,
                "Use Filtered Data",
                "Clustering should be performed on filtered data.\n\n"
                "Please:\n"
                "1. Go to 'Statistical Filter' tab\n"
                "2. Set FDR, Ontology, and Direction filters\n"
                "3. Click 'Apply Filter'\n"
                "4. Select the generated 'Filtered:' tab\n"
                "5. Then try clustering again"
            )
            return
        
        # 현재 탭의 데이터 가져오기 (tab_data에서 직접)
        if current_tab_index not in self.tab_data:
            QMessageBox.warning(
                self,
                "No Data",
                "No data available in current tab."
            )
            return
        
        # tab_data에서 DataFrame과 Dataset 가져오기
        dataframe = self.tab_data[current_tab_index]['dataframe']
        dataset = self.tab_data[current_tab_index]['dataset']
        
        if dataframe is None or dataframe.empty:
            QMessageBox.warning(
                self,
                "No Data",
                "Current tab has no data."
            )
            return
        
        # 임시 Dataset 생성 (filtered 데이터로)
        from models.data_models import Dataset
        filtered_dataset = Dataset(
            name=current_tab_name,
            dataset_type=DatasetType.GO_ANALYSIS,
            dataframe=dataframe.copy(),
            original_columns={},
            metadata=self.presenter.current_dataset.metadata if self.presenter.current_dataset else {}
        )
        
        # 클러스터링 설정 다이얼로그
        from gui.go_clustering_dialog import GOClusteringDialog
        
        dialog = GOClusteringDialog(filtered_dataset, self)
        
        # Connect signal to handle clustered data
        def _on_clustered_data_ready(clustered_data: pd.DataFrame):
            """Handle clustered data from dialog"""
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Main window received clustered data: {len(clustered_data)} rows")
            logger.info(f"Clustered data columns: {clustered_data.columns.tolist()}")
            
            # 새로운 데이터셋 생성하여 표시
            from models.data_models import Dataset, DatasetType
            from models.standard_columns import StandardColumns
            
            # cluster_id 열을 가장 왼쪽으로 이동
            if StandardColumns.CLUSTER_ID in clustered_data.columns:
                # 열 순서 재배치: cluster_id를 맨 앞으로
                cols = clustered_data.columns.tolist()
                cols.remove(StandardColumns.CLUSTER_ID)
                cols.insert(0, StandardColumns.CLUSTER_ID)
                clustered_data = clustered_data[cols]
                logger.info(f"Moved cluster_id to first column")
            
            dataset_name = f"Clustered: {filtered_dataset.name}"
            clustered_dataset = Dataset(
                name=dataset_name,
                dataset_type=DatasetType.GO_ANALYSIS,
                dataframe=clustered_data,
                original_columns={},
                metadata=filtered_dataset.metadata
            )
            
            logger.info(f"Created clustered dataset: {dataset_name}")
            
            # 새 탭 생성 및 데이터 표시
            table = self._create_data_tab(dataset_name, sheet_type='clustered')
            self.populate_table(table, clustered_data, clustered_dataset)
            
            # 탭 데이터 저장
            tab_index = self.data_tabs.count() - 1  # 방금 추가한 탭
            if tab_index in self.tab_data:
                self.tab_data[tab_index]['dataframe'] = clustered_data
                self.tab_data[tab_index]['dataset'] = clustered_dataset
                self.tab_data[tab_index]['sheet_type'] = 'clustered'
            else:
                self.tab_data[tab_index] = {
                    'dataframe': clustered_data,
                    'dataset': clustered_dataset,
                    'parent_dataset': None,
                    'sheet_type': 'clustered',
                    'sheet_label': 'Clustered',
                    'filter_params': None,
                    'comparison_params': None,
                }
            
            # 새 탭으로 전환 (이때 _on_tab_changed가 호출되어 current_dataset 업데이트)
            self.data_tabs.setCurrentIndex(tab_index)
            
            # 명시적으로 current_dataset 설정 (탭 전환 이벤트가 먼저 발생할 수 있음)
            self.presenter.current_dataset = clustered_dataset
            
            logger.info(f"Displayed clustered data in new tab (index {tab_index})")
        
        dialog.clustered_data_ready.connect(_on_clustered_data_ready)
        dialog.exec()
    
    def _on_filter_go_results(self):
        """GO/KEGG 결과 필터링 다이얼로그 열기"""
        from PyQt6.QtWidgets import QMessageBox
        from models.data_models import DatasetType
        
        # 현재 데이터셋 확인
        if self.presenter.current_dataset is None:
            QMessageBox.warning(
                self,
                "No Dataset",
                "Please load a GO/KEGG dataset first."
            )
            return
        
        if self.presenter.current_dataset.dataset_type != DatasetType.GO_ANALYSIS:
            QMessageBox.warning(
                self,
                "Invalid Dataset",
                "Filtering is only available for GO/KEGG datasets.\n"
                "Please load GO/KEGG results first."
            )
            return
        
        # GO/KEGG 필터링 다이얼로그
        from gui.go_filter_dialog import GOFilterDialog
        
        dialog = GOFilterDialog(self.presenter.current_dataset, self)
        dialog.exec()
    
    def _on_atac_visualization(self, plot_type: str):
        """ATAC-seq 전용 시각화"""
        from PyQt6.QtWidgets import QMessageBox
        from models.data_models import DatasetType, Dataset

        current_index = self.data_tabs.currentIndex()
        if current_index < 0 or current_index not in self.tab_data:
            QMessageBox.warning(self, "No Data", "Please load an ATAC-seq dataset first.")
            return

        dataframe = self.tab_data[current_index]['dataframe']
        dataset = self.tab_data[current_index]['dataset']
        if dataset is None or dataset.dataset_type != DatasetType.ATAC_SEQ:
            QMessageBox.warning(self, "Invalid Dataset",
                                "This visualization is only available for ATAC-seq datasets.")
            return

        # 현재 탭의 필터링된 dataframe 사용
        meta_copy = dict(dataset.metadata) if dataset.metadata else {}
        filtered_dataset = Dataset(
            name=dataset.name,
            dataset_type=dataset.dataset_type,
            dataframe=dataframe,
            original_columns=dataset.original_columns,
            metadata=meta_copy,
        )

        if plot_type == "genomic_distribution":
            from gui.genomic_distribution_dialog import GenomicDistributionDialog
            dialog = GenomicDistributionDialog(filtered_dataset, self)
            dialog.exec()
        elif plot_type == "tss_distance":
            from gui.tss_distance_dialog import TSSDistanceDialog
            dialog = TSSDistanceDialog(filtered_dataset, self)
            dialog.exec()
        elif plot_type == "ma_plot":
            from gui.ma_plot_dialog import MAPlotDialog
            dialog = MAPlotDialog(filtered_dataset, self)
            dialog.exec()

    def _on_motif_enrichment_requested(self):
        """TF Motif Enrichment Plot 요청 처리."""
        from models.data_models import DatasetType
        from gui.motif_enrichment_dialog import MotifEnrichmentDialog

        current_index = self.data_tabs.currentIndex()
        if current_index < 0 or current_index not in self.tab_data:
            return

        dataset = self.tab_data[current_index]['dataset']
        if dataset is None or dataset.dataset_type != DatasetType.MOTIF_ENRICHMENT:
            return

        # 같은 프로젝트 내에 두 번째 MOTIF_ENRICHMENT 데이터셋이 있으면 DOWN 후보로 제안
        motif_datasets = [
            ds for ds in self.presenter.datasets.values()
            if ds.dataset_type == DatasetType.MOTIF_ENRICHMENT and ds is not dataset
        ]
        dataset_down = None
        if motif_datasets:
            from PyQt6.QtWidgets import QInputDialog
            names = [ds.name for ds in motif_datasets]
            choice, ok = QInputDialog.getItem(
                self,
                "Compare with another dataset?",
                "Select a second motif dataset to compare (or Cancel for single view):",
                names, 0, False
            )
            if ok:
                dataset_down = next(ds for ds in motif_datasets if ds.name == choice)

        dialog = MotifEnrichmentDialog(dataset, dataset_down=dataset_down, parent=self)
        dialog.resize(1000, 650)
        dialog.exec()

    def _on_open_chromvar_results(self):
        """chromVAR diff_tf CSV 또는 parquet 열기."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open chromVAR Results", "",
            "chromVAR Files (*diff_tf*.csv *chromVAR*.parquet *.csv *.parquet);;All Files (*)"
        )
        if not file_path:
            return
        default_name = Path(file_path).stem
        dataset_name, ok = QInputDialog.getText(
            self, "Dataset Name", "Enter a name for this chromVAR dataset:",
            QLineEdit.EchoMode.Normal, default_name
        )
        if not ok:
            return
        name = dataset_name.strip() or default_name
        self._add_recent_file(file_path)
        self.presenter.load_dataset(Path(file_path), custom_name=name)

    def _on_chromvar_requested(self):
        """chromVAR TF Activity Plot 요청 처리."""
        from models.data_models import DatasetType
        from gui.chromvar_dialog import ChromVARDialog

        current_index = self.data_tabs.currentIndex()
        if current_index < 0 or current_index not in self.tab_data:
            return
        dataset = self.tab_data[current_index]['dataset']
        if dataset is None or dataset.dataset_type != DatasetType.CHROMVAR_DIFF_TF:
            return

        # 같은 프로젝트 내 다른 CHROMVAR_DIFF_TF 데이터셋을 extra로 제공
        extra = [
            ds for ds in self.presenter.datasets.values()
            if ds.dataset_type == DatasetType.CHROMVAR_DIFF_TF and ds is not dataset
        ]
        dialog = ChromVARDialog(dataset, extra_datasets=extra if extra else None, parent=self)
        dialog.resize(950, 720)
        dialog.exec()

    def _on_tf_footprint_requested(self):
        """TF Activity Plot (Footprint) 요청 처리."""
        from models.data_models import DatasetType
        from gui.tf_footprint_dialog import TFFootprintDialog

        current_index = self.data_tabs.currentIndex()
        if current_index < 0 or current_index not in self.tab_data:
            return

        dataset = self.tab_data[current_index]['dataset']
        if dataset is None or dataset.dataset_type != DatasetType.TF_FOOTPRINT:
            return

        dialog = TFFootprintDialog(dataset, parent=self)
        dialog.resize(900, 700)
        dialog.exec()

    # ------------------------------------------------------------------ #
    #  Multi-Omics handlers
    # ------------------------------------------------------------------ #

    def _on_filter_tab_changed(self, index: int):
        """FilterPanel 탭 전환 시 ComparisonPanel / 버튼 행 show/hide"""
        is_multi_omics = self.filter_panel.is_multi_omics_tab_active()
        self.comparison_panel.setVisible(not is_multi_omics)
        self.action_buttons_widget.setVisible(not is_multi_omics)
        if is_multi_omics:
            self.multi_omics_panel.refresh_dataset_list(self.presenter.datasets)

    def _on_show_multi_omics_panel(self):
        """Analysis > Integrate RNA + ATAC 메뉴 클릭 — RNA+ATAC 탭으로 전환"""
        self.filter_panel.switch_to_multi_omics_tab()
        self.multi_omics_panel.refresh_dataset_list(self.presenter.datasets)

    def _on_integrate_requested(
        self,
        rna_name: str,
        atac_name: str,
        method: str,
        tss_window: int,
        rna_padj: float,
        rna_lfc: float,
        atac_padj: float,
        atac_lfc: float,
    ):
        """MultiOmicsPanel의 integrate_requested 시그널 처리"""
        self.logger.info(
            f"Integration requested: RNA='{rna_name}' ATAC='{atac_name}' "
            f"method={method}"
        )
        self.presenter.integrate_datasets(
            rna_name=rna_name,
            atac_name=atac_name,
            method=method,
            tss_window=tss_window,
            rna_padj=rna_padj,
            rna_lfc=rna_lfc,
            atac_padj=atac_padj,
            atac_lfc=atac_lfc,
        )

    def _on_multi_omics_visualization(self, plot_type: str):
        """Multi-Omics 전용 시각화"""
        current_index = self.data_tabs.currentIndex()
        if current_index < 0 or current_index not in self.tab_data:
            QMessageBox.warning(self, "No Data",
                                "Please run RNA + ATAC integration first.")
            return

        dataframe = self.tab_data[current_index]['dataframe']
        dataset = self.tab_data[current_index]['dataset']
        if dataset is None or dataset.dataset_type != DatasetType.MULTI_OMICS:
            QMessageBox.warning(
                self, "Invalid Dataset",
                "This visualization is only available for Multi-Omics integrated datasets."
            )
            return

        tab_name = self.data_tabs.tabText(current_index)

        if plot_type == "quadrant":
            from gui.quadrant_plot_dialog import QuadrantPlotDialog
            dialog = QuadrantPlotDialog(dataframe, title=tab_name, parent=self)
            dialog.exec()
        elif plot_type == "heatmap":
            from gui.concordance_heatmap_dialog import ConcordanceHeatmapDialog
            dialog = ConcordanceHeatmapDialog(dataframe, title=tab_name, parent=self)
            dialog.exec()
        elif plot_type == "summary":
            from gui.concordance_summary_dialog import ConcordanceSummaryDialog
            dialog = ConcordanceSummaryDialog(dataframe, title=tab_name, parent=self)
            dialog.exec()
        elif plot_type == "integrated_volcano":
            from gui.integrated_volcano_dialog import IntegratedVolcanoDialog
            dialog = IntegratedVolcanoDialog(dataframe, title=tab_name, parent=self)
            dialog.exec()

    def _on_export_multi_omics(self):
        """Multi-Omics 결과를 다중 시트 Excel로 내보내기"""
        current_index = self.data_tabs.currentIndex()
        if current_index < 0 or current_index not in self.tab_data:
            return

        dataframe = self.tab_data[current_index]['dataframe']
        dataset = self.tab_data[current_index]['dataset']
        if dataset is None or dataset.dataset_type != DatasetType.MULTI_OMICS:
            QMessageBox.warning(self, "Invalid Dataset",
                                "Please select a Multi-Omics integrated tab first.")
            return

        path, _ = QFileDialog.getSaveFileName(
            self, "Export Multi-Omics Results",
            f"{dataset.name}_integrated.xlsx",
            "Excel (*.xlsx)",
        )
        if path:
            self.presenter.export_multi_omics_excel(dataframe, path)
            self.logger.info(f"Multi-omics Excel saved: {path}")

    def _on_go_visualization(self, plot_type: str):
        """GO/KEGG 시각화"""
        from PyQt6.QtWidgets import QMessageBox
        from models.data_models import DatasetType

        # 현재 탭 확인
        current_index = self.data_tabs.currentIndex()
        if current_index < 0:
            QMessageBox.warning(self, "No Data", 
                              "Please load a GO/KEGG dataset first.")
            return
        
        # 현재 탭의 데이터 가져오기
        if current_index not in self.tab_data:
            QMessageBox.warning(self, "No Data", 
                              "No data available in current tab.")
            return
        
        dataframe = self.tab_data[current_index]['dataframe']
        dataset = self.tab_data[current_index]['dataset']
        
        # GO/KEGG 데이터셋인지 확인
        if dataset and dataset.dataset_type != DatasetType.GO_ANALYSIS:
            QMessageBox.warning(
                self,
                "Invalid Dataset",
                "GO/KEGG visualization is only available for GO/KEGG datasets.\n"
                "Please load GO/KEGG results first."
            )
            return
        
        # 현재 탭의 필터링된 데이터를 반영하기 위해 dataset의 dataframe을 업데이트
        if dataset:
            from models.data_models import Dataset
            # metadata를 사본(섯할로 복사)하여 원본 dict 변이 방지
            meta_copy = dict(dataset.metadata)
            filtered_dataset = Dataset(
                name=dataset.name,
                dataset_type=dataset.dataset_type,
                dataframe=dataframe,  # 현재 탭의 필터링된 dataframe 사용
                original_columns=dataset.original_columns,
                metadata=meta_copy
            )
            dataset = filtered_dataset
        
        # Network Chart는 Clustered 탭에서만 가능
        if plot_type == "network":
            current_tab_name = self.data_tabs.tabText(current_index)
            if not current_tab_name.startswith("Clustered:"):
                QMessageBox.information(
                    self,
                    "Use Clustered Data",
                    "Network Chart should be used with clustered data for better performance.\n\n"
                    "Please:\n"
                    "1. Filter your GO/KEGG data (Statistical Filter tab)\n"
                    "2. Select the 'Filtered:' tab\n"
                    "3. Run 'GO Analysis → Cluster GO Terms'\n"
                    "4. Select the generated 'Clustered:' tab\n"
                    "5. Then open Network Chart\n\n"
                    "This shows cluster-level relationships instead of all term-to-term connections,\n"
                    "greatly reducing computational load."
                )
                return
        
        try:
            # 시각화 다이얼로그 열기
            if plot_type == "dotplot":
                # GO Term Comparison 탭인 경우 Comparison Dot Plot
                is_comparison = (
                    dataset is not None
                    and isinstance(getattr(dataset, 'metadata', None), dict)
                    and dataset.metadata.get('is_go_comparison', False)
                )
                if is_comparison:
                    from gui.go_comparison_dot_plot_dialog import GOComparisonDotPlotDialog
                    dialog = GOComparisonDotPlotDialog(dataset, self)
                else:
                    from gui.go_dot_plot_dialog import GODotPlotDialog
                    dialog = GODotPlotDialog(dataset, self)
                dialog.exec()
                
            elif plot_type == "barplot":
                from gui.go_bar_chart_dialog import GOBarChartDialog
                dialog = GOBarChartDialog(dataset, self)
                dialog.exec()
                
            elif plot_type == "network":
                from gui.go_network_dialog import GONetworkDialog
                dialog = GONetworkDialog(dataset, self)
                dialog.exec()
            
            self.logger.info(f"GO/KEGG visualization opened: {plot_type}")
            
        except Exception as e:
            self.logger.error(f"GO/KEGG visualization failed: {e}", exc_info=True)
            QMessageBox.critical(
                self,
                "Visualization Error",
                f"Failed to create GO/KEGG visualization:\n{str(e)}"
            )
    
    def _on_filter_completed(self, filtered_df: pd.DataFrame, tab_name: str):
        """필터링/클러스터링 완료 시 새 탭에 결과 표시"""
        try:
            # 데이터셋 생성 - 현재 활성 데이터셋의 타입을 유지
            from models.data_models import Dataset, DatasetType
            current_dataset = self.presenter.current_dataset
            _par = current_dataset.name if current_dataset else None

            # 덮어쓰기 대상: "같은 부모 데이터셋"에서 나온 동일 이름의 필터 탭만.
            # (다른 데이터셋에 같은 필터를 적용한 결과는 이름이 같아도 보존한다)
            existing_indices = []
            for i in range(self.data_tabs.count()):
                if self.data_tabs.tabText(i) != tab_name:
                    continue
                entry = self.tab_data.get(i)
                if entry is not None and entry.get('parent_dataset') == _par:
                    existing_indices.append(i)

            # 기존 동일 이름 탭 제거 (역순 처리 + tab_data 재정렬)
            if existing_indices:
                for idx in reversed(existing_indices):
                    self._remove_tab_safely(idx)

            # 새 탭 생성
            table = self._create_data_tab(tab_name, sheet_type='filtered',
                                          parent_dataset=_par)
            new_tab_index = self.data_tabs.indexOf(table)
            dataset_type = current_dataset.dataset_type if current_dataset else DatasetType.GO_ANALYSIS
            
            dataset = Dataset(
                name=tab_name,
                dataset_type=dataset_type,  # 현재 dataset type 유지
                dataframe=filtered_df,
                original_columns={},
                metadata=current_dataset.metadata.copy() if current_dataset else {}
            )
            
            # 테이블에 데이터 채우기
            self.populate_table(table, filtered_df, dataset)

            # filter_params를 tab_data에 저장 (Project Save/Load용)
            criteria = getattr(self.presenter, "last_filter_criteria", None)
            if criteria is not None and new_tab_index in self.tab_data:
                self.tab_data[new_tab_index]["filter_params"] = criteria.to_dict()

            # 비교 패널 업데이트 (populate_table 이후에 한 번만)
            self._update_comparison_panel_datasets()
            
            # 탭 활성화
            self.data_tabs.setCurrentIndex(new_tab_index)
            
            self.logger.info(f"Filter completed: {tab_name} ({len(filtered_df)} rows)")
            
        except Exception as e:
            self.logger.error(f"Failed to create filtered tab: {e}", exc_info=True)
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to create filtered tab:\n{str(e)}"
            )
    
    def _on_presenter_error(self, error_message: str):
        """Presenter에서 오류 발생 시"""
        QMessageBox.critical(
            self,
            "Error",
            error_message
        )
    
    def _on_progress_updated(self, progress: int):
        """진행률 업데이트"""
        # 상태 바에 진행률 표시 (필요시 구현)
        pass
    
    def _save_ui_settings(self):
        """UI 설정 저장"""
        try:
            # 윈도우 크기와 위치
            self.settings.setValue("geometry", self.saveGeometry())
            self.settings.setValue("windowState", self.saveState())
            
            # Splitter 상태
            self.settings.setValue("mainSplitter", self.main_splitter.saveState())
            
            # 테이블 컬럼 너비 저장 (현재 활성 탭)
            current_index = self.data_tabs.currentIndex()
            if current_index >= 0:
                current_table = self.data_tabs.widget(current_index)
                if isinstance(current_table, QTableWidget):
                    col_count = current_table.columnCount()
                    col_widths = []
                    for col in range(col_count):
                        col_widths.append(current_table.columnWidth(col))
                    self.settings.setValue("tableColumnWidths", col_widths)
            
            self.logger.debug("UI settings saved")
        except Exception as e:
            self.logger.error(f"Failed to save UI settings: {e}")
    
    def _restore_ui_settings(self):
        """UI 설정 복원"""
        try:
            # 윈도우 크기와 위치
            geometry = self.settings.value("geometry")
            if geometry:
                self.restoreGeometry(geometry)
            
            window_state = self.settings.value("windowState")
            if window_state:
                self.restoreState(window_state)
            
            # Splitter 상태
            splitter_state = self.settings.value("mainSplitter")
            if splitter_state:
                self.main_splitter.restoreState(splitter_state)
            
            self.logger.debug("UI settings restored")
        except Exception as e:
            self.logger.error(f"Failed to restore UI settings: {e}")
    
    def _restore_table_column_widths(self, table: QTableWidget):
        """테이블 컬럼 너비 복원"""
        try:
            col_widths = self.settings.value("tableColumnWidths")
            if col_widths and isinstance(col_widths, list):
                col_count = min(table.columnCount(), len(col_widths))
                for col in range(col_count):
                    if col < len(col_widths):
                        # QSettings가 str로 저장할 수 있으므로 int로 변환
                        width = int(col_widths[col]) if col_widths[col] is not None else 100
                        table.setColumnWidth(col, width)
        except Exception as e:
            self.logger.error(f"Failed to restore column widths: {e}")
    
    def _show_table_context_menu(self, table: QTableWidget, pos):
        """
        테이블 셀 우클릭 시 컨텍스트 메뉴 표시
        Gene symbol/ID, GO term, KEGG pathway에 대한 외부 데이터베이스 링크 제공
        """
        from PyQt6.QtWidgets import QMenu
        from PyQt6.QtGui import QDesktopServices
        from PyQt6.QtCore import QUrl

        # 클릭된 셀 찾기
        item = table.itemAt(pos)
        if not item:
            return

        row = item.row()
        col = item.column()

        # 정렬 후에도 올바른 DataFrame 행을 찾기 위해 원본 인덱스를 UserRole에서 가져옴
        original_row = item.data(Qt.ItemDataRole.UserRole)
        if original_row is None:
            original_row = row  # populate_table이 호출되기 전 행일 경우 fallback

        # 컬럼 헤더 이름 가져오기
        header_item = table.horizontalHeaderItem(col)
        if not header_item:
            return

        column_name = header_item.text().lower()

        # 셀 값 가져오기
        cell_text = item.text().strip()

        # 컬럼 타입 감지
        is_gene_column = any(keyword in column_name for keyword in
                            ['gene_id', 'gene id', 'geneid', 'symbol', 'gene_symbol', 'gene symbol',
                             'nearest_gene', 'gene_name'])

        is_go_column = any(keyword in column_name for keyword in
                          ['term_id', 'termid', 'go_id', 'goid', 'go term'])

        is_kegg_column = any(keyword in column_name for keyword in
                            ['pathway_id', 'pathwayid', 'kegg_id', 'keggid', 'kegg pathway'])

        is_description_column = any(keyword in column_name for keyword in
                                   ['description', 'term_name', 'pathway_name', 'name'])

        # ATAC-seq 여부 — 현재 탭의 dataset 확인
        current_index = self.data_tabs.indexOf(table)
        if current_index < 0:
            current_index = self.data_tabs.currentIndex()
        is_atac_tab = False
        atac_dataset = None
        atac_dataframe = None
        if current_index in self.tab_data:
            _df = self.tab_data[current_index]['dataframe']
            _ds = self.tab_data[current_index]['dataset']
            if _ds and _ds.dataset_type == DatasetType.ATAC_SEQ:
                is_atac_tab = True
                coord_cols = {'chromosome', 'peak_start', 'peak_end'}
                if _df is not None and coord_cols.issubset(_df.columns):
                    atac_dataframe = _df
                    atac_dataset = _ds

        has_atac_coords = atac_dataframe is not None

        # 아무 것도 해당하지 않으면 메뉴 표시 안 함
        if not (is_gene_column or is_go_column or is_kegg_column or is_description_column
                or is_atac_tab):
            return

        # 빈 셀이고 ATAC 탭도 아닌 경우 표시 안 함
        if not cell_text and not is_atac_tab:
            return
        
        # 컨텍스트 메뉴 생성
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: white;
                border: 1px solid #cccccc;
            }
            QMenu::item {
                padding: 5px 20px;
            }
            QMenu::item:selected {
                background-color: #0078d4;
                color: white;
            }
        """)
        
        # Gene 컬럼인 경우
        if is_gene_column:
            self._add_gene_menu_items(menu, cell_text)
        
        # GO Term 컬럼인 경우
        elif is_go_column or (is_description_column and cell_text.startswith('GO:')):
            self._add_go_menu_items(menu, cell_text)
        
        # KEGG Pathway 컬럼인 경우
        elif is_kegg_column or (is_description_column and any(kw in cell_text.lower() for kw in ['pathway', 'kegg'])):
            self._add_kegg_menu_items(menu, cell_text)
        
        # Description 컬럼이지만 GO/KEGG가 아닌 경우 - 일반 검색만
        elif is_description_column:
            self._add_general_search_items(menu, cell_text)

        # ATAC-seq: IGV 이동 / Locus 복사
        if has_atac_coords:
            if menu.actions():
                menu.addSeparator()
            igv_action = menu.addAction("🔬 Send to IGV")
            igv_action.triggered.connect(
                lambda checked=False, r=original_row: self._send_peak_to_igv(atac_dataframe, atac_dataset, r))
            copy_action = menu.addAction("📋 Copy Locus")
            copy_action.triggered.connect(
                lambda checked=False, r=original_row: self._copy_locus(atac_dataframe, r))

        # 메뉴 표시
        if menu.actions():  # 메뉴 항목이 있을 때만 표시
            menu.exec(table.viewport().mapToGlobal(pos))
    
    def _add_gene_menu_items(self, menu, gene_text):
        """Gene 관련 메뉴 항목 추가"""
        from PyQt6.QtGui import QDesktopServices
        from PyQt6.QtCore import QUrl
        
        # NCBI Gene 검색
        ncbi_action = menu.addAction(f"🔍 Search '{gene_text}' in NCBI Gene")
        ncbi_action.triggered.connect(
            lambda: QDesktopServices.openUrl(
                QUrl(f"https://www.ncbi.nlm.nih.gov/gene/?term={gene_text}")
            )
        )
        
        # GeneCards 검색
        genecards_action = menu.addAction(f"🔍 Search '{gene_text}' in GeneCards")
        genecards_action.triggered.connect(
            lambda: QDesktopServices.openUrl(
                QUrl(f"https://www.genecards.org/cgi-bin/carddisp.pl?gene={gene_text}")
            )
        )
        
        # Ensembl 검색
        ensembl_action = menu.addAction(f"🔍 Search '{gene_text}' in Ensembl")
        ensembl_action.triggered.connect(
            lambda: QDesktopServices.openUrl(
                QUrl(f"https://www.ensembl.org/Multi/Search/Results?q={gene_text}")
            )
        )
        
        menu.addSeparator()
        
        # UniProt 검색 (단백질 정보)
        uniprot_action = menu.addAction(f"🔍 Search '{gene_text}' in UniProt")
        uniprot_action.triggered.connect(
            lambda: QDesktopServices.openUrl(
                QUrl(f"https://www.uniprot.org/uniprotkb?query={gene_text}")
            )
        )
        
        # Google Scholar 검색 (논문)
        scholar_action = menu.addAction(f"📚 Search '{gene_text}' in Google Scholar")
        scholar_action.triggered.connect(
            lambda: QDesktopServices.openUrl(
                QUrl(f"https://scholar.google.com/scholar?q={gene_text}")
            )
        )
    
    def _add_go_menu_items(self, menu, go_text):
        """GO Term 관련 메뉴 항목 추가"""
        from PyQt6.QtGui import QDesktopServices
        from PyQt6.QtCore import QUrl
        import re
        
        # GO ID 추출 (GO:0008150 형식)
        go_id_match = re.search(r'GO:\d+', go_text)
        go_id = go_id_match.group(0) if go_id_match else go_text
        
        # QuickGO (EBI)
        quickgo_action = menu.addAction(f"🔍 View '{go_id}' in QuickGO")
        quickgo_action.triggered.connect(
            lambda: QDesktopServices.openUrl(
                QUrl(f"https://www.ebi.ac.uk/QuickGO/term/{go_id}")
            )
        )
        
        # AmiGO (official GO browser)
        amigo_action = menu.addAction(f"🔍 View '{go_id}' in AmiGO")
        amigo_action.triggered.connect(
            lambda: QDesktopServices.openUrl(
                QUrl(f"http://amigo.geneontology.org/amigo/term/{go_id}")
            )
        )
        
        menu.addSeparator()
        
        # Gene Ontology (official site)
        go_action = menu.addAction(f"🔍 Search '{go_id}' in Gene Ontology")
        go_action.triggered.connect(
            lambda: QDesktopServices.openUrl(
                QUrl(f"http://geneontology.org/docs/ontology-documentation/")
            )
        )
        
        # NCBI Gene search with GO term
        ncbi_action = menu.addAction(f"🔍 Search genes with '{go_id}' in NCBI")
        ncbi_action.triggered.connect(
            lambda: QDesktopServices.openUrl(
                QUrl(f"https://www.ncbi.nlm.nih.gov/gene/?term={go_id}")
            )
        )
    
    def _add_kegg_menu_items(self, menu, kegg_text):
        """KEGG Pathway 관련 메뉴 항목 추가"""
        from PyQt6.QtGui import QDesktopServices
        from PyQt6.QtCore import QUrl
        import re
        
        # KEGG pathway ID 추출 (hsa04110, mmu04110 등)
        kegg_id_match = re.search(r'[a-z]{2,4}\d{5}', kegg_text)
        kegg_id = kegg_id_match.group(0) if kegg_id_match else kegg_text
        
        # KEGG Pathway 직접 링크
        pathway_action = menu.addAction(f"🔍 View '{kegg_id}' in KEGG Pathway")
        pathway_action.triggered.connect(
            lambda: QDesktopServices.openUrl(
                QUrl(f"https://www.genome.jp/pathway/{kegg_id}")
            )
        )
        
        # KEGG Pathway 검색
        search_action = menu.addAction(f"🔍 Search '{kegg_text}' in KEGG")
        search_action.triggered.connect(
            lambda: QDesktopServices.openUrl(
                QUrl(f"https://www.genome.jp/dbget-bin/www_bfind_sub?mode=bfind&max_hit=1000&dbkey=pathway&keywords={kegg_text}")
            )
        )
        
        menu.addSeparator()
        
        # Reactome (alternative pathway database)
        reactome_action = menu.addAction(f"🔍 Search '{kegg_text}' in Reactome")
        reactome_action.triggered.connect(
            lambda: QDesktopServices.openUrl(
                QUrl(f"https://reactome.org/content/query?q={kegg_text}")
            )
        )
        
        # WikiPathways
        wiki_action = menu.addAction(f"🔍 Search '{kegg_text}' in WikiPathways")
        wiki_action.triggered.connect(
            lambda: QDesktopServices.openUrl(
                QUrl(f"https://www.wikipathways.org/index.php/Special:SearchPathways?query={kegg_text}")
            )
        )
    
    def _add_general_search_items(self, menu, text):
        """일반 검색 메뉴 항목 추가 (description 등)"""
        from PyQt6.QtGui import QDesktopServices
        from PyQt6.QtCore import QUrl
        
        # Google Scholar 검색
        scholar_action = menu.addAction(f"📚 Search '{text}' in Google Scholar")
        scholar_action.triggered.connect(
            lambda: QDesktopServices.openUrl(
                QUrl(f"https://scholar.google.com/scholar?q={text}")
            )
        )
        
        # PubMed 검색
        pubmed_action = menu.addAction(f"📚 Search '{text}' in PubMed")
        pubmed_action.triggered.connect(
            lambda: QDesktopServices.openUrl(
                QUrl(f"https://pubmed.ncbi.nlm.nih.gov/?term={text}")
            )
        )

    # ──────────────────────────── IGV integration ────────────────────────────

    def _send_peak_to_igv(self, dataframe, dataset, row: int):
        from utils.igv_connector import IGVConnector
        from PyQt6.QtWidgets import QMessageBox

        chrom = str(dataframe.iloc[row]['chromosome'])
        start = int(dataframe.iloc[row]['peak_start'])
        end = int(dataframe.iloc[row]['peak_end'])

        port = self.settings.value("igv/port", 60151, type=int)
        padding = self.settings.value("igv/padding", 500, type=int)
        auto_genome = self.settings.value("igv/auto_genome", True, type=bool)

        connector = IGVConnector(port=port)
        if not connector.is_running():
            QMessageBox.warning(
                self, "IGV Not Running",
                "IGV에 연결할 수 없습니다.\n\n"
                "IGV를 실행하고 Tools → Preferences → Advanced에서\n"
                "'Enable port (60151)'을 체크해 주세요."
            )
            return

        if auto_genome:
            genome = (dataset.metadata.get('genome_build') or
                      self.settings.value("igv/last_genome", ""))
            if genome:
                connector.set_genome(genome)

        success = connector.goto_peak(chrom, start, end, padding)
        if not success:
            self.logger.warning(f"IGV goto failed: {chrom}:{start}-{end}")

    def _copy_locus(self, dataframe, row: int):
        from PyQt6.QtWidgets import QApplication

        chrom = str(dataframe.iloc[row]['chromosome'])
        start = int(dataframe.iloc[row]['peak_start'])
        end = int(dataframe.iloc[row]['peak_end'])
        locus = f"{chrom}:{start}-{end}"
        QApplication.clipboard().setText(locus)
        if hasattr(self, 'status_label'):
            self.status_label.setText(f"Copied: {locus}")

    def _on_igv_settings(self):
        from gui.igv_settings_dialog import IGVSettingsDialog
        dialog = IGVSettingsDialog(self.settings, self)
        dialog.exec()
