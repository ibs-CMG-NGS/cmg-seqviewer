"""
Genomic Distribution Dialog

ATAC-seq peak의 annotation 카테고리 분포를 Pie chart로 시각화합니다.
"""
import logging

import matplotlib
matplotlib.use('Qt5Agg')
logging.getLogger('matplotlib.font_manager').setLevel(logging.WARNING)

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
import matplotlib.pyplot as plt

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QMessageBox, QSizePolicy
)
from PyQt6.QtCore import Qt

from models.data_models import Dataset

_ANNOTATION_COLORS = [
    '#4e79a7', '#f28e2b', '#e15759', '#76b7b2',
    '#59a14f', '#edc948', '#b07aa1', '#ff9da7',
    '#9c755f', '#bab0ac',
]


class GenomicDistributionDialog(QDialog):
    """
    Annotation 분포 Pie chart 다이얼로그.

    dataset.dataframe['annotation'] 컬럼의 value_counts()를 기반으로
    Pie chart를 그립니다.  annotation 컬럼이 없으면 에러 메시지를 표시합니다.
    """

    def __init__(self, dataset: Dataset, parent=None):
        super().__init__(parent)
        self.logger = logging.getLogger(__name__)
        self.dataset = dataset
        self.setWindowTitle(f"Genomic Distribution — {dataset.name}")
        self.resize(700, 580)
        self._init_ui()

    # ------------------------------------------------------------------ #
    #  UI
    # ------------------------------------------------------------------ #

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        # 데이터 유효성 확인
        if not self._has_annotation_column():
            msg = QLabel(
                "<b>Annotation data not available.</b><br>"
                "This dataset does not contain an 'annotation' column.<br>"
                "Load a full-format ATAC-seq Excel file to enable this plot."
            )
            msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
            msg.setStyleSheet("color: #888; padding: 40px; font-size: 11pt;")
            layout.addWidget(msg)
            close_btn = QPushButton("Close")
            close_btn.clicked.connect(self.accept)
            layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignRight)
            return

        # Figure
        self.figure = Figure(figsize=(7, 5), tight_layout=True)
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(self.canvas)

        toolbar = NavigationToolbar(self.canvas, self)
        layout.addWidget(toolbar)

        # 하단 버튼
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

        self._draw()

    # ------------------------------------------------------------------ #
    #  Drawing
    # ------------------------------------------------------------------ #

    @staticmethod
    def _normalize_annotation(raw: str) -> str:
        """
        HOMER/ChIPseeker 형식의 세부 annotation 문자열을 대분류로 정규화.
        예) "intron (ENSMUSG00000092329, intron 1 of 15)" → "Intron"
            "Promoter-TSS (Gata1)" → "Promoter-TSS"
            "Intergenic" → "Intergenic"
        """
        if not isinstance(raw, str):
            return "Unknown"
        # 괄호 앞 부분만 취하고 앞뒤 공백 제거
        category = raw.split('(')[0].strip()
        # 첫 글자만 대문자 통일 (intron → Intron, Promoter-TSS는 유지)
        return category[0].upper() + category[1:] if category else "Unknown"

    def _draw(self):
        import pandas as pd
        df = self.dataset.dataframe
        normalized = df['annotation'].dropna().map(self._normalize_annotation)
        counts = normalized.value_counts()

        # Others 묶기 (상위 9개 초과분)
        if len(counts) > 9:
            top9 = counts.iloc[:9]
            others = counts.iloc[9:].sum()
            counts = pd.concat([top9, pd.Series({'Others': others})])

        labels = counts.index.tolist()
        sizes = counts.values.tolist()
        colors = (_ANNOTATION_COLORS * ((len(labels) // len(_ANNOTATION_COLORS)) + 1))[:len(labels)]

        ax = self.figure.add_subplot(111)
        wedges, texts, autotexts = ax.pie(
            sizes,
            labels=None,
            colors=colors,
            autopct=lambda pct: f'{pct:.1f}%' if pct >= 3 else '',
            startangle=90,
            wedgeprops={'linewidth': 0.8, 'edgecolor': 'white'},
        )
        for at in autotexts:
            at.set_fontsize(8)

        # 범례: 카테고리명 + 개수
        legend_labels = [f"{lbl}  ({cnt:,})" for lbl, cnt in zip(labels, sizes)]
        ax.legend(
            wedges, legend_labels,
            title="Annotation",
            loc='center left',
            bbox_to_anchor=(1.0, 0.5),
            fontsize=8,
        )

        total = sum(sizes)
        ax.set_title(
            f"Genomic Distribution of Peaks\n"
            f"{self.dataset.name}  |  Total: {total:,} peaks",
            fontsize=11,
        )
        self.canvas.draw()

    # ------------------------------------------------------------------ #
    #  Helpers
    # ------------------------------------------------------------------ #

    def _has_annotation_column(self) -> bool:
        return (self.dataset.dataframe is not None and
                'annotation' in self.dataset.dataframe.columns and
                not self.dataset.dataframe['annotation'].isna().all())
