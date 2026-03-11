# ATAC-seq Integration Plan

## Executive Summary

CMG-SeqViewer에 ATAC-seq 분석 기능을 추가하여 chromatin accessibility 데이터를 시각화하고, RNA-seq 데이터와 통합 분석할 수 있는 multi-omics 플랫폼으로 확장합니다.

**개발 기간:** 약 2주 (Phase 1: 1주, Phase 2: 1주)  
**코드 재사용률:** ~80% (기존 인프라 활용)  
**주요 가치:** RNA + ATAC 통합으로 유전자 조절 메커니즘 규명

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

**핵심 가설:**
- Open chromatin (↑ATAC) → Increased transcription (↑RNA)
- Closed chromatin (↓ATAC) → Decreased transcription (↓RNA)
- Discordance → Post-transcriptional regulation

---

## Technical Architecture

### Current System
```
CMG-SeqViewer (v1.0.12)
├── DatasetType
│   ├── DIFFERENTIAL_EXPRESSION
│   └── GO_ANALYSIS
├── DataLoader (Excel, TSV)
├── FilterPanel (log2FC, padj)
├── Visualization (Volcano, Heatmap, Venn)
└── DatabaseManager
```

### Extended System (v2.0)
```
CMG-SeqViewer (v2.0)
├── DatasetType
│   ├── DIFFERENTIAL_EXPRESSION
│   ├── GO_ANALYSIS
│   ├── ATAC_SEQ                    🆕
│   └── MULTI_OMICS                 🆕
├── DataLoader
│   ├── RNA-seq (existing)
│   ├── ATAC-seq (BED, Excel)       🆕
│   └── Multi-omics pair            🆕
├── FilterPanel
│   ├── RNA filters (existing)
│   └── ATAC filters (annotation)   🆕
├── MultiOmicsPanel                 🆕
│   ├── Dataset pairing
│   ├── Integration method
│   └── Concordance analysis
├── Visualization
│   ├── Existing (Volcano, Heatmap, Venn)
│   ├── Genomic Distribution        🆕
│   ├── TSS Distance Plot           🆕
│   ├── Quadrant Plot               🆕
│   └── Concordance Heatmap         🆕
└── DatabaseManager
    ├── RNA-seq datasets (existing)
    ├── ATAC-seq datasets           🆕
    └── Multi-omics pairs           🆕
```

---

## Phase 1: ATAC-seq Standalone Analysis (Week 1)

### Objective
ATAC-seq 데이터를 독립적으로 로드, 필터링, 시각화할 수 있도록 기본 인프라 구축

### 1.1 Data Model Extension

#### StandardColumns for ATAC-seq
```python
# src/models/standard_columns.py

class StandardColumns:
    # Existing RNA-seq columns
    GENE_ID = "gene_id"
    SYMBOL = "symbol"
    LOG2FC = "log2fc"
    ADJ_PVALUE = "adj_pvalue"
    
    # ATAC-seq specific columns 🆕
    PEAK_ID = "peak_id"
    CHROMOSOME = "chromosome"
    START = "start"
    END = "end"
    ANNOTATION = "annotation"
    DISTANCE_TO_TSS = "distance_to_tss"
    NEAREST_GENE = "nearest_gene"
    PEAK_WIDTH = "peak_width"
    AVG_ACCESSIBILITY = "avg_accessibility"
```

#### DatasetType Extension
```python
# src/models/data_models.py

class DatasetType(Enum):
    DIFFERENTIAL_EXPRESSION = "Differential Expression"
    GO_ANALYSIS = "GO Analysis"
    ATAC_SEQ = "ATAC-seq"  🆕
```

#### ATAC-seq Metadata
```python
# src/models/data_models.py

@dataclass
class ATACSeqMetadata:
    """ATAC-seq 데이터셋 메타데이터"""
    genome_build: str = "mm10"  # hg38, mm10, etc.
    peak_caller: str = "MACS2"  # MACS2, HOMER, etc.
    annotation_tool: str = "ChIPseeker"  # ChIPseeker, HOMER, etc.
    total_peaks: int = 0
    promoter_peaks: int = 0
    enhancer_peaks: int = 0
    intergenic_peaks: int = 0
```

### 1.2 Data Loading

#### ATAC-seq Excel Format
```
Expected columns (case-insensitive):
- peak_id, peak_name, or PeakID
- chr, chromosome
- start, startpos
- end, endpos
- log2FoldChange, log2FC, logFC
- padj, FDR, adj.P.Val
- annotation, peak_annotation
- distance_to_TSS, distanceToTSS
- nearest_gene, SYMBOL, gene_name
```

#### Loader Implementation
```python
# src/utils/atac_seq_loader.py 🆕

class ATACSeqLoader:
    """ATAC-seq differential accessibility 데이터 로더"""
    
    def load_from_excel(self, filepath: Path) -> Dataset:
        """
        Excel 파일에서 ATAC-seq 데이터 로드
        
        Returns:
            Dataset with type=DatasetType.ATAC_SEQ
        """
        
    def load_from_bed(self, filepath: Path) -> Dataset:
        """
        BED format 파일 로드 (chr, start, end, ...)
        """
        
    def _detect_annotation_column(self, df: pd.DataFrame) -> str:
        """Annotation 컬럼 자동 감지"""
        
    def _parse_peak_id(self, df: pd.DataFrame) -> pd.Series:
        """
        Peak ID 생성 또는 파싱
        Format: chr1:12345-67890
        """
        
    def _calculate_peak_width(self, df: pd.DataFrame) -> pd.Series:
        """Peak width 계산 (end - start)"""
```

### 1.3 Filtering Panel Extension

#### ATAC-seq Specific Filters
```python
# src/gui/filter_panel.py - extend existing

# 기존 RNA-seq 필터
[x] log2FC threshold: [___1.0___]
[x] Padj threshold: [___0.05___]
[x] Regulation: [Up / Down / Both]

# ATAC-seq 추가 필터 🆕 (dataset type에 따라 동적 표시)
[x] Annotation: [Promoter / Enhancer / Intergenic / All]
[x] Distance to TSS: < [___5000___] bp
[x] Peak width: [___200___] - [___2000___] bp
[x] Accessibility: > [___10___] (mean normalized counts)
```

### 1.4 Visualization (기존 재사용 + 신규)

#### 기존 시각화 재사용
```python
✅ Volcano Plot
   - X-axis: log2FC (accessibility change)
   - Y-axis: -log10(padj)
   - Works as-is!

✅ Heatmap
   - Rows: Peaks
   - Columns: Samples
   - Values: Normalized accessibility
   - Works with minor label changes

✅ Venn Diagram
   - Compare peak sets between conditions
   - Works as-is!
```

#### 신규 시각화

##### A. Genomic Distribution Plot
```python
# src/gui/genomic_distribution_dialog.py 🆕

class GenomicDistributionDialog(QDialog):
    """Peak annotation 분포 pie chart"""
    
    def __init__(self, dataset: Dataset):
        # dataset.dataframe['annotation'] 컬럼 사용
        # Categories: Promoter, Enhancer, Intergenic, Gene Body, etc.
        
    def _create_pie_chart(self):
        # matplotlib pie chart
        # Labels with counts and percentages
```

##### B. TSS Distance Plot
```python
# src/gui/tss_distance_dialog.py 🆕

class TSSDistanceDialog(QDialog):
    """Peak distance to TSS histogram"""
    
    def __init__(self, dataset: Dataset):
        # dataset.dataframe['distance_to_tss'] 컬럼 사용
        
    def _create_histogram(self):
        # X-axis: Distance to TSS (bp)
        # Y-axis: Number of peaks
        # Bins: -50kb to +50kb
```

##### C. Peak Width Distribution
```python
# src/gui/peak_width_dialog.py 🆕

class PeakWidthDialog(QDialog):
    """Peak width distribution"""
    
    def _create_histogram(self):
        # X-axis: Peak width (bp)
        # Y-axis: Frequency
        # Typical range: 200-2000bp for ATAC-seq
```

### 1.5 Database Support

#### Metadata Extension
```python
# src/models/data_models.py

class PreloadedDatasetMetadata:
    # Existing fields...
    
    # ATAC-seq specific 🆕
    genome_build: Optional[str] = None
    peak_caller: Optional[str] = None
    total_peaks: int = 0
    promoter_count: int = 0
    enhancer_count: int = 0
```

#### Database Manager
```python
# src/utils/database_manager.py - minor updates

def import_dataset(self, dataset: Dataset, metadata: PreloadedDatasetMetadata):
    # Handle both RNA-seq and ATAC-seq
    if dataset.dataset_type == DatasetType.ATAC_SEQ:
        metadata.total_peaks = len(dataset.dataframe)
        # Calculate annotation counts
```

### 1.6 GUI Updates

#### Menu Bar
```python
# src/gui/main_window.py

File Menu:
  ├─ Open Dataset (RNA-seq)
  ├─ Open ATAC-seq Dataset  🆕
  └─ ...

Visualization Menu:
  ├─ Volcano Plot (works for both)
  ├─ Heatmap (works for both)
  ├─ Venn Diagram (works for both)
  ├─ Genomic Distribution  🆕 (ATAC-seq only)
  └─ TSS Distance Plot  🆕 (ATAC-seq only)
```

### Phase 1 Deliverables

- [ ] `StandardColumns` extended with ATAC-seq columns
- [ ] `DatasetType.ATAC_SEQ` added
- [ ] `ATACSeqLoader` class implemented
- [ ] `ATACSeqMetadata` dataclass
- [ ] Filter Panel with ATAC-specific filters
- [ ] Genomic Distribution dialog
- [ ] TSS Distance dialog
- [ ] Peak Width dialog
- [ ] Database support for ATAC-seq
- [ ] Menu updates
- [ ] Unit tests for ATAC-seq loading
- [ ] Documentation update

**Estimated Time:** 5-7 days

---

## Phase 2: Multi-Omics Integration (Week 2)

### Objective
RNA-seq와 ATAC-seq 데이터를 유전자 수준에서 통합하여 concordance/discordance 분석

### 2.1 Data Model

#### MultiOmicsDataset Class
```python
# src/models/multi_omics_dataset.py 🆕

@dataclass
class MultiOmicsDataset:
    """RNA-seq + ATAC-seq 통합 데이터셋"""
    
    name: str
    rna_dataset: Dataset
    atac_dataset: Dataset
    integration_method: str  # "nearest_gene", "promoter_only", "all_peaks"
    integrated_data: Optional[pd.DataFrame] = None
    
    def integrate(self) -> pd.DataFrame:
        """
        유전자 수준 통합
        
        Returns DataFrame with columns:
            gene_id, symbol,
            rna_log2fc, rna_padj, rna_base_mean,
            peak_count, atac_log2fc_mean, atac_log2fc_max, atac_padj_min,
            concordance, regulatory_status
        """
        
    def classify_concordance(self, row) -> str:
        """
        Concordance 분류:
        - Concordant_Both_UP: RNA ↑, ATAC ↑
        - Concordant_Both_DOWN: RNA ↓, ATAC ↓
        - Discordant_RNA_UP_ATAC_DOWN: RNA ↑, ATAC ↓
        - Discordant_RNA_DOWN_ATAC_UP: RNA ↓, ATAC ↑
        - RNA_only: RNA significant, no ATAC peak
        - ATAC_only: ATAC peak, no RNA change
        - Not_significant: Neither significant
        """
```

#### Integration Methods
```python
class IntegrationMethod(Enum):
    NEAREST_GENE = "nearest_gene"      # ATAC peak의 nearest_gene 사용
    PROMOTER_ONLY = "promoter_only"    # Promoter annotation만
    ALL_PEAKS = "all_peaks"            # 모든 peak (거리 무관)
    CUSTOM_DISTANCE = "custom"         # User-defined TSS distance
```

### 2.2 Integration Algorithm

```python
# src/utils/multi_omics_integrator.py 🆕

class MultiOmicsIntegrator:
    
    def integrate_by_nearest_gene(
        self,
        rna_df: pd.DataFrame,
        atac_df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        ATAC-seq의 nearest_gene 컬럼을 기준으로 통합
        
        Steps:
        1. ATAC-seq peaks를 nearest_gene으로 그룹화
        2. 각 gene에 대해:
           - Peak count
           - Mean/Max log2FC
           - Min padj
        3. RNA-seq 데이터와 gene_id/symbol로 merge
        4. Concordance 계산
        """
        
    def integrate_by_promoter(
        self,
        rna_df: pd.DataFrame,
        atac_df: pd.DataFrame,
        tss_window: int = 2000
    ) -> pd.DataFrame:
        """
        Promoter region (TSS ± window) peak만 사용
        """
        
    def calculate_concordance_score(
        self,
        rna_log2fc: float,
        atac_log2fc: float,
        rna_padj: float,
        atac_padj: float,
        rna_thresh: float = 0.05,
        atac_thresh: float = 0.05
    ) -> dict:
        """
        Returns:
            {
                'concordance': 'Concordant_Both_UP',
                'rna_sig': True,
                'atac_sig': True,
                'same_direction': True,
                'score': 0.95  # correlation-like score
            }
        """
```

### 2.3 GUI: Multi-Omics Panel

```python
# src/gui/multi_omics_panel.py 🆕

class MultiOmicsPanel(QWidget):
    """Left panel for multi-omics integration"""
    
    def __init__(self):
        # UI Components:
        
        # Dataset Selection
        self.rna_combo = QComboBox()  # RNA-seq datasets
        self.atac_combo = QComboBox()  # ATAC-seq datasets
        
        # Integration Method
        self.method_combo = QComboBox()
        # Options: Nearest Gene, Promoter Only, All Peaks, Custom
        
        # Custom Distance (for CUSTOM_DISTANCE method)
        self.tss_distance_input = QLineEdit("2000")
        
        # Thresholds
        self.rna_padj_thresh = QDoubleSpinBox()  # default: 0.05
        self.atac_padj_thresh = QDoubleSpinBox()  # default: 0.05
        self.rna_log2fc_thresh = QDoubleSpinBox()  # default: 1.0
        self.atac_log2fc_thresh = QDoubleSpinBox()  # default: 1.0
        
        # Actions
        self.integrate_btn = QPushButton("🔗 Integrate RNA + ATAC")
        self.export_btn = QPushButton("💾 Export Integrated Data")
        
    def on_integrate_clicked(self):
        # 1. Validate dataset selection
        # 2. Create MultiOmicsDataset
        # 3. Run integration
        # 4. Create new tab with results
        # 5. Show summary statistics
```

### 2.4 Visualizations

#### A. Quadrant Plot (4-Quadrant Scatter)
```python
# src/gui/quadrant_plot_dialog.py 🆕

class QuadrantPlotDialog(QDialog):
    """
    4-Quadrant plot for multi-omics
    
    X-axis: ATAC-seq log2FC
    Y-axis: RNA-seq log2FC
    
    Quadrants:
        Q1 (top-right): Both UP (concordant)
        Q2 (top-left): RNA UP, ATAC DOWN (discordant)
        Q3 (bottom-left): Both DOWN (concordant)
        Q4 (bottom-right): RNA DOWN, ATAC UP (discordant)
    
    Features:
    - Color by concordance status
    - Size by significance (min of RNA/ATAC padj)
    - Hover tooltip: gene symbol, RNA/ATAC values
    - Quadrant lines at 0,0 (customizable thresholds)
    - Click to select genes → export list
    """
```

#### B. Concordance Heatmap
```python
# src/gui/concordance_heatmap_dialog.py 🆕

class ConcordanceHeatmapDialog(QDialog):
    """
    Dual-column heatmap
    
    Rows: Genes (sorted by concordance or significance)
    Columns: [RNA_log2FC, ATAC_log2FC]
    
    Features:
    - Color scale: Red (up) to Blue (down)
    - Cluster genes by similarity (optional)
    - Sidebar annotation: concordance status
    - Gene labels on Y-axis
    """
```

#### C. Integrated Volcano Plot
```python
# src/gui/integrated_volcano_dialog.py 🆕

class IntegratedVolcanoDialog(QDialog):
    """
    Modified volcano plot for integrated data
    
    X-axis: RNA log2FC
    Y-axis: -log10(RNA padj)
    
    Point colors:
    - Green: Concordant (ATAC supports RNA)
    - Red: Discordant (ATAC contradicts RNA)
    - Gray: RNA-only (no ATAC peak)
    
    Point size: Number of ATAC peaks near gene
    """
```

#### D. Concordance Summary Bar Chart
```python
# src/gui/concordance_summary_dialog.py 🆕

class ConcordanceSummaryDialog(QDialog):
    """
    Stacked bar chart showing concordance distribution
    
    Categories:
    - Concordant Both UP
    - Concordant Both DOWN
    - Discordant (RNA UP, ATAC DOWN)
    - Discordant (RNA DOWN, ATAC UP)
    - RNA-only significant
    - ATAC-only significant
    - Not significant
    
    Shows counts and percentages
    """
```

### 2.5 Export Functionality

#### Integrated Data Export
```python
# Output format: Excel with multiple sheets

Sheet 1: "Integrated_Summary"
├─ gene_id
├─ symbol
├─ rna_log2fc, rna_padj, rna_base_mean
├─ atac_peak_count
├─ atac_log2fc_mean, atac_log2fc_max
├─ atac_padj_min
├─ concordance_status
└─ regulatory_category

Sheet 2: "Concordant_Both_UP"
└─ Filtered genes (concordant up-regulation)

Sheet 3: "Concordant_Both_DOWN"
└─ Filtered genes (concordant down-regulation)

Sheet 4: "Discordant"
└─ All discordant genes

Sheet 5: "RNA_only"
└─ Genes with RNA change but no ATAC peak

Sheet 6: "ATAC_only"
└─ Genes with ATAC peak but no RNA change

Sheet 7: "Peak_Details"
├─ peak_id
├─ nearest_gene
├─ annotation
├─ distance_to_tss
└─ log2fc, padj
```

### 2.6 Menu Updates

```python
# src/gui/main_window.py

File Menu:
  ├─ Open Dataset (RNA-seq)
  ├─ Open ATAC-seq Dataset
  ├─ Open Multi-Omics Pair  🆕
  └─ ...

Analysis Menu:
  ├─ Filter Data
  ├─ Compare Datasets
  ├─ Integrate RNA + ATAC  🆕
  └─ ...

Visualization Menu (when multi-omics tab is active):
  ├─ Quadrant Plot  🆕
  ├─ Concordance Heatmap  🆕
  ├─ Integrated Volcano  🆕
  ├─ Concordance Summary  🆕
  └─ ...
```

### Phase 2 Deliverables

- [ ] `MultiOmicsDataset` class
- [ ] `MultiOmicsIntegrator` utility
- [ ] `MultiOmicsPanel` GUI component
- [ ] Quadrant Plot dialog
- [ ] Concordance Heatmap dialog
- [ ] Integrated Volcano dialog
- [ ] Concordance Summary dialog
- [ ] Multi-sheet Excel export
- [ ] Database support for multi-omics pairs
- [ ] Unit tests for integration algorithms
- [ ] Integration workflow documentation

**Estimated Time:** 5-7 days

---

## Data Format Specifications

### Input: ATAC-seq Differential Accessibility

#### Excel Format (Preferred)
```
Required columns:
- peak_id or peak_name or PeakID
- chr or chromosome
- start or startpos
- end or endpos
- log2FoldChange or log2FC or logFC
- padj or FDR or adj.P.Val

Optional columns:
- annotation or peak_annotation
- distance_to_TSS or distanceToTSS
- nearest_gene or SYMBOL or gene_name
- base_mean or avg_accessibility
```

Example:
```csv
peak_id,chr,start,end,log2FC,padj,annotation,nearest_gene,distance_to_tss,avg_accessibility
peak_1,chr1,1234567,1234890,2.3,0.001,Promoter,Gapdh,-500,150.5
peak_2,chr2,9876543,9877000,-1.8,0.01,Enhancer,Actb,5000,80.2
peak_3,chr3,1111111,1111555,3.1,0.0001,Intergenic,Tp53,50000,200.1
peak_4,chr1,5555555,5556000,1.5,0.05,Gene_Body,Actb,0,120.0
```

#### BED Format (Alternative)
```
# BED format with additional columns
chr1    1234567    1234890    peak_1    150.5    +    2.3    0.001    Gapdh
chr2    9876543    9877000    peak_2    80.2     +    -1.8   0.01     Actb
```

### Output: Integrated RNA + ATAC

```csv
gene_id,symbol,rna_log2fc,rna_padj,rna_base_mean,atac_peak_count,atac_log2fc_mean,atac_log2fc_max,atac_padj_min,concordance,status
ENSMUSG00001,Gapdh,2.1,0.001,1500.5,3,2.5,3.2,0.0001,Concordant,Both_UP
ENSMUSG00002,Actb,-1.5,0.01,2000.3,1,-1.2,- -1.2,0.05,Concordant,Both_DOWN
ENSMUSG00003,Tp53,2.8,0.001,800.2,0,NA,NA,NA,RNA_only,Activated_no_peak
ENSMUSG00004,Cdkn1a,-0.3,0.5,500.1,5,3.2,4.5,0.001,Discordant,Open_not_expressed
ENSMUSG00005,Myc,0.5,0.4,1200.0,2,1.8,2.1,0.01,ATAC_only,Accessible_not_changed
```

---

## Use Case Scenarios

### Scenario 1: ATAC-seq 단독 분석

**Context:** Neuron vs Astrocyte ATAC-seq 실험

**Workflow:**
1. Load ATAC-seq differential accessibility results
2. Filter: `padj < 0.05`, `|log2FC| > 1`
3. Sub-filter by annotation: `Promoter` only
4. Volcano plot → identify cell-type specific accessible promoters
5. Genomic Distribution plot → see annotation breakdown
6. Export peak list → input for HOMER motif analysis
7. GO enrichment on nearest genes → identify pathways

**Expected Results:**
- ~5,000 total differential peaks
- ~1,200 promoter peaks
- Neuron-specific: Synaptic gene promoters open
- Astrocyte-specific: Metabolic gene promoters open

### Scenario 2: RNA + ATAC 통합 분석

**Context:** Drug treatment time-course study

**Datasets:**
- RNA-seq: Drug_24hr vs Control
- ATAC-seq: Drug_24hr vs Control

**Workflow:**
1. Load both datasets
2. Multi-Omics Panel → pair datasets
3. Integration method: "Nearest Gene"
4. Set thresholds: `RNA padj < 0.05`, `ATAC padj < 0.05`
5. Run integration
6. Quadrant plot → visualize 4 categories
7. Filter: Concordant Both UP
8. Export gene list → validation candidates
9. Analyze discordant genes → post-transcriptional regulation?

**Expected Results:**
- ~3,000 genes with RNA changes
- ~8,000 ATAC peaks
- ~1,200 genes with concordant changes
- ~500 discordant genes (investigate miRNA, protein stability)

### Scenario 3: Multi-Condition Comparison

**Context:** Developmental time-course (Day0, Day3, Day7)

**Datasets:**
- RNA-seq: 3 time points, 3 comparisons
- ATAC-seq: 3 time points, 3 comparisons

**Workflow:**
1. Load all 6 datasets (3 RNA + 3 ATAC)
2. Integrate pairs:
   - Day3 vs Day0 (RNA + ATAC)
   - Day7 vs Day0 (RNA + ATAC)
   - Day7 vs Day3 (RNA + ATAC)
3. Compare temporal dynamics:
   - Early chromatin opening (Day3) → delayed expression (Day7)?
   - Chromatin closing → immediate downregulation?
4. Cluster genes by temporal pattern
5. Identify regulatory windows

**Expected Insights:**
- Pioneer factors (chromatin opens first)
- Late-response genes (requires sustained chromatin opening)
- Transient vs stable chromatin changes

### Scenario 4: Enhancer-Gene Linking

**Context:** Cell differentiation study

**Workflow:**
1. Load ATAC-seq with enhancer annotations
2. Filter: `Annotation = Enhancer`, `|log2FC| > 1.5`
3. Integrate with RNA-seq using `all_peaks` method
4. For each enhancer:
   - Find genes within 500kb
   - Check RNA expression correlation
5. Identify putative enhancer-gene pairs
6. Validate with Hi-C or H3K27ac ChIP-seq

**Advanced Analysis:**
- Motif enrichment in differential enhancers
- TF binding site prediction
- Super-enhancer identification

---

## Technical Implementation Details

### Code Reuse Strategy

#### Fully Reusable (No Changes)
```python
✅ Dataset base class
✅ FilterPanel (add filters, don't replace)
✅ VolcanoPlotDialog (works for ATAC)
✅ HeatmapDialog (works for ATAC)
✅ VennDiagramDialog (works for ATAC)
✅ ExportHandler (works for any DataFrame)
✅ ClipboardHandler
✅ LogHandler
```

#### Minor Modifications Needed
```python
⚠️ DataLoader → add ATAC-seq format detection
⚠️ ColumnMapperDialog → add ATAC-seq templates
⚠️ DatabaseManager → extend metadata schema
⚠️ MainWindow menus → add ATAC/Multi-omics items
⚠️ DatasetManager → handle ATAC dataset type
```

#### New Components
```python
🆕 ATACSeqLoader
🆕 MultiOmicsDataset
🆕 MultiOmicsIntegrator
🆕 MultiOmicsPanel
🆕 QuadrantPlotDialog
🆕 ConcordanceHeatmapDialog
🆕 GenomicDistributionDialog
🆕 TSSDistancePlotDialog
```

### Database Schema Updates

#### metadata.json Extension
```json
{
  "version": "2.0",
  "datasets": [
    {
      "dataset_id": "uuid-1234",
      "alias": "Neuron_vs_Astro_RNA",
      "dataset_type": "Differential Expression",
      ...
    },
    {
      "dataset_id": "uuid-5678",
      "alias": "Neuron_vs_Astro_ATAC",
      "dataset_type": "ATAC-seq",
      "genome_build": "mm10",
      "peak_caller": "MACS2",
      "total_peaks": 45000,
      "promoter_peaks": 12000,
      "enhancer_peaks": 18000,
      ...
    }
  ],
  "multi_omics_pairs": [
    {
      "pair_id": "uuid-9999",
      "name": "Neuron_vs_Astro_Integrated",
      "rna_dataset_id": "uuid-1234",
      "atac_dataset_id": "uuid-5678",
      "integration_method": "nearest_gene",
      "created_date": "2026-03-01T10:00:00"
    }
  ]
}
```

### Performance Considerations

#### Large Dataset Handling
```python
# ATAC-seq datasets can be large (100k+ peaks)

Optimizations:
1. Lazy loading for peak details
2. Indexed search for nearest gene lookup
3. Chunked processing for integration
4. Progress bars for long operations
5. Matplotlib downsampling for >10k points
```

#### Memory Management
```python
# Integration creates gene × peak mappings

Strategy:
1. Use sparse matrices for large peak sets
2. Stream processing for export
3. Release intermediate DataFrames
4. Optional: SQLite backend for huge datasets
```

---

## Testing Strategy

### Unit Tests

```python
# tests/test_atac_seq_loader.py
def test_load_atac_excel():
    # Test ATAC-seq Excel loading
    
def test_detect_peak_columns():
    # Test column auto-detection
    
def test_parse_peak_id():
    # Test chr1:12345-67890 parsing

# tests/test_multi_omics_integrator.py
def test_integrate_by_nearest_gene():
    # Test integration algorithm
    
def test_concordance_classification():
    # Test concordance logic
    
def test_promoter_filtering():
    # Test promoter-only integration
```

### Integration Tests

```python
# tests/integration/test_atac_workflow.py
def test_complete_atac_workflow():
    # Load → Filter → Visualize → Export
    
# tests/integration/test_multiomics_workflow.py
def test_rna_atac_integration():
    # Load both → Integrate → Export
```

### Test Data

```python
# tests/data/
├── atac_sample.xlsx          # 100 peaks
├── rna_sample.xlsx           # 50 genes
├── integrated_expected.xlsx  # Expected output
└── edge_cases/
    ├── no_overlap.xlsx       # RNA/ATAC with no overlap
    ├── missing_annotation.xlsx
    └── malformed_peak_id.xlsx
```

---

## Documentation Updates

### User Documentation

#### Help Dialog Updates
```markdown
New sections:
- "9. ATAC-seq Analysis"
  - Loading ATAC-seq data
  - ATAC-specific filters
  - Genomic distribution visualization
  - TSS distance plots

- "10. Multi-Omics Integration"
  - Pairing RNA and ATAC datasets
  - Integration methods
  - Concordance analysis
  - Quadrant plots
  - Use cases and workflows
```

#### README Updates
```markdown
## Features (v2.0)

### RNA-seq Analysis
- Differential expression visualization
- GO/KEGG enrichment
- Dataset comparison
- ...

### ATAC-seq Analysis 🆕
- Differential accessibility analysis
- Peak annotation visualization
- Genomic distribution plots
- TSS distance analysis

### Multi-Omics Integration 🆕
- RNA-seq + ATAC-seq pairing
- Gene-level concordance analysis
- Regulatory mechanism insights
- Integrated visualizations
```

### Developer Documentation

```markdown
# docs/ATAC_SEQ_ARCHITECTURE.md

## Module Structure
- models/: DatasetType, StandardColumns
- utils/: ATACSeqLoader, MultiOmicsIntegrator
- gui/: ATACSeqPanel, MultiOmicsPanel, new dialogs
- workers/: Integration background tasks

## Adding New Integration Methods
[Step-by-step guide]

## Extending Annotation Types
[How to support new peak annotations]
```

---

## Migration Plan

### Version Compatibility

```python
# Backward compatibility strategy

v1.x databases → v2.0:
✅ Fully compatible
✅ Existing RNA-seq datasets load normally
✅ New ATAC-seq and multi-omics features added

v2.0 databases → v1.x:
⚠️ ATAC-seq datasets will be ignored
⚠️ Multi-omics pairs will be ignored
⚠️ RNA-seq datasets still work
```

### Database Migration

```python
# src/utils/database_migrator.py 🆕

class DatabaseMigrator:
    
    def migrate_v1_to_v2(self, metadata_file: Path):
        """
        Add v2.0 fields to existing metadata.json
        
        Changes:
        - Add "version": "2.0"
        - Add "multi_omics_pairs": []
        - For each dataset, add type-specific fields
        """
```

---

## Release Plan

### Version 2.0 Roadmap

#### Pre-release (1 week)
- [ ] Finalize Phase 1 implementation
- [ ] Finalize Phase 2 implementation
- [ ] Complete unit tests (>80% coverage)
- [ ] Integration tests
- [ ] Documentation complete
- [ ] Internal testing with real datasets

#### Beta Release (v2.0-beta, 1 week)
- [ ] Release to select users
- [ ] Gather feedback
- [ ] Bug fixes
- [ ] Performance tuning
- [ ] UI/UX refinements

#### Official Release (v2.0, 1 week)
- [ ] Final testing
- [ ] Changelog finalization
- [ ] README updates
- [ ] GitHub release with binaries
- [ ] Announcement

**Total Timeline:** 4-5 weeks from start to v2.0 release

---

## Future Enhancements (Post v2.0)

### Phase 3: Advanced ATAC-seq Features

#### A. Motif Enrichment Integration
```python
# Integration with HOMER, MEME
- Export peak sequences for motif analysis
- Import motif results
- Visualize TF binding site enrichment
```

#### B. TF Footprinting
```python
# Visualize TF binding footprints
- Plot aggregate footprints
- Identify bound vs unbound motifs
- TF activity inference
```

#### C. Chromatin State Annotation
```python
# ChromHMM, Roadmap Epigenomics integration
- Overlay chromatin states
- Enhance functional annotation
- Cell-type specific states
```

### Phase 4: Additional Omics Types

#### A. ChIP-seq Integration
```python
DatasetType.CHIP_SEQ
- H3K27ac (active enhancers)
- H3K4me3 (active promoters)
- H3K27me3 (repressed regions)
- Integrate with RNA + ATAC
```

#### B. CUT&RUN / CUT&Tag
```python
# Similar to ChIP-seq but higher resolution
DatasetType.CUT_AND_RUN
- TF binding sites
- Histone modifications
```

#### C. Hi-C Integration
```python
# Chromatin interaction data
- Link distal enhancers to promoters
- Validate ATAC-RNA associations
- TAD boundary analysis
```

### Phase 5: Machine Learning Features

#### A. Predictive Modeling
```python
# Train models to predict:
- RNA expression from ATAC accessibility
- Enhancer-gene linkages
- TF binding from sequence + accessibility
```

#### B. Clustering & Classification
```python
# Advanced pattern recognition:
- Multi-omics clustering (RNA + ATAC)
- Cell state prediction
- Regulatory module discovery
```

---

## Risk Assessment & Mitigation

### Technical Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Peak annotation inconsistency | High | Medium | Support multiple tools (ChIPseeker, HOMER), flexible parsing |
| Large dataset performance | Medium | High | Implement lazy loading, chunked processing, progress indicators |
| Integration algorithm bugs | Medium | High | Extensive unit tests, validate with known datasets |
| UI complexity | Medium | Medium | User testing, iterative refinement, clear documentation |

### Scientific Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Naive integration misses biology | Medium | High | Multiple integration methods, expert consultation |
| Concordance thresholds arbitrary | High | Medium | Make thresholds user-configurable, document choices |
| Enhancer-gene links incorrect | Medium | Medium | Provide multiple distance options, clear caveats |

### Project Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Scope creep | High | High | Strict phase boundaries, defer Phase 3+ features |
| Testing insufficient | Medium | High | Allocate 30% time to testing, automated CI/CD |
| Documentation lag | Medium | Medium | Write docs in parallel, not after coding |

---

## Success Metrics

### Technical Metrics
- [ ] Load 50k+ peak ATAC-seq file in <5 seconds
- [ ] Integrate 3k genes (RNA) × 30k peaks (ATAC) in <10 seconds
- [ ] Render quadrant plot with 5k points smoothly
- [ ] Unit test coverage >80%
- [ ] Zero critical bugs in beta release

### User Metrics
- [ ] 5+ beta testers provide feedback
- [ ] Average user rating >4/5
- [ ] Documentation clarity rating >4/5
- [ ] 90% of users complete integration workflow successfully

### Scientific Metrics
- [ ] Concordance rates match literature (~60-70%)
- [ ] Reproduces published ATAC+RNA integration results
- [ ] Identified concordant genes validated by qPCR/ChIP

---

## References & Resources

### Tools & Algorithms
- **MACS2/3:** Peak calling (Zhang et al., 2008)
- **ChIPseeker:** Peak annotation (Yu et al., 2015)
- **DiffBind:** Differential accessibility (Ross-Innes et al., 2012)
- **ATACseqQC:** Quality control (Ou et al., 2018)

### Multi-Omics Integration
- **MOFA+:** Multi-Omics Factor Analysis (Argelaguet et al., 2020)
- **Seurat v5:** Multi-modal analysis (Hao et al., 2024)
- **GLUE:** Graph-linked unified embedding (Cao et al., 2022)

### Literature
- Buenrostro et al. (2013): Original ATAC-seq paper
- Corces et al. (2018): ATAC-seq best practices
- Granja et al. (2021): ArchR for scATAC-seq
- Wu et al. (2021): Chromatin accessibility and gene expression

---

## Appendix

### A. Column Mapping Templates

#### ATAC-seq (ChIPseeker output)
```yaml
peak_id: ["seqnames", "start", "end"]  # Combine to chr:start-end
chromosome: ["seqnames", "chr"]
start: ["start", "startpos"]
end: ["end", "endpos"]
log2fc: ["log2FoldChange", "log2FC", "logFC"]
adj_pvalue: ["padj", "FDR", "adj.P.Val"]
annotation: ["annotation", "peak_annotation"]
distance_to_tss: ["distanceToTSS", "distance_to_TSS"]
nearest_gene: ["SYMBOL", "geneId", "nearest_gene"]
```

#### ATAC-seq (DiffBind output)
```yaml
peak_id: "PeakID"
chromosome: "Chr"
start: "Start"
end: "End"
log2fc: "Fold"
adj_pvalue: "FDR"
avg_accessibility: "Conc"
```

### B. Sample Workflow Scripts

#### Bash script for data preparation
```bash
#!/bin/bash
# prepare_atac_for_viewer.sh

# Input: MACS2 narrowPeak + DESeq2 results
# Output: CMG-SeqViewer compatible Excel

# 1. Annotate peaks with ChIPseeker (R)
Rscript annotate_peaks.R peaks.narrowPeak mm10 > annotated_peaks.txt

# 2. Merge with differential analysis
python merge_diff_annotation.py \
    diffbind_results.csv \
    annotated_peaks.txt \
    -o atac_for_viewer.xlsx
```

#### Python helper script
```python
# merge_diff_annotation.py
"""
Merge DiffBind results with peak annotations
for CMG-SeqViewer import
"""

import pandas as pd
import sys

def merge_atac_data(diff_file, annot_file, output_file):
    # Load files
    diff = pd.read_csv(diff_file)
    annot = pd.read_csv(annot_file, sep='\t')
    
    # Merge on peak coordinates
    merged = diff.merge(annot, on=['chr', 'start', 'end'])
    
    # Standardize columns for CMG-SeqViewer
    viewer_df = pd.DataFrame({
        'peak_id': merged['chr'] + ':' + merged['start'].astype(str) + '-' + merged['end'].astype(str),
        'chromosome': merged['chr'],
        'start': merged['start'],
        'end': merged['end'],
        'log2fc': merged['Fold'],
        'adj_pvalue': merged['FDR'],
        'annotation': merged['annotation'],
        'nearest_gene': merged['SYMBOL'],
        'distance_to_tss': merged['distanceToTSS'],
        'avg_accessibility': merged['Conc']
    })
    
    # Export to Excel
    viewer_df.to_excel(output_file, index=False)
    print(f"✅ Saved: {output_file}")

if __name__ == "__main__":
    merge_atac_data(sys.argv[1], sys.argv[2], sys.argv[3])
```

---

## Contact & Contribution

**Maintainer:** CMG-NGS Team  
**Repository:** https://github.com/ibs-CMG-NGS/cmg-seqviewer  
**Issues:** https://github.com/ibs-CMG-NGS/cmg-seqviewer/issues

**For questions or suggestions regarding ATAC-seq integration:**
- Open a GitHub issue with label `enhancement` or `atac-seq`
- Reach out to the development team

---

## Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-28 | AI Assistant | Initial draft of ATAC-seq integration plan |

---

**Next Steps:**
1. Review this plan with the team
2. Prioritize features (Must-have vs Nice-to-have)
3. Set up development branch: `feature/atac-seq-support`
4. Begin Phase 1 implementation
5. Schedule weekly progress reviews

---

*End of Document*
