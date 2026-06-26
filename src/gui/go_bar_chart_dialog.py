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
from models.standard_columns import StandardColumns
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
        self.figure.clear()

        df = self._get_filtered_data()

        if len(df) == 0:
            ax = self.figure.add_subplot(111)
            ax.text(0.5, 0.5, 'No data to display\nAdjust filters',
                    ha='center', va='center')
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
                    ha='center', va='center')
            self.canvas.draw()
            return

        sort_by = self.sort_combo.currentText()
        if sort_by == "FDR (ascending)" and StandardColumns.FDR in df.columns:
            df = df.sort_values(StandardColumns.FDR, ascending=True)
        elif sort_by == "Gene Count (descending)" and StandardColumns.GENE_COUNT in df.columns:
            df = df.sort_values(StandardColumns.GENE_COUNT, ascending=False)
        elif sort_by == "Alphabetical" and StandardColumns.DESCRIPTION in df.columns:
            df = df.sort_values(StandardColumns.DESCRIPTION, ascending=True)

        top_n = self.top_n_spin.value()
        df = df.head(top_n)

        x_axis_type = self.x_axis_combo.currentText()
        if x_axis_type == "-log10(FDR)":
            if StandardColumns.FDR in df.columns:
                x_data = -np.log10(df[StandardColumns.FDR].replace(0, 1e-300))
            else:
                x_data = pd.Series(1, index=df.index)
        elif x_axis_type == "Gene Ratio":
            if StandardColumns.GENE_RATIO in df.columns:
                def _parse_ratio(r):
                    try:
                        if pd.isna(r):
                            return 0.0
                        if isinstance(r, (int, float)):
                            return float(r)
                        parts = str(r).split('/')
                        return float(parts[0]) / float(parts[1]) if len(parts) == 2 and float(parts[1]) > 0 else 0.0
                    except Exception:
                        return 0.0
                x_data = df[StandardColumns.GENE_RATIO].apply(_parse_ratio)
            else:
                x_data = pd.Series(1, index=df.index)
        else:  # Fold Enrichment
            if StandardColumns.FOLD_ENRICHMENT in df.columns:
                x_data = pd.to_numeric(df[StandardColumns.FOLD_ENRICHMENT], errors='coerce').fillna(0)
            else:
                x_data = pd.Series(1, index=df.index)

        if StandardColumns.DESCRIPTION in df.columns:
            y_labels = df[StandardColumns.DESCRIPTION].to_list()
        else:
            y_labels = [f"Term {i+1}" for i in range(len(df))]

        y_labels = [str(label)[:70] + '...' if len(str(label)) > 70 else str(label)
                    for label in y_labels]

        y_positions = np.arange(len(y_labels))
        bar_color = self.bar_color.name()
        horizontal = self.horizontal_check.isChecked()

        ax = self.figure.add_subplot(111)

        xlabel_text = self._xlabel_text
        ylabel_text = "GO/KEGG Terms"
        if horizontal:
            ax.barh(y_positions, x_data, color=bar_color, edgecolor='black', linewidth=0.5)
            ax.set_yticks(y_positions)
            ax.set_yticklabels(y_labels)
            ax.set_xlabel(xlabel_text, fontweight='bold')
            ax.set_ylabel(ylabel_text, fontweight='bold')
            ax.invert_yaxis()
        else:
            ax.bar(y_positions, x_data, color=bar_color, edgecolor='black', linewidth=0.5)
            ax.set_xticks(y_positions)
            ax.set_xticklabels(y_labels, rotation=45, ha='right')
            ax.set_ylabel(xlabel_text, fontweight='bold')
            ax.set_xlabel(ylabel_text, fontweight='bold')

        ax.set_title("GO/KEGG Enrichment Bar Chart", fontweight='bold')

        if horizontal:
            ax.grid(axis='x', alpha=0.3, linestyle='--')
        else:
            ax.grid(axis='y', alpha=0.3, linestyle='--')

        self.figure.tight_layout()
        self.canvas.draw()

    # ── Export ────────────────────────────────────────────────────────────

    def _export_data(self):
        from PyQt6.QtWidgets import QFileDialog

        df = self._get_filtered_data()

        sort_by = self.sort_combo.currentText()
        if sort_by == "FDR (ascending)" and StandardColumns.FDR in df.columns:
            df = df.sort_values(StandardColumns.FDR, ascending=True)
        elif sort_by == "Gene Count (descending)" and StandardColumns.GENE_COUNT in df.columns:
            df = df.sort_values(StandardColumns.GENE_COUNT, ascending=False)
        elif sort_by == "Alphabetical" and StandardColumns.DESCRIPTION in df.columns:
            df = df.sort_values(StandardColumns.DESCRIPTION, ascending=True)

        top_n = self.top_n_spin.value()
        df = df.head(top_n)

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
