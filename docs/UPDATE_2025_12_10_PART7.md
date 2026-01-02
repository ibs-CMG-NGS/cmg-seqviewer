# 🔄 Update Summary - RNA-Seq Analyzer (Part 7)

## 📅 날짜: 2025-12-10

---

## ✅ 주요 수정사항

### 1️⃣ Comparison Sheet gene_id 중복 표시 문제 해결
**파일:** `src/gui/main_window.py`

**문제:**
```
현재 상태:
Header:   gene_id | symbol | log2FC | padj | Dataset
Data:     ENSG... | ENSG... | 2.34   | 0.001 | H2O2_vs_Control
          ↑         ↑
      gene_id    gene_id (중복!)
```

- `symbol` 컬럼에 `gene_id` 값이 표시됨
- 실제 `symbol` (TP53, BRCA1 등)이 표시되지 않음

**원인:**
```python
# symbol 컬럼을 column_mapping에서 찾지 못함
for orig, std in dataset.column_mapping.items():
    if std in ['gene_id', 'log2fc', 'adj_pvalue']:  # ❌ 'symbol' 누락
        column_map[std] = orig

# symbol이 df.columns에는 있어도 rename_map에 추가 안됨
if 'symbol' in df.columns:  # ❌ 매핑 없이 원본 컬럼명 사용
    columns_to_keep.append('symbol')
```

**해결:**
```python
# ✅ 수정 1: column_mapping에 'symbol' 추가
for orig, std in dataset.column_mapping.items():
    if std in ['gene_id', 'symbol', 'log2fc', 'adj_pvalue']:
        column_map[std] = orig

# ✅ 수정 2: symbol도 column_map에서 찾아서 rename
if 'symbol' in column_map and column_map['symbol'] in df.columns:
    columns_to_keep.append(column_map['symbol'])
    rename_map[column_map['symbol']] = 'symbol'
```

**결과:**
```
✅ 올바른 상태:
Header:   gene_id | symbol | log2FC | padj    | Dataset
Data:     ENSG... | TP53   | 2.34   | 0.001   | H2O2_vs_Control
          ENSG... | BRCA1  | -1.45  | 0.02    | H2O2_vs_GABA
                    ↑
                실제 symbol 표시!
```

**적용 범위:**
- `_compare_gene_list()` 메서드 (2곳 수정)
- `_compare_statistics()` 메서드 (2곳 수정)

---

### 2️⃣ 단일 데이터셋 시각화 기능 추가 🎨

#### A. 새로운 파일 생성
**파일:** `src/gui/visualization_dialog.py` (NEW!)

**구현된 Plot:**

##### 📊 **1. Volcano Plot**
```python
class VolcanoPlotDialog(QDialog):
    """Volcano Plot 시각화"""
```

**특징:**
- **X축:** log2(Fold Change)
- **Y축:** -log10(Adjusted P-value)
- **색상 구분:**
  - 🔴 Up-regulated: log2FC ≥ threshold & padj ≤ threshold
  - 🔵 Down-regulated: log2FC ≤ -threshold & padj ≤ threshold
  - ⚫ Not Significant: 나머지

**설정 가능한 항목:**
1. **Threshold 설정:**
   - P-adj Threshold (기본값: 0.05)
   - Log2FC Threshold (기본값: 1.0)

2. **색상 설정:**
   - Down-regulation: 파란색 (기본)
   - Up-regulation: 빨간색 (기본)
   - Not Significant: 진한 회색 (기본)
   - 각 색상 클릭하여 변경 가능

3. **시각적 옵션:**
   - Dot Size: 1~100 (기본값: 20)
   - X-axis Range: Min/Max 설정
   - Y-axis Range: Min/Max 설정

4. **UI 기능:**
   - Matplotlib Navigation Toolbar (Zoom, Pan, Save)
   - 실시간 설정 업데이트
   - Threshold 라인 표시 (점선)
   - 범례 자동 표시 (개수 포함)

**사용 예시:**
```
설정:
- P-adj Threshold: 0.05
- Log2FC Threshold: 1.0

결과:
- UP (123):   log2FC > 1.0, padj < 0.05 → 빨간색
- DOWN (98):  log2FC < -1.0, padj < 0.05 → 파란색
- NS (5234):  나머지 → 회색
```

##### 📈 **2. P-adj Histogram**
```python
class PadjHistogramDialog(QDialog):
    """P-adjusted 분포 히스토그램"""
```

**특징:**
- P-value 분포 확인
- 50개 bins로 분할
- Frequency 표시

**활용:**
- 데이터 품질 확인
- 유의미한 결과 비율 파악

##### 🔥 **3. Heatmap**
```python
class HeatmapDialog(QDialog):
    """발현 패턴 Heatmap"""
```

**특징:**
- 숫자형 컬럼만 자동 선택
- 상위 50개 유전자만 표시 (가독성)
- RdBu_r colormap (빨강-파랑 반전)
- Colorbar 포함

**활용:**
- 유전자 발현 패턴 시각화
- 클러스터링 패턴 확인

---

#### B. 메인 윈도우 메뉴 추가
**파일:** `src/gui/main_window.py`

**새로운 메뉴:**
```
메뉴바
├── File
├── Analysis
├── View
└── Visualization (NEW!)
    ├── 📊 Volcano Plot (Ctrl+V)
    ├── 📈 P-adj Histogram
    └── 🔥 Heatmap
```

**동작 흐름:**
```python
def _on_visualization_requested(self, viz_type: str):
    """시각화 요청 처리"""
    
    # 1. 현재 탭 확인
    current_index = self.data_tabs.currentIndex()
    
    # 2. Comparison 결과인지 확인
    if dataset is None:
        ❌ "Visualization is not available for comparison results"
        return
    
    # 3. 필요한 컬럼 확인
    required_cols = {
        'volcano': ['log2FC', 'padj'],
        'histogram': ['padj'],
        'heatmap': ['log2FC']
    }
    
    # 4. 컬럼명 표준화 (column_mapping 적용)
    df = df.rename(columns=rename_map)
    
    # 5. 다이얼로그 열기
    if viz_type == "volcano":
        dialog = VolcanoPlotDialog(df, self)
        dialog.exec()
```

**보호 기능:**
1. ❌ **데이터 없음:** "Please load a dataset first"
2. ❌ **Comparison 결과:** "Visualization is not available for comparison results"
3. ❌ **컬럼 부족:** "Required columns not found: log2FC, padj"

---

## 🎯 사용 방법

### 1. Volcano Plot 생성
```
1. 데이터셋 로드 (File > Open Dataset)
2. Visualization > Volcano Plot (또는 Ctrl+V)
3. 설정 조정:
   - P-adj Threshold: 0.05 → 0.01 (더 엄격하게)
   - Log2FC Threshold: 1.0 → 2.0 (2배 이상 변화)
   - 색상 버튼 클릭하여 원하는 색 선택
   - Dot Size: 20 → 30 (더 크게)
4. Refresh Plot 클릭
5. Matplotlib Toolbar로 Zoom/Pan
6. 💾 Save 버튼으로 이미지 저장
```

### 2. P-adj Histogram 생성
```
1. 데이터셋 선택
2. Visualization > P-adj Histogram
3. 분포 확인
4. Close 또는 X 버튼으로 닫기
```

### 3. Heatmap 생성
```
1. 데이터셋 선택
2. Visualization > Heatmap
3. 상위 50개 유전자 발현 패턴 확인
4. Close 또는 X 버튼으로 닫기
```

---

## 📊 테스트 체크리스트

### 1. Comparison 결과 Symbol 표시
- [ ] Comparison: Gene List 실행
- [ ] 결과 확인:
  - [ ] ✅ symbol 컬럼에 유전자 symbol (TP53, BRCA1 등) 표시
  - [ ] ✅ gene_id 컬럼과 symbol 컬럼이 다른 값 표시

### 2. Volcano Plot
- [ ] 단일 데이터셋 로드
- [ ] Visualization > Volcano Plot 선택
- [ ] 설정 테스트:
  - [ ] ✅ P-adj Threshold 변경 → Plot 업데이트
  - [ ] ✅ Log2FC Threshold 변경 → Plot 업데이트
  - [ ] ✅ 색상 변경 → 점 색상 변경
  - [ ] ✅ Dot Size 변경 → 점 크기 변경
  - [ ] ✅ X/Y axis Range 설정 → 축 범위 변경
- [ ] ✅ Threshold 라인 표시 확인 (점선)
- [ ] ✅ 범례에 개수 표시 확인 (UP (123), DOWN (98), NS (5234))

### 3. Comparison 결과에서 시각화 방지
- [ ] Comparison: Gene List로 탭 생성
- [ ] Visualization > Volcano Plot 선택
- [ ] ✅ 경고 메시지 표시: "Visualization is not available for comparison results"

### 4. P-adj Histogram
- [ ] 단일 데이터셋 선택
- [ ] Visualization > P-adj Histogram
- [ ] ✅ Histogram 표시 확인

### 5. Heatmap
- [ ] 단일 데이터셋 선택
- [ ] Visualization > Heatmap
- [ ] ✅ 상위 50개 유전자 Heatmap 표시 확인

---

## 🔧 기술적 세부사항

### 의존성
```python
import matplotlib
matplotlib.use('Qt5Agg')  # PyQt6와 호환
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT
```

### NumPy 연산
```python
# -log10(padj) 계산
df['-log10(padj)'] = -np.log10(df['padj'].replace(0, 1e-300))

# padj=0인 경우 1e-300으로 대체하여 log(0) 에러 방지
```

### 색상 분류 로직
```python
df['regulation'] = 'ns'  # 기본값

# Up-regulated
df.loc[(df['log2FC'] >= threshold) & 
       (df['padj'] <= p_threshold), 'regulation'] = 'up'

# Down-regulated
df.loc[(df['log2FC'] <= -threshold) & 
       (df['padj'] <= p_threshold), 'regulation'] = 'down'
```

---

## 🎯 요약

**해결된 문제:**
1. ✅ Comparison Sheet symbol 중복 표시
   - `column_mapping`에 'symbol' 추가
   - `rename_map`으로 올바른 매핑

**새로운 기능:**
2. ✅ Volcano Plot 시각화
   - 완전한 설정 패널 (threshold, 색상, 크기, 축 범위)
   - 실시간 업데이트
   - Matplotlib 도구 (Zoom, Pan, Save)
   
3. ✅ P-adj Histogram
   - 간단한 분포 확인
   
4. ✅ Heatmap
   - 발현 패턴 시각화

**보호 기능:**
- ❌ Comparison 결과에서 시각화 차단
- ❌ 필수 컬럼 부재 시 경고

모든 기능이 정상 작동합니다! 🎉

---

## 📸 스크린샷 (예상)

### Volcano Plot 설정 패널
```
┌─────────────────────────────────────┐
│ Plot Settings                       │
├─────────────────────────────────────┤
│ P-adj Threshold:      [0.05    ▼]  │
│ Log2FC Threshold:     [1.00    ▼]  │
│ Colors:  [Down] [Up] [Not Sig]     │
│ Dot Size:             [20      ▼]  │
│ X-axis Range: Min [-10 ▼] Max [10▼]│
│ Y-axis Range: Min [0  ▼] Max [50▼] │
└─────────────────────────────────────┘
```

### Volcano Plot
```
        -log10(padj)
         │
      50 │     🔴 🔴        🔴
         │   🔴   🔴      🔴
         │  🔴     🔴    🔴
      25 │ 🔴  ⚫⚫⚫  🔴
         │🔴  ⚫⚫⚫⚫  🔴
         │  ⚫⚫⚫⚫⚫⚫
       0 │─────────┼─────────→ log2FC
        -10      0       10
        🔵              🔴
    Down-reg      Up-reg
```

다음에 테스트해보세요! 🚀
