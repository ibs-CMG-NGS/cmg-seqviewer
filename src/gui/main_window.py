"""
Main Window for RNA-Seq Data Analysis Program

Excel 스타일의 메인 윈도우를 구현합니다.
"""

from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                            QSplitter, QTabWidget, QTableWidget, QTableWidgetItem,
                            QTextEdit, QMenuBar, QMenu, QToolBar, QStatusBar,
                            QLabel, QPushButton, QFileDialog, QMessageBox,
                            QProgressBar, QInputDialog, QLineEdit, QHeaderView,
                            QSizePolicy)
from PyQt6.QtCore import Qt, pyqtSignal, QThread
from PyQt6.QtGui import QAction, QIcon, QFont, QActionGroup
import logging
from pathlib import Path
from typing import Optional, List, Dict
import pandas as pd

from core.fsm import FSM, State, Event
from core.logger import QtLogHandler, LogBuffer, get_audit_logger
from gui.filter_panel import FilterPanel
from gui.dataset_manager import DatasetManagerWidget
from gui.comparison_panel import ComparisonPanel
from gui.visualization_dialog import VolcanoPlotDialog, PadjHistogramDialog, HeatmapDialog, DotPlotDialog
from gui.venn_dialog import VennDiagramDialog
from gui.venn_dialog_comparison import VennDiagramFromComparisonDialog
from gui.help_dialog import HelpDialog
from models.data_models import FilterMode, DatasetType
from presenters.main_presenter import MainPresenter


class NumericTableWidgetItem(QTableWidgetItem):
    """숫자 정렬을 지원하는 QTableWidgetItem"""
    
    def __init__(self, value, display_text):
        super().__init__(display_text)
        self.numeric_value = value
    
    def __lt__(self, other):
        """정렬을 위한 비교 연산자"""
        if isinstance(other, NumericTableWidgetItem):
            return self.numeric_value < other.numeric_value
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
        self.tab_data: Dict[int, tuple] = {}
        
        # 최근 파일 히스토리 (최대 10개)
        self.recent_files = []
        self.max_recent_files = 10
        self._load_recent_files()
        
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
        
        # 상단: 데이터셋 관리자
        self.dataset_manager = DatasetManagerWidget()
        self.dataset_manager.dataset_selected.connect(self._on_dataset_selected)
        self.dataset_manager.add_dataset_btn.clicked.connect(self._on_add_dataset)
        self.dataset_manager.dataset_removed.connect(self._on_dataset_removed)
        # file_dropped 시그널은 제거 (data_tabs로 이동)
        main_layout.addWidget(self.dataset_manager)
        
        # 중앙: Splitter (좌측 패널 + 우측 데이터 뷰) - 인스턴스 변수로 저장
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # 좌측 패널 컨테이너 (필터 + 비교 기능)
        left_panel = QWidget()
        left_panel.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)  # 가로: 필요한 만큼, 세로: 확장
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(5)
        
        # 필터 패널
        self.filter_panel = FilterPanel()
        self.filter_panel.filter_requested.connect(self._on_filter_requested)
        self.filter_panel.analysis_requested.connect(self._on_analysis_requested)
        left_layout.addWidget(self.filter_panel)
        
        # 비교 패널
        self.comparison_panel = ComparisonPanel()
        self.comparison_panel.compare_requested.connect(self._on_comparison_requested)
        left_layout.addWidget(self.comparison_panel)
        
        # === 실행 버튼 레이아웃 (Apply Filter + Start Comparison) ===
        button_layout = QHBoxLayout()
        button_layout.setSpacing(5)
        button_layout.addWidget(self.filter_panel.apply_filter_btn)
        button_layout.addWidget(self.comparison_panel.compare_btn)
        left_layout.addLayout(button_layout)
        
        self.main_splitter.addWidget(left_panel)
        
        # 우측: 데이터 뷰 (탭) - 주로 확장되도록 설정
        self.data_tabs = QTabWidget()
        self.data_tabs.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)  # 가로/세로 모두 확장
        self.data_tabs.setTabsClosable(True)
        self.data_tabs.tabCloseRequested.connect(self._on_tab_close_requested)
        self.data_tabs.currentChanged.connect(self._on_tab_changed)
        self.data_tabs.setAcceptDrops(True)
        self.data_tabs.dragEnterEvent = self._data_tabs_drag_enter
        self.data_tabs.dropEvent = self._data_tabs_drop
        self.main_splitter.addWidget(self.data_tabs)
        
        # 초기 탭 생성
        self._create_data_tab("Whole Dataset")
        
        # Splitter 비율 설정 (좌측 30%, 우측 70%)
        self.main_splitter.setStretchFactor(0, 30)
        self.main_splitter.setStretchFactor(1, 70)
        
        # Main splitter는 확장 가능, 로그는 고정 높이
        main_layout.addWidget(self.main_splitter, stretch=100)
        
        # 하단: 로그 터미널 (고정 높이, 5-6줄 표시)
        self.log_terminal = QTextEdit()
        self.log_terminal.setReadOnly(True)
        self.log_terminal.setMinimumHeight(120)  # 5-6줄 표시 높이
        self.log_terminal.setMaximumHeight(150)  # 최대 높이
        self.log_terminal.setSizePolicy(
            QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        )
        self.log_terminal.setFont(QFont("Consolas", 11))
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
        
        # 최근 파일 메뉴
        self.recent_menu = file_menu.addMenu("Recent Files")
        self._update_recent_files_menu()
        
        file_menu.addSeparator()
        
        self.export_action = QAction("&Export Current Tab...", self)
        self.export_action.setShortcut("Ctrl+E")
        self.export_action.triggered.connect(self._on_export_data)
        # 항상 활성화
        file_menu.addAction(self.export_action)
        
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
        
        # View 메뉴
        view_menu = menubar.addMenu("&View")
        
        # 컬럼 표시 레벨 서브메뉴
        column_level_menu = view_menu.addMenu("📊 Column Display Level")
        
        self.column_level_group = QActionGroup(self)
        self.column_level_group.setExclusive(True)
        
        basic_action = QAction("Basic (Gene ID + Abundance)", self, checkable=True)
        basic_action.setData("basic")
        basic_action.setChecked(True)  # 기본값: Basic
        basic_action.triggered.connect(lambda: self._on_column_level_changed("basic"))
        self.column_level_group.addAction(basic_action)
        column_level_menu.addAction(basic_action)
        
        de_action = QAction("DE Analysis (+ log2FC, padj)", self, checkable=True)
        de_action.setData("de")
        de_action.triggered.connect(lambda: self._on_column_level_changed("de"))
        self.column_level_group.addAction(de_action)
        column_level_menu.addAction(de_action)
        
        full_action = QAction("Full (All Columns)", self, checkable=True)
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
        
        viz_menu.addSeparator()
        
        # 비교 데이터 시각화
        self.dotplot_action = QAction("⚫ Dot Plot (Comparison Data)", self)
        self.dotplot_action.triggered.connect(self._on_dotplot_requested)
        # 항상 활성화
        viz_menu.addAction(self.dotplot_action)
        
        self.venn_action = QAction("⭕ Venn Diagram (2-3 datasets)", self)
        self.venn_action.triggered.connect(self._on_venn_diagram)
        # 항상 활성화
        viz_menu.addAction(self.venn_action)
        
        viz_menu.addSeparator()
        
        # GO/KEGG 시각화 메뉴 (서브메뉴 없이 직접 추가)
        self.go_dotplot_action = QAction("🧬 GO/KEGG Dot Plot", self)
        self.go_dotplot_action.triggered.connect(lambda: self._on_go_visualization("dotplot"))
        viz_menu.addAction(self.go_dotplot_action)
        
        self.go_barplot_action = QAction("🧬 GO/KEGG Bar Chart", self)
        self.go_barplot_action.triggered.connect(lambda: self._on_go_visualization("barplot"))
        viz_menu.addAction(self.go_barplot_action)
        
        self.go_network_action = QAction("🧬 GO/KEGG Network Chart", self)
        self.go_network_action.triggered.connect(lambda: self._on_go_visualization("network"))
        viz_menu.addAction(self.go_network_action)
        
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
    
    def _create_data_tab(self, tab_name: str) -> QTableWidget:
        """새 데이터 탭 생성"""
        table = QTableWidget()
        table.setAlternatingRowColors(True)
        # 셀 단위 선택으로 변경 (기존: SelectRows)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectItems)
        table.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)  # 다중 선택 가능
        table.setSortingEnabled(True)  # 정렬 기능 활성화
        
        # 선택 색상을 연한 파란색으로 설정
        table.setStyleSheet("""
            QTableWidget::item:selected {
                background-color: #ADD8E6;  /* 연한 파란색 */
                color: black;
            }
        """)
        
        # 키보드 이벤트 핸들러 연결 (Ctrl+C/Ctrl+V)
        table.keyPressEvent = lambda event: self._handle_table_key_press(event, table)
        
        # 헤더 클릭으로 정렬 가능하도록 설정
        table.horizontalHeader().setSectionsClickable(True)
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
            self.tab_data[tab_index] = (dataframe, dataset)
        
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
                
                table.setItem(i, j, item)
        
        # 데이터 입력 완료 후 정렬 기능 활성화
        table.setSortingEnabled(True)
        
        # 저장된 컬럼 너비 복원
        self._restore_table_column_widths(table)
        
        # 컬럼 크기 자동 조정
        table.resizeColumnsToContents()
        
        # gene_symbols 열 너비 제한 (너무 넓지 않게)
        for i, col in enumerate(columns):
            if col == StandardColumns.GENE_SYMBOLS or col.lower() == 'gene_symbols':
                table.setColumnWidth(i, 150)  # 초기 너비를 150px로 제한
                break
    
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
        
        # GO/KEGG 데이터인 경우 - 원본 엑셀 파일의 컬럼 순서 유지
        if dataset and dataset.dataset_type == DatasetType.GO_ANALYSIS:
            # 내부 처리용 컬럼만 제거하고 원본 순서 그대로 유지
            columns_to_show = [col for col in all_columns if col not in internal_columns]
            return columns_to_show
        
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
        """데이터셋 선택"""
        self.presenter.switch_dataset(dataset_name)
    
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
    
    def _on_filter_requested(self):
        """필터링 요청"""
        criteria = self.filter_panel.get_filter_criteria()
        
        # 현재 dataset type 확인 및 로깅
        dataset_type = self.presenter.current_dataset.dataset_type if self.presenter.current_dataset else None
        self.logger.info(f"Filter requested: dataset_type={dataset_type}, criteria={criteria.to_dict()}")
        
        # 현재 활성화된 탭 확인
        current_tab_name = self.data_tabs.tabText(self.data_tabs.currentIndex())
        current_table = self.data_tabs.currentWidget()
        
        # 현재 탭이 Filtered 또는 Comparison 탭인 경우, 해당 데이터를 필터링
        if current_tab_name.startswith("Filtered:") or current_tab_name.startswith("Comparison:"):
            self._filter_current_tab(criteria, current_tab_name, current_table)
        else:
            # Whole Dataset 탭인 경우 기존 방식 사용
            self.presenter.apply_filter(criteria)
    
    def _filter_current_tab(self, criteria, tab_name, table):
        """현재 탭의 데이터를 필터링"""
        try:
            # 테이블 데이터를 DataFrame으로 변환
            row_count = table.rowCount()
            col_count = table.columnCount()
            
            if row_count == 0:
                QMessageBox.warning(self, "No Data", "Current tab is empty.")
                return
            
            # 헤더 읽기
            headers = []
            for col in range(col_count):
                header_item = table.horizontalHeaderItem(col)
                if header_item:
                    headers.append(header_item.text())
            
            # 데이터 읽기
            data = []
            for row in range(row_count):
                row_data = {}
                for col in range(col_count):
                    item = table.item(row, col)
                    if item:
                        value = item.text()
                        # 숫자로 변환 시도
                        try:
                            value = float(value)
                        except:
                            pass
                        row_data[headers[col]] = value
                    else:
                        row_data[headers[col]] = None
                data.append(row_data)
            
            df = pd.DataFrame(data)
            
            # 필터 적용
            if criteria.mode == FilterMode.GENE_LIST:
                # Gene list 필터
                if not criteria.gene_list:
                    QMessageBox.warning(self, "Empty Gene List", "Please enter genes to filter.")
                    return
                
                # gene_id 또는 symbol 컬럼 찾기
                gene_col = None
                if 'symbol' in df.columns:
                    gene_col = 'symbol'
                elif 'gene_id' in df.columns:
                    gene_col = 'gene_id'
                else:
                    QMessageBox.warning(self, "No Gene Column", "No gene identifier column found.")
                    return
                
                # 필터링
                filtered_df = df[df[gene_col].astype(str).str.upper().isin([g.upper() for g in criteria.gene_list])]
                new_tab_name = f"Filtered: {tab_name} - Gene List ({len(criteria.gene_list)} genes)"
                
            else:  # Statistical filter
                # Current dataset type 확인
                current_index = self.data_tabs.currentIndex()
                _, dataset = self.tab_data.get(current_index, (None, None))
                dataset_type = dataset.dataset_type if dataset else None
                
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
                    
                    # Ontology 필터
                    if criteria.ontology != "All" and StandardColumns.ONTOLOGY in filtered_df.columns:
                        filtered_df = filtered_df[filtered_df[StandardColumns.ONTOLOGY] == criteria.ontology]
                    
                    # Gene Set 필터 (UP/DOWN/TOTAL DEG로 분석한 결과)
                    if criteria.go_direction != "All" and StandardColumns.GENE_SET in filtered_df.columns:
                        # gene_set 컬럼의 값이 "UP", "DOWN", "TOTAL" 형식
                        filtered_df = filtered_df[filtered_df[StandardColumns.GENE_SET] == criteria.go_direction]
                    
                    # 탭 이름 생성
                    filters = []
                    if criteria.fdr_max < 0.001:
                        filters.append(f"FDR≤{criteria.fdr_max:.1e}")
                    else:
                        filters.append(f"FDR≤{criteria.fdr_max:.3f}")
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
            
            # 새 탭 생성
            new_table = self._create_data_tab(new_tab_name)
            self.populate_table(new_table, filtered_df)
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
            
            # 필터링
            filtered_df = df[df[gene_id_col].isin(gene_list)].copy()
            
            if filtered_df.empty:
                self.logger.warning(f"No matching genes found in dataset: {dataset.name}")
                # 대소문자 구분 없이 재시도
                filtered_df = df[df[gene_id_col].str.upper().isin([g.upper() for g in gene_list])].copy()
                if not filtered_df.empty:
                    self.logger.info(f"Found {len(filtered_df)} genes after case-insensitive matching")
                else:
                    continue
            else:
                self.logger.info(f"Found {len(filtered_df)} matching genes in dataset: {dataset.name}")
            
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
        
        # 2. 결과 DataFrame 생성
        result_rows = []
        # 타입 혼합 문제 방지를 위해 문자열로 변환 후 정렬
        for identifier in sorted(gene_mapping.keys(), key=str):
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
        table = self._create_data_tab(comparison_tab_name)
        self.populate_table(table, result_df)
        self.logger.info(f"Gene list comparison completed: {len(result_df)} genes across {len(datasets)} datasets")
    
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
        table = self._create_data_tab(comparison_tab_name)
        self.populate_table(table, result_df)
        
        # 통계 정보 로그
        self.logger.info(f"Statistics comparison completed:")
        self.logger.info(f"  - Total unique genes: {len(all_genes)}")
        self.logger.info(f"  - Common genes (in all datasets): {len(common_genes)}")
        for name, genes in dataset_genes.items():
            unique_to_dataset = genes - set.union(*(g for n, g in dataset_genes.items() if n != name))
            self.logger.info(f"  - Unique to {name}: {len(unique_to_dataset)}")
    
    def _update_comparison_panel_datasets(self):
        """비교 패널의 데이터셋 리스트 업데이트"""
        dataset_names = self.dataset_manager.get_all_datasets()
        self.comparison_panel.update_dataset_list(dataset_names)


    
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
    
    def _on_tab_close_requested(self, index: int):
        """탭 닫기 요청"""
        if index > 0:  # 첫 번째 탭(Whole Dataset)은 닫지 않음
            self.data_tabs.removeTab(index)
            # 탭 데이터도 제거
            if index in self.tab_data:
                del self.tab_data[index]
            # 메뉴 상태 업데이트
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
                _, dataset = self.tab_data[index]
                if dataset is not None:
                    self.presenter.current_dataset = dataset
                    self.logger.info(f"Tab changed to index {index}: current_dataset updated to '{dataset.name}'")
    
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
                dataframe, dataset = self.tab_data[tab_index]
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
                dataframe, dataset = self.tab_data[tab_index]
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
        QMessageBox.about(
            self, "About RNA-Seq Data Analyzer",
            "<h2>CMG-SeqViewer</h2>"
            "<p><b>Version 1.0.0</b></p>"
            "<p>A comprehensive tool for RNA-Seq data analysis and visualization.</p>"
            "<br>"
            "<p><b>Key Features:</b></p>"
            "<ul>"
            "<li><b>Data Management:</b> Multi-dataset loading and comparison</li>"
            "<li><b>Filtering:</b> Gene list and statistical filtering with active tab support</li>"
            "<li><b>Statistical Analysis:</b> Fisher's Exact Test, GSEA Lite</li>"
            "<li><b>Visualizations:</b> Volcano plots, Heatmaps, P-adj Histograms</li>"
            "<li><b>Comparison Tools:</b> Venn diagrams (2-3 datasets), Dataset statistics comparison</li>"
            "</ul>"
            "<br>"
            "<p><b>Advanced Features:</b></p>"
            "<ul>"
            "<li>Interactive tooltips with boundary detection</li>"
            "<li>Customizable plot titles, labels, and color schemes</li>"
            "<li>Heatmap clustering (Padj, Log2FC, Hierarchical)</li>"
            "<li>Adjustable colorbar ranges for heatmaps</li>"
            "<li>Cell-level selection and clipboard support (Ctrl+C/V)</li>"
            "<li>Column display levels (Basic, DE Analysis, Full)</li>"
            "</ul>"
            "<br>"
            "<p><b>Developed with:</b> Python, PyQt6, Pandas, Matplotlib, Seaborn</p>"
            "<p>© 2025 ibs CMG NGS core</p>"
        )
    
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
            
            dataframe, dataset = self.tab_data[current_index]
            
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
                dialog.exec()
            elif viz_type == "histogram":
                dialog = PadjHistogramDialog(df, self)
                dialog.exec()
            elif viz_type == "heatmap":
                dialog = HeatmapDialog(df, self)
                dialog.exec()
            
            self.logger.info(f"Visualization opened: {viz_type}")
            
        except Exception as e:
            self.logger.error(f"Visualization failed: {e}")
            QMessageBox.critical(self, "Visualization Error", 
                               f"Failed to create visualization:\n{str(e)}")
    
    def _on_dotplot_requested(self):
        """Dot Plot 시각화 (Comparison Data)"""
        # 현재 탭이 Comparison sheet인지 확인
        current_index = self.data_tabs.currentIndex()
        current_tab_name = self.data_tabs.tabText(current_index)
        
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
        dataframe, dataset = self.tab_data[current_tab_index]
        
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
            table = self._create_data_tab(dataset_name)
            self.populate_table(table, clustered_data, clustered_dataset)
            
            # 탭 데이터 저장
            tab_index = self.data_tabs.count() - 1  # 방금 추가한 탭
            self.tab_data[tab_index] = (clustered_data, clustered_dataset)
            
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
        
        dataframe, dataset = self.tab_data[current_index]
        
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
            # Dataset 복사본 생성하여 현재 탭의 dataframe 사용
            filtered_dataset = Dataset(
                name=dataset.name,
                dataset_type=dataset.dataset_type,
                dataframe=dataframe,  # 현재 탭의 필터링된 dataframe 사용
                original_columns=dataset.original_columns,
                metadata=dataset.metadata
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
            # 기존 동일한 이름의 탭이 있는지 확인하고 제거
            existing_indices = []
            
            # 동일한 이름의 탭이 있는지 확인 (덮어쓰기용)
            for i in range(self.data_tabs.count()):
                current_name = self.data_tabs.tabText(i)
                # 정확히 같은 이름의 탭이면 제거 대상 (덮어쓰기)
                if current_name == tab_name:
                    existing_indices.append(i)
            
            # 기존 동일 이름 탭 제거 (역순으로 제거하여 인덱스 문제 방지)
            if existing_indices:
                for idx in reversed(existing_indices):
                    self.data_tabs.removeTab(idx)
            
            # 새 탭 생성
            table = self._create_data_tab(tab_name)
            new_tab_index = self.data_tabs.indexOf(table)
            
            # 데이터셋 생성 - 현재 활성 데이터셋의 타입을 유지
            from models.data_models import Dataset, DatasetType
            current_dataset = self.presenter.current_dataset
            dataset_type = current_dataset.dataset_type if current_dataset else DatasetType.GO_ANALYSIS
            
            dataset = Dataset(
                name=tab_name,
                dataset_type=dataset_type,  # 현재 dataset type 유지
                dataframe=filtered_df,
                original_columns={},
                metadata={}
            )
            
            # 테이블에 데이터 채우기
            self.populate_table(table, filtered_df, dataset)
            
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
