"""
Dataset Import Dialog

현재 로드된 데이터셋을 Pre-loaded 데이터베이스로 임포트하는 다이얼로그
"""

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
                            QPushButton, QLineEdit, QTextEdit, QLabel,
                            QComboBox, QMessageBox, QGroupBox)
from PyQt6.QtCore import Qt, pyqtSignal
import logging
from datetime import datetime

from models.data_models import Dataset, PreloadedDatasetMetadata, DatasetType
from utils.database_manager import DatabaseManager


class DatasetImportDialog(QDialog):
    """
    데이터셋 임포트 다이얼로그
    
    현재 로드된 데이터셋을 메타데이터와 함께 데이터베이스에 저장합니다.
    """
    
    # Signal
    import_completed = pyqtSignal(str)  # dataset_id
    
    def __init__(self, dataset: Dataset, database_manager: DatabaseManager, parent=None):
        super().__init__(parent)
        
        self.logger = logging.getLogger(__name__)
        self.dataset = dataset
        self.db_manager = database_manager
        
        self._init_ui()
        self._prefill_data()
    
    def _init_ui(self):
        """UI 초기화"""
        self.setWindowTitle("Import Dataset to Database")
        self.setWindowFlags(
            self.windowFlags()
            | Qt.WindowType.WindowMaximizeButtonHint
            | Qt.WindowType.WindowMinimizeButtonHint
        )
        self.setGeometry(150, 150, 600, 700)
        from utils.dialog_geometry import remember_geometry
        remember_geometry(self)

        layout = QVBoxLayout(self)
        
        # 데이터셋 정보 (읽기 전용)
        info_group = QGroupBox("Dataset Information")
        info_layout = QFormLayout(info_group)
        
        self.info_name = QLabel(self.dataset.name)
        info_layout.addRow("Current Name:", self.info_name)
        
        self.info_type = QLabel(self.dataset.dataset_type.value)
        info_layout.addRow("Type:", self.info_type)
        
        self.info_rows = QLabel(str(len(self.dataset.dataframe)))
        info_layout.addRow("Rows:", self.info_rows)
        
        genes = self.dataset.get_genes()
        self.info_genes = QLabel(str(len(genes)))
        info_layout.addRow("Genes:", self.info_genes)
        
        layout.addWidget(info_group)
        
        # 메타데이터 입력
        meta_group = QGroupBox("Metadata (Required)")
        meta_layout = QFormLayout(meta_group)
        
        # 필수: Alias
        self.alias_input = QLineEdit()
        self.alias_input.setPlaceholderText("e.g., MCF7_Drug_vs_Control")
        meta_layout.addRow("* Alias:", self.alias_input)
        
        # 선택: Experiment Condition
        self.condition_input = QLineEdit()
        self.condition_input.setPlaceholderText("e.g., Drug treatment vs Control")
        meta_layout.addRow("Condition:", self.condition_input)
        
        # 선택: Cell Type
        self.cell_type_input = QLineEdit()
        self.cell_type_input.setPlaceholderText("e.g., MCF7, HeLa, HEK293")
        meta_layout.addRow("Cell Type:", self.cell_type_input)
        
        # 선택: Organism
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
        
        # 선택: Tissue
        self.tissue_input = QLineEdit()
        self.tissue_input.setPlaceholderText("e.g., Liver, Brain, Muscle")
        meta_layout.addRow("Tissue:", self.tissue_input)
        
        # 선택: Timepoint
        self.timepoint_input = QLineEdit()
        self.timepoint_input.setPlaceholderText("e.g., 24h, 48h, Day 3")
        meta_layout.addRow("Timepoint:", self.timepoint_input)
        
        # 선택: Tags
        self.tags_input = QLineEdit()
        self.tags_input.setPlaceholderText("Comma-separated tags (e.g., cancer, apoptosis)")
        meta_layout.addRow("Tags:", self.tags_input)
        
        # 선택: Notes
        self.notes_input = QTextEdit()
        self.notes_input.setPlaceholderText("Additional notes or description...")
        self.notes_input.setMaximumHeight(100)
        meta_layout.addRow("Notes:", self.notes_input)
        
        layout.addWidget(meta_group)
        
        # 원본 파일명 (자동)
        file_group = QGroupBox("File Information")
        file_layout = QFormLayout(file_group)
        
        self.filename_input = QLineEdit(self.dataset.name + ".xlsx")
        file_layout.addRow("Original Filename:", self.filename_input)
        
        layout.addWidget(file_group)
        
        # 버튼
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        import_btn = QPushButton("💾 Import to Database")
        import_btn.clicked.connect(self._on_import)
        button_layout.addWidget(import_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
    
    def _prefill_data(self):
        """기존 데이터로 필드 미리 채우기"""
        # 데이터셋 메타데이터에서 정보 가져오기
        if hasattr(self.dataset, 'metadata') and self.dataset.metadata:
            meta = self.dataset.metadata
            
            if 'experiment_condition' in meta:
                self.condition_input.setText(meta['experiment_condition'])
            
            if 'cell_type' in meta:
                self.cell_type_input.setText(meta['cell_type'])
            
            if 'organism' in meta:
                self.organism_combo.setCurrentText(meta['organism'])
            
            if 'tissue' in meta:
                self.tissue_input.setText(meta['tissue'])
            
            if 'timepoint' in meta:
                self.timepoint_input.setText(meta['timepoint'])
            
            if 'notes' in meta:
                self.notes_input.setText(meta['notes'])
        
        # Alias는 데이터셋 이름 기본값
        if not self.alias_input.text():
            self.alias_input.setText(self.dataset.name)
    
    def _on_import(self):
        """임포트 실행"""
        # 유효성 검사
        alias = self.alias_input.text().strip()
        if not alias:
            QMessageBox.warning(self, "Input Error", "Alias is required.")
            self.alias_input.setFocus()
            return
        
        try:
            # 메타데이터 생성
            tags = []
            tags_text = self.tags_input.text().strip()
            if tags_text:
                tags = [tag.strip() for tag in tags_text.split(',') if tag.strip()]
            
            metadata = PreloadedDatasetMetadata(
                dataset_id="",  # DatabaseManager에서 자동 생성
                alias=alias,
                original_filename=self.filename_input.text().strip() or (self.dataset.name + ".xlsx"),
                dataset_type=self.dataset.dataset_type,
                experiment_condition=self.condition_input.text().strip(),
                cell_type=self.cell_type_input.text().strip(),
                organism=self.organism_combo.currentText().strip(),
                tissue=self.tissue_input.text().strip(),
                timepoint=self.timepoint_input.text().strip(),
                notes=self.notes_input.toPlainText().strip(),
                tags=tags
            )
            
            # 데이터베이스에 임포트
            success = self.db_manager.import_dataset(self.dataset, metadata)
            
            if success:
                QMessageBox.information(
                    self,
                    "Import Success",
                    f"Dataset '{alias}' has been successfully imported to the database.\n\n"
                    f"You can now quickly load it from the Database Browser."
                )
                
                # Signal 발송
                self.import_completed.emit(metadata.dataset_id)
                self.accept()
            else:
                QMessageBox.critical(
                    self,
                    "Import Failed",
                    "Failed to import dataset to database.\n\nPlease check the logs for details."
                )
        
        except Exception as e:
            self.logger.error(f"Import failed: {e}")
            QMessageBox.critical(
                self,
                "Import Error",
                f"An error occurred during import:\n\n{str(e)}"
            )
