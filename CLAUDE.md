# CLAUDE.md

Project-specific instructions for Claude Code when working in this repository.

## In-app help (F1) must stay in sync with GUI changes

The F1 help dialog (`src/gui/help_dialog.py`) is the only documentation most
users (non-programmer researchers) ever see. It is currently a set of
`_get_<section>()` methods that each return a hardcoded HTML string, keyed
off a table-of-contents list in `_load_content()` / `_on_toc_selection_changed()`.

**Whenever you add or change a user-visible GUI feature** — a new menu
action, dialog, keyboard shortcut, or a meaningfully changed workflow in
`src/gui/*.py` — check whether `src/gui/help_dialog.py` needs a matching
update:
- New menu action / shortcut → add it to the relevant section AND to the
  shortcut table in "13. Tips & Shortcuts".
- New dialog / workflow → add or extend the relevant numbered section (the
  TOC already uses letter suffixes like `5b`, `5c`, `7b` for features added
  after the original numbering — follow that pattern rather than
  renumbering everything).
- Changed workflow (e.g. a dialog that used to act immediately now opens a
  settings step first) → update the existing prose, don't just append.

Do not assume this is covered elsewhere: `docs/user/*.md` is a **separate,
independently-maintained set of docs** (not loaded by the app) that already
drifted out of sync with `help_dialog.py` once before (see e.g.
`docs/user/igv-integration-guide.md` and
`docs/user/atac-rna-integration-analysis-guide.md`, which existed for a
while with zero corresponding content in the F1 dialog). Treat the two as
independent surfaces that both need updating, unless/until they're
consolidated (see below).

## Known format issue (deferred, not yet scheduled)

`help_dialog.py`'s HTML-strings-in-Python-methods format is harder to
review/diff than plain text and is the reason it drifted. The considered
fix — consolidating `help_dialog.py` and `docs/user/*.md` into one set of
Markdown files rendered at runtime via Qt's built-in `QTextEdit.setMarkdown()`
(no new dependency) — was intentionally deferred (2026-08-26) to keep a
large content-refresh pass low-risk. If asked to do a bigger doc
infrastructure pass, that migration is the recommended direction; it would
also require updating PyInstaller data bundling (`*.spec`, `build.ps1`,
`build-macos.sh`) to ship the markdown files.
