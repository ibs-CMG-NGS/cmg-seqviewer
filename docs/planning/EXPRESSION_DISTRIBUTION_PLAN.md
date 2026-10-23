# Expression Distribution (Violin/Box) Plan

- **상태**: pilot 회신 완료, `feat/expression-distribution`에서 v1 구현 중
- **목표 버전**: v1.5.0 (별도 `expression_distribution` 타입)
- **작성일**: 2026-10-22
- **관련 문서**: [Expression Distribution 도움말](../user/help/21-expression-distribution.md) · [Expression Summary](../user/help/22-expression-summary.md) · [파이프라인 연동](../developer/pipeline-integration.md) · [분석팀 요청 초안](EXPRESSION_DISTRIBUTION_ANALYSIS_TEAM_REQUEST.md)

---

## 0. Pilot Confirmation (2026-10-22)

분석팀이 `expression_distribution` pilot bundle을 제공했다.

- Dataset: Dowsett10xnuc (HypoMap subset)
- Genes: 30 marker genes
- Cell types: 43
- Samples: 6 biological samples (4 Normal chow, 2 Fasted)
- Rows: 7,740 (gene × cell_type × sample, `n_cells >= 10`)
- Layout: `pseudobulk`, `sample_unit: "biological_replicate"`
- Main: `hypomap_Dowsett10xnuc_pseudobulk.parquet` (~111 KB)
- Companions: `gene_index`, `cell_type_summary`
- Full bundle: analysis 69 + distribution 1 = 70 datasets, **70/70 imported**
  in the implementation branch (v1.4.0 would import 69/70).

확정된 핵심 답변:

- `sample`은 biological replicate이며, HypoMap에 별도 `donor` 컬럼은 없다.
- per-sample pseudobulk export 가능. quantile/cell-level도 협의 가능하지만
  pilot에는 포함되지 않았다.
- 조건 간 통계 검정은 pseudobulk DE 결과를 별도로 사용한다 (이 뷰는 descriptive).
- 전체 57k gene은 lazy query/전달 크기 협의 후 결정한다.

### 0.1 Implementation status (`feat/expression-distribution`)

- ✅ `DatasetType.EXPRESSION_DISTRIBUTION` + alias
- ✅ pseudobulk/quantile loader (`expression_distribution_loader.py`)
- ✅ manifest `distribution_schema`, `sample_count`, companion import
- ✅ import-fold auto-detect (`*_pseudobulk.parquet` + companions)
- ✅ DB load + full bundle **70/70 imported**
- ✅ CLI `load --type expression_distribution --json`
- ✅ violin/box/strip + condition/dataset/sample grouping dialog
- ✅ Export Data / Export Bundle / Pin to Tab
- ✅ F1 help section 21 + pipeline integration §9.9
- ⏳ cell-level on-demand store (Phase 3)
- ⏳ full-atlas lazy DuckDB query (v2)

---

## 1. Goal

`expression_summary`의 mean/pct/n_cells 집계 뷰는 **분포 정보**(이봉성, 긴 꼬리,
세포 간 이질성)를 잃는다. 선택한 gene에 대해 cell type별 **violin/box/strip**
분포를 보여주는 별도 뷰를 추가한다.

- 기존 `expression_summary`(dot plot/heatmap)는 그대로 유지
- 분포 뷰는 **별도 dataset type(`expression_distribution`)** 으로 분리
- 집계값으로 violin을 흉내 내지 않는다
- 선택한 gene/cell type만 query하고, 전체 store를 pandas로 로드하지 않는다

## 2. Non-goals (v1)

- 전체 57k gene × 전체 cell의 cell-level store를 앱에 상주시키는 것
- mean/pct만으로 violin을 합성하는 것
- 조건 간 통계 검정을 cell 단위로 수행하는 것 (pseudo-replication)
- 분포 뷰의 MCP tool 노출 (후속)

## 3. Current State

| 영역 | 현재 | 판단 |
|------|------|------|
| `expression_summary` | wide mean/pct + gene_index/cell_type_summary | 집계 뷰. 분포 정보 없음 |
| Dot plot/heatmap | `plots/expression_dot.py`, `plots/heatmap.py` | mean/pct 시각화 |
| DB | parquet 전체를 pandas로 로드 | 분포 데이터에는 부적합 |
| DuckDB | 미사용 (`pyarrow`만) | 분포 query에는 lazy backend 필요 |
| Manifest | `expression_schema` | `distribution_schema` 추가 필요 |

## 4. Recommended Data Strategy

| 우선순위 | 데이터 | 가능한 plot | 장점 | 제약 |
|---|---|---|---|---|
| **1** | **per-sample pseudobulk** | violin/box/strip (replicate 분포) | 크기가 상대적으로 작고 조건/replicate 비교에 적절 | cell 단위 heterogeneity는 아님 |
| **2** | **cell-level on-demand** | true violin/strip | 진짜 population heterogeneity | 선택 gene만 가능, DuckDB/Arrow 필수 |
| **3** | **quantile summary** | box/range (violin-like) | 데이터가 작고 구현 쉬움 | 진짜 violin 아님 |

> **중요:** HypoMap에 biological replicate가 없고 18개 dataset만 있다면,
> per-sample pseudobulk violin은 “dataset 간 이질성”을 보여주는 descriptive
> plot이다. 조건 비교/통계 검정에는 replicate가 필요하다.

## 5. Bundle-First Integration

분석팀은 이미 `viewer_export`로 `seqviewer_manifest.json` + `datasets/` 번들을
생성하고 있으므로, **별도 전달 포맷을 만들지 않고 기존 번들에
`expression_distribution` entry를 추가**하는 것을 요청한다.

```
export/seqviewer/
├── seqviewer_manifest.json
└── datasets/
    ├── hypomap_C185_pseudobulk.parquet
    ├── hypomap_C185_distribution_gene_index.parquet
    └── hypomap_C185_cell_type_summary.parquet
```

### Manifest 예시

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

- `dataset_type`은 **`expression_distribution`**
- `file_path`은 `datasets/<filename>` 또는 파일명
- 기존 `viewer_export`의 manifest merge 로직에 entry만 추가
- `gene_index`/`cell_type_summary`는 기존 expression summary companion 재사용 가능

## 6. Data Schemas

### 6.1 per-sample pseudobulk (1순위)

```text
gene_id, gene_name, cell_type, sample, dataset, condition,
n_cells, n_expressing, pct_expressing, mean_expression, mean_counts
```

- 한 행 = gene × cell type × sample
- violin/box의 x = cell type (또는 condition), group = sample/dataset/condition
- `sample`이 biological replicate인지 반드시 명확히 해야 함

### 6.2 cell-level on-demand (2순위)

```text
gene_id, cell_id, cell_type, dataset, sample, expression, counts
```

- 선택한 gene(예: 1–20개)만 query
- 356k cells × 20 genes ≈ 7M rows → DuckDB/Arrow로 처리
- 전체 gene × 전체 cell은 비현실적
- gene-partitioned parquet 또는 long parquet + predicate pushdown 권장

### 6.3 quantile summary (3순위)

```text
gene_id, gene_name, cell_type, dataset, condition,
n_cells, mean_expression, sd_expression, pct_expressing,
p10, p25, median, p75, p90
```

- violin 대신 **box/range plot**으로 표시
- UI 라벨은 `Distribution (quantiles)`로 표기

## 7. Viewer Architecture

```
Manifest (distribution_schema)
        │
        ▼
ExpressionDistributionService  (DuckDB/Arrow lazy query)
        │  selected genes / cell types / group_by
        ▼
Gene Expression Distribution Dialog
        │
        ├── Violin / Box / Strip renderer (Qt-free)
        ├── Export Data / Bundle / Pin
        └── Gene/cell-type selection, grouping, filters
```

- `DatasetType.EXPRESSION_DISTRIBUTION` 추가
- pseudobulk/quantile은 dataset으로 등록
- cell-level은 `CellLevelStore`로 등록하고 pandas 전체 로드 금지
- DuckDB는 **optional extra** (`[distribution]`)로 추가 검토
  - pyarrow dataset + filter로도 가능하지만 group-by/quantile/sampling은 DuckDB가 단순
- `plots/expression_violin.py` 신규 renderer (Qt 비의존)
- `plots/registry.py`에 `expression_violin` 등록 (bundle/pin 지원)
- CLI `--type expression_distribution` 및 `load --json` 확장 (구현 후)

## 8. UI/UX

메뉴:

```
Visualization → 🧬 Single-cell RNA-seq
├── 🧫 Cell-Type Composition
├── 🧬 Gene × Cell-Type Expression
└── 🎻 Gene Expression Distribution   ← 신규
```

Dialog:

- **Gene search**: distribution gene_index 기반. 필터 시트에서 열면 해당 gene list로 제한
- **Cell types**: top 10 by mean 또는 전체; 세션 상태 복원
- **Group by**: `sample` / `dataset` / `condition` (데이터에 있는 컬럼만)
- **Plot type**: Violin / Box / Strip / Box+points
  - quantile layout이면 Violin 비활성, `Box/Range`만
- **Filters**: min `n_cells`, min `pct_expressing`, max cells per group (downsampling)
- **Display**: log scale, y-range, split by condition/dataset, colors, point size/alpha
- **Export Data / Export Bundle / Pin to Tab**
- **Progress/timeout**: 대량 query 진행 표시와 취소

## 9. Performance / Limits

- 전체 store를 pandas로 로드하지 않는다
- gene/cell type 필터를 query 시점에 적용 (predicate pushdown)
- cell-level은 group당 최대 N개 cell로 downsample (기본 1,000; seed 고정)
- pseudobulk/quantile도 선택 gene만 조회
- 예상 규모:
  - cell-level 선택 20 genes × 356k cells ≈ 7M rows → query 수 초
  - 전체 gene cell-level 불가
  - pseudobulk 전체 atlas는 수천만 행 가능 → subset/선택 gene/lazy query 필수
- 앱의 기존 DB/pandas 경로와 분리해 분포 뷰만 lazy로 동작

## 10. Analysis Team Confirmation

상세 요청은 [분석팀 요청 초안](EXPRESSION_DISTRIBUTION_ANALYSIS_TEAM_REQUEST.md)에 정리했다.
핵심 확인 항목:

1. HypoMap의 **sample/replicate 정의** (donor/replicate vs 18 datasets)
2. **per-sample pseudobulk** export 가능 여부
3. pseudobulk가 어렵다면 **quantile summary** 가능 여부
4. 선택 gene에 한한 **cell-level** export 가능 여부
5. gene 범위 (전체 57k vs marker/selected panel)
6. `condition`, `sample`, `dataset`, `donor` 메타데이터 포함 여부
7. **pilot bundle** (1 dataset + 20–50 marker genes) 제공 가능 여부
8. 기존 `viewer_export`에 `expression_distribution` entry 추가 제약
9. 조건 비교/통계 검정이 목적인지, descriptive violin이면 충분한지
10. pilot 파일 크기/전달 위치

## 11. Phases & Estimates

| Phase | 내용 | 선행 조건 | 예상 |
|---|---|---|---|
| 0 | 분석팀 회신 + pilot bundle + schema 확정 | 분석팀 확인 | 1주 |
| 1 | `expression_distribution` 타입 + pseudobulk/quantile loader + DuckDB service | pilot | 1–2주 |
| 2 | Violin/box/strip renderer + dialog + gene/cell type/group UI | Phase 1 | 1–2주 |
| 3 | cell-level store + on-demand query + downsampling | cell-level pilot | 2–3주 |
| 4 | Export/Bundle/Pin, F1 help, pipeline docs, tests | Phase 2 | 1주 |

Phase 1–2만으로 pseudobulk/quantile 분포 뷰를 먼저 출시하고,
cell-level true violin은 Phase 3로 분리한다.

## 12. Testing & Docs

- `test_distribution_service.py`: pseudobulk/quantile/cell-level query, 필터, downsample
- `test_expression_distribution_dialog.py`: violin/box 모드, gene/cell type 선택, 상태 복원
- `test_plots_expression_violin.py`: Agg 렌더 smoke
- manifest/DB import 테스트
- F1 도움말 신규 섹션 (Tips/FAQ 앞), `pipeline-integration.md`에 `distribution_schema` 규격 추가
- 성능 테스트: 1M-row synthetic store에서 선택 gene query 시간 측정

## 13. Decisions / Next Actions

- 확정 필요:
  - `expression_distribution` 타입명
  - `distribution_schema` 필드명
  - DuckDB optional extra 여부
- 분석팀 회신 1·2·5·9번이 확정되면 pilot bundle 스펙 고정
- 다음 액션:
  1. 분석팀에 [요청 초안](EXPRESSION_DISTRIBUTION_ANALYSIS_TEAM_REQUEST.md) 전달
  2. pilot bundle 수령 후 Phase 1 schema 확정
  3. viewer 구현 착수
