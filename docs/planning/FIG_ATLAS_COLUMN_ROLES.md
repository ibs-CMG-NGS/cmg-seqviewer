# fig-atlas Column-Role Table — Remaining 22 Plot Types

- **Date**: 2026-11-09
- **Source**: cmg-seqviewer v1.4.1, `export_fig_atlas_bundle()` mappings
- **Purpose**: record the final mapping for the 22 remaining internal plot
  types and the synthetic sample bundle for each.
- **Status**: all 22 mappings are implemented in
  `export_fig_atlas_bundle()`; 22/22 sample bundles pass `fa bundle check`.

The seven earlier-confirmed sample types are not repeated here.

## A. Direct mappings (contract exists, shape matches)

| Your plot_type | fig-atlas plot_type | Current data columns | Current plot_params roles / notes |
|---|---|---|---|
| `volcano` | `volcano` | `gene_id`, `symbol`, `log2FC`, `padj`, `pvalue`, `base_mean`, optional `lfcse`, `stat`, sample columns | thresholds, colors, label mode; rename `log2FC`/`padj` already match |
| `heatmap` | `heatmap` | `gene_id`/`gene_name`/`symbol` + numeric sample columns (wide) | `sample_columns`, `n_genes`, normalization, transpose, sorting, colormap; exporter must pick one label column |
| `ma` | `ma_plot` | `gene_id`, `log2fc`, `base_mean`, `adj_pvalue`, optional `symbol` | thresholds/colors/labels; rename to `baseMean`, `log2FoldChange`, `padj` |
| `pca` | `pca` | `gene_id`/`symbol` + numeric sample columns (wide, one row per gene) | keep one row per gene; pass `sample_columns` if not every numeric column is a sample |
| `go_bar` | `go_bar` | `term_id`, `description`, `ontology`, `gene_ratio`, `bg_ratio`, `pvalue`, `fdr`, `qvalue`, `gene_count`, `gene_symbols`, `fold_enrichment`, `direction`, `gene_set` | top N, x-axis, sort, colors; rename to contract columns |
| `go_dot` | `go_dot` | `term_id`, `description`, `ontology`, `gene_ratio`, `bg_ratio`, `pvalue`, `fdr`, `qvalue`, `gene_count`, `gene_symbols`, `fold_enrichment`, `direction`, `gene_set` | x = Gene Ratio/Fold Enrichment; size = Gene Count; colour = FDR; required names already match |
| `go_cluster_dot` | `go_cluster_dot` | `cluster_id`, `gene_set`, `ontology`, `term_id`, `description`, `gene_ratio`, `bg_ratio`, `pvalue`, `fdr`, `qvalue`, `gene_count`, `gene_symbols`, `fold_enrichment`, `direction`, `_cluster_size`, `_fe_median` | cluster representative table; rename |
| `count_summary` | `count_summary` | `dataset`, `log2fc`, `adj_pvalue` (long) | `fdr_max`, `lfc_min`, `as_pct`, `unit`, `order`; names already match |
| `venn` | `venn` | `dataset`, `item` (long membership) | set labels/unit/filter; names already match |
| `multi_group_heatmap` | `multi_group_heatmap` | `gene_label` + numeric sample columns (wide) | `gene_label_col`, `sample_columns`, `sample_groups`, clustering; names already match |
| `meta_volcano` | `volcano` | `gene_id`, `symbol`, `meta_effect_log2fc`, `meta_log2fc_mean`, `meta_log2fe_mean`, `meta_pvalue_fisher`, `meta_fdr_fisher`, `meta_pvalue_stouffer`, `meta_pvalue_re`, `meta_found_in` | `p_col`, `x_col`, thresholds; send pooled log2FC and meta P as `log2FC`, `padj` |

## B. Direct after a reshape

| Your plot_type | fig-atlas plot_type | Current data columns | Reshape / exporter action |
|---|---|---|---|
| `gene_expression_bar` | `bar_scatter` | gene label column (`gene_id`/`symbol`) + sample columns; group membership in `plot_params.sample_groups` | wide -> long: one row per (gene, sample group) with `symbol`, `group`, `value`; keep replicate-level rows for points |
| `concordance_summary` | `bar_scatter` | `concordance` category column | count rows per category -> `symbol`=category, `value`=count; add a constant `group` series (`group_col`) |
| `composition` | `stacked_bar` | `cell_type`, `PropMean.<condition>` columns, `prop_ratio`, `pvalue`, `fdr` | wide -> long: one row per (condition, cell type) with `category`, `part`, `count` (or proportion) |
| `annotation_comparison` | `cross_condition_dotplot` | `dataset`, `annotation`, `log2fc`, `adj_pvalue` (long) | rename: `annotation` -> `GO Term`, `dataset` -> `Condition`, signed `-log10(adj_pvalue)` -> `Signed -log10(FDR)` |

## C. New contracts/renderers — resolved mapping

The fig-atlas 2026-11-09 reply resolved these; all are implemented.

| Your plot_type | fig-atlas plot_type | Contract roles / exporter action | Sample |
|---|---|---|---|
| `expression_dot` | `dot_matrix` | `row_col: gene_name`, `col_col: cell_type`, `size_col: pct_expressing`, `color_col: mean_expression`; numeric colour is supported | `samples/expression_dot.csv` |
| `genomic_distribution` | `stacked_bar` | `category` = `"all"`, `part` = `annotation`, `count` = number of peaks, `percent: true` (or `bar_scatter` with a `groups` entry) | `samples/genomic_distribution.csv` |
| `concordance_heatmap` | `heatmap` | `label_col: symbol`, `sample_columns: [rna_log2fc, atac_log2fc_mean]`, `normalization: none`; keep `concordance` as an unused extra | `samples/concordance_heatmap.csv` |
| `quadrant` | `group_scatter` | `x_col: atac_log2fc_mean`, `y_col: rna_log2fc`, `group_col: concordance`; cut-offs via `x_cutoffs`/`y_cutoffs` in `plot_params` | `samples/quadrant.csv` |
| `integrated_volcano` | `threshold_scatter` | `x_col: rna_log2fc`, `y_col: rna_padj` (`y_transform: neg_log10`), `effect_col`/`sig_col`, `color_col: concordance`, `size_col: peak_count` | `samples/integrated_volcano.csv` |
| `upset` | `upset` | `dataset_col: dataset`, `item_col: item`; long membership table | `samples/upset.csv` |
| `go_comparison_dot` | `dot_matrix` | reshape wide -> long: `description`, `dataset`, `fe`, `fdr`, `gene_count`; `row_col: description`, `col_col: dataset`, `size_col: gene_count`, `color_col: fe` | `samples/go_comparison_dot.csv` |

## Implementation notes

- `go_dot` is in the direct table and has a validated `samples/go_dot_bundle/`
  (`fa bundle check`: ok).
- `pca`: the exporter keeps the gene × sample orientation, which fig-atlas
  confirmed in the updated 2026-11-09 reply; `sample_columns` is passed when the
  table has non-sample numeric columns.
- All 22 new sample bundles are in
  `cmg_fig_atlas_bundle_samples_2026-11-09/`.
- `fa bundle check`: **22/22 ok, 0 warnings, 0 errors**.
- `fa ingest`/`build --preflight`/`verify`: pass; preflight warnings are from the
  deliberately dense 22-panel test layout.
- fig-atlas v0.4.0 is the reference package for the new contracts/renderers.
- `fa lint` reports 3 unread keys for `plots.go_cluster_dot.direction_colors`,
  which fig-atlas's `fa ingest` adds; the bundle metadata itself has no such key.
