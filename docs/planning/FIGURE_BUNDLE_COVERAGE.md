# Figure Bundle Coverage Audit

- **Date**: 2026-10-23
- **Code baseline**: v1.4.1
- **Purpose**: verify that every user-facing figure can be handed off to the
  external figure-atlas / publication-layout pipeline as a reproducible bundle.

## 1. Scope

The viewer is responsible for **panel-level** reproducibility:

- PNG/PDF/SVG output
- standalone regeneration script
- input data and statistics
- metadata and manifest

The external figure-atlas pipeline is responsible for **figure-level**
publication work:

- final journal size and margins
- multi-panel composition (a/b/c)
- figure-level typography and annotations
- final submission layout

In-app multi-panel composition is therefore **not** part of this plan.

## 2. Bundle contract

`export_figure_bundle()` currently produces:

```text
<figure>_bundle/
├── scripts/figure.py
├── inputs/data.csv
├── inputs/statistics.csv       (optional)
├── outputs/figure.png/.pdf/.svg
├── outputs/<source_stem>.png/.pdf/.svg
├── metadata/metadata.yaml
└── manifest.json
```

The external contract is documented in
[external_pipeline_requirements.md](external_pipeline_requirements.md).

## 3. Coverage summary

| Status | Count | Notes |
|---|---:|---|
| Internal bundle-ready (script builder) | 29 plot types | See §4 |
| fig-atlas contract mappings | 7 sample shapes | See §5 |
| Ambiguous / legacy | 2 | See §6 |
| Open contract items | 2 | See §7 |

## 4. Bundle-ready figures (internal cmg-seqviewer bundle)

These have `get_bundle_context()` and a dedicated `_build_*_plot_script()`
branch (no generic fallback):

| Plot type | Figure |
|---|---|
| `volcano` | Volcano plot |
| `heatmap` | Heatmap / expression summary heatmap |
| `ma` | MA plot |
| `pca` | PCA |
| `padj_histogram` | P-value histogram |
| `comparison_dot` | Comparison dot plot |
| `tss_distance` | TSS distance |
| `motif_enrichment` | TF motif enrichment |
| `tf_footprint` | TF footprint activity |
| `chromvar` | chromVAR TF activity |
| `go_dot` | GO/KEGG dot plot |
| `go_bar` | GO/KEGG bar chart |
| `go_comparison_dot` | GO/KEGG comparison dot plot |
| `go_cluster_dot` | GO cluster summary dot plot |
| `genomic_distribution` | Genomic distribution |
| `gene_expression_bar` | Gene expression bar + scatter |
| `composition` | Cell-type composition |
| `expression_dot` | Gene × cell-type dot plot |
| `expression_distribution` | Gene expression distribution |
| `quadrant` | RNA vs ATAC quadrant |
| `concordance_heatmap` | Concordance heatmap |
| `concordance_summary` | Concordance summary |
| `integrated_volcano` | Integrated volcano |
| `meta_volcano` | Meta volcano |
| `count_summary` | DE/DA count summary |
| `annotation_comparison` | Genomic annotation comparison |
| `venn` | Venn diagram |
| `upset` | UpSet plot |
| `multi_group_heatmap` | Multi-group heatmap |

## 5. fig-atlas contract coverage

Internal bundle coverage (29 plot types) is complete. fig-atlas contract
mapping is implemented for all 29 types: the seven earlier sample shapes below
plus the 22 types in [FIG_ATLAS_COLUMN_ROLES.md](FIG_ATLAS_COLUMN_ROLES.md).
The 22 new sample bundles pass `fa bundle check` **22/22**.

| cmg plot_type | fig-atlas plot_type |
|---|---|
| `padj_histogram` | `histogram` |
| `tss_distance` | `histogram` |
| `motif_enrichment` | `motif_dotplot` |
| `tf_footprint` | `threshold_scatter` |
| `comparison_dot` | `cross_condition_dotplot` |
| `chromvar` | `volcano` |
| `expression_distribution` | `violin` |

`fa bundle check` passes **7/7** for the updated samples. The remaining 22
internal plot types still need a fig-atlas contract mapping before they can be
handed off.

## 5.1 Contract coverage vs visual fidelity

All 29 viewer plot types have a fig-atlas **contract mapping**, and the 22 new
sample bundles pass `fa bundle check`. That is not the same as pixel-identical
reproduction: some mappings use the closest existing fig-atlas shape and reduce
viewer-specific options.

| Viewer figure | Mapping | Fidelity note |
|---|---|---|
| `genomic_distribution` | `stacked_bar` | viewer pie -> stacked share bar |
| `concordance_heatmap` | `heatmap` | concordance category strip is not drawn |
| `composition` | `stacked_bar` | viewer ratio/means modes are reduced to the stacked mean/ratio shape |
| `annotation_comparison` | `cross_condition_dotplot` | viewer counts/proportion/enrichment modes are not all represented |
| `gene_expression_bar` | `bar_scatter` | significance brackets require a p-value column; not automatic |
| `comparison_dot` | `cross_condition_dotplot` | gene comparison uses the GO-style shape; Gene Ratio is a proxy |
| `motif_enrichment` | `motif_dotplot` | viewer bar chart becomes a motif dot plot; colour is significance |
| `chromvar` | `volcano` | only the volcano mode is mapped; scatter/heatmap modes are not |
| `go_comparison_dot` | `dot_matrix` | top-N/min-dataset/FDR filtering may differ from the viewer |

The remaining mapped types (histograms, violin, volcano, MA, PCA, GO dot/bar/
cluster, count summary, Venn, UpSet, multi-group heatmap, expression dot, etc.)
are close to the viewer shape.

## 6. Ambiguous / legacy

- `GONetworkDialog` currently exposes a bundle for the **cluster summary dot
  plot** (`go_cluster_dot`). The network tab is disabled in the current UI, so
  this is consistent; if the network tab is re-enabled, add a separate
  `go_network` bundle type.
- `VolcanoPlotDialog` and `HeatmapDialog` are legacy wrapper dialogs. The
  embedded `VolcanoPlotWidget` / `HeatmapWidget` already have bundle contexts;
  the wrappers are not the primary UI path.

## 7. fig-atlas contract notes / open items

Resolved by the fig-atlas replies and the `export_fig_atlas_bundle()` path:

- `plot_type` uses registered fig-atlas names (see §5).
- `plot_params` carries the column roles and thresholds.
- `figure_number` is left empty; the project layer assigns it.
- `panel_notes` is a string (one bundle = one panel).
- `statistics_tables: []` is accepted when only design cut-off lines are drawn.
- The fig-atlas bundle writes one `outputs/<source_stem>.*` set and no script.
- `claim_boundary` is a sentence about what the panel does and does not support.
- Histogram bundles send the viewer's bin count (`bins: 50`).
- chromVAR `volcano` sends only thresholds (no threshold-scatter roles).
- Expression Distribution uses `hue_col: condition` for grouped violins.
- Motif colour is significance (`-log10(p)`), with an explicit colourbar label.
- All 22 additional types are mapped; `fa bundle check` is **22/22** on the new
  sample bundles.
- PCA orientation is confirmed (gene × sample; the renderer transposes
  internally).
- `go_cluster_dot.direction_colors` is a renderer default reported as
  `not_reached`, not a bundle problem.

No open fig-atlas contract items remain. The next step is real project bundles
in cmg-figure.

## 8. Recommended order

1. Keep the coverage regression test green for new dialogs.
2. Use the 22 synthetic bundles as the frozen contract reference set.
3. Prepare real project bundles and the project-level FigureSpec in cmg-figure.
4. Run the same check/ingest/build/verify cycle in the project environment.

## 9. Related documents

- [Figure quality / reproducibility plan](FIGURE_QUALITY_REPRODUCIBILITY_PLAN.md)
- [External pipeline requirements](external_pipeline_requirements.md)
- [Archived bundle export implementation](archive/BUNDLE_EXPORT_IMPLEMENTATION.md)
