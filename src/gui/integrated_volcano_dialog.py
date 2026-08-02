"""
Integrated Volcano Dialog

기존 Volcano Plot 기반으로 RNA-seq DE 결과를 표시하되:
  - 점 색상: concordance 카테고리 (ATAC 지지 여부)
  - 점 크기: ATAC peak count (근처 peak 수)
  - hover: 유전자 심볼 + RNA log2FC / padj + concordance

X축: RNA log2FC
Y축: -log10(RNA padj)
"""

import logging

from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QPushButton,
    QDoubleSpinBox, QGroupBox, QFormLayout,
    QCheckBox, QSpinBox,
)
from PyQt6.QtCore import Qt
import pandas as pd

from models.multi_omics_dataset import IntegratedColumns
from gui.base_plot_dialog import BasePlotDialog


class IntegratedVolcanoDialog(BasePlotDialog):
    """
    Integrated Volcano Plot

    Multi-Omics 통합 결과에서 RNA-seq DE 데이터를 Volcano Plot으로 표시하며
    concordance 카테고리에 따라 점 색상을 부여합니다.
    점 크기는 ATAC peak count에 비례합니다.
    """

    def __init__(self, integrated_df: pd.DataFrame, title: str = "Integrated Volcano Plot", parent=None):
        self.logger = logging.getLogger(__name__)
        self.df = integrated_df.copy()
        self.plot_title = title

        self._ax = None
        self._cid_hover = None
        self._scatter_data = []

        super().__init__("Integrated Volcano Plot — RNA-seq with ATAC concordance", parent, figsize=(7, 6))
        self._update_plot()

    # ── Controls ──────────────────────────────────────────────────────────

    def _setup_controls(self, layout: QVBoxLayout):
        # Thresholds
        thresh_group = QGroupBox("Thresholds")
        thresh_form = QFormLayout(thresh_group)

        self.padj_spin = QDoubleSpinBox()
        self.padj_spin.setRange(0.0001, 1.0)
        self.padj_spin.setDecimals(4)
        self.padj_spin.setValue(0.05)
        self.padj_spin.valueChanged.connect(self._update_plot)
        thresh_form.addRow("RNA padj ≤", self.padj_spin)

        self.lfc_spin = QDoubleSpinBox()
        self.lfc_spin.setRange(0.0, 10.0)
        self.lfc_spin.setDecimals(4)
        self.lfc_spin.setValue(1.0)
        self.lfc_spin.valueChanged.connect(self._update_plot)
        thresh_form.addRow("RNA |log2FC| ≥", self.lfc_spin)

        layout.addWidget(thresh_group)

        # Point Size
        size_group = QGroupBox("Point Size")
        size_form = QFormLayout(size_group)

        self.base_size_spin = QSpinBox()
        self.base_size_spin.setRange(5, 200)
        self.base_size_spin.setValue(30)
        self.base_size_spin.valueChanged.connect(self._update_plot)
        size_form.addRow("Base size:", self.base_size_spin)

        self.scale_by_peak_cb = QCheckBox("Scale by peak count")
        self.scale_by_peak_cb.setChecked(True)
        self.scale_by_peak_cb.stateChanged.connect(self._update_plot)
        size_form.addRow("", self.scale_by_peak_cb)

        layout.addWidget(size_group)

    # ── Plot ──────────────────────────────────────────────────────────────

    def _plot_params(self) -> dict:
        return {
            'padj_threshold': self.padj_spin.value(),
            'log2fc_threshold': self.lfc_spin.value(),
            'base_size': self.base_size_spin.value(),
            'scale_by_peak': self.scale_by_peak_cb.isChecked(),
            'title': self.plot_title,
        }

    def _do_plot(self):
        """렌더는 순수 함수 src/plots/integrated_volcano.py 에 있으며 번들과 공유한다.
        hover 툴팁(Qt 전용)은 render 반환 scatter_data 를 재사용한다."""
        from plots.integrated_volcano import render_integrated_volcano

        self.figure.clear()
        ax = self.figure.add_subplot(111)
        self._ax = ax
        self._scatter_data = render_integrated_volcano(ax, self.df, self._plot_params())

        # Hover annotation
        self._annot = ax.annotate(
            "", xy=(0, 0), xytext=(15, 15),
            textcoords="offset points",
            bbox=dict(boxstyle="round", fc="white", alpha=0.9),
            arrowprops=dict(arrowstyle="->"),
            zorder=1000,
        )
        self._annot.set_visible(False)
        if self._cid_hover is not None:
            self.canvas.mpl_disconnect(self._cid_hover)
        self._cid_hover = self.canvas.mpl_connect("motion_notify_event", self._on_hover)

        self.figure.tight_layout()
        self.canvas.draw()

    def _on_hover(self, event):
        if event.inaxes is None or not hasattr(self, '_annot') or self._annot is None:
            return

        col_sym  = IntegratedColumns.GENE_SYMBOL
        col_lfc  = IntegratedColumns.RNA_LOG2FC
        col_padj = IntegratedColumns.RNA_PADJ
        col_cat  = IntegratedColumns.CONCORDANCE
        col_peak = IntegratedColumns.PEAK_COUNT

        found = False
        for sc, sub in self._scatter_data:
            cont, ind = sc.contains(event)
            if cont and len(ind["ind"]) > 0:
                idx = ind["ind"][0]
                row = sub.iloc[idx]
                sym  = row.get(col_sym, "?")
                lfc  = row.get(col_lfc, float("nan"))
                padj = row.get(col_padj, float("nan"))
                cat  = row.get(col_cat, "")
                peak = row.get(col_peak, "N/A")
                text = (
                    f"{sym}\n"
                    f"log2FC: {lfc:.3f}\n"
                    f"padj: {padj:.2e}\n"
                    f"peaks: {peak}\n"
                    f"{cat}"
                )
                self._annot.xy = (event.xdata, event.ydata)
                self._annot.set_text(text)
                self._annot.set_visible(True)
                self.figure.canvas.draw_idle()
                found = True
                break

        if not found and hasattr(self, '_annot') and self._annot.get_visible():
            self._annot.set_visible(False)
            self.figure.canvas.draw_idle()

    # ── Bundle export ─────────────────────────────────────────────────────

    def get_bundle_context(self) -> dict:
        return {
            'figure': self.figure,
            'dataframe': self.df,
            'plot_params': self._plot_params(),
            'dataset_name': self.plot_title,
            'plot_type': 'integrated_volcano',
            'figure_title': self.plot_title,
            'figure_slug': 'integrated_volcano',
            'source_stem': 'integrated_volcano',
            'notes': 'Generated from cmg-seqviewer Integrated Volcano plot',
        }

