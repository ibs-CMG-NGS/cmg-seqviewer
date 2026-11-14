# MCP Privacy and Data Governance

> **Short version:** MCP tool output goes to your AI client and may be sent to a
> model provider. The server cannot control the client's retention, training, or
> transfer policy. Do not enable MCP for identifiable human data without
> institutional IRB/DPIA review.

## Threat model

- MCP results are transmitted to the AI client, which may forward them to a model
  provider.
- The client/provider may log, retain, or train on the content.
- A local MCP server does **not** mean the data stays local.
- MCP is optional and the SDK is not installed by default.

## Exposure levels

| Level | Name | Returned by default? | Contents |
|---|---|---|---|
| L0 | `schema_only` | yes | column names, dtypes, counts, metadata |
| L1 | `aggregate` | opt-in | group counts/means/top-N aggregates |
| L2 | `preview` | opt-in | small row preview (default 20, max 100) |
| L3 | `full` | never via MCP | full table; use CLI/local files |

Default policy is `schema_only`. `aggregate`, `preview`, images, writes, and
network access must be explicitly enabled per workspace.

## Consent and configuration

- The server starts in `schema_only` when `.cmg-mcp-policy.json` is absent.
- Higher exposure levels are recorded in the workspace policy file.
- A dataset may additionally carry an `ai_access` flag in its manifest/metadata
  (future integration); the MCP layer still enforces the workspace policy.
- `allow_network=false` blocks enrichment by default.
- `CMG_MCP_DISABLE=1` or `"enabled": false` disables the server.
- Uninstalling the optional `[mcp]` extra removes the server entirely.

## Network and enrichment

`allow_network=false` is the default. GO/KEGG enrichment requires
`allow_network=true` because even local runs may need annotation caches
(GO OBO, NCBI gene2go/gene_info, Enrichr GMT). Enrichment results contain
pathway names and gene symbols, so they also require `data_policy=aggregate`
or `preview`; a full enrichment table requires `preview`.

## Images and plots

Volcano, heatmap, and dot-plot images can contain gene symbols, cell types, and
condition names. `allow_images=false` is the default; enabling it requires a
project-level decision. Prefer aggregate/schema-only responses for exploratory
questions.

## Audit log

- Default: `~/.cmg-seqviewer/mcp_audit.jsonl`
- Recorded: timestamp, tool name, truncated dataset-handle hash, data policy,
  response size.
- Not recorded: row values, absolute paths, user names.
- Audit logging is local and best-effort; it is not a substitute for
  institutional data governance.

## Recommended practice

- Identifiable human data: obtain IRB/DPIA approval first; default MCP off.
- Prefer a local model (Ollama/llama.cpp) or an institution-approved provider.
- Keep the workspace root narrow and use relative artifact paths.
- Review `.cmg-mcp-policy.json` before sharing a project.
- Do not enable `preview` for a whole project just to answer one question; prefer
  a temporary policy and disable it afterward.
