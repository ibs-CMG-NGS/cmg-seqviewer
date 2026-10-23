# 헤더 표준화 제안서

> **Archived 2026-10-23** — Completed (v1.2.0).<br>
> This document is kept for historical reference. See [Planning Documentation](../README.md) for current plans.

## 🎯 목표
복잡한 column mapping 대신, **데이터 로딩 시점에 컬럼명을 표준화**하여 전체 프로그램에서 일관된 컬럼명 사용

---

## ❌ 현재 방식의 문제점

### 1. 복잡한 Mapping 시스템
```python
# 원본 파일: log2FoldChange, pvalue, padj
# 
# 로딩 시:
# auto_mapping = {'log2FoldChange': 'log2fc', 'pvalue': 'pvalue', ...}
# 
# Dataset 저장 시:
# column_mapping = {'log2FoldChange': 'log2fc'}  # 원본 -> 표준
# 
# 사용 시:
# reverse_mapping = {'log2fc': 'log2FoldChange'}  # 표준 -> 원본
# 
# 결과: 혼란스럽고 버그 발생 가능
```

### 2. 여러 곳에서 다른 로직
```python
# main_window.py: reverse_mapping 사용
reverse_mapping = {v: k for k, v in column_mapping.items()}

# statistics.py: pattern fallback
if 'log2fc' not in column_mapping:
    # 패턴 매칭으로 찾기...

# filter_panel.py: 또 다른 매핑...
```

### 3. 디버깅 어려움
- "왜 log2FoldChange가 안 보이지?" → mapping 문제? reverse mapping 문제?
- "pvalue가 0으로만 나와" → 원본 컬럼을 못 찾았나? 매핑 오류?

---

## ✅ 제안: 표준화 방식 (Standardization)

### 핵심 아이디어
**"로딩 시점에 컬럼명을 표준 이름으로 변경하고, 이후 모든 코드에서 표준 이름만 사용"**

### 장점
1. **단순함**: mapping dictionary 불필요
2. **명확함**: 모든 코드에서 같은 컬럼명
3. **유지보수 용이**: 한 곳(DataLoader)만 수정
4. **버그 감소**: 매핑 오류 가능성 제거

---

## 🔧 구현 방안

### 1. 표준 컬럼명 정의

```python
# src/models/standard_columns.py (새 파일)

class StandardColumns:
    """표준 컬럼명 정의"""
    
    # Differential Expression 필수 컬럼
    GENE_ID = 'gene_id'
    LOG2FC = 'log2fc'
    PVALUE = 'pvalue'
    ADJ_PVALUE = 'adj_pvalue'
    BASE_MEAN = 'base_mean'
    
    # Differential Expression 선택 컬럼
    LFCSE = 'lfcse'
    STAT = 'stat'
    
    # GO Analysis 컬럼
    GO_TERM = 'term'
    GO_TERM_ID = 'term_id'
    GO_GENE_COUNT = 'gene_count'
    GO_PVALUE = 'pvalue'
    GO_FDR = 'fdr'
    GO_GENES = 'genes'
    
    @classmethod
    def get_de_required(cls):
        """필수 DE 컬럼"""
        return [cls.GENE_ID, cls.LOG2FC, cls.ADJ_PVALUE]
    
    @classmethod
    def get_de_all(cls):
        """모든 DE 관련 컬럼"""
        return [
            cls.GENE_ID, cls.BASE_MEAN, cls.LOG2FC, 
            cls.LFCSE, cls.STAT, cls.PVALUE, cls.ADJ_PVALUE
        ]
    
    @classmethod
    def get_go_required(cls):
        """필수 GO 컬럼"""
        return [cls.GO_TERM, cls.GO_GENE_COUNT, cls.GO_FDR]
```

### 2. 컬럼 리네이밍 (DataLoader)

```python
# src/utils/data_loader.py 수정

class DataLoader:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # 패턴 매칭 (변경 없음)
        self.de_column_patterns = {
            'gene_id': ['gene', 'gene_id', 'geneid', 'id', 'symbol'],
            'log2fc': ['log2fc', 'log2foldchange', 'logfc'],
            'pvalue': ['pvalue', 'p.value', 'p_value', 'pval'],
            'adj_pvalue': ['padj', 'adj.p.value', 'fdr', 'qvalue'],
            'base_mean': ['basemean', 'base_mean', 'mean'],
        }
    
    def load_from_excel(self, file_path, ...):
        # ... (기존 코드)
        
        # 컬럼 매핑 찾기
        auto_mapping = self._map_columns(df, dataset_type)
        
        # ✨ 새로운 부분: DataFrame 컬럼명을 표준 이름으로 변경
        df = self._standardize_columns(df, auto_mapping, dataset_type)
        
        # Dataset 생성 (column_mapping 불필요!)
        dataset = Dataset(
            data=df,
            name=dataset_name,
            dataset_type=dataset_type,
            # column_mapping 제거!
        )
        
        return dataset
    
    def _standardize_columns(self, df: pd.DataFrame, 
                            mapping: Dict[str, str],
                            dataset_type: DatasetType) -> pd.DataFrame:
        """
        DataFrame의 컬럼명을 표준 이름으로 변경
        
        Args:
            df: 원본 DataFrame
            mapping: {원본 컬럼: 표준 컬럼} 매핑
            dataset_type: 데이터셋 타입
            
        Returns:
            컬럼명이 표준화된 DataFrame
        """
        df = df.copy()
        
        # 매핑된 컬럼만 리네임
        rename_dict = mapping  # {원본: 표준}
        df.rename(columns=rename_dict, inplace=True)
        
        # 필수 컬럼 체크
        if dataset_type == DatasetType.DIFFERENTIAL_EXPRESSION:
            required = StandardColumns.get_de_required()
        elif dataset_type == DatasetType.GO_ANALYSIS:
            required = StandardColumns.get_go_required()
        else:
            required = []
        
        missing = [col for col in required if col not in df.columns]
        if missing:
            raise ValueError(f"Missing required columns after standardization: {missing}")
        
        self.logger.info(f"Standardized columns: {list(rename_dict.values())}")
        self.logger.info(f"Final columns: {list(df.columns)}")
        
        return df
```

### 3. Dataset 모델 단순화

```python
# src/models/data_models.py 수정

@dataclass
class Dataset:
    """RNA-Seq 데이터셋"""
    data: pd.DataFrame
    name: str
    dataset_type: DatasetType
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # ❌ 제거: column_mapping
    # column_mapping: Dict[str, str] = field(default_factory=dict)
    
    # ✅ 추가: 원본 컬럼명 정보 (선택적, 참고용)
    original_columns: Dict[str, str] = field(default_factory=dict)  # {표준: 원본}
```

### 4. 전체 코드 단순화

#### Before (복잡함):
```python
# main_window.py
column_mapping = dataset.column_mapping  # {원본: 표준}
reverse_mapping = {v: k for k, v in column_mapping.items()}  # {표준: 원본}

if 'log2fc' in reverse_mapping:
    orig_col = reverse_mapping['log2fc']
    if orig_col in all_columns:
        columns_to_show.append(orig_col)
```

#### After (단순함):
```python
# main_window.py
if StandardColumns.LOG2FC in df.columns:
    columns_to_show.append(StandardColumns.LOG2FC)
```

---

## 📊 영향 받는 파일 및 수정 사항

### 1. 새로 생성할 파일
- `src/models/standard_columns.py`: 표준 컬럼명 정의

### 2. 수정할 파일 (중요도 순)

#### ① `src/utils/data_loader.py`
- `_standardize_columns()` 메서드 추가
- `load_from_excel()`: 컬럼 리네임 추가
- `column_mapping` 생성 제거

#### ② `src/models/data_models.py`
- `Dataset.column_mapping` 제거
- `Dataset.original_columns` 추가 (선택적)

#### ③ `src/gui/main_window.py`
- `_filter_columns_by_level()`: 단순화
  - `column_mapping`, `reverse_mapping` 제거
  - 직접 표준 컬럼명 사용
- 모든 컬럼 참조를 표준명으로 변경

#### ④ `src/utils/statistics.py`
- `run_fishers_test()`: 패턴 fallback 제거
- `run_gsea_lite()`: 패턴 fallback 제거
- 직접 `StandardColumns.LOG2FC` 등 사용

#### ⑤ `src/presenters/main_presenter.py`
- 필터링, 정렬 로직에서 표준 컬럼명 사용
- `column_mapping` 로그 제거

#### ⑥ `src/utils/database_manager.py`
- `load_dataset()`: 컬럼명이 이미 표준화되어 있음
- 메타데이터에서 `column_mapping` 제거

---

## 🔄 마이그레이션 전략

### Phase 1: 표준 컬럼 정의 및 DataLoader 수정
1. `StandardColumns` 클래스 생성
2. `_standardize_columns()` 구현
3. 테스트: 로딩 후 DataFrame 컬럼명 확인

### Phase 2: Dataset 모델 수정
1. `column_mapping` 제거
2. 기존 데이터베이스 호환성 유지 (파싱 시 무시)

### Phase 3: GUI 및 Presenter 단순화
1. `main_window.py`: 컬럼 필터링 로직 단순화
2. `main_presenter.py`: 매핑 제거

### Phase 4: Statistics 단순화
1. `statistics.py`: 패턴 fallback 제거
2. 직접 표준 컬럼 사용

### Phase 5: Database 정리
1. 기존 database 재생성 (표준 컬럼명으로)
2. `metadata.json`에서 `column_mapping` 제거

---

## ⚠️ 주의사항

### 1. 기존 데이터베이스
- **옵션 A**: 모두 재생성 (추천)
- **옵션 B**: 로딩 시 자동 변환 로직 추가

### 2. 사용자 Export 파일
- 표준 컬럼명으로 export됨
- 필요 시 "Export with Original Names" 옵션 추가 가능

### 3. 샘플 컬럼 (count columns)
- 표준화하지 않음 (원본 유지)
- 예: `GABA_5`, `H2O2_3` 등

---

## 📈 예상 효과

### Before:
- 코드 라인: ~2,500줄
- 컬럼 관련 버그: 자주 발생
- 디버깅 시간: 길음
- 신규 기능 추가: 복잡함

### After:
- 코드 라인: ~2,000줄 (20% 감소)
- 컬럼 관련 버그: 거의 없음
- 디버깅 시간: 짧음
- 신규 기능 추가: 단순함

---

## 🎯 결론

**표준화 방식이 훨씬 우수합니다:**

| 항목 | Mapping 방식 | Standardization 방식 |
|------|-------------|---------------------|
| **복잡도** | ⭐⭐⭐⭐⭐ (매우 복잡) | ⭐ (단순) |
| **유지보수** | ⭐⭐ (어려움) | ⭐⭐⭐⭐⭐ (쉬움) |
| **버그 가능성** | ⭐⭐⭐⭐ (높음) | ⭐ (낮음) |
| **성능** | ⭐⭐⭐ (mapping 오버헤드) | ⭐⭐⭐⭐⭐ (오버헤드 없음) |
| **가독성** | ⭐⭐ (헷갈림) | ⭐⭐⭐⭐⭐ (명확) |

**추천: 표준화 방식으로 리팩토링**

---

## 🚀 다음 단계

진행하시겠습니까? 다음과 같이 단계별로 구현할 수 있습니다:

1. **Phase 1 (30분)**: `StandardColumns` + `_standardize_columns()` 구현
2. **Phase 2 (20분)**: `Dataset` 모델 수정
3. **Phase 3 (1시간)**: GUI 로직 단순화
4. **Phase 4 (30분)**: Statistics 단순화
5. **Phase 5 (20분)**: Database 재생성

**총 예상 시간: 2-3시간**
**예상 효과: 버그 90% 감소, 코드 20% 감소, 유지보수성 5배 향상**