"""공용 Figure 스타일/내보내기 컨트롤 위젯."""
from PyQt6.QtWidgets import (
    QWidget, QFormLayout, QHBoxLayout, QComboBox, QDoubleSpinBox, QPushButton,
)
from PyQt6.QtCore import pyqtSignal, QSettings
from utils import figure_theme


class FigureStylePanel(QWidget):
    """테마/사이징/내보내기 공용 컨트롤. 테마 변경 시 changed 신호 방출."""

    changed = pyqtSignal()  # 다시 그려야 하는 변경 (테마)

    def __init__(self, parent=None):
        super().__init__(parent)
        form = QFormLayout(self)
        form.setContentsMargins(0, 0, 0, 0)

        # ── 테마 선택 + Edit 버튼 ──────────────────────────
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(figure_theme.list_themes())
        self.theme_combo.currentTextChanged.connect(self._on_theme_changed)

        self._edit_btn = QPushButton("Edit…")
        self._edit_btn.setFixedWidth(52)
        self._edit_btn.setToolTip("Edit Custom theme parameters")
        self._edit_btn.clicked.connect(self._open_customize)

        theme_row = QWidget()
        theme_layout = QHBoxLayout(theme_row)
        theme_layout.setContentsMargins(0, 0, 0, 0)
        theme_layout.addWidget(self.theme_combo, stretch=1)
        theme_layout.addWidget(self._edit_btn)
        form.addRow("Theme:", theme_row)

        self._update_edit_btn()

        # ── 저장 크기 (mm) ────────────────────────────────
        self.width_mm = QDoubleSpinBox()
        self.width_mm.setRange(30, 400)
        self.width_mm.setValue(85)
        self.width_mm.setSuffix(" mm")
        self.height_mm = QDoubleSpinBox()
        self.height_mm.setRange(30, 400)
        self.height_mm.setValue(70)
        self.height_mm.setSuffix(" mm")
        form.addRow("Export W:", self.width_mm)
        form.addRow("Export H:", self.height_mm)

        # ── DPI ───────────────────────────────────────────
        self.dpi_combo = QComboBox()
        self.dpi_combo.addItems(["300", "600", "150"])
        form.addRow("DPI (raster):", self.dpi_combo)

        # ── 포맷 ──────────────────────────────────────────
        self.fmt_combo = QComboBox()
        self.fmt_combo.addItems(["pdf", "svg", "png", "tiff", "eps"])
        form.addRow("Format:", self.fmt_combo)

        # ── QSettings에서 Custom 테마 복원 ─────────────────
        self._load_custom_from_settings()

    # ─────────────────────────────────────────────────────────
    def _load_custom_from_settings(self):
        settings = QSettings("RNASeqDataView", "MainWindow")
        params = figure_theme.load_custom_params(settings)
        figure_theme.update_custom_theme(params)

    def _on_theme_changed(self, _):
        self._update_edit_btn()
        self.changed.emit()

    def _update_edit_btn(self):
        """Custom 선택 시 Edit 버튼 강조, 다른 테마에서는 보조 표시."""
        is_custom = self.theme_combo.currentText() == 'Custom'
        self._edit_btn.setEnabled(True)
        self._edit_btn.setStyleSheet(
            "font-weight: bold;" if is_custom else ""
        )

    def _open_customize(self):
        from gui.widgets.theme_customize_dialog import ThemeCustomizeDialog
        dlg = ThemeCustomizeDialog(self)
        if dlg.exec():
            # 테마를 Custom으로 전환하고 리드로우
            idx = self.theme_combo.findText('Custom')
            if idx >= 0:
                self.theme_combo.blockSignals(True)
                self.theme_combo.setCurrentIndex(idx)
                self.theme_combo.blockSignals(False)
            self._update_edit_btn()
            self.changed.emit()

    # ─────────────────────────────────────────────────────────
    def theme_name(self) -> str:
        return self.theme_combo.currentText()

    def size_mm(self) -> tuple:
        return (self.width_mm.value(), self.height_mm.value())

    def export_opts(self) -> dict:
        return {
            "fmt": self.fmt_combo.currentText(),
            "dpi": int(self.dpi_combo.currentText()),
            "size_mm": self.size_mm(),
        }
