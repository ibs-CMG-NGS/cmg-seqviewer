"""
Concordance Heatmap Dialog

행: 유전자 (concordance 정렬)
열: [RNA_log2FC | ATAC_log2FC_mean]
색상: Red(up) ↔ Blue(down)
우측 사이드바: concordance 카테고리 어노테이션
"""

import logging
import numpy as np
import matplotlib.patches as mpatches
import matplotlib.colors as mcolors

from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QSpinBox, QCheckBox,
)
from PyQt6.QtCore import Qt
import pandas as pd

from models.multi_omics_dataset import ConcordanceCategory, IntegratedColumns
from gui.base_plot_dialog import BasePlotDialog


class ConcordanceHeatmapDialog(BasePlotDialog):
    """
    Concordance Heatmap

    유의한(sig) 유전자만 표시하며 concordance 카테고리 순으로 정렬합니다.
    """

    _CATEGORY_ORDER = [
        ConcordanceCategory.CONCORDANT_BOTH_UP,
        ConcordanceCategory.CONCORDANT_BOTH_DOWN,
        ConcordanceCategory.DISCORDANT_RNA_UP,
        ConcordanceCategory.DISCORDANT_RNA_DOWN,
        ConcordanceCategory.RNA_ONLY,
        ConcordanceCategory.ATAC_ONLY,
    ]

    def __init__(self, integrated_df: pd.DataFrame, title: str = "Concordance Heatmap", parent=None):
        self.logger = logging.getLogger(__name__)
        self.df = integrated_df.copy()
        self.plot_title = title
        self._ax_heat = None

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

    def _do_plot(self):
        self.figure.clear()

        col_rna   = IntegratedColumns.RNA_LOG2FC
        col_atac  = IntegratedColumns.ATAC_LOG2FC_MEAN
        col_cat   = IntegratedColumns.CONCORDANCE
        col_sym   = IntegratedColumns.GENE_SYMBOL
        max_genes = self.max_genes_spin.value()

        df = self.df[
            self.df[col_cat].isin(self._CATEGORY_ORDER)
        ].dropna(subset=[col_rna, col_atac])

        cat_order = {c: i for i, c in enumerate(self._CATEGORY_ORDER)}
        df = df.copy()
        df["_cat_order"] = df[col_cat].map(cat_order)
        df = df.sort_values(["_cat_order", col_rna], ascending=[True, False])
        df = df.head(max_genes)

        if df.empty:
            ax = self.figure.add_subplot(111)
            ax.text(0.5, 0.5, "No significant genes to display",
                    ha="center", va="center", transform=ax.transAxes)
            self.canvas.draw()
            return

        heatmap_data = df[[col_rna, col_atac]].values
        gene_names   = df[col_sym].values
        categories   = df[col_cat].values

        gs = self.figure.add_gridspec(1, 2, width_ratios=[10, 1], wspace=0.05)
        ax_heat = self.figure.add_subplot(gs[0])
        ax_ann  = self.figure.add_subplot(gs[1])
        self._ax_heat = ax_heat

        import matplotlib
        vmax = np.nanpercentile(np.abs(heatmap_data), 95)
        if vmax == 0:
            vmax = 1.0
        cmap = matplotlib.colormaps.get_cmap("RdBu_r")

        im = ax_heat.imshow(
            heatmap_data, aspect="auto", cmap=cmap,
            vmin=-vmax, vmax=vmax, interpolation="nearest",
        )

        ax_heat.set_xticks([0, 1])
        ax_heat.set_xticklabels(["RNA log2FC", "ATAC log2FC"], fontsize=9)
        ax_heat.set_title(self.plot_title, fontsize=11, fontweight="bold")

        if hasattr(self, 'show_labels_cb') and self.show_labels_cb.isChecked():
            ax_heat.set_yticks(range(len(gene_names)))
            ax_heat.set_yticklabels(gene_names, fontsize=6)
        else:
            ax_heat.set_yticks([])

        ax_heat.set_ylabel(f"Genes (n={len(df)})", fontsize=9)

        self.figure.colorbar(im, ax=ax_heat, fraction=0.03, pad=0.02, label="log2FC")

        cat_colors = ConcordanceCategory.COLORS
        ann_colors = np.array([[
            mcolors.to_rgb(cat_colors.get(c, "#CCCCCC"))
        ] for c in categories])

        ax_ann.imshow(ann_colors, aspect="auto", interpolation="nearest")
        ax_ann.set_xticks([0])
        ax_ann.set_xticklabels(["Cat."], fontsize=7)
        ax_ann.set_yticks([])

        patches = [
            mpatches.Patch(
                color=cat_colors.get(c, "#CCCCCC"),
                label=c.replace("_", " "),
            )
            for c in self._CATEGORY_ORDER
            if c in df[col_cat].values
        ]
        ax_heat.legend(
            handles=patches, bbox_to_anchor=(1.25, 1), loc="upper left",
            fontsize=7, framealpha=0.7,
        )

        self.figure.tight_layout()
        self.canvas.draw()

