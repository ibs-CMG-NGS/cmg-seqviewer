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
- Render a plot to a file (only when images and writes are enabled).
- Export a table to CSV/TSV/XLSX/Parquet (only when writes are enabled).
- Search the in-app help and read a help section.
- Read the pipeline integration spec and short workflow notes.

The AI **cannot** read full tables through MCP, access files outside the
workspace, or control the GUI. For full data, use the
[command-line interface](19-command-line-interface.md) or the app itself.

## Exposure levels

| Level | Meaning | Default |
|---|---|---|
| `schema_only` | column names, dtypes, counts, metadata | yes |
| `aggregate` | group counts/means/top-N aggregates | opt-in |
| `preview` | a small row preview (default 20, max 100) | opt-in |
| full table | not available through MCP | never |

Images can contain gene symbols, cell types, and condition names, so
`allow_images` is a separate opt-in. Plot artifacts also need `allow_write`;
table exports need `allow_write` as well.
The local audit log at `~/.cmg-seqviewer/mcp_audit.jsonl` records tool names,
handle hashes, policy, and response sizes — not row values or absolute paths.

## v1 limitations

- `compare_datasets`, enrichment, and network tools are not in v1.
- No GUI bridge or live GUI control.
- No in-app chat; use your own MCP client.

---
**See also**: [Command-Line Interface](19-command-line-interface.md) ·
[Export, Clipboard, and Bundle](10-export-clipboard.md) ·
[FAQ](24-faq.md) · [User Guide](../user-guide.md)
