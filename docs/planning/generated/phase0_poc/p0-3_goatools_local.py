"""
P0-3: GOATOOLS local run + timing/memory + gene_info mapping.
Read-only w.r.t. src/; everything under docs/planning/generated/phase0_poc/.
"""
import gzip, os, re, sys, time, json, itertools, io
import resource, pandas as pd
import numpy as np

DATA = "docs/planning/generated/phase0_poc/data"
OUT = "docs/planning/generated/phase0_poc"
rss = lambda: resource.getrusage(resource.RUSAGE_SELF).ru_maxrss  # KB on Linux

# --- goatools 1.6.5 x statsmodels 0.15 compatibility shim (recorded finding) ---
# goatools' fdr_bh statsmodels path does: from statsmodels.sandbox.stats.multicomp import multipletests
# that sandbox module was removed in statsmodels 0.15; equivalent API lives in statsmodels.stats.multitest.
import statsmodels.sandbox.stats.multicomp as _sm_mc
from statsmodels.stats.multitest import multipletests as _mp
if not hasattr(_sm_mc, "multipletests"):
    _sm_mc.multipletests = _mp
    log = print
    print("[shim] statsmodels.sandbox.stats.multicomp.multipletests -> statsmodels.stats.multitest.multipletests")

def log(msg):
    print(msg, flush=True)

# ---------- 100 gene list (same as P0-2) ----------
da = pd.read_parquet("examples/Acute_1D_vs_Control_DA.parquet")
sym = da["gene_name"].dropna().astype(str).str.strip()
sym = sym[sym != ""]
uniq, seen = [], set()
for s in sym:
    u = s.upper()
    if u not in seen and u != "NAN":
        seen.add(u); uniq.append(u)
genes = uniq[:100]
log(f"[genes] {len(genes)} symbols from parquet; first10={genes[:10]}")

# ---------- gene2go: stream-filter taxid 9606 -> gene2go_9606.tsv ----------
f_g2g = os.path.join(DATA, "gene2go_human.tsv")
t0 = time.perf_counter(); m0 = rss()
n_human = 0
with gzip.open(os.path.join(DATA, "gene2go.gz"), "rt", errors="replace") as fin, \
     open(f_g2g, "w", newline="") as fout:
    header = fin.readline()          # '#tax_id\tGeneID\t...'
    fout.write(header)
    for line in fin:
        t = line.split("\t", 1)[0]
        if t == "9606":
            fout.write(line); n_human += 1
t1 = time.perf_counter()
log(f"[gene2go filter] human rows={n_human} wall={t1-t0:.2f}s mem_delta={rss()-m0}KB file={f_g2g}")

# ---------- gene_info mapping ----------
MAP = {}
geneinfo_status = "full-pandas-attempt"
m0 = rss(); t0 = time.perf_counter()
try:
    # full-file pandas read, arrow-backed string dtype to reduce memory
    GI_COLS = ["tax_id","GeneID","Symbol","LocusTag","Synonyms","dbXrefs","chromosome",
               "map_location","description","type_of_gene",
               "Symbol_from_nomenclature_authority",
               "Full_name_from_nomenclature_authority","Nomenclature_status",
               "Other_designations","Modification_date","Feature_type"]
    f = gzip.open(os.path.join(DATA, "gene_info.gz"), "rt", errors="replace")
    gi = pd.read_csv(f, sep="\t", comment="#", names=GI_COLS,
                     usecols=["tax_id", "GeneID", "Symbol"],
                     dtype={"tax_id": "int32", "GeneID": "int32", "Symbol": "string"},
                     engine="c", low_memory=True)
    t_full = time.perf_counter() - t0
    log(f"[gene_info FULL pandas read] rows={len(gi)} wall={t_full:.2f}s mem_delta={rss()-m0}KB")
    gi = gi[gi["tax_id"] == 9606]
    MAP = dict(zip(gi["Symbol"].astype(str).str.upper(), gi["GeneID"].astype(int)))
    log(f"[gene_info FULL read] human rows={len(gi)} unique_symbols={len(MAP)}")
except (MemoryError, OSError, ValueError) as e:
    geneinfo_status = f"full-pandas-failed:{type(e).__name__}:{e}"
    log(f"[gene_info FULL pandas read] FAILED -> {geneinfo_status}")
    # fallback: stream filter to human-only, then pandas
    f_h = os.path.join(DATA, "gene_info_human.tsv")
    m0b = rss(); t0b = time.perf_counter()
    n_h = 0
    with gzip.open(os.path.join(DATA, "gene_info.gz"), "rt", errors="replace") as fin, \
         open(f_h, "w", newline="") as fout:
        hheader = fin.readline()
        fout.write(hheader)
        for line in fin:
            if line.split("\t", 1)[0] == "9606":
                fout.write(line); n_h += 1
    t_filt = time.perf_counter() - t0b
    log(f"[gene_info stream filter] human rows={n_h} wall={t_filt:.2f}s mem_delta={rss()-m0b}KB")
    gi = pd.read_csv(f_h, sep="\t", usecols=["tax_id", "GeneID", "Symbol"],
                     dtype={"tax_id": "int32", "GeneID": "int32", "Symbol": "string"})
    gi = gi[gi["tax_id"] == 9606]
    MAP = dict(zip(gi["Symbol"].astype(str).str.upper(), gi["GeneID"].astype(int)))
    log(f"[gene_info fallback] human rows={len(gi)} unique_symbols={len(MAP)}")
log(f"[gene_info mapping parse wall={time.perf_counter()-t0:.2f}s final_mem_delta={rss()-m0}KB]")

entrez = [MAP[g] for g in genes if g in MAP]
cov = len(entrez)
log(f"[mapping coverage] {cov}/{len(genes)} symbols -> Entrez")
unmapped = [g for g in genes if g not in MAP]
log(f"[mapping] unmapped({len(unmapped)}): {unmapped[:20]}")
geneid2sym = {v: k for k, v in MAP.items()}
assert cov >= 1, "zero mapping coverage - cannot run GOATOOLS"

# ---------- obo load ----------
t0 = time.perf_counter(); m0 = rss()
from goatools.obo_parser import GODag
obo_dag = GODag(os.path.join(DATA, "go-basic.obo"), optional_attrs=["relationship"])
t_obo = time.perf_counter() - t0
log(f"[obo] load wall={t_obo:.2f}s mem_delta={rss()-m0}KB nodes={len(obo_dag)}")

# ---------- assoc + study ----------
from goatools.anno.genetogo_reader import Gene2GoReader
from goatools.goea.go_enrichment_ns import GOEnrichmentStudyNS
t0 = time.perf_counter(); m0 = rss()
g2r = Gene2GoReader(f_g2g, taxids=[9606])
ns2assoc = g2r.get_ns2assc()
t_assoc = time.perf_counter() - t0
log(f"[assoc] build wall={t_assoc:.2f}s mem_delta={rss()-m0}KB ns_assoc_sizes={ {k: len(v) for k, v in ns2assoc.items()} }")

t0 = time.perf_counter(); m0 = rss()
goea = GOEnrichmentStudyNS(entrez, ns2assoc, obo_dag, propagate_counts=True,
                           alpha=0.05, methods=["fdr_bh"])  # fisher_scipy removed in goatools>=1.1; fisher is the fixed base test
t_ns = time.perf_counter() - t0
log(f"[GOEnrichmentStudyNS init] wall={t_ns:.2f}s mem_delta={rss()-m0}KB")

t0 = time.perf_counter(); m0 = rss()
results = goea.run_study(entrez)
t_run = time.perf_counter() - t0
log(f"[run_study] wall={t_run:.2f}s mem_delta={rss()-m0}KB n_results={len(results)}")

# ---------- record ----------
rows = []
for r in results:
    rows.append({
        "GO": r.GO, "NS": r.NS, "name": r.name,
        "p_uncorrected": r.p_uncorrected, "p_fdr_bh": r.p_fdr_bh,
        "study_count": r.study_count, "study_n": r.study_n,
        "ratio_in_study": str(r.ratio_in_study),
        "study_items": sorted(r.study_items),  # Entrez ids
    })
res_df = pd.DataFrame(rows)
res_df.to_csv(os.path.join(OUT, "goatools_human_results.csv"), index=False)
sig = res_df[res_df["p_fdr_bh"] < 0.05]
n_sig = len(sig)
log(f"[results] significant(fdr_bh<0.05)={n_sig}/{len(res_df)}")
log(res_df[["GO","NS","name","p_fdr_bh","study_count","ratio_in_study"]].head(12).to_string())
# gene contributions check
with_contrib = sum(1 for r in results if getattr(r, "study_items", None))
log(f"[gene contrib] results with study_items (usable for _gene_set): {with_contrib}/{len(results)}")
example = results[0]
log(f"[sample result attrs] GO={example.GO} NS={example.NS} name={example.name!r} study_items={sorted(example.study_items)[:8]}")

# ---------- human coverage of study items ----------
symmapped = 0; total_items = 0
for r in results:
    ids = r.study_items
    total_items += len(ids)
    symmapped += sum(1 for i in ids if i in geneid2sym)
log(f"[symbol restore] study items mapped back to symbols: {symmapped}/{total_items}")

summary = {
    "gene_count": len(genes), "mapped_entrez": cov, "coverage": f"{cov}/{len(genes)}",
    "gene2go_human_rows": n_human, "gene_info_status": geneinfo_status,
    "obo_load_s": round(t_obo, 2), "obo_nodes": len(obo_dag),
    "assoc_build_s": round(t_assoc, 2), "ns_init_s": round(t_ns, 2),
    "run_study_s": round(t_run, 2), "mem_delta_run_KiB": rss() - m0,
    "n_results": len(results), "n_significant_fdr_bh_005": n_sig,
    "study_items_symbol_restore": f"{symmapped}/{total_items}",
}
with open(os.path.join(OUT, "p0-3_summary.json"), "w") as f:
    json.dump(summary, f, indent=2)
log("[summary] " + json.dumps(summary))
log("P0-3 DONE")
