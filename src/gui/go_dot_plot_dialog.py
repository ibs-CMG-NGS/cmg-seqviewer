"""
GO/KEGG Dot Plot Visualization Dialog
"""

from typing import Optional
import pandas as pd
import numpy as np
from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QGroupBox,
    QWidget, QSpinBox, QComboBox, QPushButton,
    QDoubleSpinBox, QMessageBox, QFormLayout
)
from PyQt6.QtCore import Qt

from models.data_models import Dataset
from models.standard_columns import StandardColumns
from gui.base_plot_dialog import BasePlotDialog


class GODotPlotDialog(BasePlotDialog):
    """GO/KEGG Dot Plot 다이얼로그"""

    def __init__(self, dataset: Dataset, parent=None):
        self.dataset = dataset
        self.df = dataset.dataframe.copy() if dataset.dataframe is not None else pd.DataFrame()

        super().__init__("GO/KEGG Dot Plot", parent, figsize=(10, 8))
        self._update_plot()

    # ── Controls ──────────────────────────────────────────────────────────

    def _setup_controls(self, layout: QVBoxLayout):
        # Plot Settings
        settings_group = QGroupBox("Plot Settings")
        settings_layout = QFormLayout()

        self.top_n_spin = QSpinBox()
        self.top_n_spin.setRange(5, 100)
        self.top_n_spin.setValue(20)
        self.top_n_spin.valueChanged.connect(self._update_plot)
        settings_layout.addRow("Top N terms:", self.top_n_spin)

        self.x_axis_combo = QComboBox()
        self.x_axis_combo.addItems(["Gene Ratio", "Fold Enrichment"])
        self.x_axis_combo.currentTextChanged.connect(self._on_x_axis_changed)
        settings_layout.addRow("X-axis:", self.x_axis_combo)

        self.size_combo = QComboBox()
        self.size_combo.addItems(["Gene Count", "Gene Ratio", "Fold Enrichment"])
        self.size_combo.currentTextChanged.connect(self._update_plot)
        settings_layout.addRow("Dot Size:", self.size_combo)

        settings_group.setLayout(settings_layout)
        layout.addWidget(settings_group)

        # Color Bar Settings
        colorbar_group = QGroupBox("Color Bar Settings")
        colorbar_layout = QFormLayout()

        self.palette_combo = QComboBox()
        self.palette_combo.addItems([
            "YlOrRd", "RdYlGn_r", "viridis", "plasma",
            "coolwarm", "seismic", "Spectral_r", "RdBu_r"
        ])
        self.palette_combo.currentTextChanged.connect(self._update_plot)
        colorbar_layout.addRow("Color Palette:", self.palette_combo)

        self.color_min_spin = QDoubleSpinBox()
        self.color_min_spin.setRange(0, 1)
        self.color_min_spin.setDecimals(4)
        self.color_min_spin.setValue(0)
        self.color_min_spin.setSingleStep(0.01)
        self.color_min_spin.valueChanged.connect(self._update_plot)
        colorbar_layout.addRow("FDR Min:", self.color_min_spin)

        self.color_max_spin = QDoubleSpinBox()
        self.color_max_spin.setRange(0, 1)
        self.color_max_spin.setDecimals(4)
        self.color_max_spin.setValue(0.05)
        self.color_max_spin.setSingleStep(0.01)
        self.color_max_spin.valueChanged.connect(self._update_plot)
        color_auto_btn = QPushButton("Auto")
        color_auto_btn.setMaximumWidth(60)
        color_auto_btn.clicked.connect(self._auto_color_range)
        fdr_max_row = QWidget()
        fdr_max_rl = QHBoxLayout(fdr_max_row)
        fdr_max_rl.setContentsMargins(0, 0, 0, 0)
        fdr_max_rl.setSpacing(4)
        fdr_max_rl.addWidget(self.color_max_spin)
        fdr_max_rl.addWidget(color_auto_btn)
        colorbar_layout.addRow("FDR Max:", fdr_max_row)
        colorbar_group.setLayout(colorbar_layout)
        layout.addWidget(colorbar_group)

        # track x-axis label for use in _do_plot
        self._xlabel_text = "Gene Ratio"

        # Plot Customization
        custom_group = QGroupBox("Plot Customization")
        custom_layout = QFormLayout()

        self.width_spin = QSpinBox()
        self.width_spin.setRange(6, 20)
        self.width_spin.setValue(12)
        self.width_spin.valueChanged.connect(self._on_figure_size_changed)
        custom_layout.addRow("Width (in):", self.width_spin)

        self.height_spin = QSpinBox()
        self.height_spin.setRange(4, 16)
        self.height_spin.setValue(8)
        self.height_spin.valueChanged.connect(self._on_figure_size_changed)
        custom_layout.addRow("Height (in):", self.height_spin)

        custom_group.setLayout(custom_layout)
        layout.addWidget(custom_group)

    def _extra_buttons(self) -> list:
        return [("Export Data", self._export_data)]

    # ── Slots ─────────────────────────────────────────────────────────────

    def _on_x_axis_changed(self, text: str):
        self._xlabel_text = text
        self._update_plot()

    def _on_figure_size_changed(self):
        self.figure.set_size_inches(self.width_spin.value(), self.height_spin.value())
        self.canvas.draw()

    def _get_filtered_data(self) -> pd.DataFrame:
        return self.df.copy()

    def _calculate_gene_ratio(self, df: pd.DataFrame) -> pd.Series:
        if StandardColumns.GENE_RATIO in df.columns:
            def parse_ratio(ratio_str):
                try:
                    if pd.isna(ratio_str):
                        return 0.0
                    if isinstance(ratio_str, (int, float)):
                        return float(ratio_str)
                    parts = str(ratio_str).split('/')
                    if len(parts) == 2:
                        numerator = float(parts[0])
                        denominator = float(parts[1])
                        return numerator / denominator if denominator > 0 else 0.0
                    return 0.0
                except Exception:
                    return 0.0
            return df[StandardColumns.GENE_RATIO].apply(parse_ratio)
        elif StandardColumns.GENE_COUNT in df.columns:
            max_count = df[StandardColumns.GENE_COUNT].max()
            if max_count > 0:
                return df[StandardColumns.GENE_COUNT] / max_count
        return pd.Series(0.5, index=df.index)

    def _auto_color_range(self):
        df = self._get_filtered_data()
        if StandardColumns.FDR in df.columns:
            fdr_values = df[StandardColumns.FDR].dropna()
            if len(fdr_values) > 0:
                self.color_min_spin.setValue(float(fdr_values.min()))
                self.color_max_spin.setValue(float(fdr_values.max()))
                self._update_plot()

    # ── Plot ──────────────────────────────────────────────────────────────

    def _do_plot(self):
        self.figure.clear()

        df = self._get_filtered_data()

        if len(df) == 0:
            ax = self.figure.add_subplot(111)
            ax.text(0.5, 0.5, 'No data to display\nAdjust filters',
                    ha='center', va='center', fontsize=14)
            self.canvas.draw()
            return

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

        gene_ratios = self._calculate_gene_ratio(df)
        df = df.copy()
        df['_gene_ratio'] = gene_ratios

        x_axis_type = self.x_axis_combo.currentText()
        if x_axis_type == "Fold Enrichment" and StandardColumns.FOLD_ENRICHMENT in df.columns:
            df['_x_val'] = pd.to_numeric(df[StandardColumns.FOLD_ENRICHMENT], errors='coerce').fillna(0)
        else:
            df['_x_val'] = df['_gene_ratio']

        df = df.sort_values('_x_val', ascending=False)

        top_n = self.top_n_spin.value()
        df = df.head(top_n)
        df = df.sort_values('_x_val', ascending=True)

        x_data = df['_x_val']

        if StandardColumns.DESCRIPTION in df.columns:
            y_labels = df[StandardColumns.DESCRIPTION].to_list()
        else:
            y_labels = [f"Term {i+1}" for i in range(len(df))]

        y_labels = [str(label)[:60] + '...' if len(str(label)) > 60 else str(label)
                    for label in y_labels]

        y_data = np.arange(len(y_labels))

        if StandardColumns.FDR in df.columns:
            colors = df[StandardColumns.FDR]
            cmap = self.palette_combo.currentText()
            color_label = "FDR"
            vmin = self.color_min_spin.value()
            vmax = self.color_max_spin.value()
        else:
            colors = 'steelblue'
            cmap = None
            color_label = None
            vmin = None
            vmax = None

        size_mode = self.size_combo.currentText()
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

        ax = self.figure.add_subplot(111)

        scatter = ax.scatter(x_data, y_data, c=colors, s=sizes,
                             cmap=cmap, alpha=0.7, edgecolors='black', linewidth=0.5,
                             vmin=vmin, vmax=vmax)

        max_s = float(sizes.max() if hasattr(sizes, 'max') else sizes)
        max_r_pt = np.sqrt(max_s) / 2
        fig_w_pt = self.figure.get_size_inches()[0] * self.figure.dpi
        fig_h_pt = self.figure.get_size_inches()[1] * self.figure.dpi
        x_margin = max_r_pt / (fig_w_pt * 0.55) + 0.05
        y_margin = max_r_pt / (fig_h_pt * 0.80) + 0.05
        ax.margins(x=x_margin, y=y_margin)

        n_terms = len(df)
        if n_terms <= 10:
            ylabel_fontsize = 9
        elif n_terms <= 20:
            ylabel_fontsize = 8
        elif n_terms <= 30:
            ylabel_fontsize = 7
        else:
            ylabel_fontsize = 6

        ax.set_yticks(y_data)
        ax.set_yticklabels(y_labels, fontsize=ylabel_fontsize)
        ax.set_xlabel(self._xlabel_text, fontsize=11, fontweight='bold')
        ax.set_ylabel("GO/KEGG Terms", fontsize=11, fontweight='bold')
        ax.set_title("GO/KEGG Enrichment Dot Plot", fontsize=13, fontweight='bold')
        ax.grid(axis='x', alpha=0.3, linestyle='--')

        if cmap is not None and color_label is not None:
            cbar = self.figure.colorbar(scatter, ax=ax, shrink=0.5, pad=0.02, anchor=(0, 1.0))
            cbar.set_label(color_label, fontsize=10)

        if _size_rep is not None and _norm_max is not None:
            from matplotlib.lines import Line2D

            _leg_fontsize = 8

            def _legend_ms(val):
                s = _S_MIN + np.clip(val / _norm_max, 0, 1) * (_S_MAX - _S_MIN)
                return 2.0 * np.sqrt(s / np.pi)

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

        try:
            self.figure.tight_layout(rect=(0, 0, 0.85, 1))
        except Exception:
            if len(y_labels) > 0:
                max_label_len = max(len(str(label)) for label in y_labels)
                base_margin = 0.30
                char_factor = max_label_len * 0.004
                left_margin = min(0.50, base_margin + char_factor)
            else:
                left_margin = 0.30
            self.figure.subplots_adjust(left=left_margin, right=0.85)

        self.canvas.draw()
        renderer = self.figure.canvas.get_renderer()
        bbox = ax.get_window_extent(renderer=renderer)
        ax_w_px = bbox.width
        ax_h_px = bbox.height
        max_s = float(sizes.max() if hasattr(sizes, 'max') else sizes)
        max_r_px = np.sqrt(max_s) / 2
        x_range = float(x_data.max() - x_data.min()) if len(x_data) > 1 else 1.0
        y_range = float(len(y_data) - 1) if len(y_data) > 1 else 1.0
        x_pad = (max_r_px / ax_w_px) * x_range * 1.3 if ax_w_px > 0 else x_range * 0.05
        y_pad = (max_r_px / ax_h_px) * y_range * 1.3 if ax_h_px > 0 else y_range * 0.05
        ax.set_xlim(float(x_data.min()) - x_pad, float(x_data.max()) + x_pad)
        ax.set_ylim(-0.5 - y_pad, float(len(y_data) - 1) + 0.5 + y_pad)
        self.canvas.draw()

    # ── Export ────────────────────────────────────────────────────────────

    def _export_data(self):
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
