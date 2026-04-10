# Plan: Dataset Tree Panel

**목적**: 상단 가로형 콤보박스 방식의 Dataset 선택 UI를 좌측 세로 트리 패널로 교체.  
각 Dataset을 루트 노드로, 파생된 Filtered/Comparison/Clustered sheet를 child 노드로 표시.  
트리에서 노드를 클릭하면 해당 탭이 활성화되고, 탭을 전환하면 트리 선택도 동기화된다.

---

## 1. 현재 구조 (As-Is)

```
MainWindow
├── DatasetManagerWidget (QWidget, 가로 bar)
│   ├── QLabel "Current Dataset:"
│   ├── QComboBox  dataset_combo           ← dataset 전환
│   ├── QPushButton "➕ Add Dataset"
│   ├── QPushButton "✏️ Rename"
│   ├── QPushButton "➖ Remove"
│   └── QLabel  info_label
│
├── QSplitter (horizontal)
│   ├── left_panel (QWidget)
│   │   ├── FilterPanel
│   │   ├── ComparisonPanel
│   │   └── [Apply Filter] [Start Comparison]
│   │
│   └── QTabWidget  data_tabs              ← 모든 sheet가 flat하게 나열
│       ├── "Whole Dataset: DESeq2"
│       ├── "Filtered: DESeq2 - p≤0.05"
│       ├── "Whole Dataset: GO_UP"
│       ├── "Filtered: GO_UP - FDR≤0.05"
│       └── "Comparison: Gene List (2)"
│
└── QTextEdit  log_terminal

내부 데이터:
  tab_data: Dict[int, (DataFrame, Dataset)]   ← 탭 인덱스 → 데이터
  DatasetManagerWidget.dataset_combo          ← 루트 dataset 목록
```

**문제점**:
- 탭이 많아지면 flat 나열이라 어느 dataset에서 파생됐는지 파악 어려움
- Dataset 전환(combo)과 탭 선택이 연동되지 않아 상태가 불일치할 수 있음
- 현재 dataset의 상세 정보가 좁은 라벨에만 표시됨

---

## 2. 목표 구조 (To-Be)

```
MainWindow
├── QSplitter (horizontal, 3-way 또는 2-way)
│
│   ├── [좌측 패널, QSplitter vertical]
│   │   │
│   │   ├── DatasetTreePanel (QWidget, 새 파일)  ← 상단부
│   │   │   ├── QToolBar: [➕ Add] [➖ Remove] [✏️ Rename]
│   │   │   └── QTreeWidget  dataset_tree
│   │   │       ├── 📊 DESeq2  (DE, 1,234 rows)     ← root: dataset
│   │   │       │   ├── 📋 Whole                    ← child: sheet
│   │   │       │   ├── 🔍 Filtered: p≤0.05
│   │   │       │   └── 🔍 Filtered: Gene List
│   │   │       ├── 🔬 GO_UP  (GO, 856 rows)
│   │   │       │   ├── 📋 Whole
│   │   │       │   ├── 🔍 Filtered: FDR≤0.05
│   │   │       │   └── 🔗 Comparison: Gene List
│   │   │       └── [Standalone]                    ← root-level 그룹
│   │   │           └── 🔗 Comparison: Statistics
│   │   │
│   │   └── [필터/비교 패널, 하단부]
│   │       ├── FilterPanel
│   │       ├── ComparisonPanel
│   │       └── [Apply Filter] [Start Comparison]
│   │
│   └── QTabWidget  data_tabs                       ← 기존 유지 (탭 이름 단축)
│       ├── "DESeq2 · Whole"
│       ├── "DESeq2 · p≤0.05"
│       ├── "GO_UP · Whole"
│       └── "GO_UP · FDR≤0.05"
│
└── QTextEdit  log_terminal

내부 데이터 변경:
  tab_data: Dict[int, TabEntry]
    TabEntry = {
      'dataframe': DataFrame,
      'dataset': Dataset,
      'parent_dataset': str | None,   ← 루트 dataset 이름 (새로 추가)
      'sheet_type': str,              ← 'whole'|'filtered'|'comparison'|'clustered'
    }
```

---

## 3. 신규 파일

### `src/gui/dataset_tree_panel.py`

새로 작성하는 위젯. 기존 `dataset_manager.py`의 기능을 흡수하되 트리 구조로 확장.

```python
class DatasetTreePanel(QWidget):
    # 시그널
    dataset_selected = pyqtSignal(str)        # root dataset 전환
    sheet_selected = pyqtSignal(int)          # tab_index 활성화 요청
    dataset_removed = pyqtSignal(str)
    rename_requested = pyqtSignal(str, str)   # old_name, new_name
    add_requested = pyqtSignal()

    # 주요 메서드
    def add_root_dataset(name, metadata)      # 루트 노드 추가
    def add_sheet(parent_name, tab_index, sheet_label, sheet_type)  # child 노드 추가
    def remove_sheet(tab_index)               # child 노드 제거
    def remove_root_dataset(name)             # 루트 + 모든 child 제거
    def rename_root_dataset(old, new)         # 루트 노드 이름 변경
    def sync_selection(tab_index)             # 탭 전환 시 트리 선택 동기화
    def get_current_root_dataset() -> str
    def get_all_root_datasets() -> List[str]
```

**트리 아이템 구조**:
```
QTreeWidgetItem (root)
  .data(Qt.UserRole+0) = dataset_name: str
  .data(Qt.UserRole+1) = 'root'
  .data(Qt.UserRole+2) = metadata: dict

QTreeWidgetItem (child)
  .data(Qt.UserRole+0) = tab_index: int
  .data(Qt.UserRole+1) = sheet_type: str  ('whole'|'filtered'|'comparison'|'clustered')
```

---

## 4. 수정 파일 및 변경 범위

### 4-1. `src/gui/dataset_manager.py`

현재 역할: Dataset 목록 관리(QComboBox) + metadata 저장  
**변경 계획**: `DatasetTreePanel`로 기능 이전 후 이 파일은 **삭제 또는 빈 호환 shim**으로 남김.

외부 참조 확인이 필요한 public API:
- `add_dataset(name, info, metadata)` → `DatasetTreePanel.add_root_dataset()`
- `remove_dataset(name)` → `DatasetTreePanel.remove_root_dataset()`
- `rename_dataset(old, new)` → `DatasetTreePanel.rename_root_dataset()`
- `get_current_dataset()` → `DatasetTreePanel.get_current_root_dataset()`
- `get_all_datasets()` → `DatasetTreePanel.get_all_root_datasets()`
- `dataset_selected` signal → 동일 시그널로 유지
- `dataset_removed` signal → 동일 시그널로 유지

### 4-2. `src/gui/main_window.py`

변경 지점 목록:

| 위치 | 현재 | 변경 후 |
|------|------|---------|
| `__init__` imports | `from gui.dataset_manager import DatasetManagerWidget` | `from gui.dataset_tree_panel import DatasetTreePanel` |
| `_init_ui()` L130~136 | `DatasetManagerWidget()` + `main_layout.addWidget()` | `DatasetTreePanel()` + 좌측 패널 상단에 배치 |
| `tab_data` 타입 | `Dict[int, tuple]` | `Dict[int, dict]` (TabEntry 구조체) |
| `_create_data_tab()` | 탭만 생성 | 트리 child 노드도 등록 |
| `_on_filter_completed()` | 탭 생성 | 탭 생성 + 트리 child 노드 추가 |
| `_on_tab_close_requested()` | `data_tabs.removeTab()` | 탭 제거 + 트리 child 노드 제거 |
| `_on_tab_changed()` | 메뉴 업데이트 | 메뉴 업데이트 + `tree.sync_selection(index)` |
| `_on_dataset_renamed()` | 탭 이름 문자열 치환 | 탭 이름 + 트리 노드 이름 업데이트 |
| `_on_dataset_removed()` | 단순 제거 | 트리 루트 노드 + 모든 child 제거 |
| `_update_comparison_panel_datasets()` | combo에서 읽음 | 트리에서 읽음 |

**레이아웃 변경**:
```
현재:
  main_layout (VBox)
    └─ DatasetManagerWidget (가로 bar)  ← 제거
    └─ QSplitter
         ├─ left_panel (FilterPanel + ComparisonPanel)
         └─ data_tabs

변경 후:
  main_layout (VBox)
    └─ QSplitter (horizontal)
         ├─ left_panel (VBox, QSplitter vertical)
         │    ├─ DatasetTreePanel  (stretch=1, 기본 높이 ~200px)
         │    └─ filter+comparison (stretch=2)
         └─ data_tabs
```

### 4-3. `tab_data` 구조 변경

```python
# 현재
tab_data: Dict[int, tuple]
tab_data[idx] = (dataframe, dataset)

# 변경 후
tab_data: Dict[int, dict]
tab_data[idx] = {
    'dataframe': DataFrame,
    'dataset': Dataset,
    'parent_dataset': str | None,   # 루트 dataset 이름
    'sheet_type': str,              # 'whole'|'filtered'|'comparison'|'clustered'
    'sheet_label': str,             # 트리에 표시할 짧은 이름 (탭 이름과 별개)
}
```

`tab_data`를 읽는 모든 위치 수정 필요:
- `populate_table()` L553: `(dataframe, dataset)` → `dict`
- `_filter_current_tab()` L982, 1034
- `_on_tab_changed()` L1702
- `_on_column_level_changed()` L1725, 1741
- `_on_filter_completed()` L2660
- `_on_dot_plot_requested()` L2597, 2720
- 기타 `tab_data[idx]` 접근부 (~15곳)

---

## 5. 트리 ↔ 탭 동기화 로직

### 탭 전환 시 (탭 클릭 → 트리 동기화)
```
_on_tab_changed(index)
  → tree.sync_selection(index)
    → tree 내부에서 tab_index == index인 child 아이템 찾아 select
    → 해당 child의 parent root도 expand
  ※ 순환 방지: sync_selection() 호출 중 sheet_selected 시그널 block
```

### 트리 클릭 시 (트리 → 탭 전환)
```
tree.itemClicked(item)
  → item이 child이면:
      sheet_selected.emit(tab_index)
      → main_window.data_tabs.setCurrentIndex(tab_index)
      ※ _on_tab_changed()가 다시 sync_selection()을 호출하지 않도록 guard flag
  → item이 root이면:
      dataset_selected.emit(dataset_name)
      → presenter.switch_dataset(dataset_name)
      → Whole Dataset 탭으로 자동 이동
```

### Guard 패턴 (무한 루프 방지)
```python
self._syncing_tree = False  # init에서 False

def _on_tab_changed(self, index):
    if not self._syncing_tree:
        self._syncing_tree = True
        self.dataset_tree.sync_selection(index)
        self._syncing_tree = False
    ...

def _on_tree_sheet_selected(self, tab_index):
    if not self._syncing_tree:
        self._syncing_tree = True
        self.data_tabs.setCurrentIndex(tab_index)
        self._syncing_tree = False
```

---

## 6. 탭 이름 단축 (선택적 개선)

현재 탭 이름이 너무 길어 탭이 많아지면 가독성 저하.  
트리로 dataset 이름이 표시되므로 탭에서는 sheet 종류만 보여줄 수 있음.

```
현재 탭 이름                            → 단축 탭 이름
"Whole Dataset: DESeq2"               → "Whole"
"Filtered: DESeq2 - p≤0.05"          → "p≤0.05"
"Filtered: Gene Symbols (5 genes)"   → "Gene Sym. (5)"
"Comparison: Gene List (2 datasets)" → "Comparison"
```

단, 탭 이름을 단축하면 탭만 보고 어느 dataset인지 모를 수 있으므로 **툴팁**으로 전체 이름 제공.  
→ 이 부분은 트리 패널 구현 완료 후 별도 커밋으로 처리.

---

## 7. 구현 순서 (단계별 커밋)

### Phase 1 — `tab_data` 구조 변경 (내부 리팩토링)
- `tab_data`를 tuple에서 dict로 변경
- 모든 접근부를 dict key 방식으로 수정
- `parent_dataset`, `sheet_type` 필드 추가 (빈 값으로 채워두기)
- **기능 변경 없음**, 리팩토링만
- 커밋: `refactor: convert tab_data from tuple to dict with parent_dataset/sheet_type fields`

### Phase 2 — `DatasetTreePanel` 위젯 신규 작성
- `src/gui/dataset_tree_panel.py` 파일 생성
- `QTreeWidget` 기반 UI, 시그널 정의, 노드 CRUD 메서드
- 단독으로 테스트 가능한 상태
- 커밋: `feat: add DatasetTreePanel widget with QTreeWidget`

### Phase 3 — `main_window.py` 레이아웃 교체
- `DatasetManagerWidget` 제거, `DatasetTreePanel` 배치
- 좌측 패널 내부 `QSplitter` 추가 (트리 / 필터+비교)
- 시그널 재연결 (`dataset_selected`, `dataset_removed`)
- 커밋: `feat: replace DatasetManagerWidget with DatasetTreePanel in layout`

### Phase 4 — 트리 ↔ 탭 동기화
- `_create_data_tab()`, `_on_filter_completed()` 에서 트리 child 노드 추가
- `_on_tab_close_requested()` 에서 child 노드 제거
- `_on_tab_changed()` 에서 트리 선택 동기화
- `_on_tree_sheet_selected()` 핸들러 추가
- Guard flag 적용
- 커밋: `feat: bidirectional sync between dataset tree and tab widget`

### Phase 5 — 기존 DatasetManagerWidget 제거 및 정리
- `dataset_manager.py` 삭제 또는 deprecated stub으로 교체
- 탭 이름 단축 (선택적)
- 커밋: `refactor: remove DatasetManagerWidget, clean up tab names`

---

## 8. 리스크 및 주의사항

| 리스크 | 대응 |
|--------|------|
| `tab_data` 인덱스가 탭 제거 시 shift되는 문제 | 탭 제거 후 `tab_data`를 재인덱싱하는 기존 로직 유지 (현재도 동일 문제 있음 → Phase 1에서 확인) |
| 트리 ↔ 탭 순환 시그널 | Guard flag `_syncing_tree` 패턴으로 차단 |
| Comparison 탭의 parent 불명확 | `parent_dataset=None`, `sheet_type='comparison'`으로 처리, 트리에서는 별도 "Standalone" 그룹 또는 관련 dataset 중 첫 번째를 parent로 |
| 좌측 패널 세로 공간 | `DatasetTreePanel` 기본 높이 200px, 사용자가 `QSplitter` 드래그로 조절 가능 |
| Database 탭 반입 시 트리 업데이트 누락 | `_on_load_from_database()` 내 `dataset_manager.add_dataset()` 호출부 모두 찾아 교체 |

---

## 9. 파일 변경 요약

| 파일 | 변경 유형 | 작업량 |
|------|----------|--------|
| `src/gui/dataset_tree_panel.py` | **신규 작성** | ~200줄 |
| `src/gui/main_window.py` | 수정 (대규모) | ~100줄 수정/추가 |
| `src/gui/dataset_manager.py` | 삭제 또는 stub | 최소화 |
| `src/gui/comparison_panel.py` | 확인 필요 | dataset list 연동 부분 |

---

## 10. 구현 전 확인 필요 사항

- [ ] `tab_data` 키(tab_index)가 탭 제거 후 올바르게 갱신되는지 현재 동작 검증
- [ ] `comparison_panel.update_dataset_list()`가 받는 데이터 형식 확인
- [ ] `presenter.datasets` dict와 `DatasetManagerWidget` combo의 동기화 방식 확인
- [ ] 데이터베이스 불러오기 경로에서 `add_dataset()` 호출 위치 전수 조사
