# Plan: Dataset Tree Panel

**목적**: 상단 가로형 콤보박스 방식의 Dataset 선택 UI를 좌측 세로 트리 패널로 교체.  
각 Dataset을 루트 노드로, 파생된 Filtered/Comparison/Clustered sheet를 child 노드로 표시.  
트리에서 노드를 클릭하면 해당 탭이 활성화되고, 탭을 전환하면 트리 선택도 동기화된다.  
**확장 목표**: 트리 구조 전환과 함께 분석 세션을 `.seqproj` 파일로 저장/복원하는 기능을 함께 구축하여 분석 재현성을 확보한다.

**Created**: 2026-04-10  
**Updated**: 2026-06-01  
**Status**: ✅ Phase 1–7 구현 완료 (v1.2.1)

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

### Phase 1 — `tab_data` 구조 변경 (내부 리팩토링) ✅ 완료
- `tab_data`를 tuple에서 dict로 변경
- 모든 접근부를 dict key 방식으로 수정
- `parent_dataset`, `sheet_type`, `filter_params`, `comparison_params` 필드 추가

### Phase 2 — `DatasetTreePanel` 위젯 신규 작성 ✅ 완료
- `src/gui/dataset_tree_panel.py` 신규 작성
- `QTreeWidget` 기반 UI, 시그널 정의, 노드 CRUD 메서드
- `add_root_dataset()`, `add_sheet()`, `remove_sheet()`, `sync_selection()` 구현

### Phase 3 — `main_window.py` 레이아웃 교체 ✅ 완료
- `DatasetManagerWidget` 제거, `DatasetTreePanel` 배치
- 좌측 패널 내부 `QSplitter` 추가 (트리 상단 / 필터+비교 하단)
- 시그널 재연결 (`dataset_selected`, `dataset_removed`, `add_requested`)

### Phase 4 — 트리 ↔ 탭 동기화 ✅ 완료
- `_create_data_tab()`, `_on_filter_completed()` 에서 트리 child 노드 추가
- `_on_tab_close_requested()` 에서 child 노드 제거
- `_on_tab_changed()` 에서 `sync_selection()` 호출
- Guard flag `_syncing_tree` 적용으로 무한 루프 방지

### Phase 5 — 기존 DatasetManagerWidget 제거 및 정리 ✅ 완료
- `DatasetManagerWidget` 가로 bar 제거
- 탭 이름 단축 + 툴팁으로 전체 이름 제공

### Phase 6 — Project Save/Load (`.seqproj`) ✅ 완료
- `src/utils/project_io.py` 신규 작성 (`ProjectIO` 클래스)
- File 메뉴에 Save Project (Ctrl+Shift+S) / Open Project (Ctrl+Shift+O) 추가
- `_on_save_project()`, `_on_open_project_path()` 핸들러 구현
- Recent Projects 서브메뉴 (`_build_recent_projects_menu()`) 구현
- DB 소스 / 파일 소스 / DB fallback 세 경로 모두 지원

### Phase 7 — Plot 탭 임베딩 ✅ 완료
- `VolcanoPlotWidget`, `HeatmapWidget` dialog에서 canvas 분리 (Adapter 패턴)
- `embed_settings=True/False` 파라미터로 설정 패널 위치 제어
- `get_settings_panel()` 메서드 — `embed_settings=False` 시 외부 배치용 패널 반환
- dialog 하단 "📌 Pin to Tab" 버튼 → `plot_pinned` 시그널 emit
- `_pin_plot_to_tab()` 핸들러: `tab_data`에 `sheet_type='plot'`, `plot_type`, `plot_params`, `plot_widget` 저장
- `_SHEET_ICONS['plot'] = '📈'` 추가, 트리 노드 등록
- `.seqproj` 연동: `plot_type` + `plot_params` 직렬화/복원 (2026-06-01 완료)

### Phase 7 Extension — Right Panel Settings Dock ✅ 완료 (2026-06-01)
- `QDockWidget("Plot Settings")` → 우측 도킹 패널
- plot 탭 활성화 시 해당 위젯의 `get_settings_panel()` 결과를 dock에 삽입
- 비-plot 탭 전환 시 dock 자동 숨김
- `_update_plot_settings_dock(index)` 메서드로 탭 전환마다 갱신
- `tab_data` 등록을 `setCurrentIndex()` 호출 **이전**에 수행하여 race condition 해소

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

| 파일 | 변경 유형 | 상태 |
|------|----------|------|
| `src/gui/dataset_tree_panel.py` | 신규 작성 | ✅ 완료 |
| `src/utils/project_io.py` | 신규 작성 | ✅ 완료 |
| `src/gui/main_window.py` | 수정 (대규모) | ✅ 완료 |
| `src/gui/visualization_dialog.py` | VolcanoPlotWidget/HeatmapWidget 분리 | ✅ 완료 |
| `src/gui/dataset_manager.py` | 제거 (stub 불필요) | ✅ 완료 |

---

## 10. 구현 완료 사항 확인

- [x] `tab_data` 키(tab_index)가 탭 제거 후 올바르게 갱신됨 — `_remove_tab_safely()` 재인덱싱 로직 검증
- [x] `comparison_panel.update_dataset_list()` — `DatasetTreePanel.get_all_root_datasets()` 경유로 교체
- [x] `presenter.datasets` 동기화 — `DatasetTreePanel.add_root_dataset()` 호출 시 동시 업데이트
- [x] 데이터베이스 불러오기 경로 전수 조사 완료 — `_on_load_from_database()` 및 `_open_project_path()` 모두 수정

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

## 12. Project Save/Load 기능 설계 — ✅ 구현 완료

**완료일**: 2026-06-01 (Phase 6) / plot 탭 저장/복원: 2026-06-01 (Phase 7 연동)

### 배경 및 동기

트리 패널 전환으로 데이터셋 → 파생 시트 간의 계층 관계가 명확히 드러난다.  
이 계층 구조는 곧 "분석 세션의 스냅샷"이므로, 파일로 저장/복원하는 기능을 함께 구축하는 것이 자연스럽다.

구현 전 상태:
- `QSettings` (`RNASeqDataView/MainWindow`): 윈도우 크기, splitter 비율만 저장
- `~/.rna_seq_viewer_recent.json`: 최근 열었던 파일 경로 목록만 저장
- 분석 상태 저장 없음

**구현 완료 범위:**
- `src/utils/project_io.py` — `ProjectIO` 클래스 (`save`/`load`/`build_spec`)
- File 메뉴 Save Project (Ctrl+Shift+S) / Open Project (Ctrl+Shift+O)
- Recent Projects 서브메뉴
- filtered 시트 복원 (`filter_params` replay)
- plot 시트 저장 (`plot_type`/`plot_params` 직렬화) 및 복원 (`VolcanoPlotWidget`/`HeatmapWidget` 재생성)
- DB 소스 / 파일 소스 / DB fallback 세 경로 모두 지원
- `loaded_ds_name` 추적으로 unique_name 충돌 방지

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
        },
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

| 시트 타입 | 저장 가능? | 복원 방법 | 상태 |
|-----------|-----------|----------|------|
| Whole | ✅ | 원본 파일 재로드 | ✅ 완료 |
| Filtered (p-value/FC) | ✅ | 원본 재로드 후 filter_params replay | ✅ 완료 |
| Filtered (Gene List) | ✅ | gene_list 임베드 후 재적용 | ✅ 완료 |
| Comparison | ✅ | dataset_names 목록으로 재실행 | ⚠️ 미구현 |
| Volcano/Heatmap Plot | ✅ | plot_params로 위젯 재생성 | ✅ 완료 |
| Clustered (Heatmap) | ⚠️ 부분 | clustering_seed 저장 시 재현 가능, 없으면 skip | ⚠️ 미구현 |
| Multi-Omics 통합 | ✅ | RNA+ATAC 이름 쌍으로 재실행 | ⚠️ 미구현 |

---

### 12-3. 구현 파일: `src/utils/project_io.py` ✅ 완료

```python
class ProjectIO:
    FORMAT_VERSION = "1.0"
    FILE_EXTENSION = ".seqproj"

    @staticmethod
    def build_spec(tab_data, presenter_datasets, ui_state) -> dict:
        """tab_data에서 직렬화 가능한 spec dict 생성"""

    @staticmethod
    def save(path: Path, spec: dict) -> None:
        """spec을 .seqproj JSON 파일로 저장"""

    @staticmethod
    def load(path: Path) -> dict:
        """.seqproj 파일 파싱 (실제 DataFrame 재구성은 MainWindow에서)"""

    @staticmethod
    def _make_relative_paths(spec: dict, project_dir: Path) -> dict: ...

    @staticmethod
    def _resolve_paths(spec: dict, project_dir: Path) -> dict: ...
```

`build_spec()`은 `tab_data`를 순회하며 각 탭의 `sheet_type`에 따라:
- `filtered`: `filter_params` 포함
- `plot`: `plot_type` + `plot_params` 포함 (2026-06-01 추가)
- `whole`: 레이블만 기록

---

### 12-4. `main_window.py` 메뉴 추가 ✅ 완료

```python
# File 메뉴 (기존 Open/Save 아래에 삽입)
file_menu.addSeparator()
file_menu.addAction("Save Project...",    self._on_save_project,  QKeySequence("Ctrl+Shift+S"))
file_menu.addAction("Open Project...",    self._on_open_project,  QKeySequence("Ctrl+Shift+O"))
file_menu.addMenu(self._build_recent_projects_menu())  # 서브메뉴
```

---

### 12-5. filter_params 저장 시점 ✅ 완료

`_on_filter_completed()` 에서 `filter_params`를 `tab_data`에 함께 저장:

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

### 12-6. 기술적 주의사항 및 해결 현황

**파일 경로 이식성** ✅ 구현됨  
→ `os.path.relpath()` 우선, 드라이브 다를 경우 절대 경로 fallback (`project_io.py` `_make_relative_paths`).

**gene_list 크기**  
gene_list가 수천 개일 경우 `.seqproj` 크기가 커짐.  
→ 1,000개 초과 시 분리 저장 옵션 — 미구현 (향후 개선).

**복원 실패 처리** ✅ 구현됨  
→ 원본 파일 없거나 컬럼 구조 변경 시 해당 dataset만 skip, `missing_files` 리스트에 기록 후 경고 다이얼로그 표시.

**Clustered 탭 재현성**  
→ 미구현. 클러스터링 시 `clustering_seed` 저장 후 `.seqproj`에 기록 방식 계획 중.

---

## 13. Plot 탭 임베딩 (Phase 7) — ✅ 구현 완료

**완료일**: 2026-06-01

### 배경 및 동기

기존 Volcano Plot / Heatmap은 `QDialog` 팝업으로만 구현되어 있었다.  
한계:
- 하나의 plot을 보면서 다른 데이터셋/시트와 비교 불가
- dialog를 닫으면 결과가 사라지며 "상태"가 없음
- Project 저장(.seqproj) 연동 불가

Phase 1~5에서 구축한 `tab_data` dict + `DatasetTreePanel` 트리 구조가 `sheet_type: 'plot'`을 수용.

---

### 13-1. 구현 전략 — ✅ 채택 방식

**dialog 하단 "📌 Pin to Tab" 버튼** 방식 채택.  
dialog는 "빠른 확인"용으로 유지, 영구 보존이 필요한 경우에만 탭으로 고정.

```
VolcanoPlotDialog / HeatmapDialog
  └─ 하단 버튼바: [Export PNG] [📌 Pin to Tab]   ← 신규
```

"📌 Pin to Tab" 클릭 시:
1. 현재 파라미터 스냅샷 → `plot_params` dict
2. `plot_pinned(widget, label, plot_type, plot_params)` 시그널 emit
3. `MainWindow._pin_plot_to_tab()` 수신 → 탭 추가 + `tab_data` 등록 + 트리 child 추가

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

### 13-3. 구현된 위젯 분리 구조

| 파일 | 구현 상태 |
|------|----------|
| `gui/visualization_dialog.py` — `VolcanoPlotWidget` | ✅ 완료 |
| `gui/visualization_dialog.py` — `HeatmapWidget` | ✅ 완료 |
| `gui/visualization_dialog.py` — `DotPlotDialog` | 미분리 (계획 보류) |
| `gui/pca_dialog.py` — `PCADialog` | 미분리 (계획 보류) |
| `gui/venn_dialog.py` — `VennDiagramDialog` | 미분리 (계획 보류) |

**실제 구현된 Adapter 패턴:**

```python
class VolcanoPlotWidget(QWidget):
    """탭 임베드용 — embed_settings 파라미터로 설정 패널 위치 제어"""
    def __init__(self, dataframe, plot_params=None, parent=None,
                 show_pin_button=True, embed_settings=True): ...
    def get_settings_panel(self) -> QWidget | None:
        """embed_settings=False일 때 외부 배치용 패널 반환"""

class VolcanoPlotDialog(QDialog):
    plot_pinned = pyqtSignal(QWidget, str, str, dict)  # widget, label, plot_type, plot_params
    """dialog는 embed_settings=True로 VolcanoPlotWidget 내포"""
    def _on_pin_requested(self, params):
        tab_widget = VolcanoPlotWidget(self.dataframe, plot_params=params,
                                       show_pin_button=False, embed_settings=False)
        self.plot_pinned.emit(tab_widget, label, 'volcano', params)
```

`embed_settings=False`로 생성된 위젯은 설정 패널을 `_settings_panel` 속성에 분리 보관.  
→ `get_settings_panel()` 로 꺼내 **Right Panel Dock**에 삽입.

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

### 13-6. 구현 완료 내역

1. ✅ Phase 6 먼저 완료 — `tab_data` 직렬화 인프라, `filter_params`/`comparison_params` 직렬화
2. ✅ `VolcanoPlotWidget` + `HeatmapWidget` 분리 및 탭 임베드 검증
3. ⏸ 나머지 dialog (PCA, Venn, DotPlot) 분리 — 우선순위 낮음, 별도 Phase로 이연
4. ✅ `.seqproj` plot 탭 저장/복원 통합 (2026-06-01 완료)

---

### 13-7. 기술적 주의사항 및 해결 현황

**matplotlib 재렌더링 비용**  
복잡한 heatmap은 재렌더링 수초 소요.  
→ 현재 Pin 시점에 1회만 렌더링 후 위젯 재사용. Lazy render는 미구현 (추후 개선 가능).

**메모리**  
탭 수가 늘어나면 matplotlib figure 누적.  
→ `_remove_tab_safely()` 에서 `sheet_type == 'plot'` 시 `plt.close(fig)` 호출 필요 (미해결 — 추후 개선).

**탭 내 파라미터 재조정 UI** ✅ **해결됨 (Right Panel Dock)**  
→ `embed_settings=False` + `get_settings_panel()` 패턴으로 설정 패널을 우측 `QDockWidget`에 삽입.  
→ plot 탭 전환 시 `_update_plot_settings_dock()` 호출로 dock 내용 자동 교체.

**Race condition (tab_data vs setCurrentIndex)**  
→ `_pin_plot_to_tab()` 에서 `tab_data[tab_index] = {...}` 를 `setCurrentIndex()` 호출 **이전**에 수행하여 해소.

---

## 14. Right Panel Settings Dock (Phase 7 Extension) — ✅ 완료

**완료일**: 2026-06-01

### 14-1. 구현 내용

`MainWindow` 우측에 `QDockWidget("Plot Settings")` 추가.  
plot 탭이 활성화될 때 해당 위젯의 설정 패널을 dock에 삽입, 비-plot 탭 전환 시 dock 숨김.

```python
# main_window.py _init_ui() 내
self.plot_settings_dock = QDockWidget("Plot Settings", self)
self.plot_settings_dock.setObjectName("PlotSettingsDock")
self.plot_settings_dock.setAllowedAreas(
    Qt.DockWidgetArea.RightDockWidgetArea | Qt.DockWidgetArea.LeftDockWidgetArea
)
self.plot_settings_dock.setMinimumWidth(250)
self.plot_settings_dock.setMaximumWidth(380)
self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.plot_settings_dock)
self.plot_settings_dock.hide()
self._current_settings_widget: QWidget | None = None
```

### 14-2. 탭 전환 시 dock 갱신 흐름

```
_on_tab_changed(index)
  └→ _update_plot_settings_dock(index)
       ├─ tab_data[index].sheet_type == 'plot'?
       │    YES → plot_widget.get_settings_panel() 가져와 dock에 삽입 → dock.show()
       └─ NO  → dock.hide(), _current_settings_widget = None
```

### 14-3. embed_settings 패턴

| 생성 위치 | embed_settings | 설정 패널 위치 |
|----------|---------------|---------------|
| Dialog 내 (빠른 확인용) | `True` (기본값) | 위젯 레이아웃 내 좌측 스크롤 영역 |
| Pin to Tab 후 탭 위젯 | `False` | `_settings_panel` 속성에 분리 보관 → Dock에 삽입 |
