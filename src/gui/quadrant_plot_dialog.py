"""
Quadrant Plot Dialog

X축: ATAC log2FC, Y축: RNA log2FC
각 사분면에 concordance 카테고리를 색상으로 표시합니다.
"""

import logging

from PyQt6.QtWidgets import (
    QVBoxLayout, QGroupBox, QFormLayout, QDoubleSpinBox, QCheckBox,
)
from PyQt6.QtCore import Qt
import pandas as pd

from gui.base_plot_dialog import BasePlotDialog
from gui.widgets.category_style_panel import CategoryStylePanel
from gui.widgets.quadrant_hover import QuadrantHoverTooltip
from models.multi_omics_dataset import ConcordanceCategory


class QuadrantPlotDialog(BasePlotDialog):
    """
    RNA log2FC vs ATAC log2FC Quadrant Plot

    Q1 (top-right)  : RNA↑ ATAC↑  → Concordant Both UP
    Q2 (top-left)   : RNA↑ ATAC↓  → Discordant RNA UP
    Q3 (bottom-left): RNA↓ ATAC↓  → Concordant Both DOWN
    Q4 (bottom-right): RNA↓ ATAC↑ → Discordant RNA DOWN
    """

    def __init__(
        self, integrated_df: pd.DataFrame, title: str = "Quadrant Plot", parent=None,
        rna_lfc_cutoff: float = 1.0, atac_lfc_cutoff: float = 1.0,
    ):
        self.logger = logging.getLogger(__name__)
        self.df = integrated_df.copy()
        self.plot_title = title
        self._init_rna_lfc_cutoff = rna_lfc_cutoff
        self._init_atac_lfc_cutoff = atac_lfc_cutoff

        super().__init__("Quadrant Plot — RNA vs ATAC log2FC", parent, figsize=(7, 6))
        self._hover = QuadrantHoverTooltip(self.canvas)
        self._update_plot()

    # ── Controls ──────────────────────────────────────────────────────────

    def _setup_controls(self, layout: QVBoxLayout):
        thresh_group = QGroupBox("Significance Thresholds")
        thresh_layout = QFormLayout()

        self.show_thresholds_cb = QCheckBox("Show threshold lines")
        self.show_thresholds_cb.setChecked(True)
        self.show_thresholds_cb.toggled.connect(self._update_plot)
        thresh_layout.addRow(self.show_thresholds_cb)

        self.rna_thresh_spin = QDoubleSpinBox()
        self.rna_thresh_spin.setRange(0.0, 20.0)
        self.rna_thresh_spin.setDecimals(2)
        self.rna_thresh_spin.setSingleStep(0.25)
        self.rna_thresh_spin.setValue(self._init_rna_lfc_cutoff)
        self.rna_thresh_spin.valueChanged.connect(self._update_plot)
        thresh_layout.addRow("RNA |log2FC| ≥", self.rna_thresh_spin)

        self.atac_thresh_spin = QDoubleSpinBox()
        self.atac_thresh_spin.setRange(0.0, 20.0)
        self.atac_thresh_spin.setDecimals(2)
        self.atac_thresh_spin.setSingleStep(0.25)
        self.atac_thresh_spin.setValue(self._init_atac_lfc_cutoff)
        self.atac_thresh_spin.valueChanged.connect(self._update_plot)
        thresh_layout.addRow("ATAC |log2FC| ≥", self.atac_thresh_spin)

        thresh_group.setLayout(thresh_layout)
        layout.addWidget(thresh_group)

        style_group = QGroupBox("Category Styles")
        style_layout = QVBoxLayout()
        self._cat_style = CategoryStylePanel(
            ConcordanceCategory.ALL, ConcordanceCategory.COLORS,
        )
        self._cat_style.changed.connect(self._update_plot)
        style_layout.addWidget(self._cat_style)
        style_group.setLayout(style_layout)
        layout.addWidget(style_group)

    # ── Plot ──────────────────────────────────────────────────────────────

    def _plot_params(self) -> dict:
        return {
            'category_styles': self._cat_style.get_styles(),
            'title': self.plot_title,
            'rna_lfc_cutoff': self.rna_thresh_spin.value() if self.show_thresholds_cb.isChecked() else None,
            'atac_lfc_cutoff': self.atac_thresh_spin.value() if self.show_thresholds_cb.isChecked() else None,
        }

    def _do_plot(self):
        """렌더는 순수 함수 src/plots/quadrant.py 에 있으며 번들과 공유한다.
        hover 툴팁(Qt 전용)은 QuadrantHoverTooltip이 render 반환 scatter_data를 재사용한다."""
        from plots.quadrant import render_quadrant

        self.figure.clear()
        ax = self.figure.add_subplot(111)
        scatter_data = render_quadrant(ax, self.df, self._plot_params())
        self.figure.tight_layout()

        self._hover.bind(ax, scatter_data)
        self.canvas.draw()

    # ── Bundle export ─────────────────────────────────────────────────────

    def get_bundle_context(self) -> dict:
        return {
            'figure': self.figure,
            'dataframe': self.df,
            'plot_params': self._plot_params(),
            'dataset_name': self.plot_title,
            'plot_type': 'quadrant',
            'figure_title': self.plot_title,
            'figure_slug': 'quadrant_plot',
            'source_stem': 'quadrant_plot',
            'notes': 'Generated from cmg-seqviewer Quadrant (RNA vs ATAC) plot',
        }

