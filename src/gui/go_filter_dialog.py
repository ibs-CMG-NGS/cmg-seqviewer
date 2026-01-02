"""
GO/KEGG Filter Dialog

GO/KEGG 분석 결과를 필터링하기 위한 다이얼로그입니다.

Features:
    - FDR 임계값 설정 (슬라이더)
    - Ontology 선택 (BP/CC/MF/KEGG)
    - Direction 선택 (UP/DOWN/TOTAL)
    - Gene count 범위 설정
    - Description 텍스트 검색
"""

from typing import List, Optional
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox,
    QLabel, QSlider, QDoubleSpinBox, QSpinBox,
    QCheckBox, QLineEdit, QPushButton, QRadioButton,
    QButtonGroup, QMessageBox
)
from PyQt6.QtCore import Qt

from models.data_models import Dataset


class GOFilterDialog(QDialog):
    """GO/KEGG 결과 필터링 다이얼로그"""
    
    def __init__(self, dataset: Dataset, parent=None):
        super().__init__(parent)
        self.dataset = dataset
        self.setWindowTitle("Filter GO/KEGG Results")
        self.setMinimumWidth(500)
        
        self._init_ui()
    
    def _init_ui(self):
        """UI 초기화"""
        layout = QVBoxLayout(self)
        
        # FDR Threshold
        fdr_group = self._create_fdr_group()
        layout.addWidget(fdr_group)
        
        # Ontology Selection
        ontology_group = self._create_ontology_group()
        layout.addWidget(ontology_group)
        
        # Direction Selection
        direction_group = self._create_direction_group()
        layout.addWidget(direction_group)
        
        # Gene Count Range
        gene_count_group = self._create_gene_count_group()
        layout.addWidget(gene_count_group)
        
        # Description Search
        description_group = self._create_description_group()
        layout.addWidget(description_group)
        
        # Buttons
        button_layout = self._create_buttons()
        layout.addLayout(button_layout)
    
    def _create_fdr_group(self) -> QGroupBox:
        """FDR 임계값 그룹 생성"""
        group = QGroupBox("FDR Threshold")
        layout = QVBoxLayout(group)
        
        # Scientific notation 입력을 위한 QLineEdit + 슬라이더 사용
        input_layout = QHBoxLayout()
        
        # Label
        input_layout.addWidget(QLabel("FDR ≤"))
        
        # Scientific notation 입력 필드
        self.fdr_input = QLineEdit()
        self.fdr_input.setText("0.05")
        self.fdr_input.setFixedWidth(120)
        self.fdr_input.setPlaceholderText("e.g., 1e-5")
        self.fdr_input.setToolTip("Enter FDR threshold (supports scientific notation like 1e-5)")
        input_layout.addWidget(self.fdr_input)
        
        # Preset buttons for common values
        preset_layout = QHBoxLayout()
        preset_values = [
            ("0.1", 0.1),
            ("0.05", 0.05),
            ("0.01", 0.01),
            ("1e-3", 0.001),
            ("1e-5", 1e-5),
            ("1e-10", 1e-10),
        ]
        
        for label, value in preset_values:
            btn = QPushButton(label)
            btn.setFixedWidth(50)
            btn.clicked.connect(lambda checked, v=value: self._set_fdr_value(v))
            preset_layout.addWidget(btn)
        
        preset_layout.addStretch()
        
        # Validation
        from PyQt6.QtGui import QDoubleValidator
        validator = QDoubleValidator(0.0, 1.0, 20)  # 20 decimal places
        validator.setNotation(QDoubleValidator.Notation.ScientificNotation)
        self.fdr_input.setValidator(validator)
        
        layout.addLayout(input_layout)
        
        # Preset buttons
        preset_label = QLabel("Quick presets:")
        preset_label.setStyleSheet("color: #666; font-size: 9pt; margin-top: 5px;")
        layout.addWidget(preset_label)
        layout.addLayout(preset_layout)
        
        # Scientific notation 안내
        info_label = QLabel("💡 Supports scientific notation (e.g., 1e-5 = 0.00001)")
        info_label.setStyleSheet("color: #666; font-size: 9pt; font-style: italic;")
        layout.addWidget(info_label)
        
        # FDR 필터 활성화 체크박스
        self.fdr_enabled = QCheckBox("Enable FDR filtering")
        self.fdr_enabled.setChecked(True)
        layout.addWidget(self.fdr_enabled)
        
        return group
    
    def _set_fdr_value(self, value: float):
        """FDR 값 설정 (preset 버튼용)"""
        if value >= 0.001:
            self.fdr_input.setText(f"{value:.3f}")
        else:
            self.fdr_input.setText(f"{value:.2e}")
    
    def _create_ontology_group(self) -> QGroupBox:
        """Ontology 선택 그룹 생성"""
        group = QGroupBox("Ontology")
        layout = QVBoxLayout(group)
        
        # 체크박스들
        self.bp_checkbox = QCheckBox("Biological Process (BP)")
        self.bp_checkbox.setChecked(True)
        
        self.cc_checkbox = QCheckBox("Cellular Component (CC)")
        self.cc_checkbox.setChecked(True)
        
        self.mf_checkbox = QCheckBox("Molecular Function (MF)")
        self.mf_checkbox.setChecked(True)
        
        self.kegg_checkbox = QCheckBox("KEGG Pathway")
        self.kegg_checkbox.setChecked(True)
        
        # Select All / Deselect All 버튼
        button_layout = QHBoxLayout()
        select_all_btn = QPushButton("Select All")
        deselect_all_btn = QPushButton("Deselect All")
        
        select_all_btn.clicked.connect(self._select_all_ontologies)
        deselect_all_btn.clicked.connect(self._deselect_all_ontologies)
        
        button_layout.addWidget(select_all_btn)
        button_layout.addWidget(deselect_all_btn)
        button_layout.addStretch()
        
        layout.addWidget(self.bp_checkbox)
        layout.addWidget(self.cc_checkbox)
        layout.addWidget(self.mf_checkbox)
        layout.addWidget(self.kegg_checkbox)
        layout.addLayout(button_layout)
        
        return group
    
    def _create_direction_group(self) -> QGroupBox:
        """Direction 선택 그룹 생성"""
        group = QGroupBox("Direction")
        layout = QVBoxLayout(group)
        
        # 라디오 버튼 그룹
        self.direction_group = QButtonGroup()
        
        self.all_radio = QRadioButton("All (UP/DOWN/TOTAL)")
        self.up_radio = QRadioButton("UP-regulated only")
        self.down_radio = QRadioButton("DOWN-regulated only")
        self.total_radio = QRadioButton("TOTAL/Overall only")
        
        self.all_radio.setChecked(True)
        
        self.direction_group.addButton(self.all_radio, 0)
        self.direction_group.addButton(self.up_radio, 1)
        self.direction_group.addButton(self.down_radio, 2)
        self.direction_group.addButton(self.total_radio, 3)
        
        layout.addWidget(self.all_radio)
        layout.addWidget(self.up_radio)
        layout.addWidget(self.down_radio)
        layout.addWidget(self.total_radio)
        
        return group
    
    def _create_gene_count_group(self) -> QGroupBox:
        """Gene count 범위 그룹 생성"""
        group = QGroupBox("Gene Count Range")
        layout = QVBoxLayout(group)
        
        # Min gene count
        min_layout = QHBoxLayout()
        min_layout.addWidget(QLabel("Minimum:"))
        self.min_gene_spinbox = QSpinBox()
        self.min_gene_spinbox.setMinimum(0)
        self.min_gene_spinbox.setMaximum(10000)
        self.min_gene_spinbox.setValue(2)
        self.min_gene_spinbox.setFixedWidth(100)
        min_layout.addWidget(self.min_gene_spinbox)
        min_layout.addStretch()
        
        # Max gene count
        max_layout = QHBoxLayout()
        max_layout.addWidget(QLabel("Maximum:"))
        self.max_gene_spinbox = QSpinBox()
        self.max_gene_spinbox.setMinimum(0)
        self.max_gene_spinbox.setMaximum(10000)
        self.max_gene_spinbox.setValue(1000)
        self.max_gene_spinbox.setFixedWidth(100)
        max_layout.addWidget(self.max_gene_spinbox)
        max_layout.addStretch()
        
        # Gene count 필터 활성화
        self.gene_count_enabled = QCheckBox("Enable gene count filtering")
        self.gene_count_enabled.setChecked(True)
        
        layout.addLayout(min_layout)
        layout.addLayout(max_layout)
        layout.addWidget(self.gene_count_enabled)
        
        return group
    
    def _create_description_group(self) -> QGroupBox:
        """Description 검색 그룹 생성"""
        group = QGroupBox("Description Search")
        layout = QVBoxLayout(group)
        
        # 검색 입력
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Contains:"))
        self.description_edit = QLineEdit()
        self.description_edit.setPlaceholderText("Enter keywords to search in term description...")
        search_layout.addWidget(self.description_edit)
        
        # Case sensitive 옵션
        self.case_sensitive_checkbox = QCheckBox("Case sensitive")
        self.case_sensitive_checkbox.setChecked(False)
        
        # Description 필터 활성화
        self.description_enabled = QCheckBox("Enable description filtering")
        self.description_enabled.setChecked(False)
        
        layout.addLayout(search_layout)
        layout.addWidget(self.case_sensitive_checkbox)
        layout.addWidget(self.description_enabled)
        
        return group
    
    def _create_buttons(self) -> QHBoxLayout:
        """버튼 레이아웃 생성"""
        layout = QHBoxLayout()
        
        # Reset 버튼
        reset_btn = QPushButton("Reset to Default")
        reset_btn.clicked.connect(self._reset_to_default)
        
        layout.addWidget(reset_btn)
        layout.addStretch()
        
        # OK / Cancel 버튼
        ok_btn = QPushButton("Apply Filter")
        cancel_btn = QPushButton("Cancel")
        
        ok_btn.clicked.connect(self._apply_filter)
        cancel_btn.clicked.connect(self.reject)
        
        ok_btn.setDefault(True)
        
        layout.addWidget(ok_btn)
        layout.addWidget(cancel_btn)
        
        return layout
    
    def _apply_filter(self):
        """필터 적용"""
        # 선택된 Ontology 확인
        ontologies = self.get_selected_ontologies()
        if not ontologies:
            QMessageBox.warning(
                self,
                "No Ontology Selected",
                "Please select at least one ontology type."
            )
            return
        
        # MainPresenter를 통해 필터링 실행
        parent = self.parent()
        if parent and hasattr(parent, 'presenter'):
            presenter = parent.presenter  # type: ignore
            
            presenter.filter_go_kegg_data(
                dataset=self.dataset,
                fdr_threshold=self.get_fdr_threshold(),
                ontologies=ontologies,
                direction=self.get_direction(),
                gene_count_range=self.get_gene_count_range(),
                description_filter=self.get_description_filter()
            )
            
            self.accept()
        else:
            QMessageBox.critical(
                self,
                "Error",
                "Cannot access presenter. Please try again."
            )
    
    def _select_all_ontologies(self):
        """모든 Ontology 선택"""
        self.bp_checkbox.setChecked(True)
        self.cc_checkbox.setChecked(True)
        self.mf_checkbox.setChecked(True)
        self.kegg_checkbox.setChecked(True)
    
    def _deselect_all_ontologies(self):
        """모든 Ontology 선택 해제"""
        self.bp_checkbox.setChecked(False)
        self.cc_checkbox.setChecked(False)
        self.mf_checkbox.setChecked(False)
        self.kegg_checkbox.setChecked(False)
    
    def _reset_to_default(self):
        """기본값으로 리셋"""
        # FDR
        self.fdr_input.setText("0.05")
        self.fdr_enabled.setChecked(True)
        
        # Ontology
        self._select_all_ontologies()
        
        # Direction
        self.all_radio.setChecked(True)
        
        # Gene count
        self.min_gene_spinbox.setValue(2)
        self.max_gene_spinbox.setValue(1000)
        self.gene_count_enabled.setChecked(True)
        
        # Description
        self.description_edit.clear()
        self.case_sensitive_checkbox.setChecked(False)
        self.description_enabled.setChecked(False)
    
    # Getter 메서드들
    def get_fdr_threshold(self) -> Optional[float]:
        """FDR 임계값 반환"""
        if self.fdr_enabled.isChecked():
            try:
                return float(self.fdr_input.text())
            except ValueError:
                return 0.05  # 기본값
        return None
    
    def get_selected_ontologies(self) -> List[str]:
        """선택된 Ontology 리스트 반환"""
        ontologies = []
        if self.bp_checkbox.isChecked():
            ontologies.append("BP")
        if self.cc_checkbox.isChecked():
            ontologies.append("CC")
        if self.mf_checkbox.isChecked():
            ontologies.append("MF")
        if self.kegg_checkbox.isChecked():
            ontologies.append("KEGG")
        return ontologies
    
    def get_direction(self) -> Optional[str]:
        """선택된 Direction 반환"""
        button_id = self.direction_group.checkedId()
        if button_id == 0:  # All
            return None
        elif button_id == 1:  # UP
            return "UP"
        elif button_id == 2:  # DOWN
            return "DOWN"
        elif button_id == 3:  # TOTAL
            return "TOTAL"
        return None
    
    def get_gene_count_range(self) -> Optional[tuple]:
        """Gene count 범위 반환 (min, max)"""
        if self.gene_count_enabled.isChecked():
            return (self.min_gene_spinbox.value(), self.max_gene_spinbox.value())
        return None
    
    def get_description_filter(self) -> Optional[tuple]:
        """Description 필터 반환 (keyword, case_sensitive)"""
        if self.description_enabled.isChecked() and self.description_edit.text().strip():
            return (self.description_edit.text().strip(), self.case_sensitive_checkbox.isChecked())
        return None
