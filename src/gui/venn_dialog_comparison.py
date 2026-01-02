"""
Venn Diagram Dialog for Comparison Sheet

Comparison sheet의 데이터를 기반으로 Venn diagram 생성
"""

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
                            QLabel, QGroupBox, QDoubleSpinBox, QFormLayout, QCheckBox)
from PyQt6.QtCore import Qt
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib_venn import venn2, venn3
import pandas as pd
import logging


class VennDiagramFromComparisonDialog(QDialog):
    """Comparison sheet에서 Venn Diagram 생성"""
    
    def __init__(self, comparison_df, parent=None):
        """
        Args:
            comparison_df: Comparison sheet의 DataFrame
                          (gene_id, symbol, Status, Found_in, Dataset1_log2FC, Dataset1_padj, ...)
        """
        super().__init__(parent)
        self.comparison_df = comparison_df
        self.logger = logging.getLogger(__name__)
        
        # Dataset 이름 추출 (컬럼명에서 '_log2FC'나 '_padj' 제거)
        self.dataset_names = []
        for col in comparison_df.columns:
            if col.endswith('_log2FC'):
                dataset_name = col.replace('_log2FC', '')
                if dataset_name not in self.dataset_names:
                    self.dataset_names.append(dataset_name)
        
        if len(self.dataset_names) < 2 or len(self.dataset_names) > 3:
            raise ValueError(f"Venn diagram requires 2-3 datasets, found {len(self.dataset_names)}")
        
        self.setWindowTitle(f"Venn Diagram - {len(self.dataset_names)} Datasets")
        self.setMinimumSize(900, 700)
        
        # 필터 설정 기본값
        self.apply_filter = False
        self.log2fc_threshold = 1.0
        self.padj_threshold = 0.05
        
        self._init_ui()
        self._plot()
    
    def _init_ui(self):
        """UI 초기화"""
        layout = QVBoxLayout(self)
        
        # 설정 패널
        settings_group = QGroupBox("Filter Settings")
        settings_layout = QFormLayout()
        
        # 필터 적용 체크박스
        self.filter_check = QCheckBox("Apply statistical filter")
        self.filter_check.setChecked(self.apply_filter)
        self.filter_check.stateChanged.connect(self._on_filter_changed)
        settings_layout.addRow("", self.filter_check)
        
        # Log2FC threshold
        self.log2fc_spin = QDoubleSpinBox()
        self.log2fc_spin.setRange(0.0, 10.0)
        self.log2fc_spin.setDecimals(2)
        self.log2fc_spin.setValue(self.log2fc_threshold)
        self.log2fc_spin.setSingleStep(0.1)
        self.log2fc_spin.setEnabled(False)
        self.log2fc_spin.valueChanged.connect(self._on_threshold_changed)
        settings_layout.addRow("|Log2FC| ≥:", self.log2fc_spin)
        
        # Padj threshold
        self.padj_spin = QDoubleSpinBox()
        self.padj_spin.setRange(0.0001, 1.0)
        self.padj_spin.setDecimals(4)
        self.padj_spin.setValue(self.padj_threshold)
        self.padj_spin.setSingleStep(0.01)
        self.padj_spin.setEnabled(False)
        self.padj_spin.valueChanged.connect(self._on_threshold_changed)
        settings_layout.addRow("Padj ≤:", self.padj_spin)
        
        settings_group.setLayout(settings_layout)
        layout.addWidget(settings_group)
        
        # Matplotlib Figure
        self.figure = Figure(figsize=(10, 8))
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self)
        
        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)
        
        # 버튼
        button_layout = QHBoxLayout()
        
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self._plot)
        button_layout.addWidget(refresh_btn)
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
    
    def _on_filter_changed(self):
        """필터 체크박스 변경 시"""
        self.apply_filter = self.filter_check.isChecked()
        self.log2fc_spin.setEnabled(self.apply_filter)
        self.padj_spin.setEnabled(self.apply_filter)
        self._plot()
    
    def _on_threshold_changed(self):
        """Threshold 변경 시"""
        self.log2fc_threshold = self.log2fc_spin.value()
        self.padj_threshold = self.padj_spin.value()
        if self.apply_filter:
            self._plot()
    
    def _plot(self):
        """Venn Diagram 그리기"""
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        
        # 각 데이터셋의 유전자 세트 생성
        gene_sets = {}
        
        for dataset_name in self.dataset_names:
            log2fc_col = f'{dataset_name}_log2FC'
            padj_col = f'{dataset_name}_padj'
            
            # 해당 데이터셋에 값이 있는 행 필터링
            df_subset = self.comparison_df[
                self.comparison_df[log2fc_col].notna() & 
                self.comparison_df[padj_col].notna()
            ].copy()
            
            # 통계 필터 적용 (옵션)
            if self.apply_filter:
                df_subset = df_subset[
                    (abs(df_subset[log2fc_col]) >= self.log2fc_threshold) &
                    (df_subset[padj_col] <= self.padj_threshold)
                ]
            
            # 유전자 세트 생성 (symbol 우선, 없으면 gene_id)
            genes = set()
            for _, row in df_subset.iterrows():
                gene_id = row.get('gene_id', '')
                symbol = row.get('symbol', '')
                identifier = symbol if symbol else gene_id
                if identifier:
                    genes.add(identifier)
            
            gene_sets[dataset_name] = genes
            self.logger.info(f"{dataset_name}: {len(genes)} genes")
        
        # Venn diagram 그리기
        try:
            if len(self.dataset_names) == 2:
                sets = [gene_sets[name] for name in self.dataset_names]
                venn = venn2(sets, set_labels=self.dataset_names, ax=ax)
            else:  # 3개
                sets = [gene_sets[name] for name in self.dataset_names]
                venn = venn3(sets, set_labels=self.dataset_names, ax=ax)
            
            # 타이틀
            if self.apply_filter:
                title = f"Venn Diagram\n(|Log2FC| ≥ {self.log2fc_threshold}, Padj ≤ {self.padj_threshold})"
            else:
                title = "Venn Diagram\n(All genes in comparison)"
            ax.set_title(title, fontsize=14, fontweight='bold')
            
        except Exception as e:
            self.logger.error(f"Failed to create Venn diagram: {e}")
            ax.text(0.5, 0.5, f'Error creating Venn diagram:\n{str(e)}', 
                   ha='center', va='center', fontsize=12, transform=ax.transAxes)
        
        self.figure.tight_layout()
        self.canvas.draw()
