"""
Genomic Distribution Dialog

ATAC-seq peak의 annotation 카테고리 분포를 Pie chart로 시각화합니다.
"""
import logging

from PyQt6.QtWidgets import QVBoxLayout

from models.data_models import Dataset
from gui.base_plot_dialog import BasePlotDialog


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

    def _plot_params(self) -> dict:
        return {'dataset_name': self.dataset.name, 'max_categories': 9}

    def _do_plot(self):
        """렌더는 순수 함수 src/plots/genomic_distribution.py 에 있으며 번들과 공유한다."""
        from plots.genomic_distribution import render_genomic_distribution

        self.figure.clear()
        render_genomic_distribution(self.figure, self.dataset.dataframe, self._plot_params())
        self.canvas.draw()

    # ── Bundle export ─────────────────────────────────────────────────────

    def get_bundle_context(self) -> dict:
        return {
            'figure': self.figure,
            'dataframe': self.dataset.dataframe,
            'plot_params': self._plot_params(),
            'dataset_name': self.dataset.name,
            'plot_type': 'genomic_distribution',
            'figure_title': f'Genomic Distribution — {self.dataset.name}',
            'figure_slug': 'genomic_distribution',
            'source_stem': 'genomic_distribution',
            'notes': 'Generated from cmg-seqviewer Genomic Distribution plot',
        }
