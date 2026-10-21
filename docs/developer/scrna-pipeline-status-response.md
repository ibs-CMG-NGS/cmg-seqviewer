# cmg-seqviewer 현재 버전 및 scRNA-seq 파이프라인 번들 호환성 — 회신

- **수신**: scRNA-seq 3차 분석 파이프라인 (`ibs-CMG-NGS/sc-rna-seq-analysis-r`)
- **발신**: cmg-seqviewer 개발팀
- **기준 코드**: branch `feat/cli`, commit `46a491a` (2026-10-20), v1.3.2 기반
- **검증 환경**: Linux, Python 3.12, pytest 330 passed

> **검증 완료**: `C:\Users\KimYG\Desktop\output`의 실제 번들을 Import Folder → DB →
> Expression Summary/Composition 뷰까지 검증했습니다. 아래 결과는 실측값입니다.

---

## 1. viewer version / commit / branch

| 항목 | 값 |
|------|----|
| version | **v1.3.2 기반 + 미릴리스 통합 커밋** |
| branch | `feat/cli` |
| commit | `46a491a` (`feat(expression): support HypoMap pipeline manifests and long exports`) |
| commit date | 2026-10-20 |
| 다음 릴리스 | **v1.4.0** 권장 (새 DatasetType 2종 + mixed bundle 대응) |

v1.3.2 이후 `seqviewer_manifest.json` Import 로직 변경:

- `composition` / `expression_summary` DatasetType 추가
- 파이프라인 고유 `manifest.json`(`table=expression`, `files={...}`) 자동 인식
- `expression_schema` 저장/복원
- `file_path`/`original_filename`/`alias`/`dataset_id` 누락 시 자동 보완
- Import Folder에서 폴더명 `/YYYY-initials-organism-type/` 기반 researcher/date 추론
- mixed bundle에서 지원 타입만 Import하고 미지원 타입은 skip

---

## 2. 지원 DatasetType 목록

현재 `DatasetType` enum 값:

```
differential_expression
go_analysis
multi_group
atac_seq
multi_omics
motif_enrichment
tf_footprint
chromvar_diff_tf
composition
expression_summary
unknown
```

별칭도 허용:

- `differential_accessibility` → `atac_seq`
- `time_series`, `coexpression_module` → `multi_group`
- `cell_composition`, `composition_analysis` → `composition`
- `expression_atlas`, `cell_type_expression` → `expression_summary`

**v1.3.2에서 문제가 되었던 `composition`, `expression_summary` 모두 현재 지원됩니다.**

---

## 3. composition 지원 여부 / 스키마

**지원합니다.** 파이프라인의 현재 컬럼을 **그대로 사용할 수 있습니다.**

| 컬럼 | viewer 처리 |
|------|-------------|
| `cell_type` | 표준 `cell_type` |
| `PropMean.Normal.chow` | 조건 평균 비율 (원본 이름 유지, 조건명 `Normal.chow`) |
| `PropMean.Fasted` | 조건 평균 비율 (조건명 `Fasted`) |
| `PropRatio` | 표준 `prop_ratio` |
| `Tstatistic` | 추가 컬럼으로 보존 (현재 plot에는 미사용) |
| `P.Value` | 표준 `pvalue` |
| `FDR` | 표준 `fdr` |

- 자동 감지 조건: `cell_type` + `PropMean.*` 2개 이상(또는 `PropRatio`) + p-value/FDR
- long format으로 바꿀 필요 없습니다.
- 화면: **Visualization → 🧫 Cell-Type Composition**
  - PropRatio 막대 (FDR 유의성 색/별표)
  - 조건별 평균 비율 그룹 막대
  - FDR 필터, Top N, Export/Bundle/Pin

---

## 4. expression_summary 지원 여부 (wide/long)

**지원합니다.**

### wide (권장)

- `gene_id`, `gene_name`, cell type별 mean 컬럼
- companion: `pct_expressing`, `gene_index`, `cell_type_summary`
- 57,362 × 184 wide도 수용 가능 (139 columns 실측, 메모리 약 100–150MB)
- companion은 **별도 dataset으로 넣지 말고** `expression_schema.companion_files`에
  지정해 주세요. viewer가 같은 폴더에서 읽습니다.

### long

- per-dataset long은 **최대 5,000,000 rows**까지 pivot으로 지원
- Dowsett long 2,593,263 rows: 로드 약 **5–6초** (57,362 genes × 139 cell types)
- 전체 atlas 10.6M rows는 v1 한도 초과 → wide 사용 또는 v2 DuckDB 대기
- long-only 번들도 `expression_schema.layout: "long"`이면 동작합니다.

### `expression_schema.companion_files`

viewer가 읽습니다. 다음 키를 사용합니다.

```json
"companion_files": {
  "pct": "expression_wide_pct.parquet",
  "gene_index": "gene_index.parquet",
  "cell_type_summary": "cell_type_summary.parquet"
}
```

값은 basename 또는 `datasets/<filename>` 모두 허용합니다(importer가 basename으로 정규화).

추가로 `cell_type_dataset_counts`, `skipped_groups`도 companion_files에 넣으면
DB로 함께 복사됩니다(현재 UI에서는 직접 사용하지 않음).

---

## 5. manifest 스키마 변경 사항

### 새로 추가된 필드 (모두 optional)

- `expression_schema` (object) — expression_summary 전용
- `cell_type_count` (int) — expression_summary 세포타입 수 (표시/요약용)
- `expression_schema.companion_files` (object)
- `expression_schema.pct_scale` (`"0-1"` 또는 `"0-100"`)
- `expression_schema.cell_type_columns` (array, optional)
- `expression_schema.by_dataset`, `dataset_column` (optional, informational)

### 기존 필드

- `dataset_type`은 **필수**입니다. 자동 추론하지 않습니다.
- `file_path`/`original_filename`/`alias`/`dataset_id`는 하나 이상 있으면 나머지를 자동 보완합니다.
- `file_path`는 bundle root 기준 상대경로를 유지해 주세요. `datasets/foo.parquet` 또는
  `foo.parquet` 모두 동작합니다. `../`나 절대경로는 사용하지 마세요.
- `dataset_id` 중복 처리 규칙은 동일합니다. 같은 ID는 skip, 누락 시 파일명 기반 uuid5.
- top-level `schema_version`은 받아들이지만 현재 DB에는 저장하지 않습니다.
  dataset별 `expression_schema.schema_version`은 저장됩니다.

### expression_schema 필수/권장

| 필드 | 필수 | 비고 |
|------|------|------|
| `layout` | ✅ | `"wide"` 또는 `"long"` |
| `companion_files` | 권장 | pct/gene_index/cell_type_summary |
| `pct_scale` | 권장 | `"0-100"` (파이프라인 현재 값) |
| `cell_type_level` | 권장 | `C66_named`, `C185_named` |
| `gene_id_type` | 권장 | `symbol` |
| `value_type` | 선택 | 기본 `mean_expression` |
| `cell_type_columns` | 선택 | 자동 추론이 어려운 wide 표에서 명시 |

---

## 6. mixed bundle 동작

**지원 타입만 Import하고, 미지원 타입은 skip합니다. bundle 전체를 거부하지 않습니다.**

- `tutorial_compare` (69개, 모두 지원 타입): **69 imported**
- v1.3.2에서 composition 1개가 skip되던 현상은 현재 해결됨
- 지원하지 않는 `dataset_type`이 섞여 있으면 해당 항목만 skip되고 나머지는 Import
- 주의: importer의 `skipped_no_file` 카운터는 "파일 없음"뿐 아니라 "metadata 항목
  파싱 실패"도 포함합니다. 로그에 구체적인 사유가 남습니다.

---

## 7. Import 테스트 결과 (실측)

### 7.1 `tutorial_compare` (69 datasets)

- imported: **69**
- skipped_duplicate: **0**
- skipped_no_file: **0**
- 오류 로그: 없음
- DB dataset 수: **69**
- Import 시간: **약 1.6초**
- 타입별 load 확인: DE(24,506 rows) / GO(89 terms) / Composition(10 rows) / Multi-Group(57,362 rows) 모두 정상

### 7.2 `hypomap_expression` (C185 wide, 57,362 × 184)

- imported: **1**
- skipped_duplicate: **0**
- skipped_no_file: **0**
- DB dataset 수: **1**
- Import **0.64초**, load **0.40초**
- 184 cell types, companions(pct/gene_index/cell_type_summary) 모두 로드
- Expression Summary 다이얼로그 **0.45초**, dot plot/heatmap 정상

### 7.3 `hypomap_c66_expression` (C66 wide, 57,362 × 65)

- imported: **1**
- skipped_duplicate: **0**
- skipped_no_file: **0**
- DB dataset 수: **1**
- Import **0.38초**, load **0.09초**
- 65 cell types, companions 모두 로드
- Expression Summary 다이얼로그 **0.30초**, gene 검색/heatmap 정상

### 7.4 `hypomap_dowsett_long` (long, 2,593,263 rows, 139 cell types)

- imported: **1**
- skipped_duplicate: **0**
- skipped_no_file: **0**
- DB dataset 수: **1**
- Import **0.51초**, long pivot load **6.53초**
- 57,362 genes × 139 cell types로 복원, companions 모두 로드
- Expression Summary 다이얼로그 **0.30초**, pct_scale `0-100`

### 7.5 C66 multi_group fallback

- imported: **1**
- skipped_duplicate: **0**
- skipped_no_file: **0**
- DB dataset 수: **1**
- load 정상 (`multi_group`, 57,362 rows, 65 sample columns)

## 8. 표시/탐색 가능한 기능

### composition

- **Visualization → 🧫 Cell-Type Composition**
- PropRatio 막대 (증가/감소 색, FDR 별표)
- 조건별 평균 비율 그룹 막대 (`PropMean.*`)
- FDR 필터, Top N, 정렬
- Export Data / Export Bundle / Pin to Tab
- Filter Panel Statistical 탭에서 FDR 필터

### expression_summary

- **Visualization → 🧬 Gene × Cell-Type Expression**
- gene_id/gene_name 검색 (대소문자 무시, 다중 선택)
- dot plot: size = `pct_expressing`, color = `mean_expression`
- top-N heatmap (mean)
- `n_cells` threshold 미만 회색 처리
- gene_index 정보 (`max_mean_expression`, `max_pct_expressing`, `top_cell_type`)
- cell type tooltip에 `n_cells`, `n_genes_detected`, `top_dataset` 표시
- Export Data / Export Bundle / Pin to Tab

### wide vs long UI 차이

없습니다. long은 로드 시 wide로 pivot되므로 동일한 화면을 사용합니다. 단, long은
초기 로드가 더 느립니다(2.6M rows 기준 약 5–6초).

---

## 9. DB migration 필요 여부

**필요 없습니다.**

- DatasetType 추가는 DB schema 변경이 아닙니다.
- 기존 `metadata.json`/parquet과 공존 가능합니다.
- 새 dataset은 additive로 추가됩니다.
- 단, **v1.3.2 이하 viewer는 새 DatasetType을 읽지 못합니다.** 새 번들을 사용하려면
  viewer를 업그레이드해야 합니다.
- 다운그레이드 전에는 DB 백업을 권장합니다.

---

## 10. multi_group fallback 유지 여부

**현재 viewer에서는 fallback이 필요 없습니다.** `expression_summary`가 정식 지원되므로
C66 fallback을 제거해도 됩니다.

권장:

- 새 viewer 배포가 완료될 때까지 **한 릴리스 정도만** fallback을 유지
- fallback과 `expression_summary`를 **같은 DB에 동시에 Import하지 않기**
  (동일 데이터가 두 dataset으로 보임)
- fallback을 유지한다면 alias/tags에 `fallback`을 표시해 구분

---

## 11. known issues / 제약

1. **long 5M rows 초과**: 전체 10.6M rows long은 v1에서 거부됩니다. wide 사용 또는
   v2 DuckDB loader가 필요합니다.
2. **wide 57k × 184**: 메모리 약 100–150MB, 로드 <1초 수준으로 문제 없습니다.
   단, heatmap은 top-N만 렌더합니다(전체 57k × 184 렌더는 지원하지 않음).
3. **gene alias/synonym 검색**: 대소문자 무시 substring만 지원합니다. synonym 검색은
   아직 없습니다.
4. **mixed bundle skip counter**: `skipped_no_file`이 metadata 파싱 실패도 포함합니다.
5. **`Tstatistic`**: composition에서 보존되지만 현재 plot에는 사용하지 않습니다.
6. **fallback 중복**: fallback과 expression_summary를 함께 Import하면 중복 dataset이
   생깁니다.
7. **old viewer**: v1.3.2 이하에서는 `composition`/`expression_summary`가
   `'... is not a valid DatasetType'`으로 실패합니다.

---

## 12. 파이프라인에 요청할 변경 사항

우선순위 순:

1. **현재 번들 형식 유지** — `output/.../export/seqviewer`의 실제 번들(C185 184 columns 포함)을
   검증했으므로 스키마 변경은 필요 없습니다. 추가 run도 같은 형식으로 전달해 주세요.
2. **`expression_schema.layout`/`companion_files`/`pct_scale` 유지** — 현재 구조 그대로
   사용 가능합니다. `pct_scale`은 `"0-100"`으로 명시해 주세요.
3. **`file_path`는 `datasets/<filename>` 형태의 상대경로 유지** — 절대경로/`../` 금지.
4. **전체 atlas는 wide 권장, long은 per-dataset만** — long 5M rows 한도.
5. **composition은 현재 컬럼 유지** — `Tstatistic`은 추가 컬럼으로 두어도 됩니다.
6. **fallback 제거 시점** — 새 viewer 배포 후 한 릴리스 뒤 제거 권장.
7. **`dataset_type`은 항상 명시** — 자동 추론하지 않습니다.
8. **`tags`는 문자열 배열**로 유지.

---

## 13. 다음 액션

1. 파이프라인 팀: 추가 run이 생기면 동일 형식으로 번들 전달 (현재 형식 유지)
2. viewer 팀: v1.4.0 릴리스 준비 (version bump + build)
3. 파이프라인 팀: 새 viewer 배포 후 multi_group fallback 제거 검토
4. 양측: C185 184-column/full long의 실제 사용성 피드백 공유

문의나 추가 스키마 요청은 이 저장소 이슈로 남겨 주세요.
