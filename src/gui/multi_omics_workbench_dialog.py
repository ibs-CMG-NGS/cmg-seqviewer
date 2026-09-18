"""
RNA + ATAC Integration Workbench

MultiOmicsPanel에서 "Integrate RNA + ATAC"를 누르면 열리는 다이얼로그.
JOIN(비싼 연산)은 한 번만 수행하고, 4개 유의성 cutoff는 라이브로 조절하면서
Quadrant Plot 미리보기로 즉시 확인할 수 있다. Apply를 눌러야 실제 데이터셋
탭에 커밋되며, 적용과 동시에 다이얼로그가 닫힌다. 다시 조절하려면 Multi-Omics
패널에서 워크벤치를 다시 연다.

GOClusteringDialog(fit 한 번 + threshold 변경 시 즉시 cut)와 동일한 패턴이지만,
RNA-ATAC JOIN은 hierarchical clustering보다 훨씬 가벼운 연산이라 백그라운드
스레드 없이 동기적으로 수행한다.
"""

import matplotlib
matplotlib.use('QtAgg')
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
try:
    from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
except ImportError:
    from matplotlib.backends.backend_qt import NavigationToolbar2QT as NavigationToolbar  # type: ignore
from matplotlib.figure import Figure

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, QFormLayout,
    QLabel, QPushButton, QDoubleSpinBox, QCheckBox, QMessageBox,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal

from models.data_models import Dataset
from models.multi_omics_dataset import ConcordanceCategory, IntegratedColumns
from gui.widgets.category_style_panel import CategoryStylePanel
from gui.widgets.quadrant_hover import QuadrantHoverTooltip


class MultiOmicsWorkbenchDialog(QDialog):
    """RNA + ATAC 통합 cutoff를 라이브로 조절하는 다이얼로그.

    Apply 시 MultiOmicsPanel.integrate_requested와 동일한 8-value 순서로
    integration_apply_requested를 emit한다 — main_window는 이를 그대로
    presenter.integrate_datasets(...)에 넘겨 기존 탭/트리/재현 레시피 로직을
    100% 재사용한다.
    """

    integration_apply_requested = pyqtSignal(
        str, str, str, int, float, float, float, float
    )

    def __init__(
        self,
        rna_dataset: Dataset,
        atac_dataset: Dataset,
        method: str = "nearest_gene",
        tss_window: int = 2000,
        rna_padj: float = 0.05,
        rna_lfc: float = 1.0,
        atac_padj: float = 0.05,
        atac_lfc: float = 1.0,
        parent=None,
    ):
        super().__init__(parent)
        self._rna_dataset = rna_dataset
        self._atac_dataset = atac_dataset
        self._method = method
        self._tss_window = tss_window

        self.setWindowTitle("RNA + ATAC Integration Workbench")
        self.setWindowFlags(
            self.windowFlags()
            | Qt.WindowType.WindowMaximizeButtonHint
            | Qt.WindowType.WindowMinimizeButtonHint
        )
        self.resize(1100, 750)
        from utils.dialog_geometry import remember_geometry
        remember_geometry(self)

        self._init_ui(rna_padj, rna_lfc, atac_padj, atac_lfc)
        self._hover = QuadrantHoverTooltip(self.canvas)

        # 비싼 부분: JOIN은 한 번만 (groupby + outer merge — 가벼운 연산이라 동기 실행)
        from utils.multi_omics_integrator import MultiOmicsIntegrator
        try:
            self._joined_df = MultiOmicsIntegrator().build_joined(
                rna_dataset.dataframe, atac_dataset.dataframe, method, tss_window
            )
        except Exception as e:
            QMessageBox.critical(self, "Join Error", f"RNA/ATAC join failed:\n{e}")
            self._joined_df = None

        # 라이브 재분류 디바운스 — 스핀박스 연타/휠 이벤트를 한 번으로 합침
        # (classify_dataframe 자체는 벡터화되어 저렴하지만, redraw 비용을 아낀다)
        self._recut_timer = QTimer(self)
        self._recut_timer.setSingleShot(True)
        self._recut_timer.setInterval(100)
        self._recut_timer.timeout.connect(self._refresh)
        for spin in (
            self.rna_padj_spin, self.rna_lfc_spin, self.atac_padj_spin, self.atac_lfc_spin,
        ):
            spin.valueChanged.connect(lambda _v: self._recut_timer.start())
        self.show_thresholds_cb.toggled.connect(lambda _v: self._recut_timer.start())
        self._cat_style.changed.connect(lambda: self._recut_timer.start())

        self._refresh()

    # ── UI ───────────────────────────────────────────────────────────────

    def _init_ui(self, rna_padj, rna_lfc, atac_padj, atac_lfc):
        layout = QHBoxLayout(self)

        # ── 좌측: cutoff + 표시 설정 ────────────────────────────────────
        left = QVBoxLayout()

        from gui.multi_omics_panel import MultiOmicsPanel

        thresh_group = QGroupBox("Significance Thresholds")
        thresh_form = QFormLayout(thresh_group)

        self.rna_padj_spin = QDoubleSpinBox()
        MultiOmicsPanel._setup_padj_spin(self.rna_padj_spin, rna_padj)
        thresh_form.addRow("RNA padj ≤", self.rna_padj_spin)

        self.rna_lfc_spin = QDoubleSpinBox()
        MultiOmicsPanel._setup_lfc_spin(self.rna_lfc_spin, rna_lfc)
        thresh_form.addRow("RNA |log2FC| ≥", self.rna_lfc_spin)

        self.atac_padj_spin = QDoubleSpinBox()
        MultiOmicsPanel._setup_padj_spin(self.atac_padj_spin, atac_padj)
        thresh_form.addRow("ATAC padj ≤", self.atac_padj_spin)

        self.atac_lfc_spin = QDoubleSpinBox()
        MultiOmicsPanel._setup_lfc_spin(self.atac_lfc_spin, atac_lfc)
        thresh_form.addRow("ATAC |log2FC| ≥", self.atac_lfc_spin)

        self.show_thresholds_cb = QCheckBox("Show threshold lines")
        self.show_thresholds_cb.setChecked(True)
        self.show_thresholds_cb.setToolTip(
            "RNA/ATAC |log2FC| cutoff 위치에 점선 기준선을 표시합니다(위 cutoff 값을 그대로 사용)."
        )
        thresh_form.addRow(self.show_thresholds_cb)

        left.addWidget(thresh_group)

        style_group = QGroupBox("Category Styles")
        style_layout = QVBoxLayout()
        self._cat_style = CategoryStylePanel(ConcordanceCategory.ALL, ConcordanceCategory.COLORS)
        style_layout.addWidget(self._cat_style)
        style_group.setLayout(style_layout)
        left.addWidget(style_group)

        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet("color:#444; font-size:9pt;")
        left.addWidget(self.status_label)

        left.addStretch()

        button_row = QHBoxLayout()
        self.apply_button = QPushButton("Apply")
        self.apply_button.setToolTip("현재 cutoff로 데이터셋 탭을 생성/갱신하고 창을 닫습니다.")
        self.apply_button.clicked.connect(self._on_apply)
        button_row.addWidget(self.apply_button)

        close_button = QPushButton("Close")
        close_button.clicked.connect(self.reject)
        button_row.addWidget(close_button)
        left.addLayout(button_row)

        layout.addLayout(left, 0)

        # ── 우측: Quadrant Plot 미리보기 ─────────────────────────────────
        right = QVBoxLayout()
        self.figure = Figure(figsize=(7, 6))
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self)
        right.addWidget(self.toolbar)
        right.addWidget(self.canvas)
        layout.addLayout(right, 1)

    # ── 라이브 재분류 / 렌더링 ────────────────────────────────────────────

    def _refresh(self):
        """싼 연산: 캐시된 self._joined_df를 재분류하고 Quadrant를 다시 그린다.
        re-join은 하지 않는다."""
        if self._joined_df is None:
            return

        from utils.multi_omics_integrator import MultiOmicsIntegrator
        from plots.quadrant import render_quadrant

        classified = MultiOmicsIntegrator.classify_dataframe(
            self._joined_df,
            self.rna_padj_spin.value(), self.rna_lfc_spin.value(),
            self.atac_padj_spin.value(), self.atac_lfc_spin.value(),
        )

        show_thresh = self.show_thresholds_cb.isChecked()
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        scatter_data = render_quadrant(ax, classified, {
            'category_styles': self._cat_style.get_styles(),
            'title': f"{self._rna_dataset.name} + {self._atac_dataset.name}",
            'rna_lfc_cutoff': self.rna_lfc_spin.value() if show_thresh else None,
            'atac_lfc_cutoff': self.atac_lfc_spin.value() if show_thresh else None,
        })
        self.figure.tight_layout()
        self._hover.bind(ax, scatter_data)
        self.canvas.draw()

        counts = classified[IntegratedColumns.CONCORDANCE].value_counts().to_dict()
        self.status_label.setText(
            "  |  ".join(f"{c}: {counts.get(c, 0)}" for c in ConcordanceCategory.ALL)
        )

    # ── Apply ────────────────────────────────────────────────────────────

    def _on_apply(self):
        if self._joined_df is None:
            return
        self.integration_apply_requested.emit(
            self._rna_dataset.name, self._atac_dataset.name, self._method, self._tss_window,
            self.rna_padj_spin.value(), self.rna_lfc_spin.value(),
            self.atac_padj_spin.value(), self.atac_lfc_spin.value(),
        )
        self.accept()
