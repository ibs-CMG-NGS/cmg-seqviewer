"""
Genomic Distribution Dialog

ATAC-seq peak의 annotation 카테고리 분포를 Pie chart로 시각화합니다.
"""
import logging

import pandas as pd
from PyQt6.QtWidgets import QVBoxLayout
from PyQt6.QtCore import Qt

from models.data_models import Dataset
from gui.base_plot_dialog import BasePlotDialog

_ANNOTATION_COLORS = [
    '#4e79a7', '#f28e2b', '#e15759', '#76b7b2',
    '#59a14f', '#edc948', '#b07aa1', '#ff9da7',
    '#9c755f', '#bab0ac',
]


class GenomicDistributionDialog(BasePlotDialog):
    """
    Annotation 분포 Pie chart 다이얼로그.

    dataset.dataframe['annotation'] 컬럼의 value_counts()를 기반으로
    Pie chart를 그립니다.  annotation 컬럼이 없으면 에러 메시지를 표시합니다.
    """

    def __init__(self, dataset: Dataset, parent=None):
        self.logger = logging.getLogger(__name__)
        self.dataset = dataset

        super().__init__(f"Genomic Distribution — {dataset.name}", parent, figsize=(7, 5))
        self._update_plot()

    # ── Controls ──────────────────────────────────────────────────────────

    def _setup_controls(self, layout: QVBoxLayout):
        # No extra controls needed for this simple pie chart
        pass

    # ── Plot ──────────────────────────────────────────────────────────────

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
        category = raw.split('(')[0].strip()
        return category[0].upper() + category[1:] if category else "Unknown"

    def _do_plot(self):
        self.figure.clear()
        ax = self.figure.add_subplot(111)

        if not self._has_annotation_column():
            ax.text(
                0.5, 0.5,
                "Annotation data not available.\n"
                "This dataset does not contain an 'annotation' column.\n"
                "Load a full-format ATAC-seq Excel file to enable this plot.",
                ha='center', va='center', transform=ax.transAxes,
                fontsize=10, color='#888888',
                bbox=dict(boxstyle='round', fc='#f8f8f8', ec='#cccccc', alpha=0.8),
            )
            self.canvas.draw()
            return

        df = self.dataset.dataframe
        normalized = df['annotation'].dropna().map(self._normalize_annotation)
        counts = normalized.value_counts()

        if len(counts) > 9:
            top9 = counts.iloc[:9]
            others = counts.iloc[9:].sum()
            counts = pd.concat([top9, pd.Series({'Others': others})])

        labels = counts.index.tolist()
        sizes = counts.values.tolist()
        colors = (_ANNOTATION_COLORS * ((len(labels) // len(_ANNOTATION_COLORS)) + 1))[:len(labels)]

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

    # ── Helpers ───────────────────────────────────────────────────────────

    def _has_annotation_column(self) -> bool:
        return (self.dataset.dataframe is not None and
                'annotation' in self.dataset.dataframe.columns and
                not self.dataset.dataframe['annotation'].isna().all())
