# ATAC-seq Integration Plan

## Status Overview

| Phase | 내용 | 상태 | 버전 |
|-------|------|------|------|
| **Phase 1** | ATAC-seq Standalone Analysis | ✅ **완료** | v1.2.0 (2026-04-30) |
| **Phase 2** | Multi-Omics Integration (RNA + ATAC) | ⏳ **미구현** | — |
| **Phase 3+** | 고급 기능 (Motif, ChIP-seq, ML) | 🔮 **장기 계획** | — |

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

# ⏳ Phase 2: Multi-Omics Integration — 미구현

**목표:** RNA-seq와 ATAC-seq 데이터를 유전자 수준에서 통합하여 concordance/discordance 분석

**예상 규모:** 5–7일

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

## 2.6 메뉴 업데이트 (미구현)

```
File Menu:
  └─ Open Multi-Omics Pair  (신규)

Analysis Menu:
  └─ Integrate RNA + ATAC  (신규)

Visualization Menu (multi-omics 탭 활성 시):
  ├─ Quadrant Plot
  ├─ Concordance Heatmap
  ├─ Integrated Volcano
  └─ Concordance Summary
```

---

## Phase 2 체크리스트

- [ ] `DatasetType.MULTI_OMICS` 추가
- [ ] `MultiOmicsDataset` 클래스 (`src/models/multi_omics_dataset.py`)
- [ ] `MultiOmicsIntegrator` 유틸 (`src/utils/multi_omics_integrator.py`)
- [ ] `MultiOmicsPanel` GUI 컴포넌트
- [ ] Quadrant Plot dialog
- [ ] Concordance Heatmap dialog
- [ ] Concordance Summary Bar Chart dialog
- [ ] Integrated Volcano dialog
- [ ] Multi-sheet Excel export
- [ ] Database multi-omics pair 저장 지원
- [ ] File / Analysis / Visualization 메뉴 업데이트
- [ ] Unit tests for integration algorithms
- [ ] F1 Help: Multi-Omics Integration 섹션 추가

---

---

# 🔮 Phase 3+: 장기 계획

## Phase 3: 고급 ATAC-seq 기능

- **Motif Enrichment 통합**: HOMER/MEME 결과 import, TF binding site 시각화
- **TF Footprinting**: Aggregate footprint 시각화
- **Chromatin State Annotation**: ChromHMM / Roadmap Epigenomics 연동

## Phase 4: 추가 Omics 타입

- **ChIP-seq**: H3K27ac, H3K4me3, H3K27me3 통합
- **CUT&RUN / CUT&Tag**: TF binding sites
- **Hi-C**: Enhancer-gene linking 검증

## Phase 5: Machine Learning

- RNA 발현을 ATAC 접근성으로 예측
- Multi-omics clustering
- 조절 모듈 발견

---

---

## Technical Architecture: 현재 상태 (v1.2.0)

```
CMG-SeqViewer (v1.2.0)
├── DatasetType
│   ├── DIFFERENTIAL_EXPRESSION    ✅
│   ├── GO_ANALYSIS                ✅
│   ├── MULTI_GROUP                ✅
│   └── ATAC_SEQ                   ✅ (Phase 1 완료)
├── DataLoader
│   ├── RNA-seq (Excel, CSV, Parquet)  ✅
│   ├── GO/KEGG                        ✅
│   ├── Multi-Group                    ✅
│   └── ATAC-seq (Excel, Parquet)      ✅
├── FilterPanel
│   ├── DE filters (log2FC, padj)      ✅
│   ├── GO filters (FDR, FE, ontology) ✅
│   └── ATAC filters (annotation, TSS, width)  ✅
├── Visualization
│   ├── Volcano Plot (RNA + ATAC)      ✅
│   ├── MA Plot (ATAC)                 ✅
│   ├── Heatmap                        ✅
│   ├── GO Dot Plot / Network          ✅
│   ├── Venn Diagram                   ✅
│   ├── Genomic Distribution           ✅
│   └── TSS Distance Plot              ✅
├── MultiOmicsPanel                    ⏳ Phase 2
│   ├── Dataset pairing                ⏳
│   ├── Integration method             ⏳
│   └── Concordance analysis           ⏳
└── DatabaseManager
    ├── RNA-seq datasets               ✅
    ├── ATAC-seq datasets              ✅
    └── Multi-omics pairs              ⏳ Phase 2
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

## Document History

| Version | Date | 변경 사항 |
|---------|------|----------|
| 1.0 | 2026-02-28 | 초기 계획 작성 |
| 2.0 | 2026-04-30 | Phase 1 완료 반영; 계획과 구현 차이 명시; Phase 2 상세화 |
