# 19. Command Line Interface

## 19.1 Overview

CMG-SeqViewer ships a command-line interface for scripted / headless use — no
display or `QApplication` is ever created, so it runs on a server or HPC node
with no GUI available. It reuses the same import/auto-detection layer as the
desktop app and the same `FilterEngine` as the Filter Panel, so a CLI filter
produces the same result as applying the equivalent filter in the GUI.

The CLI is for **confirmed, repeatable procedures** — exploring a dataset
interactively still belongs in the GUI. Once a procedure is settled, a
**recipe** file lets you replay it on one file (`run`) or apply it across many
files at once (`batch`).

Because manual column mapping requires a dialog, the CLI never prompts for it:
if a file's columns cannot be auto-detected, the command fails immediately with
a clear error (listing the required columns and what was actually found) instead
of opening a GUI dialog.

### Installation and invocation

Installed as a console script (see **README → Installation**):

```bash
cmg-seqviewer-cli --help
```

From a source checkout, the equivalent is:

```bash
python src/cli.py --help
```

If you run the package as a module, make `src/` importable first:

```bash
PYTHONPATH=src python -m cli --help
```

### Subcommands

| Command | Purpose |
|---|---|
| `load` | Inspect a file's detected type, row count, columns, and validity |
| `filter` | Load + filter (statistical, gene list, keyword, or column subset) + export |
| `run` | Replay one recipe against its `input:` file |
| `batch` | Apply one recipe's filter/output settings across many files |
| `summary` | Print a JSON-safe dataset summary |
| `query` | Select columns/rows without filtering |
| `plot` | Render a registered plot type headlessly |
| `export` | Write the loaded table as CSV/TSV/XLSX/Parquet |
| `datasets` | List or describe datasets in the pre-loaded database |
| `compare` | Compare two or more DE datasets (common/unique genes) |
| `schema` | List plot types and help sections |
| `help` | Search or print the built-in F1 help |

### General conventions

- `--type` forces a dataset type instead of auto-detection. It accepts
  `atac`, `differential_expression`, `go_analysis`, `multi_group`,
  `composition`, `expression_summary`, `expression_distribution`, `chromvar`,
  `motif`, and `footprint`.
- `--out` writes a table/image to a file; without it, table commands print to
  stdout.
- `--json` (where available) prints machine-readable JSON for CI and scripts.
- `--verbose` prints a traceback on failure instead of only the one-line error.
- Exit code `0` means success; `1` means failure (see **19.6**).

## 19.2 `load` — inspect a file

Loads a file through the same auto-detection used by **File → Open Dataset**,
and reports what was detected — without writing anything. Useful to sanity-check
a file (or a column-mapping fix) before scripting around it.

```bash
cmg-seqviewer-cli load sample1_DE.xlsx
```

```
type: differential_expression
rows: 1523
columns: gene_id, log2fc, pvalue, adj_pvalue, baseMean
valid: True
```

`--type atac` forces ATAC-seq routing instead of auto-detection (for files whose
headers do not otherwise self-identify as ATAC-seq) — the same purpose as
**File → Open ATAC-seq Dataset...** in the GUI:

```bash
cmg-seqviewer-cli load weird_headers.parquet --type atac
```

Use `--type` for any supported type when auto-detection is ambiguous:

```bash
cmg-seqviewer-cli load data.csv --type go_analysis
cmg-seqviewer-cli load data.parquet --type chromvar
```

### Machine-readable output (`--json`)

For scripted/CI validation, add `--json` to print the same verdict as a JSON
object instead of human-readable lines:

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

`missing_required_columns` being empty and `valid` being `true` means the file
is safe to import into the database. Auto-detection works for `.xlsx`, `.csv`,
`.tsv`, and `.parquet` inputs.

## 19.3 `filter` — load + filter one file

Applies a one-off filter and writes (or prints) the result. The default mode is
`statistical`; the same command also supports gene-list, keyword, and
column-subset modes.

### Statistical mode (default)

Statistical flag names and defaults match the Filter Panel's Statistical tab:

```bash
cmg-seqviewer-cli filter sample1_DE.xlsx \
  --adj-pvalue-max 0.05 --log2fc-min 1.0 --regulation both \
  --out sample1_filtered.xlsx
```

For GO/KEGG results:

```bash
cmg-seqviewer-cli filter go_result.xlsx --type go_analysis \
  --fdr-max 0.05 --ontology BP --go-direction UP \
  --go-min-gene-count 3 --out go_filtered.csv
```

For ATAC-seq:

```bash
cmg-seqviewer-cli filter atac.parquet --type atac \
  --adj-pvalue-max 0.05 --log2fc-min 1.0 \
  --atac-annotation Promoter --atac-distance-max 1000 \
  --out atac_filtered.csv
```

For Multi-Group results:

```bash
cmg-seqviewer-cli filter multi_group.csv --type multi_group \
  --mg-padj-max 0.05 --mg-basemean-min 10 \
  --out multi_group_filtered.csv
```

### Gene-list mode

One gene symbol per line; input order is preserved in the output:

```bash
cmg-seqviewer-cli filter sample1_DE.xlsx --mode gene_list \
  --gene-list-file genes.txt --out gene_filtered.csv
```

For GO/KEGG data you can filter by term ID instead of gene symbol:

```bash
cmg-seqviewer-cli filter go_result.xlsx --type go_analysis --mode gene_list \
  --term-id GO:0006955 --term-id GO:0006954 --out terms.csv
```

`--gene-list-file` and `--term-id` are mutually exclusive.

### Keyword mode

Case-insensitive substring search. If `--search-column` is omitted, the CLI
chooses the identifier column automatically (GO/KEGG: description/term ID; other
types: symbol/gene ID):

```bash
cmg-seqviewer-cli filter sample1_DE.xlsx --mode keyword \
  --keyword hypoxia --search-column description --out keyword.csv
```

### Column-subset mode

Keeps only the requested columns (original column order is preserved; row count
is unchanged):

```bash
cmg-seqviewer-cli filter sample1_DE.xlsx --mode column_subset \
  --columns gene_id log2fc adj_pvalue --out subset.csv
```

`gene-list` and `column-subset` are accepted as aliases. Omit `--out` to print
the filtered table to stdout instead of writing a file. Output format is chosen
from the `--out` extension: `.xlsx`, `.csv`, `.tsv`, or `.parquet`. If a filter
matches no rows, the command still succeeds and writes an empty table; adjust
the thresholds if that was not intended.

### Filter flag reference

| Flag | Applies to | Meaning |
|---|---|---|
| `--type` | all | Force dataset type instead of auto-detecting |
| `--mode` | all | `statistical` (default), `gene_list`, `keyword`, `column_subset` |
| `--gene-list-file`, `--term-id` | gene_list | Gene symbols file or GO/KEGG term IDs |
| `--keyword`, `--search-column` | keyword | Substring and optional target column |
| `--columns` | column_subset | Columns to keep, in original order |
| `--adj-pvalue-max` | DE / ATAC | Filter Panel "Padj" |
| `--log2fc-min` | DE / ATAC | Filter Panel "log2FC" |
| `--regulation` | DE / ATAC | `up`, `down`, or `both` |
| `--fdr-max`, `--fold-enrichment-min`, `--go-min-gene-count`, `--ontology`, `--go-direction` | GO/KEGG | Advanced GO Filter |
| `--mg-padj-max`, `--mg-basemean-min` | Multi-Group | Multi-Group statistical filter |
| `--atac-annotation`, `--atac-distance-max`, `--atac-peak-width-min`/`--atac-peak-width-max` | ATAC-seq | ATAC-seq Filtering section |

## 19.4 Recipes — `run` and `batch`

A **recipe** is a YAML (or JSON) file that records an input file, a filter, and
an output — the same idea as `EnrichmentRequest.to_recipe_dict()` already used
for GO/KEGG enrichment cache reproducibility (see **6. GO/KEGG Enrichment
Analysis — Cache & reproducibility**), extended to the general load → filter →
export pipeline.

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

Keys under `filter:` are the `FilterCriteria` field names — the same values the
`filter` flags above set. An unknown top-level key, an unknown `filter:` key, or
an invalid `mode` all fail immediately with the offending key named, rather than
being silently ignored.

Other recipe examples:

```yaml
# Gene list
filter:
  mode: gene_list
  gene_list: [G1, G2, G3]
```

```yaml
# Keyword
filter:
  mode: keyword
  search_keyword: hypoxia
  search_column: description
```

```yaml
# Column subset
filter:
  mode: column_subset
  subset_columns: [gene_id, log2fc, adj_pvalue]
```

**`run`** replays one recipe against its own `input:` file:

```bash
cmg-seqviewer-cli run recipe.yaml
```

**`batch`** applies one recipe's `filter:`/`output:` settings across many files
at once — write the recipe once a procedure is confirmed, then run it over an
entire dataset collection. The recipe's own `input:` is ignored in this mode;
files come from `--inputs` glob pattern(s) instead:

```bash
cmg-seqviewer-cli batch recipe.yaml \
  --inputs "data/*.xlsx" \
  --out-dir results/ \
  --manifest manifest.json
```

Each matched file is processed independently — one file's failure prints
`[FAIL] <file>: <error>` to stderr and does not stop the rest. A summary line
(`batch complete: N/M succeeded`) is printed at the end, and the process exits
with code `1` if any file failed. `--manifest` additionally writes a JSON array
with one entry per file (`input`, `status`, `dataset_type`, `rows_total`,
`rows_filtered`, `output`, or `error`) — a machine-readable record of what was
run, suitable for checking into a results folder alongside the filtered tables.

## 19.5 Headless inspection, comparison, and plotting

These commands use the shared `src/services/` layer, so they behave the same way
as the CLI filtering path and can be called by an AI client or a pipeline.

### `summary`

Prints a JSON-safe dataset summary. Text output shows the main fields; `--json`
returns the full summary:

```bash
cmg-seqviewer-cli summary data/DE.xlsx
cmg-seqviewer-cli summary data/DE.xlsx --json
```

### `query`

Selects columns and a row range without filtering. `--offset` is 0-based;
without `--out`, the result is printed to stdout:

```bash
cmg-seqviewer-cli query data/DE.xlsx \
  --columns gene_id log2fc adj_pvalue --limit 100 --offset 0 \
  --out preview.csv
```

### `plot`

Renders any registered plot type with the same renderers as the GUI. Run
`schema --json` to discover the current `plot_type` names:

```bash
cmg-seqviewer-cli schema --json
cmg-seqviewer-cli plot data/DE.xlsx --plot-type volcano \
  --params-json '{"log2fc_threshold": 1.0, "padj_threshold": 0.05}' \
  --out figures/volcano.png --dpi 300 --figsize 10x7
```

`--out` is required. The plot is rendered headlessly with matplotlib Agg; no
`QApplication` is created. Use `--figsize WIDTHxHEIGHT` and `--dpi` for output
size/resolution.

### `export`

Writes the loaded table as CSV/TSV/Excel/Parquet. The format defaults to the
`--out` extension; override it with `--format`:

```bash
cmg-seqviewer-cli export data/DE.xlsx --out exported/de.csv
cmg-seqviewer-cli export data/DE.xlsx --out exported/de.dat --format parquet
```

### `datasets`

Lists or describes datasets in the pre-loaded database. Use `--database-dir` to
point at a non-default database (useful for a project export or a CI fixture):

```bash
cmg-seqviewer-cli datasets list --json
cmg-seqviewer-cli datasets list --query hypoxia --type differential_expression
cmg-seqviewer-cli datasets list --organism "Homo sapiens" --tag pilot
cmg-seqviewer-cli datasets describe <dataset_id> --json
```

`datasets describe` loads the parquet to include its schema; add `--no-schema`
to read metadata only. `--query` searches alias/notes/tags/researcher;
`--cell-type`, `--organism`, `--researcher`, and `--tag` add filters.

### `compare`

Compares two or more DE datasets using the same `StatisticalAnalyzer` as the
GUI. It reports common genes, per-dataset unique genes, and an optional
comparison table:

```bash
cmg-seqviewer-cli compare a_DE.csv b_DE.csv --json
cmg-seqviewer-cli compare a_DE.csv b_DE.csv --json --include-table
cmg-seqviewer-cli compare a_DE.csv b_DE.csv --out comparison.csv
```

`--gene-list` restricts the comparison to a text file of genes (one per line);
`--adj-pvalue-max` / `--log2fc-min` set the significance cutoffs.
`--include-table` includes the table in JSON (limited by `--table-limit`,
default 50); `--out` writes the full table and adds its path to JSON as
`artifact`.

### `schema` and `help`

`schema` lists plot types and help sections; `help` searches or prints the
Markdown F1 help:

```bash
cmg-seqviewer-cli schema --json
cmg-seqviewer-cli help filter --json
cmg-seqviewer-cli help --section 01-getting-started
```

## 19.6 Exit codes and scripting

Every subcommand returns `0` on success and `1` on failure (an unrecognized
file, missing required columns, a bad recipe, or — for `batch` — at least one
file failing), so the CLI composes normally with shell `&&` / CI pipelines.
Pass `--verbose` to any subcommand for a full traceback instead of the one-line
`Error: ...` message on stderr.

Examples:

```bash
# Stop the shell pipeline if load fails
cmg-seqviewer-cli load data.csv --json > load.json

# Run a batch and keep the per-file manifest for CI
cmg-seqviewer-cli batch recipe.yaml --inputs "data/*.csv" \
  --out-dir results/ --manifest results/manifest.json
```

## 19.7 Common workflows

### DE: load → filter → volcano → export

```bash
cmg-seqviewer-cli load data/DE.xlsx
cmg-seqviewer-cli filter data/DE.xlsx \
  --adj-pvalue-max 0.05 --log2fc-min 1.0 --out results/DE_filtered.csv
cmg-seqviewer-cli plot results/DE_filtered.csv --plot-type volcano \
  --out results/volcano.png
cmg-seqviewer-cli export results/DE_filtered.csv --out results/DE_filtered.xlsx
```

### Gene list → filtered table

```bash
cmg-seqviewer-cli filter data/DE.xlsx --mode gene_list \
  --gene-list-file genes.txt --out results/gene_list.csv
```

### GO/KEGG: filter terms → plot

```bash
cmg-seqviewer-cli filter data/GO.xlsx --type go_analysis \
  --fdr-max 0.05 --ontology BP --out results/GO_filtered.csv
cmg-seqviewer-cli plot results/GO_filtered.csv --plot-type go_dot \
  --out results/go_dot.png
```

### Many files with one recipe

```bash
cmg-seqviewer-cli batch recipe.yaml --inputs "data/*.xlsx" \
  --out-dir results/ --manifest results/manifest.json
```

### Compare two DE results

```bash
cmg-seqviewer-cli compare results/A_DE.csv results/B_DE.csv \
  --json --include-table --out results/comparison.csv
```

## 19.8 Troubleshooting

- **`No module named ...`** — use the installed `cmg-seqviewer-cli`, or run
  from the repository with `python src/cli.py` / `PYTHONPATH=src python -m cli`.
- **`Required columns not found`** — run `load` first to inspect the detected
  columns, then use `--type` or fix the input column names.
- **`Unsupported plot_type`** — run `cmg-seqviewer-cli schema --json` to see the
  current plot types.
- **`No data matches` / empty output** — loosen the filter thresholds; an empty
  result is still a successful command.
- **One file failed in `batch`** — the rest still ran; read the `[FAIL]` line
  and the `--manifest` entry for that file.
- **Paths with spaces** — quote them in the shell:
  `cmg-seqviewer-cli load "data/my sample.xlsx"`.
- **GUI is unavailable** — that is expected; all commands above run headlessly.

---
**See also**: [User Guide](../user-guide.md) · [FAQ](24-faq.md) · [AI Agent / MCP](19a-ai-agent-mcp.md)
