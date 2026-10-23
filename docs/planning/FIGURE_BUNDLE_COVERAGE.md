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
| Bundle-ready with dedicated script builder | 23 plot types | See §4 |
| Missing bundle context / builder | 6 figures | See §5 |
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

| Figure | File | Current state | Needed |
|---|---|---|---|
| P-value histogram | `src/gui/visualization_dialog.py::PadjHistogramDialog` | No bundle button/context | Pure renderer + `padj_histogram` builder |
| Comparison dot plot | `src/gui/visualization_dialog.py::DotPlotDialog` | No bundle button/context | Pure renderer + `comparison_dot` builder |
| chromVAR TF activity | `src/gui/chromvar_dialog.py::ChromVARDialog` | No bundle button/context | Renderer for volcano/scatter/heatmap modes + builder |
| TF motif enrichment | `src/gui/motif_enrichment_dialog.py::MotifEnrichmentDialog` | No bundle button/context | Single/comparison renderer + builder |
| TF footprint | `src/gui/tf_footprint_dialog.py::TFFootprintDialog` | No bundle button/context | Scatter renderer + builder |
| TSS distance | `src/gui/tss_distance_dialog.py::TSSDistanceDialog` | No bundle button/context | Histogram renderer + builder |

These six are reachable from the GUI (`main_window.py`), so a user can create
the figure but cannot hand it off as a bundle.

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

1. Add bundle contexts and pure renderers for the six missing figures.
2. Harden `metadata.yaml` to match the external contract.
3. Add a coverage regression test that fails when a new `BasePlotDialog`
   subclass lacks `get_bundle_context()` and is not explicitly allowlisted.
4. Run every generated `scripts/figure.py` headlessly to verify reproduction.

## 9. Related documents

- [Figure quality / reproducibility plan](FIGURE_QUALITY_REPRODUCIBILITY_PLAN.md)
- [External pipeline requirements](external_pipeline_requirements.md)
- [Archived bundle export implementation](archive/BUNDLE_EXPORT_IMPLEMENTATION.md)
