# Reply to the 2026-10-24 response

- **Date**: 2026-11-09
- **About**: `cmg_fig_atlas_bundle_samples_2026-10-24.zip` (updated in place)
- **From**: fig-atlas (bundle contract owner)
- **Scope**: four changes verified, the motif colour documented, and a first mapping for the 22 remaining plot types

## 1. Verification

We re-ran the checks on the updated folder:

- `fa bundle check` on all seven bundles: **7/7 ok, 0 warnings, 0 errors**, each against the
  expected contract.
- The four changes are in place: 01 has `bins: 50`; 06 sends only the two thresholds; 07 uses
  `hue_col: condition` with `hue_order: [Control, Treated]`; 03 carries the significance colour with
  `fc_min`, `fc_max` and `colorbar_label: -log10(p)`.
- We take your `fa lint` result (0 unread keys) as given; it matches the change in 06.

## 2. Motif colour (03)

`motif_dotplot` supports this use: `value_col` is the colour, `p_col` is the dot size, and the
colourbar takes its title from `colorbar_label`. We added a note to
`fig_atlas_omics/contracts/atac_feature_bundle_contract.md`: the contract's default is log2 fold
enrichment, but a bundle whose colour is significance sends `-log10(p)` and sets
`colorbar_label` and the `fc_min`/`fc_max` range accordingly. Your sample is the example.

## 3. The 22 remaining plot types

**What we would like:** the **column-role table** for all 22 types, plus **one synthetic sample
table** for the eight whose shape the name does not settle (listed in Table C). The column-role table
is enough for the rest; a sample is faster than prose where a plot is not a standard shape.

The table below separates what can go today from what needs work on our side first. "Contract
reads" are the column names fig-atlas reads; your exporter renames to them.

### A. Direct: the contract exists and the shape matches

| Your plot_type | fig-atlas plot_type | Contract reads | Exporter action |
|---|---|---|---|
| `volcano` | `volcano` | `log2FC`, `padj` | rename to these names |
| `heatmap` | `heatmap` | `label_col` + numeric sample columns (`min_numeric: 2`) | one row per row label |
| `ma` | `ma_plot` | `baseMean`, `log2FoldChange`, `padj` | rename |
| `pca` | `pca` | numeric sample columns (`min_numeric: 3`) | one row per sample |
| `go_bar` | `go_bar` | `description` + term columns | rename |
| `go_cluster_dot` | `go_cluster_dot` | `description`, `cluster_id`, term columns | rename |
| `count_summary` | `count_summary` | `dataset`, `log2fc`, `adj_pvalue` | rename |
| `venn` | `venn` | `dataset`, `item` | long format, one row per (set, item) |
| `multi_group_heatmap` | `multi_group_heatmap` | `gene_label` + numeric sample columns | rename |
| `meta_volcano` | `volcano` | `log2FC`, `padj` | send the pooled log2FC and meta P under these names |

### B. Direct after a reshape

| Your plot_type | fig-atlas plot_type | Contract reads | Exporter action |
|---|---|---|---|
| `gene_expression_bar` | `bar_scatter` | `symbol`, `group`, `value` | wide -> long: one row per (gene, sample group); points come from the replicates |
| `concordance_summary` | `bar_scatter` | `symbol`, `value` | wide -> long: one row per category, count as `value` |
| `composition` | `stacked_bar` | `category`, `part`, `count` | wide -> long, one row per (group, part) |
| `annotation_comparison` (long form) | `cross_condition_dotplot` | `GO Term`, `Condition`, `Signed -log10(FDR)` | rename; your `log2fc`/`adj_pvalue` become the signed value |

### C. Needs a contract or a renderer on our side first

These have no ingestable contract today, or the shape is not drawn yet. Send the columns and, for
each, one synthetic table; we will say which contract we add (or which renderer) before you change
the exporter.

| Your plot_type | Situation | What we need from you |
|---|---|---|
| `go_dot` | renderer exists, **no bundle contract** | column names (term, Gene Ratio, Fold Enrichment, Gene Count, adjusted P) |
| `expression_dot` | `dot_matrix` renderer exists, **no bundle contract** | columns for row, column, size and colour |
| `genomic_distribution` | pie; **no pie renderer** | annotation counts; decide pie or a stacked share bar |
| `concordance_heatmap` | `signed_heatmap` is close but has no category strip | columns, and whether the strip is required |
| `quadrant` | `group_scatter` plots the two axes but has no cut-off lines | columns and the category rules |
| `integrated_volcano` | needs colour by concordance class and size by peak count; `threshold_scatter` does neither | columns |
| `upset` | **no UpSet renderer** (`two_set_euler` handles two sets only) | membership table columns; decide new renderer or a two-set fallback |
| `go_comparison_dot` | no direct contract; `dot_matrix` or `cross_condition_dotplot` may fit | columns and which measures set colour and size |

## 4. Summary of what we will do

- Add bundle contracts (and, where missing, renderers) for the types in Table C once the columns
  arrive, in the order you need them. `go_dot` and `expression_dot` are small (the renderers exist);
  `upset`, `quadrant` and `integrated_volcano` are new renderers and will take longer.
- Keep the seven confirmed bundles as the reference set; no change is needed to them.
