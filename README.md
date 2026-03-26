# CMG-SeqViewer - RNA-Seq Data Analysis & Visualization

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![PyQt6](https://img.shields.io/badge/PyQt-6-green.svg)](https://www.riverbankcomputing.com/software/pyqt/)

## ?�� System Requirements

### Windows
- **OS**: Windows 10 (64-bit) or later
- **Architecture**: x64
- **Memory**: 4GB RAM minimum, 8GB recommended
- **Display**: 1280x720 minimum resolution

### macOS
- **OS**: macOS 13.0 Ventura or later
- **Architecture**: Intel (x86_64) or Apple Silicon (via Rosetta 2)
- **Memory**: 4GB RAM minimum, 8GB recommended
- **Display**: 1280x720 minimum resolution
- **Note**: PyQt6 requires macOS 13.0+. For older macOS versions, please build from source with PyQt5.

---

## �?Overview

**CMG-SeqViewer** is a comprehensive desktop application for RNA-Seq differential expression analysis and GO/KEGG pathway enrichment visualization. Built with Python and PyQt6, it provides an Excel-like interface for biologists to analyze genomic data without programming.

### ??Latest Update: v1.1.4 (Mar 2026)

- ?�� **GO Term Search by Gene Symbol**: Gene List tab now filters GO terms containing any of the input genes in their `gene_symbols` column ??results sorted by hit count
- ?�� **GO Dot Plot**: Added Dot Size selector (Gene Count / Gene Ratio / Fold Enrichment) with smart legend bins
- ?�� **Dot-separator Column Mapping**: Parquet files with `Gene.Set`, `GO.ID`, `Adjusted.P-value` etc. now correctly mapped
- ?���?**gene_set Column Position**: Moved to second position in GO table (after ontology) for quicker scan
- �?**Dot Occlusion Fix**: GO Dot Plot edge dots no longer clipped
- ?�� **Leftover Column Cleanup**: `KEGG.ID` / `KEGG.Pathway` residual columns removed from table view

[?�� Full Release Notes](docs/RECENT_UPDATES.md)

---

## ?�� Key Features

### Data Management
- **Multi-dataset Support**: Load and manage multiple RNA-Seq datasets simultaneously
- **Dual Data Types**: 
  - Differential Expression (DE) analysis results
  - GO/KEGG enrichment analysis results
- **Smart Column Mapping**: Automatic detection of 30+ column name variants
- **Drag & Drop**: Drop Excel files directly onto the application
- **Recent Files**: Quick access to last 10 loaded datasets
- **Dataset Renaming**: Change names anytime - updates everywhere automatically

### GO/KEGG Analysis ?��
- **Clustering Methods**:
  - Jaccard Similarity (gene overlap-based)
  - Kappa Statistic (statistical correlation)
  - Hierarchical clustering (average, complete, single, ward linkage)
- **Interactive Network Visualization**:
  - Color-coded clusters with automatic palette
  - Convex hulls around cluster boundaries
  - Real-time hover tooltips
  - Pan, zoom, and matplotlib toolbar
  - Configurable node size, edge transparency, label size
- **Cluster Management**:
  - Min/Max cluster size filters
  - Singleton handling
  - Representative term selection per cluster
  - Export with `cluster_id` column
- **Visualizations**:
  - Dot Plot: Gene ratio vs FDR scatter
  - Bar Chart: Top enriched terms
  - Network Chart: Cluster-based network (requires clustered data)

### Statistical Analysis
- **Filtering**: Advanced filters by adj.p-value, log2FC, and regulation direction
- **Fisher's Exact Test**: Gene list enrichment analysis
- **GSEA Lite**: Gene set enrichment with directionality
- **Multi-dataset Comparison**: 
  - Compare 2-5 datasets
  - Gene list or statistics mode
  - Intersection/Union options
  - Venn diagrams (2-3 datasets)

### Visualizations
- **Volcano Plot**: log2FC vs -log10(padj) with auto-scale and tooltips
- **Heatmap**: Expression patterns with hierarchical clustering
- **Dot Plot**: Comparison results with gene clustering
- **P-adj Histogram**: Distribution of significance values
- **Venn Diagram**: Dataset overlap visualization

### User Interface
- **Excel-like Tabbed Interface**: Familiar navigation
- **Filter Panel**: Left sidebar for controls and gene input
- **Dataset Manager**: Quick dataset switching and renaming
- **Log Terminal**: Real-time activity tracking
- **Child Windows**: Separate plot windows with full matplotlib tools
- **Smart Tooltips**: Auto-positioning tooltips that never get cut off

### Advanced Architecture
- **FSM (Finite State Machine)**: Robust state management (12 states, 18 events)
- **MVP Pattern**: Clean separation of GUI and business logic
- **Async Processing**: QThread-based workers prevent UI freezing
- **Comprehensive Logging**: Application and audit logs
- **Export Functionality**: Excel, CSV, TSV with one click

## ?���?Architecture

### Design Patterns
- **MVP (Model-View-Presenter)**: Separation of concerns
- **FSM (Finite State Machine)**: State management
- **Observer Pattern**: Event-driven updates

### Project Structure
```
rna-seq-data-view/
?��??� src/
??  ?��??� main.py                 # Entry point
??  ?��??� core/
??  ??  ?��??� fsm.py             # Finite State Machine
??  ??  ?��??� logger.py          # Logging system
??  ?��??� models/
??  ??  ?��??� data_models.py     # Data structures
??  ?��??� gui/
??  ??  ?��??� main_window.py     # Main GUI
??  ??  ?��??� filter_panel.py    # Filter controls
??  ??  ?��??� dataset_manager.py # Dataset management
??  ??  ?��??� workers.py         # Async workers
??  ?��??� presenters/
??  ??  ?��??� main_presenter.py  # Business logic coordinator
??  ?��??� utils/
??      ?��??� data_loader.py     # Data loading utilities
??      ?��??� statistics.py      # Statistical analysis
?��??� logs/                       # Log files
?��??� test/                       # Unit tests
?��??� requirements.txt
?��??� setup.py
?��??� README.md
```

---

## ?�� Installation

> **?�� Note on Pre-loaded Datasets**: This public repository does NOT include internal research datasets. The application works perfectly by loading your own Excel files. For internal distribution with pre-loaded data, see [Internal Distribution Guide](docs/INTERNAL_DISTRIBUTION.md).

### Option 1: Download Pre-built Executable (Recommended for Users)

**Windows:**
1. Go to [Releases](https://github.com/ibs-CMG-NGS/cmg-seqviewer/releases)
2. Download `CMG-SeqViewer-Windows.zip`
3. Extract and run `CMG-SeqViewer.exe`

**macOS:**
1. Go to [Releases](https://github.com/ibs-CMG-NGS/cmg-seqviewer/releases)
2. Download `CMG-SeqViewer-macOS.dmg`
3. Open DMG and drag app to Applications

**?�� For Internal Users**: Contact your organization administrator for the internal build with pre-loaded datasets.

### Option 2: Run from Source (For Developers)

#### Prerequisites
- Python 3.9 or higher
- Windows 10/11, macOS 13.0+, or Linux with Qt support

#### Quick Start

```powershell
# Windows
git clone https://github.com/ibs-CMG-NGS/cmg-seqviewer.git
cd cmg-seqviewer

# Create and activate virtual environment
python -m venv venv
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run application
python src\main.py
# OR use the dev script
.\run_dev.ps1
```

```bash
# macOS/Linux
git clone https://github.com/ibs-CMG-NGS/cmg-seqviewer.git
cd cmg-seqviewer

python3 -m venv venv
source venv/bin/activate

pip install -r requirements.txt

python src/main.py
```

**Detailed Guides:**
- [?�� Quick Start Guide](docs/QUICK_START.md)
- [?���?Development Setup](docs/DEVELOPMENT.md)

---

## ?? Quick Start

### 1. Loading Data

**Differential Expression Data:**
```
File ??Open Dataset (Ctrl+O)
```
- Supports Excel (.xlsx, .xls)
- Requires: gene_id, log2fc, adj_pvalue columns
- Auto-detects column name variants

**GO/KEGG Analysis Data:**
```
File ??Open GO/KEGG Dataset
```
- Requires: term_id, description, fdr, gene_count columns
- Supports multiple ontologies (BP, MF, CC, KEGG)

**Drag & Drop:**
- Drop Excel file anywhere on window
- Automatic type detection

### 2. Filtering Data

**Statistical Filters:**
```
Left Panel ??Statistical Filter
- Adj. p-value: 0.05 (default)
- |log?�FC|: 1.0 (default)
- Regulation: Up/Down/Both
```

**Gene List Filter:**
```
Left Panel ??Gene List
- Paste gene IDs (one per line)
- Or load from text file
- Click "Apply Filter"
```

> **DE data**: filters rows where gene ID/symbol exactly matches the list.  
> **GO/KEGG data**: filters GO terms whose `gene_symbols` column contains **any** of the listed genes ??sorted by number of matching genes (most relevant terms first).

**Re-filtering:**
- Select a "Filtered:" tab
- Apply new filters on filtered results
- Creates "Filtered:Filtered:" tab

### 3. GO Term Clustering ?��

```
1. Load GO/KEGG dataset
2. Filter to significant terms (e.g., FDR < 1e-5, BP ontology)
3. Select filtered tab
4. Analysis ??Cluster GO Terms
5. Configure clustering:
   - Similarity method: Jaccard (default)
   - Threshold: 0.3 (higher = stricter)
   - Clustering method: average (default)
6. View interactive network
7. Click "Apply" to create Clustered: tab
```

### 4. Visualizations

**Volcano Plot (DE data):**
```
Visualization ??Volcano Plot (Ctrl+V)
- Hover for gene info
- Customize colors, sizes, axes
- Auto-scale buttons
```

**GO Dot Plot (GO data):**
```
Visualization ??GO/KEGG Dot Plot
- Dot size: gene ratio/count
- Dot color: FDR/p-value
- Top N terms
```

**Network Chart (Clustered GO data):**
```
Visualization ??GO/KEGG Network Chart
- Requires "Clustered:" tab
- Cluster-based network
- Color-coded by cluster
```

### 5. Export Results

```
File ??Export Current Tab (Ctrl+E)
- Excel (.xlsx)
- CSV (.csv)
- TSV (.tsv)
```

---

## ?�� Data Format Requirements

### Differential Expression Data

**Required columns** (case-insensitive, multiple variants supported):
- **Gene ID**: `gene_id`, `GeneID`, `ID`, `symbol`, `Gene`
- **Log2 Fold Change**: `log2FC`, `log2fc`, `logFC`, `log2FoldChange`
- **Adjusted P-value**: `padj`, `adj_pvalue`, `FDR`, `adj.pvalue`, `qvalue`

**Optional but recommended**:
- `pvalue`: Raw p-value
- `baseMean`: Mean expression level
- `lfcSE`: Log fold change standard error

**Example:**
| gene_id | log2fc | pvalue | padj | baseMean |
|---------|--------|--------|------|----------|
| BRCA1 | 2.54 | 0.0001 | 0.0023 | 1234.5 |
| TP53 | -1.87 | 0.0002 | 0.0045 | 987.3 |

### GO/KEGG Analysis Data

**Required columns**:
- **Term ID**: `term_id`, `ID`, `GO_ID`, `KEGG_ID`
- **Description**: `description`, `Term`, `Description`, `GO Term`
- **Gene Count**: `gene_count`, `Count`, `GeneCount`
- **FDR**: `fdr`, `adj_pvalue`, `padj`, `FDR`

**Highly recommended for clustering**:
- **Gene Symbols**: `geneID`, `Genes`, `genes` (slash-separated: `BRCA1/TP53/MYC`)
- **Gene Set**: `gene_set`, `direction` (UP/DOWN/TOTAL)
- **Ontology**: `ontology`, `Ont` (BP/MF/CC/KEGG)

**Optional**:
- `pvalue`: Raw p-value
- `qvalue`: Q-value
- `gene_ratio`: Gene ratio (e.g., "10/100")
- `bg_ratio`: Background ratio
- `fold_enrichment`: Fold enrichment

**Example:**
| term_id | description | gene_count | fdr | geneID | gene_set | ontology |
|---------|-------------|------------|-----|--------|----------|----------|
| GO:0006955 | immune response | 25 | 1.2e-6 | BRCA1/TP53/MYC | UP | BP |
| GO:0008283 | cell proliferation | 18 | 3.4e-5 | TP53/EGFR | DOWN | BP |

---

## ?���?Project Structure

```
rna-seq-data-view/
?��??� src/
??  ?��??� main.py                      # Application entry point
??  ?��??� core/
??  ??  ?��??� fsm.py                   # Finite State Machine (12 states)
??  ??  ?��??� logger.py                # Logging system
??  ?��??� models/
??  ??  ?��??� data_models.py           # Dataset, DatasetType classes
??  ??  ?��??� standard_columns.py      # Column name standardization
??  ?��??� gui/
??  ??  ?��??� main_window.py           # Main window (2800+ lines)
??  ??  ?��??� filter_panel.py          # Filter controls
??  ??  ?��??� dataset_manager.py       # Dataset switching/renaming
??  ??  ?��??� go_clustering_dialog.py  # GO clustering UI (1300+ lines)
??  ??  ?��??� go_dot_plot_dialog.py    # GO dot plot
??  ??  ?��??� go_bar_chart_dialog.py   # GO bar chart
??  ??  ?��??� go_network_dialog.py     # GO network chart
??  ??  ?��??� visualization_dialog.py  # Volcano, Heatmap, P-adj plots
??  ??  ?��??� help_dialog.py           # F1 help system
??  ??  ?��??� workers.py               # Async QThread workers
??  ?��??� presenters/
??  ??  ?��??� main_presenter.py        # Business logic (MVP pattern)
??  ?��??� utils/
??  ??  ?��??� data_loader.py           # Excel/CSV loading
??  ??  ?��??� go_kegg_loader.py        # GO/KEGG specific loader
??  ??  ?��??� go_clustering.py         # Clustering algorithms
??  ??  ?��??� statistics.py            # Fisher's test, GSEA
??  ??  ?��??� database_manager.py      # SQLite session storage
??  ?��??� workers/
??      ?��??� load_worker.py           # Async data loading
??      ?��??� filter_worker.py         # Async filtering
??      ?��??� go_workers.py            # GO clustering worker
??      ?��??� comparison_worker.py     # Dataset comparison
?��??� database/                         # Pre-loaded datasets (SQLite)
?��??� logs/                            # Application and audit logs
?��??� test/                            # Unit tests
?��??� docs/
??  ?��??� RECENT_UPDATES.md            # Latest feature updates
??  ?��??� GITHUB_SETUP.md              # GitHub & CI/CD guide
??  ?��??� QUICK_START.md               # User quick start
??  ?��??� DEVELOPMENT.md               # Developer setup
??  ?��??� DATABASE_GUIDE.md            # Database schema
?��??� .github/
??  ?��??� workflows/
??      ?��??� build.yml                # CI/CD: Windows + macOS builds
?��??� requirements.txt                 # Production dependencies
?��??� requirements-dev.txt             # Development dependencies
?��??� setup.py                         # Package configuration
?��??� rna-seq-viewer.spec              # PyInstaller spec (Windows)
?��??� cmg-seqviewer-macos.spec         # PyInstaller spec (macOS)
?��??� create_icon.py                   # App icon generator
?��??� README.md                        # This file
```

---

## ?�� Configuration & Settings

### Application Settings
Settings are automatically saved and restored:
- Filter thresholds (p-value, log2FC)
- Visualization preferences (colors, sizes)
- Window positions and sizes
- Column display levels
- Decimal precision

### Environment Variables
Create `.env` file (copy from `.env.example`):
```bash
# Database
DATABASE_PATH=database/rna_seq_data.db

# Logging
LOG_LEVEL=INFO
LOG_DIR=logs

# UI
DEFAULT_PADJ_THRESHOLD=0.05
DEFAULT_LOG2FC_THRESHOLD=1.0
```

---

## ?�� Logging

### Application Log
**Location**: `logs/rna_seq_YYYYMMDD_HHMMSS.log`
- Detailed technical logging
- DEBUG, INFO, WARNING, ERROR levels
- Stack traces for exceptions
- Performance metrics

### Audit Log
**Location**: `logs/audit_YYYYMMDD.log`
- User action tracking
- Dataset load/filter/export events
- Analysis execution timestamps
- Session lifecycle

Both logs are displayed in real-time in the terminal panel (bottom of main window).

---

## ?�� Testing

```powershell
# Run all tests
pytest test/

# Run with coverage
pytest --cov=src test/

# Run specific test file
pytest test/test_data_loader.py

# Verbose output
pytest -v test/
```

### Test Structure
```
test/
?��??� test_data_loader.py       # Data loading tests
?��??� test_statistics.py         # Statistical analysis tests
?��??� test_go_clustering.py      # GO clustering tests
?��??� test_fsm.py               # State machine tests
```

---

## ?���?Development

### Architecture Overview

```
?��??�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�??
??                    Main Window (View)                  ??
?? ?��??�?�?�?�?�?�?�?�?�?�?�?�?�?? ?��??�?�?�?�?�?�?�?�?�?�?�?�?�?? ?��??�?�?�?�?�?�?�?�?�?�?�?�?�????
?? ??Filter Panel ?? ?? Data Tabs   ?? ?? Log Panel   ????
?? ?��??�?�?�?�?�?�?�?�?�?�?�?�?�?? ?��??�?�?�?�?�?�?�?�?�?�?�?�?�?? ?��??�?�?�?�?�?�?�?�?�?�?�?�?�????
?��??�?�?�?�?�?�?�?�?�?�?�?��??�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�??
             ??User Actions
             ??
?��??�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�??
??             Main Presenter (Controller)                ??
?? ??Coordinates business logic                           ??
?? ??Manages FSM state transitions                        ??
?? ??Delegates to workers                                 ??
?��??�?�?�?�?�?�?�?�?�?�?�?��??�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�??
             ??Events & Data
             ??
?��??�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�??
??               FSM (Finite State Machine)               ??
?? States: IDLE ??LOADING ??LOADED ??FILTERING ??...     ??
?? Events: LOAD_DATA, FILTER_DATA, START_ANALYSIS, ...   ??
?��??�?�?�?�?�?�?�?�?�?�?�?��??�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�??
             ??
    ?��??�?�?�?�?�?�?�?��??�?�?�?�?�?�?�?��??�?�?�?�?�?�?�?�?�?�?�?�?�?��??�?�?�?�?�?�?�?�?�?�?�?�?�??
    ??                ??             ??             ??
?��??�?�?�?�?�?�?�?�??   ?��??�?�?�?�?�?�?�?�?�?�?�?�???��??�?�?�?�?�?�?�?�?�?�?�?�???��??�?�?�?�?�?�?�?�??
??Workers ??   ??  Models    ????   Utils    ????  DB    ??
??Async)  ??   ??(Dataset)   ????Statistics) ????SQLite) ??
?��??�?�?�?�?�?�?�?�??   ?��??�?�?�?�?�?�?�?�?�?�?�?�???��??�?�?�?�?�?�?�?�?�?�?�?�???��??�?�?�?�?�?�?�?�??
```

### FSM State Diagram

```
IDLE ?�?�LOAD_DATA?�?�> LOADING_DATA ?�?�DATA_LOAD_SUCCESS?�?�> DATA_LOADED
                         ??                                   ??
                         ??                                   ??
                    ERROR_OCCURRED <?�?�?�?�?�?�?�?� FILTER_DATA ?�?�> FILTERING
                         ??                                   ??
                         ?��??�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?� FILTER_COMPLETE
                                                              ??
                                                              ??
                                                        (Various Analysis States)
```

[?�� Full FSM Documentation](docs/FSM_DIAGRAM.md)

### Adding New Features

#### 1. Add New Analysis Method

```python
# 1. Add to utils/statistics.py
def new_analysis(df, **kwargs):
    # Your analysis logic
    return result

# 2. Add FSM state/event in core/fsm.py
Event.START_NEW_ANALYSIS = "START_NEW_ANALYSIS"
State.NEW_ANALYSIS_RUNNING = "NEW_ANALYSIS_RUNNING"

# 3. Add UI controls in gui/filter_panel.py or new dialog
class NewAnalysisDialog(QDialog):
    # Your UI

# 4. Connect in presenters/main_presenter.py
def start_new_analysis(self):
    self.fsm.trigger(Event.START_NEW_ANALYSIS)
    # Create worker, connect signals
```

#### 2. Add New Visualization

```python
# 1. Create dialog in gui/
class NewPlotDialog(QDialog):
    def __init__(self, dataset, parent=None):
        # Setup matplotlib canvas
        
    def _plot(self):
        # Plotting logic

# 2. Add menu item in gui/main_window.py
visualization_menu.addAction("New Plot", self._on_new_plot)

# 3. Connect handler
def _on_new_plot(self):
    dialog = NewPlotDialog(current_dataset, self)
    dialog.exec()
```

### Code Style
- **PEP 8** compliance
- **Type hints** where appropriate
- **Docstrings** for all public methods
- **Comments** for complex logic

---

## ?�� Known Issues

1. **Network Chart Performance**: Degrades with >200 terms
   - **Workaround**: Use clustering first, then visualize clustered results

2. **macOS Icon**: Requires manual `.icns` creation during GitHub Actions build
   - **Status**: Automated in workflow with `sips` and `iconutil`

3. **Matplotlib Backend Warnings**: Some deprecation warnings from Qt5?�Qt6 transition
   - **Impact**: Cosmetic only, no functionality affected

[?�� Report a Bug](https://github.com/ibs-CMG-NGS/cmg-seqviewer/issues)

---

## 🗺️ Roadmap

### v1.2 (Q2 2026)
- [ ] Dataset Tree Panel: tree-based dataset/sheet navigation replacing the top combo bar
- [ ] GO enrichment analysis (run enrichment from within app)
- [ ] Session save/load functionality
- [ ] Batch export (multiple visualizations at once)

### v1.3 (Q3 2026)
- [ ] KEGG pathway diagram overlay
- [ ] Protein-protein interaction networks
- [ ] Custom color scheme editor
- [ ] Command-line interface for automation

### v2.0 (Future)
- [ ] RNA-Seq count data analysis (DESeq2/edgeR integration)
- [ ] Single-cell RNA-Seq support
- [ ] Web version (Dash/Streamlit)
- [ ] API for programmatic access

---

##  License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

##  Contributors

Contributions are welcome! Please read our Contributing Guidelines first.

##  Acknowledgments

### Core Technologies
- **PyQt6**: Modern GUI framework
- **pandas**: Data manipulation and analysis
- **NumPy**: Numerical computing
- **SciPy**: Statistical analysis (Fisher's test, hierarchical clustering)
- **Matplotlib**: Publication-quality visualizations
- **Seaborn**: Statistical data visualization
- **NetworkX**: Graph/network analysis for GO clustering
- **openpyxl**: Excel file handling

### Inspiration
- **ClueGO** (Cytoscape plugin): GO term clustering visualization approach
- **EnhancedVolcano** (R/Bioconductor): Volcano plot design
- **clusterProfiler** (R/Bioconductor): GO enrichment workflow

##  Support & Contact

### Getting Help
-  [Documentation](docs/)
-  [Issue Tracker](https://github.com/ibs-CMG-NGS/cmg-seqviewer/issues)
-  [Discussions](https://github.com/ibs-CMG-NGS/cmg-seqviewer/discussions)

### Reporting Issues
When reporting bugs, please include:
1. CMG-SeqViewer version (Help  About)
2. Operating system and version
3. Steps to reproduce
4. Expected vs actual behavior
5. Log file excerpt (if applicable)

##  Citation

If you use CMG-SeqViewer in your research, please cite:

```bibtex
@software{cmg_seqviewer,
  author = {CMG-SeqViewer Contributors},
  title = {CMG-SeqViewer: RNA-Seq Data Analysis and Visualization Tool},
  year = {2026},
  url = {https://github.com/ibs-CMG-NGS/cmg-seqviewer},
  version = {1.1.4}
}
```

##  Related Projects

- [DESeq2](https://bioconductor.org/packages/release/bioc/html/DESeq2.html) - Differential expression analysis in R
- [clusterProfiler](https://bioconductor.org/packages/release/bioc/html/clusterProfiler.html) - GO enrichment in R
- [DAVID](https://david.ncifcrf.gov/) - Functional annotation web tool

---

##  Quick Links

| Resource | Link |
|----------|------|
| **Releases** | [Download Latest](https://github.com/ibs-CMG-NGS/cmg-seqviewer/releases) |
| **Documentation** | [docs/](docs/) |
| **Recent Updates** | [RECENT_UPDATES.md](docs/RECENT_UPDATES.md) |
| **GitHub Setup** | [GITHUB_SETUP.md](docs/GITHUB_SETUP.md) |
| **?�� Internal Distribution** | [INTERNAL_DISTRIBUTION.md](docs/INTERNAL_DISTRIBUTION.md) |
| **Database Structure** | [database/README.md](database/README.md) |

---

<div align="center">

**Made with ?�️ for the bioinformatics community**

[ Back to top](#cmg-seqviewer---rna-seq-data-analysis--visualization)

</div>
