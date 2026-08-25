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
    QLabel, QLineEdit, QFileDialog, QTableWidget, QTableWidgetItem,
    QSplitter, QMessageBox,
)
from PyQt6.QtCore import Qt
import pandas as pd

from models.multi_omics_dataset import ConcordanceCategory, IntegratedColumns
from utils.export_paths import remembered_save_path


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
        self._ax = None
        self._init_ui()
        self._plot()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        # 타이틀 편집 바
        title_layout = QHBoxLayout()
        title_layout.addWidget(QLabel("Title:"))
        self.title_edit = QLineEdit(self.plot_title)
        self.title_edit.textChanged.connect(self._update_title)
        title_layout.addWidget(self.title_edit)
        layout.addLayout(title_layout)

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
        btn_layout.addWidget(save_btn)
        bundle_btn = QPushButton("Export Bundle")
        bundle_btn.setToolTip("재현 가능한 figure 번들(데이터+스크립트+메타)로 export")
        bundle_btn.clicked.connect(self._on_export_bundle)
        btn_layout.addWidget(bundle_btn)
        pin_btn = QPushButton("📌 Pin to Tab")
        pin_btn.setToolTip("이 플롯을 메인 창의 탭으로 고정합니다(스냅샷).")
        pin_btn.clicked.connect(self._on_pin_to_tab)
        btn_layout.addWidget(pin_btn)
        btn_layout.addStretch()
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

    def _plot_params(self) -> dict:
        return {'title': self.title_edit.text()}

    def _plot(self):
        """렌더는 순수 함수 src/plots/concordance_summary.py 에 있으며 번들과 공유한다."""
        from plots.concordance_summary import render_concordance_summary

        self.figure.clear()
        ax = self.figure.add_subplot(111)
        self._ax = ax

        render_concordance_summary(ax, self.df, self._plot_params())

        self.figure.tight_layout()
        self.canvas.draw()

        col_cat = IntegratedColumns.CONCORDANCE
        counts  = self.df[col_cat].value_counts()
        total   = len(self.df)
        categories = ConcordanceCategory.ALL
        counts_ordered = [counts.get(c, 0) for c in categories]

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

    def _update_title(self, text: str):
        if self._ax:
            self._ax.set_title(text, fontsize=12, fontweight="bold")
            self.canvas.draw_idle()

    def _on_save(self):
        path, _ = remembered_save_path(
            self, "Save Figure", "concordance_summary.png",
            "PNG (*.png);;SVG (*.svg);;PDF (*.pdf)"
        )
        if path:
            self.figure.savefig(path, dpi=150, bbox_inches="tight")
            self.logger.info(f"Concordance summary saved: {path}")

    # ── Bundle export / Pin to Tab ──────────────────────────────────────────
    # BasePlotDialog를 상속하지 않는 다이얼로그라 동일 기능을 자체적으로 갖춘다
    # (gui/base_plot_dialog.py의 _on_export_bundle/_on_pin_to_tab과 동일한 로직).

    def get_bundle_context(self) -> dict:
        return {
            'figure': self.figure,
            'dataframe': self.df,
            'plot_params': self._plot_params(),
            'dataset_name': self.plot_title,
            'plot_type': 'concordance_summary',
            'figure_title': self.title_edit.text(),
            'figure_slug': 'concordance_summary',
            'source_stem': 'concordance_summary',
            'notes': 'Generated from cmg-seqviewer Concordance Summary (RNA vs ATAC) plot',
        }

    def _on_export_bundle(self):
        context = self.get_bundle_context()
        slug = context.get("figure_slug", "figure_bundle")
        path, _ = remembered_save_path(
            self, "Export Figure Bundle — choose folder name",
            f"{slug}_bundle", "Figure Bundle Folder (*)",
        )
        if not path:
            return
        try:
            from utils.figure_bundle_export import export_figure_bundle
            bundle_dir = export_figure_bundle(
                context, path, slug,
                context.get("figure_title", "Figure"),
                context.get("plot_type", "plot"),
            )
            QMessageBox.information(self, "Bundle exported", f"Bundle created at:\n{bundle_dir}")
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Bundle export failed", str(exc))

    def _find_pin_host(self):
        """부모 체인을 거슬러 pin_plot_from_context() 를 가진 메인 윈도우를 찾는다."""
        w = self.parent()
        seen = 0
        while w is not None and seen < 10:
            if hasattr(w, "pin_plot_from_context"):
                return w
            w = w.parent() if hasattr(w, "parent") else None
            seen += 1
        return None

    def _on_pin_to_tab(self):
        host = self._find_pin_host()
        if host is None:
            QMessageBox.information(
                self, "Pin to Tab",
                "이 창에서는 탭 고정을 사용할 수 없습니다 (메인 창에서 열어주세요).")
            return
        try:
            host.pin_plot_from_context(self.get_bundle_context())
            QMessageBox.information(self, "Pinned",
                                    "플롯을 메인 창의 탭으로 고정했습니다.")
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Pin failed", str(exc))
