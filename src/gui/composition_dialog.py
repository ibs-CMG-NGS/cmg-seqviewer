"""Cell-type Composition Dialog.

propeller/limma 기반 세포타입 비율 변화 결과(`cell_type`, `PropMean.<cond>`,
`PropRatio`, `P.Value`, `FDR`)를 시각화한다.

- PropRatio 보기: 세포 타입별 비율 차이를 발산형 막대로, FDR 별표와 함께 표시
- Mean proportion 보기: 조건별 평균 비율을 세포 타입별 그룹 막대로 표시
"""
from __future__ import annotations

import logging

import pandas as pd
from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QDoubleSpinBox, QFormLayout, QGroupBox,
    QRadioButton, QButtonGroup, QSpinBox, QVBoxLayout, QFileDialog, QMessageBox,
)

from gui.base_plot_dialog import BasePlotDialog
from plots.composition import render_composition, select_composition_rows
from utils.export_paths import remembered_save_path


class CompositionDialog(BasePlotDialog):
    """Cell-type composition 전용 플롯 다이얼로그."""

    def __init__(self, dataset, parent=None):
        self.logger = logging.getLogger(__name__)
        self.dataset = dataset
        self.df = dataset.dataframe.copy() if dataset.dataframe is not None else pd.DataFrame()
        self.mean_columns = list(dataset.metadata.get('mean_columns', []) or [])
        self.conditions = list(dataset.metadata.get('conditions', []) or [])

        # metadata가 없을 때 컬럼명에서 재추론 (DB에서 막 불러온 경우 등)
        if not self.mean_columns:
            from utils.composition_loader import prop_mean_condition
            self.mean_columns = [c for c in self.df.columns
                                 if prop_mean_condition(c) is not None]
            self.conditions = [prop_mean_condition(c) for c in self.mean_columns]

        super().__init__(f"Cell-Type Composition — {dataset.name}", parent, figsize=(10, 7))
        self._update_plot()

    # ── Controls ──────────────────────────────────────────────────────────

    def _setup_controls(self, layout: QVBoxLayout):
        view_group = QGroupBox("View")
        view_layout = QVBoxLayout()
        self.ratio_radio = QRadioButton("PropRatio (difference)")
        self.means_radio = QRadioButton("Mean proportion by condition")
        self.ratio_radio.setChecked(True)
        self._view_group = QButtonGroup(self)
        self._view_group.addButton(self.ratio_radio)
        self._view_group.addButton(self.means_radio)
        view_layout.addWidget(self.ratio_radio)
        view_layout.addWidget(self.means_radio)
        view_group.setLayout(view_layout)
        layout.addWidget(view_group)

        filter_group = QGroupBox("Data Filter")
        form = QFormLayout()
        self.significant_only = QCheckBox("Significant only")
        self.significant_only.setChecked(False)
        form.addRow("", self.significant_only)

        self.fdr_spin = QDoubleSpinBox()
        self.fdr_spin.setDecimals(4)
        self.fdr_spin.setRange(0.0, 1.0)
        self.fdr_spin.setSingleStep(0.01)
        self.fdr_spin.setValue(0.05)
        form.addRow("FDR ≤", self.fdr_spin)

        self.top_n_spin = QSpinBox()
        self.top_n_spin.setRange(1, 5000)
        self.top_n_spin.setValue(30)
        form.addRow("Top N:", self.top_n_spin)

        self.sort_combo = QComboBox()
        self._sort_items = ["Ratio / Max mean", "FDR", "Cell type"]
        self.sort_combo.addItems(self._sort_items)
        form.addRow("Sort by:", self.sort_combo)

        self.percent_check = QCheckBox("Show as %")
        self.percent_check.setChecked(True)
        form.addRow("", self.percent_check)

        self.show_values_check = QCheckBox("Show significance marks")
        self.show_values_check.setChecked(True)
        form.addRow("", self.show_values_check)
        filter_group.setLayout(form)
        layout.addWidget(filter_group)

        self.means_radio.toggled.connect(self._on_view_changed)
        for w in (self.significant_only, self.percent_check, self.show_values_check):
            w.toggled.connect(self._update_plot)
        self.fdr_spin.valueChanged.connect(self._update_plot)
        self.top_n_spin.valueChanged.connect(self._update_plot)
        self.sort_combo.currentIndexChanged.connect(self._update_plot)

        self._on_view_changed()

    def _on_view_changed(self):
        is_means = self.means_radio.isChecked()
        self.percent_check.setEnabled(is_means)
        self.show_values_check.setEnabled(not is_means)
        self._update_plot()

    # ── Plot inputs ───────────────────────────────────────────────────────

    def _sort_by_value(self) -> str:
        idx = self.sort_combo.currentIndex()
        if idx == 1:
            return 'FDR'
        if idx == 2:
            return 'cell type'
        return 'max mean' if self.means_radio.isChecked() else 'ratio'

    def _plot_params(self) -> dict:
        return {
            'mode': 'means' if self.means_radio.isChecked() else 'ratio',
            'cell_type_col': 'cell_type',
            'ratio_col': 'prop_ratio',
            'pvalue_col': 'pvalue',
            'fdr_col': 'fdr',
            'mean_columns': list(self.mean_columns),
            'conditions': list(self.conditions),
            'fdr_threshold': self.fdr_spin.value(),
            'significant_only': self.significant_only.isChecked(),
            'top_n': self.top_n_spin.value(),
            'sort_by': self._sort_by_value(),
            'percent': self.percent_check.isChecked(),
            'show_values': self.show_values_check.isChecked(),
        }

    def _do_plot(self):
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        render_composition(ax, self.df, self._plot_params())
        try:
            self.figure.tight_layout()
        except Exception:
            pass

    # ── Export ────────────────────────────────────────────────────────────

    def _extra_buttons(self) -> list:
        return [("Export Data", self._export_data)]

    def _export_data(self):
        df = select_composition_rows(self.df, self._plot_params())
        if df.empty:
            QMessageBox.information(self, "No Data", "Nothing to export with the current filters.")
            return
        path, _ = remembered_save_path(
            self, "Export Composition Data",
            f"{self.dataset.name}_composition.csv",
            "CSV (*.csv);;Excel (*.xlsx);;TSV (*.tsv)")
        if not path:
            return
        try:
            lower = path.lower()
            if lower.endswith('.xlsx'):
                df.to_excel(path, index=False)
            elif lower.endswith('.tsv'):
                df.to_csv(path, index=False, sep='\t')
            else:
                df.to_csv(path, index=False)
            QMessageBox.information(self, "Exported", f"Saved to:\n{path}")
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Export failed", str(exc))

    def get_bundle_context(self) -> dict:
        df = select_composition_rows(self.df, self._plot_params())
        slug = self.dataset.name.replace(' ', '_')
        mode = 'means' if self.means_radio.isChecked() else 'ratio'
        return {
            'figure': self.figure,
            'dataframe': df,
            'plot_params': self._plot_params(),
            'dataset_name': self.dataset.name,
            'plot_type': 'composition',
            'figure_title': f"Cell-Type Composition — {self.dataset.name}",
            'figure_slug': f"{slug}_composition_{mode}",
            'source_stem': f"{slug}_composition_{mode}",
            'notes': 'Generated from cmg-seqviewer Cell-Type Composition plot '
                     '(propeller/limma PropRatio or condition mean proportions).',
        }
