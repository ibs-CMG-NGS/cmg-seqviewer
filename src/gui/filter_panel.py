"""
Filter Panel Widget

좌측 필터 패널 구현 - Tab 기반 인터페이스
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
                            QLabel, QLineEdit, QTextEdit, QPushButton,
                            QDoubleSpinBox, QCheckBox, QComboBox, QRadioButton,
                            QButtonGroup, QFileDialog, QTabWidget)
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QDragEnterEvent, QDropEvent
from models.data_models import FilterCriteria, FilterMode
from typing import List
from pathlib import Path
import logging


class FilterPanel(QWidget):
    """
    필터 패널
    
    유전자 리스트 입력 및 필터링 조건 설정
    
    두 가지 필터링 모드를 Tab으로 구분:
    1. Gene List 탭: 특정 유전자 목록으로 필터링
    2. Statistical 탭: p-value, FC 기준으로 필터링
    """
    
    filter_requested = pyqtSignal()
    analysis_requested = pyqtSignal(str)  # analysis_type
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = logging.getLogger(__name__)
        self._init_ui()
        
        # 드래그 앤 드롭 활성화 (gene_input에만 적용)
        # gene_input은 _init_ui에서 생성되므로 여기서 설정
    
    def _init_ui(self):
        """UI 초기화"""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        # === Tab Widget 생성 ===
        self.filter_tabs = QTabWidget()
        self.filter_tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #cccccc;
                border-radius: 5px;
            }
            QTabBar::tab {
                padding: 8px 16px;
                margin: 2px;
            }
            QTabBar::tab:selected {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
            }
            QTabBar::tab:!selected {
                background-color: #e0e0e0;
            }
        """)
        
        # === Tab 1: Gene List Filter ===
        gene_tab = QWidget()
        gene_layout = QVBoxLayout(gene_tab)
        gene_layout.setContentsMargins(10, 10, 10, 10)
        
        # 유전자 리스트 텍스트 입력
        gene_layout.addWidget(QLabel("Gene List:"))
        self.gene_input = QTextEdit()
        self.gene_input.setPlaceholderText(
            "Enter gene IDs (one per line)\n"
            "or paste from Excel (Ctrl+V)\n"
            "or drag & drop a gene list file\n\n"
            "Example:\n"
            "BRCA1\n"
            "TP53\n"
            "EGFR"
        )
        self.gene_input.setMaximumHeight(200)
        self.gene_input.textChanged.connect(self._update_gene_count)
        
        # 키 이벤트 핸들러 연결 (Ctrl+V 자동 포맷팅용)
        self.gene_input.keyPressEvent = self._gene_input_key_press
        
        # 드래그 앤 드롭 설정
        self.gene_input.setAcceptDrops(True)
        self.gene_input.dragEnterEvent = self._gene_drag_enter
        self.gene_input.dropEvent = self._gene_drop
        
        gene_layout.addWidget(self.gene_input)
        
        # 유전자 개수 라벨
        self.gene_count_label = QLabel("Genes: 0")
        gene_layout.addWidget(self.gene_count_label)
        
        # 파일에서 로드 버튼
        load_file_layout = QHBoxLayout()
        self.load_file_btn = QPushButton("📁 Load from File...")
        self.load_file_btn.clicked.connect(self._on_load_file)
        load_file_layout.addWidget(self.load_file_btn)
        
        self.save_file_btn = QPushButton("💾 Save to File...")
        self.save_file_btn.clicked.connect(self._on_save_file)
        load_file_layout.addWidget(self.save_file_btn)
        
        self.clear_gene_btn = QPushButton("🗑️ Clear")
        self.clear_gene_btn.clicked.connect(lambda: self.gene_input.clear())
        load_file_layout.addWidget(self.clear_gene_btn)
        gene_layout.addLayout(load_file_layout)
        
        gene_layout.addStretch()
        self.filter_tabs.addTab(gene_tab, "🧬 Gene List")
        
        # === Tab 2: Statistical Filter ===
        stats_tab = QWidget()
        stats_layout = QVBoxLayout(stats_tab)
        stats_layout.setContentsMargins(10, 10, 10, 10)
        
        # === DE Analysis Filtering Section ===
        de_label = QLabel("<b>DE Analysis Filtering:</b>")
        stats_layout.addWidget(de_label)
        
        # Adj p-value와 log2FC를 한 줄로 배열
        de_thresholds_layout = QHBoxLayout()
        
        # Adjusted p-value
        de_thresholds_layout.addWidget(QLabel("Adj. p-value ≤"))
        self.adj_pvalue_input = QDoubleSpinBox()
        self.adj_pvalue_input.setRange(0.0, 1.0)
        self.adj_pvalue_input.setSingleStep(0.01)
        self.adj_pvalue_input.setDecimals(3)
        self.adj_pvalue_input.setValue(0.05)
        self.adj_pvalue_input.setMaximumWidth(80)
        de_thresholds_layout.addWidget(self.adj_pvalue_input)
        
        de_thresholds_layout.addSpacing(20)
        
        # log2 Fold Change
        de_thresholds_layout.addWidget(QLabel("|log₂FC| ≥"))
        self.log2fc_input = QDoubleSpinBox()
        self.log2fc_input.setRange(0.0, 10.0)
        self.log2fc_input.setSingleStep(0.1)
        self.log2fc_input.setDecimals(2)
        self.log2fc_input.setValue(1.0)
        self.log2fc_input.setMaximumWidth(80)
        de_thresholds_layout.addWidget(self.log2fc_input)
        
        de_thresholds_layout.addStretch()
        stats_layout.addLayout(de_thresholds_layout)
        
        # Regulation Direction for DE
        de_direction_layout = QHBoxLayout()
        de_direction_layout.addWidget(QLabel("Regulation:"))
        self.regulation_group = QButtonGroup()
        
        self.both_radio = QRadioButton("Both")
        self.both_radio.setChecked(True)
        self.both_radio.setToolTip("Show both up- and down-regulated genes")
        self.regulation_group.addButton(self.both_radio, 0)
        de_direction_layout.addWidget(self.both_radio)
        
        self.up_radio = QRadioButton("Up")
        self.up_radio.setToolTip("Show only up-regulated genes (log2FC > 0)")
        self.regulation_group.addButton(self.up_radio, 1)
        de_direction_layout.addWidget(self.up_radio)
        
        self.down_radio = QRadioButton("Down")
        self.down_radio.setToolTip("Show only down-regulated genes (log2FC < 0)")
        self.regulation_group.addButton(self.down_radio, 2)
        de_direction_layout.addWidget(self.down_radio)
        
        de_direction_layout.addStretch()
        stats_layout.addLayout(de_direction_layout)
        
        # === Horizontal Line ===
        separator = QLabel()
        separator.setStyleSheet("border-top: 2px solid #cccccc; margin: 10px 0px;")
        separator.setFixedHeight(2)
        stats_layout.addWidget(separator)
        stats_layout.addSpacing(5)
        
        # === GO/KEGG Analysis Filtering Section ===
        go_label = QLabel("<b>GO/KEGG Analysis Filtering:</b>")
        stats_layout.addWidget(go_label)
        
        # FDR cutoff (자유 입력, scientific notation 지원)
        go_fdr_layout = QHBoxLayout()
        go_fdr_layout.addWidget(QLabel("FDR ≤"))
        
        self.go_fdr_input = QLineEdit()
        self.go_fdr_input.setText("0.05")
        self.go_fdr_input.setMaximumWidth(100)
        self.go_fdr_input.setPlaceholderText("e.g., 1e-5")
        self.go_fdr_input.setToolTip("Enter FDR threshold (supports scientific notation like 1e-5)")
        
        # Validation
        from PyQt6.QtGui import QDoubleValidator
        validator = QDoubleValidator(0.0, 1.0, 20)
        validator.setNotation(QDoubleValidator.Notation.ScientificNotation)
        self.go_fdr_input.setValidator(validator)
        go_fdr_layout.addWidget(self.go_fdr_input)
        
        # Preset 버튼들
        preset_values = [("0.1", 0.1), ("0.05", 0.05), ("0.01", 0.01), ("1e-3", 0.001), ("1e-5", 1e-5)]
        for label, value in preset_values:
            btn = QPushButton(label)
            btn.setMaximumWidth(45)
            btn.setToolTip(f"Set FDR to {value}")
            btn.clicked.connect(lambda checked, v=value: self._set_go_fdr_value(v))
            go_fdr_layout.addWidget(btn)
        
        go_fdr_layout.addStretch()
        stats_layout.addLayout(go_fdr_layout)
        
        # Ontology와 Direction을 한 줄로 배치
        go_filters_layout = QHBoxLayout()
        
        # Ontology 선택
        go_filters_layout.addWidget(QLabel("Ontology:"))
        self.ontology_combo = QComboBox()
        self.ontology_combo.addItems(["All", "BP", "MF", "CC", "KEGG"])
        self.ontology_combo.setToolTip("Biological Process / Molecular Function / Cellular Component / KEGG")
        go_filters_layout.addWidget(self.ontology_combo)
        
        go_filters_layout.addSpacing(20)
        
        # Gene Set 선택 (UP/DOWN/TOTAL DEG)
        go_filters_layout.addWidget(QLabel("Gene Set:"))
        self.go_direction_combo = QComboBox()
        self.go_direction_combo.addItems(["All", "UP", "DOWN", "TOTAL"])
        self.go_direction_combo.setToolTip("DEG group used for GO/KEGG analysis (UP-regulated, DOWN-regulated, or TOTAL DEGs)")
        go_filters_layout.addWidget(self.go_direction_combo)
        
        go_filters_layout.addStretch()
        stats_layout.addLayout(go_filters_layout)
        
        # Advanced Filtering 버튼
        self.advanced_go_filter_btn = QPushButton("⚙️ Advanced Filtering...")
        self.advanced_go_filter_btn.setToolTip("Open advanced GO/KEGG filtering dialog")
        self.advanced_go_filter_btn.clicked.connect(lambda: self.analysis_requested.emit("go_advanced_filter"))
        stats_layout.addWidget(self.advanced_go_filter_btn)
        
        stats_layout.addStretch()
        self.filter_tabs.addTab(stats_tab, "📊 Statistical")
        
        # Tab Widget 추가
        layout.addWidget(self.filter_tabs)
        
        # === Apply Filter 버튼 ===
        self.apply_filter_btn = QPushButton("🔍 Apply Filter")
        self.apply_filter_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 10px;
                font-weight: bold;
                font-size: 11pt;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        self.apply_filter_btn.clicked.connect(self.filter_requested.emit)
        layout.addWidget(self.apply_filter_btn)
        
        # Stretch
        layout.addStretch()
    
    def _update_gene_count(self):
        """유전자 개수 업데이트"""
        genes = self.get_gene_list()
        self.gene_count_label.setText(f"Genes: {len(genes)}")
    
    def get_gene_list(self) -> List[str]:
        """입력된 유전자 리스트 반환"""
        text = self.gene_input.toPlainText()
        
        # 여러 구분자로 분리
        separators = ['\n', '\r\n', '\t', ',', ';', ' ']
        genes = [text]
        
        for sep in separators:
            new_genes = []
            for gene in genes:
                new_genes.extend(gene.split(sep))
            genes = new_genes
        
        # 공백 제거 및 중복 제거
        genes = list(set(gene.strip() for gene in genes if gene.strip()))
        
        return genes
    
    def set_gene_list(self, genes: List[str]):
        """유전자 리스트 설정"""
        self.gene_input.setPlainText('\n'.join(genes))
    
    def _on_load_file(self):
        """파일에서 유전자 리스트 로드"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Load Gene List",
            "",
            "Gene List Files (*.txt *.csv *.gmt);;Text Files (*.txt);;CSV Files (*.csv);;GMT Files (*.gmt);;All Files (*.*)"
        )
        
        if not file_path:
            return
        
        try:
            genes = self._parse_gene_file(Path(file_path))
            self.set_gene_list(genes)
            self.logger.info(f"Loaded {len(genes)} genes from {file_path}")
        except Exception as e:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(
                self,
                "File Load Error",
                f"Failed to load gene list:\n{str(e)}"
            )
            self.logger.error(f"Failed to load gene list: {e}", exc_info=True)
    
    def _on_save_file(self):
        """유전자 리스트를 파일로 저장"""
        genes = self.get_gene_list()
        
        if not genes:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(
                self,
                "No Genes",
                "Gene list is empty. Nothing to save."
            )
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Gene List",
            f"gene_list_{len(genes)}_genes.txt",
            "Text Files (*.txt);;CSV Files (*.csv);;All Files (*.*)"
        )
        
        if not file_path:
            return
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                for gene in genes:
                    f.write(f"{gene}\n")
            
            self.logger.info(f"Saved {len(genes)} genes to {file_path}")
            
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.information(
                self,
                "Save Successful",
                f"Saved {len(genes)} genes to:\n{file_path}"
            )
        except Exception as e:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(
                self,
                "File Save Error",
                f"Failed to save gene list:\n{str(e)}"
            )
            self.logger.error(f"Failed to save gene list: {e}", exc_info=True)
    
    def _parse_gene_file(self, file_path: Path) -> List[str]:
        """
        유전자 리스트 파일 파싱
        
        지원 형식:
        - TXT: 한 줄에 하나씩
        - CSV: 첫 번째 컬럼
        - GMT: GSEA gene set format
        """
        genes = []
        
        with open(file_path, 'r', encoding='utf-8') as f:
            if file_path.suffix.lower() == '.gmt':
                # GMT 형식: gene_set_name\tdescription\tgene1\tgene2\t...
                for line in f:
                    if line.strip():
                        parts = line.strip().split('\t')
                        if len(parts) > 2:
                            genes.extend(parts[2:])  # 3번째 컬럼부터 유전자
            elif file_path.suffix.lower() == '.csv':
                # CSV 형식: 첫 번째 컬럼만 사용
                for line in f:
                    if line.strip():
                        first_col = line.split(',')[0].strip()
                        if first_col and not first_col.startswith('#'):
                            genes.append(first_col)
            else:
                # TXT 형식: 한 줄에 하나씩
                for line in f:
                    gene = line.strip()
                    if gene and not gene.startswith('#'):
                        genes.append(gene)
        
        # 중복 제거
        genes = list(set(gene.strip() for gene in genes if gene.strip()))
        return genes
    
    def get_filter_criteria(self) -> FilterCriteria:
        """현재 필터 조건 반환 (활성화된 Tab 기준)"""
        # 현재 선택된 탭 확인 (0: Gene List, 1: Statistical)
        current_tab = self.filter_tabs.currentIndex()
        mode = FilterMode.GENE_LIST if current_tab == 0 else FilterMode.STATISTICAL
        
        # 유전자 리스트 (Gene List 탭일 때만)
        gene_list = None
        if mode == FilterMode.GENE_LIST:
            genes = self.get_gene_list()
            gene_list = genes if genes else None
        
        # Regulation direction 결정
        regulation_direction = "both"  # 기본값
        if hasattr(self, 'regulation_group'):
            checked_button_id = self.regulation_group.checkedId()
            if checked_button_id == 1:  # Up
                regulation_direction = "up"
            elif checked_button_id == 2:  # Down
                regulation_direction = "down"
        
        return FilterCriteria(
            mode=mode,
            adj_pvalue_max=self.adj_pvalue_input.value(),
            log2fc_min=self.log2fc_input.value(),
            gene_list=gene_list,
            fdr_max=self._get_go_fdr_value(),
            regulation_direction=regulation_direction,
            ontology=self.ontology_combo.currentText(),
            go_direction=self.go_direction_combo.currentText(),
        )
    
    def _get_go_fdr_value(self) -> float:
        """GO FDR 입력값을 float로 변환"""
        try:
            return float(self.go_fdr_input.text())
        except ValueError:
            return 0.05  # 기본값
    
    def _set_go_fdr_value(self, value: float):
        """GO FDR 값 설정 (preset 버튼용)"""
        if value >= 0.001:
            self.go_fdr_input.setText(f"{value:.3f}")
        else:
            self.go_fdr_input.setText(f"{value:.2e}")
    
    def set_filter_criteria(self, criteria: FilterCriteria):
        """필터 조건 설정"""
        # 탭 전환
        if criteria.mode == FilterMode.GENE_LIST:
            self.filter_tabs.setCurrentIndex(0)  # Gene List 탭
        else:
            self.filter_tabs.setCurrentIndex(1)  # Statistical 탭
        
        # 값 설정
        self.adj_pvalue_input.setValue(criteria.adj_pvalue_max)
        self.log2fc_input.setValue(criteria.log2fc_min)
        self._set_go_fdr_value(criteria.fdr_max)
        if criteria.gene_list:
            self.set_gene_list(criteria.gene_list)
    
    def get_go_filter_criteria(self):
        """
        GO/KEGG 필터링 기준 반환
        
        Returns:
            dict: FDR, Ontology, Direction 정보
        """
        return {
            'fdr_max': self._get_go_fdr_value(),
            'ontology': self.ontology_combo.currentText(),
            'direction': self.go_direction_combo.currentText(),
        }
    
    def _gene_drag_enter(self, event: QDragEnterEvent):
        """Gene input 드래그 진입 이벤트"""
        if event.mimeData().hasUrls():
            # 파일 확장자 체크
            urls = event.mimeData().urls()
            if urls:
                file_path = urls[0].toLocalFile()
                if file_path.lower().endswith(('.txt', '.csv', '.gmt')):
                    event.accept()
                    return
        # 텍스트 드래그는 기본 동작 허용
        elif event.mimeData().hasText():
            event.accept()
            return
        event.ignore()
    
    def _gene_drop(self, event: QDropEvent):
        """Gene input 드롭 이벤트"""
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if urls:
                file_path = urls[0].toLocalFile()
                if file_path.lower().endswith(('.txt', '.csv', '.gmt')):
                    try:
                        genes = self._parse_gene_file(Path(file_path))
                        self.set_gene_list(genes)
                        self.logger.info(f"Loaded {len(genes)} genes from dropped file: {file_path}")
                        event.accept()
                    except Exception as e:
                        self.logger.error(f"Failed to load gene list from dropped file: {e}")
                        event.ignore()
                    return
        # 텍스트 드래그는 기본 동작 허용
        elif event.mimeData().hasText():
            # QTextEdit의 기본 드롭 동작 호출
            from PyQt6.QtWidgets import QTextEdit
            QTextEdit.dropEvent(self.gene_input, event)
            return
        event.ignore()
    
    def _gene_input_key_press(self, event):
        """Gene input 키 이벤트 핸들러 (Ctrl+V 자동 포맷팅)"""
        from PyQt6.QtGui import QKeyEvent
        from PyQt6.QtCore import Qt
        from PyQt6.QtWidgets import QTextEdit, QApplication
        
        # Ctrl+V 감지
        if event.key() == Qt.Key.Key_V and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            # 클립보드 텍스트 가져오기
            clipboard = QApplication.clipboard()
            text = clipboard.text()
            
            if text:
                # gene1/gene2/gene3 형식을 gene1\ngene2\ngene3으로 변환
                # 여러 구분자 지원: /, \t, ,
                import re
                # 슬래시, 탭, 쉼표를 개행으로 변환
                formatted_text = re.sub(r'[/\t,]+', '\n', text)
                # 연속된 개행을 하나로
                formatted_text = re.sub(r'\n+', '\n', formatted_text)
                # 양쪽 공백 제거
                formatted_text = formatted_text.strip()
                
                # 포맷팅된 텍스트를 삽입
                cursor = self.gene_input.textCursor()
                cursor.insertText(formatted_text)
                
                # 이벤트 처리 완료
                event.accept()
                return
        
        # 다른 키는 기본 동작
        QTextEdit.keyPressEvent(self.gene_input, event)
