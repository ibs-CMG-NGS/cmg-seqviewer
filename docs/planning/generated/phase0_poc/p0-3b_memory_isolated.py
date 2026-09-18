"""
P0-3b: GOATOOLS memory isolation (fresh process) + artifact preparation.
Incremental ru_maxrss per phase BEFORE the heavy gene_info parse contaminates peak.
Also prepares: entrez2sym_human.json, mouse symbol map, gene2go_mouse.tsv, sha256 manifest.
"""
import gzip, os, json, time, hashlib, resource
import pandas as pd

DATA = "docs/planning/generated/phase0_poc/data"
OUT = "docs/planning/generated/phase0_poc"
rss = lambda: resource.getrusage(resource.RUSAGE_SELF).ru_maxrss  # KB Linux

base = rss()
print(f"[baseline] rss={base}KB", flush=True)

# --- obo load ---
t0 = time.perf_counter()
from goatools.obo_parser import GODag
obo_dag = GODag(os.path.join(DATA, "go-basic.obo"), optional_attrs=["relationship"])
t_obo = time.perf_counter() - t0
r1 = rss()
print(f"[obo] wall={t_obo:.2f}s rss_delta={r1-base}KB nodes={len(obo_dag)}", flush=True)

# --- assoc (human GT) ---
from goatools.anno.genetogo_reader import Gene2GoReader
t0 = time.perf_counter()
g2r = Gene2GoReader(os.path.join(DATA, "gene2go_human.tsv"), taxids=[9606])
ns2assoc = g2r.get_ns2assc()
t_a = time.perf_counter() - t0
r2 = rss()
print(f"[assoc human] wall={t_a:.2f}s rss_delta={r2-r1}KB sizes={ {k:len(v) for k,v in ns2assoc.items()} }", flush=True)

# --- NS init + run_study ---
import statsmodels.sandbox.stats.multicomp as _sm_mc
from statsmodels.stats.multitest import multipletests as _mp
_sm_mc.multipletests = _mp  # goatools 1.6.5 x statsmodels 0.15 shim
from goatools.goea.go_enrichment_ns import GOEnrichmentStudyNS

genes = json.load(open(os.path.join(OUT, "p0-3_genes.json"))) if os.path.exists(os.path.join(OUT, "p0-3_genes.json")) else None
# rebuild 100-gene list + entrez mapping (needed for study ids)
da = pd.read_parquet("examples/Acute_1D_vs_Control_DA.parquet")
sym = da["gene_name"].dropna().astype(str).str.strip()
sym = sym[sym != ""]
uniq, seen = [], set()
for s in sym:
    u = s.upper()
    if u not in seen and u != "NAN":
        seen.add(u); uniq.append(u)
genes = uniq[:100]
json.dump(genes, open(os.path.join(OUT, "p0-3_genes.json"), "w"))

# gene_info full parse (after GOATOOLS phases, so isolated rss deltas captured above)
GI_COLS = ["tax_id","GeneID","Symbol","LocusTag","Synonyms","dbXrefs","chromosome",
           "map_location","description","type_of_gene",
           "Symbol_from_nomenclature_authority",
           "Full_name_from_nomenclature_authority","Nomenclature_status",
           "Other_designations","Modification_date","Feature_type"]
t0 = time.perf_counter()
f = gzip.open(os.path.join(DATA, "gene_info.gz"), "rt", errors="replace")
gi = pd.read_csv(f, sep="\t", comment="#", names=GI_COLS,
                 usecols=["tax_id","GeneID","Symbol"],
                 dtype={"tax_id":"int32","GeneID":"int32","Symbol":"string"},
                 engine="c", low_memory=True)
t_gi = time.perf_counter() - t0
r3 = rss()
print(f"[gene_info full parse] wall={t_gi:.2f}s rss_delta={r3-r2}KB rows={len(gi)}", flush=True)

h = gi[gi["tax_id"] == 9606]
m = gi[gi["tax_id"] == 10090]
hmap = dict(zip(h["Symbol"].astype(str).str.upper(), h["GeneID"].astype(int)))
mmap = dict(zip(m["Symbol"].astype(str).str.upper(), m["GeneID"].astype(int)))
print(f"[maps] human_symbols={len(hmap)} mouse_symbols={len(mmap)}", flush=True)

entrez = [hmap[g] for g in genes if g in hmap]
geneid2sym = {v: k for k, v in hmap.items()}
esym = {str(e): geneid2sym[e] for e in entrez}
json.dump(esym, open(os.path.join(OUT, "entrez2sym_human.json"), "w"))
print(f"[map save] entrez2sym_human.json entries={len(esym)}", flush=True)

# mouse gene2go filter + mouse symbol map for P0-7
t0 = time.perf_counter()
with gzip.open(os.path.join(DATA, "gene2go.gz"), "rt", errors="replace") as fin, \
     open(os.path.join(DATA, "gene2go_mouse.tsv"), "w", newline="") as fout:
    hdr = fin.readline(); fout.write(hdr)
    n = 0
    for line in fin:
        if line.split("\t", 1)[0] == "10090":
            fout.write(line); n += 1
print(f"[gene2go mouse filter] rows={n} wall={time.perf_counter()-t0:.2f}s", flush=True)

# mouse ~50 symbols (Title-case trials) for P0-7
mouse_genes = ["Trp53","Myc","Cdkn1a","Bcl2","Bax","Casp3","Mtor","Akt1","Stat3","Jun",
               "Pten","Mdm2","Tp73","Casp9","Bad","Bak1","Mcl1","Mapk1","Mapk3","Pik3ca",
               "Pik3r1","Foxo3","Rela","Nfkb1","Nfkb2","Sirt1","Ubc","Gapdh","Actb","Hprt",
               "Tnf","Il6","Il1b","Ccl2","Cxcl1","Vegfa","Hif1a","Sod1","Cat","Gpx1",
               "Odc1","Psma1","Psmb5","Hsp90aa1","Hspa8","Eif4e","Rps6","Cdkn2a","Rb1","Ccnd1"]
mapped_mouse = {g: int(v) for g, v in mmap.items() if g in set(x.upper() for x in mouse_genes)}
json.dump(mapped_mouse, open(os.path.join(OUT, "mouse_entrez_map.json"), "w"))
print(f"[mouse map] {len(mapped_mouse)}/{len(mouse_genes)} mouse symbols mapped", flush=True)

# incrementally proceed: GOEnrichmentStudyNS init + run_study (isolated deltas worth reporting)
t0 = time.perf_counter()
goea = GOEnrichmentStudyNS(entrez, ns2assoc, obo_dag, propagate_counts=True,
                           alpha=0.05, methods=["fdr_bh"])
t_init = time.perf_counter() - t0
r4 = rss()
print(f"[NS init] wall={t_init:.2f}s rss_delta={r4-r3}KB", flush=True)

t0 = time.perf_counter()
results = goea.run_study(entrez)
t_run = time.perf_counter() - t0
r5 = rss()
print(f"[run_study] wall={t_run:.2f}s rss_delta={r5-r4}KB n_results={len(results)}", flush=True)

# sha256 manifest of raw downloads
manifest = {}
for fn in ["go-basic.obo", "gene2go.gz", "gene_info.gz"]:
    p = os.path.join(DATA, fn)
    t0 = time.perf_counter()
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    manifest[fn] = {"sha256": h.hexdigest(), "size_bytes": os.path.getsize(p), "hash_s": round(time.perf_counter()-t0, 1)}
json.dump(manifest, open(os.path.join(OUT, "p0-3_download_manifest.json"), "w"), indent=2)
print("[manifest]", json.dumps(manifest))

mem = {"baseline_kb": base, "after_obo_kb": r1, "after_assoc_kb": r2,
       "after_geneinfo_kb": r3, "after_ns_init_kb": r4, "after_run_kb": r5,
       "obo_delta_kb": r1-base, "assoc_delta_kb": r2-r1, "geneinfo_delta_kb": r3-r2,
       "ns_init_delta_kb": r4-r3, "run_delta_kb": r5-r4,
       "peak_rss_kb": r5, "peak_gb": round(r5/1048576, 2)}
json.dump(mem, open(os.path.join(OUT, "p0-3_memory.json"), "w"), indent=2)
print("[memory]", json.dumps(mem))
print("P0-3b DONE")
