# 7. GO Term Comparison

## 7.1 Overview

GO Term Comparison lets you compare enriched GO/KEGG terms **across multiple datasets**
side by side. It collects a union of terms from all selected datasets, builds a
comparison table with FDR, gene count, and fold enrichment per dataset, and then
optionally visualizes the result as an interactive dot plot.

## 7.2 Requirements

- At least **2 GO/KEGG datasets** loaded in the session
- A **GO term ID list** entered in the Filter Panel (Gene List input area) — the
 comparison is scoped to these terms only

*If no GO term IDs are provided, the app shows an error and cancels.*

## 7.3 Step-by-Step Workflow

1. Load 2 or more GO/KEGG datasets (e.g., `Ctrl_GO`, `KO_GO`, `OE_GO`) — either
 pipeline-imported files or in-app enrichment results (`Enrichment: …`).
2. Enter the GO term IDs you want to compare in **Filter Panel → Gene List**:

```
GO:0006915
GO:0007049
GO:0008150
```

3. Open the **Comparison Panel** (left panel, below Filter Panel).
4. Select the GO datasets to compare.
5. Set **Comparison Type** to **GO Term Comparison**.
6. Click **Apply** — a new tab **"Comparison: GO Terms"** appears.

> **Workflow example**: compare an imported pipeline result with an in-app
> enrichment result on the same DEG background — because both share the standard
> column contract (`term_id`, `description`, `gene_set`, `fold_enrichment`, `_gene_set`),
> the comparison table and dot plot treat them identically.

## 7.4 Comparison Results Table

The result tab contains one row per GO term with columns for each dataset:

| Column | Description |
|---|---|
| `term_id` | GO/KEGG term identifier (e.g., `GO:0006915`) |
| `description` | Term name / description |
| `ontology` | BP / MF / CC / KEGG |
| `<Dataset>_fdr` | Adjusted p-value (FDR) for each dataset |
| `<Dataset>_gene_count` | Number of enriched genes |
| `<Dataset>_fold_enrichment` | Fold enrichment score |
| `found_in` | Comma-separated list of datasets where the term is significant |

Terms not found in a dataset receive `NaN` for that dataset's columns.

## 7.5 GO Term Comparison Dot Plot

After running a GO Term Comparison, visualize the result as a dot plot:

1. Switch to the **"Comparison: GO Terms"** tab
2. Click **Visualization → GO/KEGG Dot Plot**

### Plot layout

- **X-axis:** datasets (one column per dataset)
- **Y-axis:** GO terms
- **Dot color:** FDR value (low FDR = deep color)
- **Dot size:** Gene Count or Fold Enrichment (selectable)

### Dot plot controls

| Control | Description |
|---|---|
| **Dot Size Metric** | What determines dot area: **Gene Count** (absolute number of enriched genes), **Fold Enrichment** (score relative to background), or **Gene Ratio** (fraction of genes in the term, if available) |
| **Top N Terms** | Limit the plot to the N most significant GO terms (ranked by minimum FDR across datasets) |
| **Transpose** | Swap axes: X = GO Terms, Y = Datasets |
| **Color Map** | Matplotlib colormap for FDR values (default: `RdYlBu_r`) |
| **FDR range** | Min/max FDR cutoff for the color scale |
| **Figure Size** | Width and height in inches |

### Legend

The dot-size legend uses three biologically meaningful reference values
(small / medium / large) derived from the chosen metric's typical range, so dot
sizes are consistent across datasets and plots.

### Export

- **💾 Save Figure** — PNG / SVG / PDF
- Right-click the comparison result table to copy or export as CSV

## 7.6 Tips

- Pre-filter each GO dataset by FDR before running a comparison — this reduces noise
 in the result table.
- Enter only biologically relevant GO term IDs (e.g., terms from a published pathway
 list) to keep the comparison focused.
- Use **Transpose** when you have many datasets but few terms.
- Terms with `NaN` FDR appear as empty (no dot) in the plot — this visually
 highlights dataset-specific enrichment.

---
**See also**: [User Guide](../user-guide.md) · [FAQ](20-faq.md) · [6.2 Meta-signature enrichment](06-go-enrichment-analysis.md#6-2-meta-signature-enrichment)
