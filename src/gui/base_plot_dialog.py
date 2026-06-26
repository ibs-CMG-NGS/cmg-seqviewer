"""모든 플롯 다이얼로그의 공통 기반 클래스."""
import matplotlib
matplotlib.use('QtAgg')
import logging
logging.getLogger('matplotlib.font_manager').setLevel(logging.WARNING)
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
try:
    from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
except ImportError:
    from matplotlib.backends.backend_qt import NavigationToolbar2QT as NavigationToolbar  # type: ignore
from matplotlib.figure import Figure

from PyQt6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QGroupBox, QScrollArea, QMessageBox, QFileDialog,
)
from PyQt6.QtCore import Qt

from utils import figure_theme, figure_export
from gui.widgets.figure_style_panel import FigureStylePanel
from gui.widgets.plot_labels_panel import PlotLabelsPanel


class BasePlotDialog(QDialog):
    """
    공통 기반 플롯 다이얼로그.

    서브클래스 구현 계약
    ─────────────────────
    필수:
      _setup_controls(layout: QVBoxLayout)  ← 좌측 패널 컨트롤 배치
      _do_plot()                            ← 실제 matplotlib 그리기

    선택 (기본값: empty → 버튼 숨김):
      _extra_buttons() → list[(label, callback)]  ← Export Data 등 추가 버튼
    """

    def __init__(self, title: str, parent=None, figsize=(10, 8)):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setWindowFlags(
            self.windowFlags()
            | Qt.WindowType.WindowMaximizeButtonHint
            | Qt.WindowType.WindowMinimizeButtonHint
        )

        self.figure = Figure(figsize=figsize)
        self.canvas = FigureCanvas(self.figure)

        self._style = FigureStylePanel()
        self._style.changed.connect(self._update_plot)

        self._labels = PlotLabelsPanel()
        self._labels.changed.connect(self._update_plot)

        self._init_layout()

    # ── 레이아웃 ──────────────────────────────────────────────────────────────

    def _init_layout(self):
        main = QHBoxLayout(self)
        main.setContentsMargins(4, 4, 4, 4)
        main.setSpacing(4)

        # 좌측: 스크롤 가능 설정 패널
        left_container = QWidget()
        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(4, 4, 4, 4)

        self._setup_controls(left_layout)           # 서브클래스 제공

        labels_group = QGroupBox("Plot Labels & Legend")
        lv = QVBoxLayout()
        lv.addWidget(self._labels)
        labels_group.setLayout(lv)
        left_layout.addWidget(labels_group)

        style_group = QGroupBox("Figure Style & Export")
        sv = QVBoxLayout()
        sv.addWidget(self._style)
        style_group.setLayout(sv)
        left_layout.addWidget(style_group)
        left_layout.addStretch()

        scroll = QScrollArea()
        scroll.setWidget(left_container)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setMinimumWidth(220)
        scroll.setMaximumWidth(300)
        main.addWidget(scroll)

        # 우측: 툴바 + 캔버스 + 버튼 바
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)

        toolbar = NavigationToolbar(self.canvas, self)
        right_layout.addWidget(toolbar)
        right_layout.addWidget(self.canvas)
        right_layout.addLayout(self._build_button_bar())

        main.addWidget(right, stretch=3)

    def _build_button_bar(self) -> QHBoxLayout:
        bar = QHBoxLayout()

        refresh_btn = QPushButton("Refresh Plot")
        refresh_btn.clicked.connect(self._update_plot)
        bar.addWidget(refresh_btn)

        save_btn = QPushButton("Save Figure")
        save_btn.clicked.connect(self._save_figure)
        bar.addWidget(save_btn)

        for label, callback in (self._extra_buttons() or []):
            btn = QPushButton(label)
            btn.clicked.connect(callback)
            bar.addWidget(btn)

        bar.addStretch()

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        bar.addWidget(close_btn)

        return bar

    # ── 서브클래스 훅 ─────────────────────────────────────────────────────────

    def _setup_controls(self, layout: QVBoxLayout):
        """서브클래스: 좌측 패널에 도메인 컨트롤 추가."""

    def _extra_buttons(self) -> list:
        """서브클래스: [(label, callback)] 추가 버튼 목록. 없으면 빈 리스트."""
        return []

    def _do_plot(self):
        """서브클래스: 실제 matplotlib 그리기 로직."""

    # ── 공용 메서드 ───────────────────────────────────────────────────────────

    def _apply_labels(self):
        """첫 번째 Axes에 PlotLabelsPanel 설정 적용. 멀티 Axes 다이얼로그는 오버라이드."""
        if self.figure.axes:
            self._labels.apply_to_axes(self.figure.axes[0])

    def _update_plot(self):
        with figure_theme.theme_context(self._style.theme_name()):
            self._do_plot()
            self._apply_labels()
        self.canvas.draw_idle()

    def _save_figure(self):
        opts = self._style.export_opts()
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Figure",
            f"figure.{opts['fmt']}",
            figure_export.filter_string(),
        )
        if not path:
            return
        try:
            saved = figure_export.save_figure(self.figure, path, **opts)
            QMessageBox.information(self, "Saved", f"Figure saved to:\n{saved}")
        except ValueError as e:
            QMessageBox.warning(self, "Unsupported Format", str(e))
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Failed to save:\n{e}")
