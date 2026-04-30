# Recent Updates & New Features

## 2026-04-30: v1.2.0 - ATAC-seq Differential Accessibility Support

### NEW: ATAC-seq DA Data Loading
- **File → Open ATAC-seq Dataset…** — dedicated menu item for ATAC-seq Excel/Parquet files
- Auto-detected from `peak_id` column (HOMER-annotated DESeq2 output format)
- Supports 14 standard columns: `peak_id`, `chromosome`, `peak_start/end`, `nearest_gene`, `gene_id`, `annotation`, `distance_to_tss`, `base_mean`, `log2fc`, `lfcse`, `pvalue`, `adj_pvalue`, `direction`
- `peak_width` automatically computed as `peak_end − peak_start`
- Also loads from Database Browser (Parquet cache)

### NEW: ATAC-seq Filters
Three new controls in the Statistical Filter tab (visible only when ATAC-seq tab is active):
- **Annot:** filter by broad annotation category (Intergenic, Intron, Promoter-TSS, Exon, TTS, …) — populated dynamically from the loaded dataset
- **|TSS| ≤:** keep peaks within N bp of the nearest TSS
- **Peak Width:** minimum and/or maximum peak width in bp

### NEW: Genomic Distribution Plot
- Pie chart of ATAC-seq peak annotation categories
- HOMER annotation strings auto-normalized to broad categories (e.g. `"intron (ENSMUSG..., intron 2 of 4)"` → `"Intron"`)
- Shows peak count and percentage per category; top 9 + Others grouping

### NEW: TSS Distance Plot
- Histogram of distance from each peak center to the nearest TSS
- Default range ±50 kb; user-adjustable range and bin count
- Reference lines at TSS (0 bp), ±2 kb, ±5 kb
- Summary: % peaks within ≤2 kb and ≤5 kb

### NEW: MA Plot
- X axis: log₂(base mean accessibility); Y axis: log₂FC
- Points colored Up / Down / NS by adj. p-value and |log2FC| thresholds
- Gene label modes: Top N by |log2FC|, or custom gene list from file
- Hover tooltip: nearest_gene, log2FC, base mean, adj. p-value
- Same settings panel layout as Volcano Plot (Plot Settings / Customization / Gene Annotation)

### IMPROVED: Column Display Level → Basic / Stat / Full
- Renamed from "Basic (Gene ID + Abundance) / DE Analysis / Full" for clarity
- **Basic**: peak_id, chromosome, coordinates, nearest_gene (ATAC) or gene_id, symbol (DE)
- **Stat**: Basic + base_mean, log2fc, pvalue, adj_pvalue, direction
- **Full**: Stat + lfcse, annotation, distance_to_tss, gene_id, peak_width

### FIX: ATAC-seq UI not activating on initial load
- Fixed `_update_view_with_dataset` to call `_update_atac_ui` alongside `_update_filter_panel_go_mode`
- ATAC filter section and Visualization menu items now activate immediately on file load or database load

### FIX: Volcano plot unavailable on filtered ATAC tab
- Root cause: `removeTab()` shifts Qt tab indices synchronously, but `tab_data` dict keys were not updated before the signal fired
- Fixed with `_remove_tab_safely()`: updates `tab_data` keys before calling `removeTab()`

### FIX: ATAC gene list filtering
- Gene list filter on ATAC-seq data now correctly uses `nearest_gene` (gene symbol) column, not `gene_id` (ENSEMBL ID)

---

## 2026-04-19: v1.1.6 - GO Term Comparison & Dot Plot Legend Improvements

### NEW: GO Term List Filtering
- Enter `GO:XXXXXXX` IDs (one per line) in the **Filter Panel → Gene List** tab while a GO/KEGG dataset is active
- Click **Apply Filter** → new tab *"Filtered: GO Term List (N terms)"*
- Matches against `term_id` / `go_id` column; non-GO IDs trigger a warning

### NEW: GO Term Comparison
- Compare enriched GO/KEGG terms across ≥2 datasets side by side
- **Requirement**: GO term IDs entered in Filter Panel (used as the comparison term set)
- **Workflow**: Comparison Panel → select GO datasets → Comparison Type: *GO Term Comparison* → Apply
- Result tab *"Comparison: GO Terms"* — wide-format table with per-dataset FDR, gene count, fold enrichment
- Terms not found in a dataset shown as `NaN`

### NEW: GO Term Comparison Dot Plot
- Available on *"Comparison: GO Terms"* tab via **Visualization → GO/KEGG Dot Plot**
- X = Datasets, Y = GO Terms (or transposed)
- Dot color = FDR; Dot size = Gene Count or Fold Enrichment (selectable)
- 3-tier size legend with consistent area→diameter scaling

### IMPROVED: Dot Plot Size Legend
- 3-tier biologically meaningful reference markers (small / medium / large) derived from fixed typical ranges — consistent across sessions and datasets
- Correct area→diameter formula: `2 * sqrt(s / π)` instead of `sqrt(s) / 2`
- Dynamic legend spacing, bold title, professional appearance (`fancybox=False`)

### IMPROVED: Comparison Panel UI
- Dedicated left-panel `ComparisonPanel` widget with *GO Term Comparison* mode
- Cleaner dataset selection list with Select All / Clear helpers

---

## 2026-04-01: v1.1.5 - Multi-Group Heatmap & Gene List Order Preservation


### 🎨 Unified UI Theme
- **Forced Light Theme**: Consistent, readable UI across all macOS system appearance settings
  - Fusion style with explicit light palette
  - Black text on white/light gray backgrounds
  - Eliminates dark mode readability issues (black text on dark gray was unreadable)
- **Cross-Platform Consistency**: Same look and feel on Windows and macOS

### 🖥️ macOS Fixes
- **Finder Launch**: Fixed double-click launch from Finder
  - Enhanced working directory management with `sys._MEIPASS`
  - Added `RESOURCEPATH` environment variable for resource lookup
  - Error logging for debugging launch issues
- **Log Terminal Visibility**: Log terminal no longer collapses
  - Fixed size policy (200-250px guaranteed height)
  - Main content area has expansion priority (stretch=100)
  - Always visible regardless of window resizing

### 📋 Platform Requirements
- **macOS**: Minimum version updated to **macOS 13.0 Ventura** (PyQt6 requirement)
- **Windows**: No changes (Windows 10/11 continues to work)
- **Apple Silicon**: Supported via Rosetta 2

### 🔧 Technical Improvements
- Better resource path handling in frozen executables
- Enhanced error visibility for launch failures
- Improved layout behavior for consistent UI across platforms

---

## 2025-12-31: GO/KEGG Analysis Major Update

### 🆕 GO Term Clustering (ClueGO-style)
- **Interactive Clustering Dialog**: Full-featured dialog with real-time network visualization
- **Similarity Methods**: 
  - Jaccard Similarity (gene overlap-based)
  - Kappa Statistic (statistical correlation)
- **Hierarchical Clustering**: Multiple linkage methods (average, complete, single, ward)
- **Network Visualization**:
  - Color-coded clusters with automatic palette
  - Convex hulls around cluster boundaries
  - Interactive tooltips on hover
  - Configurable node size, edge transparency, label size
  - Pan, zoom, and matplotlib toolbar support
- **Cluster Management**:
  - Min/Max cluster size filters
  - Singleton handling
  - Representative term selection
  - Cluster statistics table
  - Collapsible legend panel
- **Apply Functionality**: Export clustered results to new tab with `cluster_id` column

### 📊 GO/KEGG Visualizations
- **Dot Plot**: Gene ratio vs FDR scatter plot with configurable sizing and coloring
- **Bar Chart**: Top enriched terms with -log10(FDR) bars
- **Network Chart**: Cluster-based network visualization (requires clustered data)

### 🔧 Data Model Improvements
- **Gene Set Column**: Added `gene_set` column for GO data (UP/DOWN/TOTAL)
  - Conceptually distinct from DE regulation direction
  - Indicates which DEG group was used for GO analysis
- **Cluster ID Column**: Standardized `cluster_id` column in `StandardColumns`
- **Column Name Flexibility**: Support for multiple column name variants

### 🎨 UI/UX Enhancements
- **Filter Panel Updates**:
  - "Regulation" label for DE data
  - "Gene Set" label for GO data with explanatory tooltip
- **Menu Restructuring**:
  - Flattened GO/KEGG menu items to main level
  - Added 🧬 emoji icons for GO/KEGG items
  - Clearer menu hierarchy
- **Re-filtering Support**: Apply filters on already-filtered tabs (Filtered:Filtered analysis)

### 📖 Documentation
- **Help Dialog Update**: Added comprehensive GO/KEGG Analysis section (Section 4)
- **Encoding Fixes**: Resolved all corrupted characters and emoji issues
- **Content Organization**: Properly numbered sections with HTML entities

### 🐛 Bug Fixes
- **Volcano Plot Autoscale**: Fixed column name mismatch (`log2FC` vs `log2fc`)
- **Debug Log Cleanup**: Removed unnecessary debug print statements
- **Tab Switching**: Improved dataset awareness when switching between tabs
- **Column Filtering**: Fixed internal column exclusion logic

---

## Previous Major Updates

### 2025-12-10: Multi-Dataset Comparison
- Venn Diagram support for 2-3 datasets
- Gene list and statistics comparison modes
- Intersection/Union options
- Comparison results export

### 2025-12-09: Visualization Improvements
- Heatmap with hierarchical clustering
- Dot Plot for comparison results
- Enhanced Volcano Plot with tooltips
- P-adj Histogram customization

### 2025-12-08: FSM & Architecture Refinement
- Finite State Machine (FSM) implementation
- MVP pattern enforcement
- Async worker threads
- Comprehensive logging

---

## Migration Notes

### For Existing Users

1. **GO Data Loading**: 
   - `gene_set` column is now preferred over `direction` for GO analysis
   - Old data with `direction` column still works
   
2. **Filtering**:
   - Filter panel now shows "Gene Set" for GO data
   - "Regulation" is used for DE data filtering
   
3. **Clustering**:
   - New "Cluster GO Terms" menu item under Analysis
   - Requires GO/KEGG dataset
   - Creates new "Clustered:" tab with cluster_id column

4. **Autoscale**:
   - Volcano plot autoscale buttons now work correctly
   - Handles both `log2FC` and `log2fc` column names

---

## Known Issues & Limitations

- Network Chart performance degrades with >200 terms (use clustering first)
- Clustering requires gene symbol column (geneID, Genes, or genes)
- macOS .icns icon requires manual creation during build
- Some matplotlib backends may show deprecation warnings

---

## Upcoming Features (Roadmap)

- [ ] GO enrichment analysis integration (run enrichment from within app)
- [ ] KEGG pathway diagram overlay
- [ ] Custom color scheme editor
- [ ] Batch export for multiple visualizations
- [ ] Session save/load functionality
- [ ] Python API for programmatic access
