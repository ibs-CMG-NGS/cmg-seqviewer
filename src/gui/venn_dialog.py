"""
Venn Diagram Dialog

2-3개 데이터셋 간의 유전자 overlap을 Venn diagram으로 시각화
"""

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
                            QLabel, QGroupBox, QComboBox, QDoubleSpinBox, QFormLayout)
from PyQt6.QtCore import Qt
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib_venn import venn2, venn3, venn2_circles, venn3_circles
import pandas as pd
import logging


class VennDiagramDialog(QDialog):
    """Venn Diagram 시각화 다이얼로그"""
    
    def __init__(self, datasets, parent=None):
        """
        Args:
            datasets: List of Dataset objects (2-3개)
        """
        super().__init__(parent)
        self.datasets = datasets
        self.logger = logging.getLogger(__name__)
        
        if len(datasets) < 2 or len(datasets) > 3:
            raise ValueError("Venn diagram requires 2-3 datasets")
        
        self.setWindowTitle(f"Venn Diagram - {len(datasets)} Datasets")
        self.setMinimumSize(900, 700)
        
        self._init_ui()
        self._plot()
    
    def _init_ui(self):
        """UI 초기화"""
        layout = QVBoxLayout(self)
        
        # 설정 패널
        settings_group = QGroupBox("Settings")
        settings_layout = QHBoxLayout()
        
        # 필터 기준 선택
        settings_layout.addWidget(QLabel("Filter by:"))
        self.filter_combo = QComboBox()
        self.filter_combo.addItems([
            "All Genes",
            "DEG only (|log2FC| ≥ 1, padj ≤ 0.05)",
            "Highly significant (|log2FC| ≥ 2, padj ≤ 0.01)",
            "Custom..."
        ])
        self.filter_combo.currentIndexChanged.connect(self._plot)
        settings_layout.addWidget(self.filter_combo)
        
        settings_layout.addStretch()
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
        
        button_layout.addStretch()
        layout.addLayout(button_layout)
    
    def _get_gene_sets(self):
        """각 데이터셋의 유전자 세트 가져오기"""
        gene_sets = []
        filter_type = self.filter_combo.currentIndex()
        
        for dataset in self.datasets:
            df = dataset.dataframe.copy()
            
            # 필터 적용
            if filter_type == 1:  # DEG only
                if 'log2FC' in df.columns and 'padj' in df.columns:
                    df = df[(abs(df['log2FC']) >= 1.0) & (df['padj'] <= 0.05)]
                elif 'log2fc' in df.columns and 'adj_pvalue' in df.columns:
                    df = df[(abs(df['log2fc']) >= 1.0) & (df['adj_pvalue'] <= 0.05)]
            elif filter_type == 2:  # Highly significant
                if 'log2FC' in df.columns and 'padj' in df.columns:
                    df = df[(abs(df['log2FC']) >= 2.0) & (df['padj'] <= 0.01)]
                elif 'log2fc' in df.columns and 'adj_pvalue' in df.columns:
                    df = df[(abs(df['log2fc']) >= 2.0) & (df['adj_pvalue'] <= 0.01)]
            
            # gene_id 수집 (symbol 우선)
            if 'symbol' in df.columns:
                genes = set(df['symbol'].dropna().unique())
            elif 'gene_id' in df.columns:
                genes = set(df['gene_id'].dropna().unique())
            else:
                genes = set()
            
            gene_sets.append(genes)
            self.logger.info(f"Dataset '{dataset.name}': {len(genes)} genes")
        
        return gene_sets
    
    def _plot(self):
        """Venn diagram 그리기"""
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        
        # 유전자 세트 가져오기
        gene_sets = self._get_gene_sets()
        
        if len(self.datasets) == 2:
            # 2-way Venn
            venn = venn2(
                gene_sets,
                set_labels=[ds.name for ds in self.datasets],
                ax=ax,
                alpha=0.6
            )
            
            # 원 테두리
            venn2_circles(gene_sets, ax=ax, linewidth=1.5)
            
            # 색상 설정
            if venn.get_patch_by_id('10'):
                venn.get_patch_by_id('10').set_color('#ff9999')
            if venn.get_patch_by_id('01'):
                venn.get_patch_by_id('01').set_color('#9999ff')
            if venn.get_patch_by_id('11'):
                venn.get_patch_by_id('11').set_color('#cc99cc')
        
        elif len(self.datasets) == 3:
            # 3-way Venn
            venn = venn3(
                gene_sets,
                set_labels=[ds.name for ds in self.datasets],
                ax=ax,
                alpha=0.6
            )
            
            # 원 테두리
            venn3_circles(gene_sets, ax=ax, linewidth=1.5)
            
            # 색상 설정
            colors = {
                '100': '#ff9999',
                '010': '#9999ff',
                '001': '#99ff99',
                '110': '#ffcc99',
                '101': '#ffff99',
                '011': '#99ffff',
                '111': '#cccccc'
            }
            
            for region_id, color in colors.items():
                patch = venn.get_patch_by_id(region_id)
                if patch:
                    patch.set_color(color)
        
        # 제목 및 통계
        filter_name = self.filter_combo.currentText()
        title = f"Gene Overlap - {filter_name}\n"
        
        # 공통/unique 유전자 통계
        if len(gene_sets) == 2:
            common = gene_sets[0] & gene_sets[1]
            unique_0 = gene_sets[0] - gene_sets[1]
            unique_1 = gene_sets[1] - gene_sets[0]
            
            title += f"Common: {len(common)} | "
            title += f"Unique to {self.datasets[0].name}: {len(unique_0)} | "
            title += f"Unique to {self.datasets[1].name}: {len(unique_1)}"
        
        elif len(gene_sets) == 3:
            common = gene_sets[0] & gene_sets[1] & gene_sets[2]
            title += f"Common to all: {len(common)}"
        
        ax.set_title(title, fontsize=12, fontweight='bold', pad=20)
        
        self.figure.tight_layout()
        self.canvas.draw()
