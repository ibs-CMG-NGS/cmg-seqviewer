## CMG-SeqViewer v1.4.0

Minor release adding a headless CLI, single-cell composition/expression views,
and pipeline bundle support.

### Added

- **Headless CLI** (`cmg-seqviewer-cli`)
  - `load`, `filter`, and `export` commands with `--json` machine-readable
    validation for pipeline CI.
  - Recipe-driven `run` and `batch` workflows using the same import/filter
    logic as the GUI.
  - DE, GO/KEGG, Multi-Group, ATAC, and Composition inputs in CSV, TSV, and
    Parquet format.

- **Cell-Type Composition**
  - New `composition` dataset type for propeller/limma results
    (`cell_type`, `PropMean.<condition>`, `PropRatio`, `FDR`).
  - PropRatio bars or grouped mean-proportion bars with FDR filtering.
  - CLI support via `--type composition`.

- **Expression Summary**
  - New `expression_summary` dataset type for HypoMap-style gene × cell-type
    matrices.
  - Wide mean/pct matrices, optional `gene_index` and `cell_type_summary`
    companions, and long-format pivot up to 5,000,000 rows.
  - Gene search, % expressing dot plot, and top-N heatmap.
  - CLI support via `--type expression_summary`.

- **Pipeline bundle support**
  - Pipeline-specific `manifest.json` (`table=expression`, `files={...}`) is
    auto-recognized.
  - `expression_summary` bundles are auto-detected from wide/long files and
    companions even without a manifest.
  - `dataset_id`, `original_filename`, and `file_path` are derived when omitted;
    researcher and analysis date are inferred from
    `/YYYY-initials-organism-type/` folder names.
  - `cell_type_count` is preserved in dataset metadata.

- **Single-cell RNA-seq submenu**
  - Groups Cell-Type Composition and Gene × Cell-Type Expression under
    `Visualization → Single-cell RNA-seq`.

### Fixed and improved

- WSLg mixed-DPI menu/popup ghosting and invisible cursors mitigated
  (Wayland default; xcb remains opt-in).
- Windows builds use a Per-Monitor V2 DPI manifest.
- Expression dot-plot labels remain fully visible; transpose and colormap are
  shared with the heatmap; selection state persists across refresh.
- Import column auto-mapping precedence and required-column validation are more
  robust, including manual mapping for GO/KEGG and ATAC.
- Multi-Group sample-column detection no longer treats `fdr`, `qvalue`, or a
  numeric `cluster_id` as samples.

### Compatibility and upgrade notes

- **v1.3.2 and earlier cannot read** the new `composition` /
  `expression_summary` dataset types. Bundles exported for v1.4.0 require
  **v1.4.0 or later**.
- `expression_distribution` is **not part of v1.4.0**; it was added in
  **v1.4.1**.
- Expression Summary long-format pivot is capped at 5,000,000 rows in v1. Use
  wide mean/pct matrices for the full atlas.
- The CLI is available as `cmg-seqviewer-cli` and `rna-seq-analyzer` after
  installation.

### Validation

- **339 passed, 4 deselected** (the 4 deselected tests require live network
  access).
- CLI `load --json`, Composition, and Expression Summary paths verified.
- Real pipeline bundles imported through Import Folder/DB.

### Documentation

- F1 help sections: Command Line Interface (19), Cell-Type Composition (20),
  Expression Summary (21), Tips (22), FAQ (23).
- Pipeline integration schema reference updated.
- MCP / AI agent and Expression Distribution planning documents added.

### Full changes

- PR: https://github.com/ibs-CMG-NGS/cmg-seqviewer/pull/9
- Compare: https://github.com/ibs-CMG-NGS/cmg-seqviewer/compare/v1.3.2...v1.4.0
- Release notes: https://github.com/ibs-CMG-NGS/cmg-seqviewer/blob/v1.4.0/docs/deployment/release-notes-v1.4.0.md
