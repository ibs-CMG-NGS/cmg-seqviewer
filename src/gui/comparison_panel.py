"""
비교 분석 패널
여러 데이터셋을 선택하여 비교 분석 수행
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QPushButton, QListWidget, QLabel, QComboBox,
    QCheckBox, QAbstractItemView
)
from PyQt6.QtCore import pyqtSignal
from typing import List


class ComparisonPanel(QWidget):
    """데이터셋 비교 분석 패널"""
    
    # 시그널 정의
    compare_requested = pyqtSignal(list, str)  # (선택된 데이터셋 리스트, 비교 타입)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
        
    def _init_ui(self):
        """UI 초기화"""
        layout = QVBoxLayout(self)
        
        # === Dataset 선택 영역 ===
        dataset_group = QGroupBox("Select Datasets to Compare")
        dataset_layout = QVBoxLayout()
        
        # 안내 레이블
        info_label = QLabel("Select 2 or more datasets for comparison:")
        dataset_layout.addWidget(info_label)
        
        # 데이터셋 리스트 (다중 선택 가능)
        self.dataset_list = QListWidget()
        self.dataset_list.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        self.dataset_list.setMaximumHeight(150)
        self.dataset_list.itemSelectionChanged.connect(self._update_status)  # 선택 변경 시 상태 업데이트
        dataset_layout.addWidget(self.dataset_list)
        
        # 선택 도우미 버튼
        button_layout = QHBoxLayout()
        self.select_all_btn = QPushButton("Select All")
        self.clear_selection_btn = QPushButton("Clear Selection")
        self.select_all_btn.clicked.connect(self._on_select_all)
        self.clear_selection_btn.clicked.connect(self._on_clear_selection)
        button_layout.addWidget(self.select_all_btn)
        button_layout.addWidget(self.clear_selection_btn)
        button_layout.addStretch()
        dataset_layout.addLayout(button_layout)
        
        dataset_group.setLayout(dataset_layout)
        layout.addWidget(dataset_group)
        
        # === 비교 타입 선택 영역 ===
        comparison_group = QGroupBox("Comparison Type")
        comparison_layout = QVBoxLayout()
        
        self.comparison_type = QComboBox()
        self.comparison_type.addItems([
            "Gene List Filtering",
            "Statistics Filtering"
        ])
        self.comparison_type.currentIndexChanged.connect(self._on_comparison_type_changed)
        comparison_layout.addWidget(self.comparison_type)
        
        # 비교 타입 설명
        self.comparison_desc = QLabel()
        self.comparison_desc.setWordWrap(True)
        self.comparison_desc.setStyleSheet("color: #666; font-size: 10pt;")
        self._update_comparison_description()
        comparison_layout.addWidget(self.comparison_desc)
        
        comparison_group.setLayout(comparison_layout)
        layout.addWidget(comparison_group)
        
        # === 옵션 영역 ===
        options_group = QGroupBox("Options")
        options_layout = QVBoxLayout()
        
        # 공통 유전자만 표시
        self.common_genes_only = QCheckBox("Show common genes only (intersection)")
        self.common_genes_only.setChecked(False)
        self.common_genes_only.setToolTip("Display only genes found in ALL selected datasets")
        self.common_genes_only.toggled.connect(self._on_common_genes_toggled)
        options_layout.addWidget(self.common_genes_only)
        
        # 유니크 유전자 포함
        self.include_unique = QCheckBox("Include unique genes (union)")
        self.include_unique.setChecked(True)
        self.include_unique.setToolTip("Include genes found in any dataset")
        self.include_unique.toggled.connect(self._on_include_unique_toggled)
        options_layout.addWidget(self.include_unique)
        
        options_group.setLayout(options_layout)
        layout.addWidget(options_group)
        
        # === 실행 버튼 ===
        self.compare_btn = QPushButton("Start Comparison")
        self.compare_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 8px;
                font-weight: bold;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.compare_btn.clicked.connect(self._on_compare_clicked)
        layout.addWidget(self.compare_btn)
        
        # === 상태 표시 ===
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: #666; font-style: italic;")
        layout.addWidget(self.status_label)
        
        layout.addStretch()
    
    def update_dataset_list(self, dataset_names: List[str]):
        """
        데이터셋 리스트 업데이트
        
        Args:
            dataset_names: 데이터셋 이름 리스트
        """
        self.dataset_list.clear()
        self.dataset_list.addItems(dataset_names)
        self._update_status()
    
    def _on_select_all(self):
        """모든 데이터셋 선택"""
        self.dataset_list.selectAll()
        self._update_status()
    
    def _on_clear_selection(self):
        """선택 해제"""
        self.dataset_list.clearSelection()
        self._update_status()
    
    def _on_comparison_type_changed(self):
        """비교 타입 변경 시"""
        self._update_comparison_description()
        self._update_status()
    
    def _update_comparison_description(self):
        """비교 타입 설명 업데이트"""
        descriptions = {
            0: "Apply the same gene list filter to multiple datasets and compare results side by side.",
            1: "Apply the same statistical criteria (log2FC, p-value) to multiple datasets and compare."
        }
        current_index = self.comparison_type.currentIndex()
        self.comparison_desc.setText(descriptions.get(current_index, ""))
    
    def _update_status(self):
        """상태 업데이트"""
        selected_count = len(self.dataset_list.selectedItems())
        
        # 모든 비교 타입은 2개 이상 필요
        required = "2+"
        valid = selected_count >= 2
        
        # 상태 메시지 및 버튼 활성화
        if selected_count == 0:
            self.status_label.setText("No datasets selected")
            self.compare_btn.setEnabled(False)
        elif not valid:
            self.status_label.setText(f"⚠️ This comparison requires {required} datasets (selected: {selected_count})")
            self.compare_btn.setEnabled(False)
        else:
            self.status_label.setText(f"✓ {selected_count} datasets selected - Ready to compare")
            self.compare_btn.setEnabled(True)
    
    def _on_compare_clicked(self):
        """비교 실행 버튼 클릭"""
        selected_items = self.dataset_list.selectedItems()
        selected_datasets = [item.text() for item in selected_items]
        comparison_type = self.comparison_type.currentText()
        
        if len(selected_datasets) >= 2:
            # 비교 타입 매핑
            type_mapping = {
                "Gene List Filtering": "gene_list",
                "Statistics Filtering": "statistics"
            }
            
            comparison_key = type_mapping.get(comparison_type, "gene_list")
            self.compare_requested.emit(selected_datasets, comparison_key)
    
    def _on_common_genes_toggled(self, checked):
        """공통 유전자 옵션 토글 - exclusive 처리"""
        if checked:
            # common_genes_only가 체크되면 include_unique 해제
            self.include_unique.blockSignals(True)
            self.include_unique.setChecked(False)
            self.include_unique.blockSignals(False)
    
    def _on_include_unique_toggled(self, checked):
        """유니크 유전자 포함 옵션 토글 - exclusive 처리"""
        if checked:
            # include_unique가 체크되면 common_genes_only 해제
            self.common_genes_only.blockSignals(True)
            self.common_genes_only.setChecked(False)
            self.common_genes_only.blockSignals(False)
