# 20. FAQ

Scenario-based answers to the most common questions. Each answer links to the
section that explains the feature in depth.

## 20.1 Which engine should I use — online, local, offline, or auto?

**Auto** is the safe default: it uses Enrichr online when the network is
available and no custom background is set, and falls back to GOATOOLS local.
Choose **Online** for the widest database coverage (GO + KEGG), **Local /
Offline** when you want reproducible local statistics (or are behind a proxy /
no network), and **Offline** strictly when no network may be touched.
See **6. GO/KEGG Enrichment Analysis — Engine modes**.

## 20.2 Enrichment ran, but the dataset has no KEGG rows — is something wrong?

KEGG is analyzed **online only** in v1 (ADR-1 Option 1). In `Local`/`Offline`
mode the dialog shows "KEGG is inactive" and skips KEGG; run **Online** to
include KEGG. See **6. GO/KEGG Enrichment Analysis — Engine modes**.

## 20.3 Why are mouse GO results coming from the local engine even in Auto mode?

There is no mouse GO library on Enrichr (P0-7 finding), so mouse GO always runs
locally via GOATOOLS (taxid 10090). Mouse KEGG (`KEGG_2019_Mouse`) is available
online. See **6. GO/KEGG Enrichment Analysis — Mouse**.

## 20.4 Can I use my own background gene list?

Yes — load a background file in the analysis dialog. A custom background forces
the **local** engine (Enrichr does not support custom backgrounds;
ADR-2 2A). See **6. GO/KEGG Enrichment Analysis — Engine modes**.

## 20.5 What does "Done: N terms" mean, and where do the results go?

The dialog summarises the standardised result rows; the result is registered as
an `Enrichment: …` **GO_ANALYSIS dataset** and appears in the Dataset Tree with
the same standard columns (and order) as imported pipeline results. Open it with
the existing GO visualizations. See **6. GO/KEGG Enrichment Analysis** and
**5. GO/KEGG Analysis — Filtering GO/KEGG Results**.

## 20.6 The first run needs a download — can I work offline at all?

The first run downloads `go-basic.obo`, `gene2go`, `gene_info`, and GMT
snapshots into the AppData cache. Offline/uncached first run fails with a
"cache download" message; after any successful run the cache is reused
(sha256-verified, TTL auto-refresh, `HTTPS_PROXY` respected). See
**6. GO/KEGG Enrichment Analysis — Cache & reproducibility**.

## 20.7 My GO/KEGG terms aren't clustering — everything is a singleton?

Clustering uses the `_gene_set` column. If every row has an empty `_gene_set`
(the warning "all rows have empty _gene_set" in the log), the gene-list column
was not recognised. Imported/analyzed results normally carry `gene_symbols`, so
re-import or re-run through the standard path. See **5. GO/KEGG Analysis — GO
Term Clustering** and the **algorithm summary** there.

## 20.8 What is the difference between GSEA Lite and GSEA prerank?

**GSEA Lite (Wilcoxon)** is the built-in rank-based GSEA on predefined in-app
gene sets (Analysis menu). **GSEA prerank (gseapy)** is part of the GO/KEGG
enrichment pipeline — it runs `gseapy.prerank` with international gene sets
(GO/KEGG cached GMT) on a meta ranking. They are different features (A7
naming). See **8. Statistical Analysis — GSEA Lite** and **6. GO/KEGG
Enrichment Analysis — Meta-signature enrichment**.

## 20.9 Can I compare pipeline-imported GO results with in-app enrichment results?

Yes. Both go through the same standardisation (`term_id`, `description`,
`gene_set`, `fold_enrichment`, `_gene_set` with identical column order), so GO
Term Comparison and the visualization menus treat them identically. See
**7. GO Term Comparison**.

## 20.10 Will my enrichment results survive a project save/load?

Result rows are saved like other GO_ANALYSIS datasets; the request itself is
preserved in the dataset metadata as `enrichment_recipe`. **Auto re-run on
load is a v1 non-goal** — export the table for long-term storage. See
**6. GO/KEGG Enrichment Analysis — Cache & reproducibility** and
**17. Project Save/Load**.

## 20.11 The in-app help — how is it maintained?

F1 opens the viewer that renders `docs/user/help/*.md` (one file per section,
English). Edit the markdown files directly; images live in
`docs/user/help/assets/`. The long-form documentation is
`docs/user/user-guide.md`. See the **README/planning** docs for the overhaul
design (`docs/planning/HELP_SYSTEM_OVERHAUL_PLAN.md`).

---
**See also**: [User Guide](../user-guide.md)
