# ATAC-seq 3차 파이프라인 — SeqViewer 패키징 개선 요구사항

## 배경

`2026-ljh-hiy-human-atac`(human) 결과를 CMG-SeqViewer Database Browser로 들여오는 과정에서
세 가지 문제를 발견했다. 셋 모두 **앱 버그가 아니라 3차 분석 파이프라인이 `seqviewer/datasets/`
패키지를 만들 때 빠뜨린 부분**이며, 다음 파이프라인 개선 시 반영이 필요하다.

---

## 문제 1: `tf_variability.csv`가 `datasets/` 패키지에서 빠짐

### 증상

`seqviewer/datasets/`에는 `*_chromVAR_DiffTF.parquet`이 들어있지만, TF 이름 조회용
`chromvar/tf_variability.csv`는 포함되어 있지 않다. 이 폴더만 따로 떼어 Database Browser의
"Import Folder"로 불러오면 TF 이름이 JASPAR ID(`MA0004.1` 등)로만 표시되고 실제 유전자
심볼(`Arnt`, `Ahr::Arnt` 등)이 뜨지 않는다.

### 원인

CMG-SeqViewer의 chromVAR 로더는 parquet 파일이 있는 폴더부터 상위 3단계까지 디렉토리를
훑어 `tf_variability.csv`를 자동으로 찾는다. 파이프라인 결과 폴더 전체
(`.../chromvar/tf_variability.csv` vs `.../seqviewer/datasets/*.parquet`)를 그대로 옮기면
상위 디렉토리 관계가 유지되어 자동으로 찾아지지만, **`seqviewer/datasets/` 폴더만 분리해서
배포하면 상위 경로 관계가 끊어져 찾지 못한다.**

### 요구사항

`seqviewer/datasets/` 패키지(및 `seqviewer_import.zip`)를 만드는 단계에서
`chromvar/tf_variability.csv`를 **같은 `datasets/` 폴더에 평평하게(서브폴더 없이) 같이
복사**해야 한다.

```
seqviewer/datasets/
├── Acute_1D_vs_Control_chromVAR_DiffTF.parquet
├── Acute_1D_vs_Control_DA.parquet
├── Acute_1D_vs_Control_GO_KEGG.parquet
├── ...
└── tf_variability.csv          ← 추가 필요 (chromVAR 데이터셋이 1개라도 있으면 항상 포함)
```

chromVAR 비교가 여러 개라도 `tf_variability.csv`는 프로젝트당 1개만 생성되므로, 모든
`*_chromVAR_DiffTF.parquet`이 이 파일 하나를 공유해서 참조하면 된다.

---

## 문제 2: ATAC parquet에 실험 메타데이터가 채워지지 않음

### 증상

Database Browser에서 RNA-seq 계열 데이터셋(DE/GO, mouse)은 Condition, Organism, Tags가
모두 채워져 있는데, ATAC DA 데이터셋(`1D_vs_CONTROL_DA` 등)은 Condition/Cell Type/Organism이
공란이고 Tags도 `-`로 비어 있다.

| Alias | Condition | Organism | Tags |
|---|---|---|---|
| Acute_1D vs Control DE | Acute_1D vs Control | mouse | DE, Acute_1D, Control |
| 1D_vs_CONTROL_DA | *(공란)* | *(공란)* | `-` |

### 이미 존재하는 좋은 예시 — `seqviewer_manifest.json`

human-atac 파이프라인이 만든 `seqviewer/seqviewer_manifest.json`과
`seqviewer/staging/*_entries.json`을 보면, 이미 아래 정보를 정확히 채워서 만들고 있다:

```json
{
  "alias": "Acute_1D vs Control DA",
  "dataset_type": "differential_accessibility",
  "experiment_condition": "Acute_1D vs Control",
  "organism": "human",
  "row_count": 186199,
  "peak_count": 186199,
  "significant_peaks": 16538,
  "padj_cutoff": 0.05,
  "log2fc_cutoff": 0.585,
  "tags": ["DA", "ATAC", "Acute_1D", "Control"]
}
```

**이 포맷을 모든 ATAC 파이프라인 실행에 일관되게 적용하는 것이 목표다.** 이번 human-atac
실행에서는 이미 잘 만들어졌지만, 그 외 비교조건(mouse 등)에서는 만들어지지 않거나
일부만 채워진 경우가 있었다.

### 요구사항: 채워야 할 필드

파이프라인이 실행 시점에 이미 알고 있는 정보이므로, 추가 분석 없이 그대로 기록만 하면 된다.

| 필드 | 채울 값 | 파이프라인이 이미 아는 값인가? |
|---|---|---|
| `experiment_condition` | 비교 조건명 (예: `Acute_1D vs Control`) | ✅ 비교 설정값 |
| `organism` | 종 (`human`/`mouse` 등) | ✅ config_used.yml에 존재 |
| `genome_build` | 참조 게놈 (`hg38`, `mm10` 등) | ✅ config_used.yml에 존재 |
| `peak_caller` | Peak calling 툴 (예: `MACS2`) | ✅ 파이프라인 설정값 |
| `row_count` / `peak_count` | 전체 peak/TF/term 수 | ✅ DataFrame 길이 |
| `significant_peaks` | padj/log2FC 컷오프 통과 개수 | ✅ DA 분석 결과 |
| `padj_cutoff` / `log2fc_cutoff` | 분석에 사용한 임계값 | ✅ config_used.yml에 존재 |
| `tags` | `["DA"/"GO"/"chromVAR", "ATAC", 조건1, 조건2]` | ✅ 비교 설정값으로 자동 생성 가능 |
| `cell_type` / `tissue` / `timepoint` | 실험 메타데이터 | ⚠️ 샘플 메타데이터 CSV에 있으면 채우고, 없으면 공란 유지(허용) |

→ 이미 human-atac 파이프라인이 `seqviewer_manifest.json`에서 거의 다 하고 있으므로,
**이 manifest 생성 로직을 모든 ATAC 프로젝트 실행에 빠짐없이 적용**하는 것이 핵심이다.

### ⚠️ 앱 측 후속 작업 (참고)

위 manifest/staging json을 파이프라인이 잘 만들어도, **현재 CMG-SeqViewer의
"Import Folder" 기능은 이 JSON을 읽지 않고 parquet 컬럼만 보고 타입을 추측한다**
(`organism`, `experiment_condition`, `tags` 등은 채우지 않음). 즉 지금 이 요구사항만으로는
Database Browser에 자동으로 반영되지 않으며, 앱 쪽에도 "Import Folder 시
`seqviewer_manifest.json`이 있으면 우선 사용" 로직 추가가 필요하다 — 이건 별도로 앱 개발
backlog에 등록할 것.

---

## 문제 3: GO/KEGG parquet에 분석 메타데이터 행이 데이터와 섞임

### 증상

CMG-SeqViewer에서 GO/KEGG 데이터셋을 열면 테이블 하단에 아래와 같이
모든 컬럼이 `nan`인 행들이 보인다:

| ontology | category  | term_id | description | … |
|----------|-----------|---------|-------------|---|
| Info     | *(NaN)*   | *(NaN)* | *(NaN)*     | … |
| Info     | *(NaN)*   | *(NaN)* | *(NaN)*     | … |

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
...
```

RNA-seq GO/KEGG parquet 파일에서도 동일하게 발생한다.

### 원인

파이프라인 R 스크립트가 분석 파라미터와 통계 요약값을 결과 DataFrame의
하단에 `ontology = "Info"` 행으로 이어붙인 뒤 parquet(또는 Excel)으로 저장한다.
CMG-SeqViewer는 이 행들을 일반 GO term 행과 구분 없이 읽기 때문에 테이블에 노출된다.

### 올바른 위치 — `seqviewer_manifest.json`

이 정보들은 이미 `seqviewer_manifest.json`에 넣을 수 있는 필드들과 완전히 겹친다:

| `Parameter` 값 | manifest 필드 |
|---|---|
| `Comparison` | `experiment_condition` |
| `DE Method` | *(신규 필드 `de_method` 추가 권장)* |
| `P-value Cutoff (padj)` | `padj_cutoff` |
| `Log2FC Cutoff` | `log2fc_cutoff` |
| `Species` | `organism` |
| `Total GO Terms Found` | `row_count` |
| `Analysis Date` | *(신규 필드 `analysis_date` 추가 권장)* |

### 요구사항

GO/KEGG parquet(및 Excel) 파일을 저장하기 전에, R 스크립트에서 `ontology = "Info"` 행과
`Parameter` / `Value` 컬럼을 제거한다. 해당 정보는 `seqviewer_manifest.json`에만 기록한다.

```r
# 변경 전 (현재)
final_df <- bind_rows(go_results, info_rows)   # Info 행을 결과에 이어붙임
write_parquet(final_df, output_path)

# 변경 후
# Info 행은 manifest에만 기록하고 parquet에는 넣지 않음
write_parquet(go_results, output_path)         # 순수 GO/KEGG term 행만 저장
```

### ⚠️ 앱 측 방어 처리 (이미 완료, 참고)

**CMG-SeqViewer v1.2.4 이상**에서는 로드 시 `ontology = 'Info'` 행과
`Parameter` / `Value` 컬럼을 자동으로 제거하는 방어 로직이 추가되어 있다
(`go_kegg_loader.py`, `data_loader.py`). 이 조치는 기존 parquet 파일과의 호환성을
위한 것이며, 파이프라인 측 수정이 근본 해결책이다.

---

## 체크리스트 (다음 파이프라인 개선 시)

- [ ] `seqviewer/datasets/`에 `tf_variability.csv` 포함 (chromVAR 데이터셋 존재 시)
- [ ] 모든 ATAC 프로젝트 실행에서 `seqviewer_manifest.json` + `seqviewer/staging/*_entries.json` 생성을 표준화
- [ ] manifest에 `genome_build`, `peak_caller` 필드 추가 (현재는 빠져 있음)
- [ ] GO/KEGG parquet 저장 전 `ontology='Info'` 행 및 `Parameter`/`Value` 컬럼 제거 — manifest에만 기록
- [ ] manifest에 `de_method`, `analysis_date` 필드 추가 (GO Info 행에서 이동)
- [ ] (앱 측, 별도 작업) Database Browser "Import Folder"가 manifest를 읽도록 개선
