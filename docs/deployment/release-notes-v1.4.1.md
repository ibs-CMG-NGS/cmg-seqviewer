# CMG-SeqViewer v1.4.1 Release Notes

- **Release date**: 2026-10-23
- **Previous release**: [v1.4.0](https://github.com/ibs-CMG-NGS/cmg-seqviewer/releases/tag/v1.4.0)
- **Full diff**: https://github.com/ibs-CMG-NGS/cmg-seqviewer/compare/v1.4.0...v1.4.1
- **Branch**: `chore/release-v1.4.1` (from `feat/expression-distribution`)

## Highlights

### Gene Expression Distribution (violin/box)

- New `expression_distribution` dataset type for **per-sample pseudobulk** and
  **quantile summary** tables from the scRNA-seq pipeline.
- New view:
  `Visualization → 🧬 Single-cell RNA-seq → 🎻 Gene Expression Distribution`.
- **Violin / Box / Strip / Box + points** by cell type.
- Group by **condition**, **dataset**, or **sample**; individual sample values
  are overlaid as points.
- Gene search and multi-gene panels; cell types default to **top 10 by mean**
  with Top 10 / Select all / Clear controls.
- **Min n_cells** and **Min % expressing** filters; log-scale y-axis.
- **Export Data**, **Save Figure**, **Export Bundle**, and **Pin to Tab**.

### Pipeline bundle support

- Recognizes `dataset_type: "expression_distribution"` in
  `seqviewer_manifest.json`.
- New `distribution_schema` carries layout, sample/condition columns,
  `sample_unit`, `pct_scale`, value definition, and companion files.
- Companion files (`gene_index`, `cell_type_summary`) are copied and loaded
  with the primary dataset.
- `sample_count` is stored in dataset metadata.
- Auto-detects `*_pseudobulk.parquet` + companion sets without a manifest.
- The analysis team's pilot bundle imports **70/70 datasets** (69 analysis +
  1 distribution).

### CLI

- `cmg-seqviewer-cli load <pseudobulk.parquet> --type expression_distribution --json`.
- Auto-detects pseudobulk/quantile long tables from `cell_type` +
  `mean_expression` + `sample`/quantile columns.

### Documentation

- New F1 help section **21. Expression Distribution (Violin/Box)**; later
  sections renumbered (Expression Summary 22, Tips 23, FAQ 24).
- `docs/developer/pipeline-integration.md` §9.9 documents the
  `expression_distribution` parquet schema and manifest.
- Planning docs updated with the 2026-10-22 pilot confirmation and
  implementation status.

## Validation

- `354 passed, 4 deselected`.
- `mkdocs build --strict` succeeds.
- Pilot `expression_distribution_only`: 1/1 imported.
- Full pilot bundle: 70/70 imported; distribution dataset loads with
  `gene_index` and `cell_type_summary`.
- SHA256 checksums of the delivered pilot verified.
- Offscreen dialog smoke test and figure export verified.

## Upgrade notes

- **Viewer compatibility**: v1.4.0 and earlier cannot read
  `expression_distribution` datasets. A mixed bundle imports normally in
  v1.4.0 but skips the distribution entry; v1.4.1 imports all 70.
- The view is **descriptive**. Condition inference/statistical testing requires
  the pipeline's pseudobulk DE results.
- v1 loads one distribution dataset at a time (up to 5,000,000 rows). The full
  atlas should be split by dataset or exported as a selected gene panel.

## Known limitations

- Cell-level on-demand distribution data is not included.
- Full-atlas lazy DuckDB query is planned for v2.
- Quantile input renders box/range (no violin) because cell-level values are
  not available.
- Per-dataset facets and condition-level statistical tests are not part of
  this view.

## Assets

The tag-triggered GitHub Actions workflow builds and publishes:

- `CMG-SeqViewer-Windows.zip`
- `CMG-SeqViewer-macOS.dmg`
