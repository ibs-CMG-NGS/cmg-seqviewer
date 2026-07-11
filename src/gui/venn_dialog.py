"""
Venn Diagram Dialog

2-3개 데이터셋 간의 유전자(또는 ATAC peak) overlap을 Venn diagram으로 시각화
"""

from PyQt6.QtWidgets import (
    QVBoxLayout, QGroupBox, QFormLayout, QComboBox,
)
from PyQt6.QtCore import Qt
import pandas as pd
import logging

from gui.base_plot_dialog import BasePlotDialog
from models.data_models import DatasetType
from utils import peak_overlap


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
        """데이터셋별 비교 set 추출.

        ATAC_SEQ 데이터셋은 peak_id(좌표) 기준, 그 외(RNA-seq DE 등)는
        gene symbol/gene_id 기준으로 set을 구성한다.
        """
        gene_sets = []
        filter_type = self.filter_combo.currentIndex() if hasattr(self, 'filter_combo') else 0

        padj_threshold = {1: 0.05, 2: 0.01}.get(filter_type)
        log2fc_threshold = {1: 1.0, 2: 2.0}.get(filter_type)

        for dataset in self.datasets:
            if dataset.dataset_type == DatasetType.ATAC_SEQ:
                items = peak_overlap.get_peak_set(dataset, padj_threshold, log2fc_threshold)
                gene_sets.append(items)
                self.logger.info(f"Dataset '{dataset.name}': {len(items)} peaks")
                continue

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

    def _build_membership_df(self):
        """데이터셋별 비교 집합을 long-format(dataset/item) 멤버십 테이블로. (df, labels) 반환."""
        gene_sets = self._get_gene_sets()
        labels = [ds.name for ds in self.datasets]
        frames = [pd.DataFrame({'dataset': lbl, 'item': list(s)})
                  for lbl, s in zip(labels, gene_sets)]
        df = pd.concat(frames, ignore_index=True) if frames else \
            pd.DataFrame(columns=['dataset', 'item'])
        return df, labels

    def _plot_params(self, labels=None) -> dict:
        if labels is None:
            labels = [ds.name for ds in self.datasets]
        is_atac = all(ds.dataset_type == DatasetType.ATAC_SEQ for ds in self.datasets)
        filter_name = self.filter_combo.currentText() if hasattr(self, 'filter_combo') else "All Genes"
        return {
            'set_labels': labels,
            'unit': 'Peak' if is_atac else 'Gene',
            'filter_name': filter_name,
        }

    # ── Plot ──────────────────────────────────────────────────────────────

    def _do_plot(self):
        """렌더는 순수 함수 src/plots/venn.py 에 있으며 번들과 공유한다."""
        from plots.venn import render_venn

        self.figure.clear()
        ax = self.figure.add_subplot(111)
        df, labels = self._build_membership_df()
        render_venn(ax, df, self._plot_params(labels))
        self.figure.tight_layout()
        self.canvas.draw()

    # ── Bundle export ─────────────────────────────────────────────────────

    def get_bundle_context(self) -> dict:
        df, labels = self._build_membership_df()
        return {
            'figure': self.figure,
            'dataframe': df,
            'plot_params': self._plot_params(labels),
            'dataset_name': 'venn',
            'plot_type': 'venn',
            'figure_title': f'Venn Diagram — {len(self.datasets)} Datasets',
            'figure_slug': 'venn_diagram',
            'source_stem': 'venn_diagram',
            'notes': 'Generated from cmg-seqviewer Venn Diagram (long-format membership input)',
        }
