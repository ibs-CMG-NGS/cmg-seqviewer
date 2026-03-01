# CMG-SeqViewer 아키텍처 가이드 (Architecture Guide)

> 🏗️ CMG-SeqViewer의 설계 원칙, 패턴, 내부 구조를 설명하는 개발자 문서

## 목차

1. [개요](#개요)
2. [아키텍처 패턴](#아키텍처-패턴)
3. [디렉토리 구조](#디렉토리-구조)
4. [핵심 컴포넌트](#핵심-컴포넌트)
5. [데이터 흐름](#데이터-흐름)
6. [상태 관리](#상태-관리)
7. [비동기 처리](#비동기-처리)
8. [확장 가이드](#확장-가이드)

---

## 개요

### 설계 목표

CMG-SeqViewer는 다음 원칙을 따라 설계되었습니다:

**1. 관심사의 분리 (Separation of Concerns)**
- GUI 로직과 비즈니스 로직 분리
- 데이터 모델과 프레젠테이션 분리

**2. 확장성 (Extensibility)**
- 새로운 시각화 추가 용이
- 플러그인 아키텍처 (계획)

**3. 유지보수성 (Maintainability)**
- 명확한 디렉토리 구조
- 문서화된 인터페이스

**4. 성능 (Performance)**
- 비동기 데이터 로딩
- 백그라운드 스레드 처리
- 메모리 효율적 데이터 구조

### 기술 스택

**GUI Framework**:
- **PyQt6**: 크로스플랫폼 GUI
- **Qt Widgets**: 전통적인 데스크톱 UI

**데이터 처리**:
- **pandas**: 데이터프레임 조작
- **NumPy**: 수치 계산

**시각화**:
- **matplotlib**: 기본 플롯
- **seaborn**: 통계 플롯
- **networkx**: 네트워크 시각화

**파일 I/O**:
- **openpyxl**: Excel 읽기/쓰기
- **pyarrow**: Parquet 포맷 (데이터베이스)

**통계**:
- **scipy**: 통계 테스트
- **scikit-learn**: 클러스터링

---

## 아키텍처 패턴

### 1. MVP (Model-View-Presenter)

CMG-SeqViewer는 **MVP 패턴**을 기반으로 합니다.

```
┌─────────────────────────────────────────────┐
│                   View                      │
│  (GUI 컴포넌트 - PyQt6 Widgets)              │
│  - main_window.py                           │
│  - filter_panel.py                          │
│  - visualization_dialog.py                  │
└─────────────┬───────────────────────────────┘
              │ Events (signals)
              ↓
┌─────────────────────────────────────────────┐
│                 Presenter                   │
│  (비즈니스 로직 조율)                         │
│  - main_presenter.py                        │
│  - filter_presenter.py                      │
└─────────────┬───────────────────────────────┘
              │ Commands
              ↓
┌─────────────────────────────────────────────┐
│                  Model                      │
│  (데이터 및 비즈니스 로직)                    │
│  - dataset_model.py                         │
│  - filter_model.py                          │
└─────────────────────────────────────────────┘
```

**각 레이어의 책임**:

**View** (GUI 레이어):
- 사용자 인터페이스 렌더링
- 사용자 입력 수집
- PyQt6 signals 발생
- Presenter에 의존하지 않음 (loose coupling)

**Presenter** (중재자):
- View의 이벤트 처리
- Model 업데이트 호출
- View 업데이트 지시
- 비즈니스 로직 조율

**Model** (데이터 및 로직):
- 데이터 저장 및 관리
- 비즈니스 로직 구현
- 상태 변경 알림 (signals)
- View/Presenter 모름 (완전 독립)

**장점**:
- 단위 테스트 용이 (각 레이어 독립 테스트)
- GUI 변경 시 Model 영향 없음
- 여러 View가 같은 Model 공유 가능

### 2. FSM (Finite State Machine)

애플리케이션의 주요 상태 전환은 **FSM**으로 관리합니다.

**상태 정의** (`src/core/fsm.py`):

```python
from enum import Enum

class AppState(Enum):
    IDLE = "idle"                  # 데이터 없음
    DATA_LOADED = "data_loaded"    # 데이터 로드됨
    FILTERING = "filtering"        # 필터링 중
    FILTERED = "filtered"          # 필터 적용됨
    VISUALIZING = "visualizing"    # 시각화 생성 중
    COMPARING = "comparing"        # 데이터셋 비교 중
    ERROR = "error"                # 오류 상태
```

**전환 다이어그램**:

```
         ┌─────┐
    ┌───→│IDLE │←───┐
    │    └──┬──┘    │
    │       │ Import│ Clear All
    │       ↓       │
    │  ┌─────────┐  │
    │  │  DATA   │──┘
    │  │ LOADED  │
    │  └────┬────┘
    │       │ Apply Filter
    │       ↓
    │  ┌─────────┐
    │  │FILTERING│
    │  └────┬────┘
    │       │ Complete
    │       ↓
    │  ┌─────────┐
    └──│FILTERED │
       └────┬────┘
            │ Visualize
            ↓
       ┌─────────┐
       │VISUALIZE│
       └─────────┘
```

**구현** (`src/core/fsm.py`):

```python
class AppStateMachine:
    def __init__(self):
        self.state = AppState.IDLE
        self.transitions = {
            AppState.IDLE: [AppState.DATA_LOADED, AppState.ERROR],
            AppState.DATA_LOADED: [AppState.FILTERING, AppState.COMPARING, AppState.IDLE],
            AppState.FILTERING: [AppState.FILTERED, AppState.ERROR],
            AppState.FILTERED: [AppState.VISUALIZING, AppState.FILTERING, AppState.DATA_LOADED],
            # ... 등
        }
    
    def transition_to(self, new_state: AppState) -> bool:
        """상태 전환 시도"""
        if new_state in self.transitions.get(self.state, []):
            old_state = self.state
            self.state = new_state
            self.on_state_change(old_state, new_state)
            return True
        else:
            logger.warning(f"Invalid transition: {self.state} -> {new_state}")
            return False
    
    def on_state_change(self, old: AppState, new: AppState):
        """상태 변경 시 이벤트"""
        logger.info(f"State transition: {old.value} -> {new.value}")
        # GUI 업데이트, 로그 기록 등
```

**사용 예시**:

```python
# Presenter에서
def import_dataset(self, file_path: str):
    if self.fsm.transition_to(AppState.DATA_LOADED):
        # 데이터 로드 로직
        self.model.load_data(file_path)
        self.view.update_ui()
    else:
        # 전환 실패 (현재 상태에서 불가능)
        self.view.show_error("Cannot load data in current state")
```

**장점**:
- 유효하지 않은 상태 전환 방지
- 디버깅 용이 (상태 로그)
- 복잡한 워크플로우 명확화

### 3. Observer Pattern

**상황**: Model 변경 시 여러 View 업데이트

**구현**: PyQt6 signals/slots

```python
# Model
class DatasetModel(QObject):
    data_changed = pyqtSignal()  # Signal 정의
    
    def set_data(self, df: pd.DataFrame):
        self._data = df
        self.data_changed.emit()  # 변경 알림

# View
class DataTable(QTableView):
    def __init__(self, model: DatasetModel):
        super().__init__()
        model.data_changed.connect(self.refresh_table)  # 구독
    
    def refresh_table(self):
        # 테이블 업데이트
        pass
```

### 4. Factory Pattern

**상황**: 시각화 객체 생성

**구현**:

```python
class VisualizationFactory:
    @staticmethod
    def create(viz_type: str, data: pd.DataFrame, **kwargs):
        if viz_type == "volcano":
            return VolcanoPlot(data, **kwargs)
        elif viz_type == "heatmap":
            return Heatmap(data, **kwargs)
        elif viz_type == "network":
            return NetworkVisualization(data, **kwargs)
        else:
            raise ValueError(f"Unknown visualization type: {viz_type}")
```

**장점**:
- 객체 생성 로직 중앙화
- 새 시각화 타입 추가 용이

---

## 디렉토리 구조

### 전체 구조

```
src/
├── __init__.py
├── main.py                # 진입점
├── core/                  # 핵심 인프라
│   ├── __init__.py
│   ├── fsm.py             # Finite State Machine
│   └── logger.py          # 로깅 시스템
├── models/                # 데이터 모델 (MVP - Model)
│   ├── __init__.py
│   ├── dataset_model.py   # 데이터셋 관리
│   ├── filter_model.py    # 필터링 로직
│   └── statistics_model.py # 통계 분석
├── presenters/            # 프레젠터 (MVP - Presenter)
│   ├── __init__.py
│   ├── main_presenter.py  # 메인 로직
│   └── filter_presenter.py
├── gui/                   # GUI 컴포넌트 (MVP - View)
│   ├── __init__.py
│   ├── main_window.py     # 메인 윈도우
│   ├── filter_panel.py    # 필터 패널
│   ├── visualization_dialog.py
│   ├── go_clustering_dialog.py
│   └── workers.py         # QThread workers
├── utils/                 # 유틸리티
│   ├── __init__.py
│   ├── file_io.py         # 파일 I/O
│   ├── statistics.py      # 통계 함수
│   └── validators.py      # 입력 검증
└── workers/               # 백그라운드 작업 (Deprecated - gui/workers.py 사용)
```

### 레이어별 역할

**core/**: 애플리케이션 전체에서 사용하는 핵심 인프라
- FSM: 상태 관리
- Logger: 로깅 시스템 (파일 + 터미널)

**models/**: 순수 Python 데이터 모델 및 비즈니스 로직
- GUI 의존성 없음
- 단위 테스트 가능
- pandas DataFrame 기반

**presenters/**: View와 Model 연결
- PyQt6 signals/slots 사용
- 비동기 작업 조율
- FSM 상태 관리

**gui/**: PyQt6 GUI 컴포넌트
- QMainWindow, QWidget, QDialog 등
- 사용자 입력 처리
- signals 발생

**utils/**: 재사용 가능한 유틸리티 함수
- 파일 I/O (Excel, Parquet)
- 통계 계산 (Fisher, GSEA)
- 데이터 검증

**workers/**: 백그라운드 스레드 작업 (Deprecated)
- 현재는 `gui/workers.py` 사용
- QThread 기반
- 긴 작업 비동기 처리

---

## 핵심 컴포넌트

### 1. DatasetModel

**위치**: `src/models/dataset_model.py`

**역할**: 데이터셋 저장 및 관리

**주요 속성**:
```python
class DatasetModel:
    def __init__(self):
        self.name: str = ""
        self.data: pd.DataFrame = None
        self.data_type: str = "DE"  # "DE" or "GO_KEGG"
        self.metadata: dict = {}
```

**주요 메서드**:
```python
def load_from_excel(self, file_path: str, sheet_name: str, column_mapping: dict):
    """Excel에서 데이터 로드"""
    
def apply_filter(self, adj_p: float, log2fc: float, direction: str) -> pd.DataFrame:
    """필터 적용 (새 DataFrame 반환)"""
    
def get_filtered_data(self) -> pd.DataFrame:
    """필터링된 데이터 반환"""
    
def export_to_excel(self, file_path: str, df: pd.DataFrame = None):
    """Excel로 내보내기"""
```

**Signals**:
```python
data_changed = pyqtSignal()      # 데이터 변경됨
filter_applied = pyqtSignal()    # 필터 적용됨
```

### 2. MainPresenter

**위치**: `src/presenters/main_presenter.py`

**역할**: 메인 애플리케이션 로직 조율

**초기화**:
```python
class MainPresenter:
    def __init__(self, view: MainWindow):
        self.view = view
        self.datasets: Dict[str, DatasetModel] = {}
        self.fsm = AppStateMachine()
        self._connect_signals()
```

**주요 메서드**:
```python
def import_dataset(self, file_path: str, settings: dict):
    """데이터셋 임포트"""
    
def apply_filter(self, dataset_name: str, filters: dict):
    """필터 적용"""
    
def create_visualization(self, viz_type: str, dataset_name: str, **kwargs):
    """시각화 생성"""
    
def compare_datasets(self, dataset_names: List[str], mode: str):
    """데이터셋 비교"""
```

### 3. MainWindow

**위치**: `src/gui/main_window.py`

**역할**: 메인 GUI 윈도우

**구성**:
```python
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self._init_ui()
        self._create_menu_bar()
        self._create_central_widget()
        self._create_dock_widgets()
    
    def _init_ui(self):
        """UI 초기화"""
        self.setWindowTitle("CMG-SeqViewer")
        self.setGeometry(100, 100, 1400, 800)
    
    def _create_menu_bar(self):
        """메뉴바 생성"""
        file_menu = self.menuBar().addMenu("File")
        # Import, Export, Exit 등
    
    def _create_central_widget(self):
        """중앙 위젯 (탭 인터페이스)"""
        self.tab_widget = QTabWidget()
        self.setCentralWidget(self.tab_widget)
    
    def _create_dock_widgets(self):
        """도크 위젯 (Filter Panel, Dataset Manager)"""
        self.filter_dock = FilterPanel()
        self.addDockWidget(Qt.LeftDockWidgetArea, self.filter_dock)
```

**Signals**:
```python
import_requested = pyqtSignal(str)           # 임포트 요청
filter_requested = pyqtSignal(dict)          # 필터 요청
visualization_requested = pyqtSignal(str, dict)  # 시각화 요청
```

### 4. Workers (비동기 처리)

**위치**: `src/gui/workers.py`

**목적**: UI 블로킹 방지

**Base Worker**:
```python
class BaseWorker(QThread):
    finished = pyqtSignal(object)  # 결과
    error = pyqtSignal(str)        # 에러
    progress = pyqtSignal(int)     # 진행률
    
    def __init__(self, func, *args, **kwargs):
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs
    
    def run(self):
        try:
            result = self.func(*self.args, **self.kwargs)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))
```

**특수 Workers**:

**DataLoadWorker**: Excel 파일 로드
```python
class DataLoadWorker(BaseWorker):
    def run(self):
        try:
            df = pd.read_excel(self.file_path, sheet_name=self.sheet)
            self.progress.emit(50)
            # 컬럼 매핑
            df_mapped = self.map_columns(df, self.mapping)
            self.progress.emit(100)
            self.finished.emit(df_mapped)
        except Exception as e:
            self.error.emit(str(e))
```

**ClusteringWorker**: GO/KEGG 클러스터링
```python
class ClusteringWorker(BaseWorker):
    def run(self):
        try:
            from scipy.cluster.hierarchy import linkage, fcluster
            
            # Similarity matrix 계산
            similarity = self.calculate_similarity(self.data)
            self.progress.emit(30)
            
            # Clustering
            Z = linkage(similarity, method=self.linkage_method)
            self.progress.emit(70)
            
            clusters = fcluster(Z, self.threshold, criterion='distance')
            self.progress.emit(100)
            
            self.finished.emit(clusters)
        except Exception as e:
            self.error.emit(str(e))
```

**사용 예시**:
```python
# Presenter에서
def load_data_async(self, file_path: str):
    self.worker = DataLoadWorker(file_path, sheet=0)
    self.worker.progress.connect(self.view.update_progress)
    self.worker.finished.connect(self.on_data_loaded)
    self.worker.error.connect(self.on_error)
    self.worker.start()

def on_data_loaded(self, df: pd.DataFrame):
    self.model.set_data(df)
    self.view.show_success("Data loaded successfully")
```

---

## 데이터 흐름

### Import 워크플로우

```
사용자: File → Import Dataset
    ↓
MainWindow: import_requested signal 발생
    ↓
MainPresenter: import_dataset() 호출
    ↓
DatasetImportDialog: 설정 입력 (이름, 타입, 컬럼 매핑)
    ↓
MainPresenter: DataLoadWorker 시작
    ↓
DataLoadWorker: 백그라운드에서 Excel 로드
    ↓ (finished signal)
MainPresenter: 데이터 수신
    ↓
DatasetModel: 새 모델 생성 및 저장
    ↓
MainPresenter: FSM 상태 → DATA_LOADED
    ↓
MainWindow: 새 탭 생성, 데이터 테이블 표시
```

### Filter 워크플로우

```
사용자: Filter Panel 설정 → Apply Filter
    ↓
FilterPanel: filter_requested signal
    ↓
MainPresenter: apply_filter() 호출
    ↓
FilterPresenter: 필터 검증
    ↓
MainPresenter: FSM 상태 → FILTERING
    ↓
DatasetModel: apply_filter() 실행
    ↓ (결과 DataFrame 반환)
MainPresenter: 새 탭 생성 ("Dataset:Filtered")
    ↓
MainPresenter: FSM 상태 → FILTERED
    ↓
MainWindow: 필터링된 데이터 표시
```

### Visualization 워크플로우

```
사용자: Visualization → Volcano Plot
    ↓
MainWindow: visualization_requested signal
    ↓
MainPresenter: create_visualization() 호출
    ↓
MainPresenter: FSM 상태 → VISUALIZING
    ↓
VisualizationDialog: 설정 입력 (크기, 색상 등)
    ↓
MainPresenter: VisualizationWorker 시작 (선택사항)
    ↓
VisualizationWorker: matplotlib Figure 생성
    ↓ (finished signal)
MainPresenter: Figure 수신
    ↓
새 Window: Figure 표시 (plt.show())
    ↓
MainPresenter: FSM 상태 → DATA_LOADED (복귀)
```

---

## 상태 관리

### FSM 상태 상세

**IDLE**:
- 조건: 데이터셋 없음
- 가능한 작업: Import Dataset
- 불가능: Filter, Visualize, Compare

**DATA_LOADED**:
- 조건: 1개 이상 데이터셋 로드
- 가능한 작업: Filter, Visualize, Compare, Import (추가)
- 불가능: (없음)

**FILTERING**:
- 조건: 필터링 진행 중
- 가능한 작업: (대기)
- 불가능: 모든 사용자 입력 (진행 중)

**FILTERED**:
- 조건: 필터링 완료
- 가능한 작업: Visualize, Re-filter, Export
- 불가능: (없음)

**VISUALIZING**:
- 조건: 시각화 생성 중
- 가능한 작업: (대기)
- 불가능: 다른 시각화 동시 생성 (선택사항)

**COMPARING**:
- 조건: 다중 데이터셋 비교 중
- 가능한 작업: (대기)
- 불가능: 새 데이터셋 Import

**ERROR**:
- 조건: 오류 발생
- 가능한 작업: 이전 상태로 복귀, Clear
- 불가능: (상황에 따라 다름)

### 상태 전환 로직

**전환 가능성 체크**:
```python
def can_apply_filter(self) -> bool:
    return self.fsm.state in [AppState.DATA_LOADED, AppState.FILTERED]

def can_visualize(self) -> bool:
    return self.fsm.state in [AppState.DATA_LOADED, AppState.FILTERED]
```

**사용자 작업 검증**:
```python
def on_filter_button_clicked(self):
    if self.presenter.can_apply_filter():
        self.presenter.apply_filter(self.get_filter_settings())
    else:
        QMessageBox.warning(self, "Warning", "Cannot apply filter in current state")
```

---

## 비동기 처리

### QThread 기반 비동기

**목적**: UI 블로킹 방지

**사용 시나리오**:
- Excel 파일 로드 (대용량)
- GO/KEGG 클러스터링 (계산 집약적)
- 대규모 데이터 필터링
- 네트워크 시각화 레이아웃 계산

**구현 패턴**:

```python
class MyWorker(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal(object)
    error = pyqtSignal(str)
    
    def __init__(self, data, params):
        super().__init__()
        self.data = data
        self.params = params
    
    def run(self):
        try:
            # 단계 1
            result_1 = self.step_1()
            self.progress.emit(33)
            
            # 단계 2
            result_2 = self.step_2(result_1)
            self.progress.emit(66)
            
            # 단계 3
            final_result = self.step_3(result_2)
            self.progress.emit(100)
            
            self.finished.emit(final_result)
        except Exception as e:
            logger.exception("Worker error")
            self.error.emit(str(e))
```

**Presenter에서 사용**:

```python
def run_clustering(self, data, settings):
    # Progress dialog
    self.progress_dialog = QProgressDialog("Clustering...", "Cancel", 0, 100, self.view)
    self.progress_dialog.setWindowModality(Qt.WindowModal)
    
    # Worker 시작
    self.worker = ClusteringWorker(data, settings)
    self.worker.progress.connect(self.progress_dialog.setValue)
    self.worker.finished.connect(self.on_clustering_finished)
    self.worker.error.connect(self.on_clustering_error)
    self.worker.start()

def on_clustering_finished(self, result):
    self.progress_dialog.close()
    self.model.set_clusters(result)
    self.view.update_table()
    QMessageBox.information(self.view, "Success", "Clustering completed")

def on_clustering_error(self, error_msg):
    self.progress_dialog.close()
    QMessageBox.critical(self.view, "Error", f"Clustering failed: {error_msg}")
```

### 취소 기능 (선택사항)

**구현**:
```python
class CancellableWorker(QThread):
    def __init__(self):
        super().__init__()
        self._is_cancelled = False
    
    def cancel(self):
        self._is_cancelled = True
    
    def run(self):
        for i in range(100):
            if self._is_cancelled:
                logger.info("Worker cancelled")
                return
            # 작업 수행
            time.sleep(0.1)
            self.progress.emit(i)

# Dialog에서
def on_cancel_clicked(self):
    self.worker.cancel()
    self.worker.wait()  # 종료 대기
```

---

## 확장 가이드

### 1. 새 시각화 추가

**단계**:

**1) Visualization 클래스 작성** (`src/gui/my_visualization_dialog.py`):
```python
from PyQt6.QtWidgets import QDialog
import matplotlib.pyplot as plt

class MyVisualizationDialog(QDialog):
    def __init__(self, data: pd.DataFrame, parent=None):
        super().__init__(parent)
        self.data = data
        self._init_ui()
    
    def _init_ui(self):
        # 설정 UI (QFormLayout 등)
        pass
    
    def generate(self):
        # matplotlib Figure 생성
        fig, ax = plt.subplots(figsize=(10, 6))
        # 플롯 로직
        plt.show()
```

**2) MainWindow 메뉴에 추가**:
```python
# main_window.py
def _create_visualization_menu(self):
    viz_menu = self.menuBar().addMenu("Visualization")
    
    # 기존: Volcano, Heatmap 등
    
    # 새 시각화
    my_viz_action = QAction("My Visualization", self)
    my_viz_action.triggered.connect(self.on_my_viz_requested)
    viz_menu.addAction(my_viz_action)

def on_my_viz_requested(self):
    self.visualization_requested.emit("my_viz", {})
```

**3) Presenter에서 처리**:
```python
# main_presenter.py
def create_visualization(self, viz_type: str, settings: dict):
    if viz_type == "my_viz":
        self._create_my_viz(settings)
    # ... 기존 코드

def _create_my_viz(self, settings: dict):
    data = self.get_current_data()
    dialog = MyVisualizationDialog(data, parent=self.view)
    dialog.exec()
```

### 2. 새 필터 타입 추가

**예시**: Gene Annotation 필터

**1) FilterModel 확장**:
```python
# filter_model.py
def apply_annotation_filter(self, df: pd.DataFrame, annotation: str) -> pd.DataFrame:
    """Gene annotation 기반 필터"""
    if "annotation" not in df.columns:
        return df
    return df[df["annotation"].str.contains(annotation, case=False, na=False)]
```

**2) FilterPanel UI 추가**:
```python
# filter_panel.py
def _init_ui(self):
    # 기존 필터 UI
    
    # Annotation 필터
    annotation_label = QLabel("Annotation:")
    self.annotation_input = QLineEdit()
    self.annotation_input.setPlaceholderText("e.g., kinase, receptor")
    layout.addRow(annotation_label, self.annotation_input)
```

**3) Presenter에서 적용**:
```python
# filter_presenter.py
def apply_filter(self, settings: dict):
    df = self.model.data.copy()
    
    # 기존 필터 적용
    df = self.model.apply_pvalue_filter(df, settings["adj_p"])
    df = self.model.apply_fc_filter(df, settings["log2fc"])
    
    # 새 필터
    if settings.get("annotation"):
        df = self.model.apply_annotation_filter(df, settings["annotation"])
    
    return df
```

### 3. 새 통계 분석 추가

**예시**: Hypergeometric Test

**1) Statistics 함수 작성** (`src/utils/statistics.py`):
```python
from scipy.stats import hypergeom

def hypergeometric_test(gene_list: List[str], gene_set: List[str], background: List[str]) -> float:
    """
    Hypergeometric test for gene set enrichment
    
    Parameters:
    - gene_list: 관심 유전자 리스트
    - gene_set: Gene set (pathway 등)
    - background: 전체 유전자 우주
    
    Returns:
    - p-value
    """
    M = len(background)  # 전체
    n = len(gene_set)    # Gene set 크기
    N = len(gene_list)   # 샘플 크기
    k = len(set(gene_list) & set(gene_set))  # 겹침
    
    p_value = hypergeom.sf(k - 1, M, n, N)
    return p_value
```

**2) Analysis 메뉴에 추가**:
```python
# main_window.py
analysis_menu = self.menuBar().addMenu("Analysis")
hyper_action = QAction("Hypergeometric Test", self)
hyper_action.triggered.connect(self.on_hyper_test_requested)
analysis_menu.addAction(hyper_action)
```

**3) Dialog 작성**:
```python
# hypergeometric_dialog.py
class HypergeometricDialog(QDialog):
    def __init__(self, datasets: Dict[str, DatasetModel], parent=None):
        super().__init__(parent)
        self.datasets = datasets
        # UI: Gene list 입력, Gene set 선택, Background 선택
    
    def run_test(self):
        gene_list = self.get_gene_list()
        gene_set = self.get_gene_set()
        background = self.get_background()
        
        p_value = hypergeometric_test(gene_list, gene_set, background)
        
        # 결과 표시
        self.result_label.setText(f"P-value: {p_value:.4e}")
```

### 4. 플러그인 시스템 (계획 - v2.1.0+)

**목표**: 사용자 정의 Python 스크립트 실행

**아키텍처**:

```
plugins/
├── my_analysis.py
├── custom_viz.py
└── __init__.py
```

**Plugin API**:
```python
# plugins/my_analysis.py
from cmg_seqviewer.plugin import Plugin

class MyAnalysisPlugin(Plugin):
    name = "My Custom Analysis"
    version = "1.0.0"
    
    def run(self, data: pd.DataFrame, params: dict) -> pd.DataFrame:
        # 사용자 정의 분석
        result = ...
        return result
    
    def get_params_dialog(self):
        # 파라미터 입력 Dialog 반환
        return MyParamsDialog()
```

**Plugin Manager**:
```python
class PluginManager:
    def __init__(self):
        self.plugins = []
    
    def load_plugins(self, plugin_dir: str):
        # plugin_dir에서 모든 .py 파일 로드
        # Plugin 클래스 인스턴스화
        pass
    
    def get_plugin(self, name: str) -> Plugin:
        # 이름으로 플러그인 검색
        pass
    
    def run_plugin(self, name: str, data: pd.DataFrame, params: dict):
        plugin = self.get_plugin(name)
        return plugin.run(data, params)
```

---

## 참고 문서

- [MVP 패턴 상세](https://en.wikipedia.org/wiki/Model%E2%80%93view%E2%80%93presenter)
- [PyQt6 공식 문서](https://www.riverbankcomputing.com/static/Docs/PyQt6/)
- [FSM 패턴](https://en.wikipedia.org/wiki/Finite-state_machine)
- [Observer 패턴](https://en.wikipedia.org/wiki/Observer_pattern)

---

**마지막 업데이트**: 2026-03-01  
**버전**: v1.2.0
