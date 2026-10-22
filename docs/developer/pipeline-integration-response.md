# scRNA-seq 3차 분석 파이프라인 연동 회신

- **수신**: `ibs-CMG-NGS/sc-rna-seq-analysis-r` (R/Seurat 3차 분석 파이프라인 담당)
- **발신**: cmg-seqviewer 개발팀
- **기준 코드**: 커밋 `417d981` (v1.3.2 기반, 다음 릴리스 포함 예정)
- **원문**: [`cmg-seqviewer-integration-questions.md`](https://github.com/ibs-CMG-NGS/sc-rna-seq-analysis-r/blob/main/docs/cmg-seqviewer-integration-questions.md)

---

## 0. 회신 요약

| 항목 | 상태 | 회신 요지 |
|------|------|-----------|
| Q1 manifest 스키마 | ✅ 확정 | 아래 스키마 사용. `dataset_type`만 필수, 나머지 식별자는 자동 보완 |
| Q2 Multi-Group 스키마 | ✅ 확정 | `padj` 또는 `cluster_id` + 숫자형 샘플 3개↑. `gene_id`/`gene_symbol` 권장 |
| Q3 DE 메타 컬럼 | ✅ 가능 | `cell_type`, `contrast` 그대로 유지 가능 (부분매칭 주의) |
| Q4 CLI JSON | ✅ 구현 | `load --json`, exit code 0/1. DE/GO/Multi-Group parquet 직접 검증 가능 |
| Q5 GO/KEGG 명시 컬럼 | ✅ 권장 | `Gene Set`/`Ontology` 명시 컬럼이 추론보다 우선 |
| Q6 DB browser 그룹화 | ⏳ 미구현 | 현재는 검색/필터/정렬. 그룹화는 v2.0 계획 |
| Q7 single-cell 스키마 | ⏳ 미정 | 로드맵만 존재. 현재는 DE/GO/Multi-Group/Composition으로 reshape |
| R1 composition type | ✅ 구현 | `composition` 타입 + 전용 plot + CLI/DB/manifest 지원 |

**핵심 원칙은 그대로 유지합니다.** 뷰어는 Seurat/h5ad를 직접 읽지 않고, 파이프라인이
뷰어 스키마(DE / GO·KEGG / Multi-Group / Composition)로 reshape한 **parquet + manifest**를
소비합니다.

---

## 1. Q1 — `seqviewer_manifest.json` 정식 스키마

### 1.1 인식 위치

| 경로 | 사용 시점 |
|------|-----------|
| `{DB}/datasets/seqviewer_manifest.json` + 같은 폴더의 `*.parquet` | DB 스캔/Refresh |
| `{source}/seqviewer_manifest.json` + `{source}/datasets/*.parquet` | **Import Folder** |
| `{source}/metadata.json` + `{source}/datasets/*.parquet` | Import Folder (기존 방식) |

`metadata.json`과 manifest가 동시에 있으면 `metadata.json`이 우선합니다.

### 1.2 최소 예시

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
      "tissue": "PBMC",
      "timepoint": "24h",
      "row_count": 1523,
      "gene_count": 1523,
      "significant_genes": 210,
      "tags": ["scRNA", "Tcell", "IFN"],
      "researcher": ["ljh"],
      "notes": "Seurat v5, DESeq2 pseudobulk, apeglm"
    }
  ]
}
```

### 1.3 필드

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `dataset_type` | string | ✅ | 아래 허용값. **자동 추론하지 않음** |
| `file_path` 또는 `original_filename` | string | ✅ (하나 이상) | parquet 파일명만 (경로 금지) |
| `alias` | string | 권장 | 없으면 파일명 stem |
| `dataset_id` | string | 선택 | 없으면 파일명 기반 uuid5 자동 생성 |
| `experiment_condition` | string | 권장 | 비교 조건 |
| `cell_type` | string | 선택 | 세포 타입 (dataset 수준 라벨) |
| `organism` | string | 권장 | 예: `Homo sapiens` |
| `tissue` | string | 선택 | 조직 |
| `timepoint` | string | 선택 | 시간점 |
| `row_count` | int | 선택 | 전체 행 수 |
| `gene_count` | int | 선택 | DE 유전자 수 / ATAC peak 수 / composition 세포타입 수 |
| `significant_genes` | int | 선택 | padj(및 \|log2FC\|) 기준 유의 수 |
| `notes` | string | 선택 | 자유 메모 (파이프라인 버전, 방법 등) |
| `tags` | string[] | 선택 | 검색 태그. **문자열 배열**로 작성 |
| `researcher` | string 또는 string[] | 선택 | 이니셜. `tags`에도 자동 추가 |
| `project_name` | string | 선택 | 프로젝트 식별자 |
| `analysis_date` | string | 선택 | `YYYY-MM-DD` |
| `import_date` | string | 선택 | ISO 8601 |
| `genome_build` | string | 선택 | 예: `hg38`, `mm10` |
| `peak_caller` | string | 선택 | ATAC 전용 |

**`dataset_type` 허용값:**

```
differential_expression
go_analysis
multi_group
composition
expression_summary
atac_seq
multi_omics
motif_enrichment
tf_footprint
chromvar_diff_tf
unknown
```

별칭도 허용됩니다: `differential_accessibility`→`atac_seq`,
`time_series`/`coexpression_module`→`multi_group`,
`cell_composition`/`composition_analysis`→`composition`,
`expression_atlas`/`cell_type_expression`→`expression_summary`.

현재 `schema_version`, `provenance`, `padj_cutoff`, `log2fc_cutoff` 같은 키는
**저장되지 않고 무시**됩니다. 파이프라인 provenance는 `notes`/`tags`로 표현해 주세요.
(정식 필드 추가가 필요하면 이슈로 요청해 주시면 검토하겠습니다.)

### 1.4 자동 보완 규칙

| 누락 키 | 자동 보완 |
|---------|-----------|
| `file_path` | `original_filename`의 basename |
| `original_filename` | `file_path`의 basename |
| `alias` | 파일명 stem |
| `dataset_id` | 파일명 기반 uuid5 (재반입 시 중복 방지) |

### 1.5 DB 폴더명 파싱 (`/YYYY-initials-organism-type/`)

`researcher` 또는 `analysis_date`가 비어 있으면 **Import Folder로 선택한 폴더의
이름**에서 추론합니다. manifest/metadata가 있어도 동일하게 적용됩니다.

```
2026-ljh-human-de
│    │   │     └─ type
│    │   └─────── organism
│    └─────────── researcher (알파벳, 길이 ≤ 4)
└──────────────── year
```

- 첫 segment가 4자리 숫자이고 전체 segment가 3개 이상일 때만 동작
- `analysis_date`는 `YYYY-01-01`로 보완
- researcher 후보는 마지막 2개를 제외한 중간 segment 중 알파벳·길이 ≤4
- `tags`에도 이니셜 자동 추가

---

## 2. Q2 — Multi-Group 정확한 요구 스키마

### 2.1 자동 감지 조건

다음을 **모두** 만족하면 `multi_group`으로 인식합니다.

1. `padj` / `p_adj` / `p_value` / `p_val` 중 하나가 있음, **또는** `cluster_id`가 있음
2. `log2foldchange` / `log2fc` / `log2_fold_change` / `lfc` 계열 컬럼이 **없음**
3. 통계·메타 컬럼을 제외한 **숫자형 컬럼이 3개 이상**

`fdr`, `qvalue`, `baseMean`, `stat`, `pvalue`, `lfcse`, 숫자형 `cluster_id`,
`gene_id`/`gene`/`id`/`symbol`은 **샘플 컬럼에서 제외**됩니다.

### 2.2 유전자 ID 컬럼

- 특정 표준명이 강제되지는 않습니다.
- 히트맵 라벨은 `gene_symbol` → `gene_id` → 행 번호 순서로 사용됩니다.
- **첫 컬럼을 `gene_id` 또는 `gene_symbol`로 두는 것을 권장**합니다.

### 2.3 샘플 컬럼 명명/타입

- 고정 규칙은 없으며 **숫자형이면 샘플**로 인식됩니다.
- 그룹은 컬럼명 끝의 replicate 숫자를 제거해 추론합니다
  (`HP1hr1`→`HP1hr`). GUI에서는 `_S20` 전역 인덱스와 끝 숫자를 제거하는 규칙으로
  한 번 더 보정합니다.
- 권장: `<condition>_<rep>` (예: `Tcell_IFN_1`, `Tcell_IFN_2`).

### 2.4 `cluster_id` 필수 여부

- **필수는 아닙니다.** `padj`/`p_value`가 있으면 없어도 됩니다.
- `padj`도 `cluster_id`도 없는 **순수 pseudobulk count matrix**는 자동 감지되지
  않습니다. 이 경우 다음 중 하나로 명시하세요.
  - CLI: `cmg-seqviewer-cli load matrix.csv --type multi_group`
  - manifest: `"dataset_type": "multi_group"`
- `cluster_id`는 문자열(`"Cluster01"`, `"all"` 등)을 권장합니다. 숫자형도 샘플에서는
  제외되지만, 문자열이 의미상 명확합니다.

### 2.5 예시

**pseudobulk 행렬:**

```text
gene_id  Tcell_ctrl_1  Tcell_ctrl_2  Tcell_IFN_1  Tcell_IFN_2
G1       120.5         118.2         340.1        355.0
G2       0.0           1.2           88.4         91.2
```

**LRT/time-series 결과:**

```text
gene_id  padj    baseMean  stat    ctrl_1  ctrl_2  24h_1  24h_2  3D_1  3D_2
G1       0.001   210.4     45.2    100.1   98.2    220.1  230.4  310.5 320.1
```

---

## 3. Q3 — DE dataset에 추가 메타 컬럼 유지

**그대로 넘겨도 됩니다.** DE 로더는 매핑된 컬럼만 표준명으로 rename하고, 매핑되지
않은 컬럼은 보존합니다. `cell_type`, `contrast`는 DE 패턴에 걸리지 않아 그대로
남습니다.

주의사항 2가지:

1. **부분매칭**: 표준 컬럼이 비어 있을 때 추가 컬럼이 잘못 매핑될 수 있습니다.
   예를 들어 `symbol` 컬럼이 없으면 `gene_biotype`/`gene_type`이 `symbol`로 잡힐 수
   있습니다. `cell_type`/`contrast` 자체는 안전하지만, 가능하면 `gene_id`,
   `symbol`, `log2fc`, `adj_pvalue`를 정확한 이름으로 포함해 주세요.
2. **저발현 행 사전 제거**: DE를 Excel/CSV/CLI로 로드할 때 앱이
   `baseMean < max(5, 숫자형 비표준 컬럼 수)` 행을 제거합니다. **DB parquet 로드
   경로에는 이 제거가 적용되지 않습니다.** 따라서 `cmg-seqviewer-cli load --json`의
   `rows`가 manifest의 `row_count`보다 작을 수 있습니다. CI에서는 `valid`와
   `missing_required_columns`를 기준으로 검증하고, 행 수 비교 시 이 차이를
   감안해 주세요.

---

## 4. Q4 — CLI `load`의 기계 판독 출력

### 4.1 JSON 출력

`load --json`이 판정 결과를 JSON으로 출력합니다.

```bash
cmg-seqviewer-cli load datasets/Tcell_IFN_vs_Control_DE.parquet --json
```

```json
{
  "dataset_type": "differential_expression",
  "rows": 1518,
  "columns": ["gene_id", "log2fc", "adj_pvalue", "baseMean", "symbol"],
  "valid": true,
  "required_columns": ["gene_id", "log2fc", "adj_pvalue"],
  "missing_required_columns": [],
  "file": "datasets/Tcell_IFN_vs_Control_DE.parquet"
}
```

- `valid`가 `true`이고 `missing_required_columns`가 비어 있으면 DB 반입 가능한 상태입니다.
- **DE/GO/Multi-Group/Composition 모두 CSV/TSV/Parquet 직접 로드**를 지원합니다.
- 자동 감지가 실패하면 `--type differential_expression|go_analysis|multi_group|atac|composition|expression_summary`으로
  강제할 수 있습니다.

### 4.2 Exit code

| 코드 | 의미 |
|------|------|
| `0` | 성공 |
| `1` | 실패 (파일 미인식, 필수 컬럼 누락, 잘못된 recipe, batch 부분 실패 등) |

`--verbose`를 붙이면 one-line `Error:` 대신 전체 traceback을 출력합니다.

### 4.3 CI 검증 예시

```bash
set -euo pipefail

for f in output/export/seqviewer/datasets/*.parquet; do
  cmg-seqviewer-cli load "$f" --json > /tmp/seqviewer_report.json
  python - <<'PY'
import json, sys
r = json.load(open("/tmp/seqviewer_report.json"))
if not r["valid"] or r["missing_required_columns"]:
    print(f"INVALID: {r['file']} missing={r['missing_required_columns']}")
    sys.exit(1)
print(f"OK: {r['file']} ({r['dataset_type']}, {r['rows']} rows)")
PY
done
```

`load`가 실패하면 exit code 1이므로 `set -e`만으로도 CI가 중단됩니다.

---

## 5. Q5 — GO/KEGG `Gene Set` / `Ontology` 명시 컬럼

**명시 컬럼 방식을 권장합니다.** 현재 동작:

- `Gene Set`/`gene_set` → `gene_set`
- `Ontology`/`ontology`/`category` → `ontology`
- `Direction`/`direction` → `direction`

`Direction`/`Ontology`가 **없거나 NaN일 때만** `Gene Set` 문자열에서 추론합니다
(예: `UP_BP`, `DOWN_MF`, `KEGG`). 즉 명시 컬럼이 항상 우선합니다.

Excel 다중 시트에서도 Direction/Ontology는 데이터 내부 컬럼에서 읽고, 시트명은
`Gene Set` 컬럼이 없을 때만 fallback으로 사용합니다. KEGG 시트가 구조적으로
KEGG임이 명백한데 Ontology 컬럼이 없으면 `KEGG`로 stamp합니다.

`ontology='Info'` 행과 `Parameter`/`Value` 컬럼은 로드 시 제거됩니다. 분석
파라미터는 manifest의 `notes`/`tags`에 기록해 주세요.

---

## 6. Q6 — 다수 dataset의 DB browser 성능

현재 DB browser는 **평면 테이블**입니다.

- 검색: alias, condition, tags, researcher
- 필터: Type, Organism, Researcher, Cell Type
- 헤더 정렬, 다중 선택
- **그룹화/폴더 트리/일괄 접기는 없습니다.**

수십~수백 개 규모는 필터+정렬로 운용 가능하지만, 세포타입×contrast 탐색에는
그룹화가 유용합니다. `docs/user/database-guide.md`에 v2.0 계획으로
"데이터셋 그룹화/폴더 구조"가 등록되어 있습니다. 일정이 확정되면 별도로
공유드리겠습니다.

---

## 7. Q7 — v2.0 single-cell 지원

현재는 README 로드맵의 체크리스트 한 줄뿐이고, **공유할 수 있는 스키마는 아직
없습니다.** 현재 권장 경로는 다음과 같습니다.

- 뷰어는 Seurat/h5ad를 직접 읽지 않음
- 파이프라인이 DE / GO·KEGG / Multi-Group / **Composition** parquet로 reshape
- 세포타입별 DE/GO는 `cell_type`을 manifest 메타데이터로 기록 → DB 검색/필터
- 세포타입 간 비교는 Multi-Group/Composition 활용

스키마가 확정되면 본 문서와 `docs/developer/pipeline-integration.md`에 반영하겠습니다.

---

## 8. R1 — `composition` dataset type (구현 완료)

### 8.1 상태

현재 코드에 **`composition` dataset type + 전용 plot**이 구현되어 있습니다.
별도 우회 없이 다음을 사용할 수 있습니다.

- `Visualization → 🧬 Single-cell RNA-seq → 🧫 Cell-Type Composition`
- PropRatio 막대 / 조건별 평균 비율 그룹 막대
- FDR 필터, Top N, 정렬, 유의성 별표
- CLI `load --json`, `filter --fdr-max`
- manifest/DB 적재
- Export Data / Export Bundle

### 8.2 요구 스키마

| 컬럼 | 필수 | 규칙 |
|------|------|------|
| `cell_type` | ✅ | `CellType`/`population` 등도 자동 인식 |
| `PropMean.<condition>` | ✅ (또는 `PropRatio`) | 조건별 평균 비율. 조건명은 `PropMean.` 뒤 문자열 |
| `PropRatio` | ✅ (또는 `PropMean` 2개↑) | 조건 간 비율 차이 |
| `P.Value` / `pvalue` | 권장 | `P.Value`, `p_value`, `pvalue` 모두 인식 |
| `FDR` / `padj` | 권장 | `FDR`, `padj`, `adj_pvalue`, `qvalue` 모두 인식 |

표준화 결과는 `cell_type`, `prop_ratio`, `pvalue`, `fdr`이며, `PropMean.*` 컬럼은
원본 이름을 유지합니다.

### 8.3 최소 예시

```text
cell_type  PropMean.Control  PropMean.Treatment  PropRatio  P.Value  FDR
T cell     0.45              0.55                0.10       0.001    0.003
B cell     0.30              0.20               -0.10       0.020    0.030
NK cell    0.25              0.25                0.00       0.900    0.950
```

manifest:

```json
{
  "alias": "Tcell_IFN_composition",
  "file_path": "Tcell_IFN_composition.parquet",
  "dataset_type": "composition",
  "experiment_condition": "IFN vs Control",
  "organism": "Homo sapiens",
  "tags": ["scRNA", "composition", "propeller"]
}
```

### 8.4 제약

- 뷰어는 **propeller/limma 계산을 직접 수행하지 않습니다.** 파이프라인이 계산한
  결과 표만 시각화합니다.
- `PropRatio`만 있고 `PropMean.*`가 없으면 비율 차이 막대만 사용할 수 있습니다.
- `PropMean.*`가 2개 이상이면 평균 비율 그룹 막대도 사용할 수 있습니다.

---

## 9. E1~E4 대응 현황

| 단계 | 내용 | 상태 |
|------|------|------|
| E1 | DE / GO·KEGG 어댑터 export (뷰어 무수정) | ✅ 진행 가능. `load --json`으로 검증 |
| E2 | manifest 생성 + DB 적재 | ✅ 스키마 확정. `Import Folder` 사용 |
| E3 | Multi-Group export + upstream `cluster_id` | ✅ 스키마 확정. 순수 행렬은 `--type multi_group`/manifest |
| E4 | composition type 반영 | ✅ 현재 코드에 구현됨 |

---

## 10. 파이프라인 측 권장 규약

1. **`dataset_type`은 항상 명시**해 주세요. 이것만은 자동 추론하지 않습니다.
2. `file_path`/`original_filename`은 **parquet 파일명만** (경로 금지).
3. `tags`는 **문자열 배열**로 작성해 주세요 (`"tags": "a,b"` 금지).
4. Multi-Group은 첫 컬럼을 `gene_id` 또는 `gene_symbol`로, 샘플은
   `<condition>_<rep>` 형태를 권장합니다.
5. DE는 `gene_id`, `symbol`, `log2fc`, `adj_pvalue`, `baseMean`을 정확한 이름으로
   포함해 주세요.
6. GO/KEGG는 `Gene Set`, `Ontology`, `Direction`을 **명시 컬럼**으로 주세요.
7. GO/KEGG 데이터에 `ontology='Info'` 행을 넣지 말고, 분석 파라미터는 manifest에
   기록해 주세요.
8. Composition은 `cell_type`, `PropMean.<condition>`, `PropRatio`, `P.Value`,
   `FDR` 이름을 유지해 주세요.
9. CI에서는 `cmg-seqviewer-cli load <file> --json`의 `valid` /
   `missing_required_columns`를 검증해 주세요.

---

## 11. 참고 문서

- [`docs/developer/pipeline-integration.md`](pipeline-integration.md) — 전체 연동 규격
  (DE/GO/metadata/manifest/Multi-Group/Composition)
- [`docs/user/help/19-command-line-interface.md`](../user/help/19-command-line-interface.md) — CLI 사용법
- [`docs/user/help/20-cell-type-composition.md`](../user/help/20-cell-type-composition.md) — Composition 사용법

문의나 추가 스키마 요청은 이 저장소 이슈로 남겨 주세요.

---

**See also**: [HypoMap 발현 요약 테이블 연동 회신](hypomap-expression-integration-response.md)
(전 유전자 × 세포타입 expression summary의 수용 범위와 `expression_summary` 설계)
