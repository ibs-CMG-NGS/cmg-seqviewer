# CMG-SeqViewer v1.4.0 Release Notes

- **Release date**: 2026-10-23
- **Previous release**: [v1.3.2](https://github.com/ibs-CMG-NGS/cmg-seqviewer/releases/tag/v1.3.2)
- **Full diff**: https://github.com/ibs-CMG-NGS/cmg-seqviewer/compare/v1.3.2...v1.4.0
- **Branch**: `chore/release-v1.4.0` (from `feat/cli`)

## Highlights

### Command-line interface

- New `cmg-seqviewer-cli` entry point with `load`, `filter`, `export`, `run`, and `batch`.
- `load --json` returns machine-readable validation output for pipeline CI.
- Recipe-driven `run`/`batch` workflows reuse the GUI's import and filter logic.
- DE, GO/KEGG, Multi-Group, ATAC, Composition, and Expression Summary datasets
  accept CSV, TSV, and Parquet inputs.
- `--type` covers `differential_expression`, `go_analysis`, `multi_group`,
  `atac_seq`, `composition`, and `expression_summary`.

### Single-cell RNA-seq views

- New **Cell-Type Composition** dataset type and view:
  - PropRatio bars or grouped mean-proportion bars.
  - FDR filtering.
  - `--type composition` CLI/DB support.
- New **Expression Summary** dataset type and view:
  - HypoMap-style wide mean/pct matrices.
  - Long-format pivot up to 5,000,000 rows.
  - Optional `gene_index` / `cell_type_summary` companion files.
  - Gene search, % expressing dot plot, and top-N heatmap.
  - `--type expression_summary` CLI/DB support.
- New `Visualization → 🧬 Single-cell RNA-seq` submenu groups single-cell views.

### Pipeline bundle compatibility

- Pipeline-specific `manifest.json` (`table=expression`, `files={...}`) is
  auto-recognized.
- `expression_summary` bundles are auto-detected from wide mean/pct,
  gene_index, cell_type_summary, or long-format files even without a manifest.
- `dataset_id`, `original_filename`, and `file_path` are auto-derived when omitted.
- Researcher/analysis date are inferred from `/YYYY-initials-organism-type/`
  folder names.
- `cell_type_count` is preserved in dataset metadata.
- Mixed bundles import supported dataset types and skip unsupported ones.

### Fixes

- WSLg mixed-DPI menu/popup ghosting and invisible cursors mitigated:
  Wayland is the default; xcb remains an opt-in path.
- Windows builds use a Per-Monitor V2 DPI manifest.
- Expression dot-plot labels remain fully visible; transpose and colormap are
  shared with the heatmap; selection state persists across refresh.
- Import column auto-mapping precedence and required-column validation are more
  robust (including GO/KEGG and ATAC manual mapping).
- Multi-Group sample-column detection no longer treats `fdr`, `qvalue`, or a
  numeric `cluster_id` as samples.

### Documentation

- F1 help sections reordered so feature sections precede Tips and FAQ.
- Pipeline integration responses and HypoMap expression summary notes updated.
- New planning documents:
  - `docs/planning/MCP_AGENT_INTEGRATION_PLAN.md`
  - `docs/planning/EXPRESSION_DISTRIBUTION_PLAN.md`
  - `docs/planning/archive/EXPRESSION_DISTRIBUTION_ANALYSIS_TEAM_REQUEST.md`

## Upgrade notes

- **Viewer compatibility**: v1.3.2 and earlier cannot read the new
  `composition` / `expression_summary` dataset types. Bundles exported for
  v1.4.0 require v1.4.0 or later.
- **CLI**: install the package or run from the source tree; entry points are
  `cmg-seqviewer-cli` and `rna-seq-analyzer`.
- **Expression Summary long format**: pivot is capped at 5,000,000 rows in v1.
  Use wide mean/pct matrices for the full atlas.

## Known limitations

- Distribution/violin views are **not included** in v1.4.0. The data
  requirements and bundle request are documented in
  `docs/planning/EXPRESSION_DISTRIBUTION_PLAN.md`; a separate
  `expression_distribution` dataset type is planned.
- Full 10.6M-row long-format atlases still require wide matrices or a future
  lazy/DuckDB loader.

## Assets

The tag-triggered GitHub Actions workflow builds and publishes:

- `CMG-SeqViewer-Windows.zip`
- `CMG-SeqViewer-macOS.dmg`
