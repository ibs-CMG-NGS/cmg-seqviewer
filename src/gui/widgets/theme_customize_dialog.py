"""Custom 테마 편집 다이얼로그."""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QGroupBox,
    QDoubleSpinBox, QCheckBox, QLineEdit,
    QDialogButtonBox, QLabel,
)
from PyQt6.QtCore import QSettings
from utils import figure_theme


class ThemeCustomizeDialog(QDialog):
    """사용자 정의 테마 파라미터 편집."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Custom Theme")
        self.setMinimumWidth(340)

        settings = QSettings("RNASeqDataView", "MainWindow")
        params = figure_theme.load_custom_params(settings)

        layout = QVBoxLayout(self)

        # ── Font sizes ──────────────────────────────────────
        font_group = QGroupBox("Font Sizes (pt)")
        font_form = QFormLayout(font_group)

        self.font_size    = self._spin(params['font_size'],   4, 24, font_form, "Base:")
        self.title_size   = self._spin(params['title_size'],  4, 32, font_form, "Title:")
        self.label_size   = self._spin(params['label_size'],  4, 24, font_form, "Axis label:")
        self.tick_size    = self._spin(params['tick_size'],   4, 20, font_form, "Tick label:")
        self.legend_size  = self._spin(params['legend_size'], 4, 20, font_form, "Legend:")
        layout.addWidget(font_group)

        # ── Lines & ticks ────────────────────────────────────
        line_group = QGroupBox("Lines & Ticks")
        line_form = QFormLayout(line_group)

        self.line_width  = self._spin(params['line_width'],  0.1, 4.0, line_form, "Axis linewidth:",  step=0.1, decimals=1)
        self.tick_length = self._spin(params['tick_length'], 0.0, 12.0, line_form, "Tick length:",    step=0.5, decimals=1)
        layout.addWidget(line_group)

        # ── Spines & Grid ────────────────────────────────────
        style_group = QGroupBox("Spines & Grid")
        style_form = QFormLayout(style_group)

        self.spine_top   = QCheckBox()
        self.spine_top.setChecked(bool(params['spine_top']))
        style_form.addRow("Show top spine:", self.spine_top)

        self.spine_right = QCheckBox()
        self.spine_right.setChecked(bool(params['spine_right']))
        style_form.addRow("Show right spine:", self.spine_right)

        self.grid = QCheckBox()
        self.grid.setChecked(bool(params['grid']))
        style_form.addRow("Show grid:", self.grid)

        layout.addWidget(style_group)

        # ── Font family ──────────────────────────────────────
        font_fam_group = QGroupBox("Font Family (comma-separated, first available used)")
        font_fam_layout = QVBoxLayout(font_fam_group)
        self.font_family = QLineEdit(params['font_family'])
        font_fam_layout.addWidget(self.font_family)
        font_fam_layout.addWidget(QLabel("e.g.  Arial, DejaVu Sans"))
        layout.addWidget(font_fam_group)

        # ── Buttons ──────────────────────────────────────────
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel |
            QDialogButtonBox.StandardButton.RestoreDefaults
        )
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        buttons.button(QDialogButtonBox.StandardButton.RestoreDefaults).clicked.connect(
            self._restore_defaults
        )
        layout.addWidget(buttons)

    # ─────────────────────────────────────────────────────────
    def _spin(self, value, lo, hi, form, label,
              step=1.0, decimals=0) -> QDoubleSpinBox:
        w = QDoubleSpinBox()
        w.setRange(lo, hi)
        w.setSingleStep(step)
        w.setDecimals(decimals)
        w.setValue(float(value))
        form.addRow(label, w)
        return w

    def _collect(self) -> dict:
        return {
            'font_size':   self.font_size.value(),
            'title_size':  self.title_size.value(),
            'label_size':  self.label_size.value(),
            'tick_size':   self.tick_size.value(),
            'legend_size': self.legend_size.value(),
            'line_width':  self.line_width.value(),
            'tick_length': self.tick_length.value(),
            'spine_top':   self.spine_top.isChecked(),
            'spine_right': self.spine_right.isChecked(),
            'grid':        self.grid.isChecked(),
            'font_family': self.font_family.text().strip() or 'DejaVu Sans',
        }

    def _accept(self):
        params = self._collect()
        settings = QSettings("RNASeqDataView", "MainWindow")
        figure_theme.save_custom_params(settings, params)
        figure_theme.update_custom_theme(params)
        self.accept()

    def _restore_defaults(self):
        d = figure_theme.CUSTOM_DEFAULTS
        self.font_size.setValue(d['font_size'])
        self.title_size.setValue(d['title_size'])
        self.label_size.setValue(d['label_size'])
        self.tick_size.setValue(d['tick_size'])
        self.legend_size.setValue(d['legend_size'])
        self.line_width.setValue(d['line_width'])
        self.tick_length.setValue(d['tick_length'])
        self.spine_top.setChecked(d['spine_top'])
        self.spine_right.setChecked(d['spine_right'])
        self.grid.setChecked(d['grid'])
        self.font_family.setText(d['font_family'])
