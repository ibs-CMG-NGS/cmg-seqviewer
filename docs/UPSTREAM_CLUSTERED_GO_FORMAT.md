# Upstream Clustered-GO Output Format (for CMG-SeqViewer)

**Purpose** — Move GO-term clustering into the upstream pipeline (secondary
analysis) and export the result as **Excel or Parquet** so CMG-SeqViewer can
import it and draw the **Cluster Dot Plot** directly, without re-running the
in-app "Cluster GO Terms" step.

CMG-SeqViewer recognizes a GO table as *clustered* when it contains a
**`cluster_id`** column, and it (re)computes each cluster's **representative
term** (min-FDR member) and **member count** itself. So the pipeline only needs
to emit standard GO enrichment columns **plus a `cluster_id` assignment**.

---

## 1. Required / recognized columns

Header names below are the ones CMG-SeqViewer's GO loader maps automatically
(case-insensitive; `.`/space variants accepted). One row = one GO/KEGG term.

| Column (use this header) | Maps to | Required | Notes |
|---|---|---|---|
| `GO ID` (or `KEGG ID`, `Term ID`) | `term_id` | ✔ | term identifier |
| `GO Term` (or `KEGG Pathway`, `Description`) | `description` | ✔ | dot-plot y-labels |
| `Gene Ratio` | `gene_ratio` | ✔ | e.g. `12/300` (string) |
| `Background Ratio` | `bg_ratio` | ✔ | e.g. `120/28891` (string) |
| **`Adjusted P-value`** (or `FDR`, `p.adjust`) | `fdr` | ✔ | **do NOT name it `padj`** — see §5 |
| `P-value` | `pvalue` | ○ | |
| `Gene Count` | `gene_count` | ○ | numerator of Gene Ratio; enables dot size = gene count and the Count filter |
| `Gene Symbols` (or `Genes`, `geneID`) | `gene_symbols` | ○ | `/`-separated list, e.g. `TP53/EGFR/MYC` |
| `Gene Set` | `gene_set` | ✔* | the gene list this GO was run on (e.g. `UP`, `DOWN`, `TOTAL`, or `Cluster01`) — becomes the "Gene Set" filter |
| `Ontology` | `ontology` | ✔* | `BP` / `CC` / `MF` / `KEGG` |
| **`cluster_id`** | `cluster_id` | ✔ | **the clustering result — see §2** |

`✔*` — if omitted, `Gene Set`/`Ontology` are inferred from the sheet name
(e.g. a sheet named `UP_BP`), but providing explicit columns is cleaner.

- **`fold_enrichment` is derived automatically** as `gene_ratio ÷ bg_ratio`; no
  need to precompute it.
- Internal helpers (`_gene_set`, `is_representative`, `representative_term`) are
  **not** needed — CMG-SeqViewer derives them.

---

## 2. `cluster_id` — the one column that matters

- **Type: string.** Members of a real cluster must be **digit strings**.
  Zero-padded is recommended for stable sorting: `"001"`, `"002"`, ….
  (Integers `1, 2` are **not** recognized as clusters — must be strings.)
- **Singletons** (terms not in any multi-term cluster): use a **non-digit**
  value, e.g. `"Singleton"` (or `"-1"`). These are excluded from the cluster
  view by default and shown as size-1 items when "Include singletons" is on.
- **Make `cluster_id` globally unique across the whole file.** Cluster GO terms
  *within each* `Gene Set × Ontology` group (e.g. BP-UP separately from BP-DOWN),
  but number them so `"001"` never means two different clusters in one file.
  Example numbering: `BP-UP → 001–005`, `BP-DOWN → 006–009`, `KEGG-UP → 010…`.
  - Why: the dot plot groups rows by `cluster_id`. If IDs collide across groups
    and the user plots without filtering to one group first, distinct clusters
    would merge. Globally-unique IDs avoid this. (Alternatively, always filter to
    one Gene Set × Ontology before plotting.)

---

## 3. Clustering method (to match the in-app result)

CMG-SeqViewer's built-in clustering, if you want to reproduce it exactly:

- **Similarity** = **Jaccard** of each term's gene set: `|A∩B| / |A∪B|`
  (genes from the `Gene Symbols` list).
- **Linkage** = hierarchical, **average linkage**.
- **Cut** at distance = `1 − similarity_threshold`; default
  **`similarity_threshold = 0.7`** → cut at distance 0.3.
- **Singletons** (final cluster size 1) are separated out.

You are free to use your own method (e.g. overlap coefficient, semantic
similarity) — CMG-SeqViewer only reads the resulting `cluster_id`.

---

## 4. File layout

Either format works; the loader concatenates **all sheets** (Excel) into one GO
dataset.

**Excel (.xlsx)** — one sheet per `Gene Set × Ontology` group is fine
(e.g. `cluster1_BP`, `cluster1_KEGG`, `UP_BP`, `DOWN_BP`, …), each carrying the
columns above including `cluster_id`. Avoid sheet names containing
`info` / `metadata` / `analysis` (those are skipped as metadata sheets).

**Parquet (.parquet)** — a single long table with all rows and the columns
above. Preserves dtypes, so keep `cluster_id` as a **string** column and
`Gene Symbols` as a `/`-joined string.

---

## 5. Gotchas (please follow)

- **Adjusted-p header must be `Adjusted P-value` / `FDR` / `p.adjust` — never
  `padj`.** A column literally named `padj` makes the importer misdetect the
  file as differential-expression data and load only the first sheet.
- **`cluster_id` must be strings**, digit-strings for members (`"001"`),
  non-digit for singletons (`"Singleton"`).
- **`Gene Symbols` uses `/` as the delimiter** (needed only if you want in-app
  re-clustering / the cluster network; not required for the dot plot).
- Keep `Gene Ratio` / `Background Ratio` as `"num/den"` strings (fold enrichment
  is computed from them).

---

## 6. Minimal example (one group)

| Gene Set | Ontology | GO ID | GO Term | Gene Ratio | Background Ratio | Adjusted P-value | Gene Count | Gene Symbols | cluster_id |
|---|---|---|---|---|---|---|---|---|---|
| UP | BP | GO:0006955 | immune response | 18/300 | 210/28891 | 2.1e-07 | 18 | IL6/TNF/… | 001 |
| UP | BP | GO:0002376 | immune system process | 22/300 | 260/28891 | 5.0e-07 | 22 | IL6/CD8A/… | 001 |
| UP | BP | GO:0007049 | cell cycle | 15/300 | 190/28891 | 8.3e-06 | 15 | CCNB1/CDK1/… | 002 |
| UP | BP | GO:0051301 | cell division | 12/300 | 150/28891 | 3.1e-05 | 12 | CDK1/AURKB/… | 002 |
| UP | BP | GO:0016567 | protein ubiquitination | 9/300 | 300/28891 | 4.0e-03 | 9 | UBE2C/… | Singleton |

## 7. Using it in CMG-SeqViewer

1. Import the Excel/Parquet (`+` Add Dataset). It loads as a GO dataset with the
   `cluster_id` column preserved.
2. (Optional) Statistical Filter → pick `Ontology` and `Gene Set` (now lists your
   actual groups) to narrow to one group.
3. **GO Analysis → Cluster Dot Plot** — opens directly because a `cluster_id`
   column is present (no in-app "Cluster GO Terms" step needed). Color = fold
   enrichment, size = cluster member count; "Include singletons" and "Top N by"
   are available. Export Bundle for a reproducible figure.
