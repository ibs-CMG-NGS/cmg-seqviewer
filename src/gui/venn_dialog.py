"""
Venn Diagram Dialog

2-3개 데이터셋 간의 유전자 overlap을 Venn diagram으로 시각화
"""

from PyQt6.QtWidgets import (
    QVBoxLayout, QGroupBox, QFormLayout, QComboBox,
)
from PyQt6.QtCore import Qt
from matplotlib_venn import venn2, venn3, venn2_circles, venn3_circles
import pandas as pd
import logging

from gui.base_plot_dialog import BasePlotDialog


class VennDiagramDialog(BasePlotDialog):
    """Venn Diagram 시각화 다이얼로그"""

    def __init__(self, datasets, parent=None):
        """
        Args:
            datasets: List of Dataset objects (2-3개)
        """
        if len(datasets) < 2 or len(datasets) > 3:
            raise ValueError("Venn diagram requires 2-3 datasets")

        self.datasets = datasets
        self.logger = logging.getLogger(__name__)

        super().__init__(f"Venn Diagram — {len(datasets)} Datasets", parent, figsize=(10, 8))
        self._update_plot()

    # ── Controls ──────────────────────────────────────────────────────────

    def _setup_controls(self, layout: QVBoxLayout):
        settings_group = QGroupBox("Settings")
        settings_layout = QFormLayout()

        self.filter_combo = QComboBox()
        self.filter_combo.addItems([
            "All Genes",
            "DEG only (|log2FC| ≥ 1, padj ≤ 0.05)",
            "Highly significant (|log2FC| ≥ 2, padj ≤ 0.01)",
            "Custom..."
        ])
        self.filter_combo.currentIndexChanged.connect(self._update_plot)
        settings_layout.addRow("Filter by:", self.filter_combo)

        settings_group.setLayout(settings_layout)
        layout.addWidget(settings_group)

    # ── Data helpers ──────────────────────────────────────────────────────

    def _get_gene_sets(self):
        gene_sets = []
        filter_type = self.filter_combo.currentIndex() if hasattr(self, 'filter_combo') else 0

        for dataset in self.datasets:
            df = dataset.dataframe.copy()

            if filter_type == 1:
                if 'log2FC' in df.columns and 'padj' in df.columns:
                    df = df[(abs(df['log2FC']) >= 1.0) & (df['padj'] <= 0.05)]
                elif 'log2fc' in df.columns and 'adj_pvalue' in df.columns:
                    df = df[(abs(df['log2fc']) >= 1.0) & (df['adj_pvalue'] <= 0.05)]
            elif filter_type == 2:
                if 'log2FC' in df.columns and 'padj' in df.columns:
                    df = df[(abs(df['log2FC']) >= 2.0) & (df['padj'] <= 0.01)]
                elif 'log2fc' in df.columns and 'adj_pvalue' in df.columns:
                    df = df[(abs(df['log2fc']) >= 2.0) & (df['adj_pvalue'] <= 0.01)]

            if 'symbol' in df.columns:
                genes = set(df['symbol'].dropna().unique())
            elif 'gene_id' in df.columns:
                genes = set(df['gene_id'].dropna().unique())
            else:
                genes = set()

            gene_sets.append(genes)
            self.logger.info(f"Dataset '{dataset.name}': {len(genes)} genes")

        return gene_sets

    # ── Plot ──────────────────────────────────────────────────────────────

    def _do_plot(self):
        self.figure.clear()
        ax = self.figure.add_subplot(111)

        gene_sets = self._get_gene_sets()

        if len(self.datasets) == 2:
            venn = venn2(
                gene_sets,
                set_labels=[ds.name for ds in self.datasets],
                ax=ax,
                alpha=0.6
            )
            venn2_circles(gene_sets, ax=ax, linewidth=1.5)

            if venn.get_patch_by_id('10'):
                venn.get_patch_by_id('10').set_color('#ff9999')
            if venn.get_patch_by_id('01'):
                venn.get_patch_by_id('01').set_color('#9999ff')
            if venn.get_patch_by_id('11'):
                venn.get_patch_by_id('11').set_color('#cc99cc')

        elif len(self.datasets) == 3:
            venn = venn3(
                gene_sets,
                set_labels=[ds.name for ds in self.datasets],
                ax=ax,
                alpha=0.6
            )
            venn3_circles(gene_sets, ax=ax, linewidth=1.5)

            colors = {
                '100': '#ff9999', '010': '#9999ff', '001': '#99ff99',
                '110': '#ffcc99', '101': '#ffff99', '011': '#99ffff',
                '111': '#cccccc'
            }
            for region_id, color in colors.items():
                patch = venn.get_patch_by_id(region_id)
                if patch:
                    patch.set_color(color)

        filter_name = self.filter_combo.currentText() if hasattr(self, 'filter_combo') else "All Genes"
        title = f"Gene Overlap - {filter_name}\n"

        if len(gene_sets) == 2:
            common = gene_sets[0] & gene_sets[1]
            unique_0 = gene_sets[0] - gene_sets[1]
            unique_1 = gene_sets[1] - gene_sets[0]
            title += f"Common: {len(common)} | "
            title += f"Unique to {self.datasets[0].name}: {len(unique_0)} | "
            title += f"Unique to {self.datasets[1].name}: {len(unique_1)}"
        elif len(gene_sets) == 3:
            common = gene_sets[0] & gene_sets[1] & gene_sets[2]
            title += f"Common to all: {len(common)}"

        ax.set_title(title, fontsize=12, fontweight='bold', pad=20)

        self.figure.tight_layout()
        self.canvas.draw()
