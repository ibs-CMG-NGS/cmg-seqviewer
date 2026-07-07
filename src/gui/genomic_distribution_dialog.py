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
from utils.annotation_categories import normalize_annotation, color_for_category


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
        normalized = df['annotation'].dropna().map(normalize_annotation)
        counts = normalized.value_counts()

        if len(counts) > 9:
            top9 = counts.iloc[:9]
            others = counts.iloc[9:].sum()
            counts = pd.concat([top9, pd.Series({'Others': others})])

        labels = counts.index.tolist()
        sizes = counts.values.tolist()
        colors = [color_for_category(lbl, i) for i, lbl in enumerate(labels)]

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
