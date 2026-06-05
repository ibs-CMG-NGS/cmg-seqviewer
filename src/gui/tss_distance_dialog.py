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

    # ── Plot ──────────────────────────────────────────────────────────────

    def _do_plot(self):
        self.figure.clear()
        ax = self.figure.add_subplot(111)

        if not self._has_tss_column():
            ax.text(
                0.5, 0.5,
                "Distance-to-TSS data not available.\n"
                "This dataset does not contain a 'distance_to_tss' column.\n"
                "Load a full-format ATAC-seq Excel file to enable this plot.",
                ha='center', va='center', transform=ax.transAxes,
                fontsize=10, color='#888888',
                bbox=dict(boxstyle='round', fc='#f8f8f8', ec='#cccccc', alpha=0.8),
            )
            self.canvas.draw()
            return

        dist_range = self.range_spin.value() if hasattr(self, 'range_spin') else self._DEFAULT_RANGE
        bins = self.bins_spin.value() if hasattr(self, 'bins_spin') else self._DEFAULT_BINS

        df = self.dataset.dataframe
        series = df['distance_to_tss'].dropna().astype(float)
        clipped = series.clip(-dist_range, dist_range)

        n, bin_edges, patches = ax.hist(
            clipped,
            bins=bins,
            range=(-dist_range, dist_range),
            color='#4e79a7',
            edgecolor='white',
            linewidth=0.3,
        )

        for pos, label, ls, color in [
            (0,       'TSS',  '-',  '#e15759'),
            (-2_000,  '−2kb', '--', '#888888'),
            ( 2_000,  '+2kb', '--', '#888888'),
            (-5_000,  '−5kb', ':',  '#aaaaaa'),
            ( 5_000,  '+5kb', ':',  '#aaaaaa'),
        ]:
            if abs(pos) <= dist_range:
                ax.axvline(pos, linestyle=ls, color=color, linewidth=1.2, alpha=0.85)
                if pos == 0:
                    ax.text(pos + dist_range * 0.01, ax.get_ylim()[1] * 0.95,
                            label, color=color, fontsize=8, va='top')

        ax.set_xlabel("Distance to TSS (bp)", fontsize=10)
        ax.set_ylabel("Number of Peaks", fontsize=10)
        ax.set_title(
            f"TSS Distance Distribution\n{self.dataset.name}",
            fontsize=11,
        )

        def bp_to_kb(x, _):
            return f"{int(x / 1000)}kb" if x != 0 else "0"
        from matplotlib.ticker import FuncFormatter
        ax.xaxis.set_major_formatter(FuncFormatter(bp_to_kb))

        self.canvas.draw()

        # Update summary label if it exists
        if hasattr(self, 'summary_label'):
            within_2kb = (series.abs() <= 2_000).sum()
            within_5kb = (series.abs() <= 5_000).sum()
            total = len(series)
            pct_2kb = within_2kb / total * 100 if total > 0 else 0
            pct_5kb = within_5kb / total * 100 if total > 0 else 0
            self.summary_label.setText(
                f"Total: {total:,} peaks  |  "
                f"≤2kb from TSS: {within_2kb:,} ({pct_2kb:.1f}%)  |  "
                f"≤5kb from TSS: {within_5kb:,} ({pct_5kb:.1f}%)"
            )

    # ── Helpers ───────────────────────────────────────────────────────────

    def _has_tss_column(self) -> bool:
        return (self.dataset.dataframe is not None and
                'distance_to_tss' in self.dataset.dataframe.columns and
                not self.dataset.dataframe['distance_to_tss'].isna().all())
