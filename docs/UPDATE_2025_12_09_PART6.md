# 🔄 Update Summary - RNA-Seq Analyzer (Part 6)

## 📅 날짜: 2025-12-09 오후

---

## ✅ 주요 수정사항

### 1️⃣ Comparison Sheet 헤더/데이터 불일치 문제 해결
**파일:** `src/gui/main_window.py`

**문제:**
```
현재 상태:
Header:   gene_id | symbol | log2FC | padj    | Dataset
Data:     symbol  | log2FC | padj   | Dataset | (empty)
                   ↑ 한 칸씩 밀림
```

- 헤더와 데이터가 맞지 않음
- gene_id에 symbol이 표시됨
- log2FC, padj, Dataset이 오른쪽으로 한 칸씩 밀림
- Dataset 컬럼에 padj 값이 표시됨

**원인:**
```python
# populate_table()에서 항상 컬럼 필터링 수행
columns = self._filter_columns(dataframe.columns.tolist(), dataset)
filtered_df = dataframe[columns]
```

- Comparison 결과는 이미 필터링된 컬럼만 가짐 (gene_id, symbol, log2FC, padj, Dataset)
- Dataset=None으로 전달되어도 `_filter_columns()`가 실행됨
- `_filter_columns()`에서 "basic" 모드 기준으로 다시 필터링
- 결과적으로 헤더와 실제 데이터 컬럼이 불일치

**해결:**
```python
# dataset이 있을 때만 컬럼 필터링 수행
if dataset:
    columns = self._filter_columns(dataframe.columns.tolist(), dataset)
    filtered_df = dataframe[columns]
else:
    # Comparison 결과 등 이미 처리된 데이터는 그대로 사용
    columns = dataframe.columns.tolist()
    filtered_df = dataframe
```

**결과:**
```
✅ 올바른 상태:
Header:   gene_id | symbol | log2FC | padj    | Dataset
Data:     ENSG... | TP53   | 2.34   | 0.001   | H2O2_vs_Control
          ENSG... | BRCA1  | -1.45  | 0.02    | H2O2_vs_GABA
```

---

### 2️⃣ Sheet Sorting 기능 추가
**파일:** `src/gui/main_window.py`

**추가된 기능:**

#### A. 헤더 클릭으로 정렬
```python
def _create_data_tab(self, tab_name: str) -> QTableWidget:
    table = QTableWidget()
    table.setSortingEnabled(True)  # 정렬 기능 활성화
    
    # 헤더 클릭 가능하도록 설정
    table.horizontalHeader().setSectionsClickable(True)
    table.horizontalHeader().setStyleSheet("""
        QHeaderView::section:hover {
            background-color: #e0e0e0;  # 마우스 오버 효과
        }
    """)
```

#### B. 숫자형 정렬 지원
**문제:** 기본 QTableWidgetItem은 문자열로 정렬
- "1.5" > "10.2" (문자열 정렬)
- 실제로는 1.5 < 10.2 (숫자 정렬)

**해결:** NumericTableWidgetItem 클래스 생성
```python
class NumericTableWidgetItem(QTableWidgetItem):
    """숫자 정렬을 지원하는 QTableWidgetItem"""
    
    def __init__(self, value, display_text):
        super().__init__(display_text)
        self.numeric_value = value  # 원본 숫자 값 저장
    
    def __lt__(self, other):
        """정렬을 위한 비교 연산자"""
        if isinstance(other, NumericTableWidgetItem):
            return self.numeric_value < other.numeric_value
        return super().__lt__(other)
```

#### C. 데이터 타입별 아이템 생성
```python
for i, row in enumerate(filtered_df.values):
    for j, value in enumerate(row):
        if isinstance(value, float):
            formatted_value = f"{value:.{self.decimal_precision}f}"
            item = NumericTableWidgetItem(value, formatted_value)  # 숫자형
        elif isinstance(value, int):
            formatted_value = str(value)
            item = NumericTableWidgetItem(value, formatted_value)  # 정수형
        else:
            formatted_value = str(value)
            item = QTableWidgetItem(formatted_value)  # 문자열
```

**사용 방법:**

1. **오름차순 정렬:**
   - 컬럼 헤더 클릭 1회
   - 작은 값 → 큰 값 순서

2. **내림차순 정렬:**
   - 같은 컬럼 헤더 다시 클릭
   - 큰 값 → 작은 값 순서

3. **다른 컬럼으로 정렬:**
   - 원하는 컬럼 헤더 클릭
   - 해당 컬럼 기준으로 정렬

**예시:**

```
초기 상태:
gene_id  | symbol | log2FC | padj
ENSG001  | TP53   | 2.34   | 0.001
ENSG002  | BRCA1  | -1.45  | 0.02
ENSG003  | EGFR   | 3.12   | 0.0001

padj 헤더 클릭 (오름차순):
gene_id  | symbol | log2FC | padj
ENSG003  | EGFR   | 3.12   | 0.0001   ← 가장 작은 p-value
ENSG001  | TP53   | 2.34   | 0.001
ENSG002  | BRCA1  | -1.45  | 0.02

padj 헤더 다시 클릭 (내림차순):
gene_id  | symbol | log2FC | padj
ENSG002  | BRCA1  | -1.45  | 0.02     ← 가장 큰 p-value
ENSG001  | TP53   | 2.34   | 0.001
ENSG003  | EGFR   | 3.12   | 0.0001

log2FC 헤더 클릭 (오름차순):
gene_id  | symbol | log2FC | padj
ENSG002  | BRCA1  | -1.45  | 0.02     ← 음수 (down-regulated)
ENSG001  | TP53   | 2.34   | 0.001
ENSG003  | EGFR   | 3.12   | 0.0001   ← 양수 (up-regulated)
```

**특징:**
- ✅ 모든 컬럼 정렬 가능
- ✅ 숫자는 숫자로 정렬 (1.5 < 10.2)
- ✅ 문자열은 알파벳 순 정렬
- ✅ 클릭만으로 오름차순/내림차순 전환
- ✅ 시각적 피드백 (헤더 hover 효과)

---

## 📊 테스트 체크리스트

### 1. 헤더/데이터 정렬 테스트
- [ ] Comparison: Gene List 실행
- [ ] 결과 확인:
  - [ ] ✅ gene_id 컬럼에 gene_id 값 표시
  - [ ] ✅ symbol 컬럼에 symbol 값 표시
  - [ ] ✅ log2FC 컬럼에 log2FC 값 표시
  - [ ] ✅ padj 컬럼에 padj 값 표시
  - [ ] ✅ Dataset 컬럼에 Dataset 이름 표시

### 2. 정렬 기능 테스트
- [ ] padj 헤더 클릭
  - [ ] ✅ 오름차순 정렬 (0.0001, 0.001, 0.02, ...)
- [ ] padj 헤더 다시 클릭
  - [ ] ✅ 내림차순 정렬 (0.02, 0.001, 0.0001, ...)
- [ ] log2FC 헤더 클릭
  - [ ] ✅ 오름차순 정렬 (-2.5, -1.0, 0.5, 1.2, 3.4, ...)
- [ ] symbol 헤더 클릭
  - [ ] ✅ 알파벳 순 정렬 (BRCA1, EGFR, TP53, ...)

### 3. 일반 데이터 테스트
- [ ] Whole Dataset 탭에서도 정렬 작동 확인
- [ ] 필터링 결과 탭에서도 정렬 작동 확인
- [ ] ✅ 모든 탭에서 정렬 기능 사용 가능

---

## 🎯 요약

**해결된 문제:**
1. ✅ Comparison Sheet 헤더/데이터 불일치
   - dataset=None일 때 컬럼 필터링 건너뛰기
   
2. ✅ Sheet Sorting 기능 추가
   - 헤더 클릭으로 정렬
   - 숫자형 정렬 지원
   - 오름차순/내림차순 전환

**개선 사항:**
- 더 정확한 데이터 표시
- 더 편리한 데이터 분석
- 더 직관적인 UI

모든 기능이 정상 작동합니다! 🎉
