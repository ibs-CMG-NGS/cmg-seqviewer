# Reply to the 2026-10-24 handoff

- **Date**: 2026-10-24
- **About**: `cmg_fig_atlas_bundle_samples_2026-10-24.zip`
- **From**: fig-atlas (bundle contract owner)
- **Scope**: review of the revised bundles, four remaining items, and answers to the open questions in §0.1 of your checklist

## What we verified

- `SHA256SUMS`: 48 of 48 entries match.
- `fa bundle check` on all seven bundles, run again on our side: **7/7 ok, 0 warnings, 0 errors**.
  The contract each bundle matched is the one we expected (see the table below).
- The bundle shape is now the contract shape: `inputs/data.csv` + `metadata/metadata.yaml` only,
  no drawing script, one output set, `plot_type` a registered renderer name, `figure_number` empty,
  `claim_boundary` a sentence about the panel, `environment` with the matplotlib version.
- We accept `statistics_tables: []` for these samples, given your statement that the panels draw
  design cut-off lines and not test marks.

| Bundle | fig-atlas plot_type | Contract |
|---|---|---|
| 01_padj_histogram | `histogram` | core.histogram |
| 02_tss_distance | `histogram` | core.histogram |
| 03_motif_enrichment | `motif_dotplot` | atac_feature.motif_enrichment |
| 04_tf_footprint | `threshold_scatter` | core.threshold_scatter |
| 05_comparison_dot | `cross_condition_dotplot` | cross_condition.enrichment |
| 06_chromvar | `volcano` | de_go.volcano |
| 07_expression_distribution | `violin` | core.violin |

## Four items to change before the next delivery

1. **06_chromvar: remove `x_col`, `y_col`, `effect_col`, `sig_col` from `plot_params`.**
   `volcano` is not a threshold scatter: it reads the contract columns `log2FC` and `padj` itself
   and takes only the thresholds (`log2fc_threshold`, `padj_threshold`) and styling from
   `plot_params`. The four keys are not read; `fa lint` reports them as unread keys after ingest.
2. **01_padj_histogram: add `bins: 50`.**
   The viewer draws 50 bins; without the key fig-atlas uses its default of 20, so the panel does not
   match the reference PNG.
3. **07_expression_distribution: switch to the grouped violin.**
   Send `x_col: cell_type`, `y_col: mean_expression`, `hue_col: condition`,
   `hue_order: [Control, Treated]` and drop the combined `category` column (or keep it as an
   unused extra). The x axis then shows one tick per cell type and the conditions get a legend,
   which is what the viewer draws. The combined category works but prints `CT_A || Control` as
   the tick label and has no legend.
4. **03_motif_enrichment: confirm what the colour means.**
   `value_col: log_pvalue` and `p_col: neg_log10_p` both carry significance, while the contract
   describes `value_col` as log2 fold enrichment. It draws, but the colour bar will be labelled as
   enrichment. Either send a log2 enrichment column for the colour, or tell us the colour is
   significance and we will document that use (and its label) for this plot type.

## Answers to the open questions in §0.1

- **Switch bundle 07 to grouped violins?** Yes. `hue_col` is in the package:
  one violin per category and hue value, side by side inside the category, with `hue_order`,
  `hue_colors` and `hue_labels` and a hue legend. Without `hue_col` the renderer draws exactly as
  before.
- **Identity line for 04?** `show_identity_line` is in the package (with `identity_line_color`,
  `_style`, `_width`, `_alpha`); it draws y = x under the points. It is not in a release yet: use
  the development branch until the next version is tagged.
- **The other 22 internal plot types.** Send the list of names (and one sample table per type, or a
  column-role table). We will return a mapping table: fig-atlas `plot_type`, the columns the
  contract reads, and any reshape the exporter must do, as we did for these seven.

## Minor

- The bundle tree in §1 of the checklist still lists `scripts/figure.py` and
  `outputs/figure.*`. The delivery no longer contains either; update the tree so the document
  matches the ZIP.
- The console encoding issue you hit (`fa verify` needs `PYTHONIOENCODING=utf-8` on Windows because
  the report contains a Unicode minus) is a fig-atlas CLI issue, not a bundle issue. We have noted
  it.
