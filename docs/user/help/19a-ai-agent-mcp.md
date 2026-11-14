# 19a. AI Agent / MCP (experimental)

CMG-SeqViewer can expose a **headless MCP server** so an AI client you already
use (Claude Desktop, Cursor, etc.) can inspect datasets, apply filters, render
plots, export tables, and read the built-in help. The AI stays in your client;
the app does not include a chat assistant and the AI cannot click the GUI.

> **Privacy warning.** MCP tool results are sent to your AI client and may be
> logged, retained, or used by the model provider. A local server does **not**
> mean the data stays local. Do not enable MCP for identifiable human data
> without institutional IRB/DPIA review. The default is **schema only** (no row
> values); row preview, images, and writes are opt-in.

## Which interface should I use?

| Interface | Best for | AI agent? |
|---|---|---|
| GUI | Interactive exploration, dialogs, project state, IGV, annotation | No |
| CLI | Shell scripts, HPC/CI, recipes, batch processing | Not the standard AI path |
| MCP | Claude Desktop, Cursor, and other MCP clients | **Yes** |
| GUI bridge | Future: hand results to a running GUI | Future |

AI clients should call the **MCP server**, not shell out to `cmg-seqviewer-cli`.
CLI and MCP share the same `src/services/` layer, but they are not identical
surfaces: CLI has `run`/`batch`/`datasets`, while MCP adds resources/prompts and
the enrichment tool. The GUI remains the place for interactive work.

## Install

MCP is an optional extra, so a normal install does not include it:

```bash
pip install "rna-seq-data-analyzer[mcp]"
cmg-seqviewer-mcp
```

In a development checkout use `pip install -e ".[mcp]"`.

## Configure a workspace

Create `.cmg-mcp-policy.json` in the project folder you want the AI to access.
Start from this safe default:

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

Point your MCP client at the server and set the workspace explicitly:

```json
{
  "mcpServers": {
    "cmg-seqviewer": {
      "command": "cmg-seqviewer-mcp",
      "args": [],
      "env": {"CMG_MCP_WORKSPACE": "/path/to/project"}
    }
  }
}
```

`CMG_MCP_DISABLE=1` turns the server off. The optional
`CMG_MCP_POLICY` variable selects a different policy file.

## What the AI can do

- List loaded datasets and inspect schema, dtypes, counts, and metadata.
- Summarize a dataset and apply a filter to create a child dataset.
- Compare two or more DE datasets: overlap counts by default; gene lists need
  `aggregate`/`preview`, and a comparison table needs `preview`.
- Run GO/KEGG ORA on a DE dataset; this needs `allow_network=true` and an
  `aggregate`/`preview` data policy.
- Render a plot to a file (only when images and writes are enabled).
- Export a table to CSV/TSV/XLSX/Parquet (only when writes are enabled).
- Search the in-app help and read a help section.
- Read the pipeline integration spec and short workflow notes.

The AI **cannot** read full tables through MCP, access files outside the
workspace, or control the GUI. For full data, use the
[command-line interface](19-command-line-interface.md) or the app itself.

## Feature boundary (v1.2)

Supported through MCP:

- Dataset load/inspect/summary/query preview (preview is opt-in)
- Filtering (statistical, gene list, keyword, column subset)
- Headless plot rendering and table export (opt-in)
- DE dataset comparison
- Dataset-source GO/KEGG ORA (network opt-in)
- F1 help and schema/workflow resources

Not supported through MCP:

- Clicking or controlling the GUI; no GUI bridge yet
- Interactive column mapping
- Database import/edit/delete (MCP has no database tools)
- Project save/load, tabs, pinned plots, session state
- IGV integration, gene annotation, multi-omics integration
- Expression summary/distribution dialog-specific workflows
- Enrichment from pasted genes, meta-signature, or prerank (dataset-source ORA only)
- Full-table transfer (`L3`); use `export_table` or the CLI for local files

## Exposure levels

| Level | Meaning | Default |
|---|---|---|
| `schema_only` | column names, dtypes, counts, metadata | yes |
| `aggregate` | group counts/means/top-N aggregates | opt-in |
| `preview` | a small row preview (default 20, max 100) | opt-in |
| full table | not available through MCP | never |

Images can contain gene symbols, cell types, and condition names, so
`allow_images` is a separate opt-in. Plot artifacts also need `allow_write`;
table exports need `allow_write` as well. Comparison gene lists and enrichment
results are data values, so they require `data_policy=aggregate` or `preview`;
a comparison/enrichment table requires `preview`. Enrichment also needs
`allow_network=true` because even local runs may need annotation caches.
The local audit log at `~/.cmg-seqviewer/mcp_audit.jsonl` records tool names,
handle hashes, policy, and response sizes — not row values or absolute paths.

## v1.2 limitations

- Enrichment supports dataset-source ORA only (no paste/meta/prerank yet).
- No GUI bridge or live GUI control.
- No in-app chat; use your own MCP client.

---
**See also**: [Command-Line Interface](19-command-line-interface.md) ·
[Export, Clipboard, and Bundle](10-export-clipboard.md) ·
[FAQ](24-faq.md) · [User Guide](../user-guide.md)
