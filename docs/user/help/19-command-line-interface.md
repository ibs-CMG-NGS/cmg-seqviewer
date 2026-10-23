# 19. Command Line Interface

## 19.1 Overview

CMG-SeqViewer also ships a command-line interface for scripted / headless
use — no display or `QApplication` is ever created, so it runs on a
server or HPC node with no GUI available. It reuses the exact same
loading, auto-detection, and filtering logic as the desktop app (both
sides call into `utils/dataset_detection.py` and
`MainPresenter.compute_filtered_df()`), so a CLI filter produces the same
result as applying the equivalent filter in the Filter Panel.

The CLI is for **confirmed, repeatable procedures** — exploring a dataset
interactively still belongs in the GUI. Once a filtering procedure is
settled, a **recipe** file lets you replay it on one file (`run`) or apply
it across many files at once (`batch`), which is the package's current
batch-processing capability.

Because manual column mapping requires a dialog, the CLI never prompts for
it: if a file's columns can't be auto-detected, the command fails
immediately with a clear error (listing the required columns and what was
actually found) instead of opening a GUI dialog.

Installed as a console script (see **README → Installation**):

```bash
cmg-seqviewer-cli --help
```

or, from a source checkout, equivalently:

```bash
python src/cli.py --help
```

Four subcommands are available: `load`, `filter`, `run`, `batch`.

## 19.2 `load` — inspect a file

Loads a file through the same auto-detection used by **File → Open
Dataset**, and reports what was detected — without writing anything.
Useful to sanity-check a file (or a column-mapping fix) before scripting
around it.

```bash
cmg-seqviewer-cli load sample1_DE.xlsx
```

```
type: differential_expression
rows: 1523
columns: gene_id, log2fc, pvalue, adj_pvalue, baseMean
valid: True
```

`--type atac` forces ATAC-seq routing instead of auto-detection (for files
whose headers don't otherwise self-identify as ATAC-seq) — the same
purpose as **File → Open ATAC-seq Dataset...** in the GUI:

```bash
cmg-seqviewer-cli load weird_headers.parquet --type atac
```

`--type` also accepts `differential_expression`, `go_analysis`,
`multi_group`, `composition`, and `expression_summary` to bypass
auto-detection for those types.

### Machine-readable output (`--json`)

For scripted/CI validation, add `--json` to print the same verdict as a
JSON object instead of human-readable lines:

```bash
cmg-seqviewer-cli load sample1_DE.parquet --json
```

```json
{
  "dataset_type": "differential_expression",
  "rows": 1523,
  "columns": ["gene_id", "log2fc", "adj_pvalue", "baseMean"],
  "valid": true,
  "required_columns": ["gene_id", "log2fc", "adj_pvalue"],
  "missing_required_columns": [],
  "file": "sample1_DE.parquet"
}
```

`missing_required_columns` being empty and `valid` being `true` means the
file is safe to import into the database. Auto-detection works for
`.xlsx`, `.csv`, `.tsv`, and `.parquet` inputs.

## 19.3 `filter` — load + filter one file

Applies a one-off statistical filter and writes (or prints) the result.
Flag names and defaults match the Filter Panel's Statistical tab exactly:

```bash
cmg-seqviewer-cli filter sample1_DE.xlsx \
  --adj-pvalue-max 0.05 --log2fc-min 1.0 --regulation both \
  --out sample1_filtered.xlsx
```

Omit `--out` to print the filtered table to stdout instead of writing a
file. Output format is chosen from the `--out` extension: `.xlsx`, `.csv`,
`.tsv`, or `.parquet`.

Common flags (see `cmg-seqviewer-cli filter --help` for the full list):

| Flag | Applies to | Matches |
|------|-----------|---------|
| `--type` | all | Force dataset type instead of auto-detecting: `atac`, `differential_expression`, `go_analysis`, `multi_group`, `composition`, `expression_summary` |
| `--adj-pvalue-max` | DE / ATAC | Filter Panel "Padj" |
| `--log2fc-min` | DE / ATAC | Filter Panel "log2FC" |
| `--regulation` | DE / ATAC | Up / Down / Both |
| `--fdr-max`, `--fold-enrichment-min`, `--go-min-gene-count`, `--ontology`, `--go-direction` | GO/KEGG | Advanced GO Filter |
| `--mg-padj-max`, `--mg-basemean-min` | Multi-Group | Multi-Group statistical filter |
| `--atac-annotation`, `--atac-distance-max`, `--atac-peak-width-min`/`--atac-peak-width-max` | ATAC-seq | ATAC-seq Filtering section |

## 19.4 Recipes — `run` and `batch`

A **recipe** is a YAML (or JSON) file that records an input file, a
filter, and an output — the same idea as
`EnrichmentRequest.to_recipe_dict()` already used for GO/KEGG enrichment
cache reproducibility (see **6. GO/KEGG Enrichment Analysis — Cache &
reproducibility**), extended to the general load → filter → export
pipeline.

```yaml
# recipe.yaml
input: data/sample1_DE.xlsx
# type: atac              # optional — force dataset type, skips auto-detection
# name: MyDataset          # optional — dataset name (default: filename)
filter:
  mode: statistical         # statistical / gene_list / keyword / column_subset
  adj_pvalue_max: 0.05
  log2fc_min: 1.0
  regulation_direction: both
output:
  table: results/sample1_filtered.xlsx
```

Keys under `filter:` are the `FilterCriteria` field names — the same
values the `filter` flags above set. An unknown top-level key, an unknown
`filter:` key, or an invalid `mode` all fail immediately with the
offending key named, rather than being silently ignored.

**`run`** replays one recipe against its own `input:` file:

```bash
cmg-seqviewer-cli run recipe.yaml
```

**`batch`** applies one recipe's `filter:`/`output:` settings across many
files at once — this is the batch-processing capability: write the recipe
once a procedure is confirmed, then run it over an entire dataset
collection. The recipe's own `input:` is ignored in this mode; files come
from `--inputs` glob pattern(s) instead:

```bash
cmg-seqviewer-cli batch recipe.yaml \
  --inputs "data/*.xlsx" \
  --out-dir results/ \
  --manifest manifest.json
```

Each matched file is processed independently — one file's failure prints
`[FAIL] <file>: <error>` to stderr and does not stop the rest. A summary
line (`batch complete: N/M succeeded`) is printed at the end, and the
process exits with code `1` if any file failed. `--manifest` additionally
writes a JSON array with one entry per file (`input`, `status`,
`dataset_type`, `rows_total`, `rows_filtered`, `output`, or `error`) — a
machine-readable record of what was run, suitable for checking into a
results folder alongside the filtered tables.

## 19.5 Exit codes and scripting

Every subcommand returns `0` on success and `1` on failure (an
unrecognized file, missing required columns, a bad recipe, or — for
`batch` — at least one file failing), so the CLI composes normally with
shell `&&` / CI pipelines. Pass `--verbose` to any subcommand for a full
traceback instead of the one-line `Error: ...` message on stderr.

---
**See also**: [User Guide](../user-guide.md) · [FAQ](23-faq.md)
