"""Precompute small maps needed by the standalone converter (survive deletion of big data/ artifacts)."""
import os, json, time, re
import pandas as pd
DATA = "docs/planning/generated/phase0_poc/data"
OUT = "docs/planning/generated/phase0_poc"

# 1) obo name map for all GO ids used by GOATOOLS results + enrichr GO
from goatools.obo_parser import GODag
obo_dag = GODag(os.path.join(DATA, "go-basic.obo"), optional_attrs=["relationship"])
obo_names = {}
for go_id, term in obo_dag.items():
    obo_names[go_id] = term.name
print("obo_names entries:", len(obo_names))

# 2) GOATOOLS assoc term sizes: full 9606 assoc, propagate is_a (mirrors GOATOOLS count semantics)
from goatools.anno.genetogo_reader import Gene2GoReader
from goatools.ratio import count_terms
g2r = Gene2GoReader(os.path.join(DATA, "gene2go_human.tsv"), taxids=[9606])
assoc_union = {}
for rec in g2r.get_associations():   # flat per-gene-per-GO records
    assoc_union.setdefault(rec.DB_ID, set()).add(rec.GO_ID)
all_genes = sorted(assoc_union.keys())
print("9606 genes in assoc:", len(all_genes))
t0 = time.perf_counter()
term_pop = count_terms(all_genes, assoc_union, obo_dag)
print(f"count_terms full-assoc wall={time.perf_counter()-t0:.2f}s terms={len(term_pop)}")
goatools_term_sizes = {k: int(v) for k, v in term_pop.items()}
json.dump(goatools_term_sizes, open(os.path.join(OUT, "goatools_term_sizes.json"), "w"))
print("saved goatools_term_sizes.json entries:", len(goatools_term_sizes))

# 3) GMT maps (term size per term_id / name) + universe sizes
def load_gmt(path):
    sizes_by_go, sizes_by_name, universe = {}, {}, set()
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 3:
                continue
            name = parts[0]
            genes = [g.upper() for g in parts[2:] if g.strip() and g.upper() != "NAN"]
            universe.update(genes)
            m = re.search(r"\(GO:(\d{7})\)", name)
            if m:
                sizes_by_go["GO:" + m.group(1)] = len(genes)
            sizes_by_name[name] = len(genes)
    return sizes_by_go, sizes_by_name, len(universe)

g_go, n_go, u_go = load_gmt(os.path.join(OUT, "enrichr_output/gmt/GO_Biological_Process_2023.gmt"))
g_kg, n_kg, u_kg = load_gmt(os.path.join(OUT, "enrichr_output/gmt/KEGG_2021_Human.gmt"))
json.dump({"sizes_by_go": g_go, "universe": u_go}, open(os.path.join(OUT, "gmt_go_sizes.json"), "w"))
json.dump({"sizes_by_name": n_kg, "universe": u_kg}, open(os.path.join(OUT, "gmt_kegg_sizes.json"), "w"))
json.dump(obo_names, open(os.path.join(OUT, "obo_names.json"), "w"))
print("gmt_go: entries=", len(g_go), "universe=", u_go)
print("gmt_kegg: entries=", len(n_kg), "universe=", u_kg)
# sanity: GOATOOLS BP term M check (assoc vs GMT where both exist)
res = pd.read_csv(os.path.join(OUT, "goatools_human_results.csv"))
sample = res[res["GO"] == "GO:0007010"]
gs = goatools_term_sizes.get("GO:0007010")
gm = g_go.get("GO:0007010")
print("GO:0007010 cytoskeleton organization: assoc_size=", gs, "gmt_size=", gm, "study_count=", res[res.GO=='GO:0007010'].study_count.iloc[0])
print("P0-4 prep DONE")
