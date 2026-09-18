#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
P0-7: Mouse (taxid 10090) local GOATOOLS run + online Enrichr mouse-library check (A3).
Uses saved artifacts (gene2go_mouse.tsv, mouse_entrez_map.json, go-basic.obo).
"""
import json
import os
import resource
import time

DATA = "docs/planning/generated/phase0_poc/data"
OUT = "docs/planning/generated/phase0_poc"
rss = lambda: resource.getrusage(resource.RUSAGE_SELF).ru_maxrss  # KB

# ---- mouse symbols (Title-case per plan A6) and mapping ----
candidates = ["Trp53", "Myc", "Cdkn1a", "Bcl2", "Bax", "Casp3", "Mtor", "Akt1", "Stat3", "Jun",
              "Pten", "Mdm2", "Tp73", "Casp9", "Bad", "Bak1", "Mcl1", "Mapk1", "Mapk3", "Pik3ca",
              "Pik3r1", "Foxo3", "Rela", "Nfkb1", "Nfkb2", "Sirt1", "Ubc", "Gapdh", "Actb", "Hprt",
              "Tnf", "Il6", "Il1b", "Ccl2", "Cxcl1", "Vegfa", "Hif1a", "Sod1", "Cat", "Gpx1",
              "Odc1", "Psma1", "Psmb5", "Hsp90aa1", "Hspa8", "Eif4e", "Rps6", "Cdkn2a", "Rb1", "Ccnd1"]
mmap = json.load(open(os.path.join(OUT, "mouse_entrez_map.json")))  # symbol -> entrez (48)
entrez = sorted({int(v) for v in mmap.values()})
sym_by_id = {int(v): k for k, v in mmap.items()}
unmapped = [g for g in candidates if g.upper() not in mmap]
print(f"[mouse] candidates={len(candidates)} mapped={len(entrez)} unmapped={unmapped}", flush=True)

# ---- GOATOOLS mouse ----
import statsmodels.sandbox.stats.multicomp as _sm_mc
from statsmodels.stats.multitest import multipletests as _mp
_sm_mc.multipletests = _mp  # goatools 1.6.5 x statsmodels 0.15 shim
from goatools.obo_parser import GODag
from goatools.anno.genetogo_reader import Gene2GoReader
from goatools.goea.go_enrichment_ns import GOEnrichmentStudyNS

base = rss()
t0 = time.perf_counter()
obo_dag = GODag(os.path.join(DATA, "go-basic.obo"), optional_attrs=["relationship"])
t_obo = time.perf_counter() - t0
print(f"[mouse obo] wall={t_obo:.2f}s nodes={len(obo_dag)} rss_delta={rss()-base}KB", flush=True)

t0 = time.perf_counter()
g2r = Gene2GoReader(os.path.join(DATA, "gene2go_mouse.tsv"), taxids=[10090])
ns2assoc = g2r.get_ns2assc()
t_assoc = time.perf_counter() - t0
r1 = rss()
print(f"[mouse assoc] wall={t_assoc:.2f}s rss_delta={r1-base}KB sizes={ {k: len(v) for k, v in ns2assoc.items()} }", flush=True)

t0 = time.perf_counter()
goea = GOEnrichmentStudyNS(entrez, ns2assoc, obo_dag, propagate_counts=True, alpha=0.05, methods=["fdr_bh"])
t_init = time.perf_counter() - t0
print(f"[mouse NS init] wall={t_init:.2f}s", flush=True)

t0 = time.perf_counter()
results = goea.run_study(entrez)
t_run = time.perf_counter() - t0
r2 = rss()
print(f"[mouse run_study] wall={t_run:.2f}s rss_delta={r2-r1}KB n_results={len(results)}", flush=True)

rows = []
for r in results:
    rows.append({"GO": r.GO, "NS": r.NS, "name": r.name, "p_uncorrected": r.p_uncorrected,
                 "p_fdr_bh": r.p_fdr_bh, "study_count": r.study_count, "study_n": r.study_n,
                 "pop_count": getattr(r, "pop_count", ""), "pop_n": getattr(r, "pop_n", ""),
                 "symbols": "/".join(sorted({sym_by_id.get(i, str(i)) for i in r.study_items}))})
import pandas as pd
res_df = pd.DataFrame(rows)
res_df.to_csv(os.path.join(OUT, "goatools_mouse_results.csv"), index=False)
sig = res_df[res_df["p_fdr_bh"] < 0.05]
print(f"[mouse results] total={len(res_df)} significant(fdr_bh<0.05)={len(sig)}", flush=True)
print(res_df[["GO", "NS", "name", "p_fdr_bh", "study_count", "symbols"]].head(8).to_string(index=False), flush=True)

# ---- online mouse library check (A3) ----
import gseapy
from gseapy import get_library_name
try:
    t0 = time.perf_counter()
    libs = get_library_name(organism="mouse")  # hits Enrichr datasetStatistics
    t_libs = time.perf_counter() - t0
    print(f"[mouse libs] get_library_name(mouse) returned {len(libs)} libraries in {t_libs:.2f}s", flush=True)
    mouse_hits = [l for l in libs if ("mouse" in l.lower() or "mgi" in l.lower())]
    go_kegg_hits = [l for l in libs if ("GO_" in l or "KEGG" in l)]
    print(f"[mouse libs] libraries containing 'mouse'/'MGI' ({len(mouse_hits)}):", flush=True)
    for l in sorted(mouse_hits):
        print("   -", l, flush=True)
    print(f"[mouse libs] GO/KEGG-named libraries containing 'mouse'/'MGI': {len([l for l in mouse_hits if 'GO_' in l or 'KEGG' in l])}", flush=True)
    for l in sorted(mouse_hits):
        if "GO_" in l or "KEGG" in l:
            print("   (GO/KEGG)", l, flush=True)
    # explicitly list whether a mouse GO Biological Process library exists
    mouse_go_bp = [l for l in libs if "GO_Biological" in l and ("mouse" in l.lower() or "mgi" in l.lower())]
    print(f"[mouse libs] mouse GO_Biological_Process libraries found: {len(mouse_go_bp)} -> {mouse_go_bp}", flush=True)
    # document that GO_Biological_Process_2023 is human-centered (uppercase symbol library)
    print("[mouse libs] note: GO_Biological_Process_2023 (used in P0-2) is a human gene-symbol library; "
          "mouse-specific GO sets are NOT offered by Enrichr (evidence for ADR mouse=local-first)", flush=True)
    json.dump(sorted(libs), open(os.path.join(OUT, "enrichr_mouse_libraries.json"), "w"))
except Exception as e:
    import traceback
    print(f"[mouse libs] get_library_name FAILED: {e}", flush=True)
    traceback.print_exc()

print("P0-7 DONE", flush=True)