# Changelog

All notable changes to CMG-SeqViewer will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added
- External data folder support for post-deployment dataset management
- Gene annotation context menu (right-click on gene symbols/IDs)
  - Links to NCBI Gene, GeneCards, Ensembl, UniProt, Google Scholar
- GO/KEGG term annotation context menu
  - GO terms: QuickGO, AmiGO, Gene Ontology
  - KEGG pathways: KEGG Pathway, Reactome, WikiPathways
- Help documentation section for gene annotation features
- ATAC-seq integration plan document (future v2.0)

### Changed
- Database system now supports multiple data paths (external + legacy)
- Metadata loading requires metadata.json + parquet files together

### Fixed
- Auto-metadata generation bug (1 parquet file creating 6 incorrect datasets)
- File source tracking for multi-path database resolution

---

## [v1.0.12] - 2025-12-XX

### Fixed
- Windows ZIP archive structure for proper extraction

---

## [v1.0.11] - 2026-01-01

### Added
- Unified light theme across all platforms for consistency
- macOS Finder launch support with proper resource path handling
- Log terminal with guaranteed minimum height (200-250px)
- Enhanced error logging for debugging launch issues

### Changed
- **macOS Requirement**: Minimum version updated to macOS 13.0 Ventura (PyQt6 requirement)
- Fusion style applied for cross-platform UI consistency
- Main content area expansion priority improved

### Fixed
- Dark mode readability issues on macOS (black text on dark background)
- Log terminal collapsing issue
- Double-click launch from Finder on macOS
- Resource path handling in frozen executables

---

## [v1.0.10] - 2025-12-31

### Added
- **GO Term Clustering** (ClueGO-style)
  - Interactive clustering dialog with network visualization
  - Jaccard and Kappa similarity methods
  - Hierarchical clustering (average, complete, single, ward)
  - Color-coded clusters with convex hull boundaries
  - Interactive tooltips and zoom/pan support
  - Representative term selection
  - Cluster statistics table
  - Export clustered results with `cluster_id` column
  
- **GO/KEGG Visualizations**
  - Dot Plot (gene ratio vs FDR)
  - Bar Chart (top enriched terms)
  - Network Chart (cluster-based, requires clustered data)

- **Gene Set Column** for GO data
  - Indicates which DEG group (UP/DOWN/TOTAL) was used for analysis
  - Distinct from DE regulation direction

### Changed
- Filter Panel: "Regulation" label for DE data, "Gene Set" label for GO data
- Menu structure: Flattened GO/KEGG items with 🧬 emoji icons
- Help Dialog: Added comprehensive GO/KEGG Analysis section (Section 4)
- Column Name Support: More flexible variant detection

### Fixed
- Volcano Plot autoscale: Column name mismatch (`log2FC` vs `log2fc`)
- Re-filtering: Support for filtering already-filtered tabs
- Debug log cleanup: Removed unnecessary print statements
- Encoding issues: Resolved corrupted characters and emoji in documentation

---

## [v1.0.9] - 2025-12-10

### Added
- Multi-dataset comparison feature
  - Venn Diagram for 2-3 datasets
  - Gene list comparison mode
  - Statistics comparison mode
  - Intersection/Union options
  - Comparison results export to Excel

### Changed
- Comparison Panel added to left sidebar
- Dataset selection with "Select All" / "Clear Selection" helpers

---

## [v1.0.8] - 2025-12-09

### Added
- Heatmap visualization with hierarchical clustering
  - Z-score, Min-Max, Log2 normalization options
  - Gene sorting by padj, log2FC, or clustering
  - Multiple colormap options (RdBu_r, viridis, plasma, etc.)
  - Transpose option (swap genes and samples)
  - Customizable colorbar range

### Changed
- Visualization menu reorganized
- Improved tooltip positioning (always visible)

---

## [v1.0.7] - 2025-12-08

### Added
- Dot Plot visualization for dataset comparison
  - Dot size represents significance (padj)
  - Dot color represents fold change (log2FC)
  - Gene clustering option
  - Transpose support

### Fixed
- Plot settings persistence across sessions
- Tooltip auto-positioning to prevent cutoff

---

## [v1.0.6] - 2025-12-07

### Added
- Dataset rename functionality
  - Updates all references (tabs, comparison lists, internal structures)
  - Accessible via Dataset Manager "Rename" button

- Recent Files menu
  - Quick access to last 10 loaded files
  - Path preview (2-3 levels for clarity)
  - Auto-cleanup of non-existent files

### Changed
- Dataset Manager UI improvements
- Menu bar reorganization

---

## [v1.0.5] - 2025-12-06

### Added
- Drag & Drop support for Excel files
- Window-specific icons for taskbar identification
  - Main window: DNA helix icon
  - Volcano plot: Volcano icon
  - Heatmap: Heat icon
  - Database browser: Database icon

### Changed
- Improved cell selection (individual cells, not just rows)
- Selection color: Light blue (#ADD8E6) for better visibility

---

## [v1.0.4] - 2025-12-05

### Added
- Clipboard operations (Ctrl+C / Ctrl+V)
  - Copy selected cells in tab-delimited format
  - Paste gene lists into Filter Panel
  - Excel-compatible formatting

### Fixed
- Column width persistence
- Table sorting stability

---

## [v1.0.3] - 2025-12-04

### Added
- Column display levels (Basic, DE Analysis, Full)
- Decimal precision setting (1-6 decimal places)
- Export to multiple formats (Excel, CSV, TSV)

### Changed
- Filter Panel layout improvements
- Status bar information display

---

## [v1.0.2] - 2025-12-03

### Added
- P-adj Histogram visualization
- Volcano Plot customization
  - Adjustable thresholds, colors, sizes
  - Custom axis labels and title
  - Figure size control

### Fixed
- Tooltip positioning in plots
- Matplotlib toolbar integration

---

## [v1.0.1] - 2025-12-02

### Added
- Database management system
  - Pre-loaded dataset storage
  - Database browser dialog
  - Import/export datasets
  - Metadata management

### Changed
- FSM (Finite State Machine) for application states
- Improved error handling

---

## [v1.0.0] - 2025-12-01

### Added
- Initial release
- RNA-Seq differential expression data loading
- GO/KEGG enrichment data loading
- Basic filtering (gene list, statistical thresholds)
- Volcano plot visualization
- Multi-dataset management
- Excel-like table interface
- Cross-platform support (Windows, macOS)

---

## Migration Notes

### v1.0.11 → v1.0.12+
- No breaking changes
- Database format backward compatible

### v1.0.10 → v1.0.11
- macOS users: Requires macOS 13.0+ (Ventura or later)
- Older macOS versions: Build from source with PyQt5

### v1.0.9 → v1.0.10
- GO/KEGG data: New `gene_set` column added (auto-detected from existing data)
- Database files remain compatible

---

## Links
- [Repository](https://github.com/ibs-CMG-NGS/cmg-seqviewer)
- [Issues](https://github.com/ibs-CMG-NGS/cmg-seqviewer/issues)
- [Releases](https://github.com/ibs-CMG-NGS/cmg-seqviewer/releases)
