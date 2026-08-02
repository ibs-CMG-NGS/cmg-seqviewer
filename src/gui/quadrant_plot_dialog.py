"""
Quadrant Plot Dialog

X축: ATAC log2FC, Y축: RNA log2FC
각 사분면에 concordance 카테고리를 색상으로 표시합니다.
"""

import logging
import numpy as np

from PyQt6.QtWidgets import (
    QVBoxLayout, QGroupBox, QFormLayout, QSpinBox, QDoubleSpinBox,
)
from PyQt6.QtCore import Qt
import pandas as pd

from gui.base_plot_dialog import BasePlotDialog


class QuadrantPlotDialog(BasePlotDialog):
    """
    RNA log2FC vs ATAC log2FC Quadrant Plot

    Q1 (top-right)  : RNA↑ ATAC↑  → Concordant Both UP
    Q2 (top-left)   : RNA↑ ATAC↓  → Discordant RNA UP
    Q3 (bottom-left): RNA↓ ATAC↓  → Concordant Both DOWN
    Q4 (bottom-right): RNA↓ ATAC↑ → Discordant RNA DOWN
    """

    def __init__(self, integrated_df: pd.DataFrame, title: str = "Quadrant Plot", parent=None):
        self.logger = logging.getLogger(__name__)
        self.df = integrated_df.copy()
        self.plot_title = title

        self._scatter_data = []
        self._annot = None
        self._ax = None
        self._cid_mouse = None

        super().__init__("Quadrant Plot — RNA vs ATAC log2FC", parent, figsize=(7, 6))
        self._update_plot()

    # ── Controls ──────────────────────────────────────────────────────────

    def _setup_controls(self, layout: QVBoxLayout):
        settings_group = QGroupBox("Plot Settings")
        settings_layout = QFormLayout()

        self.point_size_spin = QSpinBox()
        self.point_size_spin.setRange(5, 200)
        self.point_size_spin.setValue(30)
        self.point_size_spin.valueChanged.connect(self._update_plot)
        settings_layout.addRow("Point size:", self.point_size_spin)

        self.alpha_spin = QDoubleSpinBox()
        self.alpha_spin.setRange(0.05, 1.0)
        self.alpha_spin.setDecimals(2)
        self.alpha_spin.setSingleStep(0.05)
        self.alpha_spin.setValue(0.70)
        self.alpha_spin.valueChanged.connect(self._update_plot)
        settings_layout.addRow("Alpha:", self.alpha_spin)

        settings_group.setLayout(settings_layout)
        layout.addWidget(settings_group)

    # ── Plot ──────────────────────────────────────────────────────────────

    def _plot_params(self) -> dict:
        return {
            'point_size': self.point_size_spin.value(),
            'alpha': self.alpha_spin.value(),
            'title': self.plot_title,
        }

    def _do_plot(self):
        """렌더는 순수 함수 src/plots/quadrant.py 에 있으며 번들과 공유한다.
        hover 툴팁(Qt 전용)은 render 반환 scatter_data 를 재사용한다."""
        from plots.quadrant import render_quadrant

        self.figure.clear()
        ax = self.figure.add_subplot(111)
        self._ax = ax
        self._scatter_data = render_quadrant(ax, self.df, self._plot_params())
        self.figure.tight_layout()

        self._annot = ax.annotate(
            "",
            xy=(0, 0), xytext=(12, 12), textcoords="offset points",
            bbox=dict(boxstyle="round,pad=0.4", fc="lightyellow", ec="gray", alpha=0.92),
            arrowprops=dict(arrowstyle="->", color="gray", lw=0.8),
            fontsize=8, zorder=10,
        )
        self._annot.set_visible(False)

        if self._cid_mouse is not None:
            self.canvas.mpl_disconnect(self._cid_mouse)
        self._cid_mouse = self.canvas.mpl_connect('motion_notify_event', self._on_mouse_move)
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

    def _on_mouse_move(self, event):
        if event.inaxes is None or self._ax is None:
            if self._annot and self._annot.get_visible():
                self._annot.set_visible(False)
                self.canvas.draw_idle()
            return

        xlim = self._ax.get_xlim()
        ylim = self._ax.get_ylim()
        x_range = xlim[1] - xlim[0]
        y_range = ylim[1] - ylim[0]

        best_dist = float('inf')
        best_info = None

        ex, ey = event.xdata, event.ydata
        for data in self._scatter_data:
            if len(data['x']) == 0:
                continue
            dx = (data['x'] - ex) / (x_range or 1)
            dy = (data['y'] - ey) / (y_range or 1)
            dists = np.sqrt(dx ** 2 + dy ** 2)
            idx = int(np.argmin(dists))
            if dists[idx] < best_dist:
                best_dist = dists[idx]
                best_info = (
                    data['x'][idx],
                    data['y'][idx],
                    data['symbol'][idx],
                    data['concordance'][idx],
                    data['padj'][idx],
                )

        real_threshold = 0.025
        if best_dist < real_threshold and best_info is not None:
            x, y, sym, cat, padj = best_info
            padj_str = f"{padj:.2e}" if not np.isnan(padj) else "N/A"
            text = (
                f"{sym}\n"
                f"RNA log2FC: {y:.3f}\n"
                f"ATAC log2FC: {x:.3f}\n"
                f"RNA padj: {padj_str}\n"
                f"{cat}"
            )
            self._annot.xy = (x, y)
            self._annot.set_text(text)
            xlim = self._ax.get_xlim()
            ylim = self._ax.get_ylim()
            xoff = -90 if (x > (xlim[0] + xlim[1]) / 2) else 12
            yoff = -60 if (y > (ylim[0] + ylim[1]) / 2) else 12
            self._annot.xyann = (xoff, yoff)
            self._annot.set_visible(True)
            self.canvas.draw_idle()
        else:
            if self._annot and self._annot.get_visible():
                self._annot.set_visible(False)
                self.canvas.draw_idle()

