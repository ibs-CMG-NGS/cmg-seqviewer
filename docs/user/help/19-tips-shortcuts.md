# 19. Tips & Shortcuts

## 19.1 Keyboard Shortcuts

 | Shortcut
 | Action

 | **Ctrl+O**
 | Open Dataset

 | **Ctrl+A**
 | Open ATAC-seq Dataset

 | **Ctrl+G**
 | Open GO/KEGG Results

 | **Ctrl+B**
 | Browse Database (Database Browser)

 | **Ctrl+I**
 | Import Current Dataset to Database

 | **Ctrl+E**
 | Export Current Tab

 | **Ctrl+F**
 | Find in Sheet (opens the keyword search bar)

 | **Ctrl+Shift+F**
 | Apply Filter

 | **Ctrl+V**
 | Volcano Plot (or Paste in Gene List)

 | **Ctrl+P**
 | PCA Plot

 | **Ctrl+C**
 | Copy Selected Cells

 | **Ctrl+1**
 | Toggle Datasets (tree) panel

 | **Ctrl+2**
 | Toggle Filter / Compare panel

 | **Ctrl+\\**
 | Toggle Split View

 | **Ctrl+Shift+S**
 | Save Project (.seqproj)

 | **Ctrl+Alt+S**
 | Save Project As... (.seqproj)

 | **Ctrl+Shift+O**
 | Open Project (.seqproj)

 | **Ctrl+Q**
 | Exit Application

 | **F1**
 | Open this Help Documentation

*Tip: file dialogs for export/save (Excel/CSV export, figure/data export,
 Save Project As, etc.) share one remembered "last used folder" for the session,
 so each new export defaults to wherever you saved most recently.*

## 19.2 Best Practices

- **Dataset Naming:** Use descriptive names when loading datasets for easier identification

- **Recent Files:** Leverage Recent Files menu for quick access to frequently used data

- **Dataset Renaming:** Use the Rename button to update dataset names as your analysis progresses

- **Data Quality:** Ensure your input data has proper gene IDs and symbols

- **Column Names:** Use standard names (gene_id, symbol, log2FC, padj) - case insensitive

- **Multiple Filters:** Apply filters sequentially to narrow down results

- **Comparison Options:** Choose intersection vs. union carefully:

 - Intersection: Find genes changed in ALL conditions (more stringent)

 - Union: Find genes changed in ANY condition (more comprehensive)

- **Visualization Settings:** All plot settings are saved between sessions

- **Tab Management:** Close unused tabs (click X) to keep workspace organized

- **Drag & Drop:** Quickly load files by dragging them onto the application window

## 19.3 New Features Summary

- **📂 Dataset Tree Panel:** Left panel now shows datasets as a tree with child nodes
 for each derived sheet (Whole, Filtered, Comparison, Plot). Click to switch tabs,
 bidirectional sync with the tab bar.

- **💾 Project Save/Load (.seqproj):** Save your analysis session as a
 lightweight recipe (datasets, filters, comparisons, RNA–ATAC integration,
 pinned Volcano/Heatmap tabs) and re-derive it later. Use
 **File → Save Project** (Ctrl+Shift+S) / **Open Project** (Ctrl+Shift+O).
 See section **7b** for what is and isn't restored. Recent Projects sub-menu
 for quick access.

- **📌 Pin to Tab:** Plot dialogs now have a "📌 Pin to Tab" button to embed
 Volcano Plot or Heatmap as a persistent tab in the main window.

- **Plot Settings Dock:** Right-side dock panel appears automatically when
 a pinned plot tab is active. Adjust thresholds, colors, and colormaps
 without reopening dialogs.

- **🌡️ Multi-Group Heatmap:** LRT omnibus result CSV → interactive Z-score clustermap
 with group color bars, gene cluster cutting, and CSV export

- **Gene List Filtering on Multi-Group:** Filter by gene symbol on multi-group sheets;
 child filtered sheets can be directly passed to the heatmap dialog

- **Dataset Database:** Parquet-based DB for instant dataset loading

- **📥 Import Folder:** Merge pipeline output folders into the DB in one click

- **merge_db.py:** CLI tool for batch-merging multiple pipeline runs

- **Auto-Register:** Drop parquet files and click Refresh — no metadata editing

- **🔵 PCA Plot:** Sample-level PCA from abundance columns (Ctrl+P)

- **🔍 GO Term List Filtering:** Paste GO:XXXXXXX IDs into the Filter Panel to filter GO datasets to specific terms

- **📊 GO Term Comparison:** Compare enriched GO/KEGG terms across multiple datasets side by side with an interactive dot plot

- **Window Icons:** Each window has a unique icon for easy identification in taskbar

- **Dataset Rename:** Change dataset names anytime - updates everywhere automatically

- **Recent Files:** Quick access to your 10 most recent files with path preview

- **Drag & Drop:** Drop Excel files anywhere to load datasets instantly

- **Dot Plot:** New visualization for comparison results with clustering

- **Smart Tooltips:** Auto-positioning tooltips that never get cut off

- **Gene Clustering:** Reorder genes by similarity in heatmaps and dot plots

- **Cell Selection:** Select individual cells, not just rows

- **Clipboard:** Ctrl+C/V support for Excel-like workflow

- **Comparison Panel:** Dedicated panel for dataset comparisons with clear options

## 19.4 Performance Tips

- **Large Datasets:** Use Basic or DE Analysis column view to improve responsiveness

- **Heatmaps:** Limit to top 100-200 genes for better performance

- **Gene Clustering:** May take longer with >100 genes - consider pre-filtering

- **Multiple Tabs:** Close tabs you're not using to free up memory

## 19.5 Getting Help

- Press **F1** anytime to open this documentation

- Check **Help →About** for version information and latest features

- Review log messages at the bottom of the window for detailed status

---
**See also**: [User Guide](../user-guide.md) · [FAQ](20-faq.md)
