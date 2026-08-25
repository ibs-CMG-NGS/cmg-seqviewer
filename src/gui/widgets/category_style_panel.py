"""카테고리별 color/point size/alpha 컨트롤 그리드.

concordance 카테고리처럼 고정된 카테고리 집합을 갖는 scatter 플롯에서, 카테고리마다
색상·크기·투명도를 개별 조절할 수 있게 한다. PlotLabelsPanel과 동일한 changed 규약
(pyqtSignal, 다이얼로그가 직접 _update_plot에 연결)을 따른다.
"""
from PyQt6.QtWidgets import (
    QWidget, QGridLayout, QLabel, QPushButton, QSpinBox, QDoubleSpinBox, QColorDialog,
)
from PyQt6.QtGui import QColor
from PyQt6.QtCore import pyqtSignal


class CategoryStylePanel(QWidget):
    """카테고리별 color swatch + size + alpha 그리드."""

    changed = pyqtSignal()

    def __init__(
        self,
        categories: list,
        default_colors: dict,
        default_size: int = 30,
        default_alpha: float = 0.70,
        parent=None,
    ):
        super().__init__(parent)
        self._categories = list(categories)
        self._colors = {c: default_colors.get(c, "#CCCCCC") for c in self._categories}

        grid = QGridLayout(self)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setVerticalSpacing(3)
        grid.setHorizontalSpacing(6)

        self._swatches = {}
        self._size_spins = {}
        self._alpha_spins = {}

        for row, cat in enumerate(self._categories):
            label = QLabel(cat.replace("_", " "))
            label.setToolTip(cat)
            grid.addWidget(label, row, 0)

            swatch = QPushButton()
            swatch.setFixedSize(22, 22)
            swatch.setToolTip(f"Click to change color for {cat}")
            self._style_swatch(swatch, self._colors[cat])
            swatch.clicked.connect(self._make_picker(cat, swatch))
            grid.addWidget(swatch, row, 1)

            size_spin = QSpinBox()
            size_spin.setRange(5, 200)
            size_spin.setValue(default_size)
            size_spin.setToolTip("Point size")
            size_spin.valueChanged.connect(self.changed)
            grid.addWidget(size_spin, row, 2)

            alpha_spin = QDoubleSpinBox()
            alpha_spin.setRange(0.05, 1.0)
            alpha_spin.setDecimals(2)
            alpha_spin.setSingleStep(0.05)
            alpha_spin.setValue(default_alpha)
            alpha_spin.setToolTip("Alpha (transparency)")
            alpha_spin.valueChanged.connect(self.changed)
            grid.addWidget(alpha_spin, row, 3)

            self._swatches[cat] = swatch
            self._size_spins[cat] = size_spin
            self._alpha_spins[cat] = alpha_spin

    # ── 내부 ──────────────────────────────────────────────────────────────

    def _make_picker(self, cat: str, btn: QPushButton):
        def _pick():
            color = QColorDialog.getColor(QColor(self._colors[cat]), self, f"Color for {cat}")
            if color.isValid():
                self._colors[cat] = color.name()
                self._style_swatch(btn, color.name())
                self.changed.emit()
        return _pick

    @staticmethod
    def _style_swatch(btn: QPushButton, hex_color: str):
        btn.setStyleSheet(
            f"QPushButton {{ background-color: {hex_color}; "
            f"border: 1px solid #888; border-radius: 3px; }}"
        )

    # ── 공개 API ──────────────────────────────────────────────────────────

    def get_styles(self) -> dict:
        """카테고리 -> {'color', 'size', 'alpha'} dict. render_quadrant의 category_styles로 그대로 전달."""
        return {
            cat: {
                'color': self._colors[cat],
                'size': self._size_spins[cat].value(),
                'alpha': self._alpha_spins[cat].value(),
            }
            for cat in self._categories
        }
