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
import numpy as np
import matplotlib
matplotlib.use('Qt5Agg')
logging.getLogger('matplotlib.font_manager').setLevel(logging.WARNING)
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
import matplotlib.patches as mpatches

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QDoubleSpinBox, QGroupBox, QFormLayout,
    QFileDialog, QCheckBox, QSpinBox, QWidget,
)
from PyQt6.QtCore import Qt
import pandas as pd

from models.multi_omics_dataset import ConcordanceCategory, IntegratedColumns


class IntegratedVolcanoDialog(QDialog):
    """
    Integrated Volcano Plot

    Multi-Omics 통합 결과에서 RNA-seq DE 데이터를 Volcano Plot으로 표시하며
    concordance 카테고리에 따라 점 색상을 부여합니다.
    점 크기는 ATAC peak count에 비례합니다.
    """

    def __init__(self, integrated_df: pd.DataFrame, title: str = "Integrated Volcano Plot", parent=None):
        super().__init__(parent)
        self.logger = logging.getLogger(__name__)
        self.df = integrated_df.copy()
        self.plot_title = title
        self.setWindowTitle("Integrated Volcano Plot — RNA-seq with ATAC concordance")
        self.resize(900, 700)
        self.setWindowFlags(
            self.windowFlags()
            | Qt.WindowType.WindowMaximizeButtonHint
            | Qt.WindowType.WindowMinimizeButtonHint
        )
        self._init_ui()
        self._plot()

    def _init_ui(self):
        main_layout = QHBoxLayout(self)

        # ── 왼쪽: 설정 패널 ────────────────────────────────────────────
        left = QVBoxLayout()

        thresh_group = QGroupBox("Thresholds")
        thresh_form = QFormLayout(thresh_group)

        self.padj_spin = QDoubleSpinBox()
        self.padj_spin.setRange(0.0001, 1.0)
        self.padj_spin.setDecimals(4)
        self.padj_spin.setValue(0.05)
        self.padj_spin.valueChanged.connect(self._plot)
        thresh_form.addRow("RNA padj ≤", self.padj_spin)

        self.lfc_spin = QDoubleSpinBox()
        self.lfc_spin.setRange(0.0, 10.0)
        self.lfc_spin.setDecimals(2)
        self.lfc_spin.setValue(1.0)
        self.lfc_spin.valueChanged.connect(self._plot)
        thresh_form.addRow("RNA |log2FC| ≥", self.lfc_spin)

        left.addWidget(thresh_group)

        size_group = QGroupBox("Point Size")
        size_form = QFormLayout(size_group)

        self.base_size_spin = QSpinBox()
        self.base_size_spin.setRange(5, 200)
        self.base_size_spin.setValue(30)
        self.base_size_spin.valueChanged.connect(self._plot)
        size_form.addRow("Base size:", self.base_size_spin)

        self.scale_by_peak_cb = QCheckBox("Scale by peak count")
        self.scale_by_peak_cb.setChecked(True)
        self.scale_by_peak_cb.stateChanged.connect(self._plot)
        size_form.addRow("", self.scale_by_peak_cb)

        left.addWidget(size_group)

        self.legend_cb = QCheckBox("Show legend")
        self.legend_cb.setChecked(True)
        self.legend_cb.stateChanged.connect(self._plot)
        left.addWidget(self.legend_cb)

        left.addStretch()

        save_btn = QPushButton("💾 Save Figure")
        save_btn.clicked.connect(self._on_save)
        left.addWidget(save_btn)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        left.addWidget(close_btn)

        left_widget = QWidget()
        left_widget.setLayout(left)
        left_widget.setMaximumWidth(210)
        main_layout.addWidget(left_widget)

        # ── 오른쪽: 캔버스 ─────────────────────────────────────────────
        right = QVBoxLayout()
        self.figure = Figure(figsize=(7, 6), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self)
        right.addWidget(self.toolbar)
        right.addWidget(self.canvas)

        right_widget = QWidget()
        right_widget.setLayout(right)
        main_layout.addWidget(right_widget, stretch=1)

        # hover annotation
        self._annot = None
        self._scatter_data = []

    def _plot(self):
        if not hasattr(self, 'figure'):
            return
        self.figure.clear()
        self._scatter_data = []
        ax = self.figure.add_subplot(111)

        col_sym  = IntegratedColumns.GENE_SYMBOL
        col_lfc  = IntegratedColumns.RNA_LOG2FC
        col_padj = IntegratedColumns.RNA_PADJ
        col_cat  = IntegratedColumns.CONCORDANCE
        col_peak = IntegratedColumns.PEAK_COUNT

        padj_thr = self.padj_spin.value()
        lfc_thr  = self.lfc_spin.value()
        base_sz  = self.base_size_spin.value()
        scale_by_peak = self.scale_by_peak_cb.isChecked()

        df = self.df.dropna(subset=[col_lfc, col_padj]).copy()
        df['_neg_log10_padj'] = -np.log10(df[col_padj].clip(lower=1e-300))

        colors = ConcordanceCategory.COLORS

        for cat in ConcordanceCategory.ALL:
            sub = df[df[col_cat] == cat]
            if sub.empty:
                continue

            if scale_by_peak and col_peak in sub.columns:
                peak_cnt = sub[col_peak].fillna(1).clip(lower=1)
                sizes = base_sz * (1 + np.log1p(peak_cnt) * 0.8)
            else:
                sizes = base_sz

            sc = ax.scatter(
                sub[col_lfc], sub['_neg_log10_padj'],
                c=colors.get(cat, "#CCCCCC"),
                s=sizes, alpha=0.75, linewidths=0.3,
                edgecolors="white",
                label=f"{cat.replace('_',' ')} (n={len(sub)})",
                zorder=3,
            )
            self._scatter_data.append((sc, sub))

        # 기준선
        ax.axhline(-np.log10(padj_thr), color="black",
                   linestyle="--", linewidth=0.8, alpha=0.6)
        ax.axvline( lfc_thr, color="black", linestyle="--", linewidth=0.8, alpha=0.6)
        ax.axvline(-lfc_thr, color="black", linestyle="--", linewidth=0.8, alpha=0.6)

        ax.set_xlabel("RNA-seq log2FC", fontsize=11)
        ax.set_ylabel("-log10(RNA padj)", fontsize=11)
        ax.set_title(self.plot_title, fontsize=13, fontweight="bold")
        ax.grid(True, alpha=0.25)

        if self.legend_cb.isChecked():
            ax.legend(bbox_to_anchor=(1.01, 1), loc="upper left",
                      fontsize=7.5, framealpha=0.7)

        # Hover annotation
        self._annot = ax.annotate(
            "", xy=(0, 0), xytext=(15, 15),
            textcoords="offset points",
            bbox=dict(boxstyle="round", fc="white", alpha=0.9),
            arrowprops=dict(arrowstyle="->"),
            zorder=1000,
        )
        self._annot.set_visible(False)
        self.figure.canvas.mpl_connect("motion_notify_event", self._on_hover)

        self.figure.tight_layout()
        self.canvas.draw()

    def _on_hover(self, event):
        if event.inaxes is None or self._annot is None:
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

        if not found and self._annot.get_visible():
            self._annot.set_visible(False)
            self.figure.canvas.draw_idle()

    def _on_save(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Figure", "integrated_volcano.png",
            "PNG (*.png);;SVG (*.svg);;PDF (*.pdf)"
        )
        if path:
            self.figure.savefig(path, dpi=150, bbox_inches="tight")
            self.logger.info(f"Integrated volcano saved: {path}")
