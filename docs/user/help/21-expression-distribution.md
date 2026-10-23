# 21. Expression Distribution (Violin/Box)

## 21.1 Overview

The **Expression Distribution** view shows how expression varies **across
samples** for a gene and cell type — not just the mean. It is designed for
per-sample **pseudobulk** data from the scRNA-seq pipeline, with a quantile
summary fallback.

- **pseudobulk**: each point/violin body is one biological sample/replicate.
- **quantile**: the table stores `p10/p25/median/p75/p90`; the view draws a
  box/range instead of a violin.
- The view is **descriptive**. It does not perform differential-expression
  statistics; use the pipeline's pseudobulk DE results for condition tests.

## 21.2 Input format

The primary table is **long-format**:

| gene_id | gene_name | cell_type | sample | dataset | condition | n_cells | n_expressing | pct_expressing | mean_expression | mean_counts |
|---------|-----------|-----------|--------|---------|-----------|---------|--------------|----------------|-----------------|-------------|
| Agrp    | Agrp      | C66-46: Agrp.GABA-4 | Dowsett10xnuc_fasted1 | Dowsett10xnuc | Fasted | 116 | 106 | 91.38 | 1.9938 | 6.5259 |

Required columns:

- `gene_id`
- `cell_type`
- `mean_expression` (normalised `data` layer mean for sample × cell type)
- `sample` for `layout: "pseudobulk"`, or `median` for `layout: "quantile"`

Recommended metadata columns:

- `gene_name`, `dataset`, `condition`
- `n_cells`, `n_expressing`, `pct_expressing`, `mean_counts`
- quantile layout: `p10`, `p25`, `p75`, `p90`

Optional companion files:

| Companion | Contents |
|-----------|----------|
| `gene_index` | per-gene `max_mean_expression`, `max_pct_expressing`, `n_cell_types_detected` |
| `cell_type_summary` | per-cell-type `n_cells` |

## 21.3 Importing

**Import Folder** recognizes `seqviewer_manifest.json` with
`dataset_type: "expression_distribution"`:

```
export/seqviewer/
├── seqviewer_manifest.json
└── datasets/
    ├── hypomap_Dowsett10xnuc_pseudobulk.parquet
    ├── hypomap_Dowsett10xnuc_gene_index.parquet
    └── hypomap_Dowsett10xnuc_cell_type_summary.parquet
```

```json
{
  "datasets": [{
    "dataset_id": "...",
    "alias": "HypoMap Dowsett10xnuc pseudobulk distribution",
    "file_path": "hypomap_Dowsett10xnuc_pseudobulk.parquet",
    "dataset_type": "expression_distribution",
    "organism": "Mus musculus",
    "row_count": 7740,
    "gene_count": 30,
    "cell_type_count": 43,
    "sample_count": 6,
    "distribution_schema": {
      "schema_version": "1.0",
      "layout": "pseudobulk",
      "gene_id_type": "symbol",
      "cell_type_column": "cell_type",
      "sample_column": "sample",
      "sample_unit": "biological_replicate",
      "dataset_column": "dataset",
      "condition_column": "condition",
      "group_columns": ["condition", "dataset"],
      "value_column": "mean_expression",
      "pct_column": "pct_expressing",
      "n_cells_column": "n_cells",
      "pct_scale": "0-100",
      "companion_files": {
        "gene_index": "hypomap_Dowsett10xnuc_gene_index.parquet",
        "cell_type_summary": "hypomap_Dowsett10xnuc_cell_type_summary.parquet"
      }
    }
  }]
}
```

If you copy a `*_pseudobulk.parquet` file plus `*_gene_index.parquet` /
`*_cell_type_summary.parquet` directly into `data/datasets/`, **Refresh**
auto-detects the bundle even without a manifest. The manifest is still
recommended for `sample_unit`, `condition`, and provenance.

The CLI can validate the primary table directly:

```bash
cmg-seqviewer-cli load hypomap_Dowsett10xnuc_pseudobulk.parquet \
  --type expression_distribution --json
```

## 21.4 Opening the view

Open the dataset in the Database Browser, then choose
**Visualization → 🧬 Single-cell RNA-seq → 🎻 Gene Expression Distribution**.

## 21.5 Controls

- **Genes**: search a `gene_id` or `gene_name` (case-insensitive substring)
  and press Enter. Add multiple genes to compare them as vertically stacked
  panels.
- **Cell types**: initially the **top 10 by mean expression** for the selected
  gene(s). Use **Top 10 by mean**, **Select all**, or **Clear**. The list is
  ranked by mean and keeps your selection when genes change.
- **Group by**: `Condition`, `Dataset`, or `Sample` (only columns present in
  the table). `Condition` is the default and draws side-by-side violins for
  each condition; individual sample values are overlaid as points.
- **Plot type**: Violin, Box, Strip, or Box + points. Quantile input forces
  Box/range because there are no cell-level values.
- **Min n_cells / Min % expressing**: remove low-support groups.
- **Log scale (y)**: useful for long-tailed expression.
- **Label length**: truncate long cell-type labels.

The plot is refit to the window on resize. **Refresh Plot** redraws with the
current filters.

## 21.6 Export

- **Export Data** saves the currently filtered long table as CSV/TSV/Excel.
- **Save Figure** exports the plot (PNG/PDF/SVG/TIFF).
- **Export Bundle** creates a reproducible figure bundle; **Pin to Tab** keeps
  the plot as a persistent tab.

## 21.7 Interpretation and limitations

- A violin/box requires **replicate or quantile** values. The aggregated
  `expression_summary` (mean/pct/n_cells only) cannot produce a true violin.
- If `sample_unit: "biological_replicate"`, the spread reflects biological
  variability. If a dataset has only one sample per condition, the plot is
  descriptive and cannot support condition inference.
- No statistical test is performed. Use pseudobulk DE results for
  condition comparisons.
- v1 loads one dataset at a time (pseudobulk up to 5,000,000 rows). The full
  atlas should be split by dataset or exported as a selected gene panel.
- Cell-level data is not included in the pseudobulk bundle.

---
**See also**: [User Guide](../user-guide.md) · [FAQ](24-faq.md) · [Dataset Database](03-dataset-database.md) · [Expression Summary](22-expression-summary.md)
