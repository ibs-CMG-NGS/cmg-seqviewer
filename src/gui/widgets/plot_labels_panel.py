"""플롯 타이틀·축 레이블·틱·범례 통합 컨트롤 위젯."""
from PyQt6.QtWidgets import (
    QWidget, QFormLayout, QLineEdit, QCheckBox, QComboBox,
    QHBoxLayout,
)
from PyQt6.QtCore import pyqtSignal


class PlotLabelsPanel(QWidget):
    """
    모든 플롯 다이얼로그에서 공통으로 쓰는 레이블/범례 설정 패널.

    동작 규칙
    ─────────
    Title / X Label / Y Label:
      - 값이 있으면 → ax에 적용 (override)
      - 비어 있으면 → ax에 적용 안 함 (단, 사용자가 직접 비운 경우는 '' 적용)
      - set_defaults() 로 프로그래매틱 초기화 시 수정 플래그 불변

    Tick labels: 체크박스 상태 항상 적용 (기본 on)
    Legend: 체크박스 on/off + 위치 콤보 항상 적용 (기본 on)
    """

    changed = pyqtSignal()

    LEGEND_POSITIONS = [
        'best',
        'upper right', 'upper left',
        'lower right', 'lower left',
        'center left', 'center right',
        'upper center', 'lower center',
        'center',
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        form = QFormLayout(self)
        form.setContentsMargins(0, 0, 0, 0)
        form.setVerticalSpacing(4)

        # ── 수정 플래그 (textEdited만 감지) ──────────────────────────
        self._title_edited = False
        self._xlabel_edited = False
        self._ylabel_edited = False

        # ── Title ────────────────────────────────────────────────────
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("empty = no title")
        self.title_edit.textEdited.connect(lambda: self._set_edited('title'))
        self.title_edit.textChanged.connect(self.changed)
        form.addRow("Title:", self.title_edit)

        # ── X Label ──────────────────────────────────────────────────
        self.xlabel_edit = QLineEdit()
        self.xlabel_edit.setPlaceholderText("empty = no label")
        self.xlabel_edit.textEdited.connect(lambda: self._set_edited('xlabel'))
        self.xlabel_edit.textChanged.connect(self.changed)
        form.addRow("X Label:", self.xlabel_edit)

        # ── Y Label ──────────────────────────────────────────────────
        self.ylabel_edit = QLineEdit()
        self.ylabel_edit.setPlaceholderText("empty = no label")
        self.ylabel_edit.textEdited.connect(lambda: self._set_edited('ylabel'))
        self.ylabel_edit.textChanged.connect(self.changed)
        form.addRow("Y Label:", self.ylabel_edit)

        # ── Tick labels (X / Y 나란히) ────────────────────────────────
        ticks_row = QWidget()
        tl = QHBoxLayout(ticks_row)
        tl.setContentsMargins(0, 0, 0, 0)
        tl.setSpacing(12)

        self.xticklabels_check = QCheckBox("X")
        self.xticklabels_check.setChecked(True)
        self.xticklabels_check.stateChanged.connect(self.changed)
        tl.addWidget(self.xticklabels_check)

        self.yticklabels_check = QCheckBox("Y")
        self.yticklabels_check.setChecked(True)
        self.yticklabels_check.stateChanged.connect(self.changed)
        tl.addWidget(self.yticklabels_check)
        tl.addStretch()
        form.addRow("Tick labels:", ticks_row)

        # ── Legend: show + position ───────────────────────────────────
        legend_row = QWidget()
        ll = QHBoxLayout(legend_row)
        ll.setContentsMargins(0, 0, 0, 0)
        ll.setSpacing(6)

        self.legend_check = QCheckBox("Show")
        self.legend_check.setChecked(True)
        self.legend_check.stateChanged.connect(self._on_legend_toggle)
        ll.addWidget(self.legend_check)

        self.legend_pos_combo = QComboBox()
        self.legend_pos_combo.addItems(self.LEGEND_POSITIONS)
        self.legend_pos_combo.currentTextChanged.connect(self.changed)
        ll.addWidget(self.legend_pos_combo, stretch=1)
        form.addRow("Legend:", legend_row)

    # ── 내부 ──────────────────────────────────────────────────────────

    def _set_edited(self, which: str):
        setattr(self, f'_{which}_edited', True)

    def _on_legend_toggle(self):
        self.legend_pos_combo.setEnabled(self.legend_check.isChecked())
        self.changed.emit()

    # ── 공개 API ──────────────────────────────────────────────────────

    def set_defaults(self, title: str = '', xlabel: str = '', ylabel: str = ''):
        """
        다이얼로그 생성 시 기본값 주입 (setText 이므로 _edited 플래그 불변).
        비어있는 인자는 기존 값을 건드리지 않음.
        """
        if title:
            self.title_edit.setText(title)
        if xlabel:
            self.xlabel_edit.setText(xlabel)
        if ylabel:
            self.ylabel_edit.setText(ylabel)

    def apply_to_axes(self, ax):
        """
        ax에 현재 패널 설정 적용.
        - title/xlabel/ylabel: 수정됐거나 값이 있을 때만 override
        - tick labels: 항상 적용
        - legend: 항상 적용
        """
        # Title
        t = self.title_edit.text()
        if self._title_edited or t:
            ax.set_title(t)

        # X / Y label
        xl = self.xlabel_edit.text()
        if self._xlabel_edited or xl:
            ax.set_xlabel(xl)

        yl = self.ylabel_edit.text()
        if self._ylabel_edited or yl:
            ax.set_ylabel(yl)

        # Tick labels
        ax.tick_params(axis='x', labelbottom=self.xticklabels_check.isChecked())
        ax.tick_params(axis='y', labelleft=self.yticklabels_check.isChecked())

        # Legend
        handles, _ = ax.get_legend_handles_labels()
        if self.legend_check.isChecked():
            if handles:
                ax.legend(loc=self.legend_pos_combo.currentText())
        else:
            legend = ax.get_legend()
            if legend is not None:
                legend.remove()

    def get_params(self) -> dict:
        """직렬화 / get_plot_params() 연동용."""
        return {
            'labels_title':          self.title_edit.text(),
            'labels_xlabel':         self.xlabel_edit.text(),
            'labels_ylabel':         self.ylabel_edit.text(),
            'show_xticklabels':      self.xticklabels_check.isChecked(),
            'show_yticklabels':      self.yticklabels_check.isChecked(),
            'show_legend':           self.legend_check.isChecked(),
            'legend_position':       self.legend_pos_combo.currentText(),
        }

    def load_params(self, params: dict):
        """get_params() 결과를 복원."""
        if 'labels_title' in params:
            self.title_edit.setText(params['labels_title'])
        if 'labels_xlabel' in params:
            self.xlabel_edit.setText(params['labels_xlabel'])
        if 'labels_ylabel' in params:
            self.ylabel_edit.setText(params['labels_ylabel'])
        if 'show_xticklabels' in params:
            self.xticklabels_check.setChecked(bool(params['show_xticklabels']))
        if 'show_yticklabels' in params:
            self.yticklabels_check.setChecked(bool(params['show_yticklabels']))
        if 'show_legend' in params:
            self.legend_check.setChecked(bool(params['show_legend']))
        if 'legend_position' in params:
            idx = self.LEGEND_POSITIONS.index(params['legend_position']) \
                  if params['legend_position'] in self.LEGEND_POSITIONS else 0
            self.legend_pos_combo.setCurrentIndex(idx)
        self._on_legend_toggle()  # legend_pos_combo enabled 상태 동기화
