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
        self._plotted_df = None  # 마지막 render_go_dot() 결과(선택+정렬 반영) — Export 용

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

        # 표시 순서 (선택은 항상 FDR 최소 Top N; 이 콤보는 순서만 결정)
        self.sort_combo = QComboBox()
        self.sort_combo.addItems(["FDR", "Gene Ratio", "Fold Enrichment", "Gene Count"])
        self.sort_combo.setToolTip(
            "Top N term 선택은 항상 FDR(유의성) 기준이며,\n"
            "이 옵션은 뽑힌 term의 표시 순서만 바꿉니다."
        )
        self.sort_combo.currentTextChanged.connect(self._update_plot)
        settings_layout.addRow("Sort by:", self.sort_combo)

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

    # ── Bundle / params ────────────────────────────────────────────────────

    def _plot_params(self) -> dict:
        return {
            'top_n': self.top_n_spin.value(),
            'x_axis': self.x_axis_combo.currentText(),
            'size_mode': self.size_combo.currentText(),
            'sort_by': self.sort_combo.currentText(),
            'palette': self.palette_combo.currentText(),
            'color_min': self.color_min_spin.value(),
            'color_max': self.color_max_spin.value(),
            'xlabel_text': getattr(self, '_xlabel_text', self.x_axis_combo.currentText()),
            'fig_width': self.width_spin.value(),
            'fig_height': self.height_spin.value(),
        }

    def get_bundle_context(self) -> dict:
        return {
            'figure': self.figure,
            'dataframe': self.df,
            'plot_params': self._plot_params(),
            'dataset_name': getattr(self.dataset, 'name', 'unknown'),
            'plot_type': 'go_dot',
            'figure_title': 'GO/KEGG Enrichment Dot Plot',
            'figure_slug': 'go_dot_plot',
            'source_stem': 'go_dot_plot',
            'notes': 'Generated from cmg-seqviewer GO/KEGG dot plot',
        }

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
        """렌더는 순수 함수 src/plots/go_dot.py::render_go_dot 에 있으며 재현 번들과 공유한다.
        여기서는 그 함수를 호출한 뒤 렌더러 기반 픽셀 여백 미세보정(Qt 전용)만 처리한다.
        """
        from plots.go_dot import render_go_dot

        self.figure.clear()
        res = render_go_dot(self.figure, self._get_filtered_data(), self._plot_params())
        if res is None:
            self._plotted_df = None
            self.canvas.draw()
            return
        df, sizes = res
        # 실제 그려진(선택+표시순서 반영) 표를 저장 — Export Data 가 별도 로직 없이 재사용한다.
        self._plotted_df = df

        # 렌더러 기반 픽셀 단위 여백 미세보정 (Qt 전용 — 번들에선 margins로 충분)
        self.canvas.draw()
        try:
            ax = self.figure.axes[0]
            x_data = df['_x_val']
            y_data = np.arange(len(df))
            renderer = self.figure.canvas.get_renderer()
            bbox = ax.get_window_extent(renderer=renderer)
            ax_w_px, ax_h_px = bbox.width, bbox.height
            max_s = float(sizes.max() if hasattr(sizes, 'max') else sizes)
            max_r_px = np.sqrt(max_s) / 2
            x_range = float(x_data.max() - x_data.min()) if len(x_data) > 1 else 1.0
            y_range = float(len(y_data) - 1) if len(y_data) > 1 else 1.0
            x_pad = (max_r_px / ax_w_px) * x_range * 1.3 if ax_w_px > 0 else x_range * 0.05
            y_pad = (max_r_px / ax_h_px) * y_range * 1.3 if ax_h_px > 0 else y_range * 0.05
            ax.set_xlim(float(x_data.min()) - x_pad, float(x_data.max()) + x_pad)
            ax.set_ylim(-0.5 - y_pad, float(len(y_data) - 1) + 0.5 + y_pad)
            self.canvas.draw()
        except Exception:
            pass

    # ── Export ────────────────────────────────────────────────────────────

    def _export_data(self):
        from PyQt6.QtWidgets import QFileDialog

        # 별도로 선택 로직을 복제하지 않고, 실제 그려진 표(render_go_dot 의 반환값,
        # top-N 선택 + sort_by 표시순서까지 반영됨)를 그대로 쓴다 — 그림/export 불일치 방지.
        if self._plotted_df is None or self._plotted_df.empty:
            QMessageBox.warning(self, "No Data", "Nothing to export.")
            return
        df = self._plotted_df.drop(
            columns=[c for c in self._plotted_df.columns if c.startswith('_')],
            errors='ignore')

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
