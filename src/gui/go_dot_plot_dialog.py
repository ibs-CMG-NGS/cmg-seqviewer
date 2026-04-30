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
        
        # Size 데이터 (고정 생물학적 기준 범위로 정규화 - 데이터셋 간 일관성 유지)
        size_mode = self.size_combo.currentText()
        # (norm_max, [(val, label), ...]) — legend 3단계 고정
        _SIZE_NORM = {
            "Gene Count":      (100.0, [(10, "10 genes"), (30, "30 genes"), (80, "≥80 genes")]),
            "Gene Ratio":      (0.40,  [(0.03, "0.03"),   (0.12, "0.12"),  (0.35, "≥0.35")]),
            "Fold Enrichment": (20.0,  [(2.0,  "2×"),     (5.0,  "5×"),    (15.0, "≥15×")]),
        }
        _S_MIN, _S_MAX = 50, 500

        if size_mode == "Gene Count" and StandardColumns.GENE_COUNT in df.columns:
            raw_sizes = pd.to_numeric(df[StandardColumns.GENE_COUNT], errors='coerce').fillna(0)
        elif size_mode == "Gene Ratio":
            raw_sizes = pd.to_numeric(df['_gene_ratio'], errors='coerce').fillna(0)
        elif size_mode == "Fold Enrichment" and StandardColumns.FOLD_ENRICHMENT in df.columns:
            raw_sizes = pd.to_numeric(df[StandardColumns.FOLD_ENRICHMENT], errors='coerce').fillna(0)
        else:
            raw_sizes = None

        if raw_sizes is not None and size_mode in _SIZE_NORM:
            _norm_max, _size_rep = _SIZE_NORM[size_mode]
            sizes = _S_MIN + np.clip(raw_sizes / _norm_max, 0, 1) * (_S_MAX - _S_MIN)
        else:
            _norm_max, _size_rep = None, None
            sizes = pd.Series(100, index=df.index) if raw_sizes is None else raw_sizes * 0 + 100
        
        # Plotting
        ax = self.figure.add_subplot(111)
        
        scatter = ax.scatter(x_data, y_data, c=colors, s=sizes, 
                           cmap=cmap, alpha=0.7, edgecolors='black', linewidth=0.5,
                           vmin=vmin, vmax=vmax)
        
        # ── Axes 여백: dot이 경계에 잘리지 않도록 ──
        # 최대 dot 반지름(pt)을 데이터 범위 비율로 환산해 margins 설정
        max_s = float(sizes.max() if hasattr(sizes, 'max') else sizes)
        max_r_pt = np.sqrt(max_s) / 2  # scatter s → radius(pt)
        # canvas가 아직 렌더링 안 됐을 수 있으므로 figure 크기로 근사
        fig_w_pt = self.figure.get_size_inches()[0] * self.figure.dpi
        fig_h_pt = self.figure.get_size_inches()[1] * self.figure.dpi
        x_margin = max_r_pt / (fig_w_pt * 0.55) + 0.05   # axes 너비의 약 55% 가정 + 고정 5%
        y_margin = max_r_pt / (fig_h_pt * 0.80) + 0.05
        ax.margins(x=x_margin, y=y_margin)
        
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
        
        # Size legend (고정 3단계 - 생물학적 기준값 사용)
        if _size_rep is not None and _norm_max is not None:
            from matplotlib.lines import Line2D

            _leg_fontsize = 8

            def _legend_ms(val):
                s = _S_MIN + np.clip(val / _norm_max, 0, 1) * (_S_MAX - _S_MIN)
                return 2.0 * np.sqrt(s / np.pi)  # scatter s(면적 pt²) → Line2D markersize(지름 pt)

            # 최대 원 지름 기준으로 labelspacing 동적 계산 (겁침 방지)
            _max_diam = max(_legend_ms(v) for v, _ in _size_rep)
            _labelspacing = _max_diam / _leg_fontsize + 0.5

            legend_elements = [
                Line2D([0], [0], marker='o', color='none',
                       markerfacecolor='#808080', markeredgecolor='#333333',
                       markeredgewidth=0.8, markersize=_legend_ms(v), label=lbl)
                for v, lbl in _size_rep
            ]
            leg = ax.legend(handles=legend_elements, title=size_mode,
                            loc='upper left', fontsize=_leg_fontsize,
                            title_fontsize=_leg_fontsize,
                            labelspacing=_labelspacing,
                            handlelength=0, handletextpad=1.2,
                            borderpad=0.9, framealpha=0.95,
                            edgecolor='#bbbbbb', fancybox=False,
                            bbox_to_anchor=(1.02, 0.20))
            leg.get_title().set_fontweight('bold')
        
        # Layout 조정 - tight_layout 사용하여 자동으로 여백 조정
        try:
            self.figure.tight_layout(rect=(0, 0, 0.85, 1))  # 오른쪽 15% legend 공간
        except Exception:
            if len(y_labels) > 0:
                max_label_len = max(len(str(label)) for label in y_labels)
                base_margin = 0.30
                char_factor = max_label_len * 0.004
                left_margin = min(0.50, base_margin + char_factor)
            else:
                left_margin = 0.30
            self.figure.subplots_adjust(left=left_margin, right=0.85)

        # tight_layout 이후 실제 axes 픽셀 크기로 xlim/ylim 재보정
        # (margins()는 tight_layout에 의해 덮어쓰여질 수 있음)
        self.canvas.draw()  # 렌더링 트리거 → get_window_extent 정확해짐
        renderer = self.figure.canvas.get_renderer()
        bbox = ax.get_window_extent(renderer=renderer)   # 실제 axes 픽셀 bbox
        ax_w_px = bbox.width
        ax_h_px = bbox.height
        max_s = float(sizes.max() if hasattr(sizes, 'max') else sizes)
        max_r_px = np.sqrt(max_s) / 2  # scatter s(pt²) → radius(pt≈px at 100dpi)
        x_range = float(x_data.max() - x_data.min()) if len(x_data) > 1 else 1.0
        y_range = float(len(y_data) - 1) if len(y_data) > 1 else 1.0
        x_pad = (max_r_px / ax_w_px) * x_range * 1.3 if ax_w_px > 0 else x_range * 0.05
        y_pad = (max_r_px / ax_h_px) * y_range * 1.3 if ax_h_px > 0 else y_range * 0.05
        ax.set_xlim(float(x_data.min()) - x_pad, float(x_data.max()) + x_pad)
        ax.set_ylim(-0.5 - y_pad, float(len(y_data) - 1) + 0.5 + y_pad)
        self.canvas.draw()  # xlim/ylim 반영 후 최종 렌더링
    
    def _save_figure(self):
        """Figure 저장"""
        from PyQt6.QtWidgets import QFileDialog
        import matplotlib
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Figure",
            f"go_dot_plot_{self.dataset.name}.png",
            "PNG Files (*.png);;PDF Files (*.pdf);;SVG Files (*.svg);;TIFF Files (*.tiff);;All Files (*)"
        )
        
        if not file_path:
            return

        # 확장자가 없으면 .png 기본값
        if '.' not in file_path.split('/')[-1].split('\\')[-1]:
            file_path += '.png'

        fmt = file_path.rsplit('.', 1)[-1].lower()
        supported = self.figure.canvas.get_supported_filetypes()
        if fmt not in supported:
            QMessageBox.warning(
                self, "Unsupported Format",
                f"The format '.{fmt}' is not supported by your matplotlib {matplotlib.__version__}.\n"
                f"Supported formats: {', '.join(sorted(supported.keys()))}"
            )
            return

        try:
            if fmt in ('png', 'tiff', 'tif', 'jpg', 'jpeg'):
                self.figure.savefig(file_path, dpi=300, bbox_inches='tight')
            else:
                self.figure.savefig(file_path, bbox_inches='tight')
            QMessageBox.information(self, "Success", f"Figure saved to:\n{file_path}")
        except Exception as e:
            QMessageBox.critical(
                self, "Save Error",
                f"Failed to save figure:\n{str(e)}\n\n"
                f"matplotlib version: {matplotlib.__version__}"
            )
    
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
