"""
Venn Diagram Dialog for Comparison Sheet

Comparison sheet의 데이터를 기반으로 Venn diagram 생성
"""

from PyQt6.QtWidgets import (
    QVBoxLayout, QGroupBox, QDoubleSpinBox, QFormLayout, QCheckBox,
)
from PyQt6.QtCore import Qt
import pandas as pd
import logging

from gui.base_plot_dialog import BasePlotDialog


class VennDiagramFromComparisonDialog(BasePlotDialog):
    """Comparison sheet에서 Venn Diagram 생성"""

    def __init__(self, comparison_df, parent=None):
        """
        Args:
            comparison_df: Comparison sheet의 DataFrame
                          (gene_id, symbol, Status, Found_in, Dataset1_log2FC, Dataset1_padj, ...)
        """
        self.comparison_df = comparison_df
        self.logger = logging.getLogger(__name__)

        # Dataset 이름 추출
        self.dataset_names = []
        for col in comparison_df.columns:
            if col.endswith('_log2FC'):
                dataset_name = col.replace('_log2FC', '')
                if dataset_name not in self.dataset_names:
                    self.dataset_names.append(dataset_name)

        if len(self.dataset_names) < 2 or len(self.dataset_names) > 3:
            raise ValueError(f"Venn diagram requires 2-3 datasets, found {len(self.dataset_names)}")

        self.apply_filter = False
        self.log2fc_threshold = 1.0
        self.padj_threshold = 0.05

        super().__init__(f"Venn Diagram — {len(self.dataset_names)} Datasets", parent, figsize=(10, 8))
        self._update_plot()

    # ── Controls ──────────────────────────────────────────────────────────

    def _setup_controls(self, layout: QVBoxLayout):
        settings_group = QGroupBox("Filter Settings")
        settings_layout = QFormLayout()

        self.filter_check = QCheckBox("Apply statistical filter")
        self.filter_check.setChecked(self.apply_filter)
        self.filter_check.stateChanged.connect(self._on_filter_changed)
        settings_layout.addRow("", self.filter_check)

        self.log2fc_spin = QDoubleSpinBox()
        self.log2fc_spin.setRange(0.0, 10.0)
        self.log2fc_spin.setDecimals(4)
        self.log2fc_spin.setValue(self.log2fc_threshold)
        self.log2fc_spin.setSingleStep(0.1)
        self.log2fc_spin.setEnabled(False)
        self.log2fc_spin.valueChanged.connect(self._on_threshold_changed)
        settings_layout.addRow("|Log2FC| ≥:", self.log2fc_spin)

        self.padj_spin = QDoubleSpinBox()
        self.padj_spin.setRange(0.0001, 1.0)
        self.padj_spin.setDecimals(4)
        self.padj_spin.setValue(self.padj_threshold)
        self.padj_spin.setSingleStep(0.01)
        self.padj_spin.setEnabled(False)
        self.padj_spin.valueChanged.connect(self._on_threshold_changed)
        settings_layout.addRow("Padj ≤:", self.padj_spin)

        settings_group.setLayout(settings_layout)
        layout.addWidget(settings_group)

    # ── Slots ─────────────────────────────────────────────────────────────

    def _on_filter_changed(self):
        self.apply_filter = self.filter_check.isChecked()
        self.log2fc_spin.setEnabled(self.apply_filter)
        self.padj_spin.setEnabled(self.apply_filter)
        self._update_plot()

    def _on_threshold_changed(self):
        self.log2fc_threshold = self.log2fc_spin.value()
        self.padj_threshold = self.padj_spin.value()
        if self.apply_filter:
            self._update_plot()

    # ── Data helpers ──────────────────────────────────────────────────────

    def _gene_sets(self) -> dict:
        """현재 필터 상태로 데이터셋별 gene set을 추출."""
        gene_sets = {}
        for dataset_name in self.dataset_names:
            log2fc_col = f'{dataset_name}_log2FC'
            padj_col = f'{dataset_name}_padj'
            df_subset = self.comparison_df[
                self.comparison_df[log2fc_col].notna() &
                self.comparison_df[padj_col].notna()
            ].copy()
            if self.apply_filter:
                df_subset = df_subset[
                    (abs(df_subset[log2fc_col]) >= self.log2fc_threshold) &
                    (df_subset[padj_col] <= self.padj_threshold)
                ]
            genes = set()
            for _, row in df_subset.iterrows():
                identifier = row.get('symbol', '') or row.get('gene_id', '')
                if identifier:
                    genes.add(identifier)
            gene_sets[dataset_name] = genes
        return gene_sets

    def _build_membership_df(self):
        """gene set을 long-format(dataset/item) 멤버십 테이블로. (df, labels) 반환."""
        gene_sets = self._gene_sets()
        labels = list(self.dataset_names)
        frames = [pd.DataFrame({'dataset': lbl, 'item': list(gene_sets.get(lbl, set()))})
                  for lbl in labels]
        df = pd.concat(frames, ignore_index=True) if frames else \
            pd.DataFrame(columns=['dataset', 'item'])
        return df, labels

    def _plot_params(self, labels=None) -> dict:
        if labels is None:
            labels = list(self.dataset_names)
        if self.apply_filter:
            filter_name = f"|Log2FC| ≥ {self.log2fc_threshold:g}, Padj ≤ {self.padj_threshold:g}"
        else:
            filter_name = "All genes in comparison"
        return {'set_labels': labels, 'unit': 'Gene', 'filter_name': filter_name}

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
            'figure_title': f'Venn Diagram — {len(self.dataset_names)} Datasets',
            'figure_slug': 'venn_diagram',
            'source_stem': 'venn_diagram',
            'notes': 'Generated from cmg-seqviewer Venn Diagram (comparison sheet, long-format membership)',
        }
