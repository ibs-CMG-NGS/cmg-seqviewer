# External analysis pipeline requirements for fig-atlas-template

This document describes the requirements that an external analysis/plotting pipeline should satisfy when it generates figures for this atlas package.

The goal is to make the external pipeline produce a self-contained, reproducible figure bundle that this package can ingest, publish, and verify.

---

## 1. Purpose

The external analysis pipeline is responsible for:

- reading input data
- performing analysis
- generating figure outputs
- exporting the figure-related artifacts needed for reproducibility
- producing a bundle that this atlas package can consume

The atlas package is responsible for:

- collecting those outputs
- publishing them into the figure atlas structure
- generating README/manifest files
- verifying completeness

---

## 2. Required outputs

The external pipeline must produce the following artifacts for each figure.

### 2.1 Figure image files

The pipeline must generate at least the following output files for the figure:

- one raster image, e.g. `.png`
- one vector publication file, e.g. `.pdf`
- one editable vector file, e.g. `.svg`

The files should be written using a consistent base name, hereafter called the `source_stem`.

Example:

- `outputs/figures/figure1_heatmap.png`
- `outputs/figures/figure1_heatmap.pdf`
- `outputs/figures/figure1_heatmap.svg`

### 2.2 Figure generation script

The pipeline must provide a Python script that reproduces the figure generation.

Requirements:

- the script must be a `.py` file
- the script should be runnable independently
- it should clearly define the input files it uses
- it should clearly define the output files it writes
- it should be version-controlled and stored in a stable path

### 2.3 Data and statistics files

The pipeline should export any of the following that are relevant:

- raw or processed input data used to generate the figure
- summary statistics used to derive the plotted values
- derived tables used for the figure panels
- supplementary tables associated with the figure

Preferred formats:

- CSV for tabular data
- Parquet for larger tabular data if appropriate
- JSON/YAML for small metadata payloads

### 2.4 Metadata file

The pipeline must provide a metadata file describing the figure bundle.

Recommended contents:

- figure number
- figure slug
- figure title
- panel descriptions (a/b/c, etc.)
- source stem
- primary code script path
- input file list
- output file list
- statistics table list
- claim boundary / interpretation note
- software/environment information
- generation timestamp

Preferred format:

- YAML

---

## 3. Required metadata fields

The metadata file should include at minimum the following fields.

### 3.1 Figure identity

- `figure_number`
- `figure_slug`
- `figure_title`

### 3.2 Output location

- `source_stem`
- `output_formats`

### 3.3 Panel description

- `panel_notes` or equivalent list of panel descriptions

### 3.4 Reproducibility references

- `primary_code`
- `input_files`
- `output_files`
- `statistics_tables`

### 3.5 Interpretation note

- `claim_boundary`

### 3.6 Environment information

- Python version
- package versions used to generate the figure
- optional git commit hash
- optional dataset version / manifest version

---

## 4. Role split: panel generation vs figure assembly

A key design decision is to separate panel-level generation from final figure assembly.

### 4.1 External pipeline responsibility

The external analysis/plotting pipeline should generate and export the individual plot components for a figure.

This includes:

- one or more panel-level plot outputs
- the data/statistics used for each panel
- panel-level metadata such as panel label, title, and interpretation note

Examples:

- panel a: a line plot
- panel b: a scatter plot
- panel c: a bar plot

### 4.2 Atlas-side responsibility

The atlas-side assembly step should compose those panel-level outputs into the final multi-panel figure.

This includes:

- arranging panels into the final sub-panel layout (for example a/b/c)
- applying final figure-level styling
- adding the overall title and figure-level annotations
- preserving the panel-to-meaning mapping in metadata

In other words, the external pipeline should focus on producing individual plot units, while the atlas-side workflow should focus on assembling them into the final manuscript figure.

This is the preferred boundary because it keeps:

- panel generation reproducible and modular
- final figure composition explicit and reviewable
- style/layout changes centralized in the atlas workflow

### 4.2 Naming and path conventions

The external pipeline should follow stable naming conventions.

### 4.1 Output stem convention

The figure outputs should share the same stem:

- `source_stem = outputs/figures/figure1_heatmap`

Then the atlas package can derive:

- `.png`
- `.pdf`
- `.svg`

### 4.2 Relative paths

Paths should preferably be relative to the project root, not absolute machine paths.

### 4.3 Stable filenames

Use deterministic names so that the atlas can locate them reliably.

---

## 5. Reproducibility requirements

The external pipeline should make the figure reproducible from the bundle alone.

This means the bundle should contain enough information to answer:

- what input data was used
- what code generated the figure
- what parameters or settings were used
- what outputs were produced
- what interpretation boundary applies to the figure

### 5.1 Required reproducibility elements

The pipeline should provide:

- exact script used to generate the figure
- exact data files used
- exact output files written
- settings or config used for the figure
- optional seed values for random processes

### 5.2 Recommended reproducibility elements

- environment lockfile or dependency list
- package versions
- commit hash of the analysis repository
- dataset version or checksum

---

## 6. Figure bundle structure

The external pipeline should ideally package outputs in a directory structure like the following.

```text
figure_bundle/
  figure.py
  metadata.yaml
  data.csv
  statistics.csv
  figure.png
  figure.pdf
  figure.svg
```

A more complete structure could include:

```text
figure_bundle/
  scripts/
    figure.py
  inputs/
    data.csv
  outputs/
    figure.png
    figure.pdf
    figure.svg
  metadata/
    metadata.yaml
  tables/
    supplementary_table.csv
```

---

## 7. Execution requirements

The external pipeline should support a simple execution interface.

Preferred behavior:

- one command generates the figure bundle
- the command is documented
- the outputs are written to predictable paths
- the command can be rerun without manual edits

Example:

```bash
python figure.py
```

or

```bash
./run_figure_pipeline.sh
```

---

## 8. Validation requirements

Before handing off the bundle to this atlas package, the external pipeline should internally check that:

- the required output files exist
- the output files are non-empty
- the metadata file is complete
- referenced files actually exist
- the script can run from a clean environment

---

## 9. Recommended handoff contract

The external pipeline should hand off a bundle that contains:

- a figure generation script
- a metadata file
- input and/or statistics files used by that script
- final figure image files

That bundle should be sufficient for this atlas package to:

- publish the figure
- generate a README
- write a manifest
- verify completeness

---

## 10. Short checklist

Use the following checklist when communicating with the external pipeline team.

### Must-have

- [ ] Generate `.png`, `.pdf`, `.svg` figure outputs
- [ ] Use a stable `source_stem`
- [ ] Store a runnable Python script for figure generation
- [ ] Export data/statistics tables used by the plot
- [ ] Provide a metadata YAML file
- [ ] Record figure title, slug, number, and panel notes
- [ ] Record input/output file paths
- [ ] Record claim boundary / interpretation note
- [ ] Ensure output files are non-empty

### Nice-to-have

- [ ] Include environment/package versions
- [ ] Include git commit hash
- [ ] Include random seed values
- [ ] Include checksum or dataset version
- [ ] Provide a simple one-command execution path

---

## 11. Suggested handoff sentence

You can use the following sentence when sending this requirement to an external analysis pipeline team.

> Please generate a reproducible figure bundle for each manuscript figure containing: a runnable Python figure-generation script, the data/statistics files used to create the figure, the final `.png`/`.pdf`/`.svg` outputs, and a YAML metadata file describing the figure identity, panel notes, input/output paths, and interpretation boundary. The atlas package will consume this bundle for publishing and verification.
