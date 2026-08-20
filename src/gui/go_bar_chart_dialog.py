"""
GO/KEGG Bar Chart Visualization Dialog
"""

from typing import Optional
import pandas as pd
import numpy as np
from PyQt6.QtWidgets import (
    QGroupBox, QSpinBox, QComboBox, QPushButton,
    QCheckBox, QMessageBox, QFormLayout,
    QColorDialog, QVBoxLayout,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

from models.data_models import Dataset
from gui.base_plot_dialog import BasePlotDialog


class GOBarChartDialog(BasePlotDialog):
    """GO/KEGG Bar Chart 다이얼로그"""

    def __init__(self, dataset: Dataset, parent=None):
        self.dataset = dataset
        self.df = dataset.dataframe.copy() if dataset.dataframe is not None else pd.DataFrame()
        self.bar_color = QColor(70, 130, 180)  # steelblue default

        super().__init__("GO/KEGG Bar Chart", parent, figsize=(10, 8))
        self._update_plot()

    # ── Controls ──────────────────────────────────────────────────────────

    def _setup_controls(self, layout: QVBoxLayout):
        # Chart Settings
        settings_group = QGroupBox("Chart Settings")
        settings_layout = QFormLayout()

        self.top_n_spin = QSpinBox()
        self.top_n_spin.setRange(5, 50)
        self.top_n_spin.setValue(15)
        self.top_n_spin.valueChanged.connect(self._update_plot)
        settings_layout.addRow("Top N terms:", self.top_n_spin)

        self.x_axis_combo = QComboBox()
        self.x_axis_combo.addItems(["-log10(FDR)", "Gene Ratio", "Fold Enrichment"])
        self.x_axis_combo.currentTextChanged.connect(self._on_x_axis_changed)
        settings_layout.addRow("X-axis:", self.x_axis_combo)

        self.sort_combo = QComboBox()
        self.sort_combo.addItems(["FDR (ascending)", "Gene Count (descending)", "Alphabetical"])
        self.sort_combo.currentTextChanged.connect(self._update_plot)
        settings_layout.addRow("Sort by:", self.sort_combo)

        self.bar_color_btn = QPushButton("Choose Bar Color")
        self.bar_color_btn.setStyleSheet(f"background-color: {self.bar_color.name()};")
        self.bar_color_btn.clicked.connect(self._choose_bar_color)
        settings_layout.addRow("Bar Color:", self.bar_color_btn)

        self.horizontal_check = QCheckBox("Horizontal bars")
        self.horizontal_check.setChecked(True)
        self.horizontal_check.toggled.connect(self._update_plot)
        settings_layout.addRow("", self.horizontal_check)

        settings_group.setLayout(settings_layout)
        layout.addWidget(settings_group)

        # track x-axis label for use in _do_plot
        self._xlabel_text = "-log10(FDR)"

    def _extra_buttons(self) -> list:
        return [("Export Data", self._export_data)]

    # ── Bundle / params ────────────────────────────────────────────────────

    def _plot_params(self) -> dict:
        return {
            'top_n': self.top_n_spin.value(),
            'x_axis': self.x_axis_combo.currentText(),
            'sort_by': self.sort_combo.currentText(),
            'bar_color': self.bar_color.name(),
            'horizontal': self.horizontal_check.isChecked(),
            'xlabel_text': getattr(self, '_xlabel_text', self.x_axis_combo.currentText()),
        }

    def get_bundle_context(self) -> dict:
        return {
            'figure': self.figure,
            'dataframe': self.df,
            'plot_params': self._plot_params(),
            'dataset_name': getattr(self.dataset, 'name', 'unknown'),
            'plot_type': 'go_bar',
            'figure_title': 'GO/KEGG Enrichment Bar Chart',
            'figure_slug': 'go_bar_chart',
            'source_stem': 'go_bar_chart',
            'notes': 'Generated from cmg-seqviewer GO/KEGG bar chart',
        }

    # ── Slots ─────────────────────────────────────────────────────────────

    def _on_x_axis_changed(self, text: str):
        label_map = {
            "-log10(FDR)": "-log10(FDR)",
            "Gene Ratio": "Gene Ratio",
            "Fold Enrichment": "Fold Enrichment",
        }
        self._xlabel_text = label_map.get(text, text)
        self._update_plot()

    def _choose_bar_color(self):
        color = QColorDialog.getColor(self.bar_color, self, "Choose Bar Color")
        if color.isValid():
            self.bar_color = color
            self.bar_color_btn.setStyleSheet(f"background-color: {color.name()};")
            self._update_plot()

    def _get_filtered_data(self) -> pd.DataFrame:
        return self.df.copy()

    # ── Plot ──────────────────────────────────────────────────────────────

    def _do_plot(self):
        """렌더는 순수 함수 src/plots/go_bar.py::render_go_bar 에 있으며 재현 번들과 공유한다."""
        from plots.go_bar import render_go_bar

        self.figure.clear()
        ax = self.figure.add_subplot(111)
        render_go_bar(ax, self._get_filtered_data(), self._plot_params())
        self.figure.tight_layout()
        self.canvas.draw()

    # ── Export ────────────────────────────────────────────────────────────

    def _export_data(self):
        from PyQt6.QtWidgets import QFileDialog
        from plots.go_bar import select_go_bar_rows

        # render_go_bar 와 동일한 선택 함수를 재사용 — 두 곳에 로직을 복제하면 한쪽만
        # 고쳤을 때 그림과 export 가 어긋날 수 있다.
        df = select_go_bar_rows(self._get_filtered_data(), self._plot_params())

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Data",
            f"go_bar_chart_data_{self.dataset.name}.csv",
            "CSV Files (*.csv);;Excel Files (*.xlsx);;All Files (*)"
        )

        if file_path:
            if file_path.endswith('.xlsx'):
                df.to_excel(file_path, index=False)
            else:
                df.to_csv(file_path, index=False)
            QMessageBox.information(self, "Success", f"Data exported to:\n{file_path}")
