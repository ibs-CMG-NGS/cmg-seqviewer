# Phase 0 PoC — GO/KEGG Enrichment Engine Feasibility Verification Report

- Date: 2026-09-02 (UTC+09:00) · Repo: `/home/ygkim/cmg-seqviewer` (no product source modified)
- Authority: `docs/planning/ON_GO_ENRICHMENT_IMPLEMENTATION_PLAN.md` v1.1 (§10-0 Phase 0, §5 options, §15 verification)
- All scripts/artifacts: `docs/planning/generated/phase0_poc/` (report: `docs/planning/generated/phase0_poc_report.md`)
- Env: headless Qt (`QT_QPA_PLATFORM=offscreen`), matplotlib backend Agg; no git/gjc/formatter commands run; `src/`, `test/`, `requirements.txt`, `setup.py`, `*.spec` untouched.

---

## Summary

All seven Phase 0 gates **PASS** (P0-1…P0-7). The hybrid-engine architecture (Option 1: GOATOOLS local + Enrichr online + cached GMT) is technically feasible on the current stack (Python 3.12.3, pandas 3.0.5, numpy 2.5.2, scipy 1.18.1). Key confirmations:

- **Enrichr online** works (`GO_Biological_Process_2023`: 723 terms/1.97 s; `KEGG_2021_Human`: 107 terms/1.46 s), `Overlap` is `k/n`, `Genes` is `;`-joined, GO Terms embed `GO:xxxxxxx`, **KEGG Terms contain NO `hsa` IDs** (0/107) → ADR-4 4A confirmed.
- **enrichr() accepts a `background` parameter, but for Enrichr library names gseapy 1.3.1 routes it to the experimental Speedrichr API** (package-source verified, `gseapy/enrichr.py:731-737`); the published docstring's "ignored for library names" line is stale doc-code drift and **no P0-2 run empirically passed `background=`**. Enrichr-online custom background is therefore unsupported in v1 **by decision** (Speedrichr = unvalidated third-party service; ToS/privacy/reproducibility) → **ADR-2 2A** (mode forcing) confirmed.
- **GOATOOLS local** runs end-to-end (human 2,223 + mouse 4,343 result terms; run_study ≈ 0.1 s); **3 goatools-1.6.5-specific incompatibilities** found (module path moved, `fisher_scipy` method string removed, statsmodels 0.15 removed `sandbox.stats.multicomp`) — all fixable in Phase 1, none blockers.
- **gene_info local mapping** works (63/100 human-symbol coverage on a mouse-derived input list; full-file pandas parse of the 1.57 GB gzipped / 10.35 GB uncompressed file succeeded at +3.3 GB peak — Phase 1 should stream-filter per species).
- **Converter contract asserts A–G all PASS** (12/12) on both engines; loader round-trip through `GOKEGGLoader._standardize_columns` PASS.
- **All 4 GO dialogs + clustering smoke PASS**; clustering merges ≥1 pair at threshold 0.3 (max Jaccard 1.0000).
- **Regression**: no failures attributable to the new dependencies (test-suite drift pre-exists; `test_figure_bundle_export` green).
- **Mouse (A3)**: local GOATOOLS taxid 10090 PASS; Enrichr has **NO mouse GO Biological Process library** (only `KEGG_2019_Mouse` among GO/KEGG-named mouse sets) → mouse=local-first policy confirmed.

---

## Environment (P0-1) — **PASS**

| Item | Value |
|---|---|
| Python | 3.12.3 (pip 24.0) |
| pandas | 3.0.5 (unchanged by install) |
| numpy | 2.5.2 (unchanged) |
| scipy | 1.18.1 (unchanged) |
| PyQt6 | 6.11.0 (unchanged) |
| gseapy | 1.3.1 (new) |
| goatools | 1.6.5 (new) |
| mygene | 3.2.2 (new) |
| statsmodels | 0.15.0 (new) |
| requests | 2.34.2 (new) |
| Added transitive | anyio, biothings-client, certifi, charset-normalizer, formulaic, ftpretty, h11, httpcore, httpx, idna, interface-meta, markdown-it-py, mdurl, patsy, pydot, rich, urllib3, wrapt, xlsxwriter (19 total; +5 top-level = 24 pip additions) |
| `pip check` | "No broken requirements found." |

Evidence: `p0-1_pip_install.txt`, `baseline_freeze.txt` (53 pkgs) vs `final_freeze.txt` (77 pkgs) — **diff shows additions only (24 added: 19 transitive + 5 top-level); pandas/numpy/scipy untouched** (verified, QA-lane diff re-checked). Full install/import log incl. deep imports: `p0-1_import_check_output.txt`.

**Import findings (F11 + plan-command drift):**
1. `from goatools.goea_go_enrich_nss import GOEnrichmentStudyNS` **FAILS** in goatools 1.6.5 — module renamed to `goatools.goea.go_enrichment_ns` (class name unchanged). Plan §10-0 command needs the new path.
2. `GODag`, `Gene2GoReader`, `gseapy.enrichr/enrich/prerank/get_library_name`, `statsmodels.stats.multitest.multipletests` all import OK.
3. F11 Python-requirement note: `requirements.txt` header says "Requires: Python 3.9 or higher" and `docs/user/python-installation.md` says "Python 3.9 이상 (3.11 권장)" — **pandas 3.x requires Python ≥ 3.10** (3.12.3 verified working here). Docs are stale; recommend updating to "3.10+ (3.11/3.12 recommended)" during Phase 1/2 (files NOT edited per constraints).

---

## Enrichr real call (P0-2) — **PASS**

Input: 100 genes — unique non-empty `gene_name` values from `examples/Acute_1D_vs_Control_DA.parquet` (2,509 unique; first 100), uppercased (`GM29233, CTGF, GM15725, ACTB, ACTG2, …`). Calls: `gseapy.enrichr(gene_list=genes, gene_sets=[...], organism='human', outdir=None, no_plot=True)`.

| Call | Wall | Shape |
|---|---|---|
| GO_Biological_Process_2023 | 1.97 s | 723 × 10 |
| KEGG_2021_Human | 1.46 s | 107 × 10 |

(a) **Exact columns**: `Gene_set, Term, Overlap, P-value, Adjusted P-value, Old P-value, Old Adjusted P-value, Odds Ratio, Combined Score, Genes` (same for both).

(b) **Overlap format** — `k/n` strings (3 each):
- GO: `'3/14'`, `'4/42'`, `'6/163'`
- KEGG: `'6/152'`, `'6/169'`, `'5/124'`

(c) **Genes separator** — `;`-joined symbols (samples): `IGFBP3;SERPINE1;TPM1`, `COL1A1;COL3A1;COL1A2;LOXL1`, `ITGB1;TUBA1C;TUBA1B;TUBA1A;CALR;ACTB`.

(d) **KEGG Term cell content** — human-readable names only, **NO `hsa#####` IDs** (0/107 rows contain `hsa\d+`):
- `'Phagosome'`
- `'Tight junction'`
- `'Platelet activation'`

(e) **GO Term cell content** — embeds `GO:0000000` in parentheses (723/723 rows):
- `'Negative Regulation Of Smooth Muscle Cell Migration (GO:0014912)'`
- `'Collagen Fibril Organization (GO:0030199)'`
- `'Negative Regulation Of Cell Migration (GO:0030336)'`

(f) **Background support (G8/ADR-2 evidence — architect-corrected)**: `inspect.signature(gseapy.enrichr)` confirms a `background` parameter exists (`background: Union[List[str], int, str] = None`). Package-source check (gseapy 1.3.1 `enrichr.py:731-737`) shows that for **Enrichr library names** a set/list background is routed to the **experimental Speedrichr** endpoint (`addbackground`/`backgroundenrich`) — NOT ignored; the docstring line "Ignored when using Enrichr library names" (`gseapy/__init__.py:544-546`) is stale doc-code drift. **P0-2 did not empirically call `background=`** (recorded as a Phase 1 `-m network` test). Verdict unchanged: **ADR-2 2A (mode forcing)** — Enrichr-online custom background is rejected in v1 on ToS/privacy/reproducibility grounds (unvalidated third-party Speedrichr), and only the local path (GOATOOLS / local GMT `enrich`) honors custom backgrounds. Phase 1 `EnrichmentAnalyzer` must guard: never pass `background` to online calls.

Saved DataFrames: `enrichr_go_bp_2023.csv`, `enrichr_kegg_2021_human.csv`.

(nit) `p0-2_format_inspect.py` prints `all GO Terms have GO id embedded: False` — an `np.bool_` identity-check artifact in that exploratory script; the independent count 723/723 in (e) is correct.

---

## GOATOOLS local (P0-3) — **PASS**

### Downloads (recorded in `p0-3_download_manifest.json`, raw files deleted after hashing — sizes/times/sha are the durable evidence)

| Artifact | Bytes | Wall | sha256 (truncated) |
|---|---|---|---|
| `go-basic.obo` (uncompressed) | 32,227,785 (≈30.7 MB) | 3.36 s | `b08d45b2…` |
| `gene2go.gz` (all species) | 1,380,328,182 (≈1.38 GB) | 197.9 s | `30270747…` |
| `gene_info.gz` (all species) | 1,573,751,788 (≈1.57 GB) | 221.0 s | `6823dcac…` |

- **F8 note**: uncompressed obo confirmed ≈30.7 MB (plan's "비압축 ~30-40MB"). The compressed `go-basic.obo.gz` (~8 MB per plan) could **not** be re-pulled from the primary mirrors during the PoC: geneontology.org `.gz` path → 403/AccessDenied, `current.geneontology.org` → 403, release archives → 404 for tested dates. Phase 1 must locate a working gz mirror (or accept the uncompressed file).
- gene2go/gene_info uncompressed sizes measured: 10.99 GB / 10.35 GB (72.0 M / 124.6 M rows) → **full in-memory reads are memory-hostile; Phase 1 must stream-filter per species** (done here for gene2go; gene_info full parse measured for evidence, see below).

### gene_info local mapping (G9) — PASS

- Full-file pandas read of `gene_info.gz` (72,035,010 rows, 3 columns, arrow-backed `string` dtype): **succeeded**, ≈121–143 s, peak +2.4–3.3 GB (dominant contributor to the process peak — see memory section).
- Human slice (tax_id 9606): 193,814 rows → 193,711 unique `Symbol→GeneID` entries.
- **Mapping coverage: 63/100** symbols → Entrez. The 37 unmapped are mouse-only symbols / synonym-stale names (e.g. `CTGF` → human primary is `CCN2`, `CYR61` is a mouse alias, `GM*`/`2310015A10RIK` are mouse-specific); gene_info `Symbol` column is the primary symbol only. Phase 1 should also read the `Synonyms` column for higher coverage.

### GOATOOLS run (human, taxid 9606) — PASS

- gene2go stream-filter to 9606: 446,674 rows (~61–90 s, ~0 extra RSS).
- `GODag(go-basic.obo)`: **1.18–2.08 s**, **41,378 nodes** (rel 2026-07-26).
- `Gene2GoReader` assoc: ≈3.7–4.4 s; per-NS gene counts BP 18,131 / CC 19,487 / MF 18,607.
- `GOEnrichmentStudyNS(population=63 mapped Entrez, … propagate_counts=True, alpha=0.05, methods=[…])`: init 0.56–3.78 s; **`run_study` 0.08–0.12 s** → **2,223 results** (BP 1,613 + CC 285 + MF 325).
- **Significant (fdr_bh<0.05): 0/2,223.** Expected: population == study (the 63 DEGs act as their own background), which makes the ORA test trivial; the goal here is mechanics, not significance. Sample rows: `GO:0060048 BP cardiac muscle contraction p_fdr 1.0 study_count 1`, `GO:0034329 BP cell junction assembly p_fdr 1.0 study_count 3`, `GO:0051641 BP cellular localization p_fdr 1.0 study_count 9`.
- **Gene contributions**: all 2,223 results expose `study_items` (Entrez ids), and 6,566/6,566 study items mapped back to symbols — `_gene_set` construction is fully supported.
- `goatools_human_results.csv` (2,223 rows incl. pop_count/pop_n) saved; converter consumed it.

### Memory (isolated fresh process, `p0-3_memory.json`)

| Phase | Peak-RSS delta |
|---|---|
| baseline | 370 MB |
| + obo load | 0 KB measurable (DAG fits in existing arenas) |
| + assoc build | +189 MB |
| + gene_info full parse | **+3,329 MB** (dominant; arrow-string parse of 72 M rows) |
| + NS init (propagation) | +1,379 MB (new peak growth) |
| + run_study | +0 |
| **peak RSS** | **5.02 GB** |

Notes: `ru_maxrss` is process-peak, so per-phase deltas are lower bounds during shared-process runs; the numbers above come from a run ordered to capture GOATOOLS phases before the gene_info parse. **Attribution caveat (architect-corrected)**: the 5.02 GB peak combines the gene_info full parse (+3,329 MB) AND the NS-init propagation (+1,379 MB, an unattributed lower bound in this shared process) — the peak is NOT uniquely attributable to gene_info. The F2 "≤800 MB increase" ceiling is verified here for the **obo/assoc session cache (+189 MB) only**; Phase 1 must measure the clean-process local-GO footprint (obo+assoc+NS init+run_study, no gene_info resident) against P3-6, and stream-filter gene_info per species (mirrors the `gene2go_9606` cache design) or persist a compact per-species symbol map.

### goatools 1.6.5 × current stack findings (Phase 1 action items)

1. `GOEnrichmentStudyNS`/`GOEnrichmentStudy` no longer accept method string `'fisher_scipy'` — verified at package level against the installed goatools 1.6.5 (`goatools/multiple_testing.py` method registry); Fisher exact is now the fixed base p-value calc and `methods=` covers only multiple-test corrections. Use `methods=['fdr_bh']`.
2. goatools 1.6.5's `fdr_bh` statsmodels path does `from statsmodels.sandbox.stats.multicomp import multipletests`; in statsmodels 0.15 the **`multipletests` name is absent from `statsmodels.sandbox.stats.multicomp`** (the module itself exists — "removed module" wording would be imprecise) → `fdr_bh` fails without a shim (verified at package level against the installed venv; no run traceback captured). PoC workaround: monkeypatch `statsmodels.sandbox.stats.multicomp.multipletests = statsmodels.stats.multitest.multipletests` (shim logged in script). **Phase 1 decision (architect): pin `statsmodels>=0.14.0,<0.15`** (statsmodels exists solely to serve goatools `fdr_bh` in this venv) + a mini-fixture `fdr_bh` end-to-end regression test; do NOT carry the monkeypatch shim into product code.
3. `_parse_gene_symbols` fallback & clustering: unchanged product behavior confirmed compatible (see P0-5).

---

## Converter contract asserts (P0-4) — **PASS** (12/12)

`poc_converter.py` (standalone, no `src/` imports) implements plan §6.3–6.6 and asserts **A–G against enrichr GO, enrichr KEGG, and GOATOOLS outputs**; output: merged standardized frame `phase0_poc_standardized.csv` (3,053 rows: enrichr GO 723 + enrichr KEGG 107 + GOATOOLS 2,223).

| Assert | Result | Detail |
|---|---|---|
| A1 `_gene_set` non-empty (enrichr GO) | PASS | 723/723 rows non-empty |
| A2 `_gene_set` non-empty (GOATOOLS) | PASS | 2,223/2,223 rows non-empty |
| A3 multi-delimiter unit (`GENE1;GENE2/GENE3,GENE4` → 4) | PASS | rejoin `GENE1/GENE2/GENE3/GENE4` |
| B `gene_ratio` `^\d+/\d+$` | PASS | 0 bad rows |
| C `bg_ratio` `^\d+/\d+$` | PASS | 0 bad rows |
| D `fold_enrichment` finite (non-zero denom) | PASS | 0 non-finite with M>0; 0 M==0 rows; range 0.0012–587.92 |
| E1 direction ∈ {UP,DOWN,TOTAL} | PASS | |
| E2 ontology ∈ {BP,CC,MF,KEGG} | PASS | |
| E3 label parse mirrors `_extract_direction_ontology` | PASS | 0 mismatches |
| F1 GO rows have `GO:\d{7}` | PASS | 2,946/2,946 |
| F2 KEGG `term_id` empty unless `^hsa\d+` | PASS | observed hsa=0, empty=107/107 |
| G description canonical (shared term_ids) | PASS | 622 shared enrichr⇄GOATOOLS ids; **0 conflicts**; raw enrichr Title-Case differed from obo name for 622/622 → canonicalized to obo name (e.g. `Establishment Of Mitotic Spindle Orientation (GO:0000132)` → `establishment of mitotic spindle orientation`) |

Converter formulas (documented in script): `gene_ratio` = enrichr `Overlap` as-is / GOATOOLS `{study_count}/{study_n}`; `bg_ratio` `M/N` with M = cached-GMT term size (enrichr GO GMT universe 14,698; KEGG GMT universe 8,078) or GOATOOLS assoc term size (`count_terms` over full 9606 assoc, 17,987 terms), N = background size (online = DEG count 100; local = 63); `fold` = gene_ratio/bg_ratio with 0-denominator→NaN (mirrors `go_kegg_loader._compute_fold_enrichment`); term_id GO = first `GO:\d{7}`, KEGG = `''` unless defensive `^hsa\d+`; description ordering obo name > GMT name > Enrichr Term.

Full PASS/FAIL log: `poc_converter_output.txt`.

---

## Dialog smoke (P0-5) — **PASS**

Standardized frame (`term`, `description`, `term_id`, `gene_count`, `bg_count`, `fdr`, `pvalue`, `gene_ratio`, `bg_ratio`, `fold_enrichment`, `gene_symbols`, `gene_set`, `direction`, `ontology`, `_gene_set`) built from the converter output:

- **Loader round-trip**: converted frame fed to `GOKEGGLoader()._standardize_columns()` + `_parse_gene_symbols()` in the loader input vocabulary → 3,053 rows, 3,053 non-empty `_gene_set`, `description` round-trips unchanged → compatibility confirmed.
- `Dataset('Phase0PoC', DatasetType.GO_ANALYSIS, dataframe=…)` → `is_valid == True`.

Offscreen (`QT_QPA_PLATFORM=offscreen`, Agg):

| Dialog | Result |
|---|---|
| GOBarChartDialog | **PASS** (instantiate+show+processEvents+close, no exception) |
| GODotPlotDialog | **PASS** |
| GONetworkDialog | **PASS** |
| GOClusteringDialog | **PASS** |

**Clustering merge acceptance (≥1 pair > 0.3)**: product-path `GOClustering(similarity_threshold=0.3).fit(df).cut(0.3)` → **103 non-singleton clusters**; independent pairwise Jaccard over `_gene_set` → **max Jaccard 1.0000** at rows (0, 1916) = `GO:0014912 negative regulation of smooth muscle cell migration` present in both enrichr (BP) and GOATOOLS (BP) with identical 3-gene overlaps → **PASS**. (Cosmetic-only warnings on this headless box: matplotlib "Font family 'Arial' not found" fallback and missing Korean glyphs in DejaVu Sans — no crash; note: the clustering dialog's current default similarity threshold is **0.7**, "0.7 recommended", not ~0.3 as assumed in the plan — reconcile in Phase 1.)

Evidence: `p0-5_output.txt`, `p0-5_dialog_smoke.py`.

---

## Regression (P0-6) — **PASS** (with pre-existing drift documented)

- Exact plan command from repo root **as-is** fails at collection: `ModuleNotFoundError: No module named 'models'/'core'` — the repo has no `pytest.ini`/`conftest.py`/pythonpath config (plan Phase 1 creates `pytest.ini`). Verbatim: `p0-6_pytest_plain.txt`.
- With the src path on sys.path (`PYTHONPATH=src`, the app's own import mode): **4 failed, 16 passed, 3 errors** (verbatim: `p0-6_pytest_srcpath.txt`):
  - `test_models.py::TestDifferentialExpressionData::test_is_significant` — `TypeError: 'bool' object is not callable`: `DifferentialExpressionData.is_significant` is a **@property-with-args** in current `src/models/data_models.py`; the test calls it as a method.
  - `test_models.py::TestDataset::{test_dataset_creation,test_get_filtered_data,test_get_genes}` and `test_statistics.py` (3 fixture setup errors) — `Dataset.__init__() got an unexpected keyword argument 'column_mapping'`: the kwarg was removed from the current `Dataset` constructor.
- **None of these involve the newly installed packages** (only added packages per freeze diff; statistics.py imports numpy/pandas/scipy only; pandas/numpy/scipy versions identical before/after install) → **no regression attributable to the P0-1 dependency additions**. Pre-existing test/code drift, to be fixed in Phase 1 alongside `pytest.ini` (do not fix product code per P0-6 instructions).
- `test_figure_bundle_export.py` (F9-critical): **3 passed** when run standalone; `test_fsm.py` green in the combined run.

---

## Mouse (P0-7) — **PASS**

- **Local GOATOOLS taxid 10090**: 50 Title-case candidate mouse symbols → **48 mapped / 50 candidates** (unmapped: `Tp73`/`Trp73` and `Hprt`/`Hprt1` alias collisions — Phase 1 mapper must read the gene_info `Synonyms` column); all 48 study items found in assoc/population (the "48/48" figure in `p0-7_output.txt` is this study/population hit rate). gene2go mouse slice: 595,946 rows / 26,029 genes. `run_study` → **4,343 results** (BP 3,538 + CC 335 + MF 470), **0 significant at fdr_bh<0.05** (self-background, same as human — mechanics validated). Wall: obo 0.75 s, assoc 3.71 s, NS init 0.35 s, **run 0.06 s**; symbol restore confirmed (e.g. `BAX/IL1B`, `AKT1/CCND1/JUN`). Results: `goatools_mouse_results.csv`.
- **Online mouse library check (A3)**: `get_library_name(organism='mouse')` → 228 libraries (1.05 s).
  - Libraries containing `mouse`/`MGI` (10): `HDSigDB_Mouse_2021`, `JASPAR_PWM_Mouse_2025`, `KEGG_2019_Mouse`, `KOMP2_Mouse_Phenotypes_2022`, `MGI_Mammalian_Phenotype_Level_4_2021`, `MGI_Mammalian_Phenotype_Level_4_2024`, `Mouse_Gene_Atlas`, `PerturbAtlas_MouseGenePerturbationSigs`, `WikiPathways_2019_Mouse`, `WikiPathways_2024_Mouse` (full list: `enrichr_mouse_libraries.json`).
  - GO/KEGG-named mouse sets: **only `KEGG_2019_Mouse`**. **No mouse GO Biological Process (or any GO) library exists** (0 found) → Enrichr GO libraries (e.g. `GO_Biological_Process_2023`) are human-centered → **mouse = local-first (A3) confirmed**.

---

## ADR evidence summary

| ADR | Finding / recommendation |
|---|---|
| **ADR-1 (local GO engine)** | GOATOOLS **viable — YES**: end-to-end human+mouse runs succeed; `run_study` ≈0.1 s; obo+assoc ≈+190 MB (F2 ≤800 MB bound met for the obo/assoc session cache — clean-process full local-GO footprint still to be measured in Phase 1); the 5.02 GB peak mixes the full-file gene_info parse (+3.3 GB) with NS-init (+1.38 GB) in a shared process — Phase 1 stream-filters per species. Must absorb 3 goatools-1.6.5 quirks (module rename, `fisher_scipy` string removal, statsmodels sandbox `multipletests` name removal — decided: pin statsmodels <0.15). Option 1 (hybrid) remains the recommended default. |
| **ADR-2 (background policy)** | enrichr() signature **has** `background`; for library names gseapy 1.3.1 routes it to the experimental **Speedrichr** API (package-source verified; docstring's "ignored" line is stale drift; no P0-2 empirical call). Enrichr-online custom background is **unsupported in v1 by decision** (unvalidated third-party service — ToS/privacy/reproducibility) → **recommend 2A (mode forcing)**; Phase 1 `EnrichmentAnalyzer` guards against passing `background` online and pins a `-m network` test. Custom backgrounds are honored only on the local path (GOATOOLS population, local GMT `enrich`). |
| **ADR-3 (cache path)** | PoC wrote nothing outside the report dir (`outdir=None`; no stray files). No product decision changed; plan 3A (AppDataLocation) stands as-is. |
| **ADR-4 (KEGG term_id)** | Online KEGG `Term` contains **no `hsa` IDs (0/107)** → **4A (empty term_id, keying on description+`_gene_set`) confirmed workable**: KEGG rows carried through converter asserts (B/C/D/E/F2) and do not participate in GO clustering keys; 4B (KEGG REST name→ID enrichment) remains an optional Phase 1 enhancement. |
| **ADR-5 (offline forcing)** | No CLI work done in the PoC (pure verification); plan 5(b) (QSettings + detect_online, no CLI flag) is unaffected. |

---

## Phase 1 action items (mandatory, from Gate-1 review)

1. **EnrichmentAnalyzer 2A guard**: never pass `background=` to online `enrichr()` calls; if background is set + online mode requested → force local path + dialog warning. Add a `-m network` test pinning gseapy 1.3.1's Speedrichr route (set/list background for library names) or deliberately blocking it.
2. **Dependency pinning**: `statsmodels>=0.14.0,<0.15` in requirements/setup (sole purpose: goatools `fdr_bh`); update plan §10-0/§6.2 imports to `from goatools.goea.go_enrichment_ns import GOEnrichmentStudyNS` and `methods=['fdr_bh']`; add a mini-fixture `fdr_bh` end-to-end regression test.
3. **Memory**: measure the clean-process local-GO footprint (obo+assoc+NS init+run_study, no gene_info resident) against P3-6 ≤800 MB; stream-filter gene_info per species and persist a compact per-species symbol map incl. the `Synonyms` column (mouse aliases Tp73/Trp73, Hprt/Hprt1).
4. **test infra**: create `pytest.ini` (markers network/offline/qt + pythonpath) and `test/conftest.py` (`block_network` fixture); fix the 4 failed + 3 errored pre-existing drift tests (`is_significant` property contract, `Dataset(column_mapping=)` removal) so the F9 regression set is green in every Phase.
5. **Converter (Phase 1 `standardize_go_dataframe`)**: species-aware `_gene_set` casing (human=UPPER, mouse=Title — A6; PoC `normalize_genes` uppercases, human-only — must not be reused for mouse); surface GMT-snapshot-missing term sizes as W1/NaN instead of silent overlap-count fallback (poc_converter lines 139/161), with one missing-id unit test; description canonicalization must add cached-GMT names as fallback for GO ids missing from obo (PoC kept enrichr Title-Case for those — display-only); serialize `_gene_set` deterministically (sorted `/`-join) in any exported frame — the PoC CSV's Python set-repr column is not byte-stable across PYTHONHASHSEED (architect info).
6. **F8**: locate a working `go-basic.obo.gz` mirror (403/404 on primary mirrors during PoC) or formally accept the uncompressed 30.7 MB file.
7. **Dialog threshold reconciliation**: the clustering dialog's current default is 0.7 ("0.7 recommended"), not the plan's assumed ~0.3 — align the tooltip/default in Phase 2 or update the plan.
8. **KEGG 4B (optional)**: KEGG REST name→ID mapping remains a Phase 1 optional enhancement; 4A (empty term_id, description+`_gene_set` keying) is validated by P0-4/P0-5.

---

## Risks observed

1. **goatools 1.6.5 × statsmodels 0.15 incompatibility**: `statsmodels.sandbox.stats.multicomp` exists in 0.15 but its `multipletests` name is gone, so goatools' `fdr_bh` fails without a shim or pin (package-level verified; no run traceback captured). Phase 1: pin `statsmodels>=0.14.0,<0.15` + `fdr_bh` regression fixture.
2. **goatools API drift vs plan text**: `goatools.goea_go_enrich_nss` → `goatools.goea.go_enrichment_ns`; method string `fisher_scipy` removed (Fisher is the fixed base test). Update plan §10-0 commands/imports.
3. **NCBI raw file growth**: gene2go.gz 1.38 GB / gene_info.gz 1.57 GB (10.99 / 10.35 GB uncompressed); full pandas parse of gene_info = +3.3 GB of the 5.02 GB peak (NS init adds +1.38 GB elsewhere in the same process). Phase 1 must stream-filter per species (as prototyped), persist a compact per-species symbol map incl. the `Synonyms` column (mouse aliases Tp73/Trp73, Hprt/Hprt1), and measure the clean-process local-GO footprint against P3-6.
4. **F8 compressed-obo availability**: `go-basic.obo.gz` not retrievable from primary mirrors during the PoC (403/AccessDenied/404); uncompressed 30.7 MB confirmed. Verify an alternate gz mirror in Phase 1.
5. **Pre-existing test drift + no pytest.ini**: 4 failed/3 errored due to `is_significant` property-with-args and removed `Dataset(column_mapping=…)` kwarg; repo also lacks pythonpath config so plain `pytest` cannot collect. All pre-existing; Phase 1 infra (`pytest.ini`, test updates) addresses them.
6. **Dialog default threshold 0.7 vs plan "~0.3"** — the clustering dialog/"0.7 recommended" default differs from the plan's stated ~0.3; reconcile UI default/tooltip with the plan.
7. **Headless font cosmetics**: 'Arial' missing (matplotlib falls back) and DejaVu lacks Korean glyphs on this WSL2/headless box — graphical-only, no crash; not relevant to packaged Windows/macOS builds (fonts bundled by OS).
8. **Mouse symbol aliases** (`Tp73`/`Trp73`, `Hprt`/`Hprt1`): gene_info primary-Symbol mapping misses official-name variants; Phase 1 mapper should use the `Synonyms` column.
9. **GOATOOLS significance = 0 on DEG-self backgrounds** (human & mouse): expected under population==study; the enrichment UI must use a proper background (specified DEG background or genome annotation) as designed in §6.2; PoC gates concerned mechanics, not effect sizes.

---

## Artifacts (all under `docs/planning/generated/phase0_poc/`)

`baseline_freeze.txt`, `final_freeze.txt`, `p0-1_import_check.{py,output.txt}`, `p0-1_pip_install.txt`, `enrichr_go_bp_2023.csv`, `enrichr_kegg_2021_human.csv`, `p0-2_{enrichr_real_call,format_inspect}.py`, `p0-2_output.txt`, `p0-3_goatools_local.py`, `p0-3b_memory_isolated.py`, `p0-3c_goatools_popcounts.py`, `p0-3_{output,3b_output,3c_output,summary,memory,download_manifest}.json|txt`, `goatools_human_results.csv`, `goatools_mouse_results.csv`, `p0-3_genes.json`, `entrez2sym_human.json`, `mouse_entrez_map.json`, `obo_names.json`, `goatools_term_sizes.json`, `gmt_go_sizes.json`, `gmt_kegg_sizes.json`, `p0-4_prep_maps.py`, `poc_converter.py`, `poc_converter_output.txt`, `phase0_poc_standardized.csv`, `p0-5_dialog_smoke.py`, `p0-5_output.txt`, `p0-6_pytest_plain.txt`, `p0-6_pytest_srcpath.txt`, `p0-7_mouse.py`, `p0-7_output.txt`, `enrichr_mouse_libraries.json`.

Storage: raw downloads (2.9 GB: go-basic.obo 30.7 MB, gene2go.gz 1.38 GB, gene_info.gz 1.57 GB, per-species filter extracts, GMT files) were **deleted after hashing**; sizes/times/sha256 are the durable evidence in `p0-3_download_manifest.json` and this report. The directory totals **1.2 MB** (slightly above the 1 MB soft target because two mandated engine-result CSVs + the merged standardized frame + compact maps are retained as the review evidence).

---

## Overall gate verdict

| Gate | Verdict | One-line evidence |
|---|---|---|
| **P0-1** | **PASS** | 5 packages installed (gseapy 1.3.1, goatools 1.6.5, mygene 3.2.2, statsmodels 0.15.0, requests 2.34.2); all imports OK (1 module-path fix noted); pandas 3.0.5/numpy 2.5.2/scipy 1.18.1 unchanged; `pip check` clean. |
| **P0-2** | **PASS** | Real enrichr calls: GO 723×10 (1.97 s), KEGG 107×10 (1.46 s); Overlap `k/n`; Genes `;`-joined; GO Terms embed GO ids (723/723); KEGG Terms contain NO hsa ids (0/107); `background` param routes to experimental Speedrichr for library names (unsupported online by decision → ADR-2 2A force-local; corrected body §P0-2(f)). |
| **P0-3** | **PASS** | GOATOOLS human end-to-end: obo 41,378 nodes/2.1 s; run_study 0.08 s → 2,223 terms; isolated memory peak 5.02 GB (gene_info parse +3.3 GB dominant; obo+assoc +189 MB); gene_info local mapping 63/100; shim/pin findings recorded. |
| **P0-4** | **PASS** | Converter asserts A–G: 12/12 PASS incl. multi-delimiter unit check, term_id policy (GO 2,946/2,946; KEGG hsa=0/107), description canonical 622 shared ids / 0 conflicts. |
| **P0-5** | **PASS** | 4 dialogs offscreen no-crash; loader round-trip 3,053/3,053 non-empty `_gene_set`; clustering merge ≥1 pair (103 non-singleton; max Jaccard 1.0000 GO:0014912). |
| **P0-6** | **PASS** | No regression from new deps: test_figure_bundle_export 3 passed; 4 failed + 3 errors are pre-existing test/src drift (property-with-args `is_significant`, removed `Dataset(column_mapping=…)`); recorded verbatim. |
| **P0-7** | **PASS** | Mouse GOATOOLS taxid 10090: 48/50 mapped (Tp73/Trp73, Hprt/Hprt1 alias-unmapped; all 48 study items in assoc), run 0.06 s → 4,343 terms; Enrichr mouse: 228 libraries, GO/KEGG mouse set = only `KEGG_2019_Mouse`, **0 mouse GO libraries** → A3 mouse=local-first. |

**Gate 1 (Phase 0→1) verdict: ALL P0-1…P0-7 PASS — Phase 1 may proceed** (with the Phase 1 action items: goatools import/method/statsmodels fixes, pytest.ini + test-drift fixes, stream-filtered gene_info caching, compressed-obo mirror check, KEGG 4A keying, dialog threshold reconciliation).