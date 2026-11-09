# Reply to the 2026-11-09 mapping request

- **Date**: 2026-11-09
- **About**: `cmg_fig_atlas_mapping_2026-11-09.zip` (`COLUMN_ROLES.md` + `samples/`)
- **From**: fig-atlas (bundle contract owner)
- **Scope**: final mapping for the 22 plot types, answers to the eight questions, and the package
  changes we will make

## 0. Checks on the samples

- `go_dot`: contract `de_go.go_dot` is in the package; `fa bundle check` on
  `samples/go_dot_bundle/` → **ok**, and on `samples/go_dot.csv` (as a bundle) → **ok**. Your columns
  match the contract exactly.
- `expression_dot`: contract `core.dot_matrix` is in the package; `fa bundle check` on
  `samples/expression_dot.csv` (`row_col: gene_name`, `col_col: cell_type`,
  `size_col: pct_expressing`, `color_col: mean_expression`) → **ok**. The numeric colour it needs is
  now implemented (answer 2).
- The other six samples were read against the contracts named below; no shape problem was found.

## 1. A. Direct mappings (confirmed)

| Your plot_type | fig-atlas plot_type | Contract columns | Exporter action |
|---|---|---|---|
| `volcano` | `volcano` | `log2FC`, `padj` | names already match; keep `gene_id`, `symbol`, `base_mean`, `pvalue` as optional columns |
| `heatmap` | `heatmap` | `label_col` + numeric sample columns (min 2) | name one label column (`symbol`); one row per gene |
| `ma` | `ma_plot` | `baseMean`, `log2FoldChange`, `padj` | rename `base_mean`/`log2fc`/`adj_pvalue` |
| `pca` | `pca` | numeric sample columns (min 3) | transpose to one row per sample; keep `sample_groups` in `plot_params` |
| `go_bar` | `go_bar` | `description` (required) + term columns | names already match |
| `go_cluster_dot` | `go_cluster_dot` | `description`, `cluster_id` + term columns | names already match |
| `count_summary` | `count_summary` | `dataset`, `log2fc`, `adj_pvalue` | names already match |
| `venn` | `venn` | `dataset`, `item` | names already match |
| `multi_group_heatmap` | `multi_group_heatmap` | `gene_label` + numeric sample columns | names already match |
| `meta_volcano` | `volcano` | `log2FC`, `padj` | send `meta_log2fc_mean` → `log2FC` and the meta P → `padj` |

## 2. B. Direct after a reshape (confirmed)

| Your plot_type | fig-atlas plot_type | Contract columns | Exporter action |
|---|---|---|---|
| `gene_expression_bar` | `bar_scatter` | `symbol`, `group`, `value` | wide -> long, one row per replicate: gene, sample group, value |
| `concordance_summary` | `bar_scatter` | `symbol`, `value` | one row per concordance category, count as `value` |
| `composition` | `stacked_bar` | `category`, `part`, `count` | wide -> long, one row per (condition, cell type); `percent` in `plot_params` for shares |
| `annotation_comparison` | `cross_condition_dotplot` | `GO Term`, `Condition`, `Signed -log10(FDR)` | `annotation` -> `GO Term`, `dataset` -> `Condition`, signed `-log10(adj_pvalue)` -> `Signed -log10(FDR)` |

## 3. C. Decisions for the eight types

**1. `go_dot` — colour and size.** Colour is FDR, fixed in the renderer. Size is a config choice:
`size_mode: Gene Count` (your current measure) or `Gene Ratio` or `Fold Enrichment`; x is `x_axis:
Gene Ratio` or `Fold Enrichment`. Nothing to change in the exporter; the sample already passes.

**2. `expression_dot` — `dot_matrix` with a numeric colour.** Yes, use `dot_matrix`
(`row_col: gene_name`, `col_col: cell_type`, `size_col: pct_expressing`,
`color_col: mean_expression`). **Implemented:** a numeric `color_col` now draws a continuous colour
scale with a colourbar (`color_cmap`, `color_min`, `color_max`, `colorbar_label`), while a text
`color_col` keeps the category legend (`color_mode` forces either reading). No binning needed.

**3. `genomic_distribution` — a bar, not a pie.** We do not add a pie renderer: a pie is hard to
read and the toolkit has no print checks for it. Use `bar_scatter` (one bar per annotation category,
count as `value`) for a single peak set, or `stacked_bar` with a `set` column if several peak sets
must share one bar. Please add a `set` column to the sample if you need the stacked form.

**4. `concordance_heatmap` — `heatmap` now, strip optional.** Send `label_col: symbol` with the
numeric columns `rna_log2fc` and `atac_log2fc_mean`; the diverging colormap suits signed values. The
concordance strip is not drawn by `heatmap`; we will add an optional strip to `signed_heatmap` if
you want it, but the first mapping does not need it. Keep `concordance` in the table as an unused
extra (or a separate panel).

**5. `quadrant` — cut-off lines are config, not contract.** The contract fixes the columns only:
`x_col: atac_log2fc_mean`, `y_col: rna_log2fc`, `group_col: concordance` (with `group_colors` and
`group_labels` in `plot_params`). **Implemented:** `group_scatter` now takes `x_cutoffs` and
`y_cutoffs` (plot_params), drawn as dashed lines with colour, style, width and opacity from
`cutoff_line_*`.

**6. `integrated_volcano` — `threshold_scatter` extended.** **Implemented:** `color_col` (a
category, here `concordance`) and `size_col` (a number, here `peak_count`) are in the renderer. With
`color_col` the up/down/ns colouring is replaced by your categories and a legend; `size_col` scales
the dot area between `size_min` and `size_max`. The contract does not change (it still reads the
four role columns). `x_col`/`y_col` stay `rna_log2fc` / `rna_padj` with `y_transform: neg_log10`.

**7. `upset` — renderer added.** `upset` is in the package with the `core.upset` contract
(`dataset`, `item`, long membership). Intersections are computed in the renderer from the membership
table; no extra column is needed. Do not fall back to a two-set Euler unless a figure has two sets.

**8. `go_comparison_dot` — long table, `dot_matrix`.** Send one row per (term, dataset):
`description`, `dataset`, `fe`, `fdr`, `gene_count`. Map with `row_col: description`,
`col_col: dataset`, `size_col: gene_count`, `color_col: fe` (numeric colour from answer 2). `fdr` is
used as a filter in `plot_params` (a threshold), not as a drawn value.

## 4. What fig-atlas has added

All four are in the package now (tests and a gallery example each); they will be in the next
release:

1. `dot_matrix`: numeric `color_col` (continuous colour scale and colourbar).
2. `group_scatter`: optional `x_cutoffs` / `y_cutoffs` (config only).
3. `threshold_scatter`: `color_col` (category) and `size_col` (number).
4. `upset`: renderer + `core.upset` contract.

Until the release, the export for `expression_dot`, `quadrant`, `integrated_volcano`, `upset` and
`go_comparison_dot` can be prepared and will draw correctly on the development branch.

## 5. Next step

Send the mapping into `export_fig_atlas_bundle()` as above, then one sample bundle per new type; we
will run `fa bundle check`, ingest and preflight on them and return the report, as with the first
seven.
