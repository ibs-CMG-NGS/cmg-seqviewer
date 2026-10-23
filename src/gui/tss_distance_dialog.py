"""
TSS Distance Dialog

ATAC-seq peak의 TSS(Transcription Start Site)까지 거리 분포를
히스토그램으로 시각화합니다.
"""
import logging

import numpy as np
from PyQt6.QtWidgets import (
    QVBoxLayout, QGroupBox, QFormLayout, QLabel, QSpinBox,
)
from PyQt6.QtCore import Qt

from models.data_models import Dataset
from gui.base_plot_dialog import BasePlotDialog


class TSSDistanceDialog(BasePlotDialog):
    """
    TSS Distance 히스토그램 다이얼로그.

    dataset.dataframe['distance_to_tss'] 컬럼으로 히스토그램을 그립니다.
    컬럼이 없으면 에러 메시지를 표시합니다.
    """

    _DEFAULT_RANGE = 50_000
    _DEFAULT_BINS  = 100

    def __init__(self, dataset: Dataset, parent=None):
        self.logger = logging.getLogger(__name__)
        self.dataset = dataset
        self._summary_text = ""

        super().__init__(f"TSS Distance Distribution — {dataset.name}", parent, figsize=(7.5, 4.8))
        self._update_plot()

    # ── Controls ──────────────────────────────────────────────────────────

    def _setup_controls(self, layout: QVBoxLayout):
        ctrl_group = QGroupBox("Histogram Settings")
        ctrl_layout = QFormLayout()

        self.range_spin = QSpinBox()
        self.range_spin.setRange(1_000, 500_000)
        self.range_spin.setSingleStep(5_000)
        self.range_spin.setValue(self._DEFAULT_RANGE)
        self.range_spin.setSuffix(" bp")
        ctrl_layout.addRow("Range: ±", self.range_spin)

        self.bins_spin = QSpinBox()
        self.bins_spin.setRange(20, 500)
        self.bins_spin.setSingleStep(10)
        self.bins_spin.setValue(self._DEFAULT_BINS)
        ctrl_layout.addRow("Bins:", self.bins_spin)

        ctrl_group.setLayout(ctrl_layout)
        layout.addWidget(ctrl_group)

        self.summary_label = QLabel()
        self.summary_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.summary_label.setStyleSheet("color: #555; font-size: 9pt;")
        layout.addWidget(self.summary_label)
        self.range_spin.valueChanged.connect(self._update_plot)
        self.bins_spin.valueChanged.connect(self._update_plot)

    # ── Plot ──────────────────────────────────────────────────────────────

    def get_plot_params(self) -> dict:
        return {
            'dist_range': self.range_spin.value(),
            'bins': self.bins_spin.value(),
            'title': f"TSS Distance Distribution\n{self.dataset.name}",
        }

    def _do_plot(self):
        from plots.tss_distance import render_tss_distance
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        info = render_tss_distance(ax, self.dataset.dataframe, self.get_plot_params())
        total = info.get('total', 0)
        if hasattr(self, 'summary_label'):
            if total:
                pct_2kb = info['within_2kb'] / total * 100
                pct_5kb = info['within_5kb'] / total * 100
                self.summary_label.setText(
                    f"Total: {total:,} peaks  |  "
                    f"≤2kb from TSS: {info['within_2kb']:,} ({pct_2kb:.1f}%)  |  "
                    f"≤5kb from TSS: {info['within_5kb']:,} ({pct_5kb:.1f}%)")
            else:
                self.summary_label.setText("")

    def get_bundle_context(self) -> dict:
        return {
            'figure': self.figure,
            'dataframe': self.dataset.dataframe,
            'plot_params': self.get_plot_params(),
            'dataset_name': self.dataset.name,
            'plot_type': 'tss_distance',
            'figure_title': f"TSS Distance Distribution — {self.dataset.name}",
            'figure_slug': 'tss_distance',
            'source_stem': 'tss_distance',
            'notes': 'Generated from cmg-seqviewer TSS distance distribution',
        }

    # ── Helpers ───────────────────────────────────────────────────────────

    def _has_tss_column(self) -> bool:
        return (self.dataset.dataframe is not None and
                'distance_to_tss' in self.dataset.dataframe.columns and
                not self.dataset.dataframe['distance_to_tss'].isna().all())
