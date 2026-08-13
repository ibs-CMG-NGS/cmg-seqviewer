"""컬럼 부분선택 다이얼로그.

현재 데이터셋의 컬럼 중 남길 것을 골라 비파괴적으로 '컬럼 subset' 자식 시트를 만든다.
원본은 그대로 두고, 선택 목록만 반환한다(시트 생성/복원은 필터 파이프라인이 처리).
"""
from typing import List, Optional

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QPushButton, QLineEdit, QDialogButtonBox,
)
from PyQt6.QtCore import Qt


class ColumnSubsetDialog(QDialog):
    """컬럼 체크리스트에서 남길 컬럼을 고르는 다이얼로그."""

    def __init__(self, columns: List[str], preselected: Optional[List[str]] = None,
                 parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Columns → Subset Sheet")
        self.resize(360, 480)
        self._all_columns = list(columns)
        pre = set(preselected) if preselected is not None else set(columns)

        root = QVBoxLayout(self)
        root.addWidget(QLabel("Tick the columns to keep. A new child sheet with only\n"
                              "those columns is created (the original is unchanged)."))

        self._search = QLineEdit()
        self._search.setPlaceholderText("Filter columns…")
        self._search.textChanged.connect(self._apply_search)
        root.addWidget(self._search)

        self._list = QListWidget()
        for col in self._all_columns:
            item = QListWidgetItem(str(col))
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked if col in pre else Qt.CheckState.Unchecked)
            self._list.addItem(item)
        root.addWidget(self._list, 1)

        # 전체 선택/해제 (현재 필터에 보이는 항목 대상)
        btn_row = QHBoxLayout()
        all_btn = QPushButton("Select all")
        all_btn.clicked.connect(lambda: self._set_visible(True))
        none_btn = QPushButton("Clear all")
        none_btn.clicked.connect(lambda: self._set_visible(False))
        self._count_lbl = QLabel("")
        btn_row.addWidget(all_btn)
        btn_row.addWidget(none_btn)
        btn_row.addStretch()
        btn_row.addWidget(self._count_lbl)
        root.addLayout(btn_row)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

        self._list.itemChanged.connect(lambda _: self._update_count())
        self._update_count()

    def _apply_search(self, text: str):
        text = text.strip().lower()
        for i in range(self._list.count()):
            item = self._list.item(i)
            item.setHidden(bool(text) and text not in item.text().lower())

    def _set_visible(self, checked: bool):
        state = Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
        for i in range(self._list.count()):
            item = self._list.item(i)
            if not item.isHidden():
                item.setCheckState(state)

    def _update_count(self):
        n = len(self.selected_columns())
        self._count_lbl.setText(f"{n} / {len(self._all_columns)} selected")

    def selected_columns(self) -> List[str]:
        """체크된 컬럼을 원본 순서로 반환."""
        out = []
        for i in range(self._list.count()):
            item = self._list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                out.append(item.text())
        return out
