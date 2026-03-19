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
        
        # X-axis 선택: Gene Ratio 또는 Fold Enrichment
        self.x_axis_combo = QComboBox()
        self.x_axis_combo.addItems(["Gene Ratio", "Fold Enrichment"])
        self.x_axis_combo.currentTextChanged.connect(self._on_x_axis_changed)
        settings_layout.addRow("X-axis:", self.x_axis_combo)

        # Dot Size 선택
        self.size_combo = QComboBox()
        self.size_combo.addItems(["Gene Count", "Gene Ratio", "Fold Enrichment"])
        self.size_combo.currentTextChanged.connect(self._update_plot)
        settings_layout.addRow("Dot Size:", self.size_combo)
        
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
    
    def _on_x_axis_changed(self, text: str):
        """X-axis 콤보 변경 시 xlabel_edit 자동 동기화 후 replot"""
        self.xlabel_edit.blockSignals(True)
        self.xlabel_edit.setText(text)
        self.xlabel_edit.blockSignals(False)
        self._update_plot()

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
        
        # Sorting - 선택된 X축 값 기준으로 정렬
        # Gene Ratio 계산 (정렬 및 Gene Ratio 모드에 사용)
        gene_ratios = self._calculate_gene_ratio(df)
        df = df.copy()
        df['_gene_ratio'] = gene_ratios

        # Fold Enrichment 컬럼 준비
        x_axis_type = self.x_axis_combo.currentText()
        if x_axis_type == "Fold Enrichment" and StandardColumns.FOLD_ENRICHMENT in df.columns:
            df['_x_val'] = pd.to_numeric(df[StandardColumns.FOLD_ENRICHMENT], errors='coerce').fillna(0)
        else:
            df['_x_val'] = df['_gene_ratio']

        # 큰 값부터 정렬하여 Top N 선택
        df = df.sort_values('_x_val', ascending=False)
        
        # Top N terms 선택
        top_n = self.top_n_spin.value()
        df = df.head(top_n)
        
        # Y축 표시를 위해 다시 오름차순 정렬 (작은 값이 아래, 큰 값이 위)
        df = df.sort_values('_x_val', ascending=True)
        
        # X-axis 데이터
        x_data = df['_x_val']
        x_label = x_axis_type
        
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
        
        # Size 데이터 (Dot Size 콤보 선택에 따라)
        size_mode = self.size_combo.currentText()
        if size_mode == "Gene Count" and StandardColumns.GENE_COUNT in df.columns:
            raw_sizes = df[StandardColumns.GENE_COUNT]
            sizes = (raw_sizes * 5).clip(lower=50, upper=500)
            size_legend_unit = "genes"
        elif size_mode == "Gene Ratio":
            raw_sizes = df['_gene_ratio']
            # Gene Ratio는 0~1 사이 → 50~500 으로 정규화
            r_min, r_max = raw_sizes.min(), raw_sizes.max()
            if r_max > r_min:
                sizes = 50 + (raw_sizes - r_min) / (r_max - r_min) * 450
            else:
                sizes = pd.Series(200, index=df.index)
            size_legend_unit = "ratio"
        elif size_mode == "Fold Enrichment" and StandardColumns.FOLD_ENRICHMENT in df.columns:
            raw_sizes = pd.to_numeric(df[StandardColumns.FOLD_ENRICHMENT], errors='coerce').fillna(0)
            fe_min, fe_max = raw_sizes.min(), raw_sizes.max()
            if fe_max > fe_min:
                sizes = 50 + (raw_sizes - fe_min) / (fe_max - fe_min) * 450
            else:
                sizes = pd.Series(200, index=df.index)
            size_legend_unit = "x"
        else:
            # fallback: 고정 크기
            raw_sizes = None
            sizes = 100
            size_legend_unit = None
        
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
        
        # Size legend - Dot Size 선택에 따라 legend 표시
        if raw_sizes is not None and size_legend_unit is not None:
            from matplotlib.lines import Line2D

            s_vals = raw_sizes.dropna()
            if len(s_vals) == 0:
                s_vals = pd.Series([1.0])
            sv_min = float(s_vals.min())
            sv_max = float(s_vals.max())
            sv_mid = (sv_min + sv_max) / 2

            def _scatter_s(val):
                """원래 sizes 계산과 동일한 방법으로 scatter s값 반환"""
                if size_mode == "Gene Count":
                    return min(max(val * 5, 50), 500)
                else:
                    rng = sv_max - sv_min
                    if rng > 0:
                        return 50 + (val - sv_min) / rng * 450
                    return 200

            def _legend_ms(val):
                return np.sqrt(_scatter_s(val)) / 2

            if size_mode == "Gene Count":
                # 정수 bin 표시
                def get_bins(lo, hi):
                    bins = [10, 50, 100, 200, 500, 1000, 2000, 5000, 10000]
                    valid = [b for b in bins if lo <= b <= hi]
                    if not valid:
                        mid = (lo + hi) // 2
                        return [lo, mid, hi]
                    if len(valid) == 1:
                        mid = (lo + hi) // 2
                        return [lo, mid, hi]
                    if len(valid) == 2:
                        return [int(lo), valid[0], valid[1]]
                    mid_i = len(valid) // 2
                    return [valid[0], valid[mid_i], valid[-1]]
                rep = get_bins(int(sv_min), int(sv_max))
                labels = [f'{int(v)} {size_legend_unit}' for v in rep]
                markers_vals = rep
            else:
                # 연속형 — min / mid / max 3단계
                rep = [sv_min, sv_mid, sv_max]
                if size_mode == "Gene Ratio":
                    labels = [f'{v:.3f}' for v in rep]
                else:
                    labels = [f'{v:.1f} {size_legend_unit}' for v in rep]
                markers_vals = rep

            legend_elements = [
                Line2D([0], [0], marker='o', color='w', markerfacecolor='gray',
                       markersize=_legend_ms(v), label=lbl,
                       markeredgecolor='black', markeredgewidth=0.5)
                for v, lbl in zip(markers_vals, labels)
            ]
            ax.legend(handles=legend_elements, title=size_mode,
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
