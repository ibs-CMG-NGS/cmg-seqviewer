"""
Concordance Summary Dialog

7개 카테고리별 유전자 수 및 비율을 막대 차트로 표시합니다.
"""

import logging
import numpy as np
import matplotlib
matplotlib.use('Qt5Agg')
logging.getLogger('matplotlib.font_manager').setLevel(logging.WARNING)
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QFileDialog, QTableWidget, QTableWidgetItem,
    QSplitter,
)
from PyQt6.QtCore import Qt
import pandas as pd

from models.multi_omics_dataset import ConcordanceCategory, IntegratedColumns


class ConcordanceSummaryDialog(QDialog):
    """
    7-category Concordance Summary Bar Chart + 집계 테이블
    """

    def __init__(self, integrated_df: pd.DataFrame, title: str = "Concordance Summary", parent=None):
        super().__init__(parent)
        self.logger = logging.getLogger(__name__)
        self.df = integrated_df.copy()
        self.plot_title = title
        self.setWindowTitle("Concordance Summary")
        self.resize(800, 580)
        self.setWindowFlags(
            self.windowFlags()
            | Qt.WindowType.WindowMaximizeButtonHint
            | Qt.WindowType.WindowMinimizeButtonHint
        )
        self._init_ui()
        self._plot()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # 왼쪽: 차트
        chart_widget = __import__('PyQt6.QtWidgets', fromlist=['QWidget']).QWidget()
        chart_layout = QVBoxLayout(chart_widget)
        self.figure = Figure(figsize=(5, 5), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self)
        chart_layout.addWidget(self.toolbar)
        chart_layout.addWidget(self.canvas)
        splitter.addWidget(chart_widget)

        # 오른쪽: 집계 테이블
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Category", "Count", "%"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        splitter.addWidget(self.table)

        splitter.setSizes([500, 280])
        layout.addWidget(splitter)

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
        ax = self.figure.add_subplot(111)

        col_cat = IntegratedColumns.CONCORDANCE
        counts  = self.df[col_cat].value_counts()
        total   = len(self.df)

        categories = ConcordanceCategory.ALL
        counts_ordered = [counts.get(c, 0) for c in categories]
        colors         = [ConcordanceCategory.COLORS.get(c, "#CCCCCC") for c in categories]
        short_labels   = [c.replace("_", "\n") for c in categories]

        bars = ax.bar(range(len(categories)), counts_ordered, color=colors,
                      edgecolor="white", linewidth=0.5)

        # 막대 위에 카운트 표시
        for bar, cnt in zip(bars, counts_ordered):
            if cnt > 0:
                pct = 100 * cnt / total if total > 0 else 0
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    bar.get_height() + 0.3,
                    f"{cnt}\n({pct:.1f}%)",
                    ha="center", va="bottom", fontsize=7,
                )

        ax.set_xticks(range(len(categories)))
        ax.set_xticklabels(short_labels, fontsize=7, rotation=20, ha="right")
        ax.set_ylabel("Gene count", fontsize=10)
        ax.set_title(self.plot_title, fontsize=12, fontweight="bold")
        ax.set_xlim(-0.5, len(categories) - 0.5)

        self.figure.tight_layout()
        self.canvas.draw()

        # 테이블 채우기
        self.table.setRowCount(len(categories))
        for i, (cat, cnt) in enumerate(zip(categories, counts_ordered)):
            pct = 100 * cnt / total if total > 0 else 0
            self.table.setItem(i, 0, QTableWidgetItem(cat.replace("_", " ")))
            cnt_item = QTableWidgetItem(str(cnt))
            cnt_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(i, 1, cnt_item)
            pct_item = QTableWidgetItem(f"{pct:.1f}%")
            pct_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(i, 2, pct_item)
        self.table.resizeColumnsToContents()

    def _on_save(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Figure", "concordance_summary.png",
            "PNG (*.png);;SVG (*.svg);;PDF (*.pdf)"
        )
        if path:
            self.figure.savefig(path, dpi=150, bbox_inches="tight")
            self.logger.info(f"Concordance summary saved: {path}")
