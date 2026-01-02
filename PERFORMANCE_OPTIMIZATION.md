# Performance Optimization Guide

## 현재 리소스 사용 분석

### 메모리 사용
- **DataFrame 중복 저장**: `tab_data` 딕셔너리에 모든 탭의 DataFrame을 저장
- **QTableWidget**: 모든 데이터를 메모리에 로드하여 표시
- **Matplotlib Figures**: 각 다이얼로그마다 Figure 객체 유지

### CPU 사용
- **정렬 기능**: 대규모 데이터셋에서 실시간 정렬 시 부하
- **Plot 렌더링**: Matplotlib 렌더링이 CPU 집약적
- **Hover 이벤트**: 마우스 이동 시마다 거리 계산

## 권장 최적화 방안

### 1. 메모리 최적화 (우선순위: 높음)

#### A. LazyTableModel 구현
```python
# 현재: 모든 데이터를 QTableWidgetItem으로 변환
# 문제: 100,000행 × 20열 = 2,000,000개 QTableWidgetItem 생성

# 권장: QAbstractTableModel 사용
class LazyDataFrameModel(QAbstractTableModel):
    """DataFrame을 직접 참조하여 필요할 때만 데이터 제공"""
    def __init__(self, dataframe):
        super().__init__()
        self._data = dataframe
    
    def data(self, index, role):
        # 화면에 보이는 셀만 렌더링
        if role == Qt.DisplayRole:
            return str(self._data.iloc[index.row(), index.column()])
```

**효과**: 메모리 사용량 70-80% 감소

#### B. DataFrame 참조 방식 변경
```python
# 현재: 각 탭마다 DataFrame 복사본 저장
self.tab_data[index] = (dataframe.copy(), dataset)

# 권장: Dataset 객체에서 참조
self.tab_data[index] = (dataset.name, 'whole')  # 참조만 저장
# 필요 시 dataset.data에서 가져오기
```

**효과**: 대규모 데이터셋에서 메모리 50% 절감

#### C. Plot Figure 재사용
```python
# 현재: 각 다이얼로그마다 새 Figure 생성
class VolcanoPlotDialog(QDialog):
    def __init__(self, ...):
        self.figure = Figure()  # 매번 새로 생성

# 권장: Figure 캐싱 및 재사용
class PlotCache:
    _figures = {}
    
    @classmethod
    def get_figure(cls, plot_type, size):
        key = f"{plot_type}_{size[0]}x{size[1]}"
        if key not in cls._figures:
            cls._figures[key] = Figure(figsize=size)
        return cls._figures[key]
```

**효과**: 메모리 사용량 안정화

### 2. CPU 최적화 (우선순위: 중간)

#### A. 정렬 최적화
```python
# 현재: setSortingEnabled(True) - 모든 정렬을 즉시 수행

# 권장: 대규모 데이터는 정렬 비활성화 또는 지연 처리
if len(dataframe) > 10000:
    table.setSortingEnabled(False)
    # "Sort" 버튼 제공 - 사용자가 원할 때만 정렬
```

**효과**: 초기 로딩 속도 50% 향상

#### B. Hover 이벤트 Throttling
```python
# 현재: 모든 마우스 이동마다 _on_hover 호출

# 권장: Throttling 추가
class ThrottledHoverHandler:
    def __init__(self, interval_ms=50):
        self.timer = QTimer()
        self.timer.setSingleShot(True)
        self.timer.setInterval(interval_ms)
        self.pending_event = None
    
    def on_hover(self, event):
        if not self.timer.isActive():
            self._process_event(event)
            self.timer.start()
        else:
            self.pending_event = event
```

**효과**: CPU 사용률 30-40% 감소

#### C. 비동기 데이터 로딩
```python
# 현재: 메인 스레드에서 모든 파일 읽기

# 권장: QThread 사용
class DataLoadThread(QThread):
    data_loaded = pyqtSignal(pd.DataFrame)
    
    def run(self):
        df = pd.read_excel(self.file_path)
        self.data_loaded.emit(df)
```

**효과**: UI 응답성 100% 개선 (블로킹 제거)

### 3. 디스크 I/O 최적화 (우선순위: 낮음)

#### A. 데이터 캐싱
```python
# 대규모 파일 로드 시 캐싱
import pickle
import hashlib

def load_with_cache(file_path):
    cache_path = f".cache/{hashlib.md5(file_path.encode()).hexdigest()}.pkl"
    if os.path.exists(cache_path):
        with open(cache_path, 'rb') as f:
            return pickle.load(f)
    
    df = pd.read_excel(file_path)
    with open(cache_path, 'wb') as f:
        pickle.dump(df, f)
    return df
```

**효과**: 재로딩 시 속도 10배 향상

### 4. UI 렌더링 최적화 (우선순위: 높음)

#### A. Virtual Scrolling
```python
# QTableView + QAbstractTableModel 사용
# 화면에 보이는 행만 렌더링
```

**효과**: 100,000행 데이터를 1000행처럼 빠르게 스크롤

#### B. Plot Resolution 조정
```python
# 현재: 기본 DPI (100)

# 권장: 사용자 선택 가능하도록
self.figure = Figure(figsize=(10, 8), dpi=75)  # 낮은 DPI로 빠른 렌더링
```

**효과**: Plot 생성 속도 20-30% 향상

## 구현 우선순위

### Phase 1: 즉시 적용 가능 (난이도: 낮음)
1. ✅ Hover event throttling
2. ✅ Plot DPI 조정 옵션
3. ✅ 정렬 조건부 비활성화

### Phase 2: 중기 개선 (난이도: 중간)
4. LazyTableModel 구현
5. DataFrame 참조 방식 변경
6. 비동기 데이터 로딩

### Phase 3: 장기 개선 (난이도: 높음)
7. Virtual Scrolling 완전 구현
8. Plot Figure 캐싱 시스템
9. 데이터 압축 저장

## 성능 측정 기준

### 현재 성능 (예상)
- 100MB Excel 파일 로드: ~20초
- 50,000행 테이블 표시: ~5초
- Volcano plot 생성: ~2초
- 메모리 사용량: ~500MB (50,000행 기준)

### 목표 성능
- 100MB Excel 파일 로드: ~5초 (75% 개선)
- 50,000행 테이블 표시: ~1초 (80% 개선)
- Volcano plot 생성: ~1초 (50% 개선)
- 메모리 사용량: ~150MB (70% 개선)

## 측정 도구

### 메모리 프로파일링
```python
import tracemalloc

tracemalloc.start()
# 코드 실행
current, peak = tracemalloc.get_traced_memory()
print(f"Current: {current / 1024 / 1024:.2f} MB")
print(f"Peak: {peak / 1024 / 1024:.2f} MB")
tracemalloc.stop()
```

### CPU 프로파일링
```python
import cProfile
import pstats

profiler = cProfile.Profile()
profiler.enable()
# 코드 실행
profiler.disable()
stats = pstats.Stats(profiler)
stats.sort_stats('cumulative')
stats.print_stats(20)
```

## 추가 권장사항

### 1. 대용량 데이터 경고
```python
if len(dataframe) > 100000:
    reply = QMessageBox.question(
        self, "Large Dataset",
        f"Dataset has {len(dataframe)} rows. Display may be slow. Continue?",
        QMessageBox.Yes | QMessageBox.No
    )
```

### 2. 프로그레스 표시
```python
# 장시간 작업 시 명확한 진행 상황 표시
progress = QProgressDialog("Loading data...", "Cancel", 0, 100, self)
progress.setWindowModality(Qt.WindowModal)
```

### 3. Settings 추가
```python
# 사용자가 성능 옵션 선택
settings = {
    'max_display_rows': 10000,  # 최대 표시 행
    'plot_dpi': 75,  # Plot DPI
    'enable_sorting': False,  # 대규모 데이터 정렬 비활성
    'cache_data': True,  # 데이터 캐싱
}
```

## 결론

**즉시 구현 권장**:
1. LazyTableModel (메모리 70% 절감)
2. Hover throttling (CPU 30% 절감)
3. 비동기 로딩 (UI 응답성 100% 개선)

이 3가지만 구현해도 전반적인 성능이 2-3배 향상될 것으로 예상됩니다.
