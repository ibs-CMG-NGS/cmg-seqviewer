# Figure-Atlas Handoff Checklist

- **Date**: 2026-10-24
- **Source**: cmg-seqviewer v1.4.1 + fig-atlas exporter update
- **Delivery**: `cmg_fig_atlas_bundle_samples_2026-10-24.zip`
- **Purpose**: confirm that the external figure-atlas pipeline can ingest the
  cmg-seqviewer panel bundles without manual repair.
- **Related**:
  [Bundle coverage](FIGURE_BUNDLE_COVERAGE.md) ·
  [Figure handoff plan](FIGURE_QUALITY_REPRODUCIBILITY_PLAN.md) ·
  [External pipeline requirements](external_pipeline_requirements.md)

## 0. Downstream routing

There are two downstream packages with different responsibilities:

| Package | Role | What to send |
|---|---|---|
| **fig-atlas** | Foundational package: bundle contract, ingest, FigureSpec, publish/verify | **Synthetic sample ZIP + this checklist** for contract review |
| **cmg-figure** | Project layer: uses fig-atlas to build actual research-project figures | **Real project bundles** after the contract is confirmed |

Recommended sequence:

1. Send the synthetic sample ZIP to **fig-atlas** first.
   - Confirm bundle structure, metadata schema, FigureSpec model, script
     execution, and acceptance criteria.
2. Fix any exporter/contract mismatches in cmg-seqviewer.
3. Send real project bundles to **cmg-figure** (or the project figure owner).
   - cmg-figure decides figure numbers, panel labels (a/b/c), project-specific
     grouping, and final publication layout.
4. If cmg-figure maintains its own ingest adapter, include it in the contract
   review, but **fig-atlas remains the owner of the bundle contract**.

Do **not** send real/sensitive project data to fig-atlas for contract review;
use the synthetic sample for that step.

## 0.1 fig-atlas reply (2026-10-23) — resolved

fig-atlas confirmed:

- It reads only `inputs/data.csv` + `metadata/metadata.yaml`.
  `scripts/`, `outputs/`, `manifest.json`, and `index.json` are ignored.
- One bundle = one panel. A project (figure) can ingest many bundles.
- `plot_type` must be a registered fig-atlas renderer; the exporter now maps:

| cmg plot_type | fig-atlas plot_type |
|---|---|
| `padj_histogram` | `histogram` |
| `tss_distance` | `histogram` |
| `motif_enrichment` | `motif_dotplot` |
| `tf_footprint` | `threshold_scatter` |
| `comparison_dot` | `cross_condition_dotplot` |
| `chromvar` | `volcano` |
| `expression_distribution` | `violin` |

- `figure_number` is assigned by the project layer; leave it empty.
- `panel_notes` as a string is fine.
- `statistics_tables: []` is acceptable when only design cut-off lines are
  drawn. These seven samples draw cut-off lines, not test marks.
- fig-atlas does not run `scripts/figure.py`; the new
  `export_fig_atlas_bundle()` writes data + metadata only.

Verification after the exporter update:

- `fa bundle check`: **7/7 ok, 0 warnings, 0 errors**
- `fa ingest bundle`: **7/7** into a temporary project
- `fa build --preflight`: **ALL 1 PROJECT(S) PASSED**
- `fa verify`: **PASS** (warnings only from a deliberately dense 7-panel test
  layout)

Resolved in the 2026-10-24 reply:

- Switch `expression_distribution` to grouped violins (`x_col: cell_type`,
  `hue_col: condition`, `hue_order`).
- `threshold_scatter` identity line is available; the TF footprint sample sets
  `show_identity_line: true`.
- `motif_enrichment` colour is **significance** (`-log10(p)`), not log2 fold
  enrichment; the colourbar label says so.

Still open:

- The other 22 internal plot types need fig-atlas `plot_type` mappings.
- fig-atlas requested a list of names and column roles (or one sample table per
  type) for those 22.

---

## 1. What is being delivered

The ZIP contains seven **synthetic** panel bundles:

| Bundle | plot_type |
|---|---|
| `01_padj_histogram` | `padj_histogram` |
| `02_tss_distance` | `tss_distance` |
| `03_motif_enrichment` | `motif_enrichment` |
| `04_tf_footprint` | `tf_footprint` |
| `05_comparison_dot` | `comparison_dot` |
| `06_chromvar` | `chromvar` |
| `07_expression_distribution` | `expression_distribution` |

Each bundle contains:

```text
<bundle>/
├── inputs/data.csv
├── outputs/<source_stem>.png/.pdf/.svg   # human reference only
├── metadata/metadata.yaml
└── manifest.json
```

fig-atlas reads only `inputs/data.csv` and `metadata/metadata.yaml`. The ZIP
root also contains `README.md`, `index.json`, `SHA256SUMS`,
`FIGURE_ATLAS_HANDOFF_CHECKLIST.md`, `FIGURE_ATLAS_REPLY_2026-10-23.md`,
`FIGURE_ATLAS_REPLY_2026-10-24.md`, `FA_BUNDLE_CHECK.txt`, and
`FA_ACCEPTANCE.md`.

## 2. cmg-seqviewer side (already verified)

- [x] All 29 user-facing plot types are bundle-ready.
- [x] Seven representative sample bundles generated.
- [x] All seven bundles pass `fa bundle check` (7/7 ok, 0 warnings, 0 errors).
- [x] `metadata.yaml` reports `app_version: 1.4.1`.
- [x] `SHA256SUMS` verified.
- [x] Synthetic data only; no sensitive or identifiable data.
- [x] The viewer owns panel generation; figure-atlas owns final publication
  layout and multi-panel assembly.

## 3. What the downstream packages must confirm

### 3.1 Bundle structure and naming (fig-atlas)

- [ ] Is the current directory layout accepted as-is?
- [ ] Should the ZIP root be one figure, or a collection of panel bundles?
- [ ] Is **one bundle per panel** acceptable, or does figure-atlas expect
  **one bundle per final figure**?
- [ ] Which output naming should be canonical?
  - `outputs/figure.*`
  - `outputs/<source_stem>.*`
  - or both
- [ ] Is `manifest.json` used, ignored, or required to match a schema?
- [ ] Are relative paths inside the bundle acceptable?

### 3.2 Metadata contract (fig-atlas)

Our `metadata.yaml` currently provides:

- `figure_id`
- `figure_number` (currently empty)
- `figure_title`
- `figure_slug`
- `plot_type`
- `source_stem`
- `dataset_name`
- `claim_boundary`
- `panel_notes` (currently a single string)
- `created_at`
- `app_version`
- `environment` (Python + platform)
- `output_formats`
- `input_files`
- `output_files`
- `statistics_tables` (empty list when no statistics file)
- `plot_params`

Please confirm:

- [ ] Which fields are **required** vs optional?
- [ ] Is `figure_number` required at bundle time, or assigned later by
  figure-atlas?
- [ ] Is `panel_notes` expected as a **string**, **list**, or one entry per
  panel?
- [ ] Is `primary_code` required? If so, should it be `scripts/figure.py`?
- [ ] Is `statistics_tables: []` acceptable when no statistics file exists?
- [ ] Is the current `environment` block sufficient, or are package versions /
  git commit / dataset version required?
- [ ] Should `claim_boundary` and `panel_notes` remain separate fields?
- [ ] Is a metadata schema file available that we should validate against?

### 3.3 FigureSpec and panel mapping (fig-atlas schema; cmg-figure values)

- [ ] How should a bundle map to a `FigureSpec`?
- [ ] Is `FigureSpec` per **figure** or per **panel**?
- [ ] Who assigns figure numbers, panel labels (a/b/c), and final ordering?
- [ ] How should multiple bundles for one final figure be grouped?
- [ ] Should cmg-seqviewer provide a draft `FigureSpec` or only panel bundles?

### 3.4 Script execution and reproduction (fig-atlas / cmg-figure)

- [ ] Will figure-atlas run `scripts/figure.py`, or consume only the outputs?
- [ ] Are the dependencies acceptable?
  - Python 3.10+
  - numpy
  - pandas
  - matplotlib
  - scipy (optional; only for gene clustering in comparison dot plots)
- [ ] Should the script write `outputs/figure.*` or
  `outputs/<source_stem>.*`?
- [ ] Does figure-atlas require a fixed output filename or figure size?
- [ ] Should the script accept CLI arguments for output directory / size?

### 3.5 Data and privacy (both)

- [ ] Will real (non-synthetic) bundles be ingested on the same path?
- [ ] What is the data-retention / access policy for real bundles?
- [ ] Should sensitive datasets be excluded from the ZIP and delivered
  separately?
- [ ] Is `claim_boundary` sufficient for interpretation/provenance?

### 3.6 Validation and acceptance (fig-atlas contract; cmg-figure project)

- [ ] Which verify command / schema should we run before delivery?
- [ ] Are PNG/PDF/SVG all required, or is PNG + one vector format enough?
- [ ] Is 300 dpi PNG acceptable?
- [ ] Are empty `statistics_tables` and missing `statistics.csv` acceptable?
- [ ] What constitutes a **pass** for the first ingest test?

## 4. Questions to send with the synthetic ZIP (fig-atlas)

1. Can figure-atlas ingest the current bundle layout as-is?
2. Do you want one bundle per panel or one bundle per final figure?
3. Which metadata fields are required, and is there a schema?
4. Should `figure_number` be assigned by cmg-seqviewer or figure-atlas?
5. Should `panel_notes` be a string or a list?
6. Is `primary_code` required, and should it point to `scripts/figure.py`?
7. Is `statistics_tables: []` acceptable when no statistics file is present?
8. Will you run `scripts/figure.py`, or consume outputs only?
9. Which output naming is canonical: `figure.*` or `<source_stem>.*`?
10. How should bundles map to `FigureSpec` and panel labels?
11. Are package versions / git commit / dataset version required in metadata?
12. What is the acceptance test for the first bundle ingest?

## 5. Acceptance criteria for the first handoff

The handoff is successful when figure-atlas can:

- [ ] unzip the delivery
- [ ] identify all seven bundles
- [ ] validate the bundle structure
- [ ] parse `metadata.yaml` without manual repair
- [ ] run at least one `scripts/figure.py` successfully
- [ ] map at least one bundle to a `FigureSpec` / panel
- [ ] publish it into the atlas structure
- [ ] run its verify step successfully

After that, scale the same contract to all 29 plot types.

## 6. Known items to resolve

- `figure_number` is currently empty; ownership is undecided.
- `primary_code` is not yet a metadata field.
- `panel_notes` is a single string, not a list.
- Both `outputs/figure.*` and `outputs/<source_stem>.*` are written.
- `statistics.csv` is optional and absent in most sample bundles.
- The current `environment` block has Python/platform but not package versions
  or git commit.
- figure-atlas may need an adapter to map this bundle layout into its own
  `figures/` + `FigureSpec` structure.

## 7. Next steps

1. Send the synthetic ZIP, `README.md`, and this checklist to **fig-atlas**.
2. Collect answers to §4 and finalize the bundle contract.
3. Adjust `figure_bundle_export.py` if the contract changes.
4. Re-run the seven sample bundles and checksums.
5. Send real project bundles to **cmg-figure** and define the first real
   FigureSpec/panel mapping there.
6. Repeat the ingest test in the project environment.
