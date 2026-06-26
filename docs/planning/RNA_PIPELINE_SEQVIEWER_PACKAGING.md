# RNA-seq 3차 파이프라인 — SeqViewer 패키징 개선 요구사항

## 배경

RNA-seq DE/GO 분석 결과를 CMG-SeqViewer Database Browser로 들여올 때
메타데이터(Condition, Organism, Tags 등)가 비어 있거나 불완전한 경우가 있다.
또한 랩 내부에서 동일·유사 조건으로 여러 연구자가 반복 분석한 데이터를
한 곳에 모아 비교하는 것이 이 프로그램의 핵심 용도이므로,
**누가 언제 어떤 조건으로 분석했는지** 를 명확히 구별할 수 있어야 한다.

아래 요구사항은 모두 **앱 버그가 아니라 파이프라인이 `seqviewer/datasets/` 패키지를
만들 때 빠뜨리거나 표준화하지 않은 부분**이며, 다음 파이프라인 개선 시 반영이 필요하다.

---

## 문제 1: GO/KEGG parquet에 분석 메타데이터 행이 데이터와 섞임

### 증상

CMG-SeqViewer에서 GO/KEGG 데이터셋을 열면 테이블 하단에 아래와 같이
모든 컬럼이 `nan`인 행들이 보인다:

| ontology | category | term_id | description | … |
|---|---|---|---|---|
| Info | *(NaN)* | *(NaN)* | *(NaN)* | … |

이 행들에는 `Parameter` / `Value` 컬럼에만 값이 있으며, 실제로는 분석 파라미터 요약이다:

```
Parameter               Value
Comparison              1D vs CONTROL
Analysis Date           2026-06-22
DE Method               DESeq2
P-value Cutoff (padj)   0.05
Log2FC Cutoff           1
GO P-value Cutoff       0.05
GO Q-value Cutoff       0.25
Species                 mouse
Organism Database       org.Mm.eg.db
Total GO Terms Found    32519
```

### 원인

파이프라인 R 스크립트가 분석 파라미터와 통계 요약값을 결과 DataFrame의
하단에 `ontology = "Info"` 행으로 이어붙인 뒤 parquet(또는 Excel)으로 저장한다.

### 요구사항

GO/KEGG parquet(및 Excel) 파일 저장 전, R 스크립트에서 `ontology = "Info"` 행과
`Parameter` / `Value` 컬럼을 **제거**한다. 해당 정보는 `seqviewer_manifest.json`에만 기록한다.

```r
# 변경 전 (현재)
final_df <- bind_rows(go_results, info_rows)   # Info 행을 결과에 이어붙임
write_parquet(final_df, output_path)

# 변경 후
# Info 행은 manifest에만 기록하고 parquet에는 넣지 않음
write_parquet(go_results, output_path)         # 순수 GO/KEGG term 행만 저장
```

| `Parameter` 값 | 이동할 manifest 필드 |
|---|---|
| `Comparison` | `experiment_condition` |
| `DE Method` | `de_method` |
| `P-value Cutoff (padj)` | `padj_cutoff` |
| `Log2FC Cutoff` | `log2fc_cutoff` |
| `Species` | `organism` |
| `Organism Database` | `gene_database` |
| `Total GO Terms Found` | `row_count` |
| `Analysis Date` | `analysis_date` |

### ⚠️ 앱 측 방어 처리 (이미 완료, 참고)

**CMG-SeqViewer v1.2.4 이상**에서는 로드 시 `ontology = 'Info'` 행과
`Parameter` / `Value` 컬럼을 자동으로 제거하는 방어 로직이 추가되어 있다
(`go_kegg_loader.py`, `data_loader.py`). 이 조치는 기존 parquet 파일과의 호환성을
위한 것이며, 파이프라인 측 수정이 근본 해결책이다.

---

## 문제 2: `seqviewer_manifest.json` 미생성 또는 불완전

### 증상

Database Browser에서 RNA-seq DE 데이터셋은 Condition, Organism, Tags가
공란이거나 일부만 채워진다.

| Alias | Condition | Organism | Tags |
|---|---|---|---|
| Acute_1D vs Control DE | Acute_1D vs Control | mouse | DE, Acute_1D, Control |
| 1D_vs_CONTROL_DE | *(공란)* | *(공란)* | `-` |

### 원인

RNA-seq 파이프라인이 `seqviewer_manifest.json`을 생성하지 않거나,
생성하더라도 일부 필드만 채우는 경우가 있다.

> ATAC 파이프라인의 human-atac 실행에서는 이미 잘 만들어진 포맷이 있으므로 이를 참고한다.

### 요구사항: 채워야 할 필드

파이프라인이 실행 시점에 이미 알고 있는 정보이므로, 추가 분석 없이 그대로 기록하면 된다.

| 필드 | 채울 값 | 파이프라인이 이미 아는 값인가? |
|---|---|---|
| `experiment_condition` | 비교 조건명 (예: `Acute_1D vs Control`) | ✅ 비교 설정값 |
| `organism` | 종 (`human`/`mouse` 등) | ✅ config_used.yml에 존재 |
| `genome_build` | 참조 게놈 (`hg38`, `mm10` 등) | ✅ config_used.yml에 존재 |
| `de_method` | DE 분석 툴 (`DESeq2`, `edgeR`, `limma`) | ✅ 파이프라인 설정값 |
| `gene_database` | 유전자 DB (`org.Mm.eg.db`, `org.Hs.eg.db` 등) | ✅ config_used.yml에 존재 |
| `row_count` / `gene_count` | 전체 유전자 수 | ✅ DataFrame 길이 |
| `significant_genes` | padj/log2FC 컷오프 통과 DEG 수 | ✅ DE 분석 결과 |
| `padj_cutoff` / `log2fc_cutoff` | 분석에 사용한 임계값 | ✅ config_used.yml에 존재 |
| `tags` | `["DE"/"GO", "RNA", 조건1, 조건2]` | ✅ 비교 설정값으로 자동 생성 가능 |
| `cell_type` / `tissue` / `timepoint` | 실험 메타데이터 | ⚠️ 샘플 메타데이터 CSV에 있으면 채우고, 없으면 공란 유지(허용) |

### ⚠️ 앱 측 후속 작업 (backlog)

현재 CMG-SeqViewer의 "Import Folder" 기능은 `seqviewer_manifest.json`을 읽지 않고
parquet 컬럼만 보고 타입을 추측한다. 파이프라인이 manifest를 잘 만들어도 앱 측
"Import Folder 시 manifest 우선 사용" 로직이 추가되어야 DB에 자동 반영된다 —
별도로 앱 개발 backlog에 등록.

---

## 문제 3: 연구자·프로젝트 메타데이터 부재

### 배경

랩 내부에서 동일하거나 유사한 실험 조건(예: `1D_vs_CONTROL`)으로 여러 연구자가
반복 분석을 수행할 경우, Database Browser에서 데이터셋을 구별하기 어렵다.

### 요구사항: 추가할 manifest 필드

| 필드 | 설명 | 예시 |
|---|---|---|
| `researcher` | 분석 담당자 이니셜 또는 이름 (복수 가능) | `"ljh"`, `["ljh", "hiy"]` |
| `project_name` | 연구 묶음 식별자 (논문/과제 단위) | `"2026-mouse-rna"`, `"timecourse-rna"` |
| `analysis_date` | 분석 실행일 (`YYYY-MM-DD`) | `"2026-06-25"` |

### 경로명 규칙 (현행 관행 표준화)

파이프라인 결과 폴더 최상위 이름에 연구자·날짜 정보를 포함하는 관행을 **공식 표준으로 유지**:

```
/2026-ljh-mouse-rna/           # YYYY-이니셜들-organism-type
/2025-hiy-human-rna/
/2025-ljh-hiy-mouse-atac/      # 복수 연구자
```

manifest가 없을 때 앱 측에서 이 경로명을 파싱하여 `researcher`와 `analysis_date`를
자동 추론하는 fallback이 가능하다.

### 목표 manifest 포맷 (전체 필드 — DE 데이터셋 예시)

```json
{
  "alias": "Acute_1D vs Control DE",
  "dataset_type": "differential_expression",
  "experiment_condition": "Acute_1D vs Control",
  "organism": "mouse",
  "genome_build": "mm10",
  "de_method": "DESeq2",
  "gene_database": "org.Mm.eg.db",
  "researcher": ["ljh"],
  "project_name": "2026-mouse-rna",
  "analysis_date": "2026-06-25",
  "row_count": 18432,
  "gene_count": 18432,
  "significant_genes": 1247,
  "padj_cutoff": 0.05,
  "log2fc_cutoff": 1.0,
  "tags": ["DE", "RNA", "Acute_1D", "Control", "ljh"]
}
```

### 목표 manifest 포맷 (GO/KEGG 데이터셋 예시)

```json
{
  "alias": "Acute_1D vs Control GO KEGG",
  "dataset_type": "go_kegg_enrichment",
  "experiment_condition": "Acute_1D vs Control",
  "organism": "mouse",
  "genome_build": "mm10",
  "de_method": "DESeq2",
  "gene_database": "org.Mm.eg.db",
  "go_pvalue_cutoff": 0.05,
  "go_qvalue_cutoff": 0.25,
  "researcher": ["ljh"],
  "project_name": "2026-mouse-rna",
  "analysis_date": "2026-06-25",
  "row_count": 32519,
  "tags": ["GO", "KEGG", "RNA", "Acute_1D", "Control", "ljh"]
}
```

> **tags에 researcher 포함 권장**: 텍스트 검색 시 연구자 이니셜로도 찾을 수 있도록
> tags 배열에 researcher 값을 자동 추가한다.

---

## 디렉토리 구조 (권장)

```
seqviewer/
├── seqviewer_manifest.json          ← 모든 데이터셋 메타데이터 목록
├── staging/
│   ├── 1D_vs_CONTROL_DE_entries.json
│   ├── 1D_vs_CONTROL_GO_KEGG_entries.json
│   └── ...
└── datasets/
    ├── Acute_1D_vs_Control_DE.parquet
    ├── Acute_1D_vs_Control_GO_KEGG.parquet
    └── ...
```

> RNA-seq 파이프라인도 ATAC과 동일한 `seqviewer/` 구조로 패키징하는 것을 목표로 한다.

---

## 체크리스트 (다음 파이프라인 개선 시)

- [ ] 모든 RNA 프로젝트 실행에서 `seqviewer_manifest.json` + `seqviewer/staging/*_entries.json` 생성을 표준화
- [ ] manifest에 `genome_build`, `de_method`, `gene_database` 필드 추가
- [ ] manifest에 `researcher`, `project_name`, `analysis_date` 필드 추가
- [ ] tags 배열에 researcher 이니셜 자동 포함
- [ ] GO/KEGG parquet 저장 전 `ontology='Info'` 행 및 `Parameter`/`Value` 컬럼 제거 — manifest에만 기록
- [ ] DE parquet에 `direction` 컬럼 포함 (`UP`/`DOWN`/`NS`, padj/log2FC 기준 자동 계산)
- [ ] 경로명 규칙 `/YYYY-이니셜-organism-type/` 표준으로 유지
- [ ] (앱 측, 별도 작업) Database Browser "Import Folder"가 manifest를 읽도록 개선
- [ ] (앱 측, 별도 작업) Researcher 필드 및 텍스트 검색 확장
