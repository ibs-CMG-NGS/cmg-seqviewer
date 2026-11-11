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

Most plot windows (pinned Volcano/Heatmap tabs, standalone dialogs, and the
Concordance Summary) can export a **figure bundle** for the external
**fig-atlas** publication pipeline:

1. With the plot tab/dialog active, go to
 **File → Export Figure Bundle...** (or click **Export Bundle** in the plot window).

2. Choose a destination folder name (defaults to a name based on the plot type).

The bundle is the fig-atlas handoff shape:

- `inputs/data.csv` — the data table with the contract column names
- `metadata/metadata.yaml` — `plot_type` and the `plot_params` column roles
- one reference output set under `outputs/<source_stem>.png/pdf/svg`
- `manifest.json`

fig-atlas draws the panel itself at its final printed size; it does not run a
script. The bundle therefore carries **data + column roles**, not drawing code.
Useful for archiving a figure alongside exactly the data and parameters that
produced it, or handing it off for downstream publication layout.

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
**See also**: [User Guide](../user-guide.md) · [FAQ](24-faq.md)
