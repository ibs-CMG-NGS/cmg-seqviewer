# HypoMap 유전자×세포타입 발현 요약 테이블의 cmg-seqviewer 연동 가능 범위 — 회신

- **수신**: scRNA-seq 3차 분석 파이프라인 담당
- **발신**: cmg-seqviewer 개발팀
- **기준 코드**: 커밋 `417d981` + `5158ad0` + `expression_summary` 구현 (v1.3.2 기반)
- **구현 상태**: Phase 1(wide + long pivot ≤5M + gene_index + dot plot/heatmap + manifest/DB/CLI) 완료, 전달 sample bundle 검증 완료
- **대상 문의**: HypoMap atlas 기반 “전 유전자 × 세포타입” 발현 요약 export 연동

---

## 0. 회신 요약

| 구분 | 항목 | 답변 |
|------|------|------|
| A | generic expression 타입 | **조건부** — 신규 `expression_summary` 타입 필요 (현재 없음) |
| A | 필수 컬럼명 | **조건부** — 새 타입에서 아래 표준명 채택 제안 |
| A | manifest/schema version | **가능** — `expression_schema` 블록으로 협의 |
| A | `export_index.tsv` 등록 | **불가/조건부** — 앱은 읽지 않음. manifest 사용 |
| B | 10.6M long rows | **조건부/현재 불가** — 전체 pandas 로드 구조로는 위험 |
| B | 57k × 185 wide | **가능** — 행렬당 약 85MB, pandas 포함 100–150MB |
| B | server-side filtering | **불가 (현재)** — DuckDB/Arrow 기반은 신규 개발 |
| B | 57k × 185 heatmap | **조건부** — top-N만 지원. 전체 행 렌더는 불가 |
| C | gene_id 종류 | **가능** — symbol/Ensembl 모두 가능, mouse symbol 가능 |
| C | alias/대소문자 검색 | **조건부** — 대소문자 무시 substring 가능, synonym/alias는 미지원 |
| D | C66/C185 계층 | **조건부** — 별도 dataset 권장, 계층 선택 UI는 없음 |
| D | `:`/공백 라벨 | **가능** — 값/컬럼명으로 문제 없음 |
| D | 긴 라벨 truncation/tooltip | **조건부** — 테이블 전체 표시, tooltip/truncation 미구현 |
| E | dataset 필터 UI | **불가 (현재)** — v1은 overall + summary 권장 |
| E | per-dataset 테이블 | **조건부** — 1–1.5GB 단일 테이블은 비권장 |
| F | mean/pct/n_cells/mean_counts 표시 | **가능** — 테이블 컬럼으로 표시 |
| F | “Expression summary” 라벨 | **조건부** — 새 타입 추가 시 가능 |
| F | n_cells 작은 cell type 경고 | **조건부** — 새 뷰에서 신규 개발 |
| G | 파일 형식 | **parquet 권장** |
| G | sample bundle 테스트 | **가능** — C66 subset 권장 |
| G | 전달 위치/이름 | **제안** — 아래 레이아웃 사용 |
| H | 10.6M 불가 시 대안 | **(a) wide + gene_index를 v1**, **(c) DuckDB를 v2** 권장 |

**핵심 결론:** wide mean/pct + gene_index 조합은 **현재 구현으로 수용 가능**합니다. per-dataset long(수백만 행)은 pivot으로 지원하며, 전체 10.6M rows는 v1 범위에서 제외하고 필요 시 DuckDB 기반 lazy 로딩(v2)으로 확장하는 것을 권장합니다.

---

## 1. 현재 구조의 제약 (근거)

| 제약 | 설명 |
|------|------|
| generic parquet 테이블 타입 없음 | 현재 `DatasetType`은 DE/GO/Multi-Group/ATAC/Composition 등 분석 목적 타입만 존재. 미인식 파일은 로드 실패 |
| 전체 파일을 pandas로 로드 | parquet을 `pd.read_parquet`로 전부 메모리에 올림. 행 수 제한은 없지만 메모리/로드 시간이 행 수에 비례 |
| 서버사이드 필터 없음 | DuckDB/Arrow predicate pushdown 미사용. `pyarrow`는 parquet 읽기 용도 |
| 테이블 렌더링은 가상화 | 화면에 보이는 셀만 렌더하므로 10.6M rows도 “표시” 자체는 가능. 그러나 정렬/검색은 전체 DataFrame 연산 |
| Heatmap은 top-N만 | 일반 Heatmap 10–500 genes, Multi-Group Heatmap 10–5000 genes. 전체 57k 행 렌더는 지원하지 않음 |
| DB browser는 메타데이터 검색 | alias/condition/tags/researcher + type/organism/cell type 필터. 데이터 내부 `dataset` 값 필터는 없음 |
| `export_index.tsv` 미지원 | 앱은 `seqviewer_manifest.json`/`metadata.json`만 읽음 |

---

## 2. 문의 항목별 답변

### A. 스키마·테이블

**A1. generic parquet expression 테이블을 새 테이블 타입으로 추가할 수 있나요?**

**조건부 가능.** 현재는 없습니다. 신규 `expression_summary` dataset type을 추가하면 됩니다. 기존 Multi-Group으로 wide mean을 우회 로드하는 것은 가능하지만, cell type을 sample로 취급하므로 의미·그룹핑·라벨 측면에서 부적합합니다.

**A2. 필수 컬럼명·이름 규칙이 있나요?**

**조건부 가능.** 새 타입에서 아래 표준명을 채택할 것을 제안합니다. 기존 DE/GO 컬럼명을 억지로 맞출 필요는 없습니다.

| 용도 | 표준명 | 비고 |
|------|--------|------|
| 유전자 ID | `gene_id` | symbol/Ensembl 모두 허용 |
| 유전자 이름 | `gene_name` 또는 `symbol` | 둘 다 인식 |
| 세포 타입 | `cell_type` | long layout 필수 |
| 평균 발현 | `mean_expression` | |
| 발현 비율 | `pct_expressing` | 0–1 또는 0–100 명시 필요 |
| 세포 수 | `n_cells` | |
| 발현 세포 수 | `n_expressing` | 선택 |
| 평균 count | `mean_counts` | 선택 |
| 데이터셋 | `dataset` | 선택 |
| 세포타입 레벨 | `cell_type_level` | C66/C185 구분용 (선택) |

**A3. manifest.json/schema version은 어떻게 협의하나요?**

**가능.** 현재 코드에 `expression_schema` 블록이 정식 필드로 추가되어 있습니다. `dataset_type: "expression_summary"`와 함께 manifest에 기록하면 DB Import에서 저장·복원됩니다.

```json
"expression_schema": {
  "schema_version": "1.0",
  "layout": "wide",
  "value_type": "mean_expression",
  "cell_type_level": "C66",
  "gene_id_type": "symbol",
  "normalization": "log1p_normalized",
  "detection": "count > 0",
  "pct_scale": "0-1",
  "source": "HypoMap",
  "license": "CC BY 4.0",
  "citation": "..."
}
```

**A4. 기존 `export_index.tsv`에 expression 테이블을 어떻게 등록하나요?**

**현재 불가.** 앱은 `export_index.tsv`를 읽지 않습니다. `seqviewer_manifest.json`의 `datasets[]` 항목으로 등록해야 합니다. `export_index.tsv`는 파이프라인 내부 인덱스로 유지해도 무방하지만, 뷰어 연동에는 사용되지 않습니다. TSV index 기반 등록이 꼭 필요하면 별도 지원을 검토할 수 있으나 권장하지 않습니다.

---

### B. 성능·규모

**B5. 최대 row/column 제한이 있나요? long 10.6M rows, wide 57k × 185를 감당할 수 있나요?**

- **wide 57k × 185:** **가능.** float64 기준 행렬당 약 85MB, pandas 오버헤드 포함 100–150MB입니다. mean/pct 두 개를 동시에 올려도 200–300MB 수준입니다.
- **long 10.6M rows:** **현재 구조로는 불가/위험.** 숫자 5개 + 문자열 3–4개 기준 대략 2–4GB+로 추정되며, 로드·정렬·검색 시 UI 지연이 발생합니다.
- **per-dataset long(≤5M rows, 예: Dowsett 2.6M):** pivot으로 wide를 만들어 사용할 수 있습니다(로드 수 초).
- 하드코딩된 행 제한은 없지만, 현재는 전체 pandas 로드 방식입니다.

**B6. server-side filtering(DuckDB/Arrow/predicate pushdown)이 가능한가요? 목표 응답시간은?**

**현재 불가.** 신규 개발이 필요합니다. v1은 client-side wide 테이블 기준으로 다음 목표를 제안합니다.

| 동작 | 목표 |
|------|------|
| wide 초기 로드 | < 5초 |
| gene lookup (gene_index) | < 200ms |
| top cell types | < 2초 |
| heatmap top-N 렌더 | < 5초 |
| long table gene query (v2, DuckDB) | < 500ms |

**B7. client-side만 가능하다면 wide + gene_index 방식이 가능한가요?**

**가능 (v1 권장).** wide mean/pct + gene_index를 메모리에 올리고, gene_index에서 유전자 1행을 찾은 뒤 wide 행을 fetch하는 방식입니다. per-dataset long(≤5M rows)은 로드 시 pivot으로 동일하게 사용할 수 있고, 10.6M rows는 top-N/pagination/lazy 없이는 불가합니다.

**B8. 57k × 185 heatmap 렌더링이 가능한가요? 불가하면 최대 column 수는?**

**조건부.** 185 columns는 가능합니다. 그러나 현재 Heatmap은 **top-N gene만** 렌더합니다(일반 500, Multi-Group 5000). 57k × 185 전체를 한 번에 그리는 것은 성능·가독성 모두 비권장이며 지원 계획이 없습니다. “유전자 탐색” 목적에는 **dot plot 또는 top-N heatmap**이 적합합니다.

---

### C. Gene ID

**C9. gene_id는 symbol인가요, Ensembl ID인가요? mouse symbol을 그대로 사용해도 되나요?**

**가능.** `gene_id`는 symbol/Ensembl 모두 허용합니다. mouse symbol을 `gene_id` 또는 `gene_name`/`symbol`에 그대로 넣어도 됩니다. `gene_id`(고유 ID)와 `gene_name`(표시용 symbol)을 함께 주는 것을 권장합니다.

**C10. alias/대소문자 검색을 지원하나요? species 필드가 필요한가요?**

- **대소문자 무시 부분문자열 검색:** 현재 가능합니다.
- **alias/synonym 검색:** 자동 지원하지 않습니다. 필요하면 gene annotation 기반 alias 인덱스를 신규 개발해야 합니다.
- **species/organism:** manifest의 `organism` 필드를 권장합니다. 표시/필터/향후 alias 매핑에 사용할 수 있습니다.

---

### D. Cell type

**D11. C66/C185 계층을 한 뷰어에서 선택하게 할 수 있나요?**

**조건부.** 현재 계층 선택 UI는 없습니다. **C66과 C185를 별도 dataset entry로 넘기는 것을 권장**합니다. 한 테이블에 `cell_type_level` 컬럼을 넣고 필터하는 방식도 가능하지만, 전용 필터 UI가 필요합니다.

**D12. 라벨에 `:`와 공백이 포함됩니다. 인코딩·표시 규칙이 있나요?**

**가능.** 값/컬럼명에 `:`와 공백이 있어도 parquet·pandas·테이블 표시에 문제 없습니다. 별도 인코딩은 필요 없습니다. 단, **파일명/alias slug에는 원본 라벨을 그대로 쓰지 말고** 안전한 문자로 변환해 주세요.

**D13. 긴 라벨을 위한 truncation/tooltip이 있나요?**

**조건부.** 테이블은 전체 텍스트를 표시하며 컬럼 폭을 조절할 수 있습니다. 현재 **tooltip은 미구현**이고, Heatmap 축 라벨은 길면 겹칠 수 있습니다. 새 타입의 dot plot/heatmap에서 truncation + tooltip을 함께 구현하는 것을 권장합니다.

---

### E. Dataset·교란

**E14. dataset 필터 UI가 필요한가요? overall 테이블 + cell_type_summary만으로 충분한가요?**

**현재 dataset 필터 UI는 없습니다.** v1에서는 **overall 테이블 + `cell_type_summary`** 만으로 충분하다고 판단합니다. per-dataset 비교가 핵심 요구가 되면 새 타입에 `dataset` facet을 추가하겠습니다.

**E15. per-dataset 테이블은 별도로 요청할 가치가 있나요? 최대 1–1.5GB를 고려할 때 권장 형태는?**

**조건부.** 단일 1–1.5GB long 테이블은 권장하지 않습니다. 필요 시:
- dataset별로 파일을 분리하고 manifest entry를 나누거나
- v2의 DuckDB lazy 로딩으로 on-demand 조회

v1에서는 `cell_type_summary`만 넘겨 주세요.

---

### F. 지표·해석

**F16. mean_expression(정규화), pct_expressing(raw counts > 0), n_cells, mean_counts를 그대로 표시할 수 있나요?**

**가능.** 네 지표 모두 테이블 컬럼으로 표시 가능합니다. mean/pct wide는 Heatmap 입력으로 사용할 수 있습니다. 추가로 **Gene × Cell-Type Dot Plot**(dot size = `pct_expressing`, color = `mean_expression`)을 신규 개발하는 것을 권장합니다. 이는 scRNA-seq 발현 요약을 탐색하는 가장 자연스러운 뷰입니다.

**F17. DE가 아닌 “Expression summary”로 라벨링하는 UI가 가능한가요?**

**조건부.** 새 `expression_summary` 타입을 추가하면 dataset type 라벨/필터/뷰에서 “Expression summary”로 표시할 수 있습니다. 현재 타입 체계에는 없는 라벨입니다.

**F18. n_cells가 작은 cell type에 경고/회색 처리 등을 넣을 수 있나요?**

**조건부.** 새 타입의 dot plot/heatmap에서 `n_cells < threshold`인 cell type을 회색/반투명 처리하고 tooltip에 n_cells를 표시하는 기능을 추가할 수 있습니다. 작은 범위의 개발입니다.

---

### G. Handoff·테스트

**G19. parquet 외에 csv/arrow/duckdb 중 선호 형식이 있나요?**

**parquet 권장.** 현재 앱은 pyarrow 기반 parquet를 사용합니다. CSV는 10.6M rows에 비현실적입니다. Arrow/Feather는 현재 미사용, DuckDB는 v2에서 검토할 수 있는 신규 의존성입니다.

**G20. 전체 export 전에 C66 또는 1개 dataset subset으로 sample bundle을 먼저 전달해 테스트할 수 있나요?**

**가능하며 권장합니다.** C66 wide mean/pct + gene_index + cell_type_summary를 먼저 주시면 됩니다. long은 1개 dataset subset(예: 2–3M rows)으로 별도 테스트하는 것을 권장합니다.

**G21. 파일 전달 위치·이름 규칙이 있나요?**

아래 레이아웃을 제안합니다.

```
hypomap_C66/
├── seqviewer_manifest.json
└── datasets/
    ├── hypomap_C66_wide_mean.parquet
    ├── hypomap_C66_wide_pct.parquet
    ├── hypomap_gene_index.parquet
    └── hypomap_cell_type_summary.parquet
```

- `seqviewer_manifest.json`은 폴더 루트
- parquet은 `datasets/` 하위
- `file_path`에는 **파일명만** 기재 (경로 금지)
- C185는 별도 폴더/별도 manifest entry로 분리

---

### H. Fallback

**H22. 10.6M rows가 불가하면 현실적인 대안은?**

권장 순서:

1. **(a) wide matrix + gene_index** — v1. 유전자 탐색/heatmap/dot plot에 충분하며 구현 범위가 가장 작음
2. **(c) DuckDB-backed endpoint/lazy table** — v2. long 전체가 꼭 필요할 때
3. **(b) gene별 top-N + on-demand full table** — 중간 단계
4. **(d) cell-level viewer(cellxgene/UCSC Cell Browser)** — 세포 단위 raw expression 탐색이 필요할 때 별도 뷰어

---

## 3. 권장 v1 export bundle

### 3.1 파일

| 파일 | 내용 |
|------|------|
| `hypomap_C66_wide_mean.parquet` | `gene_id`, `gene_name`, 66 cell type numeric columns |
| `hypomap_C66_wide_pct.parquet` | 동일 shape, `pct_expressing` |
| `hypomap_gene_index.parquet` | `gene_id`, `gene_name`, `max_mean`, `max_pct`, `n_cell_types_detected` |
| `hypomap_cell_type_summary.parquet` | `cell_type`, `n_cells`, `dataset` 구성 |

### 3.2 manifest 예시

```json
{
  "datasets": [
    {
      "alias": "HypoMap C66 mean expression",
      "file_path": "hypomap_C66_wide_mean.parquet",
      "dataset_type": "expression_summary",
      "organism": "Mus musculus",
      "notes": "HypoMap C66; mean normalized expression",
      "tags": ["HypoMap", "C66", "expression"],
      "expression_schema": {
        "schema_version": "1.0",
        "layout": "wide",
        "value_type": "mean_expression",
        "cell_type_level": "C66",
        "gene_id_type": "symbol",
        "normalization": "log1p_normalized",
        "detection": "count > 0",
        "pct_scale": "0-1",
        "companion_files": {
          "pct": "hypomap_C66_wide_pct.parquet",
          "gene_index": "hypomap_gene_index.parquet",
          "cell_type_summary": "hypomap_cell_type_summary.parquet"
        },
        "source": "HypoMap",
        "license": "CC BY 4.0"
      }
    }
  ]
}
```

> **중요:** `dataset_type: "expression_summary"`는 **현재 코드에 구현되어 있습니다.** wide mean/pct + companion 파일을 `Import Folder`로 등록하면 DB Browser에서 열 수 있습니다. (구현 전 임시 검증용으로는 `dataset_type: "multi_group"`을 사용할 수 있었지만, 이제 권장하지 않습니다.)

---

## 4. 단계별 개발 계획 및 담당

### Phase 0 — sample bundle 검증 (완료)

- `output_hypomap_c66_expression`, `output_hypomap_dowsett_long` 검증 완료
- 결과는 아래 **8. Sample bundle 검증 결과** 참고

### Phase 1 — `expression_summary` 타입 (구현 완료, 담당: 뷰어 팀)

- `DatasetType.EXPRESSION_SUMMARY` 추가
- `ExpressionSummaryLoader` (wide mean/pct + gene_index + cell_type_summary; per-dataset long ≤5M rows pivot 지원)
- manifest `expression_schema` 파싱, DB Import Folder 지원
- **Gene × Cell-Type Dot Plot** (size=pct, color=mean) + top-N Heatmap
- gene 검색(`gene_id`/`gene_name`, 대소문자 무시), n_cells 회색 처리
- “Expression summary” 라벨/타입 표시
- F1/파이프라인 문서·테스트
- 상태: wide layout + companion + dot plot/heatmap + gene 검색 + CLI/DB import 구현 완료
  (per-dataset long ≤5M rows는 pivot으로 지원, 전체 10.6M은 v2)

### Phase 2 — full atlas long / DuckDB (담당: 뷰어 팀)

- 5M 초과 long(전체 10.6M) parquet을 DuckDB/Arrow로 lazy 로딩
- gene lookup / top cell types / pct filter predicate pushdown
- `dataset` facet filter, pagination
- 기간: 대략 2주+ (의존성·배포 영향 검토 포함)

---

## 5. 성능 목표 (v1)

| 동작 | 목표 |
|------|------|
| wide mean/pct 초기 로드 | < 5초 |
| gene_index lookup | < 200ms |
| dot plot 렌더 | < 2초 |
| heatmap top-N (≤500 genes × 185 cell types) | < 5초 |
| 필터 적용 | < 2초 |

5M 초과 long table(전체 10.6M)은 v1 목표에서 제외합니다. per-dataset long(≤5M)은 pivot으로 지원합니다.

---

## 6. sample bundle 요청 사항

1. **C66 wide mean/pct 전체** (57k × 66) — 우선
2. **gene_index 전체** — 우선
3. **cell_type_summary 전체** — 우선
4. **long table은 1개 dataset subset** (예: 2–3M rows) — Phase 2 검증용
5. manifest에는 `expression_schema`, `organism`, `source`, `license` 포함
6. 전달 위치: `hypomap_C66/` 폴더 (manifest 루트 + `datasets/`)

---

## 7. 협의가 필요한 사항

1. **v1 범위**: wide + gene_index만 먼저 진행할지 (권장), long까지 포함할지
2. **C66/C185**: 별도 dataset entry로 분리할지 (권장), `cell_type_level` 단일 테이블로 갈지
3. **per-dataset 테이블**: v1에서 제외해도 되는지 (권장: 제외)
4. **pct_scale**: 0–1인지 0–100인지 manifest에 명시
5. **gene_id_type**: symbol/Ensembl 중 무엇을 `gene_id`로 쓸지
6. **dot plot**: v1 필수 기능으로 포함할지 (권장: 포함)

---

## 8. Sample bundle 검증 결과 (2026-10-20)

전달해 주신 두 bundle을 실제로 Import Folder → DB → Expression Summary 뷰까지 검증했습니다.

### 8.1 `output_hypomap_c66_expression`

| 항목 | 결과 |
|------|------|
| wide mean | 57,362 genes × 65 cell types (C66_named, min_cells=10) |
| wide pct | 동일 shape, `pct_expressing` 0–100 |
| manifest | 파이프라인 고유 `manifest.json` 자동 인식 |
| DB import | 성공 (companion 포함, 약 1초) |
| DB load | 성공 (약 0.2초) |
| pct_scale | pct 최대값을 보고 `0-100` 자동 판별 |
| dot plot | `Malat1`, `Xkr4` 등 gene 검색/표시 확인 |
| gene_index | `max_mean_expression`/`max_pct_expressing` alias 인식 |
| long table | 1,916,602 rows — long-only일 때 pivot으로 로드 성공 (약 5–6초) |

### 8.2 `output_hypomap_dowsett_long`

| 항목 | 결과 |
|------|------|
| wide mean | 57,362 genes × 139 cell types (`cell_type || Dowsett10xnuc`) |
| cell_type_summary | 139 rows, `dataset` 컬럼 포함 → combined label 매핑 확인 |
| DB import | 성공 (약 0.4초) |
| DB load | 성공 (약 0.3초) |
| long table | 2,593,263 rows — long-only일 때 pivot으로 로드 성공 (약 5–6초, 57,362 genes × 139 cell types) |
| 전체 atlas long | 10.6M rows는 v1 pivot 한도(5M) 초과 → v2 DuckDB |

### 8.3 확인된 규약

- `pct_expressing`은 **0–100**으로 내보내 주세요. 앱이 pct 행렬 최대값으로 자동 판별하지만,
  manifest/`COLUMNS.md`에 명시하면 더 안전합니다.
- `gene_index`의 `max_mean_expression`/`max_pct_expressing` 이름은 그대로 사용해도 됩니다.
- `cell_type_summary`에 `dataset` 컬럼이 있으면 wide의 `cell_type || dataset` 라벨과
  자동으로 매핑됩니다.
- long은 per-dataset(≤5M rows)까지 pivot으로 지원합니다. 전체 10.6M rows는 wide 권장.

---

## 9. 참고 문서

- `docs/developer/pipeline-integration.md` — 전체 연동 규격
- `docs/developer/pipeline-integration-response.md` — 기존 Q1~Q7/R1 회신
- `docs/user/help/19-command-line-interface.md` — CLI 검증
- `docs/user/help/20-cell-type-composition.md` — Composition 뷰

---

문의나 추가 스키마 요청은 이 저장소 이슈로 남겨 주세요.
