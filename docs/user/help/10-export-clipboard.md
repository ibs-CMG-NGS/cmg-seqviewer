# 10. Export & Clipboard

## 10.1 Exporting Data

Export any tab's data to file:

1. Switch to the tab you want to export

2. Select **File →Export Current Tab** (or **Ctrl+E**)

3. Choose format:

 - Excel (.xlsx)

 - CSV (.csv)

 - TSV (.tsv)

4. Choose save location and filename

*Tip: export/save dialogs (this one included) share one remembered
 "last used folder" for the session — pick a location once and later exports
 default to it, so you won't have to re-navigate every time.*

## 10.2 Export Figure Bundle...

Most plot windows (pinned Volcano/Heatmap tabs and the majority of the
 other plot dialogs) can export a self-contained, reproducible **figure bundle**
 instead of just an image:

1. With the plot tab/dialog active, go to
 **File → Export Figure Bundle...**

2. Choose a destination folder name (defaults to a name based on the plot type)

The bundle folder contains:

3. `scripts/figure.py` — a standalone script that reproduces the figure

4. `inputs/data.csv` — the exact data used to draw it

5. `outputs/figure.png/pdf/svg` — the rendered figure (PNG always,
 PDF/SVG best-effort)

6. `metadata/metadata.yaml` and `manifest.json` —
 provenance information

Useful for archiving a figure alongside exactly the data and parameters that
 produced it, or handing it off for a downstream figure-atlas / publication workflow.
 If the current tab doesn't support this, a message says so.

## 10.3 Cell Selection

Flexible cell selection in data tables:

7. Click and drag to select individual cells

8. Select cell ranges (not just full rows)

9. Selection color: light blue for better visibility

10. Multi-selection support (Ctrl+Click)

## 10.4 Clipboard Operations

Copy and paste data like in Excel:

### Copying (Ctrl+C):

11. Select cells in any data table

12. Press **Ctrl+C**

13. Data is copied in tab-delimited format

14. Compatible with Excel, spreadsheet apps

### Pasting (Ctrl+V):

15. Copy gene IDs from any source (Excel, text file, etc.)

16. Click in the Gene List input area (Filter Panel)

17. Press **Ctrl+V**

18. Genes are automatically parsed from clipboard

19. Works with tab-delimited data - uses first column only

**Workflow Example:**

1. Find interesting genes in Comparison Statistics table

2. Select the gene_id column cells

3. Press Ctrl+C to copy

4. Click in Gene List input

5. Press Ctrl+V to paste

6. Apply filter to get detailed view of those genes

---
**See also**: [User Guide](../user-guide.md) · [FAQ](20-faq.md)
