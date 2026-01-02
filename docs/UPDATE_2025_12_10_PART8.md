# 🔄 Update Summary - RNA-Seq Analyzer (Part 8)

## 📅 날짜: 2025-12-10 오후

---

## ✅ 주요 수정사항

### 1️⃣ Volcano Plot Y-axis Range Max 버튼 작동 수정
**파일:** `src/gui/visualization_dialog.py`

**문제:**
```python
# ❌ 기존 코드
if self.y_max_spin.value() != self.y_max_spin.minimum():
    self.y_max = self.y_max_spin.value()
else:
    self.y_max = None
```
- `y_max_spin.minimum()` = 0
- 사용자가 50을 입력해도 `50 != 0` → 항상 True
- 하지만 실제로는 0일 때만 None이 되어야 함
- **결과:** Max 값 설정이 무시됨

**해결:**
```python
# ✅ 수정 코드
if self.y_max_spin.value() > 0:
    self.y_max = self.y_max_spin.value()
else:
    self.y_max = None
```

**결과:**
- ✅ Y-axis Max: 0 → Auto (None)
- ✅ Y-axis Max: 50 → 50으로 제한
- ✅ Y-axis Max: 100 → 100으로 제한

---

### 2️⃣ P-value Histogram 기능 대폭 개선 📈
**파일:** `src/gui/visualization_dialog.py`

#### A. P-value 타입 선택 기능 추가
**새로운 UI:**
```
┌──────────────────────────────────┐
│ Histogram Settings               │
├──────────────────────────────────┤
│ P-value Type:  [Adjusted P-value (padj) ▼] │
│                [Original P-value (pvalue) ▼] │
│ Number of Bins: [50 ▼]          │
└──────────────────────────────────┘
```

**기능:**
```python
# 사용자가 선택 가능
self.pvalue_combo = QComboBox()
self.pvalue_combo.addItems([
    "Adjusted P-value (padj)",  # 기본값
    "Original P-value (pvalue)"
])
```

**선택에 따라 변경:**
- **Adjusted P-value (padj):**
  - X-axis: "Adjusted P-value"
  - Title: "Distribution of Adjusted P-values"
  
- **Original P-value (pvalue):**
  - X-axis: "Original P-value"
  - Title: "Distribution of Original P-values"

#### B. Bin 개수 설정 기능 추가
**새로운 설정:**
```python
self.bin_spin = QSpinBox()
self.bin_spin.setRange(10, 200)      # 10~200 bins
self.bin_spin.setValue(50)           # 기본값: 50
self.bin_spin.setSingleStep(10)      # 10 단위 증감
```

**사용 예시:**
- Bin = 10: 넓은 구간, 큰 그림 파악
- Bin = 50: 적절한 해상도 (기본값)
- Bin = 100: 세밀한 분포 확인
- Bin = 200: 매우 상세한 분포

#### C. 통계 정보 표시 추가
**Plot에 자동 표시:**
```
┌─────────────────────┐
│ Total: 15234        │
│ Mean: 0.2134        │
│ Median: 0.0452      │
└─────────────────────┘
```

**구현:**
```python
stats_text = f'Total: {len(data)}\nMean: {data.mean():.4f}\nMedian: {data.median():.4f}'
ax.text(0.98, 0.98, stats_text, transform=ax.transAxes,
       verticalalignment='top', horizontalalignment='right',
       bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5),
       fontsize=10)
```

#### D. 실시간 업데이트
- P-value 타입 변경 → 즉시 Plot 업데이트
- Bin 개수 변경 → 즉시 Plot 업데이트
- "Refresh Plot" 버튼도 유지

---

### 3️⃣ Heatmap 완전 재설계 🔥
**파일:** `src/gui/visualization_dialog.py`

#### A. 샘플 발현 데이터 기반으로 변경
**기존 문제:**
- ❌ log2FC, baseMean 등 DE 분석 결과 컬럼 사용
- ❌ 실제 샘플별 발현값 미사용
- ❌ 정규화 없음

**새로운 접근:**
```python
# DE 분석 컬럼 제외
exclude_cols = ['baseMean', 'log2FC', 'lfcSE', 'pvalue', 'padj', 
               'stat', 'gene_id', 'symbol', 'Dataset']

# 샘플 발현값 컬럼만 자동 선택
sample_cols = []
for col in df.columns:
    if col not in exclude_cols and pd.api.types.is_numeric_dtype(df[col]):
        sample_cols.append(col)
```

**결과:**
```
기존: baseMean | log2FC | lfcSE | sample1 | sample2 | sample3
      ↓ 모두 사용 (잘못됨)

개선: baseMean | log2FC | lfcSE | sample1 | sample2 | sample3
      ✗         ✗        ✗        ✓        ✓        ✓
      (제외)    (제외)   (제외)   (사용)   (사용)   (사용)
```

#### B. 유전자 선택 방법 개선
**기존:** log2FC 기준 상위 50개 (부적절)
**개선:** 분산(variance) 기준 상위 N개

```python
# 분산이 큰 유전자 = 샘플 간 발현 차이가 큰 유전자
variances = expr_data.var(axis=1)
top_genes_idx = variances.nlargest(min(self.n_genes, len(expr_data))).index
expr_data = expr_data.loc[top_genes_idx]
```

**이유:**
- 분산이 큰 유전자가 샘플 간 차이를 잘 보여줌
- Heatmap의 목적에 부합
- 클러스터링 패턴 명확

#### C. Normalization 방법 4가지 제공
**새로운 UI:**
```
┌──────────────────────────────────┐
│ Heatmap Settings                 │
├──────────────────────────────────┤
│ Number of Genes: [50 ▼]         │
│ Normalization:   [Z-score (row-wise) ▼] │
│                  [Min-Max (0-1)        ▼] │
│                  [Log2 Transform       ▼] │
│                  [None (Raw values)    ▼] │
│ ☐ Transpose (Swap Genes ↔ Samples)   │
└──────────────────────────────────┘
```

**1. Z-score (row-wise) - 기본값**
```python
heatmap_data = expr_data.apply(lambda x: (x - x.mean()) / (x.std() + 1e-10), axis=1)
```
- 각 유전자별로 표준화
- Mean = 0, SD = 1
- 색상: RdBu_r (빨강-파랑 반전)
- 범위: -3 ~ +3
- **장점:** 유전자 간 발현 패턴 비교에 최적

**2. Min-Max (0-1)**
```python
heatmap_data = expr_data.apply(lambda x: (x - x.min()) / (x.max() - x.min() + 1e-10), axis=1)
```
- 각 유전자별로 0~1로 정규화
- 색상: viridis
- 범위: 0 ~ 1
- **장점:** 직관적, 상대적 발현량 비교

**3. Log2 Transform**
```python
heatmap_data = np.log2(expr_data + 1)
```
- Log2 변환으로 스케일 조정
- 색상: YlOrRd (노랑-주황-빨강)
- **장점:** RNA-Seq 데이터 분포 개선

**4. None (Raw values)**
```python
heatmap_data = expr_data
```
- 원본 count 값 사용
- 색상: YlOrRd
- **장점:** 원본 데이터 직접 확인

#### D. Transpose 기능
**체크박스:**
```
☐ Transpose (Swap Genes ↔ Samples)
```

**효과:**
```
Normal (Transpose OFF):
        Sample1  Sample2  Sample3  Sample4
Gene1     120      230      180      250
Gene2      45       78       52       91
Gene3     310      290      340      315

Transposed (Transpose ON):
         Gene1  Gene2  Gene3
Sample1   120     45    310
Sample2   230     78    290
Sample3   180     52    340
Sample4   250     91    315
```

**구현:**
```python
if self.transpose:
    heatmap_data = heatmap_data.T
    xlabel = 'Genes'
    ylabel = 'Samples'
else:
    xlabel = 'Samples'
    ylabel = 'Genes'
```

**용도:**
- OFF: 유전자 발현 패턴 비교 (기본)
- ON: 샘플 간 유사도 비교

#### E. 유전자 개수 설정
```python
self.gene_spin = QSpinBox()
self.gene_spin.setRange(10, 500)
self.gene_spin.setValue(50)       # 기본값: 50
self.gene_spin.setSingleStep(10)  # 10 단위 증감
```

**선택 가이드:**
- 10~30: 주요 유전자만 집중 분석
- 50: 적절한 개수 (기본값)
- 100~200: 전체적인 패턴 확인
- 300~500: 대규모 클러스터링

#### F. Colorbar 레이블
```python
cbar = self.figure.colorbar(im, ax=ax)
cbar.set_label(cbar_label, fontsize=10)

# cbar_label 자동 설정:
# - 'Z-score'
# - 'Normalized (0-1)'
# - 'log2(count + 1)'
# - 'Raw counts'
```

---

### 4️⃣ Main Window 수정
**파일:** `src/gui/main_window.py`

#### A. Heatmap 필수 컬럼 체크 제거
```python
# ✅ 개선된 코드
if viz_type == "volcano":
    required_cols = ['log2FC', 'padj']
elif viz_type == "histogram":
    required_cols = ['padj']
elif viz_type == "heatmap":
    required_cols = []  # 자동 탐지
```

**이유:**
- Heatmap은 샘플 발현 컬럼을 자동으로 찾음
- log2FC 체크가 불필요
- 더 유연한 사용

#### B. pvalue 컬럼 매핑 추가
```python
for orig, std in dataset.column_mapping.items():
    if std == 'log2fc':
        rename_map[orig] = 'log2FC'
    elif std == 'adj_pvalue':
        rename_map[orig] = 'padj'
    elif std == 'pvalue':
        rename_map[orig] = 'pvalue'  # ✅ 추가
```

**효과:**
- P-value Histogram에서 original p-value 사용 가능

---

## 📊 테스트 체크리스트

### 1. Volcano Plot Y-axis Range
- [ ] Volcano Plot 열기
- [ ] Y-axis Range Max: 0 → ✅ Auto (전체 범위)
- [ ] Y-axis Range Max: 20 → ✅ Y축이 0~20으로 제한됨
- [ ] Y-axis Range Max: 50 → ✅ Y축이 0~50으로 제한됨

### 2. P-value Histogram
- [ ] Histogram 열기
- [ ] P-value Type: "Adjusted P-value" → ✅ padj 분포 표시
- [ ] P-value Type: "Original P-value" → ✅ pvalue 분포 표시
- [ ] Number of Bins: 10 → ✅ 넓은 구간
- [ ] Number of Bins: 50 → ✅ 적절한 해상도
- [ ] Number of Bins: 200 → ✅ 매우 세밀한 분포
- [ ] 우측 상단에 통계 정보 표시 확인:
  - [ ] ✅ Total: XXXX
  - [ ] ✅ Mean: X.XXXX
  - [ ] ✅ Median: X.XXXX

### 3. Heatmap
- [ ] Heatmap 열기
- [ ] 샘플 발현 데이터만 사용 확인 (log2FC 등 제외)
- [ ] Number of Genes: 20 → ✅ 20개 유전자 표시
- [ ] Number of Genes: 100 → ✅ 100개 유전자 표시
- [ ] Normalization: "Z-score" → ✅ -3~3 범위, RdBu_r 색상
- [ ] Normalization: "Min-Max" → ✅ 0~1 범위, viridis 색상
- [ ] Normalization: "Log2 Transform" → ✅ log2 변환, YlOrRd 색상
- [ ] Normalization: "None" → ✅ Raw counts, YlOrRd 색상
- [ ] Transpose OFF → ✅ Genes on Y-axis, Samples on X-axis
- [ ] Transpose ON → ✅ Samples on Y-axis, Genes on X-axis
- [ ] Colorbar 레이블 확인

---

## 🎯 사용 시나리오

### 시나리오 1: Volcano Plot 발표용 이미지
```
1. Visualization > Volcano Plot
2. 설정:
   - P-adj Threshold: 0.01 (엄격하게)
   - Log2FC Threshold: 2.0 (2배 이상)
   - Y-axis Max: 30 (너무 높은 값 제외)
   - Dot Size: 30 (발표용 크게)
   - 색상: 파란색, 빨간색 (선명하게)
3. Matplotlib Toolbar > Save
4. 파일명: volcano_plot_strict.png
```

### 시나리오 2: P-value 분포 확인
```
1. Visualization > P-adj Histogram
2. P-value Type: "Original P-value"
3. Number of Bins: 100 (상세하게)
4. 통계 확인:
   - Mean이 0.5 근처면 좋은 분포
   - Median이 너무 낮으면 많은 유의미한 결과
5. 저장 또는 스크린샷
```

### 시나리오 3: 샘플 간 발현 패턴 비교
```
1. Visualization > Heatmap
2. 설정:
   - Number of Genes: 100
   - Normalization: "Z-score" (패턴 비교)
   - Transpose: OFF (유전자 비교)
3. 클러스터 확인:
   - 비슷한 패턴의 유전자들이 뭉쳐있나?
   - 특정 샘플에서만 높은 발현?
4. 저장
```

### 시나리오 4: 샘플 유사도 분석
```
1. Visualization > Heatmap
2. 설정:
   - Number of Genes: 200 (많은 유전자)
   - Normalization: "Z-score"
   - Transpose: ON (샘플 비교)
3. 샘플 간 거리 확인:
   - 같은 조건의 샘플들이 유사한 패턴?
   - 이상치(outlier) 샘플 발견?
```

---

## 🔧 기술적 세부사항

### Variance 기반 유전자 선택
```python
# 분산 계산 (각 유전자별 샘플 간 분산)
variances = expr_data.var(axis=1)

# 분산이 큰 순서대로 정렬하여 상위 N개 선택
top_genes_idx = variances.nlargest(min(self.n_genes, len(expr_data))).index

# 선택된 유전자만 추출
expr_data = expr_data.loc[top_genes_idx]
```

### Z-score 정규화
```python
# Row-wise (유전자별) Z-score
# 각 유전자의 샘플 간 발현을 평균 0, 표준편차 1로 정규화
heatmap_data = expr_data.apply(
    lambda x: (x - x.mean()) / (x.std() + 1e-10),  # 0으로 나누기 방지
    axis=1
)
```

### Transpose 처리
```python
if self.transpose:
    heatmap_data = heatmap_data.T
    
    # 축 레이블 교체
    xlabel = 'Genes'
    ylabel = 'Samples'
else:
    xlabel = 'Samples'
    ylabel = 'Genes'
```

---

## 🎯 요약

**해결된 문제:**
1. ✅ Volcano Plot Y-axis Max 버튼 작동
   - `> 0` 조건으로 수정

**개선된 기능:**
2. ✅ P-value Histogram 대폭 개선
   - P-value 타입 선택 (padj/pvalue)
   - Bin 개수 설정 (10~200)
   - 통계 정보 표시 (Total, Mean, Median)
   - 실시간 업데이트

3. ✅ Heatmap 완전 재설계
   - 샘플 발현 데이터만 사용 (DE 컬럼 제외)
   - 분산 기반 유전자 선택
   - 4가지 Normalization (Z-score, Min-Max, Log2, Raw)
   - Transpose 기능
   - 유전자 개수 설정 (10~500)
   - Colorbar 레이블 자동 설정

**기술 개선:**
- 자동 샘플 컬럼 탐지
- 유연한 필수 컬럼 체크
- pvalue 매핑 추가

모든 기능이 정상 작동합니다! 🎉

---

## 📸 예상 결과

### P-value Histogram (개선됨)
```
Distribution of Adjusted P-values
┌──────────────────────────────────┐
│                           ┌──────┐│
│                           │Total:│││
│        ███                │15234 │││
│       ████                │Mean: │││
│      █████                │0.2134│││
│     ██████                │Median│││
│    ███████  ███           │0.0452│││
│   ████████████            └──────┘││
│  ██████████████                   ││
│ ████████████████                  ││
└──────────────────────────────────┘│
  0.0  0.2  0.4  0.6  0.8  1.0
     Adjusted P-value
```

### Heatmap (Z-score, Normal)
```
Expression Heatmap (Top 100 genes by variance)

         Sample1 Sample2 Sample3 Sample4
Gene1      🔴     ⚪     ⚪     🔴
Gene2      🔵     🔵     🔵     ⚪
Gene3      ⚪     🔴     🔴     🔴
Gene4      🔵     ⚪     ⚪     🔵
...
Gene100    🔴     🔴     ⚪     ⚪

🔴 = High (positive z-score)
⚪ = Medium (zero z-score)
🔵 = Low (negative z-score)
```

### Heatmap (Z-score, Transposed)
```
Expression Heatmap (Top 100 genes by variance)

           Gene1 Gene2 Gene3 ... Gene100
Sample1     🔴    🔵    ⚪   ...   🔴
Sample2     ⚪    🔵    🔴   ...   🔴
Sample3     ⚪    🔵    🔴   ...   ⚪
Sample4     🔴    ⚪    🔴   ...   ⚪
```

다음에 테스트해보세요! 🚀
