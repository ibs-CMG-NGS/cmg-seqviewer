# fig-atlas Column-Role Table — Remaining 22 Plot Types

- **Date**: 2026-11-09
- **Source**: cmg-seqviewer v1.4.1, `export_fig_atlas_bundle()` mappings
- **Purpose**: give fig-atlas the current dataframe shape and column roles for the
  remaining 22 internal plot types, plus one synthetic sample table for each of
  the eight types in Table C.

The seven already-confirmed sample types are not repeated here.

## A. Direct mappings (contract exists, shape matches)

| Your plot_type | fig-atlas plot_type | Current data columns | Current plot_params roles / notes |
|---|---|---|---|
| `volcano` | `volcano` | `gene_id`, `symbol`, `log2FC`, `padj`, `pvalue`, `base_mean`, optional `lfcse`, `stat`, sample columns | thresholds, colors, label mode; rename `log2FC`/`padj` already match |
| `heatmap` | `heatmap` | `gene_id`/`gene_name`/`symbol` + numeric sample columns (wide) | `sample_columns`, `n_genes`, normalization, transpose, sorting, colormap; exporter must pick one label column |
| `ma` | `ma_plot` | `gene_id`, `log2fc`, `base_mean`, `adj_pvalue`, optional `symbol` | thresholds/colors/labels; rename to `baseMean`, `log2FoldChange`, `padj` |
| `pca` | `pca` | `gene_id`/`symbol` + numeric sample columns (wide, one row per gene) | `sample_columns`, `sample_groups`, `n_genes`, transform, scaling; transpose to one row per sample |
| `go_bar` | `go_bar` | `term_id`, `description`, `ontology`, `gene_ratio`, `bg_ratio`, `pvalue`, `fdr`, `qvalue`, `gene_count`, `gene_symbols`, `fold_enrichment`, `direction`, `gene_set` | top N, x-axis, sort, colors; rename to contract columns |
| `go_cluster_dot` | `go_cluster_dot` | `cluster_id`, `gene_set`, `ontology`, `term_id`, `description`, `gene_ratio`, `bg_ratio`, `pvalue`, `fdr`, `qvalue`, `gene_count`, `gene_symbols`, `fold_enrichment`, `direction`, `_cluster_size`, `_fe_median` | cluster representative table; rename |
| `count_summary` | `count_summary` | `dataset`, `log2fc`, `adj_pvalue` (long) | `fdr_max`, `lfc_min`, `as_pct`, `unit`, `order`; names already match |
| `venn` | `venn` | `dataset`, `item` (long membership) | set labels/unit/filter; names already match |
| `multi_group_heatmap` | `multi_group_heatmap` | `gene_label` + numeric sample columns (wide) | `gene_label_col`, `sample_columns`, `sample_groups`, clustering; names already match |
| `meta_volcano` | `volcano` | `gene_id`, `symbol`, `meta_effect_log2fc`, `meta_log2fc_mean`, `meta_log2fe_mean`, `meta_pvalue_fisher`, `meta_fdr_fisher`, `meta_pvalue_stouffer`, `meta_pvalue_re`, `meta_found_in` | `p_col`, `x_col`, thresholds; send pooled log2FC and meta P as `log2FC`, `padj` |

## B. Direct after a reshape

| Your plot_type | fig-atlas plot_type | Current data columns | Reshape / exporter action |
|---|---|---|---|
| `gene_expression_bar` | `bar_scatter` | gene label column (`gene_id`/`symbol`) + sample columns; group membership in `plot_params.sample_groups` | wide -> long: one row per (gene, sample group) with `symbol`, `group`, `value`; keep replicate-level rows for points |
| `concordance_summary` | `bar_scatter` | `concordance` category column | count rows per category -> `symbol`=category, `value`=count |
| `composition` | `stacked_bar` | `cell_type`, `PropMean.<condition>` columns, `prop_ratio`, `pvalue`, `fdr` | wide -> long: one row per (condition, cell type) with `category`, `part`, `count` (or proportion) |
| `annotation_comparison` | `cross_condition_dotplot` | `dataset`, `annotation`, `log2fc`, `adj_pvalue` (long) | rename: `annotation` -> `GO Term`, `dataset` -> `Condition`, signed `-log10(adj_pvalue)` -> `Signed -log10(FDR)` |

## C. Needs a contract or renderer on the fig-atlas side first

Sample tables are in `samples/`.

| Your plot_type | Current data columns | Current measures / roles | Sample |
|---|---|---|---|
| `go_dot` | `term_id`, `description`, `ontology`, `gene_ratio`, `bg_ratio`, `pvalue`, `fdr`, `qvalue`, `gene_count`, `gene_symbols`, `fold_enrichment`, `direction`, `gene_set` | x = Gene Ratio / Fold Enrichment; size = Gene Count / Gene Ratio / Fold Enrichment; colour = FDR | `samples/go_dot.csv` |
| `expression_dot` | `gene_id`, `gene_name`, `cell_type`, `mean_expression`, `pct_expressing`, `n_cells` | row = gene, column = cell type; size = pct; colour = mean | `samples/expression_dot.csv` |
| `genomic_distribution` | `peak_id`, `annotation` (optional `log2fc`, `adj_pvalue`) | count of peaks per annotation category | `samples/genomic_distribution.csv` |
| `concordance_heatmap` | `symbol`, `rna_log2fc`, `atac_log2fc_mean`, `concordance`, `rna_padj`, `atac_padj`, `peak_count` | rows = genes; columns = RNA/ATAC log2FC; category strip = concordance | `samples/concordance_heatmap.csv` |
| `quadrant` | `symbol`, `rna_log2fc`, `atac_log2fc_mean`, `concordance`, `rna_padj`, `peak_count` | x = ATAC log2FC, y = RNA log2FC; colour = concordance; optional cut-off lines | `samples/quadrant.csv` |
| `integrated_volcano` | `symbol`, `rna_log2fc`, `rna_padj`, `concordance`, `peak_count` | x = RNA log2FC, y = -log10(RNA padj); colour = concordance; size = peak count | `samples/integrated_volcano.csv` |
| `upset` | `dataset`, `item` (long membership) | one row per (set, item); intersections computed by the renderer | `samples/upset.csv` |
| `go_comparison_dot` | wide: `term_id`, `description`, `ontology`, `<dataset>_fe`, `<dataset>_fdr`, `<dataset>_gene_count` | colour = fold enrichment; size = gene count; filter = FDR; one column group per dataset | `samples/go_comparison_dot.csv` |

## Questions for fig-atlas

1. For `go_dot`, should colour be FDR and size be Gene Ratio, or the reverse?
2. For `expression_dot`, should the contract use `dot_matrix` with row/column/size/colour roles?
3. For `genomic_distribution`, do you prefer a pie or a stacked share bar?
4. For `concordance_heatmap`, is the category strip required, or optional?
5. For `quadrant`, should cut-off lines be part of the contract or config?
6. For `integrated_volcano`, can `threshold_scatter` be extended with colour/size roles?
7. For `upset`, should we wait for a renderer or provide a two-set Euler fallback?
8. For `go_comparison_dot`, do you prefer the wide table above or a long table per dataset?
