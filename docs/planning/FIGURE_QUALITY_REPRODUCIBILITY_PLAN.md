# Publication-Quality Figure & Bundle Handoff Plan

- **Status (2026-11-10)**: P1/P4 and the fig-atlas handoff are complete. All 29
  internal plot types have a fig-atlas mapping; the 22 new sample bundles pass
  `fa bundle check` 22/22 and fig-atlas has accepted the contract. Remaining work
  is preparing real project bundles and the FigureSpec in cmg-figure.
- **Code baseline**: v1.4.1
- **Coverage audit**: [FIGURE_BUNDLE_COVERAGE.md](FIGURE_BUNDLE_COVERAGE.md)
- **Historical details**:
  [P1 implementation](archive/FIGURE_QUALITY_P1_IMPLEMENTATION.md) ·
  [bundle implementation](archive/BUNDLE_EXPORT_IMPLEMENTATION.md)

---

## 1. Role split

### Viewer (cmg-seqviewer)

Produce a **reproducible panel bundle** for every user-facing figure:

- PNG / PDF / SVG panel output
- standalone `scripts/figure.py`
- input data and statistics
- `metadata/metadata.yaml` + `manifest.json`
- stable figure slug / source stem

### fig-atlas (foundation) and cmg-figure (project layer)

**fig-atlas** owns the foundational contract:

- bundle ingest and validation
- `FigureSpec` schema
- publish/verify workflow
- atlas-level structure

**cmg-figure** uses fig-atlas for actual research-project figures:

- figure numbers and panel labels (a/b/c)
- project-specific panel grouping
- journal page size, margins, and column width
- figure-level typography, legends, and annotations
- final submission layout and export

### Out of scope

- in-app multi-panel assembly
- journal-specific final sizing
- pixel-perfect WYSIWYG editing
- reproducing a full manuscript figure from scratch inside the viewer

This boundary keeps the viewer focused on **reproducible panel generation** and
the external pipeline focused on **figure assembly and publication layout**.

## 2. Current assets

| Asset | Status | Location |
|---|---|---|
| Central figure theme / export / style panel | ✅ P1 (2026-06-05) | `src/utils/figure_theme.py`, `figure_export.py`, `gui/widgets/figure_style_panel.py` |
| Reproducible bundle export + script generation | ✅ P4 (2026-07-09) | `src/utils/figure_bundle_export.py` |
| Bundle button in `BasePlotDialog` | ✅ | `src/gui/base_plot_dialog.py` |
| Dedicated script builders | ✅ 29 plot types | `figure_bundle_export.py` |
| Coverage audit | ✅ 2026-10-23 | [FIGURE_BUNDLE_COVERAGE.md](FIGURE_BUNDLE_COVERAGE.md) |

## 3. Active phase — Bundle handoff coverage and contract review (P2)

**Goal:** every figure reachable from the GUI can be exported as a bundle that
the external pipeline can ingest without manual repair.

### 3.1 Coverage status

All user-facing figure dialogs now have an internal bundle context and a
dedicated script builder. The audit covers 29 plot types; details are in
[FIGURE_BUNDLE_COVERAGE.md](FIGURE_BUNDLE_COVERAGE.md).

fig-atlas contract mapping is now implemented for all 29 internal plot types:
the seven earlier sample shapes (`histogram` x2, `motif_dotplot`,
`threshold_scatter`, `cross_condition_dotplot`, `volcano`, `violin`) and the 22
types in [FIG_ATLAS_COLUMN_ROLES.md](FIG_ATLAS_COLUMN_ROLES.md). The 22 new
sample bundles pass `fa bundle check` **22/22**, ingest **22/22**, and pass
`fa build --preflight` / `fa verify`. Remaining open items: confirm the PCA
gene × sample orientation and the `go_cluster_dot.direction_colors` lint key
reported by `fa ingest`.

### 3.2 Work items

- Extract each dialog's plotting logic into a Qt-free renderer under
  `src/plots/`.
- Add `get_bundle_context()` to each dialog.
- Add a dedicated `_build_*_plot_script()` branch (no generic fallback for
  pipeline handoff).
- Ensure `inputs/data.csv` contains the exact table used by the renderer.
- Add a coverage regression test:
  every `BasePlotDialog` subclass must have `get_bundle_context()` or be in an
  explicit allowlist.

### 3.3 Metadata contract hardening

Update `metadata.yaml` / `manifest.json` to match the external contract:

- `output_formats`: formats actually written
- `output_files`: real `outputs/<source_stem>.*` paths
- `panel_notes`: panel-level interpretation note
- environment: Python version, platform, app version (git commit optional)
- `statistics_tables`: only include files that exist

## 4. Optional phase — Batch panel export (P3)

If needed after P2:

- select multiple figures and export **separate** bundles in one action
- deterministic folder names and a batch index
- still panel-level only; no multi-panel composition

Multi-panel assembly remains delegated to the external pipeline.

## 5. Validation

- Every bundle contains PNG/PDF/SVG, script, data, metadata, and manifest.
- `python scripts/figure.py` runs headlessly and reproduces the panel.
- `metadata.yaml` passes the external contract check.
- Coverage test fails only for new, unlisted gaps.
- Existing bundle tests stay green (`test/test_figure_bundle_export.py`).

## 6. Next actions

1. Validate all generated scripts and the metadata contract.
2. Hand a sample bundle to the external pipeline for contract review.
3. Keep the coverage regression test green for new figures.
4. Run a release-time headless bundle validation.


## 7. Related documents

- [Figure bundle coverage audit](FIGURE_BUNDLE_COVERAGE.md)
- [Figure-atlas handoff checklist](FIGURE_ATLAS_HANDOFF_CHECKLIST.md)
- [External pipeline requirements](external_pipeline_requirements.md)
- [Expression Distribution plan](EXPRESSION_DISTRIBUTION_PLAN.md)
