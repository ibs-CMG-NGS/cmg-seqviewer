"""Pinned plot tab — 어떤 플롯이든 탭에 고정하는 범용 스냅샷 위젯.

(plot_type, dataframe, plot_params) 만으로 src/plots 레지스트리의 렌더 함수를 호출해
다시 그린다. 각 플롯 다이얼로그를 임베드 가능한 위젯으로 개별 리팩터할 필요가 없다.

스냅샷이므로 탭 안에서 설정을 편집하지는 않는다(설정 변경은 원래 다이얼로그를 다시 연다).
Save Figure / Export Bundle 은 탭에서 바로 가능하다.
"""
import logging

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QFileDialog, QMessageBox, QLabel,
)
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
try:
    from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
except ImportError:  # pragma: no cover
    from matplotlib.backends.backend_qt import NavigationToolbar2QT as NavigationToolbar  # type: ignore
from matplotlib.figure import Figure

from utils import figure_export
from plots.registry import render_to_figure, is_supported


class PinnedPlotWidget(QWidget):
    """탭에 고정된 플롯. plot_type + df + params 로 재렌더한다."""

    def __init__(self, plot_type: str, dataframe, plot_params: dict,
                 figure_title: str = "", dataset_name: str = "",
                 figsize=(10, 7), parent=None):
        super().__init__(parent)
        self.logger = logging.getLogger(__name__)
        self.plot_type = plot_type or ""
        self.dataframe = dataframe
        self.plot_params = dict(plot_params or {})
        self.figure_title = figure_title or self.plot_type or "Plot"
        self.dataset_name = dataset_name or "unknown"

        w = float(self.plot_params.get('fig_width', figsize[0]) or figsize[0])
        h = float(self.plot_params.get('fig_height', figsize[1]) or figsize[1])
        self.figure = Figure(figsize=(w, h))
        self.canvas = FigureCanvas(self.figure)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.addWidget(NavigationToolbar(self.canvas, self))
        layout.addWidget(self.canvas, stretch=1)

        bar = QHBoxLayout()
        bar.addWidget(QLabel(f"📌 {self.figure_title}"))
        bar.addStretch()
        save_btn = QPushButton("Save Figure")
        save_btn.clicked.connect(self._save_figure)
        bar.addWidget(save_btn)
        bundle_btn = QPushButton("Export Bundle")
        bundle_btn.clicked.connect(self._export_bundle)
        bar.addWidget(bundle_btn)
        layout.addLayout(bar)

        self._render()

    # ── Render ────────────────────────────────────────────────────────────

    def _render(self):
        self.figure.clear()
        try:
            ok = render_to_figure(self.figure, self.plot_type, self.dataframe, self.plot_params)
            if not ok:
                ax = self.figure.add_subplot(111)
                ax.text(0.5, 0.5,
                        f"'{self.plot_type}' is not a re-renderable plot type.",
                        ha='center', va='center', fontsize=12,
                        color='#888888', transform=ax.transAxes)
                ax.axis('off')
        except Exception as e:  # noqa: BLE001 — 탭 렌더 실패가 앱을 죽이지 않도록
            self.logger.warning(f"Pinned plot render failed ({self.plot_type}): {e}",
                                exc_info=True)
            self.figure.clear()
            ax = self.figure.add_subplot(111)
            ax.text(0.5, 0.5, f"Could not draw plot:\n{e}", ha='center', va='center',
                    fontsize=11, color='#a00', transform=ax.transAxes, wrap=True)
            ax.axis('off')
        self.canvas.draw()

    def refresh(self):
        self._render()

    # ── Export ────────────────────────────────────────────────────────────

    def _save_figure(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Figure", f"{self.plot_type or 'plot'}",
            figure_export.filter_string(),
        )
        if not path:
            return
        try:
            saved = figure_export.save_figure(self.figure, path)
            QMessageBox.information(self, "Saved", f"Figure saved:\n{saved}")
        except Exception as e:  # noqa: BLE001
            QMessageBox.critical(self, "Save failed", str(e))

    def get_plot_params(self) -> dict:
        return dict(self.plot_params)

    def get_bundle_context(self) -> dict:
        slug = (self.plot_type or 'figure') + '_plot'
        return {
            'figure': self.figure,
            'dataframe': self.dataframe,
            'plot_params': self.plot_params,
            'dataset_name': self.dataset_name,
            'plot_type': self.plot_type,
            'figure_title': self.figure_title,
            'figure_slug': slug,
            'source_stem': slug,
            'notes': 'Generated from a cmg-seqviewer pinned plot tab',
        }

    def _export_bundle(self):
        from utils.figure_bundle_export import export_figure_bundle
        ctx = self.get_bundle_context()
        slug = ctx.get('figure_slug', 'figure_bundle')
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Figure Bundle — choose folder name",
            f"{slug}_bundle", "Figure Bundle Folder (*)",
        )
        if not path:
            return
        try:
            bundle_dir = export_figure_bundle(
                ctx, path, slug, ctx.get('figure_title', 'Figure'),
                ctx.get('plot_type', 'plot'),
            )
            QMessageBox.information(self, "Bundle exported", f"Bundle created at:\n{bundle_dir}")
        except Exception as e:  # noqa: BLE001
            QMessageBox.critical(self, "Bundle export failed", str(e))
