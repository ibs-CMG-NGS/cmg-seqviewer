# CMG-SeqViewer v1.5.0 Release Notes

- **Release date**: 2026-11-15
- **Previous release**: [v1.4.1](https://github.com/ibs-CMG-NGS/cmg-seqviewer/releases/tag/v1.4.1)
- **Full diff**: https://github.com/ibs-CMG-NGS/cmg-seqviewer/compare/v1.4.1...v1.5.0
- **Branch**: `chore/release-v1.5.0` (from `master`)

> **Known issue (fixed in v1.5.1):** v1.5.0 GUI installers show `Version 1.4.1` in the About dialog. Use the v1.5.1 GUI assets.

## Highlights

### AI agent integration (MCP)

- New headless MCP server: `cmg-seqviewer-mcp`.
- Installed as an optional extra: `pip install "rna-seq-data-analyzer[mcp]"`.
- Works with MCP clients such as Claude Desktop, Cursor, and Claude Code.
- Tools:
  - `list_datasets`, `load_dataset`, `describe_dataset`, `summarize_dataset`
  - `filter_dataset`, `compare_datasets`, `run_enrichment`
  - `query_rows`, `plot`, `export_table`, `close_dataset`, `get_help`
- Resources/prompts for F1 help, dataset schemas, pipeline integration, and
  DE/expression/composition/compare/enrichment workflows.
- Claude Code end-to-end verification: list/load/summarize/compare/help/filter/
  plot and the enrichment policy gate.

### Privacy and safety controls

- Default policy is `schema_only` (no row values).
- Row preview, images, writes, and network access are separate opt-ins.
- Workspace path allowlist blocks `..` and paths outside the project.
- JSONL audit log at `~/.cmg-seqviewer/mcp_audit.jsonl` (no row values,
  absolute paths, or user names).
- Kill switch: `CMG_MCP_DISABLE=1` or `"enabled": false`.
- Enrichment requires `allow_network=true` and `aggregate`/`preview` policy.

### Expanded CLI

- New commands: `summary`, `query`, `plot`, `export`, `datasets list|describe`,
  `compare`, `schema`, and `help`.
- `filter` now supports all four modes:
  - `statistical`
  - `gene_list` (`--gene-list-file`, `--term-id`)
  - `keyword` (`--keyword`, `--search-column`)
  - `column_subset` (`--columns`)
- `datasets` provides read-only database list/describe with JSON output.
- `compare` reuses the GUI's `StatisticalAnalyzer` for DE overlap analysis.

### Shared headless services and refactor

- New shared services under `src/services/`:
  `DatasetService`, `DatabaseService`, `FilterEngine`, `FilterService`,
  `AnalysisService`, `EnrichmentService`, `PlotService`, and `HelpService`.
- `FilterEngine` is the single pure filtering implementation used by the GUI
  `MainPresenter`, CLI, and MCP.
- `MainPresenter` delegates filter computation to `FilterEngine`; CLI/MCP no
  longer construct a presenter for filtering.

### Documentation

- New F1/website page: **19a. AI Agent / MCP (Experimental)**.
- Expanded **19. Command Line Interface** with command reference, mode examples,
  recipes, common workflows, and troubleshooting.
- New developer docs: MCP integration, MCP privacy, and GUI/CLI/MCP feature
  boundaries.

## Packaging and distribution

The desktop GUI installers remain **GUI-only**. They do not bundle the CLI or
MCP server.

- **GUI**: use the normal Windows/macOS installer assets.
- **CLI**: install the Python package and use `cmg-seqviewer-cli`:
  ```bash
  pip install rna-seq-data-analyzer
  cmg-seqviewer-cli --help
  ```
- **MCP**:
  ```bash
  pip install "rna-seq-data-analyzer[mcp]"
  cmg-seqviewer-mcp
  ```
- The MCP SDK is intentionally optional and is not included in the GUI
  installers. A separate CLI tools or AI tools installer may be considered in a
  future release.

## Validation

- `431 passed, 4 deselected`.
- `mkdocs build --strict` succeeds.
- Claude Code MCP E2E: list/load/summarize/compare/help/filter/plot and
  `NETWORK_DENIED` enrichment policy gate.
- Headless plot artifact generated and verified.
- MCP server health: `Status: Connected` in Claude Code.

## Upgrade notes

- Existing GUI workflows and project files are unchanged.
- CLI/MCP are opt-in; installing the GUI installer does not enable them.
- Existing v1.4.x datasets and bundles remain compatible.
- MCP is experimental. Start with `schema_only`; enable preview/images/write/
  network only for approved projects.

## Known limitations

- No GUI bridge or live GUI control.
- MCP has no full-table transfer (`L3`); use `export_table` or local CLI files.
- `run_enrichment` supports dataset-source ORA only (no paste/meta/prerank yet).
- MCP database tools are read-only (`datasets` is CLI-only); no DB import/edit/
  delete.
- Interactive column mapping, project save/load, IGV, gene annotation, and
  multi-omics remain GUI-only.
- CLI/MCP are not bundled in the desktop installers.

## Assets

The tag-triggered GitHub Actions workflow builds and publishes:

- `CMG-SeqViewer-Windows.zip`
- `CMG-SeqViewer-macOS.dmg`
