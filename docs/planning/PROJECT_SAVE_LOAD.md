# Project Save / Load (`.seqproj`)

**Status**: Re-generation model — comparison & integration replay implemented (2026-07).

## Model: recipe, not data

A `.seqproj` file is a small JSON **recipe**, not a data container. It stores the
source of each dataset (file path or DB id) plus the **parameters** used to derive
every sheet. On open, the app reloads the sources and **re-runs** those steps to
rebuild the session.

- **Save** module: [`src/utils/project_io.py`](../../src/utils/project_io.py)
  (`ProjectIO.build_spec` / `save` / `load`).
- **Restore** driver: `MainWindow._open_project_path` in
  [`src/gui/main_window.py`](../../src/gui/main_window.py).

### Why re-generation (vs. embedding the data)

| | Re-generation (chosen) | Embed data (parquet) |
|---|---|---|
| Project file size | a few KB | MB–hundreds of MB |
| Memory at rest | same as a normal session | same |
| Open cost | reload sources + recompute recipes (one-time, bounded) | read parquet only |
| Requirement | **source files must remain available** | self-contained |

Re-generation is light on disk/memory; the only cost is a one-time recompute at
open (equal to the work of running the analysis once). The real trade-off is
**robustness**: it depends on the source files staying put and on deterministic
recompute.

## What is saved & restored

| Item | Saved as | Restored by | Status |
|---|---|---|---|
| Whole dataset (file) | relative `file_path` | `presenter.load_dataset` | ✅ |
| Whole dataset (DB) | `source:"database"` + `db_dataset_id` | `db_manager.load_dataset` | ✅ |
| Filtered sheet | `filter_params` | `FilterCriteria.from_dict` → `apply_filter` | ✅ |
| **Comparison sheet** | `comparisons[]` recipe `{dataset_names, comparison_type}` | `_perform_basic_comparison` | ✅ |
| **RNA–ATAC integration** | dataset `source:"integration"` + `integration_recipe` | `presenter.integrate_datasets(**recipe)` | ✅ |
| Volcano / Heatmap plot tab | `plot_type` + `plot_params` | `VolcanoPlotWidget` / `HeatmapWidget` + `_pin_plot_to_tab` | ✅ |
| Active tab index | `ui_state.active_tab_index` | `setCurrentIndex` | ✅ |

**Recipe capture mechanism**: creation handlers set `self._pending_sheet_recipe`
before building a `comparison` / `clustered` / `integration` tab;
`_create_data_tab` stamps it onto that tab's `comparison_params`, which
`build_spec` then serializes. Integration results (file-less MULTI_OMICS
datasets) instead carry `metadata['integration_recipe']`, saved with
`source:"integration"`.

**Restore ordering**: file/DB datasets load first; integration results are
deferred and replayed once their RNA/ATAC sources exist; comparisons replay last
(after all sources are present). Sub-sheets (filtered/plot) of any dataset —
including regenerated integration results — go through the shared
`_replay_dataset_sheets()` helper.

## What is NOT (yet) restored automatically

Reported in the **Project Restore — Partial** dialog (`unrestorable_generated`),
so nothing is dropped silently:

- **GO Term clustering results** (`clustered` sheets). The `cluster_id` pipeline
  (gene-set build → `GOClustering.cluster_terms` → min/max-size filtering →
  labeling) is entangled in the clustering dialog worker; faithful replay needs a
  pure-function extraction first. Recreate via **Analysis → Cluster GO Terms**.
- **Cross-species harmonized** and **meta-analysis** results (file-less generated
  datasets with no recipe yet).

Other notes:

- Only **Volcano** and **Heatmap** can be pinned as persistent tabs, so only those
  plots are part of a saved session. Every other visualization (MA, PCA, GO dot/bar,
  Quadrant, Meta Volcano, Venn, UpSet, …) is a modal dialog and is not saved.
- Sheets are **recomputed from the current source files**, not stored verbatim —
  if a source file changed since saving, restored sheets reflect the new file.
  If a source file is missing, that dataset and everything derived from it is
  skipped (listed under "source files not found").
- Restored plots are drawn from the parent dataset's full table.

## Deferred / roadmap

- **GO-clustering replay** — extract the clustering pipeline to a pure function
  (like the `src/plots/*` render extraction), capture `{source recipe, similarity,
  min_size, max_size}`, replay on restore.
- **Lazy regeneration** — on open, create tab placeholders and recompute a sheet
  only when its tab is first activated, to keep open fast for heavy projects.
  (Current eager replay is fine for the common case; comparisons/filters are
  seconds-scale.)
- **Harmonized / meta result** recipes — same recipe-capture pattern as
  comparison/integration.

## Format (`format_version` 1.0)

```jsonc
{
  "format_version": "1.0",
  "created_at": "…",
  "datasets": [
    { "name": "DE_A", "type": "differential_expression", "source": "file",
      "file_path": "data/DE_A.xlsx",
      "sheets": [
        { "type": "filtered", "label": "…", "filter_params": { … } },
        { "type": "plot", "label": "Volcano", "plot_type": "volcano", "plot_params": { … } }
      ] },
    { "name": "RNA + ATAC", "source": "integration", "file_path": "",
      "integration_recipe": { "rna_name": "…", "atac_name": "…", "method": "nearest_gene",
                              "tss_window": 2000, "rna_padj": 0.05, "rna_lfc": 1.0,
                              "atac_padj": 0.05, "atac_lfc": 1.0 },
      "sheets": [ … ] }
  ],
  "comparisons": [
    { "label": "Comparison: Statistics (2 datasets)",
      "comparison_params": { "kind": "comparison",
                             "dataset_names": ["DE_A", "DE_B"],
                             "comparison_type": "statistics" } }
  ],
  "ui_state": { "active_tab_index": 0, "tree_expanded_datasets": [] }
}
```
