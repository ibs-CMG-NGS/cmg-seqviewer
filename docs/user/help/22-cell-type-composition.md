# 22. Cell-Type Composition

## 22.1 Overview

The **Cell-Type Composition** view visualizes how the proportions of cell
types change between conditions — the output of propeller / limma-style
composition analyses (e.g. scRNA-seq pseudobulk pipelines).

It answers a different question from the expression views: not "which genes
change?" but "which cell populations expand or shrink?".

## 22.2 Input format

A composition table is auto-detected when it contains:

- a **cell type** column (`cell_type`, `CellType`, `population`, ...)
- **condition mean** columns named `PropMean.<condition>` (at least two), or a
  `PropRatio` column
- a **p-value / FDR** column (`P.Value`, `pvalue`, `FDR`, `padj`, ...)

Typical pipeline output:

| cell_type | PropMean.Control | PropMean.Treatment | PropRatio | P.Value | FDR |
|-----------|------------------|--------------------|-----------|---------|-----|
| T cell    | 0.45             | 0.55               | 0.10      | 0.001   | 0.003 |
| B cell    | 0.30             | 0.20               | -0.10     | 0.020   | 0.030 |
| NK cell   | 0.25             | 0.25               | 0.00      | 0.900   | 0.950 |

`PropMean.*` columns keep their original names; the condition labels are read
from the name after `PropMean.` (or `prop_mean_`).

## 22.3 Opening the view

**Visualization → 🧫 Cell-Type Composition** (the current tab must be a
composition dataset).

## 22.4 Plot modes

- **PropRatio (difference)** — one horizontal bar per cell type, sorted by
  the absolute change. Bars are **red** for significant increases, **blue**
  for significant decreases, and **grey** for non-significant changes
  (FDR ≤ threshold). Significance stars (`*`, `**`, `***`) are shown at the
  bar ends.
- **Mean proportion by condition** — grouped bars per cell type, one bar per
  `PropMean.<condition>` column, optionally shown as percentages.

Controls:

| Control | Meaning |
|---------|---------|
| Significant only | keep only rows with FDR ≤ threshold |
| FDR ≤ | significance threshold (default 0.05) |
| Top N | maximum number of cell types shown |
| Sort by | Ratio / Max mean, FDR, or cell type name |
| Show as % | display mean proportions as percentages (means mode) |
| Show significance marks | draw `*`/`**`/`***` at bar ends (ratio mode) |

Use **Export Data** to save the currently displayed rows as CSV/TSV/Excel,
and **Export Bundle** to create a reproducible figure bundle.

## 22.5 Filtering and CLI

The Filter Panel's **Statistical** tab shows an **FDR** cutoff for
composition datasets. Applying it creates a filtered child sheet.

```bash
# Inspect a composition file
cmg-seqviewer-cli load composition.parquet --json

# Filter by FDR
cmg-seqviewer-cli filter composition.parquet --fdr-max 0.05 --out sig.csv
```

Composition data can also be imported through the database by setting
`"dataset_type": "composition"` in `seqviewer_manifest.json`.

---
**See also**: [User Guide](../user-guide.md) · [FAQ](20-faq.md) · [Command Line Interface](21-command-line-interface.md)
