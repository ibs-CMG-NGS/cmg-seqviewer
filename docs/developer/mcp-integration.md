# MCP Integration (v1)

> Status: v1.2 headless server implemented and Claude Code E2E verified
> (2026-11-15). Phase 1 services/CLI are shared; the optional GUI bridge is not
> v1.2. Read [MCP privacy](mcp-privacy.md) before enabling anything beyond
> `schema_only`.

## Install and run

The MCP SDK is an **optional extra**; the normal GUI install does not need it.

```bash
# development checkout
pip install -e ".[mcp]"
cmg-seqviewer-mcp

# released wheel/sdist
pip install "rna-seq-data-analyzer[mcp]"
cmg-seqviewer-mcp
```

The server uses **stdio only** and keeps dataset handles in memory for the
session. It does not open a port and does not call an LLM.

### Workspace and policy

```bash
export CMG_MCP_WORKSPACE=/path/to/project
export CMG_MCP_POLICY=/path/to/project/.cmg-mcp-policy.json   # optional
cmg-seqviewer-mcp
```

If `CMG_MCP_WORKSPACE` is unset, the process working directory is the workspace.
A `.cmg-mcp-policy.json` in the workspace is loaded automatically. Without one,
the server starts in `schema_only` mode.

```json
{
  "data_policy": "schema_only",
  "allow_row_preview": false,
  "allow_images": false,
  "allow_write": false,
  "allow_network": false,
  "max_preview_rows": 20,
  "enabled": true
}
```

- `data_policy`: `schema_only` (default), `aggregate`, or `preview`.
- `preview` implies `allow_row_preview=true`; setting `allow_row_preview=true`
  without `data_policy=preview` is a configuration error.
- `allow_images`, `allow_write`, and `allow_network` are separate opt-ins.
- `max_preview_rows` is capped at 100.
- `CMG_MCP_DISABLE=1` is the kill switch; `enabled: false` also disables the
  server.

## Client configuration

Claude Desktop (`claude_desktop_config.json`) and Cursor (`mcp.json`) both use an
`mcpServers` map. Point the command at the console script and set the workspace
explicitly:

```json
{
  "mcpServers": {
    "cmg-seqviewer": {
      "command": "cmg-seqviewer-mcp",
      "args": [],
      "env": {
        "CMG_MCP_WORKSPACE": "/path/to/project"
      }
    }
  }
}
```

Use an absolute path to the environment's `cmg-seqviewer-mcp` if the client does
not inherit your shell `PATH`. Restart the client after changing the config.

### Manual E2E smoke test (Claude Code)

```bash
claude mcp add --scope local cmg-seqviewer-e2e \
  -e CMG_MCP_WORKSPACE=/absolute/project/path \
  -- /absolute/venv/bin/cmg-seqviewer-mcp
claude mcp get cmg-seqviewer-e2e          # expect Status: Connected
```

Then, after logging in (`/login` in Claude Code), ask it to call
`list_datasets`, `load_dataset`, `summarize_dataset`, and `compare_datasets`.
Verified with Claude Code 2.1.197 on 2026-11-15: list/load/summarize/compare/
help/filter/plot, plus the `NETWORK_DENIED` enrichment policy gate. Automated
tests use a Python MCP client.

## Tools (v1.2)

| Tool | Purpose | Policy |
|---|---|---|
| `list_datasets` | List handles loaded in this session. | always |
| `load_dataset` | Load a workspace file; return handle, schema, counts. | always |
| `describe_dataset` | Type, rows, columns, dtypes, required columns, metadata. | always |
| `summarize_dataset` | JSON-safe dataset summary. | always |
| `filter_dataset` | Apply a filter; return a new child handle and counts. | always |
| `compare_datasets` | Compare >=2 DE handles; counts by default. | always (gene lists: `aggregate`/`preview`; table: `preview`) |
| `run_enrichment` | GO/KEGG ORA on a DE handle. | `allow_network` + `aggregate`/`preview`; table: `preview` |
| `query_rows` | Small row preview (default 20, max 100). | `preview` |
| `plot` | Render a registered plot type to a workspace file. | `allow_images` + `allow_write` |
| `export_table` | Export a handle to CSV/TSV/XLSX/Parquet. | `allow_write` |
| `close_dataset` | Release a handle. | always |
| `get_help` | List/search F1 help or return one section as Markdown. | always |

`plot` needs both `allow_images` and `allow_write` because the image is an artifact.
`plot_type` is validated by `plots.registry`; v1 supports all registered
headless renderers, including `volcano`, `heatmap`, `pca`, `composition`,
`expression_dot`, `go_dot`, `go_bar`, `multi_group_heatmap`, and
`gene_expression_bar`. Plot parameters use the same names as the CLI
`--params-json`.

Successful responses include `schema_version` and `data_policy`. Artifacts
return a **workspace-relative** path plus SHA-256; absolute paths and row values
are not returned by default. `compare_datasets` returns overlap counts only
unless gene lists (`aggregate`/`preview`) or a table (`preview`) are explicitly
requested.

## Resources and prompts

Resources:

- `help://index` — JSON list of F1 help sections.
- `help://section/{slug}` — one help section as Markdown.
- `schema://dataset/{dataset_type}` — required standard columns.
- `docs://pipeline-integration` — pipeline integration specification.
- `workflow://de-analysis`, `workflow://expression-summary`,
  `workflow://composition`, `workflow://compare-datasets`, `workflow://enrichment` — short workflow notes.

Prompts:

- `de-analysis`
- `expression-summary`
- `composition`
- `compare-datasets`
- `enrichment`

## Errors

Tool errors are structured and contain no data values:

```json
{"error_code": "ROW_PREVIEW_DENIED", "message": "...", "hint": "..."}
```

Common codes: `MCP_DISABLED`, `WRITE_DENIED`, `ROW_PREVIEW_DENIED`,
`IMAGES_DENIED`, `NETWORK_DENIED`, `ENRICHMENT_POLICY_DENIED`,
`PATH_OUTSIDE_WORKSPACE`, `UNKNOWN_HANDLE`, `BAD_TYPE`, `BAD_FILTER_MODE`,
`BAD_FILTER_KEY`, `FILTER_EMPTY`, `ENRICHMENT_NO_INPUT_GENES`, `INTERNAL_ERROR`.

## Audit log

The default audit log is `~/.cmg-seqviewer/mcp_audit.jsonl` (local JSONL). Each
line records timestamp, tool, a truncated dataset-handle hash, data policy, and
response size. It does **not** record row values, absolute paths, or user names.

## v1.2 limitations

- `compare_datasets` returns counts only by default; set `include_genes=true`
  with `aggregate`/`preview`, or `include_table=true` with `preview`.
- `run_enrichment` supports dataset-source ORA only (no paste/meta/prerank yet).
- `aggregate` is accepted by policy, but `summarize_dataset` returns the
  metadata summary; grouped aggregate tools are future work.
- No full-table transfer (`L3`); use `export_table` and a local file.
- No GUI bridge or live GUI control.
- No in-app chat assistant; the AI stays in the researcher's MCP client.

See [MCP privacy](mcp-privacy.md) and the
[planning document](../planning/MCP_AGENT_INTEGRATION_PLAN.md).
