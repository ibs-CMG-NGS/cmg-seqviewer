"""
Dataset Tree Panel

좌측 패널 상단에 배치되는 트리 기반 데이터셋/시트 관리 위젯.
DatasetManagerWidget(가로 콤보박스)의 기능을 흡수하고 계층 구조로 확장한다.

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
from PyQt6.QtGui import QDragEnterEvent, QDropEvent
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
_ROLE_DATA = Qt.ItemDataRole.UserRole
_ROLE_KIND = Qt.ItemDataRole.UserRole + 1
_ROLE_META = Qt.ItemDataRole.UserRole + 2

# sheet_type → 아이콘
_SHEET_ICONS: Dict[str, str] = {
    "whole": "📋",
    "filtered": "🔍",
    "comparison": "🔗",
    "clustered": "🧩",
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

        # 툴바 (Add / Remove / Rename)
        toolbar = QHBoxLayout()
        toolbar.setSpacing(4)

        self.add_dataset_btn = QPushButton("➕ Add")
        self.add_dataset_btn.setToolTip("Add Dataset (or drag & drop a file)")
        self.add_dataset_btn.setAcceptDrops(True)
        self.add_dataset_btn.dragEnterEvent = lambda e: self.dragEnterEvent(e)
        self.add_dataset_btn.dropEvent = lambda e: self.dropEvent(e)
        self.add_dataset_btn.clicked.connect(self.add_requested.emit)
        toolbar.addWidget(self.add_dataset_btn)

        self.remove_dataset_btn = QPushButton("➖ Remove")
        self.remove_dataset_btn.setToolTip("Remove selected dataset")
        self.remove_dataset_btn.clicked.connect(self._on_remove_clicked)
        toolbar.addWidget(self.remove_dataset_btn)

        self.rename_dataset_btn = QPushButton("✏️ Rename")
        self.rename_dataset_btn.setToolTip("Rename selected dataset")
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
        item.setToolTip(0, self._build_tooltip(unique_name, metadata))
        item.setExpanded(True)

        self._update_info()
        self.dataset_added.emit(unique_name)
        return unique_name

    # backward-compat alias used by main_window.py
    def add_dataset(self, dataset_name: str, info: str = "", metadata: Optional[Dict] = None) -> str:
        """DatasetManagerWidget.add_dataset() 호환 메서드."""
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

        DatasetManagerWidget._generate_unique_name() 과 동일 로직.
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
        """루트 데이터셋 아래에 시트 child 노드를 추가한다.

        Parameters
        ----------
        parent_name  : 루트 데이터셋 이름
        tab_index    : 대응하는 QTabWidget 탭 인덱스
        sheet_label  : 트리에 표시할 텍스트
        sheet_type   : 'whole' | 'filtered' | 'comparison' | 'clustered'
        """
        root = self._find_root(parent_name)
        if root is None:
            return

        icon = _SHEET_ICONS.get(sheet_type, "📄")
        child = QTreeWidgetItem(root)
        child.setText(0, f"{icon} {sheet_label}")
        child.setData(0, _ROLE_DATA, tab_index)
        child.setData(0, _ROLE_KIND, sheet_type)
        root.setExpanded(True)

    def remove_sheet(self, tab_index: int):
        """tab_index에 해당하는 child 노드를 제거한다."""
        child = self._find_child_by_tab(tab_index)
        if child is not None:
            parent = child.parent()
            if parent is not None:
                parent.removeChild(child)

    def update_sheet_tab_index(self, old_index: int, new_index: int):
        """탭 제거 후 인덱스가 shift될 때 child 노드의 tab_index를 갱신한다."""
        for i in range(self.dataset_tree.topLevelItemCount()):
            root = self.dataset_tree.topLevelItem(i)
            for j in range(root.childCount()):
                child = root.child(j)
                if child.data(0, _ROLE_DATA) == old_index:
                    child.setData(0, _ROLE_DATA, new_index)

    # ------------------------------------------------------------------
    # Public API — synchronization
    # ------------------------------------------------------------------

    def sync_selection(self, tab_index: int):
        """탭이 전환됐을 때 트리 선택을 해당 child로 동기화한다."""
        if self._syncing:
            return
        self._syncing = True
        try:
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
            self.dataset_selected.emit(item.data(0, _ROLE_DATA))
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
