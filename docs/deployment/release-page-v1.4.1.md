## CMG-SeqViewer v1.4.1

Patch release adding the single-cell **expression distribution (violin/box)**
view and `expression_distribution` bundle support for the scRNA-seq pipeline.

### Added

- **Gene Expression Distribution view**
  - Menu: `Visualization → Single-cell RNA-seq → Gene Expression Distribution`
  - **Violin / Box / Strip / Box + points** using per-sample pseudobulk values
  - Group by **Condition / Dataset / Sample**
  - Gene search and multi-gene panels
  - Cell types default to **Top 10 by mean**, with Top 10 / Select all / Clear
  - **Min n_cells**, **Min % expressing**, and log-scale y-axis
  - **Export Data / Save Figure / Export Bundle / Pin to Tab**

- **`expression_distribution` dataset type**
  - Per-sample **pseudobulk** and **quantile summary** long-format input
  - `distribution_schema` defines layout, sample/condition columns,
    `sample_unit`, `pct_scale`, value definition, and companion files
  - `sample_count`, `gene_index`, and `cell_type_summary` metadata
  - `*_pseudobulk.parquet` + companion sets are auto-detected without a manifest

- **CLI support**
  - `cmg-seqviewer-cli load <pseudobulk.parquet> --type expression_distribution --json`
  - Auto-detection from `cell_type` + `mean_expression` + `sample`/quantile
    columns

- **Documentation**
  - New F1 help section **21. Expression Distribution (Violin/Box)**
  - Later sections renumbered: Expression Summary 22, Tips 23, FAQ 24
  - `docs/developer/pipeline-integration.md` §9.9 documents the parquet and
    manifest schema

### Changed and fixed

- Auto-detected `*_pseudobulk.parquet` files now require `gene_id`, `cell_type`,
  `sample`, and `mean_expression` before registration.
- Distribution companion files are copied during import, and manifest filenames
  are updated to the actual destination filenames.
- Companion claim handling is shared with expression summaries, preventing
  distribution companions from being registered as separate datasets.
- Expression Distribution shows a placeholder when no genes or cell types are
  selected instead of an empty plot.
- Multi-gene panels show cell-type x-axis labels only on the last panel.

### Data and bundle compatibility

- Analysis-team pilot bundle:
  - Distribution-only bundle: **1/1 imported**
  - Full bundle: 69 analysis + 1 distribution = **70/70 imported**
- **v1.4.0 and earlier** skip the `expression_distribution` entry. Use
  **v1.4.1 or later** to load distribution bundles.
- `layout: "quantile"` has no cell-level values, so the view renders box/range
  instead of violin.
- v1 loads one distribution dataset at a time (up to 5,000,000 rows). Split the
  full atlas by dataset or export a selected gene panel.

### Upgrade

1. Download and replace the existing installation:
   - `CMG-SeqViewer-Windows.zip`
   - `CMG-SeqViewer-macOS.dmg`
2. Existing databases remain compatible. Add new distribution bundles with
   **Import Folder**, or place them under `data/datasets/` and click **Refresh**.
3. Existing `expression_summary` and `composition` bundles from v1.4.0 continue
   to work unchanged.

### Validation

- **354 passed, 4 deselected** (the 4 deselected tests require live network
  access)
- `mkdocs build --strict` succeeds
- Pilot bundle SHA256 checksums verified
- Distribution dataset loads with both `gene_index` and `cell_type_summary`
  companions
- Offscreen dialog smoke test and figure export verified

### Known limitations

- No condition-level statistical test is included. Use the pipeline's
  pseudobulk DE results for inference.
- Cell-level on-demand distribution data is not included.
- Full-atlas lazy DuckDB query is planned for v2.
- Quantile input does not support violin rendering.

### Documentation

- [Expression Distribution help](https://github.com/ibs-CMG-NGS/cmg-seqviewer/blob/master/docs/user/help/21-expression-distribution.md)
- [Pipeline integration §9.9](https://github.com/ibs-CMG-NGS/cmg-seqviewer/blob/master/docs/developer/pipeline-integration.md)
- [v1.4.1 release notes](https://github.com/ibs-CMG-NGS/cmg-seqviewer/blob/master/docs/deployment/release-notes-v1.4.1.md)

### Full changes

- PR: https://github.com/ibs-CMG-NGS/cmg-seqviewer/pull/10
- Compare: https://github.com/ibs-CMG-NGS/cmg-seqviewer/compare/v1.4.0...v1.4.1
