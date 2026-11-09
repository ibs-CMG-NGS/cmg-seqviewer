# Response to the 2026-11-09 mapping decision

- **Date**: 2026-11-09
- **About**: `FIGURE_ATLAS_REPLY_2026-11-09-2.md`
- **From**: cmg-seqviewer
- **Scope**: all 22 mappings implemented, 22 sample bundles, validation, and two open questions

## 1. Implementation

All 22 mappings are now in `export_fig_atlas_bundle()`:

- **Direct**: `volcano`, `heatmap`, `ma`, `pca`, `go_bar`, `go_dot`,
  `go_cluster_dot`, `count_summary`, `venn`, `multi_group_heatmap`,
  `meta_volcano`
- **Reshape**: `gene_expression_bar`, `concordance_summary`, `composition`,
  `annotation_comparison`
- **New contract/renderer**: `expression_dot` (`dot_matrix`), 
  `genomic_distribution` (`bar_scatter`), `concordance_heatmap` (`heatmap`),
  `quadrant` (`group_scatter`), `integrated_volcano` (`threshold_scatter`),
  `upset`, `go_comparison_dot` (`dot_matrix`)

The exact column roles are recorded in `COLUMN_ROLES.md`.

## 2. Sample bundles

`cmg_fig_atlas_bundle_samples_2026-11-09/` contains one minimal bundle for each
of the 22 new types (synthetic data only, no scripts/outputs).

## 3. Validation

- `fa bundle check`: **22/22 ok, 0 warnings, 0 errors**
- `fa ingest bundle`: **22/22** into a temporary project
- `fa build --preflight` / `fa build`: **ALL 1 PROJECT(S) PASSED**
- `fa verify`: **PASS**
- `fa lint`: 0 likely typos; **3 unread keys**:
  `plots.go_cluster_dot.direction_colors` (3 keys)

The preflight warnings are from the deliberately dense 22-panel test layout
(panel intrusion / small print), not from the bundle contracts.

The 3 unread `go_cluster_dot.direction_colors` keys are added by `fa ingest`
from the renderer defaults; our `go_cluster_dot` metadata has no such key. Please
confirm whether that is a known fig-atlas default.

## 4. Open questions

1. **PCA orientation**: our table is gene × sample (the orientation
   `fig_atlas/renderers/pca.py` expects before its internal transpose). The
   mapping reply said "transpose to one row per sample". We kept gene × sample
   and the build passes; please confirm the intended orientation.
2. **`go_cluster_dot.direction_colors`**: see above.

## 5. Delivery

- Bundle samples: `cmg_fig_atlas_bundle_samples_2026-11-09/`
  (`cmg_fig_atlas_bundle_samples_2026-11-09.zip`)
- Mapping table: `cmg_fig_atlas_mapping_2026-11-09/COLUMN_ROLES.md`
- This response: `FIGURE_ATLAS_RESPONSE_2026-11-09-2.md`
