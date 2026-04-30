"""
TSS Distance Dialog

ATAC-seq peak의 TSS(Transcription Start Site)까지 거리 분포를
히스토그램으로 시각화합니다.
"""
import logging

import matplotlib
matplotlib.use('Qt5Agg')
logging.getLogger('matplotlib.font_manager').setLevel(logging.WARNING)

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
import numpy as np

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QSpinBox, QSizePolicy
)
from PyQt6.QtCore import Qt

from models.data_models import Dataset


class TSSDistanceDialog(QDialog):
    """
    TSS Distance 히스토그램 다이얼로그.

    dataset.dataframe['distance_to_tss'] 컬럼으로 히스토그램을 그립니다.
    컬럼이 없으면 에러 메시지를 표시합니다.
    """

    _DEFAULT_RANGE = 50_000   # ±50 kb
    _DEFAULT_BINS  = 100

    def __init__(self, dataset: Dataset, parent=None):
        super().__init__(parent)
        self.logger = logging.getLogger(__name__)
        self.dataset = dataset
        self.setWindowTitle(f"TSS Distance Distribution — {dataset.name}")
        self.resize(750, 560)
        self._init_ui()

    # ------------------------------------------------------------------ #
    #  UI
    # ------------------------------------------------------------------ #

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        if not self._has_tss_column():
            msg = QLabel(
                "<b>Distance-to-TSS data not available.</b><br>"
                "This dataset does not contain a 'distance_to_tss' column.<br>"
                "Load a full-format ATAC-seq Excel file to enable this plot."
            )
            msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
            msg.setStyleSheet("color: #888; padding: 40px; font-size: 11pt;")
            layout.addWidget(msg)
            close_btn = QPushButton("Close")
            close_btn.clicked.connect(self.accept)
            layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignRight)
            return

        # 컨트롤: range 조절
        ctrl_layout = QHBoxLayout()
        ctrl_layout.addWidget(QLabel("Range: ±"))
        self.range_spin = QSpinBox()
        self.range_spin.setRange(1_000, 500_000)
        self.range_spin.setSingleStep(5_000)
        self.range_spin.setValue(self._DEFAULT_RANGE)
        self.range_spin.setSuffix(" bp")
        self.range_spin.setFixedWidth(110)
        ctrl_layout.addWidget(self.range_spin)

        ctrl_layout.addSpacing(20)
        ctrl_layout.addWidget(QLabel("Bins:"))
        self.bins_spin = QSpinBox()
        self.bins_spin.setRange(20, 500)
        self.bins_spin.setSingleStep(10)
        self.bins_spin.setValue(self._DEFAULT_BINS)
        self.bins_spin.setFixedWidth(70)
        ctrl_layout.addWidget(self.bins_spin)

        redraw_btn = QPushButton("Redraw")
        redraw_btn.clicked.connect(self._redraw)
        ctrl_layout.addWidget(redraw_btn)
        ctrl_layout.addStretch()
        layout.addLayout(ctrl_layout)

        # Figure
        self.figure = Figure(figsize=(7.5, 4.8), tight_layout=True)
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(self.canvas)

        toolbar = NavigationToolbar(self.canvas, self)
        layout.addWidget(toolbar)

        # 요약 라벨
        self.summary_label = QLabel()
        self.summary_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.summary_label.setStyleSheet("color: #555; font-size: 9pt;")
        layout.addWidget(self.summary_label)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

        self._draw(self._DEFAULT_RANGE, self._DEFAULT_BINS)

    # ------------------------------------------------------------------ #
    #  Drawing
    # ------------------------------------------------------------------ #

    def _redraw(self):
        self.figure.clear()
        self._draw(self.range_spin.value(), self.bins_spin.value())

    def _draw(self, dist_range: int, bins: int):
        df = self.dataset.dataframe
        series = df['distance_to_tss'].dropna().astype(float)

        # 범위 클리핑
        clipped = series.clip(-dist_range, dist_range)

        ax = self.figure.add_subplot(111)
        n, bin_edges, patches = ax.hist(
            clipped,
            bins=bins,
            range=(-dist_range, dist_range),
            color='#4e79a7',
            edgecolor='white',
            linewidth=0.3,
        )

        # 참고선: 0 bp (TSS), ±2 kb, ±5 kb
        for pos, label, ls, color in [
            (0,        'TSS',  '-',  '#e15759'),
            (-2_000,   '−2kb', '--', '#888888'),
            ( 2_000,   '+2kb', '--', '#888888'),
            (-5_000,   '−5kb', ':',  '#aaaaaa'),
            ( 5_000,   '+5kb', ':',  '#aaaaaa'),
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

        # x축 눈금 단위: kb
        def bp_to_kb(x, _):
            return f"{int(x / 1000)}kb" if x != 0 else "0"
        from matplotlib.ticker import FuncFormatter
        ax.xaxis.set_major_formatter(FuncFormatter(bp_to_kb))

        self.canvas.draw()

        # 요약 통계
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

    # ------------------------------------------------------------------ #
    #  Helpers
    # ------------------------------------------------------------------ #

    def _has_tss_column(self) -> bool:
        return (self.dataset.dataframe is not None and
                'distance_to_tss' in self.dataset.dataframe.columns and
                not self.dataset.dataframe['distance_to_tss'].isna().all())
