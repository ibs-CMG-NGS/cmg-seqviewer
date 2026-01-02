# RNA-Seq Data Viewer - Update Part 9 (2025-12-10)

## 개요
사용자 피드백에 따른 3가지 중요한 버그 수정 및 개선 사항

---

## 1. Volcano Plot Y축 범위 설정 문제 수정

### 문제
- Y축 Min/Max 중 하나를 Auto(0)로 설정하면 다른 쪽 설정이 적용되지 않는 문제
- X축과 Y축의 로직이 일관되지 않음

### 원인
```python
# 기존 코드 (문제)
# X축: minimum 값과 비교 (정상 작동)
if self.x_min_spin.value() != self.x_min_spin.minimum():
    self.x_min = self.x_min_spin.value()

# Y축: 0보다 큰지 확인 (비일관적)
if self.y_min_spin.value() > 0:
    self.y_min = self.y_min_spin.value()
```

### 해결
```python
# 수정된 코드
# Y축도 X축과 동일한 로직 사용
if self.y_min_spin.value() != self.y_min_spin.minimum():
    self.y_min = self.y_min_spin.value()
else:
    self.y_min = None
    
if self.y_max_spin.value() != self.y_max_spin.minimum():
    self.y_max = self.y_max_spin.value()
else:
    self.y_max = None
```

### 효과
- X축과 Y축이 독립적으로 작동
- Min을 Auto로 설정해도 Max가 정상 작동
- Max를 Auto로 설정해도 Min이 정상 작동
- 일관된 사용자 경험 제공

---

## 2. Heatmap 유전자 선택 기준 변경 (Variance → Padj)

### 배경
사용자 질문: "heatmap에서 gene을 선정하는 기준이 Padj가 맞을 것 같아. variance를 사용한 특별한 이유가 있는지?"

### 답변
- **맞습니다!** 차등 발현 분석(Differential Expression)에서는 통계적 유의성이 중요합니다
- Variance 기준은 일반적인 데이터 탐색에는 유용하지만, DE 분석에서는 padj가 더 적절합니다
- Padj가 작을수록 통계적으로 유의미한 차등 발현을 보이는 유전자입니다

### 변경 사항

#### Before (Variance 기준)
```python
# 분산이 큰 유전자 선택 (발현 변동이 큰 유전자)
variances = expr_data.var(axis=1)
top_genes_idx = variances.nlargest(min(self.n_genes, len(expr_data))).index
```

#### After (Padj 기준, Fallback 포함)
```python
# padj 기준으로 가장 유의미한 유전자 선택
if 'padj' in df.columns:
    df_with_padj = df.loc[expr_data.index].copy()
    valid_padj = df_with_padj['padj'].dropna()
    if len(valid_padj) > 0:
        # padj가 작은(유의미한) 순서로 선택
        top_genes_idx = valid_padj.nsmallest(min(self.n_genes, len(valid_padj))).index
    else:
        # padj가 모두 NaN이면 분산 기준으로 대체
        variances = expr_data.var(axis=1)
        top_genes_idx = variances.nlargest(min(self.n_genes, len(expr_data))).index
else:
    # padj 컬럼이 없으면 분산 기준으로 선택
    variances = expr_data.var(axis=1)
    top_genes_idx = variances.nlargest(min(self.n_genes, len(expr_data))).index
```

### 장점
1. **생물학적 의미**: 통계적으로 유의미한 차등 발현 유전자 선택
2. **DE 분석 적합**: RNA-Seq 차등 발현 분석의 표준 기준 사용
3. **Robust Fallback**: padj가 없거나 모두 NaN인 경우 variance로 대체
4. **하위 호환성**: 기존 데이터셋에서도 정상 작동

### 사용 예시
- **Top 50 genes by padj**: 가장 유의미하게 차등 발현된 50개 유전자의 heatmap
- **Biological interpretation**: 실험 조건 간 실제로 차이가 있는 유전자 패턴 시각화

---

## 3. Matplotlib Font DEBUG 로그 억제

### 문제
프로그램 실행 시 대량의 DEBUG 로그 출력:
```
[10:54:37] DEBUG: findfont: Matching sans-serif:style=normal...
[10:54:37] DEBUG: findfont: score(FontEntry(...)) = 10.335
[10:54:37] DEBUG: findfont: score(FontEntry(...)) = 10.05
... (수백 줄 반복)
```

### 원인
- Matplotlib의 `font_manager`가 폰트를 찾을 때 모든 시스템 폰트를 스캔하며 DEBUG 로그 생성
- 기능에는 문제 없으나 로그가 지나치게 많음

### 해결
```python
# visualization_dialog.py 상단에 추가
import logging
logging.getLogger('matplotlib.font_manager').setLevel(logging.WARNING)
```

### 효과
- DEBUG 로그 억제, WARNING 이상만 표시
- 로그 가독성 향상
- 프로그램 기능에는 전혀 영향 없음
- 실제 오류 메시지는 여전히 표시됨

---

## 수정된 파일

### `src/gui/visualization_dialog.py`
1. **Imports 섹션**: matplotlib font_manager 로그 레벨 설정
2. **VolcanoPlotDialog._on_settings_changed()**: Y축 범위 로직 수정
3. **HeatmapDialog._plot()**: Padj 기준 유전자 선택으로 변경

---

## 테스트 시나리오

### 1. Volcano Plot Y-axis Range
- [x] Y-Min = Auto, Y-Max = 30 → Max 적용됨
- [x] Y-Min = 5, Y-Max = Auto → Min 적용됨
- [x] Y-Min = 5, Y-Max = 30 → 둘 다 적용됨
- [x] Y-Min = Auto, Y-Max = Auto → 전체 범위

### 2. Heatmap Gene Selection
- [x] Padj 있는 데이터: padj 기준 선택 (작은 값 우선)
- [x] Padj NaN인 행 있음: 유효한 padj만 사용
- [x] Padj 컬럼 없음: variance 기준으로 대체
- [x] Top 10, 50, 100 genes: 각각 올바른 수만큼 선택

### 3. Log Suppression
- [x] 프로그램 시작 시 font DEBUG 로그 없음
- [x] Visualization 창 열 때 font DEBUG 로그 없음
- [x] INFO, WARNING 로그는 정상 표시

---

## 사용자 영향

### 긍정적 영향
1. **Volcano Plot**: 축 범위 설정이 직관적이고 예상대로 작동
2. **Heatmap**: DE 분석에 적합한 유전자 선택 (생물학적으로 더 의미있음)
3. **로그**: 불필요한 DEBUG 로그 제거로 중요한 메시지 식별 용이

### 하위 호환성
- 모든 변경사항이 기존 기능을 유지하면서 개선
- 기존 데이터셋과 워크플로우에 영향 없음

---

## 기술적 세부사항

### Padj 기준 선택의 통계적 의미
- **Padj (Adjusted P-value)**: Multiple testing correction 적용된 p-value
- **낮은 padj = 높은 유의성**: 실험 조건 간 실제 차이가 있을 확률 높음
- **DE 분석 표준**: DESeq2, edgeR 등 모든 DE 도구에서 padj 사용
- **0.05 threshold**: 일반적으로 padj < 0.05인 유전자를 유의미하다고 판단

### Variance vs Padj
| 기준 | 장점 | 단점 | 적합한 경우 |
|------|------|------|------------|
| **Variance** | 발현 변동 큰 유전자 찾기 | 통계적 유의성 무시 | 일반 데이터 탐색 |
| **Padj** | 통계적으로 유의미한 유전자 | DE 분석 필요 | RNA-Seq DE 분석 |

### Font Logging 레벨
```python
# Python logging 레벨
CRITICAL = 50  # 심각한 에러
ERROR = 40     # 에러
WARNING = 30   # 경고 (설정한 레벨)
INFO = 20      # 정보
DEBUG = 10     # 디버그 (억제)
```

---

## 향후 개선 가능 사항

### Heatmap 추가 기능 고려
1. **Selection method 옵션**: Padj / Variance / Log2FC / Manual selection
2. **Filter by threshold**: padj < 0.05 & |log2FC| > 1 조건 등
3. **Clustering options**: Hierarchical clustering on/off
4. **Gene labels**: 중요 유전자 이름 표시 옵션

### Volcano Plot 개선
1. **Preset ranges**: Common ranges (0-10, 0-20, 0-50) 빠른 선택
2. **Symmetrical axis**: X-axis 자동 대칭 옵션
3. **Save settings**: 사용자가 선호하는 설정 저장

---

## 결론

이번 업데이트는 사용자 피드백을 반영한 3가지 핵심 개선사항입니다:
1. ✅ **Volcano Plot**: 축 범위 설정 로직 수정으로 사용성 개선
2. ✅ **Heatmap**: 생물학적으로 의미있는 유전자 선택 기준 적용
3. ✅ **로그**: 불필요한 DEBUG 로그 억제로 로그 품질 향상

모든 변경사항은 하위 호환성을 유지하며, RNA-Seq 차등 발현 분석의 표준 관행을 따릅니다.
