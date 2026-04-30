# CMG-SeqViewer - Multi-omics Data Analysis & Visualization

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![PyQt6](https://img.shields.io/badge/PyQt-6-green.svg)](https://www.riverbankcomputing.com/software/pyqt/)
[![Release](https://img.shields.io/badge/release-v1.2.0-brightgreen.svg)](https://github.com/ibs-CMG-NGS/cmg-seqviewer/releases)

---

## Overview

**CMG-SeqViewer** is a desktop application for multi-omics data analysis and visualization. It supports RNA-seq differential expression (DE), ATAC-seq differential accessibility (DA), and GO/KEGG pathway enrichment results. Built with Python and PyQt6, it provides an Excel-like interface for biologists to explore genomic data without programming.

---

## Latest Update: v1.2.0 (Apr 2026)

- [NEW] **ATAC-seq DA Support**: Load and explore ATAC-seq differential accessibility results (Excel / Parquet). Auto-detected from `peak_id` column; supports HOMER-annotated DESeq2 output format
- [NEW] **ATAC-seq Filters**: Annotation category (Intergenic / Intron / Promoter-TSS / …), Distance to TSS (|TSS| ≤ N bp), Peak Width range — all in the Statistical filter tab
- [NEW] **Genomic Distribution Plot**: Pie chart of peak annotation categories (broad categories, HOMER strings auto-normalized)
- [NEW] **TSS Distance Plot**: Histogram of peak–TSS distances with ±2 kb / ±5 kb reference lines
- [NEW] **MA Plot**: log₂(base mean) vs log₂FC scatter plot with threshold coloring, gene labels, and hover tooltips
- [IMPROVED] **Column Display Level**: renamed to **Basic / Stat / Full** — applies uniformly to both RNA-seq and ATAC-seq datasets
- [FIX] ATAC-seq data correctly recognized on initial load (filter panel and viz menu activate immediately)
- [FIX] Tab index shift bug when re-applying filters to existing filtered tabs

### Previous: v1.1.6 (Apr 2026)

- [NEW] **GO Term List Filtering**: Paste `GO:XXXXXXX` IDs into the Filter Panel to filter any GO/KEGG dataset to a specific set of terms; results in a new *"Filtered: GO Term List"* tab
- [NEW] **GO Term Comparison**: Compare enriched GO/KEGG terms across ≥2 datasets side by side — union of terms collected, per-dataset FDR / gene count / fold enrichment in wide-format table
- [NEW] **GO Term Comparison Dot Plot**: Interactive dot plot for GO comparison results (X = datasets, Y = terms; dot size = Gene Count or Fold Enrichment; dot color = FDR)
- [IMPROVED] **Dot Plot Size Legend**: 3-tier biologically meaningful reference markers with correct area→diameter formula; consistent across sessions

### Previous: v1.1.5 (Apr 2026)

- [NEW] Multi-Group Heatmap (LRT omnibus result → Z-score clustermap with group colour bars and gene cluster cutting)
- [NEW] Gene List Filtering on Multi-Group sheets
- [FIX] Gene list order preservation, cluster_id dtype, save figure error handling

[Full Release Notes](docs/RECENT_UPDATES.md)

---

## System Requirements

### Windows
- OS: Windows 10 (64-bit) or later
- Architecture: x64
- Memory: 4 GB RAM minimum, 8 GB recommended
- Display: 1280x720 minimum resolution

### macOS
- OS: macOS 13.0 Ventura or later
- Architecture: Intel (x86_64) or Apple Silicon (via Rosetta 2)
- Memory: 4 GB RAM minimum, 8 GB recommended
- Note: PyQt6 requires macOS 13.0+

---

## Key Features

### Data Management
- **Multi-dataset Support**: Load and manage multiple datasets simultaneously (RNA-seq DE, ATAC-seq DA, GO/KEGG)
- **Auto-detection**: Dataset type is detected automatically on load — no manual selection needed
- **Smart Column Mapping**: Automatic detection of 30+ column name variants (including dot-separator formats)
- **Drag & Drop**: Drop Excel/CSV/parquet files directly onto the application
- **Recent Files**: Quick access to last 10 loaded datasets
- **Dataset Renaming**: Change names anytime — updates everywhere automatically

### Filtering
- **Statistical Filter (DE/DA)**: adj. p-value, |log2FC|, regulation direction (Up/Down/Both)
- **ATAC-seq Filters**: Annotation category, Distance to TSS, Peak Width
- **Gene List Filter**:
  - DE data: exact match on gene ID/symbol
  - ATAC-seq data: match on `nearest_gene` (gene symbol)
  - GO/KEGG data: finds GO terms containing any of the input genes; sorted by overlap count
- **Advanced GO Filter**: FDR, gene count range, description keyword search, ontology and direction selection

### ATAC-seq Analysis
- **Differential Accessibility (DA)**: Load DESeq2-based DA results with HOMER annotation
- **Genomic Distribution**: Pie chart of peak categories (Intergenic, Intron, Promoter-TSS, Exon, …)
- **TSS Distance Plot**: Histogram with ±2 kb / ±5 kb reference lines
- **MA Plot**: log₂(base mean) vs log₂FC with threshold coloring, gene labels, hover tooltips
- **Column levels**: Basic (coordinates) → Stat (+log2fc/padj) → Full (all annotation columns)

### GO/KEGG Analysis
- **Clustering**: Jaccard similarity, Kappa statistic, hierarchical clustering (average/complete/single/ward)
- **Network Visualization**: Color-coded clusters, convex hulls, hover tooltips, pan/zoom
- **Dot Plot**: Configurable dot size (Gene Count / Gene Ratio / Fold Enrichment) and color (FDR / p-value)
- **Bar Chart**: Top enriched terms
- **GO Term List Filtering**: Filter GO datasets to a predefined set of `GO:XXXXXXX` IDs
- **GO Term Comparison**: Compare terms across ≥2 GO datasets with wide-format table and companion dot plot

### Multi-dataset Comparison
- **Gene List Comparison**: Wide-format table showing log2FC and padj across datasets
- **Statistics Comparison**: Common/Unique DEG identification with |log2FC| >= threshold and padj <= threshold
- **GO Term Comparison**: Side-by-side GO/KEGG enrichment comparison across multiple datasets
- **Venn Diagrams**: 2-3 dataset overlap visualization

### Visualizations
- **Volcano Plot**: log2FC vs -log10(padj) — works for both RNA-seq and ATAC-seq
- **MA Plot**: log₂(base mean) vs log₂FC — ATAC-seq and RNA-seq
- **Heatmap**: Expression patterns with hierarchical clustering
- **P-adj Histogram**: Distribution of significance values

---

## Installation

> **Note**: This public repository does not include internal research datasets. Load your own Excel/CSV/parquet files. For internal distribution with pre-loaded data, see [Internal Distribution Guide](docs/INTERNAL_DISTRIBUTION.md).

### Option 1: Download Pre-built Executable (Recommended)

**Windows**
1. Go to [Releases](https://github.com/ibs-CMG-NGS/cmg-seqviewer/releases)
2. Download `CMG-SeqViewer-Windows.zip`
3. Extract and run `CMG-SeqViewer.exe`

**macOS**
1. Go to [Releases](https://github.com/ibs-CMG-NGS/cmg-seqviewer/releases)
2. Download `CMG-SeqViewer-macOS.dmg`
3. Open DMG and drag app to Applications

### Option 2: Run from Source

#### Prerequisites
- Python 3.9 or higher
- Windows 10/11 or macOS 13.0+

#### Windows

```powershell
git clone https://github.com/ibs-CMG-NGS/cmg-seqviewer.git
cd cmg-seqviewer

python -m venv venv
venv\Scripts\activate

pip install -r requirements.txt

python src\main.py
```

#### macOS / Linux

```bash
git clone https://github.com/ibs-CMG-NGS/cmg-seqviewer.git
cd cmg-seqviewer

python3 -m venv venv
source venv/bin/activate

pip install -r requirements.txt

python src/main.py
```

---

## Quick Start

### 1. Loading Data

**RNA-seq Differential Expression**
```
File -> Open Dataset  (Ctrl+O)
```
Supports Excel (.xlsx, .xls), CSV, TSV, parquet.
Requires: gene_id, log2fc, adj_pvalue columns (auto-detects variants).

**ATAC-seq Differential Accessibility**
```
File -> Open ATAC-seq Dataset...
```
Supports Excel / Parquet. Auto-detected from `peak_id` column.
Requires: peak_id, log2fc, adj_pvalue (HOMER-annotated DESeq2 output).

**GO/KEGG Analysis Data**
```
File -> Open GO/KEGG Dataset
```
Requires: term_id, description, fdr, gene_count columns.
Supports multiple ontologies (BP, MF, CC, KEGG).

**Drag & Drop**
Drop a file anywhere on the window for automatic type detection.

### 2. Filtering

**Statistical Filter (DE / ATAC-seq data)**
```
Left Panel -> Statistical tab
  Adj. p-value <= 0.05
  |log2FC|     >= 1.0
  Regulation:  Both / Up / Down
```

**ATAC-seq Filters** (visible only when ATAC-seq tab is active)
```
Left Panel -> Statistical tab -> ATAC-seq Filtering
  Annot:   All / Intergenic / Intron / Promoter-TSS / ...
  |TSS| <= 2000 bp
  Peak Width: 200 – 2000 bp
```

**Statistical Filter (GO/KEGG data)**
```
Left Panel -> Statistical tab
  FDR   <= 0.05
  FE    >= 0  (Fold Enrichment minimum)
  Ontology:  All / BP / MF / CC / KEGG
  Gene Set:  All / UP / DOWN / TOTAL
```

**Gene List Filter**
```
Left Panel -> Gene List tab
  Paste gene IDs / symbols, one per line (Ctrl+V from Excel supported)
  Or load from .txt / .csv file
  Click "Apply Filter"
```

- DE data: exact match on gene ID or symbol
- ATAC-seq data: exact match on `nearest_gene` (gene symbol)
- GO/KEGG data: returns GO terms containing any of the listed genes in `gene_symbols`; sorted by overlap count

**Advanced GO Filter**
```
Statistical tab -> Advanced Filtering...
```
Additional controls: gene count range, description keyword search, case-sensitive toggle.

### 3. GO Term Clustering

```
1. Load GO/KEGG dataset
2. Filter to significant terms (e.g. FDR < 1e-5, BP ontology)
3. Select the filtered tab
4. Analysis -> Cluster GO Terms
5. Configure:
     Similarity:  Jaccard (default) or Kappa
     Threshold:   0.3 (higher = stricter)
     Clustering:  average (default)
6. View interactive network
7. Click "Apply" to create a "Clustered:" tab
```

### 4. GO Term Comparison

```
1. Load ≥2 GO/KEGG datasets (e.g. Ctrl_GO, KO_GO, OE_GO)
2. Enter GO term IDs in Filter Panel -> Gene List (one per line):
     GO:0006915
     GO:0007049
3. Open Comparison Panel (left panel)
4. Select the GO datasets to compare
5. Set Comparison Type: "GO Term Comparison"
6. Click "Apply"
   -> New tab: "Comparison: GO Terms"
7. Visualization -> GO/KEGG Dot Plot  (opens comparison dot plot)
```

### 5. ATAC-seq Visualizations

```
Visualization -> Genomic Distribution (ATAC)   Pie chart of annotation categories
Visualization -> TSS Distance Plot (ATAC)      Distance-to-TSS histogram
Visualization -> MA Plot (ATAC)                log2(base mean) vs log2FC
```

### 6. RNA-seq / GO Visualizations

```
Visualization -> Volcano Plot          (Ctrl+V)   DE / ATAC data
Visualization -> GO/KEGG Dot Plot                 GO data / Comparison: GO Terms tab
Visualization -> GO/KEGG Network Chart            Clustered GO data
Visualization -> Heatmap                          DE data
```

### 6. Export

```
File -> Export Current Tab  (Ctrl+E)
  Excel (.xlsx), CSV (.csv), TSV (.tsv)
```

---

## Data Format Requirements

### Differential Expression Data (RNA-seq)

Required columns (case-insensitive, many variants supported):

| Column | Accepted names |
|--------|----------------|
| Gene ID | `gene_id`, `GeneID`, `symbol`, `Gene` |
| Log2 Fold Change | `log2FC`, `log2fc`, `logFC`, `log2FoldChange` |
| Adjusted P-value | `padj`, `adj_pvalue`, `FDR`, `adj.pvalue`, `Adjusted.P-value` |

Optional: `pvalue`, `baseMean`, `lfcSE`

Example:

| gene_id | log2fc | pvalue | padj | baseMean |
|---------|--------|--------|------|----------|
| BRCA1 | 2.54 | 0.0001 | 0.0023 | 1234.5 |
| TP53 | -1.87 | 0.0002 | 0.0045 | 987.3 |

### Differential Accessibility Data (ATAC-seq)

Auto-detected from `peak_id` column. Typical DESeq2 + HOMER output (14 columns):

| Column | Accepted names | Notes |
|--------|----------------|-------|
| `peak_id` | `peak_id`, `peakid`, `peak_name`, `interval` | **Required** — triggers ATAC detection |
| `chromosome` | `chr`, `chromosome`, `seqnames` | |
| `peak_start` / `peak_end` | `start` / `end` | Used to compute `peak_width` |
| `nearest_gene` | `gene_name`, `nearest_gene`, `symbol` | Gene symbol of nearest TSS |
| `annotation` | `annotation`, `peak_annotation` | HOMER format, e.g. `intron (ENSMUSG..., intron 2 of 4)` |
| `distance_to_tss` | `distancetotss`, `distance_to_tss` | Signed bp distance |
| `base_mean` | `baseMean`, `base_mean` | |
| `log2fc` | `log2FoldChange`, `log2fc` | **Required** |
| `adj_pvalue` | `padj`, `adj_pvalue`, `FDR` | **Required** |

Example:

| peak_id | chr | start | end | gene_name | annotation | log2FoldChange | padj |
|---------|-----|-------|-----|-----------|------------|---------------|------|
| peak_1 | chr1 | 1000 | 1500 | Actb | Promoter-TSS (Actb) | 1.23 | 0.001 |
| peak_2 | chr3 | 5000 | 5400 | Gata1 | intron (ENSMUSG..., intron 1 of 3) | -0.87 | 0.032 |

### GO/KEGG Analysis Data

Required columns:

| Column | Accepted names |
|--------|----------------|
| Term ID | `term_id`, `GO.ID`, `KEGG.ID`, `ID` |
| Description | `description`, `GO.Term`, `KEGG.Pathway` |
| Gene Count | `gene_count`, `Gene.Count`, `Count` |
| FDR | `fdr`, `Adjusted.P-value`, `padj` |

Recommended for full functionality:

| Column | Notes |
|--------|-------|
| `gene_symbols` / `Gene.Symbols` | Slash- or comma-separated gene list per term |
| `gene_set` / `Gene.Set` | UP / DOWN / TOTAL |
| `ontology` | BP / MF / CC / KEGG |
| `gene_ratio` / `Gene.Ratio` | e.g. "10/100" |
| `fold_enrichment` | Numeric |

Example:

| term_id | description | gene_count | fdr | gene_symbols | gene_set | ontology |
|---------|-------------|------------|-----|--------------|----------|----------|
| GO:0006955 | immune response | 25 | 1.2e-6 | BRCA1/TP53/MYC | UP | BP |
| GO:0008283 | cell proliferation | 18 | 3.4e-5 | TP53/EGFR | DOWN | BP |

---

## Project Structure

```
cmg-seqviewer/
|-- src/
|   |-- main.py                      # Application entry point
|   |-- core/
|   |   |-- fsm.py                   # Finite State Machine (12 states)
|   |   +-- logger.py                # Logging system
|   |-- models/
|   |   |-- data_models.py           # Dataset, DatasetType (DE / ATAC / GO) classes
|   |   +-- standard_columns.py      # Column name standardization (RNA-seq + ATAC-seq)
|   |-- gui/
|   |   |-- main_window.py                   # Main window
|   |   |-- filter_panel.py                  # Filter controls (DE + ATAC + GO)
|   |   |-- comparison_panel.py              # Dataset/GO comparison panel
|   |   |-- dataset_manager.py               # Dataset switching/renaming
|   |   |-- go_clustering_dialog.py          # GO clustering UI
|   |   |-- go_dot_plot_dialog.py            # GO dot plot
|   |   |-- go_comparison_dot_plot_dialog.py # GO Term Comparison dot plot
|   |   |-- go_bar_chart_dialog.py           # GO bar chart
|   |   |-- go_network_dialog.py             # GO network chart
|   |   |-- go_filter_dialog.py              # Advanced GO filter
|   |   |-- visualization_dialog.py          # Volcano, Heatmap, P-adj plots
|   |   |-- ma_plot_dialog.py                # MA Plot (ATAC-seq / RNA-seq)
|   |   |-- genomic_distribution_dialog.py   # ATAC-seq annotation pie chart
|   |   |-- tss_distance_dialog.py           # ATAC-seq TSS distance histogram
|   |   |-- help_dialog.py                   # F1 help system
|   |   +-- workers.py                       # Async QThread workers
|   |-- presenters/
|   |   +-- main_presenter.py        # Business logic (MVP pattern)
|   +-- utils/
|       |-- data_loader.py           # Excel/CSV/parquet loading + type detection
|       |-- atac_seq_loader.py       # ATAC-seq DA loader (HOMER-annotated DESeq2)
|       |-- go_kegg_loader.py        # GO/KEGG specific loader
|       |-- go_clustering.py         # Clustering algorithms
|       |-- statistics.py            # Fisher's test, GSEA
|       +-- database_manager.py      # SQLite session storage
|-- database/                        # Pre-loaded datasets (SQLite)
|-- logs/                            # Application and audit logs
|-- test/                            # Unit tests
|-- docs/                            # Documentation
|-- .github/workflows/build.yml      # CI/CD: Windows + macOS builds
|-- requirements.txt                 # Production dependencies
|-- requirements-dev.txt             # Development dependencies
|-- setup.py
+-- README.md
```

---

## Architecture

```
Main Window (View)
      |
      | user actions
      v
Main Presenter (Controller)
  - coordinates business logic
  - manages FSM state transitions
  - delegates to async workers
      |
      v
FSM (Finite State Machine)
  IDLE -> LOADING_DATA -> DATA_LOADED -> FILTERING -> FILTER_COMPLETE -> ...
      |
      +-- Workers (async QThread)
      +-- Models  (Dataset, DatasetType)
      +-- Utils   (statistics, clustering)
      +-- DB      (SQLite session storage)
```

Design patterns: MVP, FSM, Observer, async worker pool.

[Full FSM Diagram](docs/FSM_DIAGRAM.md)

---

## Testing

```powershell
# Run all tests
pytest test/

# With coverage
pytest --cov=src test/

# Specific file
pytest test/test_data_loader.py -v
```

---

## Roadmap

### v1.2 (Q2 2026) — released
- [x] ATAC-seq DA support (load, filter, visualize)
- [x] MA Plot dialog
- [x] Genomic Distribution + TSS Distance Plot
- [x] Column Display Level unified to Basic / Stat / Full

### v1.3 (Q3 2026)
- [ ] Dataset Tree Panel: tree-based dataset/sheet navigation
- [ ] Session save/load functionality
- [ ] Batch export (multiple visualizations at once)
- [ ] GO enrichment analysis (run enrichment from within app)

### v2.0 (Future)
- [ ] KEGG pathway diagram overlay
- [ ] RNA-Seq count data analysis (DESeq2/edgeR integration)
- [ ] Single-cell RNA-Seq support
- [ ] Web version

---

## Known Issues

1. **Network Chart Performance**: Degrades with > 200 terms. Workaround: cluster first, then visualize.
2. **macOS Icon**: Requires manual `.icns` creation during build. Automated in CI workflow.
3. **Matplotlib Warnings**: Minor Qt5->Qt6 transition warnings -- cosmetic only.

[Report a Bug](https://github.com/ibs-CMG-NGS/cmg-seqviewer/issues)

---

## License

MIT License -- see [LICENSE](LICENSE).

---

## Acknowledgments

- **PyQt6** -- GUI framework
- **pandas / NumPy / SciPy** -- data processing and statistics
- **Matplotlib / Seaborn** -- visualization
- **NetworkX** -- GO term network analysis
- **openpyxl / pyarrow** -- Excel and parquet file support
- **ClueGO**, **EnhancedVolcano**, **clusterProfiler** -- conceptual inspiration

---

## Citation

```bibtex
@software{cmg_seqviewer,
  author  = {CMG-SeqViewer Contributors},
  title   = {CMG-SeqViewer: RNA-Seq Data Analysis and Visualization Tool},
  year    = {2026},
  url     = {https://github.com/ibs-CMG-NGS/cmg-seqviewer},
  version = {1.1.6}
}
```

---

## Quick Links

| Resource | Link |
|----------|------|
| Releases | [Download Latest](https://github.com/ibs-CMG-NGS/cmg-seqviewer/releases) |
| Documentation | [docs/](docs/) |
| Recent Updates | [RECENT_UPDATES.md](docs/RECENT_UPDATES.md) |
| Issue Tracker | [Issues](https://github.com/ibs-CMG-NGS/cmg-seqviewer/issues) |
| Internal Distribution | [INTERNAL_DISTRIBUTION.md](docs/INTERNAL_DISTRIBUTION.md) |
| Database Structure | [database/README.md](database/README.md) |
