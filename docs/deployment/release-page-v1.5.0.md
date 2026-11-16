## CMG-SeqViewer v1.5.0

Minor release adding a **headless MCP server for AI clients** and a substantially
expanded CLI, while keeping the desktop GUI installers unchanged.

> **Known issue (fixed in v1.5.1):** v1.5.0 GUI installers show `Version 1.4.1` in the About dialog. Use the v1.5.1 GUI assets.

### AI agent integration

- New optional MCP server: `cmg-seqviewer-mcp`
- Works with Claude Desktop, Cursor, and Claude Code
- Load/inspect/summarize/filter/compare datasets
- Render plots and export tables (opt-in)
- Run dataset-source GO/KEGG ORA (network opt-in)
- Read F1 help, schemas, and workflow prompts

Install MCP separately:

```bash
pip install "rna-seq-data-analyzer[mcp]"
cmg-seqviewer-mcp
```

> **Privacy:** MCP results go to your AI client and may be retained or used by
> the model provider. Default is `schema_only`; row preview, images, writes, and
> network access are opt-in. Do not enable MCP for identifiable human data
> without IRB/DPIA review.

### Expanded CLI

```bash
pip install rna-seq-data-analyzer
cmg-seqviewer-cli --help
```

New commands include `summary`, `query`, `plot`, `export`, `datasets`,
`compare`, `schema`, and `help`. `filter` now supports:

- `statistical`
- `gene_list` (`--gene-list-file`, `--term-id`)
- `keyword` (`--keyword`, `--search-column`)
- `column_subset` (`--columns`)

### Important distribution note

The Windows/macOS GUI installers are **GUI-only**. They do not include the CLI
or MCP server. CLI/MCP are available from source/pip as above. A separate CLI
tools or AI tools package may be considered later.

### Validation

- 431 tests passed, 4 deselected
- `mkdocs build --strict` succeeds
- Claude Code MCP E2E verified
- Headless plot artifact and MCP policy gate verified

### Documentation

- [AI Agent / MCP help](https://github.com/ibs-CMG-NGS/cmg-seqviewer/blob/master/docs/user/help/19a-ai-agent-mcp.md)
- [CLI help](https://github.com/ibs-CMG-NGS/cmg-seqviewer/blob/master/docs/user/help/19-command-line-interface.md)
- [MCP integration](https://github.com/ibs-CMG-NGS/cmg-seqviewer/blob/master/docs/developer/mcp-integration.md)
- [v1.5.0 release notes](https://github.com/ibs-CMG-NGS/cmg-seqviewer/blob/master/docs/deployment/release-notes-v1.5.0.md)

### Full changes

- Compare: https://github.com/ibs-CMG-NGS/cmg-seqviewer/compare/v1.4.1...v1.5.0
