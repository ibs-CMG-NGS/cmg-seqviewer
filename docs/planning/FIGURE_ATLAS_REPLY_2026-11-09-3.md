# Reply to the 2026-11-09 second response

- **Date**: 2026-11-10
- **About**: `cmg_fig_atlas_bundle_samples_2026-11-09.zip` (22 sample bundles)
- **From**: fig-atlas (bundle contract owner)
- **Scope**: verification of the 22 bundles, the two open questions, and the next step

## 1. Verification

We ran the checks on our side, against v0.4.0:

- `fa bundle check` on the 22 bundles: **22/22 ok, 0 warnings, 0 errors**.
- `pca`: the bundle draws (one axes), with the gene × sample table as sent.
- The contract each bundle matched is the one mapped in `FIGURE_ATLAS_REPLY_2026-11-09-2.md`.

## 2. PCA orientation — your table is right

Keep the table as it is: **one row per feature (gene), one numeric column per sample**. The renderer
transposes internally (`fig_atlas/renderers/pca.py`: `X = mat.T`) before the decomposition, so gene ×
sample is the orientation it expects. The line in our earlier reply that said "transpose to one row
per sample" was wrong; the corrected reply says what is written here. No change is needed in the
exporter or in the bundle.

## 3. `go_cluster_dot.direction_colors` — a renderer default, not a bundle problem

This is expected and is not a contract issue:

- The key is a renderer parameter: a dict of colours used when **`color_by: Direction`**. Its default
  is `{UP: ..., DOWN: ..., TOTAL: ...}`, which is why the group counts three keys.
- `fa ingest bundle` writes the renderer's full param block into the project config, including defaults,
  so the key appears there even though your metadata does not set it.
- Your panel uses `color_by: Fold Enrichment`, so the renderer never reaches the `direction_colors`
  lookup. `fa lint` groups such keys under **`not_reached`**: the code knows the name, this build did
  not get there. It is not a typo and not a dead key.
- What to do: nothing. Leaving the block in the project config is harmless, and deleting it changes
  nothing (the schema default applies again). Do not add the key to your bundle metadata.

## 4. Release

`v0.4.0` is tagged and released (2026-11-09); it contains the four new shapes the mapping relies on
(`dot_matrix` numeric colour, `group_scatter` cut-offs, `threshold_scatter` colour/size roles, `upset`),
plus the `violin` second factor and the `threshold_scatter` identity line. Install by tag:

```bash
pip install "git+https://github.com/ibs-CMG-NGS/fig-atlas@v0.4.0"
```

`fa --version` prints `fa 0.4.0`.

## 5. Next step

- Send the first **real** project bundles to the project layer (cmg-figure) with the mappings as they
  are; the 22 synthetic bundles stay as the contract reference set.
- On the first real delivery we will run the same cycle (`fa bundle check` → `fa ingest bundle` →
  `fa build --preflight` → `fa verify`) and return the report. The dense 22-panel test layout is not
  the target; real figures are built one project (figure) at a time, so the print-size warnings from
  that test layout do not apply.
