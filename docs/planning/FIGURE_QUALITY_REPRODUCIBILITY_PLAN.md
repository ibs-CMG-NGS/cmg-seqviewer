# Publication-Quality Figure & Bundle Handoff Plan

- **Status (2026-10-23)**: scope revised. P1 theme/export and P4 bundle export
  are implemented. Active work is **bundle handoff coverage**; final
  publication size/layout is delegated to the external figure-atlas pipeline.
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

### External figure-atlas pipeline

Own the final publication work:

- journal page size, margins, and column width
- multi-panel composition (a/b/c)
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
| Dedicated script builders | ✅ 23 plot types | `figure_bundle_export.py` |
| Coverage audit | ✅ 2026-10-23 | [FIGURE_BUNDLE_COVERAGE.md](FIGURE_BUNDLE_COVERAGE.md) |

## 3. Active phase — Bundle handoff coverage (P2)

**Goal:** every figure reachable from the GUI can be exported as a bundle that
the external pipeline can ingest without manual repair.

### 3.1 Coverage gaps

Six user-facing figures currently have no bundle context or dedicated builder:

1. P-value histogram (`PadjHistogramDialog`)
2. Comparison dot plot (`DotPlotDialog`)
3. chromVAR TF activity (`ChromVARDialog`)
4. TF motif enrichment (`MotifEnrichmentDialog`)
5. TF footprint (`TFFootprintDialog`)
6. TSS distance (`TSSDistanceDialog`)

Details and file locations are in
[FIGURE_BUNDLE_COVERAGE.md](FIGURE_BUNDLE_COVERAGE.md#5-missing-bundle-coverage).

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

1. Implement bundle coverage for the six missing figures.
2. Harden metadata/manifest output.
3. Add the coverage regression test.
4. Validate all generated scripts in a headless environment.
5. Hand a sample bundle to the external figure-atlas pipeline for contract
   review.

## 7. Related documents

- [Figure bundle coverage audit](FIGURE_BUNDLE_COVERAGE.md)
- [External pipeline requirements](external_pipeline_requirements.md)
- [Expression Distribution plan](EXPRESSION_DISTRIBUTION_PLAN.md)
