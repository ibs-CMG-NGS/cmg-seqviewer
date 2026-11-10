# Response to the 2026-11-10 fig-atlas verification

- **Date**: 2026-11-10
- **About**: `FIGURE_ATLAS_REPLY_2026-11-09-3.md`
- **From**: cmg-seqviewer
- **Scope**: contract closure, reference bundle freeze, and the move to cmg-figure

## 1. Confirmed

- `fa bundle check`: **22/22 ok, 0 warnings, 0 errors**.
- PCA: the gene × sample table is correct; no exporter or bundle change is
  needed.
- `go_cluster_dot.direction_colors`: understood as a renderer default reported
  under `not_reached`, not a bundle problem. We will leave the project config
  block alone and will not add it to bundle metadata.
- fig-atlas **v0.4.0** is the reference release for these contracts.

## 2. Reference set

The 22 synthetic bundles in
`cmg_fig_atlas_bundle_samples_2026-11-09/` are now frozen as the contract
reference set. The seven earlier sample bundles remain the first reference set.

## 3. Next step

We will prepare the first **real** project bundles for **cmg-figure**, using the
confirmed mappings as-is. The project layer owns:

- figure numbers and panel labels (a/b/c)
- project-specific panel grouping
- journal size/layout and final publication styling

Please provide the first project name and dataset list so we can prepare the
project-level `FigureSpec`/panel mapping and send the real bundles. The same
cycle will then run in cmg-figure:

`fa bundle check` → `fa ingest bundle` → `fa build --preflight` → `fa verify`

The dense 22-panel test layout is only a contract test; real figures are built
one project at a time, so its print-size warnings do not apply.

## 4. Delivery

- Contract reference bundles: `cmg_fig_atlas_bundle_samples_2026-11-09/`
- Mapping record: `cmg_fig_atlas_mapping_2026-11-09/COLUMN_ROLES.md`
- This response: `FIGURE_ATLAS_RESPONSE_2026-11-10.md`
