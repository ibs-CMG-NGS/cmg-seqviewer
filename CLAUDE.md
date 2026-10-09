# CLAUDE.md

Project-specific instructions for Claude Code when working in this repository.

## In-app help (F1) must stay in sync with GUI changes

The F1 help dialog (`src/gui/help_dialog.py`) is the only documentation most
users (non-programmer researchers) ever see. Since the Markdown migration
(`docs/planning/HELP_SYSTEM_OVERHAUL_PLAN.md`), its content lives entirely in
`docs/user/help/NN-slug.md` — one file per numbered section, rendered at
runtime via `QTextBrowser.setMarkdown()`. The dialog builds its table of
contents by listing that directory (filename order) and reading each file's
first `# ` heading as the title; there is no separate TOC list to maintain
in Python anymore.

**Whenever you add or change a user-visible GUI feature** — a new menu
action, dialog, keyboard shortcut, or a meaningfully changed workflow in
`src/gui/*.py` — check whether a `docs/user/help/*.md` file needs a matching
update:
- New menu action / shortcut → add it to the relevant section's `.md` AND to
  the shortcut table in `19-tips-shortcuts.md`.
- New dialog / workflow → add or extend the relevant file, or add a new
  `NN-slug.md` (the existing numbering has gaps from past insertions — match
  that pattern rather than renumbering everything).
- Changed workflow (e.g. a dialog that used to act immediately now opens a
  settings step first) → update the existing prose, don't just append.
- New images referenced via `![...](assets/foo.png)` go in
  `docs/user/help/assets/`.

`docs/user/*.md` **outside** the `help/` subfolder (e.g.
`docs/user/igv-integration-guide.md`,
`docs/user/atac-rna-integration-analysis-guide.md`, `user-guide.md`) is a
**separate, independently-maintained set of docs** that is not loaded by the
app and has drifted out of sync before. Only `docs/user/help/*.md` is the
synced source — don't assume an edit there is covered by also editing (or
not editing) the broader `docs/user/*.md` set, or vice versa.

## Help docs are also published as a website

`docs/user/help/*.md` — the exact same files the F1 dialog renders — are
also built into a static site (`mkdocs.yml`) and deployed to GitHub Pages by
`.github/workflows/docs.yml` on every push to `master` that touches
`docs/user/help/**`. `mkdocs.yml` has no `nav:` on purpose: MkDocs falls
back to auto-generating navigation from the file listing sorted by filename,
using each page's first `# ` heading — the same rule `help_dialog.py` uses
for its TOC. This means editing/adding `docs/user/help/*.md` files updates
both surfaces automatically; don't add a `nav:` list or an `index.md` to
`docs/user/help/` to fix a site-navigation issue, since either would
desync it from the in-app TOC (the one exception — the generated site's
root-redirect `index.html` — is injected at deploy time by the workflow
itself, not committed to `docs/user/help/`).

Known gap: every help page's "See also" line links to `../user-guide.md`,
which is outside `docs/user/help/` (and thus outside the website's scope) —
that link renders fine in-app but 404s on the website.
`mkdocs.yml`'s `validation.links.not_found: ignore` exists specifically to
keep that known, intentional gap from failing `mkdocs build --strict` in CI;
don't tighten it without also resolving the underlying link.
