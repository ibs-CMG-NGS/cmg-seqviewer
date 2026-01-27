"""
Database Browser Dialog

Pre-loaded 데이터셋 데이터베이스를 브라우징하고 관리하는 GUI 다이얼로그
"""

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
                            QTableWidget, QTableWidgetItem, QLineEdit, QLabel,
                            QComboBox, QMessageBox, QHeaderView, QGroupBox,
                            QFormLayout, QTextEdit, QCheckBox, QSplitter, QWidget)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from typing import List, Optional
import logging

from models.data_models import PreloadedDatasetMetadata, DatasetType
from utils.database_manager import DatabaseManager


class DatabaseBrowserDialog(QDialog):
    """
    Pre-loaded 데이터셋 브라우저 다이얼로그
    
    기능:
    - 데이터베이스 내 데이터셋 목록 표시
    - 검색 및 필터링
    - 단일/다중 선택하여 로드
    - 데이터셋 삭제
    """
    
    # Signals
    datasets_selected = pyqtSignal(list)  # 선택된 dataset_id 리스트
    
    def __init__(self, database_manager: DatabaseManager, parent=None):
        super().__init__(parent)
        
        self.logger = logging.getLogger(__name__)
        self.db_manager = database_manager
        self.selected_ids: List[str] = []
        
        self._init_ui()
        self._load_datasets()
    
    def _init_ui(self):
        """UI 초기화"""
        self.setWindowTitle("Database Browser - Pre-loaded Datasets")
        self.setGeometry(100, 100, 1200, 700)
        
        layout = QVBoxLayout(self)
        
        # 상단: 검색 및 필터
        search_group = QGroupBox("Search && Filter")
        search_layout = QHBoxLayout(search_group)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search by alias, condition, notes...")
        self.search_input.textChanged.connect(self._on_search)
        search_layout.addWidget(QLabel("Search:"))
        search_layout.addWidget(self.search_input, stretch=1)
        
        self.cell_type_filter = QComboBox()
        self.cell_type_filter.addItem("All Cell Types")
        self.cell_type_filter.currentTextChanged.connect(self._on_filter_changed)
        search_layout.addWidget(QLabel("Cell Type:"))
        search_layout.addWidget(self.cell_type_filter)
        
        self.organism_filter = QComboBox()
        self.organism_filter.addItem("All Organisms")
        self.organism_filter.currentTextChanged.connect(self._on_filter_changed)
        search_layout.addWidget(QLabel("Organism:"))
        search_layout.addWidget(self.organism_filter)
        
        # Refresh 버튼
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.setToolTip("Scan for new parquet files in data folder")
        refresh_btn.clicked.connect(self._on_refresh_database)
        search_layout.addWidget(refresh_btn)
        
        # Open Data Folder 버튼
        open_folder_btn = QPushButton("📂 Open Data Folder")
        open_folder_btn.setToolTip("Open external data folder to add parquet files")
        open_folder_btn.clicked.connect(self._on_open_data_folder)
        search_layout.addWidget(open_folder_btn)
        
        layout.addWidget(search_group)
        
        # 중앙: Splitter (테이블 + 상세 정보)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # 테이블
        self.table = QTableWidget()
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
        self.table.itemSelectionChanged.connect(self._on_selection_changed)
        
        # 선택 강조를 위한 스타일시트 적용
        self.table.setStyleSheet("""
            QTableWidget::item:selected {
                background-color: #0078d4;
                color: white;
            }
            QTableWidget::item:selected:!active {
                background-color: #0078d4;
                color: white;
            }
            QTableWidget {
                selection-background-color: #0078d4;
                gridline-color: #d0d0d0;
            }
        """)
        
        # 컬럼 설정
        columns = ["Alias", "Type", "Condition", "Cell Type", "Organism", 
                  "Rows", "Genes", "Sig. Genes", "Import Date", "Tags"]
        self.table.setColumnCount(len(columns))
        self.table.setHorizontalHeaderLabels(columns)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        
        # 더블클릭 시 로드
        self.table.doubleClicked.connect(self._on_load_selected)
        
        splitter.addWidget(self.table)
        
        # 우측: 상세 정보 패널
        detail_panel = QWidget()
        detail_layout = QVBoxLayout(detail_panel)
        
        detail_group = QGroupBox("Dataset Details")
        detail_form = QFormLayout(detail_group)
        
        self.detail_alias = QLabel("-")
        self.detail_alias.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        detail_form.addRow("Alias:", self.detail_alias)
        
        self.detail_filename = QLabel("-")
        detail_form.addRow("Original File:", self.detail_filename)
        
        self.detail_type = QLabel("-")
        detail_form.addRow("Type:", self.detail_type)
        
        self.detail_condition = QLabel("-")
        self.detail_condition.setWordWrap(True)
        detail_form.addRow("Condition:", self.detail_condition)
        
        self.detail_cell_type = QLabel("-")
        detail_form.addRow("Cell Type:", self.detail_cell_type)
        
        self.detail_organism = QLabel("-")
        detail_form.addRow("Organism:", self.detail_organism)
        
        self.detail_tissue = QLabel("-")
        detail_form.addRow("Tissue:", self.detail_tissue)
        
        self.detail_timepoint = QLabel("-")
        detail_form.addRow("Timepoint:", self.detail_timepoint)
        
        self.detail_stats = QLabel("-")
        detail_form.addRow("Statistics:", self.detail_stats)
        
        self.detail_import_date = QLabel("-")
        detail_form.addRow("Import Date:", self.detail_import_date)
        
        self.detail_notes = QTextEdit()
        self.detail_notes.setReadOnly(True)
        self.detail_notes.setMaximumHeight(100)
        detail_form.addRow("Notes:", self.detail_notes)
        
        detail_layout.addWidget(detail_group)
        
        # 관리 버튼들
        mgmt_layout = QVBoxLayout()
        
        self.edit_btn = QPushButton("✏️ Edit Metadata")
        self.edit_btn.setEnabled(False)
        self.edit_btn.clicked.connect(self._on_edit_selected)
        mgmt_layout.addWidget(self.edit_btn)
        
        delete_btn = QPushButton("🗑️ Delete Selected")
        delete_btn.clicked.connect(self._on_delete_selected)
        mgmt_layout.addWidget(delete_btn)
        
        detail_layout.addLayout(mgmt_layout)
        detail_layout.addStretch()
        
        splitter.addWidget(detail_panel)
        splitter.setStretchFactor(0, 7)
        splitter.setStretchFactor(1, 3)
        
        layout.addWidget(splitter, stretch=1)
        
        # 하단: 통계 및 버튼
        stats_layout = QHBoxLayout()
        self.stats_label = QLabel("")
        stats_layout.addWidget(self.stats_label)
        stats_layout.addStretch()
        layout.addLayout(stats_layout)
        
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.load_btn = QPushButton("📂 Load Selected Dataset(s)")
        self.load_btn.setEnabled(False)
        self.load_btn.clicked.connect(self._on_load_selected)
        button_layout.addWidget(self.load_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
    
    def _load_datasets(self):
        """데이터베이스에서 데이터셋 목록 로드"""
        try:
            metadata_list = self.db_manager.get_all_metadata()
            self._populate_table(metadata_list)
            
            # 필터 콤보박스 업데이트
            self._update_filters()
            
            # 통계 업데이트 (선택 상태 초기화)
            self._update_selection_status()
            
            self.logger.info(f"Loaded {len(metadata_list)} datasets from database")
            
        except Exception as e:
            self.logger.error(f"Failed to load datasets: {e}")
            QMessageBox.warning(self, "Error", f"Failed to load datasets:\n{str(e)}")
    
    def _populate_table(self, metadata_list: List[PreloadedDatasetMetadata]):
        """테이블에 데이터셋 목록 표시"""
        self.table.setRowCount(0)
        
        for meta in metadata_list:
            row = self.table.rowCount()
            self.table.insertRow(row)
            
            # 데이터셋 ID를 숨겨진 데이터로 저장
            alias_item = QTableWidgetItem(meta.alias)
            alias_item.setData(Qt.ItemDataRole.UserRole, meta.dataset_id)
            self.table.setItem(row, 0, alias_item)
            
            self.table.setItem(row, 1, QTableWidgetItem(meta.dataset_type.value))
            self.table.setItem(row, 2, QTableWidgetItem(meta.experiment_condition))
            self.table.setItem(row, 3, QTableWidgetItem(meta.cell_type))
            self.table.setItem(row, 4, QTableWidgetItem(meta.organism))
            self.table.setItem(row, 5, QTableWidgetItem(str(meta.row_count)))
            self.table.setItem(row, 6, QTableWidgetItem(str(meta.gene_count)))
            self.table.setItem(row, 7, QTableWidgetItem(str(meta.significant_genes)))
            
            # 날짜 포맷
            import_date = meta.import_date.split('T')[0] if meta.import_date else "-"
            self.table.setItem(row, 8, QTableWidgetItem(import_date))
            
            # 태그
            tags_str = ", ".join(meta.tags) if meta.tags else "-"
            self.table.setItem(row, 9, QTableWidgetItem(tags_str))
    
    def _update_filters(self):
        """필터 콤보박스 업데이트"""
        metadata_list = self.db_manager.get_all_metadata()
        
        # Cell Type
        cell_types = sorted(set(m.cell_type for m in metadata_list if m.cell_type))
        current_cell = self.cell_type_filter.currentText()
        self.cell_type_filter.clear()
        self.cell_type_filter.addItem("All Cell Types")
        self.cell_type_filter.addItems(cell_types)
        if current_cell in cell_types:
            self.cell_type_filter.setCurrentText(current_cell)
        
        # Organism
        organisms = sorted(set(m.organism for m in metadata_list if m.organism))
        current_org = self.organism_filter.currentText()
        self.organism_filter.clear()
        self.organism_filter.addItem("All Organisms")
        self.organism_filter.addItems(organisms)
        if current_org in organisms:
            self.organism_filter.setCurrentText(current_org)
    
    def _on_search(self):
        """검색 텍스트 변경 시"""
        self._apply_filters()
    
    def _on_filter_changed(self):
        """필터 변경 시"""
        self._apply_filters()
    
    def _apply_filters(self):
        """검색 및 필터 적용"""
        query = self.search_input.text()
        cell_type = self.cell_type_filter.currentText()
        organism = self.organism_filter.currentText()
        
        # "All ..." 선택 시 빈 문자열로 변환
        if cell_type == "All Cell Types":
            cell_type = ""
        if organism == "All Organisms":
            organism = ""
        
        # 검색 실행
        results = self.db_manager.search_datasets(
            query=query,
            cell_type=cell_type,
            organism=organism
        )
        
        self._populate_table(results)
    
    def _on_selection_changed(self):
        """테이블 선택 변경 시"""
        selected_rows = self.table.selectionModel().selectedRows()
        self.selected_ids = []
        
        for index in selected_rows:
            dataset_id = self.table.item(index.row(), 0).data(Qt.ItemDataRole.UserRole)
            self.selected_ids.append(dataset_id)
        
        self.load_btn.setEnabled(len(self.selected_ids) > 0)
        self.edit_btn.setEnabled(len(self.selected_ids) == 1)  # 편집은 단일 선택만
        
        # 선택된 항목 수 업데이트
        self._update_selection_status()
        
        # 상세 정보 업데이트 (단일 선택 시)
        if len(self.selected_ids) == 1:
            self._show_details(self.selected_ids[0])
        else:
            self._clear_details()
    
    def _update_selection_status(self):
        """선택된 항목 수 표시 업데이트"""
        stats = self.db_manager.get_statistics()
        total = stats.get('dataset_count', 0)
        
        if len(self.selected_ids) == 0:
            status_text = f"Total: {total} dataset(s)"
        elif len(self.selected_ids) == 1:
            status_text = f"Total: {total} dataset(s) | ✓ 1 selected"
        else:
            status_text = f"Total: {total} dataset(s) | ✓ {len(self.selected_ids)} selected"
        
        self.stats_label.setText(status_text)
        self.stats_label.setStyleSheet("font-weight: bold; color: #0078d4;" if len(self.selected_ids) > 0 else "")
    
    def _show_details(self, dataset_id: str):
        """데이터셋 상세 정보 표시"""
        metadata = self.db_manager.get_metadata(dataset_id)
        if metadata:
            self.detail_alias.setText(metadata.alias)
            self.detail_filename.setText(metadata.original_filename)
            self.detail_type.setText(metadata.dataset_type.value)
            self.detail_condition.setText(metadata.experiment_condition or "-")
            self.detail_cell_type.setText(metadata.cell_type or "-")
            self.detail_organism.setText(metadata.organism or "-")
            self.detail_tissue.setText(metadata.tissue or "-")
            self.detail_timepoint.setText(metadata.timepoint or "-")
            
            stats_text = (f"{metadata.row_count:,} rows | "
                         f"{metadata.gene_count:,} genes | "
                         f"{metadata.significant_genes:,} significant")
            self.detail_stats.setText(stats_text)
            
            import_date = metadata.import_date.split('T')[0] if metadata.import_date else "-"
            self.detail_import_date.setText(import_date)
            
            self.detail_notes.setText(metadata.notes or "(No notes)")
    
    def _clear_details(self):
        """상세 정보 초기화"""
        self.detail_alias.setText("-")
        self.detail_filename.setText("-")
        self.detail_type.setText("-")
        self.detail_condition.setText("-")
        self.detail_cell_type.setText("-")
        self.detail_organism.setText("-")
        self.detail_tissue.setText("-")
        self.detail_timepoint.setText("-")
        self.detail_stats.setText("-")
        self.detail_import_date.setText("-")
        self.detail_notes.setText("")
    
    def _on_load_selected(self):
        """선택된 데이터셋 로드"""
        if not self.selected_ids:
            return
        
        # Signal 발송
        self.datasets_selected.emit(self.selected_ids)
        self.accept()
    
    def _on_delete_selected(self):
        """선택된 데이터셋 삭제"""
        if not self.selected_ids:
            QMessageBox.warning(self, "No Selection", "Please select dataset(s) to delete.")
            return
        
        # 확인 메시지
        count = len(self.selected_ids)
        reply = QMessageBox.question(
            self,
            "Confirm Deletion",
            f"Are you sure you want to delete {count} dataset(s)?\n\nThis action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            success_count = 0
            for dataset_id in self.selected_ids:
                if self.db_manager.delete_dataset(dataset_id):
                    success_count += 1
            
            QMessageBox.information(
                self,
                "Deletion Complete",
                f"Successfully deleted {success_count} out of {count} dataset(s)."
            )
            
            # 목록 새로고침
            self._load_datasets()
            self.selected_ids = []
    
    def _on_edit_selected(self):
        """선택된 데이터셋 메타데이터 편집"""
        if len(self.selected_ids) != 1:
            return
        
        dataset_id = self.selected_ids[0]
        metadata = self.db_manager.get_metadata(dataset_id)
        
        if not metadata:
            QMessageBox.warning(self, "Error", "Dataset not found.")
            return
        
        from gui.dataset_edit_dialog import DatasetEditDialog
        
        dialog = DatasetEditDialog(metadata, self.db_manager, self)
        dialog.edit_completed.connect(self._on_edit_completed)
        dialog.exec()
    
    def _on_edit_completed(self, dataset_id: str):
        """편집 완료 후 목록 새로고침"""
        self.logger.info(f"Dataset metadata edited: {dataset_id}")
        self._load_datasets()
    
    def _on_refresh_database(self):
        """데이터베이스 새로고침 - 새로운 parquet 파일 스캔"""
        self.logger.info("Refreshing database...")
        
        try:
            # 데이터베이스 스캔 (새 parquet 파일 자동 임포트)
            new_count = self.db_manager.refresh_database()
            
            # 목록 새로고침
            self._load_datasets()
            
            # 결과 메시지
            if new_count > 0:
                QMessageBox.information(
                    self,
                    "Refresh Complete",
                    f"Found and imported {new_count} new dataset(s).\n\n"
                    f"Total datasets: {len(self.db_manager.metadata_list)}"
                )
            else:
                QMessageBox.information(
                    self,
                    "Refresh Complete",
                    "No new datasets found.\n\n"
                    f"Current datasets: {len(self.db_manager.metadata_list)}"
                )
                
        except Exception as e:
            self.logger.error(f"Failed to refresh database: {e}")
            QMessageBox.critical(
                self,
                "Refresh Failed",
                f"Failed to refresh database:\n{str(e)}"
            )
    
    def _on_open_data_folder(self):
        """외부 데이터 폴더를 파일 탐색기에서 열기"""
        try:
            self.db_manager.open_external_data_folder()
            
            QMessageBox.information(
                self,
                "Data Folder Opened",
                "External data folder has been opened.\n\n"
                "Add your parquet files to the 'datasets' subfolder,\n"
                "then click 'Refresh' to import them."
            )
            
        except Exception as e:
            self.logger.error(f"Failed to open data folder: {e}")
            QMessageBox.warning(
                self,
                "Error",
                f"Failed to open data folder:\n{str(e)}"
            )
