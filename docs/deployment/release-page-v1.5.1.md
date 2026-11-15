## CMG-SeqViewer v1.5.1

Patch release fixing the **About dialog version** in the GUI.

### Fixed

- The About dialog now reports **1.5.1** instead of the hardcoded `1.4.1`.
- Version now comes from the single source of truth (`src/version.py`).
- Added a regression test for the About dialog version.

### Distribution

GUI installers remain **GUI-only**. CLI/MCP are unchanged and remain available
from source/pip:

```bash
pip install rna-seq-data-analyzer
cmg-seqviewer-cli --help

pip install "rna-seq-data-analyzer[mcp]"
cmg-seqviewer-mcp
```

### Validation

- 432 tests passed, 4 deselected
- `mkdocs build --strict` succeeds
- Version consistency test covers the About dialog

### Upgrade

Replace the v1.5.0 GUI installation with v1.5.1. No data/project migration is
needed.

### Full changes

- Compare: https://github.com/ibs-CMG-NGS/cmg-seqviewer/compare/v1.5.0...v1.5.1
- Release notes: https://github.com/ibs-CMG-NGS/cmg-seqviewer/blob/master/docs/deployment/release-notes-v1.5.1.md
