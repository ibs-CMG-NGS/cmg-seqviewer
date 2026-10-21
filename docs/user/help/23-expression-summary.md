# 23. Expression Summary (Gene × Cell Type)

## 23.1 Overview

The **Expression Summary** view explores a gene × cell-type expression table —
typically a HypoMap-style atlas summary with:

- `mean_expression` (normalised mean expression)
- `pct_expressing` (percentage of cells with count > 0)
- `n_cells` (cell-type size)

It is **not** a differential-expression result. It is a reference atlas view:
search a gene, then see which cell types express it and how strongly.

## 23.2 Input format (wide layout)

The primary table is a **wide matrix**:

| gene_id | gene_name | C185-113: Nkx2-4.GABA-3 | C185-042: Astro-1 | ... |
|---------|-----------|--------------------------|-------------------|-----|
| G1      | Nkx2-4    | 0.12                     | 3.40              | ... |

- `gene_id` — required (symbol or Ensembl ID)
- `gene_name` / `symbol` — display name (falls back to `gene_id`)
- all remaining numeric columns — cell types

Optional companion files (declared in the manifest):

| Companion | Contents |
|-----------|----------|
| `pct` | same shape as the mean matrix, `pct_expressing` |
| `gene_index` | per-gene `max_mean_expression`/`max_pct_expressing` (or `max_mean`/`max_pct`), `n_cell_types_detected` |
| `cell_type_summary` | per-cell-type `n_cells` and dataset composition |

> **Wide** layout is recommended. Per-dataset **long** layout is also accepted
> up to 5,000,000 rows (it is pivoted to wide on load). Larger long tables
> (e.g. the full 10.6M-row atlas) are rejected — export the wide matrices
> instead.

## 23.3 Importing

Expression summaries are **manifest/DB-first** (they are not auto-detected
from arbitrary numeric tables). **Import Folder** also recognizes a pipeline's
own `manifest.json` (`"table": "expression"`, `"files": {...}`). Use
**File → Database → Import Folder** with:

```
hypomap_C66/
├── seqviewer_manifest.json
└── datasets/
    ├── hypomap_C66_wide_mean.parquet
    ├── hypomap_C66_wide_pct.parquet
    ├── hypomap_gene_index.parquet
    └── hypomap_cell_type_summary.parquet
```

```json
{
  "datasets": [{
    "alias": "HypoMap C66 mean expression",
    "file_path": "hypomap_C66_wide_mean.parquet",
    "dataset_type": "expression_summary",
    "organism": "Mus musculus",
    "cell_type_count": 65,
    "expression_schema": {
      "layout": "wide",
      "value_type": "mean_expression",
      "pct_scale": "0-100",
      "cell_type_level": "C66",
      "companion_files": {
        "pct": "hypomap_C66_wide_pct.parquet",
        "gene_index": "hypomap_gene_index.parquet",
        "cell_type_summary": "hypomap_cell_type_summary.parquet"
      }
    }
  }]
}
```

`file_path` and companion names may be bare filenames or `datasets/<filename>`
(the importer normalizes to the basename). The CLI can validate the primary
matrix directly:

```bash
cmg-seqviewer-cli load hypomap_C66_wide_mean.parquet \
  --type expression_summary --json
```

## 23.4 Opening the view

Open the dataset in the Database Browser, then choose
**Visualization → 🧬 Gene × Cell-Type Expression**.

## 23.5 Gene search and views

- **Gene search**: type a `gene_id` or `gene_name` (case-insensitive
  substring) and press Enter. Add multiple genes to compare them side by side.
- **Cell types**: all cell types are selected by default; Ctrl/Shift-click to
  narrow the selection.
- **Dot plot** (default): x = cell type, y = gene, dot size = % expressing,
  dot color = mean expression. Cell types below **Min n_cells** or **Min %
  expressing** are shown in grey.
- **Top-N heatmap**: the selected genes × top cell types as a heatmap
  (Z-score or raw). Long cell-type labels are truncated; hover a dot to see
  the full gene/cell-type name, mean, pct, and n_cells.

## 23.6 Export and CLI

- **Export Data** saves the currently displayed long table (dot plot) or
  matrix (heatmap) as CSV/TSV/Excel.
- **Export Bundle** creates a reproducible figure bundle; **Pin to Tab** keeps
  the plot as a persistent tab.
- CLI statistical filtering does not apply to this type. Use gene list /
  keyword filtering, or the dialog's own filters.

## 23.7 Limitations

- Per-dataset long layout is supported up to 5,000,000 rows (pivoted to wide
  on load); the full 10.6M-row atlas requires the wide matrices or the future
  DuckDB-backed loader.
- Synonym/alias gene search is not automatic (case-insensitive substring only).
- A per-dataset facet filter is not available; `cell_type_summary` is shown as
  metadata for now.
- Expression summaries must come through the manifest/DB (or CLI with
  `--type expression_summary`), not plain File → Open.

---
**See also**: [User Guide](../user-guide.md) · [FAQ](20-faq.md) · [Dataset Database](03-dataset-database.md)
