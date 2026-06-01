"""
Quadrant Plot Dialog

X축: ATAC log2FC, Y축: RNA log2FC
각 사분면에 concordance 카테고리를 색상으로 표시합니다.
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
    QLabel, QFileDialog, QMessageBox,
)
from PyQt6.QtCore import Qt
import pandas as pd

from models.multi_omics_dataset import ConcordanceCategory, IntegratedColumns


class QuadrantPlotDialog(QDialog):
    """
    RNA log2FC vs ATAC log2FC Quadrant Plot

    Q1 (top-right)  : RNA↑ ATAC↑  → Concordant Both UP
    Q2 (top-left)   : RNA↑ ATAC↓  → Discordant RNA UP
    Q3 (bottom-left): RNA↓ ATAC↓  → Concordant Both DOWN
    Q4 (bottom-right): RNA↓ ATAC↑ → Discordant RNA DOWN
    """

    def __init__(self, integrated_df: pd.DataFrame, title: str = "Quadrant Plot", parent=None):
        super().__init__(parent)
        self.logger = logging.getLogger(__name__)
        self.df = integrated_df.copy()
        self.plot_title = title
        self.setWindowTitle("Quadrant Plot — RNA vs ATAC log2FC")
        self.resize(720, 620)
        self.setWindowFlags(
            self.windowFlags()
            | Qt.WindowType.WindowMaximizeButtonHint
            | Qt.WindowType.WindowMinimizeButtonHint
        )
        self._scatter_data = []   # hover용 데이터 저장
        self._annot = None
        self._ax = None
        self._init_ui()
        self._plot()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        # Canvas
        self.figure = Figure(figsize=(7, 6), dpi=100)
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
        self._scatter_data = []
        ax = self.figure.add_subplot(111)
        self._ax = ax

        col_rna  = IntegratedColumns.RNA_LOG2FC
        col_atac = IntegratedColumns.ATAC_LOG2FC_MEAN
        col_cat  = IntegratedColumns.CONCORDANCE
        col_sym  = IntegratedColumns.GENE_SYMBOL
        col_padj = IntegratedColumns.RNA_PADJ

        df = self.df.dropna(subset=[col_rna, col_atac])

        colors = ConcordanceCategory.COLORS

        for cat in ConcordanceCategory.ALL:
            sub = df[df[col_cat] == cat]
            if sub.empty:
                continue
            ax.scatter(
                sub[col_atac], sub[col_rna],
                c=colors.get(cat, "#CCCCCC"),
                s=30, alpha=0.7, linewidths=0.3,
                edgecolors="white", label=f"{cat} (n={len(sub)})",
                zorder=3,
            )
            # hover용 데이터 저장
            padj_vals = sub[col_padj].values if col_padj in sub.columns else np.full(len(sub), np.nan)
            self._scatter_data.append({
                'x': sub[col_atac].values.astype(float),
                'y': sub[col_rna].values.astype(float),
                'symbol': sub[col_sym].values.astype(str),
                'padj': padj_vals.astype(float),
                'concordance': sub[col_cat].values.astype(str),
            })

        # 기준선
        ax.axhline(0, color="gray", linewidth=0.8, linestyle="--", zorder=1)
        ax.axvline(0, color="gray", linewidth=0.8, linestyle="--", zorder=1)

        ax.set_xlabel("ATAC-seq log2FC (chromatin accessibility)", fontsize=11)
        ax.set_ylabel("RNA-seq log2FC (gene expression)", fontsize=11)
        ax.set_title(self.plot_title, fontsize=13, fontweight="bold")

        # 사분면 레이블
        xlim = ax.get_xlim()
        ylim = ax.get_ylim()
        xpad = (xlim[1] - xlim[0]) * 0.03
        ypad = (ylim[1] - ylim[0]) * 0.03
        ax.text(xlim[1] - xpad, ylim[1] - ypad, "Q1\nBoth↑",
                ha="right", va="top", fontsize=8, color="#D73027", alpha=0.7)
        ax.text(xlim[0] + xpad, ylim[1] - ypad, "Q2\nRNA↑ATAC↓",
                ha="left",  va="top", fontsize=8, color="#FC8D59", alpha=0.7)
        ax.text(xlim[0] + xpad, ylim[0] + ypad, "Q3\nBoth↓",
                ha="left",  va="bottom", fontsize=8, color="#4575B4", alpha=0.7)
        ax.text(xlim[1] - xpad, ylim[0] + ypad, "Q4\nRNA↓ATAC↑",
                ha="right", va="bottom", fontsize=8, color="#91BFDB", alpha=0.7)

        ax.legend(bbox_to_anchor=(1.01, 1), loc="upper left", fontsize=8, framealpha=0.7)
        self.figure.tight_layout()

        # 어노테이션 (hover 툴팁)
        self._annot = ax.annotate(
            "",
            xy=(0, 0), xytext=(12, 12), textcoords="offset points",
            bbox=dict(boxstyle="round,pad=0.4", fc="lightyellow", ec="gray", alpha=0.92),
            arrowprops=dict(arrowstyle="->", color="gray", lw=0.8),
            fontsize=8, zorder=10,
        )
        self._annot.set_visible(False)

        self.canvas.mpl_connect('motion_notify_event', self._on_mouse_move)
        self.canvas.draw()

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
        # 화면 범위의 2.5% 이내 점을 가장 가까운 점으로 인식
        threshold = 0.025 * min(x_range, y_range)

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

        # 실제 거리 임계값: 축 범위의 2.5%
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
            # 점이 오른쪽/위쪽에 있으면 툴팁을 반대 방향으로
            xlim = self._ax.get_xlim()
            ylim = self._ax.get_ylim()
            xoff = -90 if (x > (xlim[0] + xlim[1]) / 2) else 12
            yoff = -60 if (y > (ylim[0] + ylim[1]) / 2) else 12
            self._annot.xyann = (xoff, yoff)
            self._annot.set_visible(True)
            self.canvas.draw_idle()
        else:
            if self._annot.get_visible():
                self._annot.set_visible(False)
                self.canvas.draw_idle()

    def _on_save(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Figure", "quadrant_plot.png",
            "PNG (*.png);;SVG (*.svg);;PDF (*.pdf)"
        )
        if path:
            self.figure.savefig(path, dpi=150, bbox_inches="tight")
            self.logger.info(f"Quadrant plot saved: {path}")
