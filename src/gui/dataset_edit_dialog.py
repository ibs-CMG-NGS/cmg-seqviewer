"""
Dataset Edit Dialog

Pre-loaded 데이터셋의 메타데이터를 편집하는 다이얼로그
"""

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
                            QPushButton, QLineEdit, QTextEdit, QLabel,
                            QComboBox, QMessageBox, QGroupBox)
from PyQt6.QtCore import pyqtSignal
import logging

from models.data_models import PreloadedDatasetMetadata, DatasetType
from utils.database_manager import DatabaseManager


class DatasetEditDialog(QDialog):
    """
    Pre-loaded 데이터셋 메타데이터 편집 다이얼로그
    """
    
    # Signal
    edit_completed = pyqtSignal(str)  # dataset_id
    
    def __init__(self, metadata: PreloadedDatasetMetadata, 
                 database_manager: DatabaseManager, parent=None):
        super().__init__(parent)
        
        self.logger = logging.getLogger(__name__)
        self.metadata = metadata
        self.db_manager = database_manager
        
        self._init_ui()
        self._load_metadata()
    
    def _init_ui(self):
        """UI 초기화"""
        self.setWindowTitle(f"Edit Dataset - {self.metadata.alias}")
        self.setGeometry(150, 150, 600, 700)
        
        layout = QVBoxLayout(self)
        
        # 읽기 전용 정보
        info_group = QGroupBox("Dataset Information (Read-only)")
        info_layout = QFormLayout(info_group)
        
        self.info_id = QLabel(self.metadata.dataset_id)
        self.info_id.setStyleSheet("color: gray; font-size: 9px;")
        info_layout.addRow("ID:", self.info_id)
        
        self.info_filename = QLabel(self.metadata.original_filename)
        info_layout.addRow("Original File:", self.info_filename)
        
        self.info_type = QLabel(self.metadata.dataset_type.value)
        info_layout.addRow("Type:", self.info_type)
        
        self.info_stats = QLabel(
            f"{self.metadata.row_count:,} rows | "
            f"{self.metadata.gene_count:,} genes | "
            f"{self.metadata.significant_genes:,} significant"
        )
        info_layout.addRow("Statistics:", self.info_stats)
        
        import_date = self.metadata.import_date.split('T')[0] if self.metadata.import_date else "-"
        self.info_date = QLabel(import_date)
        info_layout.addRow("Import Date:", self.info_date)
        
        layout.addWidget(info_group)
        
        # 편집 가능한 메타데이터
        meta_group = QGroupBox("Editable Metadata")
        meta_layout = QFormLayout(meta_group)
        
        # Alias
        self.alias_input = QLineEdit()
        self.alias_input.setPlaceholderText("e.g., MCF7_Drug_vs_Control")
        meta_layout.addRow("* Alias:", self.alias_input)
        
        # Experiment Condition
        self.condition_input = QLineEdit()
        self.condition_input.setPlaceholderText("e.g., Drug treatment vs Control")
        meta_layout.addRow("Condition:", self.condition_input)
        
        # Cell Type
        self.cell_type_input = QLineEdit()
        self.cell_type_input.setPlaceholderText("e.g., MCF7, HeLa, HEK293")
        meta_layout.addRow("Cell Type:", self.cell_type_input)
        
        # Organism
        self.organism_combo = QComboBox()
        self.organism_combo.setEditable(True)
        self.organism_combo.addItems([
            "Homo sapiens",
            "Mus musculus",
            "Rattus norvegicus",
            "Drosophila melanogaster",
            "Caenorhabditis elegans",
            "Danio rerio"
        ])
        meta_layout.addRow("Organism:", self.organism_combo)
        
        # Tissue
        self.tissue_input = QLineEdit()
        self.tissue_input.setPlaceholderText("e.g., Liver, Brain, Muscle")
        meta_layout.addRow("Tissue:", self.tissue_input)
        
        # Timepoint
        self.timepoint_input = QLineEdit()
        self.timepoint_input.setPlaceholderText("e.g., 24h, 48h, Day 3")
        meta_layout.addRow("Timepoint:", self.timepoint_input)
        
        # Tags
        self.tags_input = QLineEdit()
        self.tags_input.setPlaceholderText("Comma-separated tags")
        meta_layout.addRow("Tags:", self.tags_input)
        
        # Notes
        self.notes_input = QTextEdit()
        self.notes_input.setPlaceholderText("Additional notes or description...")
        self.notes_input.setMaximumHeight(100)
        meta_layout.addRow("Notes:", self.notes_input)
        
        layout.addWidget(meta_group)
        
        # 버튼
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        save_btn = QPushButton("💾 Save Changes")
        save_btn.clicked.connect(self._on_save)
        button_layout.addWidget(save_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
    
    def _load_metadata(self):
        """현재 메타데이터를 UI에 로드"""
        self.alias_input.setText(self.metadata.alias)
        self.condition_input.setText(self.metadata.experiment_condition)
        self.cell_type_input.setText(self.metadata.cell_type)
        self.organism_combo.setCurrentText(self.metadata.organism)
        self.tissue_input.setText(self.metadata.tissue)
        self.timepoint_input.setText(self.metadata.timepoint)
        
        # Tags
        if self.metadata.tags:
            self.tags_input.setText(", ".join(self.metadata.tags))
        
        # Notes
        self.notes_input.setText(self.metadata.notes)
    
    def _on_save(self):
        """변경사항 저장"""
        # 유효성 검사
        alias = self.alias_input.text().strip()
        if not alias:
            QMessageBox.warning(self, "Input Error", "Alias is required.")
            self.alias_input.setFocus()
            return
        
        try:
            # 메타데이터 업데이트
            self.metadata.alias = alias
            self.metadata.experiment_condition = self.condition_input.text().strip()
            self.metadata.cell_type = self.cell_type_input.text().strip()
            self.metadata.organism = self.organism_combo.currentText().strip()
            self.metadata.tissue = self.tissue_input.text().strip()
            self.metadata.timepoint = self.timepoint_input.text().strip()
            self.metadata.notes = self.notes_input.toPlainText().strip()
            
            # Tags 파싱
            tags_text = self.tags_input.text().strip()
            if tags_text:
                self.metadata.tags = [tag.strip() for tag in tags_text.split(',') if tag.strip()]
            else:
                self.metadata.tags = []
            
            # 데이터베이스에 저장
            # DatabaseManager의 메타데이터 리스트를 직접 업데이트하고 저장
            for idx, meta in enumerate(self.db_manager.metadata_list):
                if meta.dataset_id == self.metadata.dataset_id:
                    self.db_manager.metadata_list[idx] = self.metadata
                    break
            
            self.db_manager._save_metadata()
            
            QMessageBox.information(
                self,
                "Save Success",
                f"Metadata for '{alias}' has been successfully updated."
            )
            
            # Signal 발송
            self.edit_completed.emit(self.metadata.dataset_id)
            self.accept()
        
        except Exception as e:
            self.logger.error(f"Failed to save metadata: {e}")
            QMessageBox.critical(
                self,
                "Save Error",
                f"An error occurred while saving:\n\n{str(e)}"
            )
