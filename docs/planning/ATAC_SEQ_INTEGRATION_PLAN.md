# ATAC-seq Integration Plan

## Status Overview

| Phase | 내용 | 상태 | 버전 |
|-------|------|------|------|
| **Phase 1** | ATAC-seq Standalone Analysis | ✅ **완료** | v1.2.0 (2026-04-30) |
| **Phase 2** | Multi-Omics Integration (RNA + ATAC) | ✅ **완료** | v1.2.1 (2026-05-31) |
| **Phase 3A** | TF Motif Enrichment Import & 시각화 | ✅ **완료** | v1.2.2 (2026-06-08) |
| **Phase 3B** | TF Footprinting (TOBIAS BINDetect) | ✅ **완료** | v1.2.2 (2026-06-08) |
| **Phase 3C** | chromVAR Differential TF Activity | ✅ **완료** | v1.2.2 (2026-06-09) |
| **Phase 3D** | Multi-Condition DA Peak Overlap (peak 좌표 기반) | ✅ **완료** | v1.2.3 (2026-06-18) |
| **Phase 3E** | Peak-Gene 발현 상관관계 (샘플별) | 🔮 **장기 계획** | — |
| **Phase 4** | Chromatin State / ChIP-seq / Hi-C | 🔮 **장기 계획** | — |

---

## Background

### RNA-seq vs ATAC-seq

| 특성 | RNA-seq | ATAC-seq |
|------|---------|----------|
| **측정 대상** | Gene expression | Chromatin accessibility |
| **분석 단위** | Gene/Transcript | Peak/Region |
| **통계 분석** | Differential Expression | Differential Accessibility |
| **출력 데이터** | gene_id, log2FC, padj | peak_id, chr, start, end, log2FC, padj |
| **생물학적 의미** | "무엇이 발현되는가?" | "어디가 열려있는가?" |

### 통합 분석의 가치

```
ATAC-seq (Chromatin Opening)  →  RNA-seq (Gene Expression)
        ↓                                    ↓
    Open Peak                          High Expression
        ↓                                    ↓
    [Integration Analysis]
        ↓
    Regulatory Mechanism
```

---

---

# ✅ Phase 1: ATAC-seq Standalone Analysis — 완료 (v1.2.0)

**완료일:** 2026-04-30  
**브랜치:** `feat/atac-seq-support`

## 구현된 내용

### 1.1 Data Model (완료)

#### `src/models/standard_columns.py`
```python
# 추가된 ATAC-seq 컬럼 상수
PEAK_ID = "peak_id"
CHROMOSOME = "chromosome"
PEAK_START = "peak_start"      # 계획의 START → PEAK_START로 변경
PEAK_END = "peak_end"          # 계획의 END → PEAK_END로 변경
NEAREST_GENE = "nearest_gene"
ANNOTATION = "annotation"
DISTANCE_TO_TSS = "distance_to_tss"
PEAK_WIDTH = "peak_width"      # peak_end - peak_start 자동 계산

# 헬퍼 메서드
get_atac_basic()   → [peak_id, chromosome, peak_start, peak_end, nearest_gene]
get_atac_stat()    → basic + [base_mean, log2fc, pvalue, adj_pvalue, direction]
get_atac_all()     → stat + [lfcse, annotation, distance_to_tss, gene_id, peak_width]
```

#### `src/models/data_models.py`
```python
# 추가된 타입
DatasetType.ATAC_SEQ = "atac_seq"

# FilterCriteria에 추가된 ATAC 필드
atac_annotation: str = "All"
atac_distance_max: Optional[int] = None
atac_peak_width_min: Optional[int] = None
atac_peak_width_max: Optional[int] = None

# PreloadedDatasetMetadata에 추가된 필드
genome_build: str = ""
peak_caller: str = ""
```

> **계획과의 차이:** `ATACSeqMetadata` 별도 dataclass는 만들지 않고,
> 기존 `PreloadedDatasetMetadata`에 필드를 추가하는 방식으로 구현.

---

### 1.2 ATAC-seq Loader (완료)

#### `src/utils/atac_seq_loader.py` (신규)

- `ATACSeqLoader.load(path)` — Excel / Parquet 자동 선택
- `is_atac_dataframe(df)` — `peak_id` 계열 컬럼 존재 여부로 판별
- `COLUMN_PATTERNS` — 14개 표준 컬럼에 대한 30+ 입력 이름 변형 지원
- `_map_and_build()` — 컬럼 매핑 + `peak_width` 계산 + `annotation_categories` 메타데이터 저장

**자동 감지 우선순위 (`data_loader.py`):**
1. ATAC-seq (`peak_id` 체크) ← 가장 먼저
2. Multi-Group
3. DE / GO 점수 비교

---

### 1.3 필터링 (완료)

#### `src/gui/filter_panel.py`

ATAC-seq 탭 활성 시 Statistical 탭에 ATAC-seq Filtering 섹션 표시:

| 필터 | UI | 동작 |
|------|----|------|
| **Annot** | 드롭다운 (동적) | `annotation` 컬럼 prefix 매칭 |
| **\|TSS\| ≤** | 숫자 입력 + "bp" | `abs(distance_to_tss) ≤ N` |
| **Peak Width** | min – max 입력 | `peak_width` 범위 필터 |

- Annotation 드롭다운 항목은 `metadata['annotation_categories']`에서 동적 생성
- ATAC 탭이 아닐 때는 섹션 숨김

---

### 1.4 시각화 (완료)

#### ✅ 기존 재사용
- **Volcano Plot** — log2fc + adj_pvalue 있으면 ATAC-seq에도 동작
- **Venn Diagram** — peak_id 기준 집합 비교

#### ✅ 신규 구현

**`src/gui/genomic_distribution_dialog.py`**
- `annotation` 컬럼의 value_counts를 Pie chart로 시각화
- HOMER 형식 세부 문자열을 대분류로 자동 정규화
  - `"intron (ENSMUSG00000097836, intron 2 of 4)"` → `"Intron"`
  - `"Promoter-TSS (Gata1)"` → `"Promoter-TSS"`
- 범례: 카테고리명 + 개수
- `annotation` 컬럼 없으면 "not available" 메시지 표시

**`src/gui/tss_distance_dialog.py`**
- `distance_to_tss` 컬럼 → Histogram
- 기본 범위 ±50 kb, bins=100 (UI에서 조절 가능)
- 참고선: 0 bp (TSS), ±2 kb, ±5 kb
- 요약 라벨: ≤2 kb, ≤5 kb 비율

**`src/gui/ma_plot_dialog.py`** *(계획에 없던 신규 추가)*
- X축: log₂(base_mean), Y축: log₂FC
- Up / Down / NS 색상 분류 (adj_pvalue + log2fc 임계값)
- Gene label 모드: Top N by |log2FC|, Custom list
- Hover tooltip: nearest_gene, log2FC, base_mean, adj_pvalue
- VolcanoPlotDialog와 동일한 3-panel 레이아웃

> **계획과의 차이:** `Peak Width Dialog`(별도 창)는 구현하지 않음 —
> Peak Width 필터가 Filter Panel에 통합되어 충분하다고 판단.  
> 대신 `MA Plot Dialog`를 추가.

---

### 1.5 메인 윈도우 (완료)

#### `src/gui/main_window.py`

**File 메뉴:**
```
File → Open ATAC-seq Dataset...  (신규)
```

**Visualization 메뉴 (ATAC 탭 활성 시에만 enable):**
```
Visualization → Genomic Distribution (ATAC)
Visualization → TSS Distance Plot (ATAC)
Visualization → MA Plot (ATAC)
```

**View → Column Display Level:**
- 라벨 변경: "Basic / **Stat** / Full" (계획의 "DE Analysis" → "Stat"으로 추상화)
- ATAC_SEQ 분기 추가 (`_filter_columns_by_level`)

**`_update_atac_ui(tab_index)`:**
- 탭 전환 시 ATAC 여부 감지 → Filter Panel + Visualization 메뉴 활성화/비활성화

---

### 1.6 Database 지원 (완료)

#### `src/utils/database_manager.py`

ATAC-seq import 분기:
- `row_count` = total peaks
- `significant_genes` = sig DA peaks
- Annotation 카테고리 카운트 notes 저장 (Promoter / Distal / …)

---

### 1.7 버그 수정 (완료)

| 버그 | 원인 | 수정 위치 |
|------|------|-----------|
| 초기 로드 시 ATAC UI 비활성 | `_update_view_with_dataset`이 `_update_atac_ui` 미호출 | `main_presenter.py` |
| Filtered 탭의 Volcano Plot 실패 | `removeTab()` 후 `tab_data` 인덱스 불일치 | `main_window.py` → `_remove_tab_safely()` |
| Gene list 필터가 ENSEMBL ID로 검색 | ATAC 분기 없어 `gene_id` 컬럼 사용 | `main_presenter.py` → `_filter_by_gene_list()` |

---

### Phase 1 체크리스트

- [x] `StandardColumns` ATAC-seq 컬럼 상수 및 헬퍼 메서드
- [x] `DatasetType.ATAC_SEQ` 추가
- [x] `ATACSeqLoader` 구현 (`src/utils/atac_seq_loader.py`)
- [x] `FilterCriteria` ATAC 필드 추가
- [x] `PreloadedDatasetMetadata` genome_build / peak_caller 필드
- [x] Filter Panel ATAC-seq 섹션 (Annotation, TSS, Peak Width)
- [x] Genomic Distribution dialog (annotation 정규화 포함)
- [x] TSS Distance dialog
- [x] MA Plot dialog *(추가 구현)*
- [x] Database ATAC-seq import 지원
- [x] File 메뉴 / Visualization 메뉴 업데이트
- [x] Column Display Level → Basic / Stat / Full 통일
- [x] README, RECENT_UPDATES, F1 Help 문서 업데이트
- [ ] Unit tests for ATACSeqLoader *(미작성)*
- [ ] Peak Width Distribution dialog *(MA Plot으로 대체)*

---

---

# ✅ Phase 2: Multi-Omics Integration — 완료 (v1.2.1)

**완료일:** 2026-05-31  
**목표:** RNA-seq와 ATAC-seq 데이터를 유전자 수준에서 통합하여 concordance/discordance 분석

---

## 2.1 Data Model

### `MultiOmicsDataset` 클래스 (신규)

```python
# src/models/multi_omics_dataset.py

@dataclass
class MultiOmicsDataset:
    name: str
    rna_dataset: Dataset
    atac_dataset: Dataset
    integration_method: str  # "nearest_gene", "promoter_only", "all_peaks"
    integrated_data: Optional[pd.DataFrame] = None

    def integrate(self) -> pd.DataFrame:
        """
        Returns DataFrame:
            gene_id, symbol,
            rna_log2fc, rna_padj, rna_base_mean,
            peak_count, atac_log2fc_mean, atac_log2fc_max, atac_padj_min,
            concordance, regulatory_status
        """
```

### `DatasetType.MULTI_OMICS` 추가

```python
class DatasetType(Enum):
    ...
    MULTI_OMICS = "multi_omics"   # Phase 2에서 추가
```

### Concordance 분류

```
Concordant_Both_UP:        RNA ↑, ATAC ↑
Concordant_Both_DOWN:      RNA ↓, ATAC ↓
Discordant_RNA_UP_ATAC_DOWN
Discordant_RNA_DOWN_ATAC_UP
RNA_only:   RNA significant, no ATAC peak near gene
ATAC_only:  ATAC DA peak, no RNA change
Not_significant
```

---

## 2.2 Integration Algorithm

### `src/utils/multi_omics_integrator.py` (신규)

```python
class MultiOmicsIntegrator:

    def integrate_by_nearest_gene(self, rna_df, atac_df) -> pd.DataFrame:
        """
        Steps:
        1. ATAC peaks를 nearest_gene으로 그룹화
        2. 각 gene: peak_count, mean/max log2FC, min padj
        3. RNA-seq과 gene_id/symbol로 merge
        4. Concordance 분류
        """

    def integrate_by_promoter(self, rna_df, atac_df, tss_window=2000):
        """TSS ± window 내 peak만 사용"""

    def calculate_concordance_score(self, rna_log2fc, atac_log2fc, ...):
        """
        Returns:
            { 'concordance': 'Concordant_Both_UP',
              'rna_sig': True, 'atac_sig': True,
              'same_direction': True }
        """
```

---

## 2.3 GUI: Multi-Omics Panel

### `src/gui/multi_omics_panel.py` (신규)

좌측 패널에 추가될 새 탭:

```
┌─ RNA-seq Dataset ──────────┐
│ [Dataset dropdown      ▼]  │
├─ ATAC-seq Dataset ─────────┤
│ [Dataset dropdown      ▼]  │
├─ Integration Method ───────┤
│ [Nearest Gene         ▼]   │
│ TSS window: [2000] bp      │
├─ Thresholds ───────────────┤
│ RNA padj ≤ [0.05]          │
│ |RNA log2FC| ≥ [1.0]       │
│ ATAC padj ≤ [0.05]         │
│ |ATAC log2FC| ≥ [1.0]      │
└────────────────────────────┘
[🔗 Integrate RNA + ATAC]
```

---

## 2.4 시각화 (미구현)

### A. Quadrant Plot

```python
# src/gui/quadrant_plot_dialog.py

# X축: ATAC log2FC, Y축: RNA log2FC
# Q1(top-right): Both UP (concordant)
# Q2(top-left):  RNA UP, ATAC DOWN (discordant)
# Q3(bot-left):  Both DOWN (concordant)
# Q4(bot-right): RNA DOWN, ATAC UP (discordant)
# 색상: concordance 분류별
# hover: gene symbol, RNA/ATAC values
```

### B. Concordance Heatmap

```python
# src/gui/concordance_heatmap_dialog.py

# 행: 유전자 (concordance 또는 significance로 정렬)
# 열: [RNA_log2FC | ATAC_log2FC]
# 색상: Red(up) ↔ Blue(down)
# 사이드바: concordance status 어노테이션
```

### C. Concordance Summary Bar Chart

```python
# src/gui/concordance_summary_dialog.py

# 7개 카테고리별 peak count + percentage
# Stacked or grouped bar chart
```

### D. Integrated Volcano Plot

```python
# src/gui/integrated_volcano_dialog.py

# 기존 Volcano Plot에서 point color를 concordance로 교체
# Green: ATAC support, Red: Discordant, Gray: RNA-only
# Point size: ATAC peak count near gene
```

---

## 2.5 Export 형식 (미구현)

```
Excel 다중 시트 출력:
  Sheet 1: "Integrated_Summary"   — 전체 유전자
  Sheet 2: "Concordant_UP"        — Both UP
  Sheet 3: "Concordant_DOWN"      — Both DOWN
  Sheet 4: "Discordant"           — 불일치 유전자
  Sheet 5: "RNA_only"
  Sheet 6: "ATAC_only"
  Sheet 7: "Peak_Details"         — 원본 peak 정보
```

---

## 2.6 메뉴 업데이트 ✅ 구현 완료

```
File Menu:
  └─ Export Multi-Omics Results (Excel)...  ✅

Analysis Menu:
  └─ Integrate RNA + ATAC  ✅

Visualization Menu (multi-omics 탭 활성 시):
  ├─ Quadrant Plot          ✅
  ├─ Concordance Heatmap    ✅
  ├─ Integrated Volcano     ✅
  └─ Concordance Summary    ✅
```

---

## Phase 2 체크리스트

- [x] `DatasetType.MULTI_OMICS` 추가 — `src/models/data_models.py`
- [x] `MultiOmicsDataset` 클래스 — `src/models/multi_omics_dataset.py`
- [x] `MultiOmicsIntegrator` 유틸 — `src/utils/multi_omics_integrator.py`
- [x] `MultiOmicsPanel` GUI 컴포넌트 — `src/gui/multi_omics_panel.py`
- [x] Quadrant Plot dialog — `src/gui/quadrant_plot_dialog.py`
- [x] Concordance Heatmap dialog — `src/gui/concordance_heatmap_dialog.py`
- [x] Concordance Summary Bar Chart dialog — `src/gui/concordance_summary_dialog.py`
- [x] Integrated Volcano dialog — `src/gui/integrated_volcano_dialog.py`
- [x] Multi-sheet Excel export — `presenter.export_multi_omics_excel()`
- [ ] Database multi-omics pair 저장 지원
- [x] File / Analysis / Visualization 메뉴 업데이트
- [ ] Unit tests for integration algorithms
- [x] F1 Help: Multi-Omics Integration 섹션 추가

> **구현일**: 2026-05-31  
> **구현 범위**: nearest_gene / promoter_only 통합, concordance 7-category 분류, Quadrant Plot · Concordance Heatmap · Concordance Summary 시각화, 다중 시트 Excel export

---

---

# ✅ Phase 3A: TF Motif Enrichment Import & 시각화 — 완료 (v1.2.2)

**완료일:** 2026-06-08

## 배경 및 목적

Phase 2까지의 gene-level concordance는 "chromatin이 열렸다"는 것을 확인하는 데 그치고,
**왜 열렸는가 (어떤 TF가 작동했는가)** 를 설명하지 못한다.
고영향 저널 리뷰에서 TF motif 분석은 거의 필수적으로 요구된다.

외부 분석 툴(HOMER, MEME-Suite)의 결과 파일을 import·시각화하는 방식으로 이 격차를 좁힌다.
분석 자체는 외부 툴에 위임하고, CMG-SeqViewer는 결과 통합 시각화에 집중한다.

---

## 3A.1 필요 입력 파일 및 준비 방법

### [현재 지원 중] DA Peak 파일

DESeq2 기반 ATAC-seq DA 분석 결과 (이미 지원).

```r
# R에서 생성
library(DESeq2)
results_df <- as.data.frame(results(dds))
results_df$annotation      <- peak_anno@anno$annotation
results_df$distance_to_tss <- peak_anno@anno$distanceToTSS
results_df$nearest_gene    <- peak_anno@anno$SYMBOL
write.xlsx(results_df, "final_da_result.xlsx", sheetName="DA_Results")
```

**필수 컬럼:** `chr`, `start`, `end`, `nearest_gene`, `annotation`, `distanceTSS`, `log2FoldChange`, `padj`, `baseMean`

---

### [Phase 3A 신규] HOMER knownResults.txt

**생성 파이프라인:**
```bash
# 1. DA peak 결과에서 UP/DOWN 분리 → BED 파일 생성
awk 'NR>1 && $13=="UP"   {print $3"\t"$4"\t"$5"\t"$1"\t.\t."}' da_result.txt > up_peaks.bed
awk 'NR>1 && $13=="DOWN" {print $3"\t"$4"\t"$5"\t"$1"\t.\t."}' da_result.txt > down_peaks.bed
awk 'NR>1               {print $3"\t"$4"\t"$5"\t"$1"\t.\t."}' da_result.txt > all_peaks.bed

# 2. HOMER motif 분석 실행
#   -size given : BED 파일 크기 그대로 사용
#   -mask       : repeat mask 적용
#   -bg         : background peaks 지정 (없으면 HOMER 자동 생성)
findMotifsGenome.pl up_peaks.bed   hg38 homer_up_results/   -size given -mask -bg all_peaks.bed
findMotifsGenome.pl down_peaks.bed hg38 homer_down_results/ -size given -mask -bg all_peaks.bed
```

**CMG-SeqViewer에 제공할 파일:** `homer_up_results/knownResults.txt`

**파일 형식 (탭 구분):**
```
Motif Name	Consensus	P-value	Log P-value	q-value(Benjamini)	# of Target Sequences with Motif(of 1523 Total)	% of Targets Sequences with Motif	# of Background Sequences with Motif(of 10000 Total)	% of Background Sequences with Motif
IRF1(IRF)/HepG2-IRF1-ChIP-Seq(GSE51800)/Homer	AAASYGAAASY	1e-91	-2.099e+02	1e-87	771(of 1523)	50.62%	501(of 10000)	5.01%
```

**컬럼 매핑:**

| 원본 컬럼 | 표준 내부명 | 설명 |
|---|---|---|
| `Motif Name` | `motif_name` | TF 이름 + 데이터베이스 정보 |
| `Consensus` | `consensus` | 컨센서스 서열 |
| `P-value` | `motif_pvalue` | enrichment p-value |
| `q-value(Benjamini)` | `motif_qvalue` | FDR-adjusted p-value |
| `% of Targets Sequences with Motif` | `target_pct` | foreground 발견 비율 (%) |
| `% of Background Sequences with Motif` | `bg_pct` | background 발견 비율 (%) |

**파싱 특이사항:**
- `"771(of 1523)"` 형식 → 정수 추출
- `"50.62%"` 형식 → float 변환
- `Motif Name`에서 TF 이름 추출: 첫 번째 `(` 앞 문자열

---

### [Phase 3A 신규] MEME-Suite AME ame.tsv (HOMER 대안)

**생성 파이프라인:**
```bash
# 1. BED → FASTA 변환
bedtools getfasta -fi genome.fa -bed up_peaks.bed -fo up_peaks.fa

# 2. AME 실행
ame --control all_peaks.fa --oc ame_up_results/ up_peaks.fa JASPAR2020_CORE_vertebrates.meme
```

**CMG-SeqViewer에 제공할 파일:** `ame_up_results/ame.tsv`

**파일 형식 (탭 구분, `#` 시작 행은 주석):**
```
# AME (Analysis of Motif Enrichment)
rank	motif_db	motif_id	motif_alt_id	consensus	p-value	adj_p-value	...
1	JASPAR2020_CORE.meme	MA0002.1	RUNX1	TGYGGT	1.12e-157	2.79e-153	...
```

**컬럼 매핑:**

| 원본 컬럼 | 표준 내부명 |
|---|---|
| `motif_alt_id` | `motif_name` |
| `motif_id` | `motif_id` |
| `consensus` | `consensus` |
| `p-value` | `motif_pvalue` |
| `adj_p-value` | `motif_qvalue` |

---

### 필요 데이터 요약

| Phase | 파일 | 생성 방법 | 준비 난이도 |
|-------|------|-----------|-------------|
| 현재 | `final_da_result.xlsx` | DESeq2 + ChIPseeker (R) | 이미 보유 |
| 3A | `homer_up_results/knownResults.txt` | HOMER CLI | ★★☆ |
| 3A | `homer_down_results/knownResults.txt` | HOMER CLI | ★★☆ |
| 3A (대안) | `ame_up_results/ame.tsv` | MEME-Suite CLI | ★★☆ |
| 3B (예정) | `BINDetect_results/bindetect_results.txt` | TOBIAS pipeline | ★★★ |
| 3C (장기) | `peak_counts_matrix.txt` | featureCounts | ★★☆ |

---

## 3A.2 구현된 내용

### 새로 추가된 파일

**`src/utils/motif_loader.py`**
- `MotifLoader.load(path, name)` — HOMER / AME 자동 감지 + 파싱
- `is_motif_file(path)` — 파일명/내용 헤더로 motif 파일 판별
- `_parse_homer()` — `knownResults.txt` 파싱, `%`·`(of N)` 형식 변환
- `_parse_ame()` — `#` 주석 제거, 동적 헤더 파싱
- `_extract_tf_name()` — `"IRF1(IRF)/HepG2.../Homer"` → `"IRF1"`
- `-log10(p)` 자동 계산 (HOMER `Log P-value` 절댓값 또는 p-value로 계산)

**`src/gui/motif_enrichment_dialog.py`**
- `MotifEnrichmentDialog(dataset, dataset_down=None)`
- 단일 모드: 가로 막대 그래프, -log10(p) 기준 상위 N개 TF
- 비교 모드: UP / DOWN 두 결과 나란히 서브플롯
- 컨트롤: Top N (5–100), Q-value cutoff, % 오버레이 옵션
- Export Data 버튼 → Excel (시트별) 또는 CSV
- `BasePlotDialog` 상속 → 기존 테마/export 인프라 재사용

### 수정된 파일

**`src/models/standard_columns.py`** — `MotifColumns` 추가:
```python
MOTIF_NAME     = 'motif_name'
MOTIF_ID       = 'motif_id'
CONSENSUS      = 'consensus'
MOTIF_PVALUE   = 'motif_pvalue'
MOTIF_QVALUE   = 'motif_qvalue'
MOTIF_LOG_PVALUE = 'log_pvalue'
TARGET_PCT     = 'target_pct'
BG_PCT         = 'bg_pct'
TARGET_COUNT   = 'target_count'
BG_COUNT       = 'bg_count'

get_motif_required() → [motif_name, motif_pvalue]
get_motif_all()      → 전체 10개 컬럼
```

**`src/models/data_models.py`** — `DatasetType.MOTIF_ENRICHMENT = "motif_enrichment"` 추가

**`src/presenters/main_presenter.py`** — `.txt`/`.tsv` 확장자를 `MotifLoader.is_motif_file()`으로 먼저 감지

**`src/utils/data_loader.py`** — `MOTIF_ENRICHMENT` 타입은 `MotifLoader`로 위임

**`src/gui/main_window.py`**:
- File 메뉴: `Open TF Motif Results...` (.txt / .tsv)
- Visualization 메뉴: `TF Motif Enrichment Plot` (MOTIF_ENRICHMENT 탭 활성 시 enable)
- `_on_open_motif_results()` — 파일 열기 핸들러
- `_on_motif_enrichment_requested()` — 두 번째 motif 데이터셋 선택 후 비교 모드 지원
- `_update_atac_ui()` — `is_motif` 조건 추가

---

## 3A.3 사용 흐름

```
1. HOMER 또는 AME 실행 (외부 파이프라인)
   ↓
2. File → Open TF Motif Results...
   → knownResults.txt 또는 ame.tsv 선택
   ↓
3. Dataset Tree에 MOTIF_ENRICHMENT 타입으로 추가
   ↓
4. 해당 탭 선택 → Visualization → TF Motif Enrichment Plot
   ↓
5. [선택] 두 번째 motif 데이터셋(예: DOWN peaks)이 있으면 비교 모드 제안
   ↓
6. 막대 그래프: 상위 N TF, -log10(p-value) 기준 정렬
   UP (Red) / DOWN (Blue) 나란히 비교 가능
```

---

## Phase 3A 체크리스트

- [x] `DatasetType.MOTIF_ENRICHMENT` 추가
- [x] `MotifColumns` (standard_columns.py)
- [x] `MotifLoader` — HOMER / AME 자동 파싱
- [x] `MotifEnrichmentDialog` — 단일/비교 막대 그래프
- [x] `BasePlotDialog` 상속 (테마·export 재사용)
- [x] File 메뉴 `Open TF Motif Results...`
- [x] Visualization 메뉴 `TF Motif Enrichment Plot`
- [x] `.txt`/`.tsv` 파일 라우팅 (presenter)
- [ ] Project save/load에서 MOTIF_ENRICHMENT 타입 복원 검증
- [ ] Unit tests for MotifLoader

---

---

# ✅ Phase 3B: TF Footprinting (TOBIAS BINDetect) — 완료 (v1.2.2)

**완료일:** 2026-06-08

**목적:** TOBIAS BINDetect 결과로 조건 간 TF 결합 활성 변화를 시각화.
Phase 3A가 "어떤 모티프가 enriched되어 있는가"를 보여준다면,
Phase 3B는 "그 모티프에 실제로 TF가 결합하고 있는가"를 footprint score로 보여준다.

---

## 3B.1 필요 입력 파일 및 준비 방법

**생성 파이프라인 (BAM 파일 필요):**
```bash
# 조건 예시: Acute_1D vs Control

# Step 1: ATACorrect — Tn5 insertion bias 보정
TOBIAS ATACorrect --bam Acute_1D.bam --genome hg38.fa \
    --peaks all_peaks.bed --outdir ATACorrect_Acute_1D/
TOBIAS ATACorrect --bam Control.bam --genome hg38.fa \
    --peaks all_peaks.bed --outdir ATACorrect_Control/

# Step 2: ScoreBigwig — footprint score 계산
TOBIAS ScoreBigwig \
    --signal ATACorrect_Acute_1D/Acute_1D_corrected.bw \
    --regions all_peaks.bed --output Acute_1D_footprints.bw
TOBIAS ScoreBigwig \
    --signal ATACorrect_Control/Control_corrected.bw \
    --regions all_peaks.bed --output Control_footprints.bw

# Step 3: BINDetect — 조건 간 TF 결합 변화
#   --cond-names 에 지정한 이름이 결과 컬럼명에 반영됨
TOBIAS BINDetect \
    --motifs JASPAR2020_CORE_vertebrates.jaspar \
    --signals Acute_1D_footprints.bw Control_footprints.bw \
    --genome hg38.fa --peaks all_peaks.bed \
    --outdir BINDetect_results/ \
    --cond-names Acute_1D Control
```

**CMG-SeqViewer에 제공할 파일:** `BINDetect_results/bindetect_results.txt`

**파일 형식 — 조건명이 컬럼명에 포함됨 (동적):**
```
output_prefix	name	motif_file	Acute_1D_mean_score	Acute_1D_bound	Control_mean_score	Control_bound	Acute_1D_Control_change	Acute_1D_Control_pvalue
MA0002.1_RUNX1	RUNX1	JASPAR/MA0002.1.jaspar	0.3241	1823	0.1893	1102	0.1348	2.3e-12
```

**⚠️ 파싱 주의:** `{cond1}_mean_score` 등 컬럼명이 조건명에 따라 달라짐.
로더에서 헤더를 읽어 `_mean_score`, `_bound`, `_change`, `_pvalue` 접미사로 조건명 동적 감지 필요.

**컬럼 매핑 (동적):**

| 원본 패턴 | 표준 내부명 | 의미 |
|---|---|---|
| `name` | `motif_name` | TF 이름 |
| `{cond1}_mean_score` | `cond1_score` | cond1 footprint 점수 |
| `{cond2}_mean_score` | `cond2_score` | cond2 footprint 점수 |
| `{cond1}_{cond2}_change` | `footprint_change` | 결합 변화량 (양수=cond1 증가) |
| `{cond1}_{cond2}_pvalue` | `footprint_pvalue` | 유의성 |
| `{cond1}_bound` | `cond1_bound` | cond1 결합 site 수 |
| `{cond2}_bound` | `cond2_bound` | cond2 결합 site 수 |

---

## 3B.2 구현된 내용

**새로 추가된 파일:**

**`src/utils/footprint_loader.py`**
- `FootprintLoader.load(path, name)` — bindetect_results.txt 파싱
- `is_footprint_file(path)` — 파일명(`bindetect_results`) 또는 헤더(`_mean_score` + `_change`) 패턴으로 감지
- `_detect_conditions(columns)` — `{cond}_mean_score` 컬럼에서 조건명 2개 자동 추출
  - `_mean_score` 접미사 컬럼 목록으로 감지 후 `_change` 컬럼으로 순서 검증
- 표준 컬럼명 매핑 (`cond1_score`, `cond2_score`, `footprint_change`, `footprint_pvalue` 등)
- `dataset.metadata['cond1_name']`, `['cond2_name']`에 조건명 저장

**`src/gui/tf_footprint_dialog.py`**
- `TFFootprintDialog(dataset)` — TF Activity Scatter Plot
- X축 = cond1 mean score, Y축 = cond2 mean score
- 점 분류: `gain` (cond1 활성화, Red), `loss` (cond2 활성화, Blue), `ns` (Gray)
- 분류 기준: p-value cutoff + |change| 최솟값 (모두 UI에서 조절)
- 유의미 TF 상위 N개 라벨 자동 표시 (|change| 기준)
- 대각선 y=x 표시 옵션
- Export: 조건명을 원래 컬럼명으로 복원하여 내보내기
- `BasePlotDialog` 상속

**수정된 파일:**
- `src/models/data_models.py` — `DatasetType.TF_FOOTPRINT = "tf_footprint"` 추가
- `src/models/standard_columns.py` — `FootprintColumns` 추가 (11개 상수)
- `src/presenters/main_presenter.py` — `.txt` 파일에서 footprint 감지를 motif 감지보다 먼저 시도
- `src/gui/main_window.py`:
  - File 메뉴: `Open TF Footprint Results...`
  - Visualization 메뉴: `TF Activity Plot (Footprint)` (TF_FOOTPRINT 탭 활성 시 enable)
  - `_on_open_footprint_results()` — 파일 열기 핸들러
  - `_on_tf_footprint_requested()` — 시각화 핸들러
  - `_update_atac_ui()` — `is_footprint` 조건 추가

---

## 3B.3 사용 흐름

```
1. TOBIAS 3단계 파이프라인 실행 (외부)
   ATACorrect → ScoreBigwig → BINDetect
   ↓
2. File → Open TF Footprint Results...
   → bindetect_results.txt 선택
   ↓
3. Dataset Tree에 TF_FOOTPRINT 탭 추가
   (조건명 자동 감지: Acute_1D vs Control 등)
   ↓
4. Visualization → TF Activity Plot (Footprint)
   ↓
5. Scatter Plot:
   - X축 = cond1 mean score
   - Y축 = cond2 mean score
   - Red = cond1에서 더 활성화된 TF
   - Blue = cond2에서 더 활성화된 TF
   ↓
6. Export Data → 원래 조건명 컬럼으로 복원하여 Excel 저장
```

---

## Phase 3B 체크리스트

- [x] `DatasetType.TF_FOOTPRINT` 추가
- [x] `FootprintColumns` (standard_columns.py)
- [x] `FootprintLoader` — TOBIAS BINDetect 동적 컬럼 파싱
- [x] `TFFootprintDialog` — TF Activity Scatter Plot
- [x] File 메뉴 `Open TF Footprint Results...`
- [x] Visualization 메뉴 `TF Activity Plot (Footprint)`
- [x] `.txt` 파일에서 footprint 파일 감지 (motif보다 우선)
- [ ] Unit tests for FootprintLoader (조건명 동적 감지 케이스)

---

---

# ✅ Phase 3C: chromVAR Differential TF Activity — 완료 (v1.2.2)

**완료일:** 2026-06-09

## 배경

HOMER/TOBIAS 결과가 없고, 실제 파이프라인에서 chromVAR를 사용하는 경우를 위한 지원.
chromVAR는 전체 peak matrix에서 TF motif-weighted accessibility z-score를 계산하므로
DA peak 수가 적어도 안정적인 결과를 제공한다는 장점이 있다.

**실제 사용 데이터:**
- `chromvar/differential_tf/*_diff_tf.csv` — 비교군별 TF activity
- `seqviewer/datasets/*_chromVAR_DiffTF.parquet` — seqviewer용 변환 파일
- `chromvar/tf_variability.csv` — TF 이름 조회 참조 테이블

---

## 3C.1 입력 파일 형식

### diff_tf CSV (chromVAR R 패키지 출력)
```
motif,       mean_compare, mean_base, delta,   p_value, padj
MA0006.1,    -0.745,       0.188,     -0.933,  0.081,   0.255
```

### seqviewer parquet (파이프라인 사전 변환)
```
tf_name,   mean_zscore_compare, mean_zscore_base, delta_zscore, p_value, padj
MA0006.1,  -0.745,              0.188,            -0.933,       0.081,   0.255
```

**⚠️ 주의:** `tf_name`/`motif` 컬럼은 실제로 JASPAR ID (MA0006.1)이며, 
TF 이름(Ahr::Arnt 등)은 `tf_variability.csv`의 `name` 컬럼에서 조인한다.

### tf_variability.csv (TF 이름 참조)
```
motif,    name,    variability, p_value, p_value_adj
MA0470.2, E2F4,    1.86,        0.000011, 0.00817
```

---

## 3C.2 구현된 내용

**`src/utils/chromvar_loader.py`**
- CSV (diff_tf) 및 Parquet (chromVAR_DiffTF) 자동 감지·파싱
- `is_chromvar_file()` — 파일명(`diff_tf`, `chromvar`) 또는 헤더(`motif`+`delta`+`padj`) 패턴으로 감지
- `_find_variability_file()` — 동일 디렉토리 또는 최대 3단계 상위에서 `tf_variability.csv` 자동 탐색
- `_join_tf_names()` — JASPAR ID → TF 이름 조인 (미발견 시 ID 그대로 사용)
- `-log10(padj)` 자동 계산 컬럼 추가

**`src/gui/chromvar_dialog.py`**
- `ChromVARDialog(dataset, extra_datasets=None)` — 세 가지 시각화 모드:
  - **Volcano**: X=delta z-score, Y=-log10(padj), 임계선 표시, 상위 N TF 라벨
  - **Scatter**: X=base z-score, Y=compare z-score, 대각선(y=x) 기준 위/아래로 분류
  - **Multi-condition Heatmap**: 여러 CHROMVAR_DIFF_TF 데이터셋 동시 로드 시 TF × condition delta matrix
- padj / |delta| / top N label 컨트롤
- Export: 조건별 Excel 시트

**컬럼 표준화:**
```python
CHROMVAR_MOTIF_ID    = 'chromvar_motif_id'
CHROMVAR_TF_NAME     = 'chromvar_tf_name'
CHROMVAR_MEAN_COMPARE = 'chromvar_mean_compare'
CHROMVAR_MEAN_BASE   = 'chromvar_mean_base'
CHROMVAR_DELTA       = 'chromvar_delta'
CHROMVAR_PVALUE      = 'chromvar_pvalue'
CHROMVAR_PADJ        = 'chromvar_padj'
```

**수정된 파일:**
- `src/models/data_models.py` — `DatasetType.CHROMVAR_DIFF_TF` 추가
- `src/models/standard_columns.py` — `ChromVARColumns` 추가
- `src/presenters/main_presenter.py` — CSV/Parquet 에서 chromVAR 감지 (ATAC-seq 감지보다 먼저)
- `src/gui/main_window.py` — File 메뉴 `Open chromVAR Results...`, Visualization 메뉴 `chromVAR TF Activity Plot`

---

## 3C.3 사용 흐름

```
File → Open chromVAR Results...
  → *_diff_tf.csv 또는 *_chromVAR_DiffTF.parquet 선택
  ↓
같은 디렉토리에서 tf_variability.csv 자동 탐색 → TF 이름 조인
  ↓
Dataset Tree에 CHROMVAR_DIFF_TF 탭 추가
  ↓
여러 비교군(Acute_1D, Acute_3D, Chronic_100uM, Chronic_200uM) 모두 로드
  ↓
Visualization → chromVAR TF Activity Plot
  → View: Multi-condition Heatmap 선택
  → 4개 조건의 TF activity 변화를 한 화면에서 확인
```

---

## Phase 3C 체크리스트

- [x] `DatasetType.CHROMVAR_DIFF_TF` 추가
- [x] `ChromVARColumns` (standard_columns.py)
- [x] `ChromVARLoader` — CSV/parquet + TF 이름 자동 조인
- [x] `ChromVARDialog` — Volcano / Scatter / Multi-condition Heatmap
- [x] File 메뉴 `Open chromVAR Results...`
- [x] Visualization 메뉴 `chromVAR TF Activity Plot`
- [x] CSV/Parquet 라우팅 (presenter)
- [x] 실제 데이터(4개 비교군) 로딩 검증

---

---

# ✅ Phase 3D: Multi-Condition DA Peak Overlap Analysis (peak 좌표 기반) — 완료 (v1.2.3)

**완료일:** 2026-06-18

## 배경

Phase 2(RNA+ATAC)와 Phase 3A-C(TF 분석)는 모두 ATAC DA 결과를 *다른 종류의 데이터*와 비교하는
기능이다. 그러나 **ATAC DA 결과끼리(조건 간) 직접 비교**하는 기능은 아직 없다.

현재 유일한 다중 데이터셋 비교 도구인 Venn Diagram(`venn_dialog.py`)은 gene symbol/gene_id만
키로 사용한다. 이 키는 ATAC 데이터셋의 `nearest_gene` 컬럼을 인식하지 못해 실질적으로 빈 set이
되며, 설령 인식하더라도 gene 단위 비교는 peak의 다대일 집계로 방향성이 상쇄되고
"nearest gene ≠ 실제 타겟 유전자"라는 근본적 한계를 가진다.

ATAC DA 결과의 1차 측정 단위는 **peak(genomic interval)**이므로, 조건 간 비교도 gene이 아닌
**peak 좌표 / peak_id** 기준으로 해야 RNA-seq의 gene-level 비교(DE-DE)와 동등한 엄밀성을 가진다.

## 전제 조건 (중요)

이 분석이 유효하려면 비교 대상 DA 데이터셋들이 **같은 peak set(consensus/union peak)**에서
나와야 한다.

- 모든 조건의 BAM을 합쳐 peak을 한 번만 호출(call)한 경우 → `peak_id`가 조건마다 동일 →
  직접 비교 가능
- 조건별로 peak을 독립적으로 호출한 경우 → 좌표가 다르므로 `bedtools intersect`/`merge`로
  좌표를 reconcile하는 외부 전처리가 먼저 필요 (이 도구의 책임 범위 밖)

→ UI에서 이 전제를 안내 문구로 명시하고, peak_id 포맷이 데이터셋 간에 다르면 경고를 표시한다.

## 입력 데이터

추가 파일 불필요 — 이미 로드된 `DatasetType.ATAC_SEQ` 데이터셋 2개 이상을 그대로 사용한다.

## 구현된 내용

### A. peak_id 정규화 유틸리티

**`src/utils/peak_overlap.py`** (신규)
- `get_peak_set(dataset, padj_threshold=None, log2fc_threshold=None) -> set` —
  ATAC_SEQ Dataset에서 peak_id set 추출. `peak_id` 컬럼이 없으면
  `chr:start-end`로 합성. threshold가 주어지면 유의미한 peak만 포함
- `check_consensus(datasets) -> Optional[str]` — 데이터셋 쌍별 peak_id 교집합
  비율을 계산해, 모든 쌍의 최대 교집합 비율이 5% 미만이면 경고 메시지 반환

> **계획과의 차이:** `compute_overlap_matrix()`는 별도 구현하지 않음 —
> `upsetplot.from_contents()`가 동일 기능을 제공하므로 `upset_plot_dialog.py`에서
> 직접 사용.

### B. 2~3개 데이터셋: 기존 Venn Diagram 확장

**`src/gui/venn_dialog.py`** (수정)
- `_get_gene_sets()`가 `dataset.dataset_type == DatasetType.ATAC_SEQ`이면
  `peak_overlap.get_peak_set()`으로 peak_id 기준 set을 구성 (RNA-seq 등은 기존
  symbol/gene_id 로직 유지)
- Plot 제목을 ATAC 전용 선택일 때 "Gene Overlap" → "Peak Overlap"으로 자동 전환
- 기존 필터 옵션(All / DEG only / Highly significant) 재사용 — padj/log2FC
  threshold를 peak 필터링에 그대로 적용

> **계획과의 차이:** `matplotlib_venn`은 venn2/venn3만 제공하므로(venn4 없음),
> 범위는 계획의 "2~4개"가 아니라 **2~3개**로 확정. 4개 이상은 모두 UpSet으로 분기.

### C. 4개 이상 데이터셋: 신규 UpSet Plot

**`src/gui/upset_plot_dialog.py`** (신규)
- `UpsetPlotDialog(datasets)` — `upsetplot.UpSet` + `from_contents()` 사용
- 컨트롤: Significant peaks only 체크박스, Adj. p-value / |log2FC| threshold,
  Max intersections shown (Top N)
- `_apply_labels()` 오버라이드 — UpSet은 다중 axes 구조라 `BasePlotDialog`의
  단일 axes 가정을 따르지 않고 제목만 `figure.suptitle()`로 적용
- Export Data → intersection 멤버십 테이블을 Excel/CSV로 저장
- `BasePlotDialog` 상속 (테마/figure export 인프라 재사용)

**⚠️ 발견된 라이브러리 호환성 버그 및 패치:**
설치된 `upsetplot==0.9.0`이 이 환경의 `pandas==3.0.3` / `numpy==2.4.6`과 호환되지
않아 그래프가 그려지지 않는 문제를 발견. 업스트림 수정 버전이 없어 동일 파일에
monkeypatch로 대응:
- `UpSet.plot_matrix` — pandas 3.0의 강제 Copy-on-Write 하에서
  `styles[col].fillna(value, inplace=True)` (chained assignment)가 항상 no-op이
  되어 facecolor가 NaN으로 남고 `Invalid RGBA argument: nan` 에러 발생 →
  non-inplace 대입(`styles[col] = styles[col].fillna(value)`)으로 교체
- `UpSet._label_sizes` — `0.01 * abs(np.diff(ax.get_xlim()))`가 길이 1 ndarray를
  반환하는데, numpy 2.x에서 matplotlib Text 좌표 변환 시 암묵적 스칼라 변환이
  거부되어 `only 0-dimensional arrays can be converted to Python scalars` 에러
  발생 → `float(... [0])`로 명시적 스칼라 변환

두 패치 모두 로직은 원본과 동일하게 유지하고 문제가 된 대입/형변환 부분만 교체.

### D. 메뉴 연결

**`src/gui/main_window.py`** (수정)
- Visualization 메뉴: `🔗 DA Peak Overlap (ATAC-seq)...` (항상 활성화)
- `_on_da_peak_overlap()`:
  1. 로드된 `DatasetType.ATAC_SEQ` 데이터셋 목록 수집 (2개 미만이면 경고)
  2. 다중 선택 다이얼로그(`QListWidget`, MultiSelection, 기본 전체 선택)로
     비교 대상 선택
  3. 선택 개수 2-3개 → `VennDiagramDialog`, 4개 이상 → `UpsetPlotDialog`로 분기

> **계획과의 차이:** "Dataset Tree에서 Ctrl+클릭 다중 선택" 대신, 기존
> Venn Diagram 메뉴(`_on_venn_diagram`)와 동일한 패턴으로 메뉴 클릭 시 별도
> 선택 다이얼로그를 띄우는 방식으로 구현 (Dataset Tree의 다중 선택 상태를
> 활용하는 인프라가 없어 일관성 있는 기존 패턴 재사용).

## 사용 흐름

```
1. ATAC DA 데이터셋 여러 개 로드 (예: 1D/2D/3D/6H/3H vs Control, 같은 peak set 전제)
   ↓
2. Visualization → DA Peak Overlap (ATAC-seq)...
   ↓
3. 선택 다이얼로그에서 비교할 데이터셋 선택 (기본 전체 선택)
   ↓
4. peak_id 교집합 비율 자동 점검 → 모든 쌍이 5% 미만 겹치면 경고 다이얼로그
   ↓
5. 2-3개 → Venn Diagram / 4개 이상 → UpSet Plot
   ↓
6. Export Data → intersection 멤버십 테이블을 Excel/CSV로 저장
```

## Phase 3D 체크리스트

- [x] `src/utils/peak_overlap.py` — peak_id set 추출 + consensus 점검
- [x] `venn_dialog.py` — ATAC 데이터셋 peak_id 키 지원으로 확장 (2-3개)
- [x] `src/gui/upset_plot_dialog.py` — 4개 이상 UpSet plot 신규 구현
- [x] `upsetplot` pandas 3.0 / numpy 2.x 호환성 버그 패치 (monkeypatch)
- [x] consensus peak set 여부 자동 검증 + 경고 UI
- [x] `main_window.py` — `Visualization → DA Peak Overlap (ATAC-seq)...` 메뉴 + 선택 다이얼로그
- [x] Export: intersection 멤버십 테이블 (Excel/CSV)
- [x] 더미 데이터(1D/2D/3D/6H/3H vs Control 패턴)로 Venn·UpSet 동작 검증
- [ ] 실제 파이프라인 데이터로 검증 (현재는 합성 데이터로만 확인)
- [ ] Unit tests for peak_overlap.py

---

---

# 🔮 Phase 3E: Peak-Gene 발현 상관관계 (장기 계획)

**전제조건:** ≥3 샘플 쌍(RNA + ATAC)이 있어야 통계적 의미가 있음.
샘플 수가 충분하지 않으면 통계적으로 의미 없음 → 현재 구현 우선순위 낮음.

**필요 추가 입력:**
- 샘플별 peak accessibility count matrix (행=peak, 열=sample)
- 샘플별 gene expression count matrix (행=gene, 열=sample)

```bash
# featureCounts로 샘플별 peak count matrix 생성
awk 'BEGIN{print "GeneID\tChr\tStart\tEnd\tStrand"}
     NR>1{print $1"\t"$2"\t"$3"\t"$4"\t."}' all_peaks.bed > peaks.saf
featureCounts -F SAF -a peaks.saf -o peak_counts.txt sample1.bam sample2.bam ...
```

**분석 로직:**
1. Peak ↔ gene 후보 쌍 생성 (gene ± 200kb 이내 peak)
2. 샘플 간 Pearson/Spearman 상관계수 계산
3. 유의미한 상관 쌍만 "linked" 표시

**→ v2.0 이후 검토**

---

---

# 🔮 Phase 4: 추가 Omics 타입

- **ChromHMM**: DA peak에 chromatin state 어노테이션 오버레이
  - 공개 ENCODE/Roadmap BED 파일 import
  - 현재 `annotation` 컬럼 보완 (Enhancer/Bivalent/Polycomb 분류)
  - 예상 공수: 1–2일
- **ChIP-seq**: H3K27ac, H3K4me3, H3K27me3 통합
- **CUT&RUN / CUT&Tag**: TF binding sites
- **Hi-C**: Enhancer-gene linking 검증 (ABC model 연동)

---

---

## Technical Architecture: 현재 상태 (v1.2.3)

```
CMG-SeqViewer (v1.2.3)
├── DatasetType
│   ├── DIFFERENTIAL_EXPRESSION    ✅
│   ├── GO_ANALYSIS                ✅
│   ├── MULTI_GROUP                ✅
│   ├── ATAC_SEQ                   ✅ (Phase 1, v1.2.0)
│   ├── MULTI_OMICS                ✅ (Phase 2, v1.2.1)
│   ├── MOTIF_ENRICHMENT           ✅ (Phase 3A, v1.2.2)
│   ├── TF_FOOTPRINT               ✅ (Phase 3B, v1.2.2)
│   └── CHROMVAR_DIFF_TF           ✅ (Phase 3C, v1.2.2)
├── DataLoader
│   ├── RNA-seq (Excel, CSV, Parquet)   ✅
│   ├── GO/KEGG                         ✅
│   ├── Multi-Group                     ✅
│   ├── ATAC-seq (Excel, Parquet)       ✅
│   ├── Motif Enrichment (.txt, .tsv)   ✅ (HOMER / AME 자동 감지)
│   ├── TF Footprint (.txt)             ✅ (TOBIAS BINDetect 동적 컬럼)
│   └── chromVAR DiffTF (.csv, .parquet) ✅ (TF name 자동 조인)
├── FilterPanel
│   ├── DE filters (log2FC, padj)               ✅
│   ├── GO filters (FDR, FE, ontology)          ✅
│   └── ATAC filters (annotation, TSS, width)   ✅
├── Visualization
│   ├── Volcano Plot (RNA + ATAC)       ✅
│   ├── MA Plot (ATAC)                  ✅
│   ├── Heatmap                         ✅
│   ├── GO Dot Plot / Network           ✅
│   ├── Venn Diagram                    ✅ (2-3개, peak_id 또는 gene 키)
│   ├── Genomic Distribution            ✅
│   ├── TSS Distance Plot               ✅
│   ├── TF Motif Enrichment Plot        ✅ (Phase 3A — HOMER / AME)
│   ├── TF Activity Plot (Footprint)    ✅ (Phase 3B — TOBIAS BINDetect)
│   ├── chromVAR TF Activity Plot       ✅ (Phase 3C — Volcano/Scatter/Heatmap)
│   └── DA Peak Overlap (UpSet Plot)    ✅ (Phase 3D — 4개 이상 ATAC 데이터셋)
├── MultiOmicsPanel                     ✅ Phase 2 완료
│   ├── Dataset pairing (RNA + ATAC)    ✅
│   ├── Integration method              ✅ (nearest_gene / promoter_only)
│   ├── Concordance analysis            ✅ (7-category)
│   ├── Quadrant Plot                   ✅
│   ├── Concordance Heatmap             ✅
│   ├── Concordance Summary             ✅
│   ├── Integrated Volcano              ✅
│   └── Multi-sheet Excel export        ✅
└── DatabaseManager
    ├── RNA-seq datasets                ✅
    ├── ATAC-seq datasets               ✅
    └── Multi-omics pairs               ⏳ Phase 2 잔여
```

---

## Use Case Scenarios

### Scenario 1: ATAC-seq 단독 분석 ✅ 현재 가능

1. `File → Open ATAC-seq Dataset` 로 Excel/Parquet 로드
2. `Statistical Filter`: `padj < 0.05`, `|log2FC| > 1`
3. ATAC-seq Filter: `Annotation = Promoter-TSS`
4. `Visualization → Volcano Plot` → 세포 타입별 열린 프로모터 확인
5. `Visualization → Genomic Distribution` → annotation 분포 확인
6. `Visualization → TSS Distance Plot` → TSS proximity 확인
7. `Visualization → MA Plot` → log₂FC vs base_mean 산점도
8. `File → Export` → peak list 내보내기 (HOMER motif 분석 입력용)
9. `Gene List Filter`로 특정 유전자의 ATAC 데이터 추출

### Scenario 2: RNA + ATAC 통합 분석 ⏳ Phase 2 이후 가능

1. RNA-seq 및 ATAC-seq 데이터셋 로드
2. Multi-Omics Panel → 데이터셋 페어링
3. Integration method 선택
4. Quadrant plot, Concordance Heatmap으로 시각화
5. 불일치 유전자 → post-transcriptional regulation 후보

---

## Use Case Scenarios (업데이트)

### Scenario 3: TF Motif Enrichment 분석 ✅ 현재 가능

1. 외부에서 HOMER / AME 실행 → `knownResults.txt` 또는 `ame.tsv` 생성
2. `File → Open TF Motif Results...` → 파일 선택
3. Dataset Tree에 MOTIF_ENRICHMENT 탭 추가
4. `Visualization → TF Motif Enrichment Plot`
5. 두 번째 motif 파일(예: DOWN peaks)이 있으면 비교 모드 선택
6. TOP N TF를 -log10(p-value) 기준 가로 막대 그래프로 확인
7. `Export Data` → Excel로 결과 내보내기

---

## Document History

| Version | Date | 변경 사항 |
|---------|------|----------|
| 1.0 | 2026-02-28 | 초기 계획 작성 |
| 2.0 | 2026-04-30 | Phase 1 완료 반영; 계획과 구현 차이 명시; Phase 2 상세화 |
| 3.0 | 2026-05-31 | Phase 2 완료 반영 |
| 4.0 | 2026-06-08 | Phase 3A 완료 반영; Phase 3B·3C·4 상세화; 파이프라인 데이터 형식 문서화 |
| 5.0 | 2026-06-08 | Phase 3B 완료 반영 (TOBIAS BINDetect 로더 + TF Activity Scatter Plot) |
| 6.0 | 2026-06-09 | Phase 3C 완료 반영 (chromVAR 로더 + Volcano/Scatter/Heatmap); Phase 3C→3D 재번호 |
| 7.0 | 2026-06-18 | Phase 3D 신설 (Multi-Condition DA Peak Overlap, peak 좌표 기반); 기존 Phase 3D(Peak-Gene 상관관계)→3E 재번호 |
| 8.0 | 2026-06-18 | Phase 3D 완료 반영 (peak_overlap 유틸 + Venn peak_id 확장 + UpSet Plot 신규); upsetplot pandas 3.0/numpy 2.x 호환성 패치 기록 |
