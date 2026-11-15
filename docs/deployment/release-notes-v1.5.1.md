# CMG-SeqViewer v1.5.1 Release Notes

- **Release date**: 2026-11-15
- **Previous release**: [v1.5.0](https://github.com/ibs-CMG-NGS/cmg-seqviewer/releases/tag/v1.5.0)
- **Full diff**: https://github.com/ibs-CMG-NGS/cmg-seqviewer/compare/v1.5.0...v1.5.1
- **Branch**: `chore/release-v1.5.1` (from `master`)

## Fix

### About dialog version

v1.5.0 GUI builds displayed **Version 1.4.1** in the About dialog because the
string was hardcoded in `src/gui/main_window.py`. v1.5.1 reads the version from
the single source (`src/version.py`) and displays **1.5.1**.

A regression test now checks that the About dialog uses `APP_VERSION` and does
not contain a hardcoded version string.

## Distribution

No packaging boundary changes:

- GUI installers remain **GUI-only**.
- CLI/MCP remain available from source/pip:
  - `pip install rna-seq-data-analyzer` → `cmg-seqviewer-cli`
  - `pip install "rna-seq-data-analyzer[mcp]"` → `cmg-seqviewer-mcp`
- MCP privacy defaults and feature coverage are unchanged from v1.5.0.

## Validation

- `432 passed, 4 deselected`.
- `mkdocs build --strict` succeeds.
- Version-consistency test covers the About dialog.
- GUI asset version metadata checked from the build artifact.

## Upgrade notes

- Replace the v1.5.0 GUI installation with v1.5.1.
- No dataset, project, or database migration is required.
- v1.5.0 GUI assets have the wrong About version; functionality is otherwise
  unchanged.

## Assets

The tag-triggered GitHub Actions workflow builds and publishes:

- `CMG-SeqViewer-Windows.zip`
- `CMG-SeqViewer-macOS.dmg`
