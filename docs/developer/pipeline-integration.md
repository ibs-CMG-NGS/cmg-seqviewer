# Pipeline Integration Guide

RNA-seq DE/GO 분석 파이프라인 출력물을 cmg-seqviewer에 바로 연결하기 위한 규격 문서입니다.

---

## 목차

1. [개요](#1-개요)
2. [출력 디렉토리 구조](#2-출력-디렉토리-구조)
3. [DE 결과 parquet 규격](#3-de-결과-parquet-규격)
4. [GO 결과 parquet 규격](#4-go-결과-parquet-규격)
5. [metadata.json 규격](#5-metadatajson-규격)
6. [앱 연결 방법](#6-앱-연결-방법)
7. [R 파이프라인 구현 예시](#7-r-파이프라인-구현-예시)
8. [주의사항](#8-주의사항)
9. [`seqviewer_manifest.json` 규격](#9-seqviewer_manifestjson-규격)

---

## 1. 개요

### 현재 워크플로우 (문제점)

```
파이프라인 출력 (Excel / CSV)
        ↓
  앱에서 파일 수동 불러오기
        ↓
  컬럼명 매핑 (ColumnMapper dialog)  ← 매번 반복
        ↓
  DB import
```

파이프라인 출력 구조가 고정되어 있음에도 불구하고 앱에서 컬럼 매핑을 매번 반복해야 하는 마찰이 있습니다.

### 개선된 워크플로우

```
파이프라인 출력 (표준 컬럼명 parquet + metadata.json)
        ↓
  data/datasets/ 폴더에 복사
        ↓
  앱 재시작 → 자동 인식  ← 컬럼 매핑 불필요
```

파이프라인 마지막 단계에서 **표준 컬럼명 parquet** 와 **metadata.json** 을 함께 생성하면, 앱은 컬럼 매핑 없이 즉시 데이터를 인식합니다.

---

## 2. 출력 디렉토리 구조

파이프라인은 아래 구조로 출력해야 합니다.

```
output/
├── metadata.json              ← 필수: 앱 인식의 핵심
└── datasets/
    ├── {alias}_de_{uuid8}.parquet    ← DE 결과
    └── {alias}_go_{uuid8}.parquet   ← GO 결과
```

### 파일명 규칙

```
{alias_slug}_{uuid8}.parquet
```

| 항목 | 설명 | 예시 |
|------|------|------|
| `alias_slug` | alias를 영숫자/한글/언더스코어만 남긴 문자열 (최대 40자) | `MonTG_vs_nMonTF_de` |
| `uuid8` | UUID v4 앞 8자리 (충돌 방지용) | `b8cc6614` |

> **주의**: 파일명에 공백, `-`, `(`, `)` 등 특수문자는 `_`로 변환해야 합니다.

---

## 3. DE 결과 parquet 규격

### 필수 컬럼 (반드시 포함)

| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| `gene_id` | `string` | 유전자 식별자 (ENSEMBL ID 또는 symbol) |
| `symbol` | `string` | 유전자 심볼 (사람이 읽을 수 있는 이름) |
| `log2fc` | `float64` | Log2 Fold Change |
| `adj_pvalue` | `float64` | FDR (Benjamini-Hochberg adjusted p-value) |

> `symbol` 컬럼이 없을 경우 앱이 `gene_id` 값을 자동으로 복사해 사용합니다 (fallback). 가능하면 명시적으로 포함하는 것을 권장합니다.

### 권장 컬럼 (있으면 시각화에 활용됨)

| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| `base_mean` | `float64` | 전체 샘플 평균 발현량 (DESeq2: baseMean) |
| `pvalue` | `float64` | Raw p-value |
| `lfcse` | `float64` | Log2FC standard error (DESeq2: lfcSE) |
| `stat` | `float64` | Test statistic (DESeq2: stat) |

### DESeq2 출력 컬럼 대응표

| DESeq2 컬럼명 | 표준 컬럼명 | 비고 |
|---------------|------------|------|
| rownames (ENSEMBL ID) | `gene_id` | |
| gene_symbol 또는 별도 컬럼 | `symbol` | |
| `baseMean` | `base_mean` | |
| `log2FoldChange` | `log2fc` | apeglm shrinkage 후 권장 |
| `lfcSE` | `lfcse` | |
| `stat` | `stat` | |
| `pvalue` | `pvalue` | |
| `padj` | `adj_pvalue` | |

### 예시 데이터 (상위 3행)

```
gene_id          symbol    base_mean  log2fc   lfcse   stat    pvalue      adj_pvalue
ENSMUSG00000001  Actb      1523.4     -1.82    0.12    -15.2   1.2e-52     3.4e-49
ENSMUSG00000002  Gapdh     2841.1      0.43    0.09     4.8    1.6e-06     1.2e-04
ENSMUSG00000003  Tnf        234.7      3.21    0.21    15.3    8.9e-53     3.1e-49
```

---

## 4. GO 결과 parquet 규격

### 필수 컬럼 (반드시 포함)

| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| `term_id` | `string` | GO ID 또는 KEGG ID (예: `GO:0006955`, `mmu04110`) |
| `description` | `string` | Term 설명 (예: `immune response`) |
| `gene_count` | `int64` | 해당 term에 속한 유전자 수 |
| `fdr` | `float64` | BH-adjusted p-value |

### 권장 컬럼

| 컬럼명 | 타입 | 설명 | 예시 |
|--------|------|------|------|
| `pvalue` | `float64` | Raw p-value | `0.0001` |
| `qvalue` | `float64` | Q-value | `0.0023` |
| `gene_symbols` | `string` | 유전자 심볼 목록 (`/` 구분자) | `"Tnf/Il6/Cxcl10"` |
| `gene_ratio` | `string` | `"분자/분모"` 형식 | `"15/342"` |
| `bg_ratio` | `string` | `"분자/분모"` 형식 | `"200/20000"` |
| `direction` | `string` | 발현 방향 | `UP` / `DOWN` / `TOTAL` |
| `ontology` | `string` | Ontology 종류 | `BP` / `MF` / `CC` / `KEGG` |

### clusterProfiler 출력 컬럼 대응표

| clusterProfiler 컬럼명 | 표준 컬럼명 | 비고 |
|------------------------|------------|------|
| `ID` | `term_id` | |
| `Description` | `description` | |
| `Count` | `gene_count` | |
| `pvalue` | `pvalue` | |
| `p.adjust` | `fdr` | |
| `qvalue` | `qvalue` | |
| `geneID` | `gene_symbols` | `/`로 구분된 문자열 그대로 사용 가능 |
| `GeneRatio` | `gene_ratio` | |
| `BgRatio` | `bg_ratio` | |

> `direction` 과 `ontology` 컬럼은 clusterProfiler 출력에 없습니다. 파이프라인에서 직접 추가해야 합니다.

---

## 5. metadata.json 규격

### 전체 구조

```json
{
  "version": "1.0",
  "last_updated": "2026-03-10T09:00:00",
  "datasets": [
    { ... },
    { ... }
  ]
}
```

### 데이터셋 항목 (datasets 배열의 각 원소)

| 필드명 | 타입 | 필수 | 설명 |
|--------|------|------|------|
| `dataset_id` | `string` | ✅ | UUID v4 (파이프라인에서 생성, 파일명의 앞 8자리와 일치해야 함) |
| `alias` | `string` | ✅ | 앱에 표시될 이름 (예: `"MonTG vs nMonTF DE"`) |
| `original_filename` | `string` | ✅ | 원본 파일명 (참고용) |
| `dataset_type` | `string` | ✅ | `"differential_expression"` 또는 `"go_analysis"` |
| `file_path` | `string` | ✅ | parquet 파일명 (경로 아님, 파일명만) |
| `row_count` | `int` | ✅ | 전체 행 수 |
| `gene_count` | `int` | ✅ | 유전자 수 (DE) 또는 0 (GO) |
| `significant_genes` | `int` | ✅ | padj < 0.05 유전자 수 (DE) 또는 0 (GO) |
| `import_date` | `string` | ✅ | ISO 8601 형식 (예: `"2026-03-10T09:00:00"`) |
| `experiment_condition` | `string` | ☑️ 권장 | 비교 조건 (예: `"MonTG vs nMonTF"`) |
| `organism` | `string` | ☑️ 권장 | 생물종 (예: `"Mus musculus"`) |
| `cell_type` | `string` | 선택 | 세포 타입 (예: `"Primary macrophage"`) |
| `tissue` | `string` | 선택 | 조직 (예: `"Liver"`) |
| `timepoint` | `string` | 선택 | 시간점 (예: `"24h post-treatment"`) |
| `notes` | `string` | 선택 | 자유 메모 (예: `"DESeq2, apeglm shrinkage"`) |
| `tags` | `string[]` | 선택 | 검색 태그 (예: `["DESeq2", "MonTG"]`) |

### 완성 예시

```json
{
  "version": "1.0",
  "last_updated": "2026-03-10T09:00:00",
  "datasets": [
    {
      "dataset_id": "b8cc6614-30aa-498b-bd4e-7ea0f4e940ef",
      "alias": "MonTG vs nMonTF DE",
      "original_filename": "MonTG_vs_nMonTF_de.parquet",
      "dataset_type": "differential_expression",
      "experiment_condition": "MonTG vs nMonTF",
      "cell_type": "Primary macrophage",
      "organism": "Mus musculus",
      "tissue": "",
      "timepoint": "",
      "row_count": 15000,
      "gene_count": 15000,
      "significant_genes": 342,
      "import_date": "2026-03-10T09:00:00",
      "file_path": "MonTG_vs_nMonTF_de_b8cc6614.parquet",
      "notes": "DESeq2 v1.42, apeglm LFC shrinkage",
      "tags": ["DESeq2", "MonTG", "nMonTF", "macrophage"]
    },
    {
      "dataset_id": "6dac2c5c-1234-5678-abcd-ef0123456789",
      "alias": "MonTG vs nMonTF GO",
      "original_filename": "MonTG_vs_nMonTF_go.parquet",
      "dataset_type": "go_analysis",
      "experiment_condition": "MonTG vs nMonTF",
      "cell_type": "Primary macrophage",
      "organism": "Mus musculus",
      "tissue": "",
      "timepoint": "",
      "row_count": 850,
      "gene_count": 0,
      "significant_genes": 0,
      "import_date": "2026-03-10T09:00:00",
      "file_path": "MonTG_vs_nMonTF_go_6dac2c5c.parquet",
      "notes": "clusterProfiler v4.10, enrichGO (BP/MF/CC) + enrichKEGG",
      "tags": ["clusterProfiler", "GO", "KEGG", "MonTG", "nMonTF"]
    }
  ]
}
```

---

## 6. 앱 연결 방법

### 방법 A: 직접 복사 (가장 간단)

```
파이프라인 output/
    ├── metadata.json
    └── datasets/
        ├── MonTG_vs_nMonTF_de_b8cc6614.parquet
        └── MonTG_vs_nMonTF_go_6dac2c5c.parquet
```

위 파일들을 앱의 `data/` 폴더에 복사합니다.

```
# Windows
data\
    metadata.json       ← output/metadata.json 복사 (기존 항목과 병합)
    datasets\
        *.parquet       ← output/datasets/*.parquet 복사
```

앱을 재시작하면 자동으로 인식됩니다.

> **metadata.json 병합 주의**: 기존 `data/metadata.json`이 있다면 `datasets` 배열을 **합쳐야** 합니다. 덮어쓰면 기존 데이터셋이 사라집니다.

### 방법 B: export_dataset() 활용

앱에서 이미 DB에 등록된 데이터셋을 `export_dataset(dataset_id, export_dir)`로 내보낸 뒤 다른 PC에 배포합니다. metadata.json 병합이 자동으로 처리됩니다.

---

## 7. R 파이프라인 구현 예시

파이프라인 마지막 단계에 아래 함수를 추가합니다.

```r
library(arrow)      # parquet 저장
library(jsonlite)   # metadata.json 생성
library(dplyr)

# ─────────────────────────────────────────────────────────────
# 헬퍼 함수
# ─────────────────────────────────────────────────────────────

#' alias 문자열을 파일명 안전 slug로 변환
make_alias_slug <- function(alias, max_len = 40) {
  slug <- gsub("[^\\w가-힣]+", "_", alias, perl = TRUE)
  slug <- gsub("^_|_$", "", slug)
  substr(slug, 1, max_len)
}

#' UUID v4 생성 (R base 기준)
new_uuid <- function() {
  hex <- paste0(sample(c(0:9, letters[1:6]), 32, replace = TRUE), collapse = "")
  paste(
    substr(hex,  1,  8),
    substr(hex,  9, 12),
    paste0("4", substr(hex, 14, 16)),           # version 4
    paste0(sample(c("8","9","a","b"), 1), substr(hex, 18, 20)),  # variant
    substr(hex, 21, 32),
    sep = "-"
  )
}

# ─────────────────────────────────────────────────────────────
# DE 결과 저장
# ─────────────────────────────────────────────────────────────

save_de_for_seqviewer <- function(
    de_df,          # DESeq2 results() 후 data.frame으로 변환한 것
    alias,          # 앱에 표시될 이름 (예: "MonTG vs nMonTF DE")
    output_dir,     # 출력 폴더 경로
    organism   = "Mus musculus",
    cell_type  = "",
    condition  = "",
    notes      = "",
    tags       = character(0)
) {
  # 컬럼 이름 표준화
  de_std <- de_df %>%
    rename(
      gene_id    = any_of(c("gene_id", "ensembl_id", "GeneID")),
      symbol     = any_of(c("symbol", "gene_name", "external_gene_name")),
      base_mean  = any_of(c("base_mean", "baseMean")),
      log2fc     = any_of(c("log2fc", "log2FoldChange")),
      lfcse      = any_of(c("lfcse", "lfcSE")),
      stat       = any_of(c("stat", "stat")),
      pvalue     = any_of(c("pvalue", "pvalue")),
      adj_pvalue = any_of(c("adj_pvalue", "padj"))
    )

  # symbol 없으면 gene_id 복사 (앱 fallback과 동일한 로직)
  if (!"symbol" %in% colnames(de_std)) {
    de_std$symbol <- de_std$gene_id
  }

  # UUID 및 파일명 생성
  uid       <- new_uuid()
  uid8      <- substr(gsub("-", "", uid), 1, 8)
  slug      <- make_alias_slug(alias)
  filename  <- paste0(slug, "_", uid8, ".parquet")

  # 출력 폴더 생성
  datasets_dir <- file.path(output_dir, "datasets")
  dir.create(datasets_dir, recursive = TRUE, showWarnings = FALSE)

  # parquet 저장
  write_parquet(de_std, file.path(datasets_dir, filename))

  # metadata 항목 반환
  list(
    dataset_id         = uid,
    alias              = alias,
    original_filename  = filename,
    dataset_type       = "differential_expression",
    experiment_condition = condition,
    cell_type          = cell_type,
    organism           = organism,
    tissue             = "",
    timepoint          = "",
    row_count          = nrow(de_std),
    gene_count         = nrow(de_std),
    significant_genes  = sum(de_std$adj_pvalue < 0.05, na.rm = TRUE),
    import_date        = format(Sys.time(), "%Y-%m-%dT%H:%M:%S"),
    file_path          = filename,
    notes              = notes,
    tags               = as.list(tags)
  )
}

# ─────────────────────────────────────────────────────────────
# GO 결과 저장
# ─────────────────────────────────────────────────────────────

save_go_for_seqviewer <- function(
    go_df,          # clusterProfiler enrichGO/enrichKEGG 결과를 as.data.frame()한 것
    alias,          # 앱에 표시될 이름 (예: "MonTG vs nMonTF GO")
    output_dir,
    direction  = "TOTAL",   # "UP" / "DOWN" / "TOTAL"
    ontology   = "BP",      # "BP" / "MF" / "CC" / "KEGG"
    organism   = "Mus musculus",
    cell_type  = "",
    condition  = "",
    notes      = "",
    tags       = character(0)
) {
  # 컬럼 이름 표준화
  go_std <- go_df %>%
    rename(
      term_id     = any_of(c("term_id", "ID")),
      description = any_of(c("description", "Description")),
      gene_count  = any_of(c("gene_count", "Count")),
      pvalue      = any_of(c("pvalue", "pvalue")),
      fdr         = any_of(c("fdr", "p.adjust")),
      qvalue      = any_of(c("qvalue", "qvalue")),
      gene_symbols = any_of(c("gene_symbols", "geneID")),
      gene_ratio  = any_of(c("gene_ratio", "GeneRatio")),
      bg_ratio    = any_of(c("bg_ratio",   "BgRatio"))
    ) %>%
    mutate(
      direction = direction,
      ontology  = ontology
    )

  # UUID 및 파일명 생성
  uid       <- new_uuid()
  uid8      <- substr(gsub("-", "", uid), 1, 8)
  slug      <- make_alias_slug(alias)
  filename  <- paste0(slug, "_", uid8, ".parquet")

  datasets_dir <- file.path(output_dir, "datasets")
  dir.create(datasets_dir, recursive = TRUE, showWarnings = FALSE)

  write_parquet(go_std, file.path(datasets_dir, filename))

  list(
    dataset_id         = uid,
    alias              = alias,
    original_filename  = filename,
    dataset_type       = "go_analysis",
    experiment_condition = condition,
    cell_type          = cell_type,
    organism           = organism,
    tissue             = "",
    timepoint          = "",
    row_count          = nrow(go_std),
    gene_count         = 0L,
    significant_genes  = 0L,
    import_date        = format(Sys.time(), "%Y-%m-%dT%H:%M:%S"),
    file_path          = filename,
    notes              = notes,
    tags               = as.list(tags)
  )
}

# ─────────────────────────────────────────────────────────────
# metadata.json 저장 (기존 파일이 있으면 병합)
# ─────────────────────────────────────────────────────────────

save_metadata_json <- function(dataset_entries, output_dir) {
  meta_path <- file.path(output_dir, "metadata.json")

  existing_datasets <- list()
  if (file.exists(meta_path)) {
    existing <- fromJSON(meta_path, simplifyVector = FALSE)
    existing_datasets <- existing$datasets
  }

  # dataset_id 기준 중복 제거 (새 항목 우선)
  new_ids     <- sapply(dataset_entries, `[[`, "dataset_id")
  kept_old    <- Filter(function(x) !x$dataset_id %in% new_ids, existing_datasets)
  all_datasets <- c(kept_old, dataset_entries)

  metadata <- list(
    version      = "1.0",
    last_updated = format(Sys.time(), "%Y-%m-%dT%H:%M:%S"),
    datasets     = all_datasets
  )

  write_json(metadata, meta_path, pretty = TRUE, auto_unbox = TRUE)
  message("Saved metadata.json: ", length(all_datasets), " dataset(s)")
}

# ─────────────────────────────────────────────────────────────
# 사용 예시
# ─────────────────────────────────────────────────────────────

# output_dir <- "output/seqviewer"
#
# # 1. DE 결과 저장
# entry_de <- save_de_for_seqviewer(
#   de_df     = as.data.frame(dds_results),
#   alias     = "MonTG vs nMonTF DE",
#   output_dir = output_dir,
#   organism  = "Mus musculus",
#   cell_type = "Primary macrophage",
#   condition = "MonTG vs nMonTF",
#   notes     = "DESeq2 v1.42, apeglm LFC shrinkage",
#   tags      = c("DESeq2", "MonTG", "nMonTF")
# )
#
# # 2. GO 결과 저장 (UP regulated 유전자 기반)
# entry_go_up <- save_go_for_seqviewer(
#   go_df     = as.data.frame(ego_up),
#   alias     = "MonTG vs nMonTF GO UP",
#   output_dir = output_dir,
#   direction = "UP",
#   ontology  = "BP",
#   organism  = "Mus musculus",
#   condition = "MonTG vs nMonTF",
#   notes     = "clusterProfiler v4.10, enrichGO BP, UP-regulated genes",
#   tags      = c("GO", "BP", "UP", "MonTG")
# )
#
# # 3. metadata.json 저장 (병합)
# save_metadata_json(
#   dataset_entries = list(entry_de, entry_go_up),
#   output_dir      = output_dir
# )
```

---

## 8. 주의사항

### parquet 파일명과 metadata.json의 `file_path` 일치

`metadata.json`의 `file_path` 필드는 반드시 실제 parquet 파일명과 동일해야 합니다 (경로 포함하지 않음, 파일명만).

```json
// ✅ 올바름
"file_path": "MonTG_vs_nMonTF_de_b8cc6614.parquet"

// ❌ 틀림 (경로 포함)
"file_path": "output/datasets/MonTG_vs_nMonTF_de_b8cc6614.parquet"
```

### metadata.json 병합

기존 `data/metadata.json`이 있을 때 새 파일로 **덮어쓰면** 기존 데이터셋 목록이 사라집니다. 반드시 `datasets` 배열을 **병합**하세요. 위 R 예시의 `save_metadata_json()` 함수가 자동으로 병합을 처리합니다.

### NA 값 처리

DESeq2에서 `padj`가 `NA`인 행(low-count filtering 등)은 그대로 저장해도 무방합니다. 앱은 `pd.to_numeric(..., errors='coerce')`로 처리하므로 `NA → NaN`으로 자동 변환됩니다.

### gene_symbols 컬럼 구분자

GO 결과의 `gene_symbols` 컬럼은 `/` 구분자를 사용해야 합니다.

```r
# clusterProfiler의 geneID 컬럼은 이미 "/" 구분자를 사용하므로 그대로 사용 가능
go_df$gene_symbols <- go_df$geneID  # "Tnf/Il6/Cxcl10" 형식
```

---

## 9. `seqviewer_manifest.json` 규격

`metadata.json` 대신 **`seqviewer_manifest.json`** 을 사용할 수 있습니다. 두 파일 모두
`datasets` 배열을 가지며, manifest는 파이프라인이 이미 알고 있는 메타데이터
(`cell_type`, `organism`, `tags`, `provenance` 성격의 값)를 함께 담기에 적합합니다.

### 9.1 인식 위치

| 경로 | 인식 시점 |
|------|-----------|
| `{DB}/datasets/seqviewer_manifest.json` + 같은 폴더의 `*.parquet` | DB 스캔/새로고침 |
| `{source}/seqviewer_manifest.json` + `{source}/datasets/*.parquet` | **Import Folder** |
| `{source}/metadata.json` + `{source}/datasets/*.parquet` | **Import Folder** (기존 방식) |

`metadata.json`과 manifest가 동시에 있으면 `metadata.json`이 우선합니다.

### 9.2 최소 예시

```json
{
  "datasets": [
    {
      "alias": "Tcell_IFN_vs_Control_DE",
      "original_filename": "Tcell_IFN_vs_Control_DE.parquet",
      "dataset_type": "differential_expression",
      "experiment_condition": "IFN vs Control",
      "cell_type": "T cell",
      "organism": "Homo sapiens",
      "tags": ["scRNA", "Tcell", "IFN"],
      "row_count": 1523,
      "gene_count": 1523,
      "significant_genes": 210
    }
  ]
}
```

현재 앱은 다음 키를 **자동 보완**합니다 (이전에는 누락 시 항목 전체가 조용히
컬럼 추측으로 fallback됐습니다).

| 키 | 자동 보완 규칙 |
|----|----------------|
| `file_path` | `original_filename`의 basename |
| `original_filename` | `file_path`의 basename |
| `alias` | `file_path`/`original_filename`의 stem |
| `dataset_id` | 파일명 기반 uuid5 (재반입 시 중복 방지) |

`dataset_type`은 자동 추론하지 않으므로 **반드시 명시**해야 합니다.

### 9.3 전체 필드

| 필드 | 타입 | 필수 | 비고 |
|------|------|------|------|
| `dataset_type` | string | ✅ | 아래 허용값 참고 |
| `file_path` 또는 `original_filename` | string | ✅ (하나 이상) | parquet 파일명만 (경로 금지) |
| `alias` | string | 권장 | 없으면 파일명 stem |
| `dataset_id` | string | 선택 | 없으면 uuid5 자동 생성 |
| `experiment_condition` | string | 권장 | 비교 조건 |
| `cell_type` | string | 선택 | 세포 타입 |
| `organism` | string | 권장 | 예: `Homo sapiens` |
| `tissue` | string | 선택 | 조직 |
| `timepoint` | string | 선택 | 시간점 |
| `row_count` | int | 선택 | 전체 행 수 |
| `gene_count` | int | 선택 | DE 유전자 수 / ATAC peak 수 |
| `significant_genes` | int | 선택 | padj(및 |log2FC|) 기준 유의 수 |
| `notes` | string | 선택 | 자유 메모 |
| `tags` | string[] | 선택 | 검색 태그 (문자열 배열) |
| `researcher` | string 또는 string[] | 선택 | 이니셜. tags에도 자동 추가 |
| `project_name` | string | 선택 | 프로젝트 식별자 |
| `analysis_date` | string | 선택 | `YYYY-MM-DD` |
| `import_date` | string | 선택 | ISO 8601 |
| `genome_build` | string | 선택 | 예: `hg38`, `mm10` |
| `peak_caller` | string | 선택 | ATAC 전용 (예: `MACS2`) |

**`dataset_type` 허용값:**
`differential_expression`, `go_analysis`, `multi_group`, `atac_seq`, `multi_omics`,
`motif_enrichment`, `tf_footprint`, `chromvar_diff_tf`, `composition`, `unknown`
(별칭: `differential_accessibility`→`atac_seq`, `time_series`/`coexpression_module`→`multi_group`)

그 외 키(`schema_version`, `provenance`, `padj_cutoff`, `log2fc_cutoff` 등)는 현재
저장되지 않고 무시됩니다. 파이프라인 provenance는 `notes`/`tags`로 표현하거나,
추가가 필요하면 이슈로 요청해 주세요.

### 9.4 폴더명에서 researcher/analysis_date 추론

`metadata.json`/`seqviewer_manifest.json`에 `researcher` 또는 `analysis_date`가
비어 있으면 **Import Folder로 선택한 폴더의 이름**에서 추론합니다.

```
2026-ljh-human-de
│    │   │     └─ type (마지막 2개는 organism/type으로 간주)
│    │   └─────── organism
│    └─────────── researcher (알파벳, 길이 ≤ 4)
└──────────────── year
```

- 첫 segment가 4자리 숫자이고 전체 segment가 3개 이상일 때만 동작
- `analysis_date`는 `YYYY-01-01`로 채워짐
- researcher 후보는 마지막 2개를 제외한 중간 segment 중 알파벳·길이 ≤4인 것
- `tags`에도 researcher 이니셜이 자동 추가됨

### 9.5 CLI로 반입 전 검증

파이프라인 CI에서는 parquet을 직접 검증할 수 있습니다.

```bash
cmg-seqviewer-cli load datasets/Tcell_IFN_vs_Control_DE.parquet --json
```

```json
{
  "dataset_type": "differential_expression",
  "rows": 1523,
  "columns": ["gene_id", "log2fc", "adj_pvalue", "baseMean"],
  "valid": true,
  "required_columns": ["gene_id", "log2fc", "adj_pvalue"],
  "missing_required_columns": [],
  "file": "datasets/Tcell_IFN_vs_Control_DE.parquet"
}
```

`missing_required_columns`가 비어 있고 `valid`가 `true`면 DB 반입 가능한 상태입니다.
자동 감지가 실패하면 `--type differential_expression|go_analysis|multi_group|atac|composition`으로
강제할 수 있습니다.

### 9.6 Multi-Group parquet 규격

pseudobulk count matrix나 LRT/time-series/module 결과를 Multi-Group Heatmap ·
PCA · Gene Expression Bar로 넘길 때의 규격입니다.

| 항목 | 규칙 |
|------|------|
| 유전자 식별 컬럼 | `gene_id` 또는 `gene_symbol` 권장 (없으면 히트맵 라벨이 행 번호로 표시됨) |
| 샘플 컬럼 | 숫자형 컬럼 3개 이상. 이름 규칙은 자유 (`<condition>_<rep>` 권장) |
| `padj` | 선택 — 있으면 히트맵 유의성 필터에 사용. 없으면 필터만 생략됨 |
| `cluster_id` | 선택 — `padj`가 없을 때 자동 감지용으로 사용 (`"Cluster01"` 같은 문자열 권장) |
| `fdr` / `qvalue` | 통계 컬럼으로 간주되어 **샘플 컬럼에서 제외** |
| `baseMean`, `stat`, `pvalue`, `lfcse` | 통계 컬럼으로 간주되어 샘플에서 제외 |
| `cluster_id` (숫자형) | 메타 컬럼으로 간주되어 샘플에서 제외 |

**자동 감지 조건** (`is_multi_group_dataframe`):

1. `padj`/`p_adj`/`p_value`/`p_val` 중 하나, **또는** `cluster_id` 존재
2. `log2foldchange`/`log2fc`/`lfc` 계열 컬럼 **없음**
3. 통계·메타 컬럼을 제외한 숫자형 컬럼이 **3개 이상**

`padj`도 `cluster_id`도 없는 **순수 발현행렬**은 자동 감지되지 않습니다.
이 경우 다음 중 하나로 명시하세요.

```bash
cmg-seqviewer-cli load matrix.csv --type multi_group
```

```json
{ "dataset_type": "multi_group", "file_path": "matrix.parquet", "...": "..." }
```

**최소 예시 (pseudobulk matrix):**

```text
gene_id  Tcell_ctrl_1  Tcell_ctrl_2  Tcell_IFN_1  Tcell_IFN_2
G1       120.5         118.2         340.1        355.0
G2       0.0           1.2           88.4         91.2
```

**예시 (LRT/time-series 결과):**

```text
gene_id  padj    baseMean  stat    ctrl_1  ctrl_2  24h_1  24h_2  3D_1  3D_2
G1       0.001   210.4     45.2    100.1   98.2    220.1  230.4  310.5 320.1
```

### 9.7 Cell-type Composition parquet 규격

propeller/limma 기반 세포타입 비율 변화 결과를 `dataset_type: "composition"`으로
넘길 때의 규격입니다.

| 컬럼 | 필수 | 규칙 |
|------|------|------|
| `cell_type` | ✅ | 세포 타입 이름. `CellType`/`population` 등도 자동 인식 |
| `PropMean.<condition>` | ✅ (또는 `PropRatio`) | 조건별 평균 비율. 조건명은 `PropMean.` 뒤 문자열 |
| `PropRatio` | ✅ (또는 `PropMean` 2개↑) | 조건 간 비율 차이 |
| `P.Value` / `pvalue` | 권장 | `P.Value`, `p_value`, `pvalue` 모두 인식 |
| `FDR` / `padj` | 권장 | `FDR`, `padj`, `adj_pvalue`, `qvalue` 모두 인식 |

표준화 결과: `cell_type`, `prop_ratio`, `pvalue`, `fdr` (PropMean 컬럼은 원본 이름 유지).

**최소 예시:**

```text
cell_type  PropMean.Control  PropMean.Treatment  PropRatio  P.Value  FDR
T cell     0.45              0.55                0.10       0.001    0.003
B cell     0.30              0.20               -0.10       0.020    0.030
NK cell    0.25              0.25                0.00       0.900    0.950
```

manifest 예시:

```json
{
  "alias": "Tcell_IFN_composition",
  "file_path": "Tcell_IFN_composition.parquet",
  "dataset_type": "composition",
  "experiment_condition": "IFN vs Control",
  "cell_type": "T cell",
  "organism": "Homo sapiens",
  "tags": ["scRNA", "composition", "propeller"]
}
```

> 순수 `PropRatio`만 있고 `PropMean.*`가 없어도 비율 차이 막대로 시각화할 수
> 있습니다. 반대로 `PropMean.*`가 2개 이상이면 평균 비율 그룹 막대도 사용할 수
> 있습니다.

---

**See also**: [scRNA-seq 3차 분석 파이프라인 연동 회신](pipeline-integration-response.md)
(원문 Q1~Q7/R1에 대한 항목별 답변과 예시)
