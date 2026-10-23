# [요청] cmg-seqviewer expression_distribution (violin/box) 번들 export 및 pilot 데이터

- **수신**: scRNA-seq 3차 분석 파이프라인 담당
- **발신**: cmg-seqviewer 개발팀
- **관련 계획**: [Expression Distribution Plan](EXPRESSION_DISTRIBUTION_PLAN.md)
- **목적**: mean/pct 집계만으로는 알 수 없는 cell type별 발현 분포(violin/box)를
  viewer에서 보여주기 위한 `expression_distribution` 번들 export 요청 및 스키마 확인

---

## 1. 배경

현재 `expression_summary` 번들은 gene × cell type **집계값**(`mean_expression`,
`pct_expressing`, `n_cells`)을 제공합니다. Dot plot/heatmap은 mean과 detection
비율을 잘 보여주지만, **분포의 모양**(이봉성, 긴 꼬리, 세포 간 이질성)은 알 수
없습니다.

viewer에 **violin/box/strip 분포 뷰**를 추가하려고 하며, 기존 `viewer_export`
번들 파이프라인을 그대로 사용해 `expression_distribution` dataset을 추가하는
방향을 제안드립니다.

## 2. 요청 사항

1. 기존 `seqviewer_manifest.json` + `datasets/` 번들에
   **`dataset_type: "expression_distribution"`** entry를 추가해 주세요.
2. 우선 **pilot bundle**을 먼저 제공해 주세요.
   - 1개 dataset (예: Dowsett10xnuc 또는 C66)
   - 20–50개 marker genes (예: Gfap, Agrp, Pomc, Sst, ...)
   - 전체 cell type
   - 가능하면 **per-sample pseudobulk**, 어려우면 **quantile summary**
3. 아래 스키마/필드명을 확인해 주세요.
4. pilot bundle을 viewer에서 violin/box UI와 성능으로 검증한 뒤, 전체 atlas
   export 범위를 협의하겠습니다.

## 3. 권장 데이터 형식

### 3.1 1순위: per-sample pseudobulk

```text
gene_id, gene_name, cell_type, sample, dataset, condition,
n_cells, n_expressing, pct_expressing, mean_expression, mean_counts
```

- 한 행 = gene × cell type × sample
- violin/box의 분포 단위 = sample (replicate)
- `sample`이 biological replicate인지, dataset 단위인지 명확히 표시 부탁드립니다.

### 3.2 2순위: quantile summary

```text
gene_id, gene_name, cell_type, dataset, condition,
n_cells, mean_expression, sd_expression, pct_expressing,
p10, p25, median, p75, p90
```

- viewer는 violin 대신 **box/range** plot으로 표시합니다.

### 3.3 3순위: cell-level (선택 gene 한정)

```text
gene_id, cell_id, cell_type, dataset, sample, expression, counts
```

- 선택한 gene(예: 1–20개)에 대해서만 export
- gene-partitioned parquet 또는 long parquet + predicate pushdown 권장
- 전체 gene × 전체 cell은 viewer가 상주 로드하지 않습니다.

## 4. Bundle Manifest 예시

```json
{
  "schema_version": "1.0",
  "datasets": [
    {
      "dataset_id": "...",
      "alias": "HypoMap C185 pseudobulk distribution",
      "file_path": "hypomap_C185_pseudobulk.parquet",
      "dataset_type": "expression_distribution",
      "organism": "Mus musculus",
      "distribution_schema": {
        "schema_version": "1.0",
        "layout": "pseudobulk",
        "gene_id_type": "symbol",
        "cell_type_column": "cell_type",
        "sample_column": "sample",
        "group_columns": ["condition", "dataset"],
        "value_column": "mean_expression",
        "pct_column": "pct_expressing",
        "n_cells_column": "n_cells",
        "companion_files": {
          "gene_index": "hypomap_C185_distribution_gene_index.parquet",
          "cell_type_summary": "hypomap_C185_cell_type_summary.parquet"
        }
      }
    }
  ]
}
```

- `file_path`은 `datasets/<filename>` 또는 파일명
- 기존 `viewer_export`의 manifest merge 로직에 entry만 추가하는 형태
- `gene_index`/`cell_type_summary`는 기존 expression summary companion 재사용 가능

## 5. 확인 요청 (회신 부탁드립니다)

| # | 질문 | 비고 |
|---|------|------|
| 1 | HypoMap의 **sample/replicate 정의**가 무엇인가요? donor/replicate가 있나요, 아니면 18개 dataset이 사실상 sample인가요? | violin 해석의 핵심 |
| 2 | **per-sample pseudobulk**를 export할 수 있나요? | 1순위 |
| 3 | pseudobulk가 어렵다면 **quantile summary**(p10/p25/median/p75/p90)를 줄 수 있나요? | 2순위 fallback |
| 4 | 선택 gene에 한해 **cell-level** 데이터를 줄 수 있나요? (gene-partitioned parquet 등) | 3순위 |
| 5 | gene 범위는 **전체 57k**인가요, marker/selected panel인가요? | 전체면 lazy query 필수 |
| 6 | `condition`, `sample`, `dataset`, `donor` 메타데이터가 parquet에 포함되나요? | grouping/split violin |
| 7 | **pilot bundle**(1 dataset + 20–50 marker genes)을 먼저 제공할 수 있나요? | UI/성능 검증 |
| 8 | 기존 `viewer_export`에 `expression_distribution` entry를 추가하는 데 제약이 있나요? | manifest merge |
| 9 | 조건 비교/통계 검정이 목적인가요, descriptive violin이면 충분한가요? | 통계 목적이면 pseudobulk 필수 |
| 10 | pilot 파일 크기/전달 위치는 어떻게 할까요? | 전송/검증 |

## 6. Viewer 쪽 후속 작업 (참고)

- `DatasetType.EXPRESSION_DISTRIBUTION` 및 `distribution_schema` 추가
- pseudobulk/quantile은 DuckDB/Arrow **lazy query**로 선택 gene만 조회
- cell-level은 `CellLevelStore`로 등록하고 전체 pandas 로드 금지
- UI: `Visualization → 🧬 Single-cell RNA-seq → 🎻 Gene Expression Distribution`
- 구현 후 `cmg-seqviewer-cli load <file> --type expression_distribution --json`으로
  bundle 검증을 제공할 예정입니다. (현재는 미구현)

## 7. 다음 단계

1. 본 요청에 대한 가능/불가 및 pilot bundle 제공 일정 회신
2. pilot bundle schema 검토 후 `distribution_schema` 필드 확정
3. viewer 구현 착수 (Phase 1–2)
4. 전체 atlas export 범위 및 성능 협의

감사합니다.
