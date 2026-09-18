"""
Concordance Heatmap Dialog

행: 유전자 (concordance 정렬)
열: [RNA_log2FC | ATAC_log2FC_mean]
색상: Red(up) ↔ Blue(down)
우측 사이드바: concordance 카테고리 어노테이션
"""

import logging

from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout,
    QLabel, QSpinBox, QCheckBox,
)
import pandas as pd

from gui.base_plot_dialog import BasePlotDialog


class ConcordanceHeatmapDialog(BasePlotDialog):
    """
    Concordance Heatmap

    유의한(sig) 유전자만 표시하며 concordance 카테고리 순으로 정렬합니다.
    """

    def __init__(self, integrated_df: pd.DataFrame, title: str = "Concordance Heatmap", parent=None):
        self.logger = logging.getLogger(__name__)
        self.df = integrated_df.copy()
        self.plot_title = title

        super().__init__("Concordance Heatmap", parent, figsize=(7, 8))
        self._update_plot()

    # ── Controls ──────────────────────────────────────────────────────────

    def _setup_controls(self, layout: QVBoxLayout):
        max_layout = QHBoxLayout()
        max_layout.addWidget(QLabel("Max genes:"))
        self.max_genes_spin = QSpinBox()
        self.max_genes_spin.setRange(10, 500)
        self.max_genes_spin.setValue(100)
        self.max_genes_spin.setSuffix(" genes")
        max_layout.addWidget(self.max_genes_spin)
        layout.addLayout(max_layout)

        self.show_labels_cb = QCheckBox("Show gene labels")
        self.show_labels_cb.setChecked(False)
        layout.addWidget(self.show_labels_cb)

    # ── Plot ──────────────────────────────────────────────────────────────

    def _plot_params(self) -> dict:
        return {
            'max_genes': self.max_genes_spin.value(),
            'show_gene_labels': self.show_labels_cb.isChecked(),
            'title': self.plot_title,
        }

    def _do_plot(self):
        """렌더는 순수 함수 src/plots/concordance_heatmap.py 에 있으며 번들과 공유한다."""
        from plots.concordance_heatmap import render_concordance_heatmap

        self.figure.clear()
        render_concordance_heatmap(self.figure, self.df, self._plot_params())
        self.canvas.draw()

    # ── Bundle export ─────────────────────────────────────────────────────

    def get_bundle_context(self) -> dict:
        return {
            'figure': self.figure,
            'dataframe': self.df,
            'plot_params': self._plot_params(),
            'dataset_name': self.plot_title,
            'plot_type': 'concordance_heatmap',
            'figure_title': self.plot_title,
            'figure_slug': 'concordance_heatmap',
            'source_stem': 'concordance_heatmap',
            'notes': 'Generated from cmg-seqviewer Concordance Heatmap (RNA vs ATAC) plot',
        }

