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

    @staticmethod
    def _fit_settings_scroll_width(scroll: QScrollArea, container: QWidget,
                                   min_w: int = 260, max_w: int = 560) -> None:
        """좌측 설정 패널을 콘텐츠 폭에 맞춰 잡아 짤림/가로 스크롤을 없앤다.

        긴 항목을 가진 콤보박스는 기본적으로 항목 전체 폭을 최소폭으로 강제해 패널을
        과도하게 넓히거나 짤림을 유발한다. 먼저 콤보를 '축소 가능'하게 바꿔(접힌 박스는
        좁게, 드롭다운/툴팁은 전체 표시) 그 원인을 제거한 뒤, 남은 콘텐츠의 minimumSizeHint
        에 맞춰 스크롤 폭을 정한다."""
        from PyQt6.QtWidgets import QComboBox, QSizePolicy
        for cb in container.findChildren(QComboBox):
            # QComboBox 는 가장 긴 항목 폭을 minimumSizeHint 로 강제해 패널을 넓히거나
            # 짤림을 유발한다. 가로 정책을 Ignored 로 바꾸면 레이아웃이 그 힌트를 무시하고
            # 콤보는 배정된 폭 안에서 줄어든다(현재 값은 "…"로 elide, 드롭다운/툴팁은 전체).
            cb.setSizePolicy(QSizePolicy.Policy.Ignored, cb.sizePolicy().verticalPolicy())
            cb.setMinimumWidth(110)
            if not cb.toolTip():
                cb.setToolTip(cb.currentText())
        container.adjustSize()

        scrollbar_w = scroll.verticalScrollBar().sizeHint().width()
        needed = container.minimumSizeHint().width() + scrollbar_w + 8
        width = int(min(max_w, max(min_w, needed)))
        scroll.setMinimumWidth(width)
        scroll.setMaximumWidth(width + 40)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

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
        self._fit_settings_scroll_width(scroll, left_container)
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

        # get_bundle_context()를 구현한 다이얼로그는 재현 번들 export 버튼을 자동 노출
        if hasattr(self, "get_bundle_context"):
            bundle_btn = QPushButton("Export Bundle")
            bundle_btn.setToolTip("재현 가능한 figure 번들(데이터+스크립트+메타)로 export")
            bundle_btn.clicked.connect(self._on_export_bundle)
            bar.addWidget(bundle_btn)

            # 재렌더 가능한 plot_type 이면 탭 고정 버튼도 자동 노출
            try:
                from plots.registry import is_supported
                if is_supported(self.get_bundle_context().get("plot_type", "")):
                    pin_btn = QPushButton("📌 Pin to Tab")
                    pin_btn.setToolTip("이 플롯을 메인 창의 탭으로 고정합니다(스냅샷).")
                    pin_btn.clicked.connect(self._on_pin_to_tab)
                    bar.addWidget(pin_btn)
            except Exception:  # noqa: BLE001 — 버튼 노출 실패가 다이얼로그를 막지 않도록
                pass

        bar.addStretch()

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        bar.addWidget(close_btn)

        return bar

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
        """현재 플롯을 메인 창 탭으로 고정 (공용)."""
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

    def _on_export_bundle(self):
        """get_bundle_context() 를 재현 번들로 export (공용).

        기본 폴더 이름은 {slug}_bundle 로 제안하되, Save 대화상자에서 사용자가 위치와
        폴더 이름을 자유롭게 바꿀 수 있다.
        """
        context = self.get_bundle_context()
        slug = context.get("figure_slug", "figure_bundle")
        path = self._prompt_bundle_path(f"{slug}_bundle")
        if not path:
            return
        try:
            from utils.figure_bundle_export import export_figure_bundle
            bundle_dir = export_figure_bundle(
                context,
                path,
                slug,
                context.get("figure_title", "Figure"),
                context.get("plot_type", "plot"),
            )
            QMessageBox.information(self, "Bundle exported", f"Bundle created at:\n{bundle_dir}")
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Bundle export failed", str(exc))

    def _prompt_bundle_path(self, default_name: str) -> str:
        """번들 폴더 경로를 Save 대화상자로 받는다(이름 편집 가능). 취소 시 빈 문자열."""
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Figure Bundle — choose folder name",
            default_name,
            "Figure Bundle Folder (*)",
        )
        return path

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
