# Planning Documentation

> Current plans, verified against the v1.4.1 codebase (2026-10-23).
> Completed or superseded plans are retired to [archive/](archive/README.md).

## Active plans

| Document | Description | Status | Remaining work |
|---|---|---|---|
| [MCP / AI Agent integration](MCP_AGENT_INTEGRATION_PLAN.md) | Headless service layer + MCP tools for AI clients | Planned (Phase 0 not started) | Privacy/threat model, tool schema, headless service, MCP server |
| [Figure bundle handoff](FIGURE_QUALITY_REPRODUCIBILITY_PLAN.md) | Reproducible per-panel bundles for the external figure-atlas layout pipeline | P1 + P4 done; P2 validation active | coverage complete; metadata contract + headless validation ([audit](FIGURE_BUNDLE_COVERAGE.md)) |
| [Expression Distribution](EXPRESSION_DISTRIBUTION_PLAN.md) | Per-sample pseudobulk/quantile violin-box view | **v1.4.1 released** | Phase 3 cell-level store, full-atlas lazy DuckDB query, full-atlas export scope |
| [ATAC pipeline packaging](ATAC_PIPELINE_SEQVIEWER_PACKAGING.md) | Requirements for the external ATAC 3rd-party pipeline | External coordination | Pipeline-side manifest/companion fields |
| [RNA pipeline packaging](RNA_PIPELINE_SEQVIEWER_PACKAGING.md) | Requirements for the external RNA-seq 3rd-party pipeline | External coordination | Pipeline-side metadata/manifest fields |
| [External pipeline requirements](external_pipeline_requirements.md) | Figure-atlas external pipeline contract | Reference | Maintained with pipeline teams |

## Recently retired

The following plans were completed/superseded and moved to
[archive/](archive/README.md) on 2026-10-23:

- ATAC-seq integration plan (phases 1–3D)
- Multi-Group Heatmap (v1.2.1)
- Header standardization (v1.2.0)
- Dataset Tree Panel (v1.2.1)
- Online GO/KEGG enrichment plan + implementation plan (v1.3.x)
- Figure bundle export + Figure quality P1 implementation
- Meta-analysis (M1–M5)
- Project save/load
- F1 help system overhaul
- Expression Distribution analysis-team request (pilot completed; v1.4.1)

See [archive/README.md](archive/README.md) for the full list and completion
versions.

## Backlog (not scheduled)

These are ideas from earlier planning notes; none are committed to a release.

- Dark mode and user-selectable color themes
- Filter presets and expanded recent-files list
- Plugin system for custom analysis modules
- Cloud storage / collaboration links
- R script integration
- GPU acceleration
- ChIP-seq / Hi-C / multi-omics network extensions

## Notes

- Planning docs are intentionally not part of the MkDocs user-help site.
- The user-facing F1 help source is `docs/user/help/*.md`.
- Pipeline schema references live in
  [`docs/developer/pipeline-integration.md`](../developer/pipeline-integration.md).
