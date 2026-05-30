"""
Concordance Heatmap Dialog

행: 유전자 (concordance 정렬)
열: [RNA_log2FC | ATAC_log2FC_mean]
색상: Red(up) ↔ Blue(down)
우측 사이드바: concordance 카테고리 어노테이션
"""

import logging
import numpy as np
import matplotlib
matplotlib.use('Qt5Agg')
logging.getLogger('matplotlib.font_manager').setLevel(logging.WARNING)
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
import matplotlib.patches as mpatches
import matplotlib.colors as mcolors

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QSpinBox, QCheckBox, QFileDialog,
)
from PyQt6.QtCore import Qt
import pandas as pd

from models.multi_omics_dataset import ConcordanceCategory, IntegratedColumns


class ConcordanceHeatmapDialog(QDialog):
    """
    Concordance Heatmap

    유의한(sig) 유전자만 표시하며 concordance 카테고리 순으로 정렬합니다.
    """

    # 표시 순서 (Not_significant 제외)
    _CATEGORY_ORDER = [
        ConcordanceCategory.CONCORDANT_BOTH_UP,
        ConcordanceCategory.CONCORDANT_BOTH_DOWN,
        ConcordanceCategory.DISCORDANT_RNA_UP,
        ConcordanceCategory.DISCORDANT_RNA_DOWN,
        ConcordanceCategory.RNA_ONLY,
        ConcordanceCategory.ATAC_ONLY,
    ]

    def __init__(self, integrated_df: pd.DataFrame, title: str = "Concordance Heatmap", parent=None):
        super().__init__(parent)
        self.logger = logging.getLogger(__name__)
        self.df = integrated_df.copy()
        self.plot_title = title
        self.setWindowTitle("Concordance Heatmap")
        self.resize(700, 750)
        self._init_ui()
        self._plot()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        # Options
        opt_layout = QHBoxLayout()
        opt_layout.addWidget(QLabel("Max genes:"))
        self.max_genes_spin = QSpinBox()
        self.max_genes_spin.setRange(10, 500)
        self.max_genes_spin.setValue(100)
        self.max_genes_spin.setSuffix(" genes")
        opt_layout.addWidget(self.max_genes_spin)

        self.show_labels_cb = QCheckBox("Show gene labels")
        self.show_labels_cb.setChecked(False)
        opt_layout.addWidget(self.show_labels_cb)

        refresh_btn = QPushButton("↺ Refresh")
        refresh_btn.clicked.connect(self._plot)
        opt_layout.addWidget(refresh_btn)
        opt_layout.addStretch()
        layout.addLayout(opt_layout)

        # Canvas
        self.figure = Figure(figsize=(7, 8), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self)
        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)

        # 버튼
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("💾 Save Figure")
        save_btn.clicked.connect(self._on_save)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        btn_layout.addWidget(save_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

    def _plot(self):
        self.figure.clear()

        col_rna   = IntegratedColumns.RNA_LOG2FC
        col_atac  = IntegratedColumns.ATAC_LOG2FC_MEAN
        col_cat   = IntegratedColumns.CONCORDANCE
        col_sym   = IntegratedColumns.GENE_SYMBOL
        max_genes = self.max_genes_spin.value()

        # Not_significant 제외, 카테고리 순 정렬
        df = self.df[
            self.df[col_cat].isin(self._CATEGORY_ORDER)
        ].dropna(subset=[col_rna, col_atac])

        # 카테고리 순서대로 정렬
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

        # 히트맵 데이터
        heatmap_data = df[[col_rna, col_atac]].values
        gene_names   = df[col_sym].values
        categories   = df[col_cat].values

        # figure 레이아웃: [heatmap | annotation bar]
        gs = self.figure.add_gridspec(1, 2, width_ratios=[10, 1], wspace=0.05)
        ax_heat = self.figure.add_subplot(gs[0])
        ax_ann  = self.figure.add_subplot(gs[1])

        # 색상 스케일 (대칭)
        vmax = np.nanpercentile(np.abs(heatmap_data), 95)
        if vmax == 0:
            vmax = 1.0
        cmap = matplotlib.colormaps.get_cmap("RdBu_r")

        im = ax_heat.imshow(
            heatmap_data, aspect="auto", cmap=cmap,
            vmin=-vmax, vmax=vmax, interpolation="nearest",
        )

        # 컬럼 레이블
        ax_heat.set_xticks([0, 1])
        ax_heat.set_xticklabels(["RNA log2FC", "ATAC log2FC"], fontsize=9)
        ax_heat.set_title(self.plot_title, fontsize=11, fontweight="bold")

        # 유전자 레이블
        if self.show_labels_cb.isChecked():
            ax_heat.set_yticks(range(len(gene_names)))
            ax_heat.set_yticklabels(gene_names, fontsize=6)
        else:
            ax_heat.set_yticks([])

        ax_heat.set_ylabel(f"Genes (n={len(df)})", fontsize=9)

        # Colorbar
        self.figure.colorbar(im, ax=ax_heat, fraction=0.03, pad=0.02,
                             label="log2FC")

        # Annotation bar
        cat_colors = ConcordanceCategory.COLORS
        ann_colors = np.array([[
            mcolors.to_rgb(cat_colors.get(c, "#CCCCCC"))
        ] for c in categories])

        ax_ann.imshow(ann_colors, aspect="auto", interpolation="nearest")
        ax_ann.set_xticks([0])
        ax_ann.set_xticklabels(["Cat."], fontsize=7)
        ax_ann.set_yticks([])

        # Legend
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

    def _on_save(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Figure", "concordance_heatmap.png",
            "PNG (*.png);;SVG (*.svg);;PDF (*.pdf)"
        )
        if path:
            self.figure.savefig(path, dpi=150, bbox_inches="tight")
            self.logger.info(f"Concordance heatmap saved: {path}")
