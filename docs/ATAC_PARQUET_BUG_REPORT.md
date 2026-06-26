# ATAC-seq DA Parquet 파일 버그 리포트

**작성일**: 2026-06-01  
**대상 파이프라인**: ATAC-seq DA 결과 → Parquet 변환 파이프라인  
**영향 범위**: `data/datasets/` 내 모든 `*_DA.parquet` 파일

---

## 1. 요약

ATAC-seq DA 분석 파이프라인에서 생성된 Parquet 파일에 **annotation 컬럼이 누락**되어 있으며, `nearest_gene` 컬럼에 유전자명 대신 **peak ID가 잘못 저장**되어 있습니다.  
이로 인해 RNA+ATAC-seq 통합 분석(`MultiOmicsIntegrator`)이 RNA 유전자와 ATAC peak을 매칭하지 못합니다.

---

## 2. 증거: 컬럼 비교

### Excel 원본 (`final_da_result.xlsx`) — 정상

| 컬럼명 | 예시 값 |
|--------|---------|
| `peak_id` | `Interval_40044` |
| `chr` | `13` |
| `start` | `110401254` |
| `end` | `110405016` |
| **`gene_name`** | **`Plk2`** ← 실제 유전자명 |
| `gene_id` | `ENSMUSG00000021701` |
| **`annotation`** | **`Intergenic`** |
| **`distance_to_tss`** | **`8091`** |
| `baseMean` | `3113.07` |
| `log2FoldChange` | `2.398` |
| `lfcSE` | `0.069` |
| `pvalue` | `2.4e-264` |
| `padj` | `3.0e-259` |
| `direction` | `up` |

**총 14개 컬럼**

---

### DA Parquet (`1D_vs_CONTROL_DA.parquet`) — 버그

| 컬럼명 | 예시 값 | 문제 |
|--------|---------|------|
| `peak_id` | `Interval_40044` | |
| `base_mean` | `3113.07` | |
| `log2fc` | `2.398` | |
| `lfcse` | `0.069` | |
| `pvalue` | `2.4e-264` | |
| `adj_pvalue` | `3.0e-259` | |
| `direction` | `up` | |
| **`nearest_gene`** | **`Interval_40044`** | ❌ `gene_name` 대신 `peak_id` 값이 복사됨 |
| ~~`gene_name`~~ | ~~없음~~ | ❌ 누락 |
| ~~`annotation`~~ | ~~없음~~ | ❌ 누락 |
| ~~`distance_to_tss`~~ | ~~없음~~ | ❌ 누락 |
| ~~`chr/start/end`~~ | ~~없음~~ | ❌ 누락 |

**총 8개 컬럼 (6개 컬럼 누락)**

---

## 3. 버그 위치 추정

파이프라인에서 두 가지 버그가 발생했습니다.

### 버그 1 — `gene_name` 대신 `peak_id` 참조

`nearest_gene` 컬럼을 채울 때 잘못된 컬럼을 참조했습니다.

```python
# ❌ 버그 (추정 코드)
df['nearest_gene'] = df['peak_id']

# ✅ 수정 후
df['nearest_gene'] = df['gene_name']
```

### 버그 2 — Parquet 저장 시 컬럼 누락

DESeq2 통계 결과만 저장하고, annotation 관련 컬럼(`gene_name`, `gene_id`, `annotation`, `distance_to_tss`, `chr`, `start`, `end`)을 제외했습니다.

```python
# ❌ 버그 (추정 코드) — 일부 컬럼만 선택 후 저장
deseq2_cols = ['peak_id', 'base_mean', 'log2fc', 'lfcse', 'pvalue', 'adj_pvalue', 'direction']
df[deseq2_cols].to_parquet(output_path)

# ✅ 수정 후 — annotation 컬럼 포함
all_cols = ['peak_id', 'chr', 'start', 'end', 'gene_name', 'gene_id',
            'annotation', 'distance_to_tss',
            'base_mean', 'log2fc', 'lfcse', 'pvalue', 'adj_pvalue', 'direction']
df[all_cols].rename(columns={'gene_name': 'nearest_gene'}).to_parquet(output_path)
```

---

## 4. 영향 받는 파일

`data/datasets/` 내 모든 DA parquet 파일 (생성일: 2026-04-29):

| 파일명 | 행 수 | 생성일 |
|--------|-------|--------|
| `1D_vs_CONTROL_DA.parquet` | 125,490 | 2026-04-29 |
| `2D_vs_CONTROL_DA.parquet` | 127,660 | 2026-04-29 |
| `3D_vs_CONTROL_DA.parquet` | 128,310 | 2026-04-29 |
| `3H_vs_CONTROL_DA.parquet` | 125,931 | 2026-04-29 |
| `6H_vs_CONTROL_DA.parquet` | 125,689 | 2026-04-29 |

`examples/for-seqviewer/datasets/` 내 동일 파일들도 동일하게 영향 받음.

---

## 5. 현재 워크어라운드 (임시)

`ATACSeqLoader`에 방어 코드가 이미 구현되어 있습니다:

```python
# src/utils/atac_seq_loader.py
# nearest_gene이 peak_id와 동일한 경우(parquet 미완성 데이터) 빈 값으로 처리
if 'nearest_gene' in df.columns and 'peak_id' in df.columns:
    mask = df['nearest_gene'] == df['peak_id']
    if mask.all():
        df['nearest_gene'] = pd.NA
```

→ 버그가 있는 parquet을 로드하면 `nearest_gene`이 모두 NA가 되어 통합 분석에서 매칭 결과 0건이 됩니다.

**현재 사용 가능한 데이터**: `examples/pairwise/` 아래 Excel 원본 파일 (1D, 2D만 존재)은 정상이므로 `ATACSeqLoader`로 직접 로드하면 통합 분석 가능합니다.

---

## 6. 파이프라인 수정 요청 사항

DA 결과를 Parquet으로 내보낼 때 아래 컬럼이 **반드시** 포함되어야 합니다:

### 필수 컬럼 (통합 분석용)

| 컬럼명 (parquet) | 원본 컬럼명 | 용도 |
|-----------------|------------|------|
| `nearest_gene` | `gene_name` | RNA-seq과의 JOIN key |
| `annotation` | `annotation` | Promoter/Intergenic 필터링 |
| `distance_to_tss` | `distance_to_tss` | TSS 기반 promoter 분석 |

### 권장 추가 컬럼 (좌표 정보)

| 컬럼명 (parquet) | 원본 컬럼명 |
|-----------------|------------|
| `chromosome` | `chr` |
| `peak_start` | `start` |
| `peak_end` | `end` |
| `gene_id` | `gene_id` |

### 컬럼명 표준화 규칙

seqviewer의 `ATACSeqLoader`는 다음 매핑을 자동으로 처리합니다:

```
baseMean        → base_mean
log2FoldChange  → log2fc
lfcSE           → lfcse
padj            → adj_pvalue
gene_name       → nearest_gene   ← 이 매핑이 핵심
```

따라서 파이프라인에서 컬럼명을 변환하지 않고 원본 그대로 저장해도 됩니다.

---

## 7. 수정 후 검증 방법

파이프라인 수정 후, 아래 스크립트로 즉시 검증 가능합니다:

```bash
cd cmg-seqviewer
python test_integration_direct.py
```

정상 출력 예시:
```
nearest_gene 샘플 (첫 10개): ['Plk2', 'Gm9946', 'Stab1', ...]  ← 유전자명이어야 함
유효한 nearest_gene 수: 125,490 / 125,490

[concordance 분포]
Not_significant     41,847
ATAC_only            1,810
RNA_only               564
Concordant_Both_UP       6
Concordant_Both_DOWN     5
...
```

`nearest_gene` 값이 `Interval_XXXXX` 형태이면 버그가 수정되지 않은 것입니다.
