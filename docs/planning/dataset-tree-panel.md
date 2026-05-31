# Plan: Dataset Tree Panel

**목적**: 상단 가로형 콤보박스 방식의 Dataset 선택 UI를 좌측 세로 트리 패널로 교체.  
각 Dataset을 루트 노드로, 파생된 Filtered/Comparison/Clustered sheet를 child 노드로 표시.  
트리에서 노드를 클릭하면 해당 탭이 활성화되고, 탭을 전환하면 트리 선택도 동기화된다.  
**확장 목표**: 트리 구조 전환과 함께 분석 세션을 `.seqproj` 파일로 저장/복원하는 기능을 함께 구축하여 분석 재현성을 확보한다.

**Created**: 2026-04-10  
**Status**: 📝 계획 (v1.3.0 대상)

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
    'parent_dataset': str | None,        # 루트 dataset 이름
    'sheet_type': str,                   # 'whole'|'filtered'|'comparison'|'clustered'
    'sheet_label': str,                  # 트리에 표시할 짧은 이름 (탭 이름과 별개)
    'filter_params': dict | None,        # 필터 파라미터 (project save/load용)
    'comparison_params': dict | None,    # 비교 파라미터 (project save/load용)
}
```

> `filter_params`와 `comparison_params`는 트리 패널 자체보다 **project save/load**(섹션 12)를 위해 필요한 필드다.
> Phase 1에서 함께 추가하면 두 기능의 선행 작업을 한 번에 처리할 수 있다.

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

### Phase 6 — Project Save/Load (`.seqproj`)
- `src/utils/project_io.py` 신규 작성
- `main_window.py` File 메뉴에 Save/Open Project 추가
- `_on_save_project()`, `_on_open_project()` 핸들러 구현
- Recent Projects 서브메뉴 (기존 `recent_files` 메커니즘 확장)
- 커밋: `feat: add project save/load with .seqproj format`

> Phase 6은 Phase 1 완료(tab_data에 filter_params 저장) 이후에야 의미있는 복원이 가능하다.
> Phase 2~5와 병렬 진행 가능하지만, 최종 통합은 Phase 5 이후 권장.

### Phase 7 — Plot 탭 임베딩
- `VolcanoPlotWidget`, `PCAWidget` 등 dialog에서 canvas 분리 (Adapter 패턴)
- `tab_data`에 `sheet_type: 'plot'`, `plot_type`, `plot_params` 필드 추가
- Visualization 메뉴에 "Open in Tab" 옵션 추가 (기존 dialog 팝업 유지)
- 트리 노드에 plot 탭 등록 (`📈` 아이콘)
- `.seqproj` 연동: `plot_params` 직렬화/복원
- 커밋: `feat: embeddable plot widgets with tab support`

> Phase 7은 Phase 6(tab_data 직렬화 인프라) 이후 최종 통합 권장.
> 탭 임베드 자체(저장 없이)는 Phase 6 전에 선행 가능.

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
| `src/utils/project_io.py` | **신규 작성** (Phase 6) | ~150줄 |
| `src/gui/main_window.py` | 수정 (대규모) | ~120줄 수정/추가 |
| `src/gui/dataset_manager.py` | 삭제 또는 stub | 최소화 |
| `src/gui/comparison_panel.py` | 확인 필요 | dataset list 연동 부분 |

---

## 10. 구현 전 확인 필요 사항

- [ ] `tab_data` 키(tab_index)가 탭 제거 후 올바르게 갱신되는지 현재 동작 검증
- [ ] `comparison_panel.update_dataset_list()`가 받는 데이터 형식 확인
- [ ] `presenter.datasets` dict와 `DatasetManagerWidget` combo의 동기화 방식 확인
- [ ] 데이터베이스 불러오기 경로에서 `add_dataset()` 호출 위치 전수 조사

---

## 11. 코드베이스 분석 결과 — 추가 기술 주의사항

현재 `src/gui/main_window.py` 코드를 직접 분석한 결과 발견된 문제점.

### 11-1. `add_dataset_btn` 직접 접근 (L134)

```python
# 현재 (외부에서 내부 버튼 직접 접근 — 캡슐화 위반)
self.dataset_manager.add_dataset_btn.clicked.connect(self._on_add_dataset)
```

`DatasetTreePanel`에서는 `add_requested` 시그널로 교체해야 함:

```python
# 변경 후
self.dataset_tree.add_requested.connect(self._on_add_dataset)
```

`DatasetTreePanel.__init__`에서 Add 버튼 클릭 → `add_requested.emit()` 내부 처리로 감춰야 함.

---

### 11-2. `_generate_unique_name()` 사설 메서드 외부 접근 (L2912)

```python
# 현재 (private 메서드를 외부에서 호출 — 안티패턴)
unique_name = self.dataset_manager._generate_unique_name(dataset.name)
```

`DatasetTreePanel`에서는 이 메서드를 `public`으로 노출하거나, 로직을 호출부로 이전해야 함:

```python
# 방안 A: DatasetTreePanel에서 public 메서드로 제공
unique_name = self.dataset_tree.generate_unique_name(dataset.name)

# 방안 B: 이름 중복 확인 로직을 main_window에서 직접 처리
existing = self.dataset_tree.get_all_root_datasets()
unique_name = _make_unique(dataset.name, existing)  # 헬퍼 함수
```

---

### 11-3. `get_selected_datasets()` — 다중 선택 비교 기능 (L2044)

```python
# _on_compare_datasets()에서 사용
selected_datasets = self.dataset_manager.get_selected_datasets()
```

현재 `DatasetManagerWidget`의 QComboBox는 단일 선택만 지원하지만, `ComparisonPanel`이 자체적으로 체크박스 기반 다중 선택을 제공하고 있어 실제로는 `ComparisonPanel.get_selected_datasets()`가 primary 경로임.

`DatasetTreePanel`로 전환 시:
- QTreeWidget의 다중 선택(Ctrl+클릭) 또는
- `ComparisonPanel` 체크박스 방식 유지 중 하나를 선택해야 함
- **권장**: ComparisonPanel 체크박스 방식 유지, `dataset_manager.get_selected_datasets()` 경로는 `dataset_tree.get_all_root_datasets()`로 교체

---

### 11-4. `tab_data` 접근 횟수 재확인

계획 문서의 "~15곳"은 과소평가. 실제 grep 결과 **~19곳**:

| 패턴 | 횟수 |
|------|------|
| `tab_data[tab_index] = ` (쓰기) | 3 |
| `tab_data[idx]` (읽기) | 10 |
| `tab_data.get(idx, ...)` | 4 |
| `tab_data.items()` / `del tab_data[...]` | 2 |

Phase 1 (`tab_data` dict 변환) 작업량이 예상보다 크므로 **별도 PR/브랜치**로 처리 권장.

---

## 12. Project Save/Load 기능 설계

### 배경 및 동기

트리 패널 전환으로 데이터셋 → 파생 시트 간의 계층 관계가 명확히 드러난다.  
이 계층 구조는 곧 "분석 세션의 스냅샷"이므로, 파일로 저장/복원하는 기능을 함께 구축하는 것이 자연스럽다.

현재 상태:
- `QSettings` (`RNASeqDataView/MainWindow`): 윈도우 크기, splitter 비율만 저장
- `~/.rna_seq_viewer_recent.json`: 최근 열었던 파일 경로 목록만 저장
- **분석 상태(어떤 데이터를 로드했는지, 어떤 필터를 적용했는지)는 전혀 저장되지 않음**

---

### 12-1. 프로젝트 파일 형식: `.seqproj`

```json
{
  "format_version": "1.0",
  "app_version": "1.3.0",
  "created_at": "2026-05-31T10:00:00",
  "description": "",
  "datasets": [
    {
      "name": "DESeq2_KO_vs_WT",
      "type": "differential_expression",
      "file_path": "../data/deseq2_results.csv",
      "sheets": [
        {
          "type": "whole",
          "label": "Whole"
        },
        {
          "type": "filtered",
          "label": "p≤0.05 & FC≥2",
          "filter_params": {
            "filter_mode": "pvalue_fc",
            "adj_pvalue_max": 0.05,
            "log2fc_min": 1.0
          }
        },
        {
          "type": "filtered",
          "label": "Gene List (5 genes)",
          "filter_params": {
            "filter_mode": "gene_list",
            "gene_list": ["BRCA1", "TP53", "EGFR", "MYC", "KRAS"]
          }
        }
      ]
    },
    {
      "name": "GO_UP",
      "type": "go_analysis",
      "file_path": "../data/go_results.csv",
      "sheets": [
        {"type": "whole", "label": "Whole"},
        {"type": "filtered", "label": "FDR≤0.05", "filter_params": {"fdr_max": 0.05}}
      ]
    }
  ],
  "comparisons": [
    {
      "type": "gene_list",
      "label": "Gene Overlap (2)",
      "dataset_names": ["DESeq2_KO_vs_WT", "GO_UP"]
    }
  ],
  "ui_state": {
    "active_tab_index": 1,
    "tree_expanded_datasets": ["DESeq2_KO_vs_WT"]
  }
}
```

파일 경로는 `.seqproj` 파일 위치 기준 **상대 경로** 우선 저장 (이식성).  
Windows 드라이브가 다를 경우에만 절대 경로 fallback.

---

### 12-2. 저장/복원 대상 분류

| 시트 타입 | 저장 가능? | 복원 방법 |
|-----------|-----------|----------|
| Whole | ✅ | 원본 파일 재로드 |
| Filtered (p-value/FC) | ✅ | 원본 재로드 후 filter_params replay |
| Filtered (Gene List) | ✅ | gene_list 임베드 후 재적용 |
| Comparison | ✅ | dataset_names 목록으로 재실행 |
| Clustered (Heatmap) | ⚠️ 부분 | clustering_seed 저장 시 재현 가능, 없으면 skip |
| Multi-Omics 통합 | ✅ | RNA+ATAC 이름 쌍으로 재실행 |

---

### 12-3. 신규 파일: `src/utils/project_io.py`

```python
class ProjectIO:
    FORMAT_VERSION = "1.0"
    FILE_EXTENSION = ".seqproj"

    @staticmethod
    def save(path: Path, tab_data: dict, presenter_datasets: dict,
             ui_state: dict) -> None:
        """현재 분석 상태를 .seqproj 파일로 저장"""

    @staticmethod
    def load(path: Path) -> dict:
        """
        .seqproj 파일에서 프로젝트 명세를 읽어 반환.
        실제 데이터 로드는 MainPresenter가 수행.
        """

    @staticmethod
    def _make_relative_paths(spec: dict, project_dir: Path) -> dict:
        """절대 경로를 project 파일 기준 상대 경로로 변환"""

    @staticmethod
    def _resolve_paths(spec: dict, project_dir: Path) -> dict:
        """상대 경로를 절대 경로로 변환"""
```

`ProjectIO.load()`는 파싱만 수행하고, 실제 DataFrame 재구성은  
`MainPresenter.restore_project(spec)` 또는 `MainWindow._on_open_project()`에서 담당한다.

---

### 12-4. `main_window.py` 메뉴 추가

```python
# File 메뉴 (기존 Open/Save 아래에 삽입)
file_menu.addSeparator()
file_menu.addAction("Save Project...",    self._on_save_project,  QKeySequence("Ctrl+Shift+S"))
file_menu.addAction("Open Project...",    self._on_open_project,  QKeySequence("Ctrl+Shift+O"))
file_menu.addMenu(self._build_recent_projects_menu())  # 서브메뉴
```

---

### 12-5. filter_params 저장 시점

현재 필터 파라미터는 `FilterPanel` UI 상태에만 존재하며 `tab_data`에 저장되지 않는다.  
`_on_filter_completed()` 콜백이 필터 결과 탭을 생성할 때 사용된 파라미터를 함께 저장해야 한다:

```python
# _on_filter_completed() 수정
def _on_filter_completed(self, dataframe, dataset, filter_params):
    tab_index = self._create_data_tab(dataframe, dataset)
    self.tab_data[tab_index]['filter_params'] = filter_params  # 저장
    self.tab_data[tab_index]['parent_dataset'] = dataset.name
    self.tab_data[tab_index]['sheet_type'] = 'filtered'
    self.dataset_tree.add_sheet(dataset.name, tab_index, label, 'filtered')
```

Presenter에서 `filter_completed` 시그널에 `filter_params`를 함께 emit하도록 수정 필요.

---

### 12-6. 기술적 주의사항

**파일 경로 이식성**  
Windows 절대 경로(`C:\Users\...`)는 다른 PC에서 열 수 없음.  
→ `os.path.relpath(file_path, start=project_dir)` 우선, 드라이브가 다를 경우 절대 경로 fallback.

**gene_list 크기**  
gene_list가 수천 개일 경우 `.seqproj` 크기가 커짐.  
→ 1,000개 초과 시 project 파일과 같은 디렉토리에 `<project_name>_genelists/` 폴더로 분리 저장 옵션.

**복원 실패 처리**  
원본 파일이 없거나 컬럼 구조가 변경된 경우:  
→ 해당 dataset만 skip, 나머지 로드 완료 후 "일부 데이터를 불러오지 못했습니다" 경고 다이얼로그.

**Clustered 탭 재현성**  
hclust/k-means 결과는 seed 없이는 재현 불가.  
→ 클러스터링 시 `clustering_seed: int`를 tab_data에 저장, .seqproj에 기록.  
→ 없으면 프로젝트 로드 시 해당 탭을 'Whole'로 대체하고 사용자에게 안내.

---

## 13. Plot 탭 임베딩 계획 (Phase 7)

### 배경 및 동기

현재 모든 시각화(Volcano Plot, PCA, Heatmap, Venn, DotPlot 등)는 `QDialog` 팝업으로 구현되어 있다.  
이 방식의 구조적 한계:
- 하나의 plot을 보면서 다른 데이터셋/시트와 비교 불가
- dialog를 닫으면 결과가 사라지며 "상태"가 없음
- Project 저장(.seqproj) 연동 불가 — dialog 기반 plot은 파라미터 저장/복원 경로가 없음

Phase 1~5에서 구축한 `tab_data` dict + `DatasetTreePanel` 트리 구조는 `sheet_type: 'plot'`을 자연스럽게 수용할 수 있도록 설계되어 있다.

---

### 13-1. 구현 전략: "Dialog 유지 + 탭 열기 옵션" 점진적 이행

dialog를 즉시 제거하지 않고, **기존 dialog는 "빠른 확인"용으로 유지**하면서  
"탭으로 열기" 옵션을 추가하는 방식으로 마이그레이션 리스크를 최소화한다.

```
[Visualization 메뉴]
  ├── Volcano Plot...          (기존 — dialog 팝업)
  ├── Open in Tab > Volcano Plot   (신규 — 탭 임베드)
  └── ...
```

또는 dialog 하단에 "Open in Tab" 버튼 추가로도 대응 가능.

---

### 13-2. 신규 `sheet_type: 'plot'`

`tab_data` dict에 plot 탭을 위한 필드 추가:

```python
tab_data[idx] = {
    'dataframe':       None,           # plot 탭은 DataFrame 없음
    'dataset':         None,
    'parent_dataset':  'DESeq2_KO',    # 어느 데이터셋 기반인지
    'sheet_type':      'plot',
    'sheet_label':     'Volcano: p≤0.05',
    'filter_params':   None,
    'comparison_params': None,
    # 신규 필드
    'plot_type':       'volcano',      # 'volcano'|'pca'|'heatmap'|'venn'|'dotplot'
    'plot_params':     { ... },        # 재렌더링에 필요한 모든 파라미터
    'plot_widget':     QWidget,        # 임베드된 위젯 참조 (직렬화 X)
}
```

`.seqproj` 저장 시 `plot_widget`은 제외하고, `plot_type` + `plot_params`만 직렬화.  
프로젝트 복원 시 파라미터로 재렌더링.

---

### 13-3. 리팩토링 대상 파일

| 파일 | 현재 구조 | 변경 방향 |
|------|----------|----------|
| `gui/visualization_dialog.py` | `VolcanoPlotDialog`, `HeatmapDialog`, `DotPlotDialog` — `QDialog` | figure canvas를 `QWidget`으로 분리 (Adapter 패턴) |
| `gui/pca_dialog.py` | `PCADialog` — `QDialog` | 동일 |
| `gui/venn_dialog.py` | `VennDiagramDialog` — `QDialog` | 동일 |
| `gui/venn_dialog_comparison.py` | `VennDiagramFromComparisonDialog` — `QDialog` | 동일 |

**Adapter 패턴 예시:**

```python
class VolcanoPlotWidget(QWidget):
    """재사용 가능한 Volcano Plot 캔버스 — 탭 임베드용"""
    def __init__(self, dataframe, plot_params, parent=None): ...
    def rerender(self, plot_params): ...
    def export_figure(self, path): ...

class VolcanoPlotDialog(QDialog):
    """기존 dialog — VolcanoPlotWidget을 내부에서 사용"""
    def __init__(self, dataframe, parent=None):
        self._widget = VolcanoPlotWidget(dataframe, {})
        # 기존 dialog UI는 이 widget을 감싸는 shell로 유지
```

---

### 13-4. 트리 노드 구조

```
📊 DESeq2_KO_vs_WT
├── 📋 Whole
├── 🔍 Filtered: p≤0.05
└── 📈 Volcano: p≤0.05        ← sheet_type='plot', plot_type='volcano'

📊 GO_UP
├── 📋 Whole
└── 📊 Heatmap: Top 30        ← sheet_type='plot', plot_type='heatmap'
```

아이콘: `_SHEET_ICONS` dict에 `'plot': '📈'` 추가 (또는 plot_type별 개별 아이콘).

---

### 13-5. Phase 6과의 연동

`.seqproj` 형식에 plot 탭 직렬화 추가:

```json
{
  "type": "plot",
  "label": "Volcano: p≤0.05",
  "plot_type": "volcano",
  "plot_params": {
    "pvalue_threshold": 0.05,
    "log2fc_threshold": 1.0,
    "color_up": "#e74c3c",
    "color_down": "#3498db"
  }
}
```

복원 시: `plot_params`로 `VolcanoPlotWidget` 재생성 → 탭에 삽입.

---

### 13-6. 구현 순서 권장

1. **Phase 6 먼저** — `tab_data` 직렬화 인프라, `plot_params` 필드 구조 확정
2. `VolcanoPlotWidget` 하나만 먼저 분리하여 탭 임베드 검증 (파일럿)
3. 나머지 dialog 순차 전환
4. `.seqproj` plot 탭 저장/복원 통합

---

### 13-7. 기술적 주의사항

**matplotlib 재렌더링 비용**  
복잡한 heatmap/PCA는 재렌더링에 수초 소요 가능.  
→ 탭 전환 시 lazy render: 처음 탭이 보일 때만 렌더링 (`QStackedWidget.currentChanged` 활용).

**메모리**  
탭 수가 늘어나면 matplotlib figure가 메모리에 누적.  
→ 탭 닫기 시 `plt.close(fig)` 명시적 호출 필수.

**탭 내 파라미터 재조정 UI**  
plot 탭 내에서 threshold 등을 실시간 변경하려면 탭 내 우측 또는 하단에 컨트롤 패널 필요.  
→ 탭 내부를 `QSplitter`로 분할 (canvas | controls) 또는 collapsible sidebar.

**Phase 6 의존성**  
`plot_params` 구조 확정 전에는 직렬화 불가.  
→ Phase 7은 Phase 6 이후에 최종 통합. 단, 탭 임베드 자체(저장 없이)는 Phase 6 전에 선행 가능.
