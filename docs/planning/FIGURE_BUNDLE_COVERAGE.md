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
| Bundle-ready with dedicated script builder | 29 plot types | See §4 |
| Missing bundle context / builder | 0 figures | See §5 |
| Ambiguous / legacy | 2 | See §6 |
| Metadata contract gaps | 4 items | See §7 |

## 4. Bundle-ready figures

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

## 5. Missing bundle coverage

None. All user-facing `BasePlotDialog` subclasses now have a bundle context and
a dedicated script builder. The coverage regression test enforces this for
future dialogs.

## 6. Ambiguous / legacy

- `GONetworkDialog` currently exposes a bundle for the **cluster summary dot
  plot** (`go_cluster_dot`). The network tab is disabled in the current UI, so
  this is consistent; if the network tab is re-enabled, add a separate
  `go_network` bundle type.
- `VolcanoPlotDialog` and `HeatmapDialog` are legacy wrapper dialogs. The
  embedded `VolcanoPlotWidget` / `HeatmapWidget` already have bundle contexts;
  the wrappers are not the primary UI path.

## 7. Metadata contract gaps

`metadata/metadata.yaml` currently lacks or misstates:

1. `output_formats` — should list the formats actually written.
2. `output_files` — currently lists `outputs/figure.*`, while the manifest also
   writes `outputs/<source_stem>.*`; align to the real files.
3. `panel_notes` — external pipeline needs panel-level interpretation; map from
   `context["panel_notes"]` or `notes`.
4. environment info — Python version, platform, and app version; git commit is
   optional.
5. `statistics_tables` — currently always lists `inputs/statistics.csv` even
   when no statistics file was written.

## 8. Recommended order

1. Keep the coverage regression test green for new dialogs.
2. Validate `metadata.yaml` against the external contract.
3. Run every generated `scripts/figure.py` headlessly in CI or a release check.
4. Hand a sample bundle to the external figure-atlas pipeline for review.

## 9. Related documents

- [Figure quality / reproducibility plan](FIGURE_QUALITY_REPRODUCIBILITY_PLAN.md)
- [External pipeline requirements](external_pipeline_requirements.md)
- [Archived bundle export implementation](archive/BUNDLE_EXPORT_IMPLEMENTATION.md)
