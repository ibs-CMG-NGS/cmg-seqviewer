# Response to the 2026-11-09 fig-atlas review

- **Date**: 2026-11-09
- **About**: `FIGURE_ATLAS_REPLY_2026-11-09.md`
- **From**: cmg-seqviewer
- **Scope**: confirmed changes, motif-colour documentation, and the 22-type mapping request

## 1. Confirmed changes

The four requested changes are in place and verified:

- `01_padj_histogram`: `bins: 50`
- `06_chromvar`: only `log2fc_threshold` / `padj_threshold`
- `07_expression_distribution`: grouped violin (`x_col: cell_type`,
  `hue_col: condition`, `hue_order: [Control, Treated]`)
- `03_motif_enrichment`: significance colour (`-log10(p)`),
  `colorbar_label: -log10(p)`, data-derived `fc_min`/`fc_max`

Our validation:

- `fa bundle check`: **7/7 ok, 0 warnings, 0 errors**
- `fa ingest bundle`: **7/7**
- `fa build --preflight` / `fa build`: **ALL 1 PROJECT(S) PASSED**
- `fa lint`: **0 unread keys**
- `fa verify`: **PASS** (dense test-layout warnings only)

Thank you for documenting the motif colour use in the ATAC feature contract.

## 2. Mapping request for the remaining 22 types

Attached:

- `COLUMN_ROLES.md` — current dataframe columns and plot-parameter roles for all
  22 remaining internal `plot_type`s, split into:
  - **A. Direct** (contract exists, shape matches)
  - **B. Direct after a reshape**
  - **C. Needs a contract/renderer**
- `samples/` — one synthetic table for each of the eight Table C types:
  `go_dot`, `expression_dot`, `genomic_distribution`, `concordance_heatmap`,
  `quadrant`, `integrated_volcano`, `upset`, `go_comparison_dot`.

Please return the mapping table as before:

- fig-atlas `plot_type`
- columns the contract reads
- any reshape the exporter must do

For Table C, please also say whether you will add a contract/renderer or whether
we should reshape to an existing one. The open questions are listed at the end
of `COLUMN_ROLES.md`.

## 3. Next step

After the mapping table arrives, we will:

1. add the mappings to `export_fig_atlas_bundle()`;
2. generate one sample bundle per newly mapped type;
3. run `fa bundle check` and the ingest/build/lint/verify cycle;
4. keep the seven confirmed bundles as the reference set.

## 4. Delivery

- Mapping request folder: `cmg_fig_atlas_mapping_2026-11-09`
- ZIP: `cmg_fig_atlas_mapping_2026-11-09.zip`
