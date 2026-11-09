# Response to the 2026-10-24 fig-atlas review

- **Date**: 2026-10-24
- **About**: `cmg_fig_atlas_bundle_samples_2026-10-24.zip`
- **From**: cmg-seqviewer
- **Scope**: four requested changes, validation results, and the remaining 22 plot-type mappings

## 1. Changes applied

1. **06_chromvar**
   - Removed `x_col`, `y_col`, `effect_col`, and `sig_col` from `plot_params`.
   - It now sends only `log2fc_threshold` and `padj_threshold`.
   - `fa lint` after a full build reports **0 unread keys**.

2. **01_padj_histogram**
   - Added `bins: 50` so the fig-atlas panel matches the viewer's reference.

3. **07_expression_distribution**
   - Switched to the grouped violin:
     `x_col: cell_type`, `y_col: mean_expression`,
     `hue_col: condition`, `hue_order: [Control, Treated]`.
   - The combined `category` column is no longer emitted.

4. **03_motif_enrichment**
   - The colour is **significance**, not log2 fold enrichment:
     `value_col: log_pvalue` (`-log10(p)`), `p_col: neg_log10_p` (`-log10(q)`).
   - Added `fc_min: 0`, `fc_max` from the data, and
     `colorbar_label: -log10(p)`.
   - Please document this use (and the colourbar label) for `motif_dotplot`.

## 2. Validation

- `fa bundle check`: **7/7 ok, 0 warnings, 0 errors**.
- `fa ingest bundle`: **7/7** into a temporary project.
- `fa build --preflight`: **ALL 1 PROJECT(S) PASSED**.
- `fa build`: **ALL 1 PROJECT(S) PASSED**.
- `fa lint`: **0 likely typos, 0 unread keys, 17 defaults**.
- `fa verify`: **PASS**.
  - Preflight warnings are only tick-label collisions from the deliberately
    dense 7-panel test layout.
  - On Windows, `fa verify` needs `PYTHONIOENCODING=utf-8` because the report
    contains a Unicode minus; this is a fig-atlas CLI issue.

## 3. Remaining 22 plot types

We need a fig-atlas mapping for these internal `plot_type`s:

```text
volcano
heatmap
ma
pca
go_dot
go_bar
go_comparison_dot
go_cluster_dot
genomic_distribution
gene_expression_bar
composition
expression_dot
quadrant
concordance_heatmap
concordance_summary
integrated_volcano
meta_volcano
count_summary
annotation_comparison
venn
upset
multi_group_heatmap
```

Some likely reuse existing contracts (`volcano`, `ma_plot`, `go_*`,
`count_summary`, `venn`, `multi_group_heatmap`), but we do not want to guess.
Please return the mapping table as before:

- fig-atlas `plot_type`
- columns the contract reads
- any reshape the exporter must do

If it helps, we can provide one synthetic sample table per type or a
column-role table. Please say which you prefer.

## 4. Documentation

- Updated the bundle tree in `FIGURE_ATLAS_HANDOFF_CHECKLIST.md` to remove
  `scripts/figure.py` and `outputs/figure.*`.
- The updated ZIP contains:
  `README.md`, `index.json`, `SHA256SUMS`,
  `FIGURE_ATLAS_HANDOFF_CHECKLIST.md`, `FIGURE_ATLAS_REPLY_2026-10-24.md`,
  `FA_BUNDLE_CHECK.txt`, and `FA_ACCEPTANCE.md`.
