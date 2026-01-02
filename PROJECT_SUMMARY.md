# 🧬 CMG-SeqViewer - RNA-Seq Data Analysis and Visualization Program

## 📋 프로젝트 개요

**CMG-SeqViewer**는 RNA-Seq 데이터 분석을 위한 전문적인 데스크톱 애플리케이션입니다. Excel과 유사한 직관적인 인터페이스를 제공하며, FSM(유한 상태 머신) 기반의 견고한 상태 관리와 MVP 아키텍처 패턴을 적용하여 확장 가능하고 유지보수가 용이한 구조로 설계되었습니다.

### 주요 특징
- 🎯 **전문적인 분석**: Fisher's Exact Test, GSEA, 다중 데이터셋 비교
- 🎨 **직관적인 UI**: Excel 스타일의 탭 기반 인터페이스
- 🔧 **견고한 아키텍처**: FSM + MVP 패턴으로 안정적인 상태 관리
- ⚡ **비동기 처리**: QThread 기반으로 대용량 데이터 처리 시에도 UI 반응성 유지
- 📊 **다양한 시각화**: Volcano Plot, Histogram, Heatmap, Venn Diagram, Dot Plot
- 📝 **상세한 로깅**: Audit Log와 실시간 GUI 터미널

---

## ✅ 구현 완료된 기능

### 1. **핵심 아키텍처** ✓
- ✅ **FSM (Finite State Machine)**: 12개 상태, 18개 이벤트로 견고한 상태 관리
- ✅ **MVP Pattern**: Model-View-Presenter 패턴으로 GUI와 비즈니스 로직 완벽 분리
- ✅ **비동기 처리**: QThread 기반 Worker 클래스 5종 (Load, Filter, Analysis, Comparison, Export)

### 2. **데이터 관리** ✓
- ✅ Excel 파일 자동 파싱 (Differential Expression, GO Analysis)
- ✅ 지능형 컬럼 매핑 (30+ 가지 컬럼명 패턴 자동 인식)
- ✅ 다중 데이터셋 동시 관리 (탭 기반 전환)
- ✅ 유전자 리스트 파일/텍스트 입력 지원
- ✅ Drag & Drop 파일 로드
- ✅ 최근 파일 히스토리 (10개)

### 3. **필터링 기능** ✓
- ✅ **Statistical Filter**: adj.p-value, log2FC 기반 필터링
- ✅ **Regulation Direction**: Up-regulated, Down-regulated, Both 선택 필터
- ✅ **Gene List Filter**: 특정 유전자 리스트 기반 필터링
- ✅ **Multi-column Support**: 여러 데이터셋 컬럼 동시 필터링
- ✅ **Cascading Filter**: 필터링된 결과에 재필터링 가능

### 4. **통계 분석** ✓
- ✅ **Fisher's Exact Test**: 유전자 리스트 enrichment 분석 (GO term enrichment)
- ✅ **GSEA Lite**: Gene set enrichment 방향성 분석 (Up/Down regulation)
- ✅ **다중 데이터셋 비교**: 2-5개 데이터셋 간 교집합/합집합 분석
- ✅ **비교 결과 테이블**: 데이터셋별 유전자 존재 여부 매트릭스

### 5. **시각화 기능** ✓
- ✅ **Volcano Plot**: log2FC vs -log10(padj) 산점도, 커스터마이징 가능
- ✅ **P-adj Histogram**: 조정된 p-value 분포 히스토그램
- ✅ **Heatmap**: 유전자 발현 히트맵 (클러스터링 포함)
- ✅ **Venn Diagram**: 2-5개 데이터셋 벤다이어그램 (유전자 비교/분석 결과 비교)
- ✅ **Dot Plot**: GO term enrichment 시각화
- ✅ 모든 플롯 PNG/SVG/PDF 저장 기능

### 6. **GUI 구현** ✓
- ✅ **Excel 스타일 인터페이스**: 탭 기반 데이터 뷰, 정렬/검색 지원
- ✅ **필터 패널**: 좌측 사이드바, 2-탭 구조 (Gene List / Statistical)
- ✅ **데이터셋 관리자**: 상단 콤보박스, 데이터셋 추가/제거
- ✅ **비교 패널**: 다중 데이터셋 선택 및 비교 설정
- ✅ **로그 터미널**: 하단 실시간 로그 표시 (VS Code 스타일, 색상 구분)
- ✅ **메뉴바**: File, Analysis, Visualization, View, Help
- ✅ **툴바**: 주요 기능 빠른 접근 버튼
- ✅ **상태바**: 현재 데이터셋 정보, 행/열 개수 표시
- ✅ **도움말 다이얼로그**: 8개 섹션 HTML 도움말 (Getting Started ~ Tips)
- ✅ **컬럼 표시 레벨**: Basic, DE (Differential Expression), Full 전환 기능

### 7. **로깅 시스템** ✓
- ✅ **Audit Logger**: 사용자 활동 기록 (시간, 조건, 결과, 소요 시간)
- ✅ **실시간 피드백**: GUI 터미널에 색상별 즉시 표시 (INFO/WARNING/ERROR)
- ✅ **파일 로깅**: 일별 로그 파일 자동 생성 (`logs/rna_seq_YYYYMMDD_HHMMSS.log`)
- ✅ **로그 버퍼**: 최근 1000개 로그 메모리 유지

### 8. **데이터 내보내기** ✓
- ✅ Excel (.xlsx), CSV, TSV 형식 지원
- ✅ 현재 탭 데이터 내보내기
- ✅ 필터링/분석 결과 저장
- ✅ 비동기 Export Worker로 대용량 파일 저장

### 9. **기타 편의 기능** ✓
- ✅ 클립보드 복사/붙여넣기 (Ctrl+C / Ctrl+V)
- ✅ 전체 선택 (Ctrl+A)
- ✅ 숫자 정렬 지원 (NumericTableWidgetItem)
- ✅ 테이블 컬럼 자동 크기 조정
- ✅ 탭 닫기 (닫기 버튼 / Ctrl+W)
- ✅ 데이터 유효성 검사 (필수 컬럼 체크)
- ✅ 진행률 표시 (상태바 프로그레스 바)

### 10. **테스트 코드** ✓
- ✅ FSM 테스트 (상태 전환, 콜백, 유효성 검사)
- ✅ 데이터 모델 테스트 (Dataset, FilterCriteria, ComparisonResult)
- ✅ 통계 분석 테스트 (Fisher's test, GSEA, 비교 분석)

---

## 📁 프로젝트 구조

```
rna-seq-data-view/
├── src/                              # 소스 코드 루트
│   ├── main.py                       # 프로그램 진입점 ⭐
│   │
│   ├── core/                         # 핵심 로직 계층
│   │   ├── fsm.py                   # 유한 상태 머신 (FSM)
│   │   │   ├── State (Enum): 12개 상태 정의
│   │   │   ├── Event (Enum): 18개 이벤트 정의
│   │   │   ├── Transition (dataclass): 상태 전환 정의
│   │   │   └── FSM (class): 상태 관리 엔진 🔄
│   │   │       ├── trigger(event): 이벤트 트리거
│   │   │       ├── can_trigger(event): 전환 가능 여부 확인
│   │   │       ├── register_on_enter/on_exit: 상태 콜백 등록
│   │   │       └── add_state_change_listener: 리스너 등록
│   │   │
│   │   └── logger.py                # 로깅 시스템
│   │       ├── QtLogHandler: Qt GUI 로그 핸들러
│   │       ├── LogBuffer: 로그 버퍼 (1000개)
│   │       ├── get_audit_logger(): Audit 로거 팩토리
│   │       └── AuditLogger: 사용자 활동 기록 📝
│   │
│   ├── models/                       # 데이터 모델 계층
│   │   └── data_models.py           # 모든 데이터 클래스 정의 📊
│   │       ├── DatasetType (Enum): DIFFERENTIAL_EXPRESSION, GO_ANALYSIS
│   │       ├── FilterMode (Enum): GENE_LIST, STATISTICAL
│   │       ├── DifferentialExpressionData (@dataclass): DE 데이터 구조
│   │       ├── GOAnalysisData (@dataclass): GO 데이터 구조
│   │       ├── Dataset (@dataclass): 메인 데이터셋 클래스
│   │       │   ├── get_filtered_data(): 필터링된 데이터 반환
│   │       │   ├── get_genes(): 유전자 리스트 추출
│   │       │   ├── get_summary(): 데이터셋 요약 정보
│   │       │   └── _get_column_name(): 컬럼 매핑 헬퍼
│   │       ├── FilterCriteria (@dataclass): 필터 조건
│   │       │   ├── mode: FilterMode
│   │       │   ├── adj_pvalue_max: float
│   │       │   ├── log2fc_min: float
│   │       │   ├── regulation_direction: "up"/"down"/"both"
│   │       │   ├── gene_list: Optional[List[str]]
│   │       │   └── fdr_max: float
│   │       └── ComparisonResult (@dataclass): 비교 분석 결과
│   │           ├── dataset_names: List[str]
│   │           ├── common_genes: List[str]
│   │           ├── unique_genes: Dict[str, List[str]]
│   │           └── comparison_table: pd.DataFrame
│   │
│   ├── gui/                          # GUI 컴포넌트 계층
│   │   ├── main_window.py           # 메인 윈도우 (1988 lines) 🖥️
│   │   │   ├── NumericTableWidgetItem: 숫자 정렬 지원 아이템
│   │   │   └── MainWindow (QMainWindow):
│   │   │       ├── _init_ui(): UI 레이아웃 구성
│   │   │       ├── _create_menu_bar(): 메뉴바 생성
│   │   │       ├── _create_tool_bar(): 툴바 생성
│   │   │       ├── _create_status_bar(): 상태바 생성
│   │   │       ├── _on_dataset_selected(): 데이터셋 전환
│   │   │       ├── _on_filter_requested(): 필터링 요청 처리
│   │   │       ├── _filter_current_tab(): 현재 탭 필터링 (핵심)
│   │   │       ├── _on_analysis_requested(): 분석 요청 처리
│   │   │       ├── populate_table(): 테이블 데이터 채우기
│   │   │       ├── _copy_selection(): 클립보드 복사
│   │   │       ├── _paste_to_gene_input(): 클립보드 붙여넣기
│   │   │       └── _export_current_tab(): 데이터 내보내기
│   │   │
│   │   ├── filter_panel.py          # 필터 패널 (378 lines) 🔍
│   │   │   └── FilterPanel (QWidget):
│   │   │       ├── filter_tabs: QTabWidget (Gene List / Statistical)
│   │   │       ├── gene_input: QTextEdit (유전자 입력)
│   │   │       ├── adj_pvalue_input: QDoubleSpinBox
│   │   │       ├── log2fc_input: QDoubleSpinBox
│   │   │       ├── regulation_group: QButtonGroup (Up/Down/Both)
│   │   │       ├── fdr_input: QDoubleSpinBox (GO analysis용)
│   │   │       ├── get_gene_list(): 입력된 유전자 리스트 파싱
│   │   │       ├── get_filter_criteria(): FilterCriteria 반환
│   │   │       └── set_filter_criteria(): 필터 조건 설정
│   │   │
│   │   ├── dataset_manager.py       # 데이터셋 관리자 📂
│   │   │   └── DatasetManagerWidget (QWidget):
│   │   │       ├── dataset_combo: QComboBox
│   │   │       ├── add_dataset_btn: QPushButton
│   │   │       ├── remove_dataset_btn: QPushButton
│   │   │       └── Signals: dataset_selected, dataset_removed
│   │   │
│   │   ├── comparison_panel.py      # 비교 패널
│   │   │   └── ComparisonPanel (QWidget):
│   │   │       ├── dataset_checkboxes: List[QCheckBox]
│   │   │       ├── operation_combo: QComboBox (Intersection/Union)
│   │   │       └── Signal: compare_requested
│   │   │
│   │   ├── workers.py               # 비동기 Worker 클래스 ⚡
│   │   │   ├── DataLoadWorker (QThread): 데이터 로드
│   │   │   ├── FilterWorker (QThread): 데이터 필터링
│   │   │   ├── AnalysisWorker (QThread): 통계 분석
│   │   │   ├── ComparisonWorker (QThread): 데이터셋 비교
│   │   │   └── ExportWorker (QThread): 파일 내보내기
│   │   │
│   │   ├── visualization_dialog.py  # 시각화 다이얼로그 🎨
│   │   │   ├── VolcanoPlotDialog: Volcano plot 생성/커스터마이징
│   │   │   ├── PadjHistogramDialog: P-adj 히스토그램
│   │   │   ├── HeatmapDialog: 히트맵 (클러스터링)
│   │   │   └── DotPlotDialog: GO enrichment dot plot
│   │   │
│   │   ├── venn_dialog.py           # Venn 다이얼로그
│   │   │   └── VennDiagramDialog: 유전자 리스트 벤다이어그램
│   │   │
│   │   ├── venn_dialog_comparison.py
│   │   │   └── VennDiagramFromComparisonDialog: 분석 결과 벤다이어그램
│   │   │
│   │   └── help_dialog.py           # 도움말 다이얼로그 📖
│   │       └── HelpDialog (QDialog): 8개 섹션 HTML 도움말
│   │
│   ├── presenters/                   # MVP Presenter 계층
│   │   └── main_presenter.py        # 메인 Presenter (670 lines) 🎯
│   │       └── MainPresenter (QObject):
│   │           ├── fsm: FSM 인스턴스
│   │           ├── datasets: Dict[str, Dataset]
│   │           ├── current_dataset: Optional[Dataset]
│   │           ├── data_loader: DataLoader
│   │           ├── analyzer: StatisticalAnalyzer
│   │           ├── load_dataset(): 데이터 로드 (비동기)
│   │           ├── apply_filter(): 필터 적용
│   │           ├── run_fisher_test(): Fisher's Exact Test
│   │           ├── run_gsea(): GSEA Lite
│   │           ├── compare_datasets(): 다중 데이터셋 비교
│   │           ├── export_data(): 데이터 내보내기
│   │           └── Signals: dataset_loaded, filter_completed, etc.
│   │
│   └── utils/                        # 유틸리티 계층
│       ├── data_loader.py           # 데이터 로더 📥
│       │   └── DataLoader (class):
│       │       ├── COLUMN_MAPPINGS: 30+ 컬럼 패턴 매핑
│       │       ├── load_data(): Excel/CSV/TSV 로드
│       │       ├── _detect_dataset_type(): 자동 타입 감지
│       │       ├── _auto_map_columns(): 지능형 컬럼 매핑
│       │       └── _validate_dataset(): 데이터 유효성 검사
│       │
│       └── statistics.py            # 통계 분석 📈
│           └── StatisticalAnalyzer (class):
│               ├── fisher_exact_test(): Fisher's test (GO enrichment)
│               ├── gsea_lite(): GSEA 방향성 분석
│               ├── compare_datasets(): 다중 데이터셋 비교
│               └── _calculate_enrichment(): Enrichment 계산
│
├── test/                             # 단위 테스트
│   ├── test_fsm.py                  # FSM 테스트 (15 tests) ✅
│   ├── test_models.py               # 모델 테스트 (10 tests) ✅
│   └── test_statistics.py           # 통계 테스트 (8 tests) ✅
│
├── examples/                         # 사용 예제
│   └── usage_examples.py            # API 사용 예제 코드 💡
│
├── docs/                             # 문서
│   ├── FSM_DIAGRAM.md               # FSM 상태 다이어그램 📖
│   └── API_REFERENCE.md             # API 레퍼런스 (선택)
│
├── logs/                             # 로그 파일 (자동 생성)
│   ├── rna_seq_YYYYMMDD_HHMMSS.log # 일별 상세 로그
│   └── audit_YYYYMMDD.log          # Audit 로그
│
├── requirements.txt                  # 의존성 패키지 📦
│   ├── PyQt6>=6.4.0
│   ├── pandas>=1.5.0
│   ├── numpy>=1.23.0
│   ├── openpyxl>=3.0.0
│   ├── matplotlib>=3.6.0
│   ├── seaborn>=0.12.0
│   ├── scipy>=1.9.0
│   └── matplotlib-venn>=0.11.7
│
├── setup.py                          # 설치 스크립트 🔧
├── .gitignore                        # Git 무시 파일 🚫
├── README.md                         # 프로젝트 설명서 📘
├── PROJECT_SUMMARY.md                # 이 문서 (프로젝트 요약) 📋
└── DEPLOYMENT.md                     # 배포 가이드 (exe 생성) 🚀
```

---

## 🎯 핵심 설계 원칙 및 아키텍처 패턴

### 1. **FSM (Finite State Machine) 기반 상태 관리** 🔄

FSM은 프로그램의 모든 상태를 명시적으로 정의하고, 상태 간 전환을 이벤트로 제어합니다.

#### 상태 전환 흐름
```
State.IDLE 
  ↓ [LOAD_DATA]
State.LOADING_DATA
  ↓ [DATA_LOAD_SUCCESS]
State.DATA_LOADED
  ↓ [START_FILTER]
State.FILTERING
  ↓ [FILTER_SUCCESS]
State.FILTER_COMPLETE
  ↓ [START_ANALYSIS]
State.ANALYZING
  ↓ [ANALYSIS_SUCCESS]
State.ANALYSIS_COMPLETE
  ↓ [RESET] → State.DATA_LOADED
```

#### 12개 상태 (State Enum)
| 상태 | 설명 | 진입 조건 |
|------|------|----------|
| `IDLE` | 초기 상태, 데이터 없음 | 프로그램 시작 |
| `LOADING_DATA` | 데이터 로딩 중 | LOAD_DATA 이벤트 |
| `DATA_LOADED` | 데이터 로드 완료 | DATA_LOAD_SUCCESS |
| `FILTERING` | 필터링 작업 수행 중 | START_FILTER |
| `FILTER_COMPLETE` | 필터링 완료 | FILTER_SUCCESS |
| `ANALYZING` | 통계 분석 중 (Fisher's/GSEA) | START_ANALYSIS |
| `ANALYSIS_COMPLETE` | 분석 완료 | ANALYSIS_SUCCESS |
| `COMPARING` | 다중 데이터셋 비교 중 | START_COMPARISON |
| `COMPARISON_COMPLETE` | 비교 완료 | COMPARISON_SUCCESS |
| `PLOTTING` | 시각화 생성 중 | START_PLOT |
| `EXPORTING` | 데이터 내보내기 중 | START_EXPORT |
| `ERROR` | 오류 상태 | ERROR_OCCURRED |

#### 18개 이벤트 (Event Enum)
```python
# 데이터 로드
LOAD_DATA, DATA_LOAD_SUCCESS, DATA_LOAD_FAILED

# 필터링
START_FILTER, FILTER_SUCCESS, FILTER_FAILED

# 분석
START_ANALYSIS, ANALYSIS_SUCCESS, ANALYSIS_FAILED

# 비교
START_COMPARISON, COMPARISON_SUCCESS, COMPARISON_FAILED

# 시각화
START_PLOT, PLOT_COMPLETE

# 내보내기
START_EXPORT, EXPORT_COMPLETE

# 상태 제어
RESET, ERROR_OCCURRED, ERROR_RESOLVED
```

#### FSM 사용 예시
```python
# Presenter에서 FSM 제어
def load_dataset(self, file_path):
    # 상태 전환 가능 여부 확인
    if not self.fsm.can_trigger(Event.LOAD_DATA):
        self.logger.warning("Cannot load data in current state")
        return
    
    # 이벤트 트리거 (IDLE → LOADING_DATA)
    self.fsm.trigger(Event.LOAD_DATA)
    
    # 비동기 작업 시작
    worker = DataLoadWorker(file_path)
    worker.finished.connect(lambda: self.fsm.trigger(Event.DATA_LOAD_SUCCESS))
    worker.error.connect(lambda e: self.fsm.trigger(Event.DATA_LOAD_FAILED))
    worker.start()
```

#### FSM의 장점
- ✅ **명시적 상태 관리**: 현재 상태를 항상 알 수 있음
- ✅ **버그 방지**: 잘못된 상태 전환 차단 (예: 데이터 없이 필터링 시도)
- ✅ **자동 로깅**: 모든 상태 전환이 자동으로 로그에 기록
- ✅ **콜백 시스템**: 상태 진입/이탈 시 자동 실행할 함수 등록 가능
- ✅ **디버깅 용이**: 상태 히스토리 추적 가능

---

### 2. **MVP (Model-View-Presenter) 패턴** 🎯

GUI와 비즈니스 로직을 완전히 분리하여 테스트 가능하고 유지보수가 용이한 구조를 제공합니다.

#### 계층 구조
```
┌──────────────────────────────────────────────────┐
│                    View Layer                     │
│  (GUI 컴포넌트: MainWindow, FilterPanel 등)      │
│  - 사용자 입력 수신                               │
│  - 데이터 표시                                    │
│  - UI 이벤트 → Presenter로 전달                  │
└─────────────────┬────────────────────────────────┘
                  │ Signals/Slots
                  ↓
┌──────────────────────────────────────────────────┐
│                 Presenter Layer                   │
│     (MainPresenter: 비즈니스 로직 조정자)        │
│  - FSM 상태 관리                                  │
│  - Worker 생성 및 관리                           │
│  - Model과 View 중재                             │
│  - 비즈니스 규칙 적용                             │
└─────────────────┬────────────────────────────────┘
                  │ Method Calls
                  ↓
┌──────────────────────────────────────────────────┐
│                   Model Layer                     │
│ (Dataset, DataLoader, StatisticalAnalyzer 등)   │
│  - 데이터 저장 및 관리                            │
│  - 비즈니스 로직 실행 (필터링, 분석)             │
│  - 데이터 유효성 검사                             │
└──────────────────────────────────────────────────┘
```

#### 각 계층의 역할

**View (gui/main_window.py, gui/filter_panel.py)**
```python
class MainWindow(QMainWindow):
    """View는 오직 UI 표시와 사용자 입력만 처리"""
    
    def _on_filter_requested(self):
        # 1. UI에서 필터 조건 수집
        criteria = self.filter_panel.get_filter_criteria()
        
        # 2. Presenter에게 전달 (비즈니스 로직 호출 없음!)
        self.presenter.apply_filter(criteria)
    
    def _on_dataset_loaded(self, dataset_name, dataset):
        # 3. Presenter로부터 결과 수신 (Signal)
        # 4. UI에 표시만 수행
        self.populate_table(self.get_current_table(), dataset.dataframe)
```

**Presenter (presenters/main_presenter.py)**
```python
class MainPresenter(QObject):
    """Presenter는 View와 Model을 중재하고 FSM으로 상태 관리"""
    
    # Signals로 View에 결과 전달
    dataset_loaded = pyqtSignal(str, Dataset)
    filter_completed = pyqtSignal(pd.DataFrame, str)
    
    def apply_filter(self, criteria: FilterCriteria):
        # 1. FSM 상태 확인 및 전환
        if not self.fsm.can_trigger(Event.START_FILTER):
            return
        self.fsm.trigger(Event.START_FILTER)
        
        # 2. Model 호출 (비동기 Worker)
        worker = FilterWorker(self.current_dataset, criteria)
        worker.finished.connect(self._on_filter_finished)
        worker.start()
    
    def _on_filter_finished(self, result_df):
        # 3. 결과 처리 및 FSM 전환
        self.fsm.trigger(Event.FILTER_SUCCESS)
        
        # 4. View에 Signal로 결과 전달
        self.filter_completed.emit(result_df, "Filtered Data")
```

**Model (models/data_models.py, utils/data_loader.py)**
```python
@dataclass
class Dataset:
    """Model은 순수 데이터와 비즈니스 로직만 포함"""
    name: str
    dataframe: pd.DataFrame
    
    def get_filtered_data(self, **filters) -> pd.DataFrame:
        """필터링 로직 (UI 독립적)"""
        filtered = self.dataframe.copy()
        
        if 'adj_pvalue_max' in filters:
            padj_col = self._get_column_name('adj_pvalue')
            filtered = filtered[filtered[padj_col] <= filters['adj_pvalue_max']]
        
        return filtered
```

#### MVP 패턴의 장점
- ✅ **테스트 용이**: Model과 Presenter는 GUI 없이 단위 테스트 가능
- ✅ **재사용성**: Model은 다른 UI(CLI, Web 등)에서도 재사용 가능
- ✅ **유지보수**: 각 계층의 책임이 명확하여 수정 영향 범위 최소화
- ✅ **확장성**: 새 기능 추가 시 계층별로 독립적으로 작업 가능

---

### 3. **비동기 처리 (QThread Worker 패턴)** ⚡

대용량 데이터 처리 시에도 GUI가 멈추지 않도록 모든 무거운 작업을 별도 스레드에서 실행합니다.

#### 5가지 Worker 클래스 (gui/workers.py)

| Worker | 작업 내용 | 실행 시점 | 평균 소요 시간 |
|--------|----------|-----------|----------------|
| `DataLoadWorker` | Excel/CSV 파일 로드, 파싱 | 파일 열기 시 | 1-5초 (파일 크기 의존) |
| `FilterWorker` | 대규모 DataFrame 필터링 | 필터 버튼 클릭 시 | 0.1-2초 |
| `AnalysisWorker` | Fisher's test, GSEA 실행 | 분석 메뉴 선택 시 | 0.5-3초 |
| `ComparisonWorker` | 다중 데이터셋 비교 연산 | 비교 버튼 클릭 시 | 0.5-2초 |
| `ExportWorker` | Excel/CSV 파일 저장 | 내보내기 시 | 1-10초 |

#### Worker 사용 패턴
```python
# Presenter에서 Worker 생성 및 실행
def load_dataset(self, file_path: Path):
    # 1. FSM 상태 전환
    self.fsm.trigger(Event.LOAD_DATA)
    
    # 2. Worker 생성
    worker = DataLoadWorker(file_path, dataset_name)
    
    # 3. Signal 연결
    worker.finished.connect(self._on_load_finished)
    worker.error.connect(self._on_load_error)
    worker.progress.connect(self.progress_updated.emit)
    
    # 4. Worker 목록 관리 (메모리 누수 방지)
    self.active_workers.append(worker)
    worker.finished.connect(lambda: self.active_workers.remove(worker))
    
    # 5. 비동기 실행
    worker.start()

def _on_load_finished(self, dataset: Dataset):
    # 6. 결과 수신 및 FSM 전환
    self.fsm.trigger(Event.DATA_LOAD_SUCCESS)
    self.datasets[dataset.name] = dataset
    self.dataset_loaded.emit(dataset.name, dataset)
```

#### Worker 구현 예시
```python
class FilterWorker(QThread):
    """필터링 Worker"""
    finished = pyqtSignal(pd.DataFrame)
    error = pyqtSignal(str)
    progress = pyqtSignal(int)
    
    def __init__(self, dataset: Dataset, criteria: FilterCriteria):
        super().__init__()
        self.dataset = dataset
        self.criteria = criteria
    
    def run(self):
        """별도 스레드에서 실행되는 메서드"""
        try:
            # 무거운 작업 수행
            filtered_df = self.dataset.get_filtered_data(
                adj_pvalue_max=self.criteria.adj_pvalue_max,
                log2fc_min=self.criteria.log2fc_min,
                regulation_direction=self.criteria.regulation_direction
            )
            
            # 완료 Signal 발송 (메인 스레드로 전달)
            self.finished.emit(filtered_df)
            
        except Exception as e:
            # 에러 Signal 발송
            self.error.emit(str(e))
```

#### 비동기 처리의 장점
- ✅ **반응성 유지**: 10만 행 데이터 로드 중에도 UI 조작 가능
- ✅ **진행률 표시**: 상태바 프로그레스 바로 작업 진행 상황 표시
- ✅ **취소 가능**: Worker 참조 유지로 작업 중단 가능 (추후 구현 가능)
- ✅ **에러 처리**: Worker 내부 예외를 안전하게 GUI로 전달

---

## 🚀 실행 방법

### 개발 환경 설정

#### 1. 저장소 클론 및 가상환경 설정
```powershell
# Git 클론
git clone <repository-url>
cd rna-seq-data-view

# 가상환경 생성 (Python 3.8 이상 필요)
python -m venv venv

# 가상환경 활성화
# Windows PowerShell:
.\venv\Scripts\Activate.ps1

# Windows CMD:
venv\Scripts\activate.bat

# Linux/Mac:
source venv/bin/activate
```

#### 2. 의존성 설치
```powershell
# requirements.txt 기반 설치
pip install -r requirements.txt

# 또는 개별 설치
pip install PyQt6 pandas numpy openpyxl matplotlib seaborn scipy matplotlib-venn
```

#### 3. 프로그램 실행
```powershell
# src 폴더에서 실행
cd src
python main.py

# 또는 루트에서 실행
python src/main.py
```

### 테스트 실행

```powershell
# pytest 설치 (개발 의존성)
pip install pytest

# 전체 테스트 실행
python -m pytest test/ -v

# 개별 테스트 실행
python -m pytest test/test_fsm.py -v
python -m pytest test/test_models.py -v
python -m pytest test/test_statistics.py -v

# 커버리지 포함 테스트 (선택)
pip install pytest-cov
python -m pytest test/ --cov=src --cov-report=html
```

### 배포 (실행 파일 생성)

exe 파일로 배포하려면 `DEPLOYMENT.md` 문서를 참고하세요.

```powershell
# PyInstaller 설치
pip install pyinstaller

# spec 파일 기반 빌드
pyinstaller CMG-SeqViewer.spec --clean

# 빌드 결과: dist/CMG-SeqViewer.exe
```

---

## 📊 주요 클래스 및 API 레퍼런스

### **FSM (core/fsm.py)**
유한 상태 머신 구현

```python
class FSM:
    """프로그램 상태 관리 엔진"""
    
    def __init__(self, initial_state: State = State.IDLE):
        """FSM 초기화"""
        
    def trigger(self, event: Event, **kwargs) -> bool:
        """이벤트 트리거 → 상태 전환 실행
        
        Args:
            event: 트리거할 이벤트
            **kwargs: 콜백에 전달할 추가 인자
            
        Returns:
            bool: 전환 성공 여부
        """
        
    def can_trigger(self, event: Event) -> bool:
        """현재 상태에서 이벤트 트리거 가능 여부 확인"""
        
    def register_transition(self, from_state: State, event: Event, 
                          to_state: State, callback: Optional[Callable] = None):
        """상태 전환 등록"""
        
    def register_on_enter(self, state: State, callback: Callable):
        """상태 진입 시 실행할 콜백 등록"""
        
    def register_on_exit(self, state: State, callback: Callable):
        """상태 이탈 시 실행할 콜백 등록"""
        
    def add_state_change_listener(self, listener: Callable):
        """모든 상태 변경 시 호출될 리스너 등록"""
        
    def get_valid_events(self) -> List[Event]:
        """현재 상태에서 유효한 이벤트 목록 반환"""
```

### **MainPresenter (presenters/main_presenter.py)**
MVP 패턴의 Presenter, 비즈니스 로직 조정자

```python
class MainPresenter(QObject):
    """메인 Presenter - View와 Model 중재"""
    
    # Signals
    dataset_loaded = pyqtSignal(str, Dataset)
    filter_completed = pyqtSignal(pd.DataFrame, str)
    analysis_completed = pyqtSignal(dict, str)
    comparison_completed = pyqtSignal(ComparisonResult)
    error_occurred = pyqtSignal(str)
    progress_updated = pyqtSignal(int)
    
    def __init__(self, view):
        """초기화
        
        Args:
            view: MainWindow 인스턴스
        """
        
    def load_dataset(self, file_path: Path, dataset_name: Optional[str] = None,
                    custom_name: Optional[str] = None):
        """데이터셋 로드 (비동기)
        
        Args:
            file_path: 파일 경로
            dataset_name: 데이터셋 이름 (기본: 파일명)
            custom_name: 사용자 지정 이름 (선택)
        """
        
    def switch_dataset(self, dataset_name: str):
        """현재 데이터셋 전환"""
        
    def apply_filter(self, criteria: FilterCriteria):
        """필터 적용 (비동기)
        
        Args:
            criteria: FilterCriteria 객체
        """
        
    def run_fisher_test(self, gene_list: List[str]):
        """Fisher's Exact Test 실행 (비동기)
        
        Args:
            gene_list: 유전자 리스트
        """
        
    def run_gsea(self, gene_list: List[str]):
        """GSEA Lite 실행 (비동기)
        
        Args:
            gene_list: 유전자 리스트
        """
        
    def compare_datasets(self, dataset_names: List[str], 
                        gene_list: Optional[List[str]] = None,
                        operation: str = "intersection"):
        """다중 데이터셋 비교 (비동기)
        
        Args:
            dataset_names: 비교할 데이터셋 이름 리스트
            gene_list: 필터링할 유전자 리스트 (선택)
            operation: "intersection" 또는 "union"
        """
        
    def export_data(self, file_path: Path, table_widget):
        """데이터 내보내기 (비동기)
        
        Args:
            file_path: 저장 경로
            table_widget: QTableWidget 인스턴스
        """
```

### **Dataset (models/data_models.py)**
데이터셋 클래스

```python
@dataclass
class Dataset:
    """데이터셋 메인 클래스"""
    name: str
    dataset_type: DatasetType  # DIFFERENTIAL_EXPRESSION or GO_ANALYSIS
    dataframe: pd.DataFrame
    column_mapping: Dict[str, str]
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def get_filtered_data(self, **filters) -> pd.DataFrame:
        """필터링된 데이터 반환
        
        Args:
            **filters: 필터 조건
                - adj_pvalue_max: float
                - log2fc_min: float
                - regulation_direction: "up"/"down"/"both"
                - gene_list: List[str]
                - fdr_max: float (GO analysis용)
                
        Returns:
            pd.DataFrame: 필터링된 데이터
        """
        
    def get_genes(self, filters: Optional[Dict] = None) -> List[str]:
        """유전자 리스트 추출
        
        Args:
            filters: 필터 조건 (선택)
            
        Returns:
            List[str]: 유전자 심볼 리스트
        """
        
    def get_summary(self) -> Dict[str, Any]:
        """데이터셋 요약 정보
        
        Returns:
            Dict: {
                'name': str,
                'type': str,
                'rows': int,
                'columns': int,
                'gene_count': int,
                ...
            }
        """
        
    def _get_column_name(self, column_type: str) -> Optional[str]:
        """컬럼 타입에 해당하는 실제 컬럼명 반환
        
        Args:
            column_type: 'gene_id', 'log2fc', 'adj_pvalue' 등
            
        Returns:
            Optional[str]: 컬럼명 또는 None
        """
```

### **FilterCriteria (models/data_models.py)**
필터 조건 클래스

```python
@dataclass
class FilterCriteria:
    """필터 조건"""
    mode: FilterMode  # GENE_LIST or STATISTICAL
    adj_pvalue_max: float = 0.05
    log2fc_min: float = 0.0
    gene_list: Optional[List[str]] = None
    fdr_max: float = 0.05
    regulation_direction: str = "both"  # "up", "down", "both"
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환 (로깅용)"""
```

### **StatisticalAnalyzer (utils/statistics.py)**
통계 분석 엔진

```python
class StatisticalAnalyzer:
    """통계 분석 유틸리티"""
    
    def fisher_exact_test(self, gene_list: List[str], dataset: Dataset,
                         background_size: int = 20000) -> Dict[str, Any]:
        """Fisher's Exact Test (GO enrichment 분석)
        
        Args:
            gene_list: 입력 유전자 리스트
            dataset: GO analysis 데이터셋
            background_size: 전체 유전자 수 (기본: 20000)
            
        Returns:
            Dict: {
                'enriched_terms': List[Dict],  # 유의미한 GO term 리스트
                'total_terms': int,
                'significant_terms': int,
                'input_genes': int,
                'background_size': int
            }
        """
        
    def gsea_lite(self, gene_list: List[str], dataset: Dataset) -> Dict[str, Any]:
        """GSEA Lite (간소화된 Gene Set Enrichment Analysis)
        
        Args:
            gene_list: 입력 유전자 리스트
            dataset: Differential Expression 데이터셋
            
        Returns:
            Dict: {
                'up_regulated': int,  # Up-regulated 유전자 수
                'down_regulated': int,  # Down-regulated 유전자 수
                'not_significant': int,  # 유의하지 않은 유전자 수
                'direction': str,  # "up", "down", "mixed"
                'enrichment_score': float
            }
        """
        
    def compare_datasets(self, datasets: List[Dataset],
                        gene_list: Optional[List[str]] = None,
                        filters: Optional[Dict] = None) -> ComparisonResult:
        """다중 데이터셋 비교
        
        Args:
            datasets: 비교할 데이터셋 리스트
            gene_list: 필터링할 유전자 리스트 (선택)
            filters: 필터 조건 (선택)
            
        Returns:
            ComparisonResult: 비교 결과 객체
        """
```

### **DataLoader (utils/data_loader.py)**
데이터 로더

```python
class DataLoader:
    """데이터 로딩 유틸리티"""
    
    # 컬럼 매핑 패턴 (30+ 가지)
    COLUMN_MAPPINGS = {
        'gene_id': ['gene', 'gene_id', 'gene_name', 'symbol', ...],
        'log2fc': ['log2fc', 'log2foldchange', 'logfc', ...],
        'adj_pvalue': ['padj', 'adj.p.value', 'fdr', 'q_value', ...],
        ...
    }
    
    def load_data(self, file_path: Path) -> Dataset:
        """파일 로드 및 Dataset 객체 생성
        
        Args:
            file_path: Excel/CSV/TSV 파일 경로
            
        Returns:
            Dataset: 파싱된 데이터셋
            
        Raises:
            FileNotFoundError: 파일 없음
            ValueError: 지원하지 않는 형식
        """
```

## 🔍 데이터 형식 요구사항

### Differential Expression
| 필수 컬럼 | 설명 | 예시 |
|----------|------|------|
| Gene ID/Symbol | 유전자 식별자 | BRCA1, TP53 |
| log2FC | Log2 fold change | 2.5, -1.8 |
| p-value | 원본 p-value | 0.001 |
| adj.p-value | 보정 p-value | 0.01 |

### GO Analysis
| 필수 컬럼 | 설명 | 예시 |
|----------|------|------|
| Term | GO 용어 | DNA repair |
| Gene Count | 유전자 수 | 25 |
| p-value | 원본 p-value | 0.001 |
| FDR | False discovery rate | 0.01 |

## 📝 로그 예시

### Audit Log (logs/audit_YYYYMMDD.log)
```
2025-12-08 14:30:15 | INFO     | Application Started
2025-12-08 14:30:22 | INFO     | Load Dataset (file=data.xlsx, name=Experiment1)
2025-12-08 14:30:25 | INFO     | Dataset Loaded (rows=5000, type=differential_expression) [3.2s]
2025-12-08 14:31:10 | INFO     | Apply Filter (adj_pvalue_max=0.05, log2fc_min=1.0)
2025-12-08 14:31:11 | INFO     | Filtering Completed (result_count=154) [0.5s]
2025-12-08 14:32:05 | INFO     | FISHER Analysis (gene_count=25)
2025-12-08 14:32:06 | INFO     | FISHER Completed (pvalue=1.23e-05) [0.8s]
```

---

## 🎨 GUI 레이아웃 및 사용자 인터페이스

### 전체 레이아웃 구조

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  File  Analysis  Visualization  View  Help      [CMG-SeqViewer]  [Dataset ▼] │  ← 메뉴바 + 데이터셋 선택
├──────────────────────────────────────────────────────────────────────────────┤
│  📂 📊 🔍 📈 💾                                                [Add] [Remove]  │  ← 툴바
├──────────────┬───────────────────────────────────────────────────────────────┤
│              │  � Whole Dataset    [Filtered: p≤0.05 |FC|≥1] [Comparison] × │  ← 탭바
│  Filter      │  ┌──────────────────────────────────────────────────────────┐ │
│  Panel       │  │ Gene     │ log2FC │ pvalue  │ padj    │ baseMean │ ...  │ │  ← 데이터 테이블
│  ┌────────┐  │  ├──────────┼────────┼─────────┼─────────┼──────────┼──────┤ │
│  │Gene List│  │  │ BRCA1    │  2.54  │ 1.2e-05 │ 0.0012  │  145.3   │ ... │ │
│  │──────────│ │  │ TP53     │ -1.82  │ 3.4e-04 │ 0.0089  │  892.1   │ ... │ │
│  │BRCA1    │  │  │ EGFR     │  3.12  │ 8.9e-07 │ 0.0001  │  321.8   │ ... │ │
│  │TP53     │  │  │ MYC      │  1.95  │ 2.1e-04 │ 0.0045  │  654.2   │ ... │ │
│  │EGFR     │  │  │ ...      │  ...   │  ...    │  ...    │   ...    │ ... │ │
│  │         │  │  └──────────┴────────┴─────────┴─────────┴──────────┴──────┘ │
│  │         │  │                                                              │ │
│  │[Load]   │  │  Right-click: Copy, Export, Visualize                       │ │
│  └─────────┘  │  Ctrl+C: Copy selection  |  Sortable columns                │ │
│  [Clear]      │                                                              │ │
│               │                                                              │ │
│ ┌──────────┐  │                                                              │ │
│ │Statistic │  │                                                              │ │
│ │──────────│  │                                                              │ │
│ │ adj.p ≤  │  │                                                              │ │
│ │ [0.05  ] │  │                                                              │ │
│ │          │  │                                                              │ │
│ │ log2FC ≥ │  │                                                              │ │
│ │ [1.0   ] │  │                                                              │ │
│ │          │  │                                                              │ │
│ │Regulation│  │                                                              │ │
│ │ ◉ Both   │  │                                                              │ │
│ │ ○ Up     │  │                                                              │ │
│ │ ○ Down   │  │                                                              │ │
│ │          │  │                                                              │ │
│ │ FDR ≤    │  │                                                              │ │
│ │ [0.05  ] │  │                                                              │ │
│ │          │  │                                                              │ │
│ │[Apply]   │  │                                                              │ │
│ └──────────┘  │                                                              │ │
│               │                                                              │ │
│  Comparison   │                                                              │ │
│  ☑ Dataset1   │                                                              │ │
│  ☑ Dataset2   │                                                              │ │
│  ☐ Dataset3   │                                                              │ │
│  [Compare]    │                                                              │ │
│               │                                                              │ │
│  Analysis     │                                                              │ │
│  [Fisher's]   │                                                              │ │
│  [GSEA Lite]  │                                                              │ │
├───────────────┴───────────────────────────────────────────────────────────────┤
│ 📟 Terminal                                                                   │  ← 로그 터미널
│ INFO     | 14:30:25 | Dataset loaded successfully (23183 rows)               │
│ INFO     | 14:31:11 | Filtering completed: 154 genes found                   │
│ INFO     | 14:32:05 | FISHER Analysis completed (p-value: 1.23e-05)          │
└───────────────────────────────────────────────────────────────────────────────┤
│ Dataset: RNA-seq_Ben | 23183 rows × 10 columns | Ready                ⚪⚪⚪ │  ← 상태바
└───────────────────────────────────────────────────────────────────────────────┘
```

### UI 컴포넌트 상세 설명

#### 1. **상단 영역**
- **메뉴바**: File, Analysis, Visualization, View, Help
- **툴바**: 주요 기능 빠른 접근 버튼 (Open, Filter, Plot 등)
- **데이터셋 관리자**: 콤보박스 + Add/Remove 버튼

#### 2. **좌측 패널 (Filter & Analysis Panel)**
##### 필터 패널 (FilterPanel)
- **탭 1: Gene List**
  - 유전자 입력 텍스트 영역 (여러 줄)
  - Load 버튼: 텍스트 파일에서 유전자 리스트 로드
  - Clear 버튼: 입력 내용 초기화
  
- **탭 2: Statistical**
  - adj.p-value ≤ 입력 (QDoubleSpinBox, 기본값: 0.05)
  - log2FC ≥ 입력 (QDoubleSpinBox, 기본값: 1.0)
  - Regulation Direction 선택 (QRadioButton):
    - Both (기본)
    - Up-regulated
    - Down-regulated
  - FDR ≤ 입력 (GO analysis용)
  - Apply 버튼: 필터 적용

##### 비교 패널 (ComparisonPanel)
- 데이터셋 체크박스 리스트
- Operation 선택: Intersection / Union
- Compare 버튼: 비교 실행

##### 분석 패널
- Fisher's Exact Test 버튼
- GSEA Lite 버튼

#### 3. **중앙 영역 (Data View)**
- **탭 위젯**: 여러 데이터 시트 동시 관리
  - Whole Dataset 탭 (항상 존재)
  - Filtered 결과 탭들 (닫기 가능)
  - Comparison 결과 탭
  - Analysis 결과 탭

- **데이터 테이블 (QTableWidget)**
  - 정렬 가능한 컬럼 헤더
  - 숫자 컬럼: 수치 정렬 지원
  - 선택 영역 복사 (Ctrl+C)
  - 우클릭 컨텍스트 메뉴:
    - Copy Selection
    - Export to Excel/CSV
    - Create Volcano Plot
    - Create Histogram
    - Create Heatmap

#### 4. **하단 영역 (Log Terminal)**
- VS Code 스타일 터미널
- 실시간 로그 표시 (색상 구분)
  - INFO: 흰색
  - WARNING: 노란색
  - ERROR: 빨간색
- 최근 1000개 로그 유지
- 스크롤 자동 이동

#### 5. **상태바 (Status Bar)**
- 왼쪽: 현재 데이터셋 정보
- 중앙: 행/열 개수
- 오른쪽: 진행률 표시 (프로그레스 바)

### 메뉴 구조

```
File
├── Open Dataset... (Ctrl+O)
├── Open Gene List...
├── ──────────────
├── Recent Files ▶
│   ├── RNA-seq_Ben.xlsx
│   ├── Experiment_2.csv
│   └── Clear Recent
├── ──────────────
├── Export Current Tab (Ctrl+E)
│   ├── Export as Excel...
│   ├── Export as CSV...
│   └── Export as TSV...
├── ──────────────
└── Exit (Alt+F4)

Analysis
├── Filter Current Tab (Ctrl+F)
├── ──────────────
├── Fisher's Exact Test
├── GSEA Lite
├── ──────────────
└── Compare Datasets...

Visualization
├── Create Volcano Plot
├── Create P-adj Histogram
├── Create Heatmap
├── Create Dot Plot (GO)
└── Create Venn Diagram

View
├── Column Display ▶
│   ├── ◉ Basic (gene, log2FC, padj)
│   ├── ○ DE (+ baseMean, pvalue)
│   └── ○ Full (모든 컬럼)
├── ──────────────
├── Zoom In (Ctrl++)
├── Zoom Out (Ctrl+-)
├── Reset Zoom
├── ──────────────
└── Toggle Log Terminal

Help
├── Getting Started
├── User Manual
├── ──────────────
├── Keyboard Shortcuts
├── ──────────────
└── About
```

### 키보드 단축키

| 단축키 | 기능 |
|--------|------|
| `Ctrl+O` | 데이터셋 열기 |
| `Ctrl+E` | 현재 탭 내보내기 |
| `Ctrl+F` | 필터 적용 |
| `Ctrl+W` | 현재 탭 닫기 |
| `Ctrl+C` | 선택 영역 복사 |
| `Ctrl+V` | 유전자 입력란에 붙여넣기 |
| `Ctrl+A` | 전체 선택 |
| `Ctrl++` | 확대 |
| `Ctrl+-` | 축소 |
| `F1` | 도움말 |
| `F5` | 새로고침 |

---

## � 실제 사용 예시 (Use Cases)

### Use Case 1: 기본 필터링 워크플로우
```
1. 데이터셋 로드
   → File > Open Dataset > RNA-seq_Ben.xlsx 선택
   → 자동으로 컬럼 매핑 및 데이터 유효성 검사

2. Statistical 필터 적용
   → 좌측 Filter Panel > Statistical 탭
   → adj.p ≤ 0.05, log2FC ≥ 1.0 설정
   → Regulation: Up-regulated 선택
   → Apply 버튼 클릭
   → 결과: "Filtered: RNA-seq_Ben - p≤0.05, |FC|≥1.0 (Up)" 탭 생성

3. 결과 확인 및 내보내기
   → 필터링된 탭 활성화
   → File > Export as Excel
   → 파일 저장: filtered_up_genes.xlsx
```

### Use Case 2: 유전자 리스트 enrichment 분석
```
1. 관심 유전자 리스트 입력
   → 좌측 Filter Panel > Gene List 탭
   → 유전자 입력 (BRCA1, TP53, EGFR, ...)
   → 또는 Load 버튼으로 텍스트 파일 로드

2. Fisher's Exact Test 실행
   → Analysis > Fisher's Exact Test 클릭
   → GO analysis 데이터셋 선택 (팝업)
   → 결과: "Fisher's Test Result" 탭 생성
   → Enriched GO terms 테이블 표시

3. 시각화
   → 결과 탭에서 우클릭 > Create Dot Plot
   → Top 20 enriched terms 시각화
   → Export 버튼으로 PNG/SVG 저장
```

### Use Case 3: 다중 데이터셋 비교
```
1. 여러 데이터셋 로드
   → Dataset 1: Control_vs_Treatment1.xlsx
   → Dataset 2: Control_vs_Treatment2.xlsx
   → Dataset 3: Control_vs_Treatment3.xlsx

2. 비교 설정
   → 좌측 Comparison Panel
   → Dataset 1, 2, 3 체크박스 선택
   → Operation: Intersection 선택
   → Compare 버튼 클릭

3. 결과 분석
   → "Comparison Result" 탭 생성
   → 교집합 유전자 리스트 확인
   → Visualization > Create Venn Diagram
   → 3-way Venn diagram 생성
```

### Use Case 4: Cascade 필터링
```
1. 1차 필터링 (넓은 조건)
   → adj.p ≤ 0.05, log2FC ≥ 0 (Both)
   → Apply → 860개 유전자 추출

2. 필터링된 결과 탭 선택
   → "Filtered: ... - p≤0.05, |FC|≥0" 탭 활성화

3. 2차 필터링 (엄격한 조건)
   → adj.p ≤ 0.01, log2FC ≥ 1.5 (Up)
   → Apply → 45개 유전자 추출

4. 최종 결과
   → 고도로 유의미한 up-regulated 유전자만 추출
```

---

## 🔮 향후 확장 가능성

현재 구현된 아키텍처를 기반으로 다음 기능들을 쉽게 추가할 수 있습니다:

### 1. 추가 분석 기능
- **KEGG Pathway Enrichment**: Fisher's test와 유사한 구조로 구현
  ```python
  # utils/statistics.py에 메서드 추가
  def kegg_pathway_enrichment(self, gene_list, pathway_db):
      # Fisher's test와 동일한 로직
      pass
  ```

- **STRING Protein-Protein Interaction**: 네트워크 분석 추가
- **Correlation Analysis**: 유전자 간 상관관계 분석
- **Batch Effect Correction**: ComBat, limma 통합

### 2. 고급 시각화
- **Network Graph**: 유전자 네트워크 (NetworkX + Plotly)
- **PCA Plot**: 차원 축소 시각화
- **Box Plot**: 그룹별 발현량 분포
- **Time Series Plot**: 시간별 변화 추이

### 3. 데이터 처리
- **Normalization**: TPM, FPKM, DESeq2 정규화
- **Batch Processing**: 여러 파일 일괄 처리
- **Report Generation**: PDF/HTML 자동 리포트

### 4. UI 개선
- **Preferences Dialog**: 사용자 설정 저장 (JSON)
  ```python
  # config.json
  {
    "default_adj_pvalue": 0.05,
    "default_log2fc": 1.0,
    "theme": "dark",
    "font_size": 10
  }
  ```

- **Dark Theme**: PyQt6 스타일시트 적용
- **Custom Color Schemes**: 플롯 색상 프리셋
- **Plugin System**: 외부 분석 모듈 플러그인

### 5. 데이터베이스 연동
- **SQLite**: 대용량 데이터셋 캐싱
- **API Integration**: NCBI, Ensembl API 연결
- **Cloud Storage**: AWS S3, Google Drive 연동

### 구현 패턴 예시 (KEGG Pathway 추가)

```python
# 1. FSM에 상태 추가 (필요시)
# State.ANALYZING 재사용 가능

# 2. models/data_models.py에 결과 클래스 추가
@dataclass
class KEGGEnrichmentResult:
    pathway_id: str
    pathway_name: str
    gene_count: int
    pvalue: float
    fdr: float
    genes: List[str]

# 3. utils/statistics.py에 분석 메서드 추가
class StatisticalAnalyzer:
    def kegg_pathway_enrichment(self, gene_list: List[str], 
                               kegg_dataset: Dataset) -> List[KEGGEnrichmentResult]:
        """Fisher's test와 유사한 로직"""
        results = []
        for pathway in kegg_dataset.dataframe.itertuples():
            # Fisher's exact test
            odds_ratio, pvalue = fisher_exact([[a, b], [c, d]])
            results.append(KEGGEnrichmentResult(...))
        return results

# 4. presenters/main_presenter.py에 메서드 추가
class MainPresenter:
    def run_kegg_enrichment(self, gene_list: List[str]):
        self.fsm.trigger(Event.START_ANALYSIS)
        worker = AnalysisWorker('kegg', gene_list, self.current_dataset)
        worker.finished.connect(self._on_kegg_finished)
        worker.start()

# 5. gui/main_window.py에 메뉴 추가
kegg_action = QAction("KEGG Pathway", self)
kegg_action.triggered.connect(self._on_kegg_analysis)
analysis_menu.addAction(kegg_action)

def _on_kegg_analysis(self):
    gene_list = self.filter_panel.get_gene_list()
    self.presenter.run_kegg_enrichment(gene_list)
```

---

## ✨ 프로젝트 주요 특징 및 강점

### 1. **아키텍처 강점**
- ✅ **FSM 기반 상태 관리**: 복잡한 워크플로우에서도 버그 없는 안정적인 동작
- ✅ **MVP 패턴**: GUI와 로직 완전 분리로 테스트 가능하고 유지보수 용이
- ✅ **비동기 처리**: 10만 행 데이터 처리 중에도 UI 반응성 유지
- ✅ **모듈화**: 각 컴포넌트가 독립적이어서 재사용 및 확장 용이

### 2. **개발자 친화적**
- ✅ **상세한 주석**: 모든 핵심 모듈에 한글 주석 및 docstring 완비
- ✅ **타입 힌팅**: Python type hints로 코드 이해도 향상
- ✅ **명확한 네이밍**: 변수/함수명이 의도를 명확히 표현
- ✅ **예제 코드**: `examples/usage_examples.py`로 API 사용법 제시

### 3. **사용자 친화적**
- ✅ **Excel 스타일 UI**: 생물학 연구자들에게 친숙한 인터페이스
- ✅ **실시간 피드백**: 모든 작업이 로그 터미널에 즉시 표시
- ✅ **Drag & Drop**: 파일을 끌어다 놓기만 하면 자동 로드
- ✅ **도움말 시스템**: 8개 섹션 상세 HTML 도움말 내장

### 4. **전문성 및 신뢰성**
- ✅ **통계 검증**: Fisher's test, GSEA 등 검증된 분석 기법
- ✅ **데이터 유효성 검사**: 로드 시 자동으로 필수 컬럼 확인
- ✅ **에러 핸들링**: 모든 예외 상황을 사용자에게 명확히 전달
- ✅ **Audit Logging**: 모든 사용자 활동 기록으로 재현 가능

### 5. **확장성**
- ✅ **플러그인 구조**: 새 분석/시각화 추가가 명확한 패턴 존재
- ✅ **설정 파일**: requirements.txt, setup.py로 배포 준비 완료
- ✅ **배포 가이드**: DEPLOYMENT.md로 exe 생성 방법 상세 문서화

### 6. **성능 최적화**
- ✅ **Pandas 활용**: 대용량 데이터 처리에 최적화된 라이브러리 사용
- ✅ **Lazy Loading**: 필요한 시점에만 데이터 로드
- ✅ **캐싱**: 자주 사용되는 연산 결과 메모리 캐시
- ✅ **Progress Bar**: 진행 상황을 실시간으로 표시

---

## � 참고 문서

### 프로젝트 문서
- `README.md`: 프로젝트 소개 및 빠른 시작 가이드
- `PROJECT_SUMMARY.md` (이 문서): 포괄적인 아키텍처 및 구현 설명
- `DEPLOYMENT.md`: Windows exe 배포 가이드
- `docs/FSM_DIAGRAM.md`: FSM 상태 다이어그램

### 코드 문서
- 각 모듈의 docstring 참조
- `examples/usage_examples.py`: API 사용 예제
- 단위 테스트 코드: `test/` 폴더

---

## 🎓 다른 프로젝트 적용 시 참고사항

이 프로젝트의 아키텍처 패턴을 다른 프로젝트에 적용할 때 고려사항:

### 1. FSM 적용이 유용한 경우
- ✅ 여러 단계의 워크플로우가 있는 애플리케이션
- ✅ 상태에 따라 UI 동작이 달라져야 하는 경우
- ✅ 비동기 작업이 많아 순서 제어가 필요한 경우
- ❌ 단순한 CRUD 애플리케이션 (오버엔지니어링)

### 2. MVP 패턴 적용이 유용한 경우
- ✅ GUI와 비즈니스 로직의 명확한 분리가 필요한 경우
- ✅ 단위 테스트를 작성해야 하는 경우
- ✅ 여러 플랫폼(Desktop, Web, Mobile)으로 확장 가능성이 있는 경우
- ❌ 매우 작은 규모의 프로토타입 (MVC로 충분)

### 3. QThread Worker 적용이 유용한 경우
- ✅ 1초 이상 걸리는 작업이 있는 경우
- ✅ 파일 I/O, 네트워크 요청이 많은 경우
- ✅ 대용량 데이터 처리가 필요한 경우
- ❌ 모든 작업이 0.1초 이내로 끝나는 경우

### 4. 이 프로젝트에서 재사용 가능한 컴포넌트
- `core/fsm.py`: 범용 FSM 구현 (어떤 프로젝트에서도 사용 가능)
- `core/logger.py`: Qt GUI 로거 및 Audit Logger
- `gui/workers.py`: QThread Worker 패턴 예제
- 테스트 코드 구조

---

## 🏁 요약

**CMG-SeqViewer**는 RNA-Seq 데이터 분석을 위한 완성도 높은 데스크톱 애플리케이션입니다.

### 핵심 성과
- ✅ **12개 상태, 18개 이벤트** FSM으로 견고한 상태 관리
- ✅ **MVP 패턴**으로 GUI와 로직 완전 분리
- ✅ **5가지 비동기 Worker**로 반응성 있는 UI
- ✅ **10+ 가지 분석 및 시각화 기능** 구현
- ✅ **1988줄 메인 윈도우**, **670줄 Presenter** 등 대규모 코드베이스
- ✅ **33개 테스트 케이스**로 코드 품질 보장

### 학습 포인트
이 프로젝트에서 배울 수 있는 것:
1. **FSM 기반 상태 관리**: 복잡한 애플리케이션 상태 제어 방법
2. **MVP 아키텍처**: GUI 애플리케이션 설계 패턴
3. **비동기 프로그래밍**: QThread를 활용한 반응성 있는 UI 구현
4. **PyQt6 GUI 개발**: 전문적인 데스크톱 애플리케이션 개발
5. **데이터 분석 파이프라인**: Pandas 기반 데이터 처리 및 통계 분석
6. **테스트 주도 개발**: 단위 테스트 작성 및 관리

---

**프로젝트 완료 일자**: 2025년 12월 13일  
**버전**: 1.0.0  
**개발 상태**: Production Ready ✅  
**라이센스**: MIT (선택 가능)

---

📧 **문의사항이 있으시면 GitHub Issues를 통해 연락주세요.**
