"""
GO/KEGG Dot Plot Visualization Dialog
"""

from typing import Optional
import pandas as pd
import numpy as np
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox,
    QLabel, QSpinBox, QComboBox, QPushButton,
    QCheckBox, QDoubleSpinBox, QMessageBox, QFormLayout, QLineEdit
)
from PyQt6.QtCore import Qt
import matplotlib
matplotlib.use('QtAgg')
# matplotlib 로깅 레벨 설정 (debug 로그 숨김)
import logging
logging.getLogger('matplotlib').setLevel(logging.WARNING)
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
try:
    from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
except ImportError:
    from matplotlib.backends.backend_qt import NavigationToolbar2QT as NavigationToolbar  # type: ignore
from matplotlib.figure import Figure

from models.data_models import Dataset
from models.standard_columns import StandardColumns


class GODotPlotDialog(QDialog):
    """GO/KEGG Dot Plot 다이얼로그"""
    
    def __init__(self, dataset: Dataset, parent=None):
        super().__init__(parent)
        self.dataset = dataset
        self.df = dataset.dataframe.copy() if dataset.dataframe is not None else pd.DataFrame()
        
        self.setWindowTitle("GO/KEGG Dot Plot")
        self.setMinimumSize(1000, 800)
        
        # Matplotlib figure with constrained_layout for better auto-adjustment
        self.figure = Figure(figsize=(10, 8), constrained_layout=False)
        self.canvas = FigureCanvas(self.figure)
        
        self._init_ui()
        
        # 초기 플롯 생성
        self._update_plot()
    
    def _init_ui(self):
        """UI 초기화"""
        main_layout = QHBoxLayout(self)  # 전체를 좌우 배열로 변경
        
        # 왼쪽: 설정 패널들
        left_panel = QVBoxLayout()
        
        # 설정 패널
        settings_group = QGroupBox("Plot Settings")
        settings_layout = QFormLayout()  # HBoxLayout에서 FormLayout으로 변경
        
        # Top N terms
        self.top_n_spin = QSpinBox()
        self.top_n_spin.setRange(5, 100)
        self.top_n_spin.setValue(20)
        self.top_n_spin.valueChanged.connect(self._update_plot)
        settings_layout.addRow("Top N terms:", self.top_n_spin)
        
        # X-axis는 Gene Ratio로 고정 (UI에서 제거)
        # Sort by는 Gene Ratio descending으로 고정 (UI에서 제거)
        # 큰 값이 위, 작은 값이 아래로 표시
        
        # Color와 Size는 고정 (UI에서 제거, 내부적으로 FDR과 Gene Count 사용)
        # Color: FDR (고정)
        # Size: Gene Count (고정)
        
        settings_group.setLayout(settings_layout)
        left_panel.addWidget(settings_group)
        
        # Color Bar 설정 패널
        colorbar_group = QGroupBox("Color Bar Settings")
        colorbar_layout = QFormLayout()
        
        # Color palette 선택
        self.palette_combo = QComboBox()
        self.palette_combo.addItems([
            "YlOrRd", "RdYlGn_r", "viridis", "plasma", 
            "coolwarm", "seismic", "Spectral_r", "RdBu_r"
        ])
        self.palette_combo.currentTextChanged.connect(self._update_plot)
        colorbar_layout.addRow("Color Palette:", self.palette_combo)
        
        # Color bar 범위 (FDR)
        color_range_layout = QHBoxLayout()
        self.color_min_spin = QDoubleSpinBox()
        self.color_min_spin.setRange(0, 1)
        self.color_min_spin.setDecimals(4)
        self.color_min_spin.setValue(0)
        self.color_min_spin.setSingleStep(0.01)
        self.color_min_spin.valueChanged.connect(self._update_plot)
        color_range_layout.addWidget(QLabel("Min:"))
        color_range_layout.addWidget(self.color_min_spin)
        
        self.color_max_spin = QDoubleSpinBox()
        self.color_max_spin.setRange(0, 1)
        self.color_max_spin.setDecimals(4)
        self.color_max_spin.setValue(0.05)
        self.color_max_spin.setSingleStep(0.01)
        self.color_max_spin.valueChanged.connect(self._update_plot)
        color_range_layout.addWidget(QLabel("Max:"))
        color_range_layout.addWidget(self.color_max_spin)
        
        # Auto 버튼
        color_auto_btn = QPushButton("Auto")
        color_auto_btn.setMaximumWidth(60)
        color_auto_btn.clicked.connect(self._auto_color_range)
        color_range_layout.addWidget(color_auto_btn)
        
        colorbar_layout.addRow("FDR Range:", color_range_layout)
        
        colorbar_group.setLayout(colorbar_layout)
        left_panel.addWidget(colorbar_group)
        
        # Plot Customization 패널
        custom_group = QGroupBox("Plot Customization")
        custom_layout = QFormLayout()
        
        # Title
        self.title_edit = QLineEdit("GO/KEGG Enrichment Dot Plot")
        self.title_edit.textChanged.connect(self._update_plot)
        custom_layout.addRow("Title:", self.title_edit)
        
        # X Label
        self.xlabel_edit = QLineEdit("Gene Ratio")
        self.xlabel_edit.textChanged.connect(self._update_plot)
        custom_layout.addRow("X Label:", self.xlabel_edit)
        
        # Y Label
        self.ylabel_edit = QLineEdit("GO/KEGG Terms")
        self.ylabel_edit.textChanged.connect(self._update_plot)
        custom_layout.addRow("Y Label:", self.ylabel_edit)
        
        # Figure size
        size_layout = QHBoxLayout()
        self.width_spin = QSpinBox()
        self.width_spin.setRange(6, 20)
        self.width_spin.setValue(12)
        self.width_spin.valueChanged.connect(self._on_figure_size_changed)
        size_layout.addWidget(QLabel("Width:"))
        size_layout.addWidget(self.width_spin)
        
        self.height_spin = QSpinBox()
        self.height_spin.setRange(4, 16)
        self.height_spin.setValue(8)
        self.height_spin.valueChanged.connect(self._on_figure_size_changed)
        size_layout.addWidget(QLabel("Height:"))
        size_layout.addWidget(self.height_spin)
        custom_layout.addRow("Figure Size (inches):", size_layout)
        
        custom_group.setLayout(custom_layout)
        left_panel.addWidget(custom_group)
        
        left_panel.addStretch()  # 아래 여백
        
        # 왼쪽 패널을 메인 레이아웃에 추가
        main_layout.addLayout(left_panel)
        
        # 오른쪽: Plot 영역
        right_panel = QVBoxLayout()
        
        # Matplotlib canvas
        right_panel.addWidget(self.canvas)
        
        # Navigation toolbar
        toolbar = NavigationToolbar(self.canvas, self)
        right_panel.addWidget(toolbar)
        
        # 버튼
        button_layout = QHBoxLayout()
        
        refresh_btn = QPushButton("Refresh Plot")
        refresh_btn.clicked.connect(self._update_plot)
        button_layout.addWidget(refresh_btn)
        
        save_btn = QPushButton("Save Figure")
        save_btn.clicked.connect(self._save_figure)
        button_layout.addWidget(save_btn)
        
        export_btn = QPushButton("Export Data")
        export_btn.clicked.connect(self._export_data)
        button_layout.addWidget(export_btn)
        
        button_layout.addStretch()
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)
        
        right_panel.addLayout(button_layout)
        
        # 오른쪽 패널을 메인 레이아웃에 추가
        main_layout.addLayout(right_panel, stretch=3)  # 오른쪽을 더 크게
    
    def _on_figure_size_changed(self):
        """Figure 크기 변경 시 처리"""
        width = self.width_spin.value()
        height = self.height_spin.value()
        self.figure.set_size_inches(width, height)
        self.canvas.draw()
    
    def _get_filtered_data(self) -> pd.DataFrame:
        """데이터 반환 (필터링 제거 - filtered by statistics 결과만 사용)"""
        return self.df.copy()
    
    def _calculate_gene_ratio(self, df: pd.DataFrame) -> pd.Series:
        """
        Gene Ratio 계산
        
        GENE_RATIO 컬럼이 있으면 파싱 (예: "10/100" -> 0.1)
        없으면 GENE_COUNT를 최대값으로 나눔
        """
        if StandardColumns.GENE_RATIO in df.columns:
            # "10/100" 형식 파싱
            def parse_ratio(ratio_str):
                try:
                    if pd.isna(ratio_str):
                        return 0.0
                    if isinstance(ratio_str, (int, float)):
                        return float(ratio_str)
                    # "10/100" 형식 파싱
                    parts = str(ratio_str).split('/')
                    if len(parts) == 2:
                        numerator = float(parts[0])
                        denominator = float(parts[1])
                        return numerator / denominator if denominator > 0 else 0.0
                    return 0.0
                except:
                    return 0.0
            
            return df[StandardColumns.GENE_RATIO].apply(parse_ratio)
        
        elif StandardColumns.GENE_COUNT in df.columns:
            # Gene Count / Background (임시로 max 사용)
            max_count = df[StandardColumns.GENE_COUNT].max()
            if max_count > 0:
                return df[StandardColumns.GENE_COUNT] / max_count
        
        return pd.Series(0.5, index=df.index)  # 기본값
    
    def _auto_color_range(self):
        """Color bar 범위를 데이터에 맞게 자동 설정"""
        df = self._get_filtered_data()
        if StandardColumns.FDR in df.columns:
            fdr_values = df[StandardColumns.FDR].dropna()
            if len(fdr_values) > 0:
                self.color_min_spin.setValue(float(fdr_values.min()))
                self.color_max_spin.setValue(float(fdr_values.max()))
                self._update_plot()
    
    def _update_plot(self):
        """플롯 업데이트"""
        self.figure.clear()
        
        # 필터링된 데이터
        df = self._get_filtered_data()
        
        if len(df) == 0:
            ax = self.figure.add_subplot(111)
            ax.text(0.5, 0.5, 'No data to display\nAdjust filters',
                   ha='center', va='center', fontsize=14)
            self.canvas.draw()
            return
        
        # NaN 값이 있는 행 제거 (Description, FDR, Gene Count 등 필수 컬럼)
        required_cols = [StandardColumns.DESCRIPTION]
        if StandardColumns.FDR in df.columns:
            required_cols.append(StandardColumns.FDR)
        if StandardColumns.GENE_COUNT in df.columns:
            required_cols.append(StandardColumns.GENE_COUNT)
        
        df = df.dropna(subset=required_cols)
        
        if len(df) == 0:
            ax = self.figure.add_subplot(111)
            ax.text(0.5, 0.5, 'No valid data to display\n(NaN values removed)',
                   ha='center', va='center', fontsize=14)
            self.canvas.draw()
            return
        
        # Sorting - Gene Ratio로 정렬 (큰 값을 선택하기 위해 descending)
        # Gene Ratio 계산
        gene_ratios = self._calculate_gene_ratio(df)
        df = df.copy()
        df['_gene_ratio'] = gene_ratios
        
        # 큰 값부터 정렬하여 Top N 선택
        df = df.sort_values('_gene_ratio', ascending=False)  # 내림차순 정렬
        
        # Top N terms 선택
        top_n = self.top_n_spin.value()
        df = df.head(top_n)
        
        # Y축 표시를 위해 다시 오름차순 정렬 (작은 값이 아래, 큰 값이 위)
        df = df.sort_values('_gene_ratio', ascending=True)
        
        # X-axis 데이터 - Gene Ratio 고정
        x_data = df['_gene_ratio']
        x_label = "Gene Ratio"
        
        # Y-axis (Term descriptions)
        if StandardColumns.DESCRIPTION in df.columns:
            y_labels = df[StandardColumns.DESCRIPTION].to_list()
        else:
            y_labels = [f"Term {i+1}" for i in range(len(df))]
        
        # Truncate long descriptions (convert to string to handle NaN/float)
        y_labels = [str(label)[:60] + '...' if len(str(label)) > 60 else str(label) 
                   for label in y_labels]
        
        y_data = np.arange(len(y_labels))
        
        # Color 데이터 (FDR로 고정)
        if StandardColumns.FDR in df.columns:
            colors = df[StandardColumns.FDR]
            cmap = self.palette_combo.currentText()
            color_label = "FDR"
            # Color bar 범위 설정
            vmin = self.color_min_spin.value()
            vmax = self.color_max_spin.value()
        else:
            colors = 'steelblue'
            cmap = None
            color_label = None
            vmin = None
            vmax = None
        
        # Size 데이터 (Gene Count로 고정)
        if StandardColumns.GENE_COUNT in df.columns:
            sizes = df[StandardColumns.GENE_COUNT] * 5  # 스케일 조정
            sizes = sizes.clip(lower=50, upper=500)  # 최소/최대 크기 제한
        else:
            sizes = 100
        
        # Plotting
        ax = self.figure.add_subplot(111)
        
        scatter = ax.scatter(x_data, y_data, c=colors, s=sizes, 
                           cmap=cmap, alpha=0.7, edgecolors='black', linewidth=0.5,
                           vmin=vmin, vmax=vmax)
        
        # Y label 폰트 크기 동적 조정 (term 개수에 따라)
        n_terms = len(df)
        if n_terms <= 10:
            ylabel_fontsize = 9
        elif n_terms <= 20:
            ylabel_fontsize = 8
        elif n_terms <= 30:
            ylabel_fontsize = 7
        else:
            ylabel_fontsize = 6
        
        # Axes 설정
        ax.set_yticks(y_data)
        ax.set_yticklabels(y_labels, fontsize=ylabel_fontsize)
        ax.set_xlabel(self.xlabel_edit.text(), fontsize=11, fontweight='bold')
        ax.set_ylabel(self.ylabel_edit.text(), fontsize=11, fontweight='bold')
        ax.set_title(self.title_edit.text(), fontsize=13, fontweight='bold')
        
        # Grid
        ax.grid(axis='x', alpha=0.3, linestyle='--')
        
        # Colorbar (FDR) - 상단에 배치 (shrink으로 크기 조절, anchor로 위치 지정)
        if cmap is not None and color_label is not None:
            cbar = self.figure.colorbar(scatter, ax=ax, shrink=0.5, pad=0.02, anchor=(0, 1.0))
            cbar.set_label(color_label, fontsize=10)
        
        # Size legend (Gene Count) - Colorbar 아래에 배치
        if StandardColumns.GENE_COUNT in df.columns:
            from matplotlib.lines import Line2D
            # 전체 데이터셋의 gene count 범위를 기준으로 bin 계산 (가능한 경우)
            if self.dataset and self.dataset.dataframe is not None:
                full_gene_counts = self.dataset.dataframe[StandardColumns.GENE_COUNT]
                min_count = int(full_gene_counts.min())
                max_count = int(full_gene_counts.max())
            else:
                # Dataset이 없으면 현재 표시된 데이터 사용
                gene_counts = df[StandardColumns.GENE_COUNT]
                min_count = int(gene_counts.min())
                max_count = int(gene_counts.max())
            
            # 범주화 기준: 10, 50, 100, 200, 500, 1000...
            def get_representative_bins(min_val, max_val):
                """min과 max 사이에서 3개의 대표 bin 선택"""
                bins = [10, 50, 100, 200, 500, 1000, 2000, 5000, 10000]
                
                # min_val보다 크거나 같고 max_val보다 작거나 같은 bins 선택
                valid_bins = [b for b in bins if min_val <= b <= max_val]
                
                if len(valid_bins) == 0:
                    # valid bins가 없으면 실제 데이터의 min, mid, max 사용
                    mid_val = (min_val + max_val) // 2
                    return [min_val, mid_val, max_val]
                elif len(valid_bins) == 1:
                    # 1개만 있으면 min, valid_bin, max (3개로 확장)
                    bin_val = valid_bins[0]
                    if min_val < bin_val < max_val:
                        return [min_val, bin_val, max_val]
                    elif bin_val == min_val:
                        mid_val = (min_val + max_val) // 2
                        return [min_val, mid_val, max_val]
                    else:  # bin_val == max_val
                        mid_val = (min_val + max_val) // 2
                        return [min_val, mid_val, max_val]
                elif len(valid_bins) == 2:
                    # 2개 있으면 두 bins 사용 + max 값
                    # 만약 max_val이 두번째 bin과 같으면 그대로, 아니면 max_val 추가
                    if valid_bins[1] == max_val:
                        # min, bin[0], bin[1](=max)
                        return [min_val, valid_bins[0], valid_bins[1]]
                    else:
                        # bin[0], bin[1], max
                        return [valid_bins[0], valid_bins[1], max_val]
                else:
                    # 3개 이상이면 첫번째, 중간, 마지막 선택
                    mid_idx = len(valid_bins) // 2
                    return [valid_bins[0], valid_bins[mid_idx], valid_bins[-1]]
            
            representative_counts = get_representative_bins(min_count, max_count)
            # self.logger.info(f"Gene count range: {min_count}-{max_count}, selected bins: {representative_counts}")
            
            # Scatter plot과 동일한 크기 계산
            def size_to_markersize(count):
                """Gene count를 markersize로 변환 (scatter plot과 동일한 방식)"""
                # scatter에서 s=count*5 사용하고, 50-500 범위로 제한
                scatter_size = count * 5
                scatter_size = min(max(scatter_size, 50), 500)
                # markersize는 scatter size의 제곱근에 비례 (matplotlib 규칙)
                # 하지만 legend에서는 실제 크기를 보여주기 위해 비례하게 조정
                return np.sqrt(scatter_size) / 2  # /2는 legend 크기 조정용
            
            legend_elements = [
                Line2D([0], [0], marker='o', color='w', markerfacecolor='gray', 
                      markersize=size_to_markersize(representative_counts[0]), 
                      label=f'{representative_counts[0]} genes',
                      markeredgecolor='black', markeredgewidth=0.5),
                Line2D([0], [0], marker='o', color='w', markerfacecolor='gray',
                      markersize=size_to_markersize(representative_counts[1]), 
                      label=f'{representative_counts[1]} genes',
                      markeredgecolor='black', markeredgewidth=0.5),
                Line2D([0], [0], marker='o', color='w', markerfacecolor='gray',
                      markersize=size_to_markersize(representative_counts[2]), 
                      label=f'{representative_counts[2]} genes',
                      markeredgecolor='black', markeredgewidth=0.5)
            ]
            # Gene count legend를 하단에 배치 (colorbar와 겹치지 않도록)
            ax.legend(handles=legend_elements, title='Gene Count', 
                     loc='upper left', fontsize=8, framealpha=0.9, 
                     bbox_to_anchor=(1.02, 0.20))
        
        # Layout 조정 - tight_layout 사용하여 자동으로 여백 조정
        try:
            # tight_layout으로 자동 조정 시도
            self.figure.tight_layout(rect=[0, 0, 0.85, 1])  # rect로 오른쪽 15% 공간 확보
        except Exception as e:
            # tight_layout 실패 시 수동 조정
            # Y label의 최대 길이에 따라 여백 계산
            if len(y_labels) > 0:
                max_label_len = max(len(str(label)) for label in y_labels)
                # 더 큰 비율로 조정 (최소 30%, 최대 50%)
                # 문자 개수와 폰트 크기를 고려
                base_margin = 0.30
                char_factor = max_label_len * 0.004  # 문자당 0.4%
                left_margin = min(0.50, base_margin + char_factor)
            else:
                left_margin = 0.30
            self.figure.subplots_adjust(left=left_margin, right=0.85)
        
        self.canvas.draw()
    
    def _save_figure(self):
        """Figure 저장"""
        from PyQt6.QtWidgets import QFileDialog
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Figure",
            f"go_dot_plot_{self.dataset.name}.png",
            "PNG Files (*.png);;PDF Files (*.pdf);;SVG Files (*.svg);;All Files (*)"
        )
        
        if file_path:
            self.figure.savefig(file_path, dpi=300, bbox_inches='tight')
            QMessageBox.information(self, "Success", f"Figure saved to:\n{file_path}")
    
    def _export_data(self):
        """데이터 내보내기"""
        from PyQt6.QtWidgets import QFileDialog
        
        df = self._get_filtered_data()
        top_n = self.top_n_spin.value()
        
        if StandardColumns.FDR in df.columns:
            df = df.nsmallest(top_n, StandardColumns.FDR)
        else:
            df = df.head(top_n)
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Data",
            f"go_dot_plot_data_{self.dataset.name}.csv",
            "CSV Files (*.csv);;Excel Files (*.xlsx);;All Files (*)"
        )
        
        if file_path:
            if file_path.endswith('.xlsx'):
                df.to_excel(file_path, index=False)
            else:
                df.to_csv(file_path, index=False)
            
            QMessageBox.information(self, "Success", f"Data exported to:\n{file_path}")
