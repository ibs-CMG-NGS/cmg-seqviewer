"""
Dataset Tree Panel

좌측 패널 상단에 배치되는 트리 기반 데이터셋/시트 관리 위젯.

트리 구조:
  📊 DESeq2  (root node — Dataset)
  ├── 📋 Whole
  ├── 🔍 Filtered: p≤0.05
  └── 🔍 Filtered: Gene List
  📊 GO_UP
  ├── 📋 Whole
  └── 🔗 Comparison: Gene List

QTreeWidgetItem UserRole:
  root  → UserRole+0: dataset_name (str), UserRole+1: 'root', UserRole+2: metadata (dict)
  child → UserRole+0: tab_index (int),    UserRole+1: sheet_type (str)
"""

from datetime import datetime
from typing import Dict, List, Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QDragEnterEvent, QDropEvent, QIcon, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

# UserRole 상수
_ROLE_DATA      = Qt.ItemDataRole.UserRole
_ROLE_KIND      = Qt.ItemDataRole.UserRole + 1
_ROLE_META      = Qt.ItemDataRole.UserRole + 2
_ROLE_WHOLE_TAB = Qt.ItemDataRole.UserRole + 3   # root 아이템의 whole 탭 인덱스


def _make_icon(name: str) -> QIcon:
    """QPainter로 선명한 모노크롬 아이콘 생성 (plus / minus / pencil)"""
    S = 16
    px = QPixmap(S, S)
    px.fill(Qt.GlobalColor.transparent)
    p = QPainter(px)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    pen = QPen(QColor("#333333"), 1.6)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    if name == "plus":
        p.drawLine(8, 2, 8, 14)
        p.drawLine(2, 8, 14, 8)
    elif name == "minus":
        p.drawLine(3, 8, 13, 8)
    elif name == "pencil":
        # 몸통 (대각선)
        p.drawLine(4, 12, 11, 5)
        # 끝부분 (삼각형)
        p.drawLine(11, 5, 13, 3)
        p.drawLine(13, 3, 11, 3)
        p.drawLine(11, 3, 11, 5)
        # 지우개 끝
        p.drawLine(3, 13, 4, 12)
        p.drawLine(2, 14, 3, 13)
        p.drawLine(2, 14, 4, 14)
        p.drawLine(3, 13, 4, 14)
    p.end()
    return QIcon(px)

# sheet_type → 아이콘
_SHEET_ICONS: Dict[str, str] = {
    "whole": "📋",
    "filtered": "🔍",
    "comparison": "🔗",
    "clustered": "🧩",
    "plot": "📈",
}


class DatasetTreePanel(QWidget):
    """QTreeWidget 기반 데이터셋 + 시트 관리 패널.

    Signals
    -------
    dataset_selected(str)     : 루트 dataset 전환 (dataset_name)
    sheet_selected(int)       : child 시트 선택 → 탭 활성화 요청 (tab_index)
    dataset_removed(str)      : 루트 dataset 제거 요청 (dataset_name)
    rename_requested(str, str): 이름 변경 요청 (old_name, new_name)
    add_requested()           : Add Dataset 버튼 클릭
    file_dropped(str)         : 파일 드롭 (file_path)
    """

    dataset_selected = pyqtSignal(str)
    dataset_added = pyqtSignal(str)       # 루트 노드 추가 완료 후 발화 (unique_name)
    sheet_selected = pyqtSignal(int)
    dataset_removed = pyqtSignal(str)
    rename_requested = pyqtSignal(str, str)
    add_requested = pyqtSignal()
    file_dropped = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._dataset_metadata: Dict[str, Dict] = {}
        # Guard: 프로그래매틱 선택 변경 시 시그널 루프 방지
        self._syncing = False
        self._init_ui()
        self.setAcceptDrops(True)

    # ------------------------------------------------------------------
    # UI 초기화
    # ------------------------------------------------------------------

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # 툴바 (Add / Remove / Rename) — 아이콘 전용, 호버 시 이름 표시
        toolbar = QHBoxLayout()
        toolbar.setSpacing(2)

        _btn_style = (
            "QPushButton{border:1px solid #bbb; background:#f5f5f5; "
            "border-radius:3px; padding:2px 6px; font-size:13px;}"
            "QPushButton:hover{background:#dceefb; border-color:#0078d4;}"
            "QPushButton:pressed{background:#b3d7f5;}"
            "QPushButton:disabled{color:#aaa; background:#f0f0f0;}"
        )

        self.add_dataset_btn = QPushButton()
        self.add_dataset_btn.setIcon(_make_icon("plus"))
        self.add_dataset_btn.setToolTip("Add Dataset (or drag & drop a file)")
        self.add_dataset_btn.setFixedSize(26, 26)
        self.add_dataset_btn.setStyleSheet(_btn_style)
        self.add_dataset_btn.setAcceptDrops(True)
        self.add_dataset_btn.dragEnterEvent = lambda e: self.dragEnterEvent(e)
        self.add_dataset_btn.dropEvent = lambda e: self.dropEvent(e)
        self.add_dataset_btn.clicked.connect(self.add_requested.emit)
        toolbar.addWidget(self.add_dataset_btn)

        self.remove_dataset_btn = QPushButton()
        self.remove_dataset_btn.setIcon(_make_icon("minus"))
        self.remove_dataset_btn.setToolTip("Remove selected dataset")
        self.remove_dataset_btn.setFixedSize(26, 26)
        self.remove_dataset_btn.setStyleSheet(_btn_style)
        self.remove_dataset_btn.clicked.connect(self._on_remove_clicked)
        toolbar.addWidget(self.remove_dataset_btn)

        self.rename_dataset_btn = QPushButton()
        self.rename_dataset_btn.setIcon(_make_icon("pencil"))
        self.rename_dataset_btn.setToolTip("Rename selected dataset")
        self.rename_dataset_btn.setFixedSize(26, 26)
        self.rename_dataset_btn.setStyleSheet(_btn_style)
        self.rename_dataset_btn.clicked.connect(self._on_rename_clicked)
        toolbar.addWidget(self.rename_dataset_btn)

        self.info_label = QLabel("No datasets loaded")
        self.info_label.setStyleSheet("color: gray; font-size: 11px;")
        self.info_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        toolbar.addWidget(self.info_label, stretch=1)

        layout.addLayout(toolbar)

        # 트리
        self.dataset_tree = QTreeWidget()
        self.dataset_tree.setHeaderHidden(True)
        self.dataset_tree.setIndentation(16)
        self.dataset_tree.setAnimated(True)
        self.dataset_tree.setAcceptDrops(True)
        self.dataset_tree.dragEnterEvent = lambda e: self.dragEnterEvent(e)
        self.dataset_tree.dropEvent = lambda e: self.dropEvent(e)
        self.dataset_tree.itemClicked.connect(self._on_item_clicked)
        layout.addWidget(self.dataset_tree)

    # ------------------------------------------------------------------
    # Public API — root dataset
    # ------------------------------------------------------------------

    def add_root_dataset(self, dataset_name: str, metadata: Optional[Dict] = None) -> str:
        """루트 데이터셋 노드를 추가한다. 중복 시 번호를 붙여 고유 이름을 반환한다.

        Parameters
        ----------
        dataset_name : 표시 이름
        metadata     : file_path, row_count, dataset_type 등 임의 dict

        Returns
        -------
        unique_name : 실제로 저장된 고유 이름
        """
        unique_name = self.generate_unique_name(dataset_name)

        if metadata is None:
            metadata = {}
        metadata.setdefault("original_name", dataset_name)
        metadata["added_at"] = datetime.now().isoformat()
        self._dataset_metadata[unique_name] = metadata

        item = QTreeWidgetItem(self.dataset_tree)
        item.setText(0, f"📊 {unique_name}")
        item.setData(0, _ROLE_DATA, unique_name)
        item.setData(0, _ROLE_KIND, "root")
        item.setData(0, _ROLE_META, metadata)
        item.setData(0, _ROLE_WHOLE_TAB, None)   # whole 탭은 add_sheet() 호출 시 설정
        item.setToolTip(0, self._build_tooltip(unique_name, metadata))
        item.setExpanded(True)

        self._update_info()
        self.dataset_added.emit(unique_name)
        return unique_name

    # backward-compat alias used by main_window.py
    def add_dataset(self, dataset_name: str, info: str = "", metadata: Optional[Dict] = None) -> str:
        """dataset_manager 호환 메서드: add_root_dataset() 추가 방식으로 데이터셋 등록."""
        return self.add_root_dataset(dataset_name, metadata)

    def remove_root_dataset(self, dataset_name: str):
        """루트 데이터셋 노드(와 모든 child)를 제거한다."""
        root = self._find_root(dataset_name)
        if root is not None:
            index = self.dataset_tree.indexOfTopLevelItem(root)
            self.dataset_tree.takeTopLevelItem(index)
            self._dataset_metadata.pop(dataset_name, None)
            self._update_info()

    # backward-compat alias
    def remove_dataset(self, dataset_name: str):
        self.remove_root_dataset(dataset_name)

    def rename_root_dataset(self, old_name: str, new_name: str) -> str:
        """루트 데이터셋 이름을 변경한다. 고유 이름을 반환한다."""
        root = self._find_root(old_name)
        if root is None:
            return old_name

        unique_name = self.generate_unique_name(new_name)

        meta = self._dataset_metadata.pop(old_name, {})
        self._dataset_metadata[unique_name] = meta

        root.setText(0, f"📊 {unique_name}")
        root.setData(0, _ROLE_DATA, unique_name)
        root.setToolTip(0, self._build_tooltip(unique_name, meta))

        return unique_name

    # backward-compat alias
    def rename_dataset(self, old_name: str, new_name: str) -> str:
        return self.rename_root_dataset(old_name, new_name)

    def get_current_root_dataset(self) -> str:
        """현재 선택된 루트 데이터셋 이름을 반환한다. 없으면 빈 문자열."""
        item = self.dataset_tree.currentItem()
        if item is None:
            return ""
        if item.data(0, _ROLE_KIND) == "root":
            return item.data(0, _ROLE_DATA)
        # child가 선택된 경우 → 부모 루트 이름
        parent = item.parent()
        if parent is not None:
            return parent.data(0, _ROLE_DATA)
        return ""

    # backward-compat alias
    def get_current_dataset(self) -> str:
        return self.get_current_root_dataset()

    def get_all_root_datasets(self) -> List[str]:
        """모든 루트 데이터셋 이름 목록을 반환한다."""
        result = []
        for i in range(self.dataset_tree.topLevelItemCount()):
            item = self.dataset_tree.topLevelItem(i)
            result.append(item.data(0, _ROLE_DATA))
        return result

    # backward-compat alias
    def get_all_datasets(self) -> List[str]:
        return self.get_all_root_datasets()

    def get_selected_datasets(self) -> List[str]:
        """비교 분석용: 루트 데이터셋이 2개 이상이면 전체 반환."""
        datasets = self.get_all_root_datasets()
        return datasets if len(datasets) >= 2 else []

    def get_dataset_metadata(self, dataset_name: str) -> Dict:
        """데이터셋 메타데이터를 반환한다."""
        return self._dataset_metadata.get(dataset_name, {})

    def generate_unique_name(self, base_name: str) -> str:
        """중복되지 않는 고유 이름을 생성한다.

        이름이 없으면 기본값, 이미 있으면 번호 suffix 추가 (name, name_2, …).
        main_window.py에서 외부 호출되므로 public 메서드로 제공한다.
        """
        existing = self.get_all_root_datasets()
        if base_name not in existing:
            return base_name
        counter = 2
        while f"{base_name} ({counter})" in existing:
            counter += 1
        return f"{base_name} ({counter})"

    # backward-compat private alias (main_window.py L2930에서 직접 호출)
    def _generate_unique_name(self, base_name: str) -> str:
        return self.generate_unique_name(base_name)

    # ------------------------------------------------------------------
    # Public API — child sheet
    # ------------------------------------------------------------------

    def add_sheet(
        self,
        parent_name: str,
        tab_index: int,
        sheet_label: str,
        sheet_type: str = "whole",
    ):
        """루트 데이터셋 아래에 시트를 등록한다.

        sheet_type == 'whole' 일 때는 child 노드를 추가하지 않고 root 아이템에
        whole_tab_index (_ROLE_WHOLE_TAB) 를 저장한다.
        root 클릭 시 해당 탭으로 직접 전환된다.

        Parameters
        ----------
        parent_name  : 루트 데이터셋 이름
        tab_index    : 대응하는 QTabWidget 탭 인덱스
        sheet_label  : 트리에 표시할 텍스트
        sheet_type   : 'whole' | 'filtered' | 'comparison' | 'clustered' | 'plot'
        """
        root = self._find_root(parent_name)
        if root is None:
            return

        if sheet_type == "whole":
            # whole 탭은 root 자체에 연결 — child 노드 추가하지 않음
            root.setData(0, _ROLE_WHOLE_TAB, tab_index)
            return

        icon = _SHEET_ICONS.get(sheet_type, "📄")
        child = QTreeWidgetItem(root)
        child.setText(0, f"{icon} {sheet_label}")
        child.setData(0, _ROLE_DATA, tab_index)
        child.setData(0, _ROLE_KIND, sheet_type)
        root.setExpanded(True)

    def remove_sheet(self, tab_index: int):
        """tab_index에 해당하는 시트를 제거한다.

        whole 탭(root의 whole_tab_index)인 경우 root의 whole_tab_index를 초기화한다.
        """
        # 먼저 root의 whole_tab_index 체크
        for i in range(self.dataset_tree.topLevelItemCount()):
            root = self.dataset_tree.topLevelItem(i)
            if root.data(0, _ROLE_WHOLE_TAB) == tab_index:
                root.setData(0, _ROLE_WHOLE_TAB, None)
                return
        # child 노드 체크
        child = self._find_child_by_tab(tab_index)
        if child is not None:
            parent = child.parent()
            if parent is not None:
                parent.removeChild(child)

    def update_sheet_tab_index(self, old_index: int, new_index: int):
        """탭 제거 후 인덱스가 shift될 때 child/root 노드의 tab_index를 갱신한다."""
        for i in range(self.dataset_tree.topLevelItemCount()):
            root = self.dataset_tree.topLevelItem(i)
            # root whole_tab_index 갱신
            if root.data(0, _ROLE_WHOLE_TAB) == old_index:
                root.setData(0, _ROLE_WHOLE_TAB, new_index)
            # child 노드 갱신
            for j in range(root.childCount()):
                child = root.child(j)
                if child.data(0, _ROLE_DATA) == old_index:
                    child.setData(0, _ROLE_DATA, new_index)

    # ------------------------------------------------------------------
    # Public API — synchronization
    # ------------------------------------------------------------------

    def sync_selection(self, tab_index: int):
        """탭이 전환됐을 때 트리 선택을 해당 child(또는 root)로 동기화한다."""
        if self._syncing:
            return
        self._syncing = True
        try:
            # 먼저 root의 whole_tab_index 체크
            for i in range(self.dataset_tree.topLevelItemCount()):
                root = self.dataset_tree.topLevelItem(i)
                if root.data(0, _ROLE_WHOLE_TAB) == tab_index:
                    self.dataset_tree.setCurrentItem(root)
                    return
            # child 노드 체크
            child = self._find_child_by_tab(tab_index)
            if child is not None:
                self.dataset_tree.setCurrentItem(child)
        finally:
            self._syncing = False

    # ------------------------------------------------------------------
    # Drag & Drop
    # ------------------------------------------------------------------

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if urls:
                path = urls[0].toLocalFile().lower()
                if path.endswith((".xlsx", ".xls", ".csv", ".tsv")):
                    event.accept()
                    return
        event.ignore()

    def dropEvent(self, event: QDropEvent):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if urls:
                path = urls[0].toLocalFile()
                if path.lower().endswith((".xlsx", ".xls", ".csv", ".tsv")):
                    self.file_dropped.emit(path)
                    event.accept()
                    return
        event.ignore()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _find_root(self, dataset_name: str) -> Optional[QTreeWidgetItem]:
        for i in range(self.dataset_tree.topLevelItemCount()):
            item = self.dataset_tree.topLevelItem(i)
            if item.data(0, _ROLE_DATA) == dataset_name:
                return item
        return None

    def _find_child_by_tab(self, tab_index: int) -> Optional[QTreeWidgetItem]:
        for i in range(self.dataset_tree.topLevelItemCount()):
            root = self.dataset_tree.topLevelItem(i)
            for j in range(root.childCount()):
                child = root.child(j)
                if child.data(0, _ROLE_DATA) == tab_index:
                    return child
        return None

    def _update_info(self):
        count = self.dataset_tree.topLevelItemCount()
        if count == 0:
            self.info_label.setText("No datasets loaded")
        elif count == 1:
            self.info_label.setText("1 dataset loaded")
        else:
            self.info_label.setText(f"{count} datasets loaded")

    def _build_tooltip(self, dataset_name: str, metadata: Dict) -> str:
        lines = [f"<b>{dataset_name}</b>"]
        if "file_path" in metadata:
            lines.append(f"📁 {metadata['file_path']}")
        if "row_count" in metadata:
            lines.append(f"📊 {metadata['row_count']} rows")
        if "dataset_type" in metadata:
            lines.append(f"🔬 {metadata['dataset_type']}")
        if "added_at" in metadata:
            lines.append(f"🕐 {metadata['added_at'][:19]}")
        return "<br>".join(lines)

    # ------------------------------------------------------------------
    # Slot handlers (toolbar buttons)
    # ------------------------------------------------------------------

    def _on_item_clicked(self, item: QTreeWidgetItem, _column: int):
        if self._syncing:
            return
        kind = item.data(0, _ROLE_KIND)
        if kind == "root":
            dataset_name = item.data(0, _ROLE_DATA)
            whole_tab = item.data(0, _ROLE_WHOLE_TAB)
            # dataset_selected 는 항상 발화 (presenter 동기화)
            self.dataset_selected.emit(dataset_name)
            # whole 탭이 등록돼 있으면 해당 탭으로 직접 전환
            if whole_tab is not None:
                self.sheet_selected.emit(whole_tab)
        else:
            # child sheet
            tab_index = item.data(0, _ROLE_DATA)
            if tab_index is not None:
                self.sheet_selected.emit(tab_index)

    def _on_remove_clicked(self):
        name = self.get_current_root_dataset()
        if name:
            self.dataset_removed.emit(name)
            self.remove_root_dataset(name)

    def _on_rename_clicked(self):
        current = self.get_current_root_dataset()
        if not current:
            return
        new_name, ok = QInputDialog.getText(
            self,
            "Rename Dataset",
            "Enter a new name for the dataset:",
            text=current,
        )
        if not (ok and new_name and new_name != current):
            return
        if new_name in self.get_all_root_datasets():
            QMessageBox.warning(self, "Duplicate Name",
                                f"Dataset '{new_name}' already exists.")
            return
        actual_new = self.rename_root_dataset(current, new_name)
        self.rename_requested.emit(current, actual_new)
